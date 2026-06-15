# Contract — Parità superfici di governance per-assistente (`sertor-flow.install.parity/1`)

Garantisce (verificabile da test) la **parità funzionale** della governance tra Claude e Copilot
(SC-002), distinguendo le superfici **ottenute via launch** da quelle **Sertor-authored tradotte**.

## Invariante di parità

Per ogni superficie di governance prodotta per `claude`, l'installazione `copilot` MUST produrre la
stessa superficie con un contenitore valido **oppure** dichiarare un **gap** (motivo leggibile). Nessuna
omissione silenziosa (FR-011).

## Resa attesa (copilot)

| Categoria | Origine | Contenitore copilot |
|---|---|---|
| Comandi/agenti SpecKit (`/speckit.*`) | **launch** `specify init --ai copilot` | `.github/prompts/*.prompt.md` + `.github/agents/*.agent.md` |
| Macchinario `.specify/` | **launch** (condiviso) | `.specify/**` (agent-agnostic, una volta sola) |
| Agente `requirements-analyst` | Sertor-authored (render) | `.github/agents/requirements-analyst.agent.md` |
| Agente `configuration-manager` | Sertor-authored (render) | `.github/agents/configuration-manager.agent.md` |
| Skill `requirements` | Sertor-authored (render) | `.github/prompts/requirements.prompt.md` |
| Blocco rituale SDLC | Sertor-authored | `.github/copilot-instructions.md` (marker `SERTOR:SDLC-RITUAL`) |
| Costituzione-starter | assistant-agnostic | `.specify/memory/constitution.md` (identica) |

## Proprietà verificabili (test)

1. **Copertura**: superfici governance per `copilot` ⊇ quelle per `claude` (a meno di gap dichiarati).
2. **Non-regressione Claude (FR-012/SC-003)**: install `--assistant claude` produce governance
   funzionalmente equivalente a oggi (con `specify` mockato che emette il layout Claude).
3. **No vendored SpecKit**: dopo il refactor, il bundle `sertor-flow` **non** contiene più asset
   `speckit-*`/`specify/**` (test di guardia `test_no_vendored_speckit`).
4. **No core dep (SC-006)**: nessun import di `sertor_core` in `sertor-flow` (test di guardia esistente).
5. **Costituzione identica** tra assistenti.
6. **Renderer condiviso**: `sertor` e `sertor-flow` usano lo stesso renderer dal kit (un'unica fonte).
