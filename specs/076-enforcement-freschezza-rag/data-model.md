# Data Model — enforcement deterministico della freschezza RAG (hook) (E10-FEAT-011)

**Branch**: `076-enforcement-freschezza-rag` · **Fase**: Phase 1 (design)

> La feature è additiva e host-facing: **nessuna entità di dominio `sertor_core`** (Principio XI). Le
> «entità» qui sono **artefatti host-facing** (script hook, file di stato, voci di wiring) e i
> **modelli logici dell'installer** già esistenti (`Artifact`/`HookEntrySpec`/`SertorOwnedPaths`),
> riusati. Nessun nuovo `ArtifactKind`/`Surface`/`WriteStrategy`.

---

## 1. File di stato di salute RAG — `.sertor/.rag-health.json` (NUOVA entità host-facing)

L'esito di salute scritto a fine sessione, che attraversa il confine di sessione (DA-D-r1, research D-1).

| Campo | Tipo | Obblig. | Significato |
|---|---|---|---|
| `schema` | string | sì | versione del contratto: `"rag.health/1"` |
| `verdict` | enum `healthy`\|`degraded` | sì (FR-011) | verdetto derivato da `doctor` + staleness |
| `timestamp` | string ISO-8601 UTC | sì (FR-011) | quando lo stato è stato scritto |
| `reason` | string | sì se `degraded` (FR-011) | causa/area che ha fallito (testo `doctor`, scrubbed) |
| `areas` | object `{config,provider,index,mcp: pass\|warn\|fail}` | additivo | esito per-area da `doctor --json` |
| `exit_code` | int | additivo | exit code di `doctor` (gate) |

**Invarianti**
- **INV-1 (idempotenza, NFR-6)**: a verdetto `healthy` il file è **riscritto** con
  `verdict:"healthy"` (non cancellato) → il segnale d'avvio lo legge e fa no-op; lo stato non oscilla.
- **INV-2 (privacy, NFR-3)**: nessun segreto; `reason` proviene da `doctor` (già scrubbed dai
  vehicle). L'hook non compone testo nuovo a partire da `.env`.
- **INV-3 (gitignored, NFR-3)**: il file è coperto da `RUNTIME_IGNORES` (kit) → mai versionato.
- **INV-4 (sopravvivenza)**: vive in `.sertor/` (NON dentro `.index*/`), così sopravvive anche a un
  `index --full` che resetta la collezione.

**Transizioni di stato** (gate dell'induzione, FR-010/013/015):

```
                 doctor degraded            session start, file=degraded
  (assente) ────────────────────────▶ degraded ──────────────────────▶ induce correzione
      │                                   │                                   │
      │ doctor healthy                    │ agente esegue index/reconnect     │
      ▼                                   ▼  → next SessionEnd doctor healthy  ▼
   healthy ◀──────────────────────────────────────────────────────────── healthy (marker pulito)
                                 (no inducement: no-op all'avvio, INV-1)
```

---

## 2. Hook di freschezza RAG (NUOVI artefatti script host-facing)

Due script PowerShell host-agnostici (stdlib PowerShell, exit 0 sempre), bundled in
`packages/sertor/.../assets/rag/hooks/`.

### 2a. `rag-freshness.ps1` — `SessionEnd` (re-index + doctor + persistenza)
- **Disciplina**: gemella di `memory-capture.ps1` (research D-0a) — `try/catch` globale, exit 0
  sempre (FR-017), payload JSON tollerante da stdin, root da `$env:CLAUDE_PROJECT_DIR`→`cwd`→`'.'`.
- **Logica (orchestrazione, NON change-detection — FR-002)**:
  1. `uv run sertor-rag index .` (incondizionato; skip-quando-nulla-cambia delegato al core, FR-002/003).
  2. `uv run sertor-rag doctor --json` → parse del verdetto (pass/warn/fail per-area + exit code, FR-005/006).
  3. deriva `verdict` (`degraded` se exit≠0 o area in fail/warn o indice stantio; altrimenti `healthy`).
  4. scrive `.sertor/.rag-health.json` (degraded → con `reason`/messaggio prominente FR-008/009;
     healthy → INV-1, clear FR-010).
- **Confine D↔N**: re-index e doctor sono i **vehicle** (deterministici); nessun LLM (NFR-5).

### 2b. `rag-freshness-start.ps1` — `SessionStart` Claude (ripesca + induce)
- **Logica**: legge `.sertor/.rag-health.json`; se `verdict=degraded` emette su stdout la direttiva
  d'induzione (contesto SessionStart per Claude: «stato RAG degradato per <reason> → esegui
  `sertor-rag index .` e/o riconnetti l'MCP prima di procedere»); se `healthy`/assente → no-op
  (FR-012/013/014, NFR-6).
- **Confine D↔N (FR-014)**: NON esegue la correzione; **induce** soltanto. L'agente esegue.
- **Copilot CLI**: non c'è script al SessionStart — la direttiva è un **prompt nativo statico**
  (research D-2), generato da `HookEntrySpec("SessionStart","prompt",…)`.

---

## 3. Voci di wiring per-assistente (modelli logici riusati, §2 research D-0c)

| Voce | Evento | Claude (nativo) | Copilot CLI (nativo) |
|---|---|---|---|
| re-index/doctor/persist | `SessionEnd` | asset JSON statico `rag/settings.rag-freshness.json` (forma annidata `{matcher,hooks:[]}`) | generato `render_copilot_hooks([HookEntrySpec("SessionEnd","command",…,15)])` (piatto, `version:1`, `timeoutSec`) |
| ripesca/induce | `SessionStart` | asset JSON statico (script `rag-freshness-start.ps1`) | generato `HookEntrySpec("SessionStart","prompt","<direttiva>",10)` |

Sentinella sorgente per il ramo Copilot generato (gemella di `_COPILOT_MEMORY_WIRING_SENTINEL`):
`_COPILOT_FRESHNESS_END_WIRING_SENTINEL`, `_COPILOT_FRESHNESS_START_WIRING_SENTINEL`. Il dispatch in
`_rag_hook_fragment` (`install_rag.py:424`) si estende ai due nuovi sentinel (art-aware, riuso).

---

## 4. Artefatti dell'installer (`Artifact`, riuso — nessun nuovo `ArtifactKind`)

Aggiunte al `build_rag_plan` (research D-6), in coda al plan esistente (ordine canonico preservato):

| # | `ArtifactKind` | source | target (Claude) | target (Copilot) | WriteStrategy |
|---|---|---|---|---|---|
| a | `FILE` | `rag/hooks/rag-freshness.ps1` | `.claude/hooks/rag-freshness.ps1` | `.github/hooks/rag-freshness.ps1` | `CREATE_IF_ABSENT` |
| b | `FILE` | `rag/hooks/rag-freshness-start.ps1` | `.claude/hooks/rag-freshness-start.ps1` | *(nessuno — prompt statico)* | `CREATE_IF_ABSENT` |
| c | `SETTINGS_MERGE` | `rag/settings.rag-freshness.json` o sentinel | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` | `MERGE_DEDUP` |
| d | `SETTINGS_MERGE` | start-asset o start-sentinel | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` | `MERGE_DEDUP` |

> Su Copilot l'artefatto (b) **non** è depositato (il SessionStart è un prompt statico, nessuno
> script da eseguire): il plan-builder lo emette solo per Claude (ramo `is_copilot`).

## 5. Modelli del lifecycle (riuso — `SertorOwnedPaths`)

Estensione di `sertor_owned_paths` (`install_rag.py:510`):
- **`owned_files`** += `rag-freshness.ps1` (+ `rag-freshness-start.ps1` solo Claude) — rimossi su
  uninstall, aggiornati su upgrade (FR-023).
- **`shared_edits`**: la voce `SessionEnd`/`SessionStart` rag-freshness atterra nello **stesso**
  settings file della voce rag-usage/memory (`.claude/settings.json` o `sertor-hooks.json`) → già
  coperto dallo `SharedEdit(settings_target, SETTINGS, …)` esistente. Su Copilot il file
  `sertor-hooks.json` ha `delete_if_empty=True` (riuso `install_rag.py:590`): svuotato → ripulito
  (FR-023, «file hook dedicato rimasto vuoto è ripulito»).
- Coverage test `plan ⊆ owned` (già esistente): i nuovi `target_rel` devono comparire negli owned.

## 6. Cosa NON cambia
- `sertor_core` (porte/adapter/servizi/composition/CLI) — INVARIATO.
- `ArtifactKind`/`Surface`/`WriteStrategy`/`HookEntrySpec`/`render_copilot_hooks` — INVARIATI (riuso).
- Schema `install.report/1` — INVARIATO (nuovi artefatti, stesso report).
- Comportamento a indice fresco — INVARIATO (FR-003/NFR-1).
