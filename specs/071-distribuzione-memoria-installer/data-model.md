# Data Model — Distribuzione della memoria via installer (FEAT-009)

Nessuna nuova entità di dominio (`sertor-core` invariato). Le «entità» qui sono **artefatti
d'installazione** del kit, riusati.

## Artefatti del piano rag (aggiunte)
| Artefatto | `kind` | source | target (Claude) | target (Copilot CLI) | strategy |
|---|---|---|---|---|---|
| Script cattura | `FILE` | `rag/hooks/memory-capture.ps1` | `.claude/hooks/memory-capture.ps1` | `.github/hooks/memory-capture.ps1` | `CREATE_IF_ABSENT` |
| Wiring `SessionEnd` | `SETTINGS_MERGE` | `rag/settings.memory-capture.json` (Claude) · `(generated)` sentinel (Copilot) | `.claude/settings.json` | `.github/hooks/sertor-hooks.json` | `MERGE_DEDUP` |
| Manopole memoria | (parte di `ENV_MERGE` esistente) | `rag/env.{local,azure}.tmpl` | `.sertor/.env` | idem | `MERGE_ENV` |
| Cenno comandi | (parte di `MARKER_BLOCK` esistente) | `rag/claude-md-block-rag-usage.md` | `CLAUDE.md` | `.github/copilot-instructions.md` | `APPEND_BLOCK` |

## Modello logico hook (riuso `HookEntrySpec`)
- Claude: frammento JSON annidato in `rag/settings.memory-capture.json` (gemello di `settings.hooks.json`).
- Copilot: `HookEntrySpec("SessionEnd", "command", "pwsh -File .github/hooks/memory-capture.ps1", 15)` →
  `render_copilot_hooks` → `{"version":1,"hooks":{"SessionEnd":[{type,command,timeoutSec}]}}`.

## Ownership (lifecycle)
- `owned_files` += memory hook target (per-assistente).
- `shared_edits`: il target settings (`.claude/settings.json` / `.github/hooks/sertor-hooks.json`) è già
  dichiarato dall'hook rag-usage → coverage `plan ⊆ owned` soddisfatta senza nuovo shared_edit.
- Uninstall: inverso di ogni artefatto del piano (rimuove hook + voce `SessionEnd`); `delete_if_empty`
  su `sertor-hooks.json` (Copilot) invariato; `.claude/settings.json` (Claude condiviso) preservato.

## Invarianti
- `SERTOR_MEMORY` off nei template (privacy-by-default).
- Nessun segreto/contenuto negli asset (solo nomi-chiave + commenti).
- `memory.sqlite` sotto `.sertor/` → già nei `RUNTIME_IGNORES` (nessuna nuova voce `.gitignore`).
