# Contract — Interfaccia CLI `--assistant` e mapping upstream (post FEAT-012)

**Branch**: `052-copilot-cli-only`. Contratto **comportamentale offline** (nessuna rete/client reale):
ciò che ogni comando accetta sul flag `--assistant`, gli artefatti che produce per `copilot-cli`, e la
traduzione verso spec-kit. Tutte le clausole sono verificabili con test offline
(`FakeCommandRunner`/`FakeSpecifyRunner`).

## 1. Valori di assistente accettati (FR-005/006/007, SC-001/002)

| Pacchetto · comando | Valori validi | `copilot` (legacy) | Default |
|---|---|---|---|
| `sertor install wiki` | `claude`, `copilot-cli` | errore esplicito, exit 1 | `claude` |
| `sertor install rag` | `claude`, `copilot-cli` | errore esplicito, exit 1 | `claude` |
| `sertor upgrade` | `claude`, `copilot-cli` | errore esplicito, exit 1 | `claude` |
| `sertor uninstall` | `claude`, `copilot-cli` | errore esplicito, exit 1 | `claude` |
| `sertor-flow install` | `claude`, `copilot-cli` | errore (argparse choices), exit 2 | `claude` |
| `sertor-flow upgrade` | `claude`, `copilot-cli` | errore (argparse choices), exit 2 | `claude` |
| `sertor-flow uninstall` | `claude`, `copilot-cli` | errore (argparse choices), exit 2 | `claude` |

- **C1.1** Il messaggio d'errore su `copilot` MUST **nominare** `copilot-cli` come valore corretto.
  (Per `sertor`: il messaggio di `from_str` elenca i validi, che includono `copilot-cli`. Per
  `sertor-flow`: argparse elenca le `choices` `{claude, copilot-cli}`.)
- **C1.2** In **0** pacchetti il valore `copilot` produce un'installazione (SC-001).

## 2. Artefatti per `--assistant copilot-cli` (FR-002/003/008/009/010, SC-003/004)

Dopo `sertor install rag --assistant copilot-cli`:
- **C2.1** Esiste `.mcp.json` con root-key `mcpServers` contenente `sertor-rag`.
- **C2.2** NON esiste `.vscode/mcp.json` (FR-002, SC-004).
- **C2.3** Esiste `.github/hooks/sertor-hooks.json` con schema nativo Copilot (`version:1`, voci piatte,
  `timeoutSec`) — FEAT-011 invariato (FR-017).

Dopo `sertor install wiki --assistant copilot-cli`:
- **C2.4** I COMMAND (`/wiki`, skill `wiki-author`) sono `.github/agents/*.agent.md` (custom-agent).
- **C2.5** NON esistono `.github/prompts/*.prompt.md` per i COMMAND nostri (FR-003, SC-004).

Dopo `sertor-flow install --assistant copilot-cli`:
- **C2.6** Esiste `.github/agents/requirements.agent.md` (FR-009, SC-003).
- **C2.7** NON esiste `.github/prompts/requirements.prompt.md` (FR-010, SC-003).
- **C2.8** Il corpo del custom-agent `requirements` è byte-identico (body sotto frontmatter) al canonico
  `claude/skills/requirements/SKILL.md` (FR-011/anti-drift).

## 3. Mapping upstream spec-kit (FR-013/014/015, SC-006/007)

- **C3.1** Per `build_specify_command(profile)` con `profile.assistant == "copilot-cli"`, la lista
  comando contiene `--ai` seguito da `copilot` (NON `copilot-cli`).
- **C3.2** Per `profile.assistant == "claude"`, contiene `--ai claude`.
- **C3.3** La traduzione risiede in **un solo** simbolo (`_SPECKIT_AI_FLAG`) — verificabile per lettura.
- **C3.4** `launch_speckit` eseguito due volte sullo stesso ospite con `copilot-cli`: la seconda
  esecuzione ritorna `Outcome.SKIPPED` (layout già presente), NON rilancia `specify init` (idempotenza).

## 4. Non-regressione Claude (FR-016, SC-005)

- **C4.1** Gli artefatti prodotti per `--assistant claude` (sertor e sertor-flow) sono **identici** a
  pre-refactor (stessi path, stesso contenuto).
- **C4.2** I test rivolti a Claude passano **senza modifiche alla loro logica**.

## 5. Core invariato (NFR-03, SC-010)

- **C5.1** In **0** punti il refactor importa o modifica `sertor_core` (porte/adapter/composition/
  `sertor-rag`). Il kit resta stdlib-only e privo di dipendenze dal nucleo.
