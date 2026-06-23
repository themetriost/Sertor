# Contract — agente `concierge` (anticipa FEAT-009)

Agente *concierge* **vero** (la persona/orchestratore), distribuito dual-target come gli agenti di
`sertor-flow` (`requirements-analyst`/`configuration-manager`): `.claude/agents/concierge.md` ↔
`.github/agents/concierge.agent.md`. È un **dispatcher sottile a un solo ramo**: instrada le richieste
di setup verso la **skill `guided-setup`** (che porta il «come» del flusso). I compiti pieni del
concierge (altri rami verso config-recommender FEAT-004 / search-diagnose FEAT-007, check proattivi
all'avvio) **restano FEAT-009** e **non** sono in ambito (US9).

> **Decisione utente (rivista):** concierge = **agente vero con model pin**, NON uno stub-skill. La
> skill porta le istruzioni del flusso; l'agente è la persona con un modello fissato.

## Frontmatter — sorgente Claude (`assets/rag/agents/concierge.md`)

```yaml
name: concierge
description: "Entry point for getting Sertor working: when the user asks to set up / configure /
  install Sertor or get the RAG running, route to the `guided-setup` skill and follow its
  install → configure → verify flow over the deterministic vehicles. Minimal stub with a SINGLE
  branch (setup → guided-setup); the full concierge (other dispatches, proactive checks) is a
  separate future capability."
tools: Read, Bash, Grep, Glob
model: sonnet
```

- **`model: sonnet`** — il pin esplicito richiesto: l'orchestratore gira su `sonnet` (non `opus`),
  come `configuration-manager`/`wiki-curator` pinnano `haiku`. Preservato **byte-for-byte** sul lato
  Claude.
- `tools` — gli strumenti minimi per instradare ed eventualmente eseguire la skill (la skill orchestra
  i vehicle CLI/MCP).

## Rendering per-target

| Target | File | Frontmatter | Body |
|--------|------|-------------|------|
| Claude | `.claude/agents/concierge.md` | byte-copy (`model: sonnet` **preservato**) | verbatim |
| Copilot CLI | `.github/agents/concierge.agent.md` | `render_custom_agent` → `name`/`description`/`tools`; **`model:` OMESSO** (invalido su Copilot, FEAT-011/049) | verbatim (host-agnostico) |

`render_custom_agent` è la funzione del kit già usata da `sertor-flow` per gli stessi agenti — riuso
diretto, nessun nuovo seam.

## Body (contratto comportamentale)

| Intento | Azione |
|---------|--------|
| «set up / configure / install Sertor», «get the RAG working» | **instrada** verso la skill `guided-setup` (citata **per nome**) e ne segue il flusso |
| qualsiasi altro intento | **non** dispatcha (un solo ramo) |

### Vincoli (US9.2, anti scope-creep)

- **un solo ramo** (`guided-setup`); **nessun** riferimento a `config-recommender`, `search-diagnose`,
  `FEAT-004`, `FEAT-007` o capacità non esistenti;
- il body cita `guided-setup` **per nome** (closure: la skill è depositata dal piano);
- host-agnostico nel body (no `.claude/`/slash-command/nomi Claude); il **`model:`** vive nel
  frontmatter (preservato su Claude, omesso su Copilot) — non nel body;
- non importa il core, non reimplementa comandi (D↔N): è instradamento + orchestrazione via la skill.

### Agent-discovery (non auto-attivazione indebita)

L'agente vive in `.claude/agents/` ↔ `.github/agents/` (i contenitori agent-discovery nativi, dove
deve stare per essere invocabile — come `requirements-analyst`). L'attivazione è governata dal
`description` mirato al setup: non si auto-attiva fuori contesto. La cautela 056 «agente-fantasma»
riguardava un *payload* di skill messo per errore in `agents/` — qui è un agente legittimo.

## Tracciamento (durevole)

L'agente anticipa **FEAT-009**: la riga FEAT-009 del backlog d'epica
(`requirements/usabilita/epic.md`) va marcata **«parzialmente avviata (stub agente `concierge` a un
ramo)»** — gli altri rami + i check proattivi restano FEAT-009. **Non** duplicare né marcare done.

## Invarianti (test)

- `test_concierge_agent_deposited_claude`: `.claude/agents/concierge.md` esiste e il frontmatter
  contiene `model: sonnet`;
- `test_concierge_agent_deposited_copilot`: `.github/agents/concierge.agent.md` esiste e il frontmatter
  **non** contiene `model:` né nomi Claude;
- `test_concierge_routes_to_guided_setup`: il body cita `guided-setup` e **non**
  `config-recommender`/`search-diagnose`/`FEAT-004`/`FEAT-007`;
- closure: `guided-setup` (citata per nome) è una skill depositata dal rag plan su entrambi i target;
- parità: body byte-identico Claude↔Copilot (solo il frontmatter differisce, by construction).
