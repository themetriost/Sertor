# Implementation Plan: Parità funzionale completa su Copilot CLI + governance dual-target

**Branch**: `056-parita-asset-copilot` · **Spec**: `specs/056-parita-asset-copilot/spec.md` ·
**Requirements**: `requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md`
(decomposizione di FEAT-001, epica `debito-tecnico`).

> **Revisione 2026-06-19 — meccanismo NATIVO agent-skills.** Il plan precedente costruiva la parità con
> skill→custom-agent + container `.github/sertor/` + placeholder `{SKILL_DIR}`. Letta la doc ufficiale
> Copilot (agent skills native, auto-discovery per-cartella-skill), questo plan usa il **meccanismo
> nativo**: deposito della skill in `.github/skills/wiki-author/**`, skill unica che assorbe il command.

## Summary

Su un host Copilot CLI la capacità wiki è non funzionante: il **payload multi-file** della skill
`wiki-author` non viene depositato e i **body** distribuiti citano path `.claude/` e comandi `/wiki`
inesistenti. La feature ottiene la **parità funzionale completa** su Copilot CLI depositando la skill
come **skill nativa** `.github/skills/wiki-author/**` (auto-scoperta dal client), il cui `SKILL.md` è il
**dispatcher delle 8 operazioni** (assorbe il ruolo del command `/wiki`, che su Copilot non ha veicolo
nativo) e il cui payload (playbook/ops/craft) è **byte-copiato** dalla fonte unica Claude. I **body** sono
neutralizzati alla sorgente (host-agnostici); i riferimenti interni restano **relativi** e risolvono
identici grazie alla co-locazione. Si **riusa l'infrastruttura** (`iter_asset_dir` + byte-copy) come nel
ramo Claude, **rimuovendo** il render skill→custom-agent e `{SKILL_DIR}`. Una **guardia di parità
offline** con **closure dei riferimenti** rende la regressione impossibile, e tre sedi di **governance
dual-target** impediscono che il difetto rientri. Ramo Claude invariato (gate).

## Technical Context

- **Pacchetti toccati**: `sertor` (installer wiki/rag + asset), `sertor-flow` (installer governance +
  asset). **`sertor-core` INVARIATO** (porte/adapter/composition/`sertor-rag`). `sertor-install-kit`:
  toccato **solo** per **rimuovere** l'uso del render skill→custom-agent dal piano wiki (nessun nuovo
  `Surface`/`ArtifactKind`; il render custom-agent resta per `wiki-curator`).
- **Punti di codice noti**: `packages/sertor/src/sertor_installer/install_wiki.py`
  (`_build_copilot_wiki_plan` → deposito nativo a `.github/skills/`; rimozione di `_skill_dir_for`/
  `_SKILL_DIR_PLACEHOLDER`/`_COPILOT_SKILL_SUPPORT_DIR`/`_WIKI_AGENT_DST`-per-skill; `sertor_owned_paths`
  → `.github/skills/wiki-author`); `surfaces.py` (`render_custom_agent` resta per l'agente; non più per la
  skill); `install_governance.py`.
- **Asset sorgente**: `packages/sertor/.../assets/claude/{skills/wiki-author/**,agents/wiki-curator.md,
  commands/wiki.md,claude-md-block.md}`; `packages/sertor-flow/.../assets/claude/**`. Il `SKILL.md`
  Copilot è **derivato** da `commands/wiki.md` (dispatcher) → serve un punto di resa che produca il
  `SKILL.md` Copilot dal command body + frontmatter nativo.
- **Test**: `packages/sertor/tests/test_assets_copilot_parity.py` (aggiornare alla nuova topologia);
  guardia byte-identica esistente (`test_assets_copilot_guard.py`) **resta verde** per `wiki-curator`;
  coverage `plan ⊆ owned` esistente protegge i path.
- **Verifica empirica**: host reale **Spike** (Copilot CLI 1.0.63) — `/skills` elenca `wiki-author`.
- **Tooling**: `uv` (un solo `.venv`); offline (NFR-05, niente cloud nei test).

## Constitution Check (pre-design) — **PASS 11/11, nessuna deroga**

- **I (core = libreria):** `sertor-core` non viene toccato; la feature vive negli installer/asset. ✅
- **II (boundary, local-first):** nessun nuovo fetch; la guardia è offline; byte-copy locale. ✅
- **III (YAGNI, unità piccole):** riuso di `iter_asset_dir` + byte-copy esistente; **niente nuovi
  `ArtifactKind`**; il redesign **rimuove** codice (custom-agent-skill, `{SKILL_DIR}`) → meno superficie. ✅
- **IV (errori espliciti, niente null silenzioso):** la **closure dei riferimenti** trasforma un agente
  rotto-silenzioso (playbook mancante) in un **fallimento esplicito** del test. ✅
- **V (testabilità da misure):** guardia offline + SC misurabili (0 `.claude/`, 0 dangling, skill elencata
  e prima azione riesce su Spike). ✅
- **VI (idempotenza, determinismo, non-distruttività):** byte-copy deterministico; install idempotente;
  uninstall rimuove la cartella skill in blocco (owned_dir). ✅
- **VII (leggibilità, lascia il codice più pulito):** rimuove il meccanismo inventato; usa il nativo. ✅
- **VIII (config centralizzata):** nessuna nuova manopola; nulla di hardcodato fuori posto. ✅
- **IX (osservabilità):** percorso d'installazione, `install.report` invariato. ✅
- **X (host-agnostico):** è **l'embodiment** del principio — body host-agnostici + skill nativa per host. ✅
- **XI (consumo via vehicles):** install-time, non runtime-library. ✅

## Project Structure (file impattati)

```
requirements/debito-tecnico/host-agnosticita-asset-residui/requirements.md   [aggiornato 2026-06-19]
specs/056-parita-asset-copilot/{spec.md,plan.md,tasks.md}                    [questa fase]
packages/sertor/src/sertor_installer/
  install_wiki.py                  → deposito skill nativa .github/skills + sertor_owned_paths; RIMUOVE
                                     custom-agent-skill, .github/sertor, {SKILL_DIR}
  surfaces.py / kit                → SKILL.md Copilot = dispatcher da commands/wiki.md (frontmatter nativo)
  assets/claude/skills/wiki-author/{SKILL.md,wiki-playbook.md,ops/*.md,*-craft.md}  → neutralizzare
  assets/claude/agents/wiki-curator.md, commands/wiki.md, claude-md-block.md         → neutralizzare/DoD
  tests/test_assets_copilot_parity.py   → aggiornare alla topologia nativa
packages/sertor-flow/src/sertor_flow/
  install_governance.py            → audit/neutralizzare (requirements/agenti)
  assets/claude/**                 → neutralizzare body
wiki/tech/assistant-targeting.md   → sezione "parità by construction" (skill native per-host)
.claude/**, CLAUDE.md              → ri-sync dogfood (coerenza asset↔dogfood)
```

## Phase 0 — Research & Decisioni (chiuse, riviste 2026-06-19)

| ID | Decisione | Esito |
|---|---|---|
| D1 | Body dual-valido | **Neutralizzare la sorgente** (no `.claude/`/slash/`$ARGUMENTS`); payload byte-identico |
| D2 | Deposito skill Copilot | **Skill NATIVA `.github/skills/wiki-author/**`** (auto-discovery); skill unica che assorbe il command |
| D3 | Meccanismo deposito | **Riuso `iter_asset_dir` + byte-copy**; RIMUOVE render skill→custom-agent e `{SKILL_DIR}`; no nuovi ArtifactKind |
| D4 | Guardia | Offline: no `.claude/` · no slash/`$ARGUMENTS` · no "Claude Code" · **closure riferimenti** (Copilot+Claude) |
| D5 | Governance | Playbook + `assistant-targeting.md` + DoD nel rituale |
| D6 | Scope | **Full sweep**: wiki + governance + rag |
| — | SKILL.md Copilot | **Dispatcher** derivato dalla fonte unica `commands/wiki.md` + frontmatter nativo (`name`/`description`) |

**Doc ufficiali (docs.github.com/copilot, 2026-06-19):** agent skills native in `.github/skills/`,
`.claude/skills/`, `.agents/skills/`; `SKILL.md`+corpo; **auto-discovery per-cartella-skill** (tutti i
file della cartella della skill invocata, incl. `ops/`); funziona su Copilot CLI; nessun slash-command
custom (`/wiki` non creabile) → il command è assorbito dalla skill.

**Unknown risolti:** verifica Copilot reale = Spike (non xfail); host già installati = `upgrade`;
`derive-entity-types` = fuori (backlog separato).

## Phase 1 — Design

**Data model:** **nessuna entità nuova**. Concetti: *skill nativa per-host*, *payload co-locato*, *body
host-agnostico*, *dispatcher (SKILL.md Copilot da command)*, *closure*.

**Contratti:** l'unico "contratto" nuovo è la **guardia di parità** (test, non API runtime):
- *Input:* i piani d'installazione Copilot (wiki+governance+rag) resi in memoria/tmp + (per closure) il
  piano Claude.
- *Invarianti verificati:* (a) `.claude/` ∉ file resi Copilot; (b) nessuno slash-command/`$ARGUMENTS`
  come invocazione; (c) "Claude Code" ∉ body resi; (d) **closure**: ∀ riferimento-a-file in un body reso
  ⇒ il file è un target del piano (relativi risolti rispetto alla cartella del referente).
- *Output:* PASS/FAIL con nome del riferimento dangling in caso di fallimento.

**Quickstart (verifica end-to-end):** install wiki Claude (dir temp) → skill in `.claude/skills/wiki-author/`;
install wiki Copilot su Spike → skill nativa in `.github/skills/wiki-author/**` + 0 `.claude/` nei resi;
`/skills` elenca `wiki-author`; invocarla → la prima azione (Read playbook co-locato) riesce; install
Claude non-regressione; uninstall rimuove la cartella skill in blocco.

## Fasi di implementazione (mappate alle user story)

1. **US1/US2 (P1) — wiki funzionante + zero refs Claude:** neutralizzare gli asset wiki (SKILL/agent/
   command/playbook/ops/craft); riscrivere `_build_copilot_wiki_plan` per depositare l'albero skill in
   `.github/skills/wiki-author/**` (`SKILL.md` = dispatcher da `commands/wiki.md`; payload byte-copy via
   `iter_asset_dir`); **rimuovere** render skill→custom-agent, `.github/sertor/`, `{SKILL_DIR}`;
   aggiornare `sertor_owned_paths` (Copilot → `.github/skills/wiki-author`).
2. **US3 (P2) — full sweep:** audit + neutralizzare governance (`requirements`/agenti) e rag.
3. **US4 (P2) — guardia:** aggiornare `test_assets_copilot_parity.py` (4 controlli + closure su Copilot e
   Claude) alla nuova topologia nativa.
4. **US5 (P3) — governance:** sezione playbook + `assistant-targeting.md` + DoD nel `claude-md-block.md`.
5. **Ri-sync dogfood + verifica:** ri-sync `.claude/**`; suite verde (parità + byte-identica + coverage);
   verifica empirica su Spike (Claude + Copilot, `/skills`).

## Constitution Check (post-design) — **PASS 11/11, nessuna deroga**

Il design non introduce nuovi `ArtifactKind`, non tocca `sertor-core`, non aggiunge fetch né config,
**rimuove** codice (meccanismo inventato), e rafforza i Principi IV (errori espliciti via closure), VII
(usa il nativo, meno superficie) e X (host-agnosticità). Nessun elemento di complessità da tracciare.

## Complexity Tracking

Nessuna deviazione costituzionale. Rischio residuo (non costituzionale) = R4 (auto-discovery della skill
nativa su host reale), gestito empiricamente nella fase di verifica — è però il **meccanismo documentato**,
non una scommessa: il rischio è basso.
