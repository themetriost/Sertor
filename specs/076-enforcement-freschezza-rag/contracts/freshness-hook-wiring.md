# Contratto — wiring dell'hook di freschezza (per-assistente)

**Branch**: `076-enforcement-freschezza-rag`

Le voci di wiring che l'installer deposita per l'hook di freschezza, nel formato **nativo** di
ciascun assistente (FR-020/021, DA-D-r2). Fonte unica logica: `HookEntrySpec` del kit
(`render_copilot_hooks`), gemella delle voci memory-capture/rag-usage.

## 1. Claude — `.claude/settings.json` (formato annidato)

### SessionEnd (re-index + doctor + persist)
```json
{ "hooks": { "SessionEnd": [ { "hooks": [ {
  "type": "command", "shell": "powershell", "timeout": 15,
  "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/rag-freshness.ps1')"
} ] } ] } }
```
### SessionStart (ripesca + induce)
```json
{ "hooks": { "SessionStart": [ { "hooks": [ {
  "type": "command", "shell": "powershell", "timeout": 10,
  "statusMessage": "Verifico la freschezza del RAG",
  "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/rag-freshness-start.ps1') -Assistant claude"
} ] } ] } }
```

> Le due voci sono **merge-dedup** accanto alle voci esistenti (wiki SessionStart, memory SessionEnd):
> `merge_settings` preserva le altre (FR-016/018).

## 2. Copilot CLI — `.github/hooks/sertor-hooks.json` (formato piatto, generato)

### SessionEnd (command)
`render_copilot_hooks([HookEntrySpec("SessionEnd","command","pwsh -File .github/hooks/rag-freshness.ps1",15)])`
→
```json
{ "version": 1, "hooks": { "SessionEnd": [
  { "type": "command", "command": "pwsh -File .github/hooks/rag-freshness.ps1", "timeoutSec": 15 }
] } }
```
### SessionStart (prompt statico — NO script su Copilot CLI)
`render_copilot_hooks([HookEntrySpec("SessionStart","prompt","<direttiva d'induzione statica>",10)])`
→
```json
{ "version": 1, "hooks": { "SessionStart": [
  { "type": "prompt",
    "prompt": "All'avvio: leggi .sertor/.rag-health.json. Se verdict=degraded, rendi evidente il degrado (reason) e induci la correzione — esegui `sertor-rag index .` e/o riconnetti il server MCP — PRIMA di procedere col lavoro. Se healthy/assente, procedi.",
    "timeoutSec": 10 }
] } }
```

## Regole (MUST)
- **W1 (parità, FR-021)**: Copilot riceve **solo** il formato piatto `version:1`/`timeoutSec`/entry
  piatte; mai il formato Claude (annidato, `shell`/`statusMessage`/`timeout`). Generato, non asset
  statico in formato Claude (lezione FEAT-011/049).
- **W2 (non-bloccante)**: il `SessionEnd` exit 0 sempre (FR-017); il `SessionStart` Claude no-op se
  sano (FR-013/NFR-6).
- **W3 (isolamento, FR-016/018)**: voci e script distinti da memory-capture/wiki; il merge-dedup non
  tocca le altre voci.
- **W4 (D↔N, FR-014)**: il `SessionStart` (script Claude o prompt Copilot) **induce**, non esegue la
  correzione; il vehicle è eseguito dall'agente.
- **W5 (Copilot SessionStart = prompt)**: nessuno script `rag-freshness-start.ps1` depositato su
  Copilot (il SessionStart è un prompt statico; A-005).
