# Contratto — Schema hook JSON Copilot (file wiring)

**Artefatto**: `.github/hooks/sertor-hooks.json` (target `copilot` e `copilot-cli`).
**Generato da**: `render_copilot_hooks(events)` nel `sertor-install-kit` (research §2d; data-model §2).
**Verificato da**: FR-021 / SC-001 / SC-007 (test offline, stdlib `json`).
**Fonte ground-truth**: audit `wiki/log/2026-06-17.md` (voce «Audit compatibilità Copilot», 🔴).

---

## 1. Schema atteso (Copilot CLI 1.0.63)

```json
{
  "version": 1,
  "hooks": {
    "<evento>": [
      {
        "type": "command",
        "command": "<stringa>",
        "timeoutSec": 10,
        "matcher": "<opzionale, solo PreToolUse>"
      }
    ]
  }
}
```

### Regole MUST (asserzioni di test)
- **R1** (FR-001): chiave di primo livello `"version": 1` PRESENTE.
- **R2** (FR-002): `"hooks"` è un oggetto; sotto ogni chiave-evento c'è una **lista piatta** di voci
  (NESSUN livello `hooks[]` annidato dentro la voce).
- **R3** (FR-002/003): ogni voce contiene SOLO campi dello schema Copilot: `type`, `command`, `timeoutSec`,
  e opzionalmente `matcher`. **Vietati**: `shell`, `statusMessage`, `timeout` (nome Claude).
- **R4** (FR-004): il timeout usa il nome `timeoutSec` (in secondi), MAI `timeout`.
- **R5** (FR-005): le chiavi-evento accettano PascalCase **e** gli alias documentati (vedi §2); il file
  generato usa una forma e i test accettano l'alias-set come equivalente.
- **R6** (FR-006): la voce `SessionStart` su `copilot-cli` può avere `"type": "prompt"` con `command`/
  `prompt` come direttiva (forma nativa CLI); su `copilot` (VS Code) `"type": "command"`.

### Esempio conforme (wiki, target `copilot` VS Code)
```json
{
  "version": 1,
  "hooks": {
    "SessionStart": [
      { "type": "command", "command": "pwsh -File .github/hooks/wiki-session-start.ps1 -Assistant copilot", "timeoutSec": 15 }
    ],
    "Stop": [
      { "type": "command", "command": "pwsh -File .github/hooks/wiki-pending-check.ps1 -Mode Stop -Assistant copilot", "timeoutSec": 10 }
    ],
    "SessionEnd": [
      { "type": "command", "command": "pwsh -File .github/hooks/wiki-pending-check.ps1 -Mode SessionEnd -Assistant copilot", "timeoutSec": 10 }
    ]
  }
}
```

### Esempio conforme (rag-usage, PreToolUse)
```json
{
  "version": 1,
  "hooks": {
    "PreToolUse": [
      { "type": "command", "command": "pwsh -File .github/hooks/sertor-rag-usage-check.ps1 -Assistant copilot", "timeoutSec": 10, "matcher": "Bash|Write|Edit|MultiEdit" }
    ]
  }
}
```

> Il **comando esatto** (interprete `pwsh`/`powershell`, costruzione del path) è dettaglio
> d'implementazione di `/speckit-tasks`; il contratto vincola **forma e nomi di campo**, non il comando.

---

## 2. Alias eventi (FR-005, A-3)

| Logico (Claude) | Alias Copilot |
|---|---|
| `SessionStart` | `sessionStart` |
| `Stop` | `agentStop` |
| `SessionEnd` | `sessionEnd` |
| `PreToolUse` | `preToolUse` |

I test devono trattare le coppie come equivalenti (case-insensitive sul primo carattere) quando asseriscono
la presenza di un evento.

---

## 3. Anti-pattern (un test DEVE fallire se ricompaiono) — SC-007

- file senza `"version"` → R1 fail.
- voce con `"hooks": [...]` annidato → R2 fail.
- voce con `"shell"` o `"statusMessage"` → R3 fail.
- timeout chiamato `"timeout"` → R4 fail.
