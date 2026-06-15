# Implementation Plan: Enforcement lato ospite del consumo via vehicles (Gruppi B+C)

**Branch**: `042-enforcement-vehicles-ospite` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: spec 042 · `requirements/sertor-core/enforcement-principio-xi/requirements.md` (B+C).

## Summary

Estendere `sertor install rag` con due artefatti host-facing che realizzano il Principio XI lato
ospite: **(B)** un blocco `CLAUDE.md` a marker `SERTOR:RAG-USAGE` che istruisce l'agente a usare
`sertor-rag`/MCP e a non importare `sertor_core`; **(C)** un hook host-specifico (Claude Code) che
**rileva e avvisa** (default `warn`, fail-open) l'uso diretto della libreria fuori da vehicles/test.
Additivo, non distruttivo, idempotente; riusa il motore di installazione (toolkit
`sertor-install-kit`) e i suoi primitivi (`write_marker_block`, merge settings, copia file).

## Technical Context

**Language/Version**: Python ≥ 3.11; hook = PowerShell (host Claude Code). **Dependencies**: nessuna
nuova (riusa kit + assets package-data). **Project Type**: installer (`packages/sertor`).
**Constraints**: install≠run, non-distruttivo/idempotente, host-agnostico (l'hook è un adattatore del
trigger, la sua assenza non rompe nulla), default-warn/fail-open.

## Design

- **D1 (B) — Blocco CLAUDE.md.** Aggiungere a `build_rag_plan` un `Artifact(MARKER_BLOCK,
  "rag/claude-md-block-rag-usage.md", "CLAUDE.md", APPEND_BLOCK)`. In `execute_rag_plan` un ramo che
  chiama `kit.write_marker_block(path, content, MARKER_START_RAG, MARKER_END_RAG)` con marker
  `<!-- SERTOR:RAG-USAGE START/END -->` (distinti da wiki/SDLC). Nuovo asset
  `assets/rag/claude-md-block-rag-usage.md` (EN): "per il RAG usa `sertor-rag` (CLI) o i tool MCP; non
  importare `sertor_core` nei tuoi script".
- **D2 (C) — Hook.** Aggiungere a `build_rag_plan` due artefatti:
  - `Artifact(FILE, "rag/hooks/sertor-rag-usage-check.ps1", ".claude/hooks/sertor-rag-usage-check.ps1",
    CREATE_IF_ABSENT)` — lo script dell'hook.
  - `Artifact(SETTINGS_MERGE, "rag/settings.rag-usage.json", ".claude/settings.json", MERGE_DEDUP)` —
    la voce hook (PreToolUse) in `.claude/settings.json`, merge additivo dedup (preserva gli hook
    dell'utente).
  In `execute_rag_plan` rami che riusano `kit` (copia file + `merge_settings`).
- **D3 (meccanismo hook).** **PreToolUse** (matcher Bash): lo script PowerShell legge il payload JSON da
  stdin, estrae il comando, e se contiene `import sertor_core`/`from sertor_core` **e** il percorso NON
  è di test (esclude `test`/`tests`), emette un **warning non bloccante** su stderr. Default severità
  `warn` → **exit 0 sempre** (non blocca). Parse error/contesto ignoto → **fail-open** (exit 0, nessun
  segnale). `block` (Could) fuori MVP. Pattern di robustezza preso da `wiki-pending-check.ps1`.
- **D4 (dispatch).** `execute_rag_plan` esteso a gestire `MARKER_BLOCK`/`FILE`/`SETTINGS_MERGE` (oggi
  gestisce DEPENDENCIES/ENV_MERGE/MCP_MERGE/MCP_REGISTER/GITIGNORE_APPEND) riusando i primitivi del kit;
  nessun nuovo `ArtifactKind`.

> Nota: `sertor install rag` finora non toccava `.claude/` (solo `.sertor/` + root). B/C aggiungono
> artefatti `.claude/` — additivi e non distruttivi (skip/merge a marker). Coerente con `install wiki`,
> che già scrive `.claude/`.

## Constitution Check (v1.2.0)

- [x] **I/II/III/IV/VII/VIII**: invariati; thin layer sul kit, nessuna logica duplicata. **PASS.**
- [x] **V**: test installer (plan composition, idempotenza, blocco distinto, hook warn/test-exclusion).
  **PASS.**
- [x] **VI — Idempotenza/non-distruttività**: CREATE_IF_ABSENT, blocco a marker, merge dedup; install≠run.
  **PASS.**
- [x] **IX**: invariato. **PASS.**
- [x] **X — Host-agnostico**: l'hook è host/assistente-specifico (adattatore del trigger), la sua
  assenza non rompe la capacità; asset in inglese; nessuna assunzione sul dominio ospite. **PASS.**
- [x] **XI — Consumo via vehicles**: lo **realizza lato ospite** (istruzione + rilevazione). **PASS.**

**Esito:** PASS 11/11, nessuna deroga.

## Project Structure

```text
packages/sertor/src/sertor_installer/
├── install_rag.py            # build_rag_plan += MARKER_BLOCK + FILE(hook) + SETTINGS_MERGE; execute_rag_plan dispatch
└── assets/rag/
    ├── claude-md-block-rag-usage.md          # NUOVO (EN, blocco SERTOR:RAG-USAGE)
    ├── settings.rag-usage.json               # NUOVO (voce hook PreToolUse)
    └── hooks/sertor-rag-usage-check.ps1       # NUOVO (hook warn, fail-open, esclude test)
packages/sertor/tests/
└── test_install_rag*.py      # + test blocco/hook/idempotenza/dispatch
```

**Structure Decision**: nessun nuovo modulo Python; estensione di `install_rag` + 3 asset + test.

## Complexity Tracking
> Nessuna violazione. Tabella vuota.
