# Contratto — Output degli script hook per evento (per assistente)

**Soggetto**: l'output su stdout/stderr e l'exit code degli script `.ps1` invocati dagli hook, per ogni
evento e per ogni assistente. Selezione via parametro `-Assistant` (data-model §3).
**Verificato da**: FR-024 / SC-002 / SC-008 (test offline: invoca lo script, parsa stdout).
**Principio guida**: output NATIVO per assistente, **mai dual-field** (FR-011).

---

## 1. Tabella del contratto per evento

| Evento (logico) | Assistente | stdout | stderr | exit | Note |
|---|---|---|---|---|---|
| SessionStart | `claude` | direttiva (usata come contesto) | — | 0 | comportamento storico (non-regressione) |
| SessionStart | `copilot` (VS Code) | `{"additionalContext":"<direttiva>"}` | — | 0 | [ASSUNTO-VSC]; JSON valido, mai stringa nuda (FR-006/SC-003) |
| SessionStart | `copilot-cli` | — (usa `type:"prompt"`, nessuno script) | — | — | direttiva = prompt statico nel wiring |
| Stop / agentStop | `claude` | `{"systemMessage":"<msg>"}` | — | 0 | invariato (FR-040) |
| Stop / agentStop | `copilot` | `{"decision":"allow","reason":"<msg>"}` | — | 0 | non-bloccante (FR-007/Q3=b); MAI `decision:"block"` per un reminder |
| SessionEnd / sessionEnd | `claude` | `{"systemMessage":"<msg>"}` | — | 0 | invariato |
| SessionEnd / sessionEnd | `copilot` | — (nessun output consumato) | `<msg>` opz. | 0 | Copilot non consuma output qui (FR-009) |
| PreToolUse / preToolUse | `claude` | nessuno (o conforme) | warning opz. | 0 | fail-open (già oggi) |
| PreToolUse / preToolUse | `copilot` | nessuno spurio | warning opz. | 0 | fail-CLOSED su Copilot → exit 0 SEMPRE, anche su errore parsing (FR-008/041, NFR-3); nessun `decision:"deny"` |

---

## 2. Invarianti MUST (asserzioni)

- **O1** (FR-011/SC-008): per QUALSIASI evento+assistente, l'output JSON **non** contiene
  contemporaneamente un campo Claude-only (`systemMessage`) **e** un campo Copilot
  (`additionalContext`/`decision`/`reason`). No dual-field.
- **O2** (FR-008/041): lo script `preToolUse` per `copilot` esce **0** anche con stdin malformato / errore
  interno; NON emette alcun campo che Copilot interpreti come `decision:"deny"` (fail-open esplicito su un
  evento fail-closed).
- **O3** (FR-007): l'output `agentStop` per `copilot` ha `decision == "allow"` (mai `"block"` per il
  reminder wiki non-bloccante).
- **O4** (FR-006/SC-003): l'output `sessionStart` per `copilot` (VS Code) è **JSON parsabile** con
  `additionalContext`; zero stringhe nude non-JSON.
- **O5** (FR-009): l'output `sessionEnd` per `copilot` non scrive su stdout un payload che Copilot
  consumerebbe; eventuali messaggi vanno su stderr.
- **O6** (FR-040/SC-010): con `-Assistant claude` (default), ogni script produce **esattamente** l'output
  storico (test di non-regressione).

---

## 3. Parametro d'invocazione `-Assistant` (Q4=b / FR-011)

```
-Assistant <claude|copilot>   # default: claude (non-regressione)
```
- Selezionato dal **wiring per-assistente** (il comando nella voce hook passa `-Assistant copilot` sui
  target Copilot).
- Il **corpo logico** dello script (delega alla CLI deterministica, calcolo dello stato) è condiviso e
  invariante rispetto al parametro; cambia SOLO la funzione di resa dell'output finale.
- FR-012: se per un evento la resa nativa non è esprimibile in modo pulito da un singolo script
  parametrico, si ammette una **variante per-assistente** (file distinto), MAI un output non-nativo o
  dual-field. In questa feature il parametro è sufficiente.
