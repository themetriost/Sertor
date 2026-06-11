# Data Model — Installer `sertor install wiki` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Data**: 2026-06-11 | **Spec**: [`spec.md`](spec.md)

Entità del dominio dell'installer (Phase 1). Non è un modello di persistenza: l'installer opera **su
file**, senza DB. Le entità sono **value object / record in memoria** che descrivono *cosa* viene
installato e *con quale esito*. Naming di dominio (Principio VII): `Artifact`, `InstallPlan`,
`InstallReport`, `HostProfile`. Nessun import di SDK esterni (Principio I).

---

## 1. `Artifact` — artefatto installabile

Unità che l'installer porta sull'ospite. Ciascuno conosce la propria **regola di non-distruttività**.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `kind` | `ArtifactKind` (enum) | natura: `FILE`, `SETTINGS_MERGE`, `MARKER_BLOCK`, `STRUCTURE`, `CONFIG` |
| `source` | `str \| None` | risorsa negli assets (`importlib.resources`), per i `FILE`/`CONFIG`/`MARKER_BLOCK` |
| `target_rel` | `str` | percorso **relativo** al target (es. `.claude/skills/wiki-author/SKILL.md`) |
| `strategy` | `WriteStrategy` (enum) | `CREATE_IF_ABSENT`, `MERGE_DEDUP`, `APPEND_BLOCK`, `INIT_STRUCTURE`, `GENERATE_CONFIG` |

**`ArtifactKind` → `WriteStrategy` (mappa fissa):**

| `kind` | `strategy` | Regola di non-distruttività | FR |
|--------|-----------|------------------------------|----|
| `FILE` (skill, command, agent, hook) | `CREATE_IF_ABSENT` | esiste → skip (file-per-file); manca → crea | FR-008/012 |
| `SETTINGS_MERGE` (`.claude/settings.json`) | `MERGE_DEDUP` | merge additivo, dedup per `command`; malformato → fail-fast | FR-015 |
| `MARKER_BLOCK` (`CLAUDE.md`) | `APPEND_BLOCK` | marker presente → skip; assente → append/create | FR-014 |
| `CONFIG` (`wiki.config.toml`) | `GENERATE_CONFIG` | esiste → skip; manca → genera da template + valori inferiti | FR-013/018 |
| `STRUCTURE` (`wiki/`) | `INIT_STRUCTURE` | delega a `init_structure` (idempotente) | FR-010/016 |

**Regole di validità.**
- `target_rel` MUST essere relativo (mai assoluto, mai risalente con `..`): si risolve sotto `--target`.
- I `FILE` sono **inerti**: copia byte-per-byte dell'asset, nessuna trasformazione al momento
  dell'install (D3 — gli assets sono già host-agnostici).
- `CONFIG`/`MARKER_BLOCK` sono gli **unici** artefatti con contenuto **derivato** (template +
  valori) o **delimitato** (marker).

---

## 2. `HostProfile` — specificità inferita dell'ospite

Valori host-specifici raccolti *prima* di generare `wiki.config.toml` (D7). È l'unico punto in cui
l'installer "guarda" l'ospite; tutto il resto è inerte (Principio X: l'ospite si configura).

| Campo | Tipo | Origine | Default |
|-------|------|---------|---------|
| `target_root` | `Path` | `--target` o cwd | cwd |
| `source_dirs` | `list[str]` | `--source-dirs` o euristica (D7) | `["."]` se nessuna standard presente |
| `language` | `str` | `--language` | `"en"` |

**Euristica `source_dirs`** (D7, NFR-I-07): cartelle standard riconosciute, in ordine —
`src, lib, app, pkg, packages, docs, doc, tests, test, requirements, specs` — incluse se presenti
come sottocartelle dirette di `target_root`; nessuna → `["."]`. `--source-dirs` bypassa l'euristica.

**Validità.**
- `target_root` MUST esistere ed essere una directory scrivibile → altrimenti `ConfigError`/
  `IngestionError` prima di scrivere alcun artefatto (edge case spec; REQ-102/125).
- `language` è una stringa libera (non validata contro una lista): l'utente è responsabile del valore.
- Il `wiki.config.toml` generato da `HostProfile` MUST superare `load_profile` del core
  (`profile.py:151`) — invariante verificata da test (D7).

---

## 3. `InstallPlan` — sequenza ordinata di artefatti

Lista ordinata di `Artifact` che `sertor install wiki` esegue. L'ordine codifica la dipendenza
funzionale (FR-010: `structure init` **dopo** `wiki.config.toml`).

**Ordine canonico:**
1. Validazione pre-volo (`HostProfile`: target esiste/scrivibile) — **non** è un `Artifact`, è una
   guardia.
2. `FILE` × N — skill (`SKILL.md`, `wiki-playbook.md`, `*-craft.md`, `ops/*.md`), `commands/wiki.md`,
   `agents/wiki-curator.md`, `hooks/wiki-pending-check.ps1`.
3. `SETTINGS_MERGE` — `.claude/settings.json`.
4. `MARKER_BLOCK` — `CLAUDE.md`.
5. `CONFIG` — `wiki.config.toml` (generato da `HostProfile`).
6. `STRUCTURE` — `wiki/` via `init_structure(load_profile(<config generata>))`.

**Invariante (fail-fast, REQ-125 / DI-3).** L'esecuzione è sequenziale; al **primo** errore si ferma,
gli artefatti già applicati restano (no rollback), il report segnala lo stato parziale. Il re-run è
idempotente e completa i mancanti.

**Invariante (install ≠ run, FR-007/022).** Nessun `Artifact` né la guardia avviano LLM, embeddings,
rete o indicizzazione. `INIT_STRUCTURE` crea solo cartelle/file seed (è file-system, non
indicizzazione — R-I6 chiarito nei requisiti). `[rag] enabled = false` nel config generato (D7).

---

## 4. `ArtifactOutcome` — esito per artefatto

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `target_rel` | `str` | percorso relativo dell'artefatto |
| `outcome` | `Outcome` (enum) | `CREATED`, `SKIPPED`, `MERGED`, `BLOCK`, `ERROR` |
| `detail` | `str \| None` | dettaglio (es. «+3 voci hook», «già presente», causa dell'errore) |

**Mappa esiti → strategia:**

| `outcome` | Da quale strategia | Significato |
|-----------|--------------------|-------------|
| `CREATED` | tutte | artefatto scritto ex novo |
| `SKIPPED` | `CREATE_IF_ABSENT`, `GENERATE_CONFIG`, `APPEND_BLOCK`(marker presente), `INIT_STRUCTURE`(esistente) | già presente, non toccato |
| `MERGED` | `MERGE_DEDUP` | voci aggiunte (con conteggio nel `detail`); 0 aggiunte → comunque `MERGED` con detail «nessuna nuova voce» |
| `BLOCK` | `APPEND_BLOCK` | sezione step-ritual inserita nel `CLAUDE.md` |
| `ERROR` | qualunque | fallimento (permessi, JSON malformato): innesca il fail-fast |

`INIT_STRUCTURE` produce **più** `ArtifactOutcome` (uno aggregato per `wiki/` con i conteggi
`created`/`skipped_existing` dello `StructureResult` del core, `structure.py:64`).

---

## 5. `InstallReport` — esito complessivo (contratto di osservabilità)

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `target` | `str` | path assoluto del target |
| `outcomes` | `list[ArtifactOutcome]` | esiti in ordine di esecuzione |
| `created` / `skipped` / `merged` / `errors` | `int` | conteggi del riepilogo |
| `failed_step` | `str \| None` | artefatto al quale il fail-fast si è fermato (se errore) |

**Exit code derivato** (D8, REQ-143):
- `errors == 0` → **0** (anche se tutto skipped — idempotenza).
- errore di dominio in un passo → **1** (fail-fast, `failed_step` valorizzato).
- errore d'uso (argparse) → **2** (non costruisce nemmeno il report).

**Serializzazione.** Output umano di default; `--json` (Could) emette
`{target, outcomes:[{target_rel, outcome, detail}], summary:{created, skipped, merged, errors}}`.
Schema versionato come gli altri contratti del core (`wiki.*`), p.es. `install.report/1`.

---

## 6. Relazioni e confini

```
HostProfile ──(genera)──> wiki.config.toml (Artifact CONFIG)
     │
InstallPlan ──contiene──> [Artifact, …] ──(esegue)──> [ArtifactOutcome, …] ──aggrega──> InstallReport
     │                                                                                      │
     └── guardia pre-volo (target scrivibile)                                    exit code (0/1/2)

Confine verso sertor-core (Principio I, NFR-I-06):
  InstallPlan.STRUCTURE → sertor_core.wiki_tools.init_structure / load_profile  (riuso, no duplicazione)
  errori                → sertor_core.domain.errors.{SertorError, ConfigError, IngestionError}  (riuso)
```

L'installer **non** definisce nuove eccezioni se quelle del core bastano: `ConfigError` (config/JSON
malformato, target non valido), `IngestionError` (target non directory). Per lo stub
`install rag|governance` serve un esito «non implementato» con exit non-zero (D8): si usa una
`SertorError` dedicata con messaggio leggibile, mappata a exit 1 dal `main`.
