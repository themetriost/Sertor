# Phase 1 — Data Model: Rimozione stub `assets/copilot/` (E10-FEAT-023)

**Branch**: `081-stub-copilot` · **Spec**: [spec.md](./spec.md)

Feature **sottrattiva / igiene host-facing**: nessuna entità di dominio del core, nessun nuovo tipo,
nessuno schema. Le «entità» qui sono **artefatti di filesystem/test**: l'oggetto rimosso e la guardia
che ne previene la ricomparsa. Sezione minimale per design.

---

## Entità

### 1. Tree stub `assets/copilot/` — **RIMOSSO**

L'oggetto che la feature elimina.

| Campo | Valore |
|-------|--------|
| Path | `packages/sertor/src/sertor_installer/assets/copilot/` |
| Contenuto | 4 sottocartelle vuote `agents/`, `hooks/`, `instructions/`, `prompts/`, ciascuna con un solo `.gitkeep` |
| File | `agents/.gitkeep`, `hooks/.gitkeep`, `instructions/.gitkeep`, `prompts/.gitkeep` (4 file vuoti) |
| Origine storica | dir create in FEAT-044; i JSON hook in `hooks/` rimossi in FEAT-049 (sostituiti da generazione a runtime) → tree vuoto da allora |
| Consumatori a runtime/test | **zero** (verificato R-0); nessun `iter_asset_dir`/`read_asset_text`/`asset_path` rooted a `copilot/` |
| Letto a runtime | mai (i `.gitkeep` non sono input dell'installer) |
| Stato post-feature | **inesistente** (git non traccia dir vuote → rimosso l'ultimo file, la dir scompare); nessun file di rimpiazzo |

**Transizione di stato.** `presente (4 .gitkeep + 4 dir + copilot/)` → `git rm` dei 4 `.gitkeep` →
`assente (copilot/ non esiste nel tree del repo)`. Idempotente: ripetere `git rm` su file già rimossi è
no-op. Non-distruttivo verso l'ospite: sono file **del nostro package**, non file dell'utente.

### 2. Pipeline di generazione Copilot — **INVARIATA**

Resta l'unica fonte dei payload Copilot; non modificata dalla feature.

| Campo | Valore |
|-------|--------|
| Funzioni | `render_copilot_hooks` · `render_custom_agent` · `render_prompt_file` (`sertor_install_kit.surfaces`, riesportate in `sertor_installer.surfaces`) |
| Orchestratore | `build_rag_plan(AssistantId.COPILOT_CLI)` (`install_rag.py:126-244`) |
| Sorgenti | `assets/claude/**` e `assets/rag/**` (mai `assets/copilot/`) |
| Output host-facing | hook JSON (`.github/hooks/`), custom-agent (`.github/agents/*.agent.md`), prompt-file (`.github/prompts/*.prompt.md`), skill body (`.github/skills/<n>/SKILL.md`), blocco istruzione (`.github/copilot-instructions.md`) |
| Effetto della feature | **nessuno** — gli artefatti generati sono byte-identici prima e dopo (FR-004, CS-4) |

### 3. Guardie esistenti — **INVARIATE (restano verdi)**

| Test | Cosa verifica | Effetto della rimozione |
|------|---------------|-------------------------|
| `test_assets_copilot_guard.py` (incl. `test_no_hand_maintained_copilot_prompt_bodies`) | nessun body asset sotto `copilot/`; render path unico | verde (non asserisce l'esistenza dei `.gitkeep`) |
| `test_assets_copilot_parity.py` | nessun `.claude/`/slash/nome-Claude nei body resi; reference-closure | verde (legge i piani generati, non `assets/copilot/`) |
| `tests/integration/test_packaging.py` | wheel `uv build` corretto | verde (hatchling glob ricorsivo, nessun file esplicito) |

### 4. Guardia anti-ricomparsa — **NUOVA (additiva, leggera)**

| Campo | Valore |
|-------|--------|
| Collocazione | **estensione** di `packages/sertor/tests/test_assets_copilot_guard.py` (decisione R-1/DA-D-1) |
| Nome | `test_no_copilot_asset_directory` |
| Asserzione | `asset_path("copilot").is_dir() is False` (API esistente `sertor_installer.resources.asset_path`) |
| Stato corretto | **passa** quando `assets/copilot/` è assente |
| Failure mode | **fallisce** se un `.gitkeep` (o altro file) ricrea `assets/copilot/<x>/` (la dir torna a esistere) |
| Dipendenze | nessuna nuova (riuso `asset_path`); offline, deterministico |

---

## Invarianti

- **INV-1 (zero core).** Nessun simbolo di `sertor_core` toccato; nessuna porta/adapter/engine/comando.
- **INV-2 (generazione invariata).** `build_rag_plan(copilot-cli)` produce lo stesso insieme di
  artefatti prima e dopo (CS-4).
- **INV-3 (assenza è lo stato corretto).** Nessun file di rimpiazzo sotto `assets/copilot/`; la dir
  resta inesistente (FR-003, US2).
- **INV-4 (fail-loud sulla ricomparsa).** La guardia nuova rende rosso il ritorno dello stub (Principio
  XII), non lascia che l'ambiguità rientri in silenzio.
