# Quickstart — Installare Sertor su un ospite GitHub Copilot (FEAT-007)

Come un team che usa **GitHub Copilot (VS Code agent mode)** porta le capacità del pacchetto `sertor`
sul proprio repo e verifica la parità. (Ambito: wiki + rag; governance/SpecKit = `sertor-flow`/FEAT-009.)

## 1. Installazione (install ≠ run)

```bash
# RAG: server MCP + config, target Copilot
sertor install rag --assistant copilot

# Sistema-wiki: istruzioni + comandi + agente + hook, target Copilot
sertor install wiki --assistant copilot
```

Senza `--assistant` il default è `claude` (documentato). Nessuna ingestione parte da sola.

## 2. Cosa compare nel repo (target copilot)

```text
.vscode/mcp.json                      # server "sertor-rag" (chiave servers)
.github/copilot-instructions.md       # blocco rituale/uso a marker (idempotente)
.github/prompts/wiki.prompt.md        # comando /wiki e skill di autoraggio
.github/agents/wiki-curator.agent.md  # agente di bookkeeping del wiki
.github/hooks/sertor-*.json           # hook SessionStart/Stop (wiki) + PreToolUse (anti-bypass XI)
.claude/hooks/*.ps1  →  riusati come script referenziati dagli hook (stesso script)
```

(I segreti del provider restano vuoti nel template; si compilano in `.env` non versionato.)

## 3. Verifica (parità)

1. **MCP collegato**: dal client Copilot, verificare che il server `sertor-rag` risulti connesso e i
   suoi strumenti disponibili (search_code/docs/combined). Nessun editing manuale necessario.
2. **Istruzioni attive**: il blocco rituale di Sertor è presente in `.github/copilot-instructions.md`.
3. **Comando wiki**: invocare il comando di consolidazione del wiki dal client Copilot.
4. **Agente**: esiste `wiki-curator` come custom-agent Copilot.
5. **Hook**: a inizio/fine sessione scatta il promemoria di registrazione; l'uso diretto di
   `sertor_core` fuori dai vehicles produce l'avviso non bloccante (Principio XI).

## 4. Idempotenza e coesistenza

- Ri-eseguire gli stessi comandi: tutto `skipped`/`block già presente`, nessuna duplicazione.
- Installare anche per `--assistant claude` sullo stesso repo: le due configurazioni coesistono
  (`.github/**` per Copilot, `.claude/**`+`CLAUDE.md` per Claude) senza conflitti né doppio-trigger.

## 5. Esecuzione (separata)

Indicizzazione e query restano sui console-script assistant-agnostic:

```bash
sertor-rag index .
sertor-rag search "come funziona il chunking"
```
