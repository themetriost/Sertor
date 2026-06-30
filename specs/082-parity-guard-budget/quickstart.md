# Quickstart — E10-FEAT-024 (verifica delle guardie)

Tutto **offline**. Dalla root del workspace.

## 1. Le tre nuove guardie passano allo stato corrente
```powershell
uv run pytest packages/sertor/tests/test_copilot_hook_presence.py `
              packages/sertor/tests/test_hooks_rag_no_stdout_payload.py `
              tests/unit/test_claude_md_block_budget.py -q
```
Atteso: **verde** (wiki 52 ≤ 60, RAG 49 ≤ 58, SDLC 64 ≤ 70; i 3 eventi Copilot presenti; nessun
payload `decision` su stdout nei 3 script rag SessionEnd).

## 2. CS-1 — rimuovere un frammento Copilot rende rosso (manuale)
Simula la rimozione del frammento PreToolUse: in `install_rag.py` togli temporaneamente l'artifact che
usa `_COPILOT_RAG_WIRING_SENTINEL` (il solo `PreToolUse`). La shape-guard di presenza fallisce nominando
`PreToolUse`. *(L'anti-pattern del test lo verifica automaticamente senza toccare il sorgente.)*

## 3. CS-2 — un blocco sopra-soglia rende rosso (manuale)
Aggiungi ~10 righe a `assets/claude-md-block.md` (52 → ~62 > 60). Atteso: `test_blocks_within_budget`
fallisce con `sertor_installer:claude-md-block.md`, conteggio corrente, soglia 60. Ripristina dopo.

## 4. CS-2 — un 4° blocco non registrato rende rosso (manuale)
Crea `assets/claude-md-block-foo.md`. Atteso: `test_budget_coverage_exhaustive` fallisce nominando il
file non registrato. Rimuovi dopo.

## 5. CS-3 — il difetto storico FEAT-049 resta coperto
```powershell
uv run pytest packages/sertor/tests/test_schema_copilot_hooks.py -q
```
Invariato e verde; la presenza-guard (passo 1) è indipendente.

## 6. CS-4/CS-5 — non-regressione + offline su tutto il workspace
```powershell
uv run pytest -q          # zero nuovi fallimenti
uv run ruff check .       # lint pulito
```
I nuovi test girano anche **senza `pwsh`** (nessun `pytestmark` di skip): verifica su una shell senza
PowerShell che restano eseguiti e verdi.
