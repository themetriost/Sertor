# Contratto — Frontmatter nativo Copilot (prompt-file / custom-agent)

**Artefatti**: `.github/prompts/<name>.prompt.md` (VS Code) e `.github/agents/<name>.agent.md` (VS Code +
CLI), generati da `render_prompt_file` / `render_custom_agent` (data-model §2).
**Verificato da**: FR-022/023 / SC-005/006 / SC-007.
**Invariante trasversale**: il **corpo** sotto il frontmatter è byte-for-byte identico alla fonte canonica
Claude (FR-019, guard `test_assets_copilot_guard.py`).

---

## 1. Prompt-file (`*.prompt.md`) — solo target `copilot` (VS Code)

```markdown
---
agent: <valore>
---

<corpo canonico, verbatim>
```

### Regole MUST
- **F1** (FR-016/SC-006): la chiave di modalità è **`agent:`**, MAI `mode:`.
- **F2** (FR-019): il corpo (tutto ciò che segue il frontmatter) è identico alla fonte Claude.

> Valore di `agent:` da fissare in `/speckit-tasks` (requirements §4 suggerisce `agent: 'agent'`);
> l'invariante è la **chiave**, non il valore.

### Anti-pattern (SC-007)
- frontmatter con `mode:` → F1 fail.

---

## 2. Custom-agent (`*.agent.md`) — target `copilot` e `copilot-cli`

```markdown
---
name: <nome>
description: <descrizione>
tools: <strumenti>
---

<corpo canonico (persona), verbatim>
```

### Regole MUST
- **A1** (FR-017/SC-005): **NESSUN** campo `model:` (omesso per i target Copilot; il valore Claude come
  `haiku` è invalido).
- **A2** (FR-018): `name`, `description`, `tools` preservati quando presenti nella fonte.
- **A3** (FR-019): corpo identico alla fonte Claude.

### Anti-pattern (SC-007)
- custom-agent con `model: haiku` (o qualsiasi `model:` con valore Claude) → A1 fail.

---

## 3. Veicolo del COMMAND per target (Q2=c / FR-013/014/015)

| Comando/skill | `copilot` (VS Code) | `copilot-cli` |
|---|---|---|
| `/wiki`, `wiki-author` (capacità wiki) | prompt-file (`agent:`) [+ opz. custom-agent] | **custom-agent** (`.agent.md`) |
| `requirements` (governance, `sertor-flow`) | prompt-file [+ opz. custom-agent] | **custom-agent** |

- **C1** (FR-013/014/SC-004): per `copilot-cli`, ogni superficie COMMAND è installata come custom-agent
  (invocabile da CLI); **zero** comandi solo-prompt-file nel piano CLI.
- **C2** (FR-015, Should): per `copilot` (VS Code) il prompt-file resta fornito.
- **C3** (FR-025/SC-007): un test asserisce che, per `copilot-cli`, NESSUNA superficie comando è
  esclusivamente prompt-file (reintrodurre un comando solo-prompt-file su CLI → fail).
