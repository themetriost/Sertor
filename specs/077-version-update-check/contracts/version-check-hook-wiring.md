# Contratto — wiring dell'hook di version-check (per-assistente)

**Branch**: `feat013-version-check-backlog`

Le voci di wiring che l'installer deposita per il version-check, nel formato **nativo** di ciascun
assistente (FR-016, parità RNF-3). Fonte unica logica: `HookEntrySpec` del kit
(`render_copilot_hooks`), gemella delle voci freschezza/memory-capture/rag-usage.

## 1. Claude — `.claude/settings.json` (formato annidato)

### SessionEnd (GET cachata + confronto + persist)
```json
{ "hooks": { "SessionEnd": [ { "hooks": [ {
  "type": "command", "shell": "powershell", "timeout": 15,
  "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/version-check.ps1')"
} ] } ] } }
```
### SessionStart (legge lo stato + avvisa se behind)
```json
{ "hooks": { "SessionStart": [ { "hooks": [ {
  "type": "command", "shell": "powershell", "timeout": 10,
  "statusMessage": "Verifico la disponibilità di aggiornamenti Sertor",
  "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/version-check-start.ps1') -Assistant claude"
} ] } ] } }
```

> Le due voci sono **merge-dedup** accanto alle voci esistenti (wiki SessionStart, memory SessionEnd,
> freschezza SessionEnd/SessionStart): `merge_settings` preserva le altre (FR-016).

## 2. Copilot CLI — `.github/hooks/sertor-hooks.json` (formato piatto, generato)

### SessionEnd (command)
`render_copilot_hooks([HookEntrySpec("SessionEnd","command","pwsh -File .github/hooks/version-check.ps1",15)])`
→
```json
{ "version": 1, "hooks": { "SessionEnd": [
  { "type": "command", "command": "pwsh -File .github/hooks/version-check.ps1", "timeoutSec": 15 }
] } }
```
### SessionStart (prompt statico — NO script su Copilot CLI)
`render_copilot_hooks([HookEntrySpec("SessionStart","prompt","<direttiva d'avviso statica>",10)])`
→
```json
{ "version": 1, "hooks": { "SessionStart": [
  { "type": "prompt",
    "prompt": "All'avvio: leggi .sertor/.version-check.json. Se verdict=behind, mostra l'avviso (versione installata, ultima versione, comando d'aggiornamento `sertor upgrade` / `uvx --refresh …`); se sono presenti dimensions, nomina quali dimensioni sono indietro. Non applicare alcun aggiornamento da te. Se up-to-date/ahead/unknown/assente, procedi senza avviso.",
    "timeoutSec": 10 }
] } }
```

## Regole (MUST)
- **W1 (parità, FR-016)**: Copilot riceve **solo** il formato piatto `version:1`/`timeoutSec`/entry
  piatte; mai il formato Claude (annidato, `shell`/`statusMessage`/`timeout`). Generato, non asset
  statico in formato Claude (lezione FEAT-011/049).
- **W2 (non-bloccante)**: il `SessionEnd` exit 0 sempre (FR-009); il `SessionStart` Claude no-op se
  non-`behind` (INV-1/NFR-6); offline → nessun avviso, nessun errore (FR-009).
- **W3 (isolamento, FR-016)**: voci e script distinti da rag-freshness/memory-capture/wiki; il
  merge-dedup non tocca le altre voci. I due hook (freschezza + version-check) coesistono al
  SessionEnd/SessionStart, entrambi non-fatali.
- **W4 (D↔N, FR-014)**: il `SessionStart` (script Claude o prompt Copilot) **avvisa**, non applica la
  correzione; l'aggiornamento lo decide ed esegue l'utente (FR-005/CS-4). Nessun LLM nello script.
- **W5 (Copilot SessionStart = prompt)**: nessuno script `version-check-start.ps1` depositato su
  Copilot (il SessionStart è un prompt statico; A-005).
- **W6 (privacy/rete)**: l'unica rete è la GET del `/VERSION` pubblico al SessionEnd (FR-015); il
  SessionStart è **zero rete** (RNF-1).
