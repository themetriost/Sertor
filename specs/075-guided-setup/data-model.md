# Data Model — guided-setup (E12-FEAT-002)

**Branch**: `075-guided-setup` · **Fase**: Phase 1 (design)

> **Natura.** Feature **non-core**: nessuna entità di dominio, porta o motore. Inventario degli **asset**
> (skill + agente) e dei **punti di wiring** nei pacchetti `sertor`/`sertor-install-kit`. Le "entità"
> sono asset e artefatti di distribuzione, non oggetti runtime.
>
> **Revisione (decisione utente).** Il concierge è un **AGENTE vero** (con model pin), non uno
> stub-skill. La feature distribuisce **una skill** (`guided-setup`, il «come») **e un agente**
> (`concierge`, la persona/orchestratore) — il pattern `sertor-flow` (agenti + skill).

---

## §1 — Inventario degli asset SORGENTE (creati)

Bundle del pacchetto `sertor`. Le skill RAG sotto `assets/rag/skills/`; gli agenti RAG sotto
`assets/rag/agents/` (nuovo, gemello di `sertor-flow`/`assets/claude/agents/`).

| Asset | Path sorgente (nuovo) | Tipo | Surface | Render |
|-------|-----------------------|------|---------|--------|
| Skill `guided-setup` | `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md` | native agent-skill (single-file) | (skill RAG) | byte-copy (host-agnostico) |
| Agente `concierge` | `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md` | agente (dispatcher 1 ramo) | `Surface.AGENT` | Claude byte-copy · Copilot `render_custom_agent` |

**Skill `guided-setup`** — frontmatter nativo agent-skill (`name`/`description`/`user-invocable`/
`disable-model-invocation`); body EN host-agnostico byte-identico; single-file (closure file triviale);
riferimento-per-nome ai vehicle.

**Agente `concierge`** — frontmatter Claude `name: concierge` / `description:` (mirato al setup, è il
selettore d'attivazione) / `tools:` / **`model: sonnet`** (pin esplicito); body EN host-agnostico,
**un solo ramo** (instrada verso `guided-setup`, citata **per nome**); nessun riferimento a
config-recommender/search-diagnose (FEAT-004/007).

---

## §2 — Artefatti di DISTRIBUZIONE (per target)

| Asset | Claude | Copilot CLI | Render |
|-------|--------|-------------|--------|
| `guided-setup` | `.claude/skills/guided-setup/SKILL.md` | `.github/skills/guided-setup/SKILL.md` | byte-copy (identico) |
| `concierge` | `.claude/agents/concierge.md` | `.github/agents/concierge.agent.md` | Claude: byte-copy (**`model: sonnet` preservato**) · Copilot: `render_custom_agent` (**`model:` omesso**, frontmatter tradotto, body verbatim) |

Contenitori risolti via `AssistantProfile.render_path(Surface.AGENT, name)` per l'agente; via prefisso
`_CLAUDE_SKILLS_BASE`/`_COPILOT_SKILLS_BASE` per la skill. La guardia di parità verifica corpo e
frontmatter (§4).

---

## §3 — Punti di WIRING nell'installer `sertor` (modificati)

File: `packages/sertor/src/sertor_installer/install_rag.py`. Modifiche additive (RNF-7).

| # | Punto | Modifica |
|---|-------|----------|
| W1 | costanti skill | + `_USABILITY_SKILL_NAMES = ("guided-setup",)` accanto a `_EVAL_SKILL_NAMES`. |
| W2 | factory skill | generalizzare `_eval_skill_artifacts` → `_skill_artifacts(names, is_copilot)` (DRY). |
| W3 | costante + routing agente | + `_CONCIERGE_AGENT_SRC = "rag/agents/concierge.md"` + `_concierge_artifact(assistant)` (replica `sertor-flow:147-157` con `Surface.AGENT`/`render_path`). |
| W4 | render-aware FILE | + helper **locale** `_render_rag_file(art)`: `.agent.md` → `render_custom_agent`; altrimenti byte-copy. Usato da install + upgrade. **NO nuovo seam kit.** |
| W5 | `build_rag_plan` | + `plan.extend(_skill_artifacts(_USABILITY_SKILL_NAMES, is_copilot))` + `plan.append(_concierge_artifact(assistant))`. |
| W6 | `sertor_owned_paths` | skill → `owned_dirs` (`{base}/skills/guided-setup`); agente → `owned_files` (path da `render_path`). |
| W7 | `_apply_rag_upgrade` (FILE) | usare `_render_rag_file(art)` invece di `read_asset_text` → agente Copilot aggiornato con frontmatter tradotto. |

> **Nota su `_apply_rag_hook_file`.** Oggi il `FILE` del rag plan (hook script) è byte-copia pura. Con
> W4, l'apply del `FILE` usa `_render_rag_file` per tutti i `FILE` non-hook: gli script `.ps1` non
> finiscono in `.agent.md` → restano byte-copia (il branch traduce solo `.agent.md`). Nessuna
> regressione sugli hook.

**Nessuna nuova** `ArtifactKind`/`Surface`/`WriteStrategy`; **nessuna** modifica al kit
(`sertor-install-kit`); **nessuna** modifica a `sertor-core`.

---

## §4 — Punti della GUARDIA DI PARITÀ (estesi)

File: `packages/sertor/tests/test_assets_copilot_parity.py` + `tests/test_install_rag.py`.

| # | Punto | Modifica |
|---|-------|----------|
| G1 | `_render_rag` allineato al render reale | il renderer del test deve tradurre `.agent.md` (come il plan), così (a)(b)(c) coprono **l'agente** e il `model: sonnet` Claude **non sfugge** al check di leak su Copilot. **Punto critico.** |
| G2 | `(a)(b)(c)` | automatici (rag plan in `_all_copilot_bodies`) una volta allineato `_render_rag` (G1): no-`.claude/`/no-slash/no-nomi-Claude su skill **e** agente Copilot. |
| G3 | `(d)` closure mirata | «ogni asset di usabilità citato per nome (`concierge → guided-setup`) è depositato dal rag plan su quel target». |
| G4 | deposito + frontmatter | test §6 sotto. |

---

## §5 — Tracciamento dello scope (backlog d'epica)

File: `requirements/usabilita/epic.md`.

| Riga | Da | A |
|------|----|----|
| FEAT-002 (`:172`) | decomposta → requirements | **in progress** → spec/plan `075` |
| FEAT-009 (`:180`) | da decomporre | **parzialmente avviata (stub agente `concierge` a un ramo)** — gli altri rami (config-recommender/search-diagnose) + i check proattivi restano FEAT-009 |

FEAT-003 / FEAT-004: consumo opzionale citato «quando disponibili»; voci esistenti, nessuna orfana.

---

## §6 — Enumerazione completa dei file toccati/creati

**Creati (asset sorgente):**
- `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md`
- `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md`

**Modificati (wiring installer):**
- `packages/sertor/src/sertor_installer/install_rag.py` (W1-W7)

**Modificati (guardia/test, offline):**
- `packages/sertor/tests/test_assets_copilot_parity.py` (G1-G3)
- `packages/sertor/tests/test_install_rag.py` (deposito + frontmatter + lifecycle)

**Modificati (tracciamento scope):**
- `requirements/usabilita/epic.md` (§5)

**Artefatti SpecKit (creati/aggiornati):**
- `specs/075-guided-setup/{research,data-model,quickstart,plan}.md`
- `specs/075-guided-setup/contracts/{skill-guided-setup,agent-concierge,distribution-parity}.md`

**Invariati (verificato):** `sertor-core` (porte/adapter/composition/engine), `sertor-install-kit`
(assistant/surfaces/artifacts — riuso, no estensione), tutti i comandi runtime
(`install`/`configure`/`doctor`/`index`).
