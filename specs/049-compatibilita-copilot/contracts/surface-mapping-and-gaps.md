# Contratto — Surface-mapping, claim di parità e dichiarazione dei gap

**Soggetto**: la documentazione di mappatura delle superfici e l'output d'installazione, come **unica sede
veritiera** dei claim di parità Claude↔Copilot e delle dichiarazioni di gap.
**Verificato da**: FR-027/028 / SC-009; Story 8 (P2).

---

## 1. Regola dei claim (FR-027)

Una superficie può essere dichiarata **"parità funzionale piena"** SOLO se:
1. è stata **validata contro lo schema Copilot** (test di schema verde, gruppo G); **e**
2. è stata **confermata empiricamente** su un client Copilot reale.

Se manca anche solo (2), la superficie NON è "parità piena": è dichiarata **"validata-schema,
non-confermata-runtime"** (o equivalente). Mai "piena" su un assunto.

---

## 2. Stato per-superficie (da mantenere vero — SC-009)

| Superficie | Schema validato (offline) | Confermato runtime | Claim ammesso |
|---|---|---|---|
| Hook wiring (`version:1`, piatto) | sì (FR-021) | CLI 1.0.63 sì (audit) / VS Code ⏳ | parità su CLI; «non-confermato» su VS Code finché non testato |
| Output `agentStop`/`sessionEnd`/`preToolUse` | sì (FR-024) | CLI ⏳ / VS Code ⏳ | «validato-schema, non-confermato-runtime» |
| SessionStart CLI (`type:"prompt"`) | sì | CLI ⏳ | «validato-schema» |
| **SessionStart VS Code (`additionalContext`)** | sì | **NO — [ASSUNTO-VSC]** | **GAP dichiarato** (non «equivalente») finché non confermato |
| Prompt-file `agent:` | sì (FR-022) | VS Code ⏳ | «validato-schema» |
| Custom-agent (no `model:`) | sì (FR-023) | CLI/VS Code ⏳ | «validato-schema» |
| COMMAND custom-agent su CLI | sì (FR-025) | CLI ⏳ | «validato-schema» |
| MCP CLI `.mcp.json`/`mcpServers` | n/a | CLI 1.0.63 sì (PR #66) / doc indica `~/.copilot/mcp-config.json` ⚠️ | evidenza documentata (FR-020); correggere solo se smentita |

`⏳` = verifica runtime = **validazione operativa fuori ambito di prodotto** (Assumptions); la suite di
prodotto è strutturale/offline (NFR-5).

### Stato di consegna (FEAT-011 implementata)

Tutte le superfici sopra sono ora **generate nativamente** e **validate dallo schema offline** (gruppo G,
`packages/sertor/tests/test_schema_copilot_hooks.py` + `test_schema_copilot_frontmatter.py` +
`test_hooks_script_copilot.py`). In dettaglio:

- Hook wiring: generato da `render_copilot_hooks` (`sertor-install-kit`) — `version:1`, voci piatte,
  `timeoutSec`, nessun campo Claude-only. Gli asset statici in formato Claude
  (`assets/copilot/hooks/*.json`) sono stati RIMOSSI.
- Output script per evento: `wiki-pending-check.ps1` + `wiki-session-start.ps1` rendono l'output nativo via
  `-Assistant copilot` (agentStop `{decision:"allow",reason}`, sessionEnd su stderr, no dual-field);
  `sertor-rag-usage-check.ps1` resta fail-open (exit 0 sempre).
- COMMAND su `copilot-cli`: custom-agent (`.github/agents/*.agent.md`) via il `command_vehicle`
  dell'`AssistantProfile`; su `copilot` (VS Code): prompt-file con `agent:`.
- SessionStart: VS Code `type:"command"` → `{additionalContext}` **[ASSUNTO-VSC]** (gap dichiarato nel
  report d'installazione, `InstallReport.notes`); CLI `type:"prompt"` statico.
- La conferma runtime su client reale resta `⏳` (fuori ambito di prodotto); nessun claim di «parità piena»
  oltre l'evidenza CLI 1.0.63 dell'audit.

---

## 3. Output d'installazione (FR-028)

- **G1**: l'output di `sertor install`/`sertor-flow install` con target Copilot DICHIARA esplicitamente i
  gap noti/non-verificati (in particolare SessionStart VS Code [ASSUNTO-VSC]); NON li elenca come
  "funzionalmente equivalenti".
- **G2**: la documentazione di mappatura delle superfici (es. `wiki/tech/assistant-targeting.md` e/o
  `docs/`) riflette la tabella §2; nessuna voce dichiara parità non verificata (SC-009).
- **G3**: la verifica MCP CLI (FR-020) è documentata con la sua evidenza (PR #66) e il caveat doc-ufficiale.

---

## 4. Regola per nuovi asset Copilot (FR-026)

Ogni nuovo asset rivolto a Copilot aggiunto all'installer richiede un **test di validità-schema**
corrispondente PRIMA di essere considerato pronto (process gate, riflesso nella checklist di
`/speckit-tasks` e nella documentazione del gruppo G).
