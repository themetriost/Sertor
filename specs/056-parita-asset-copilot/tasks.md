# Tasks: Parità funzionale completa su Copilot CLI + governance dual-target

**Branch**: `056-parita-asset-copilot` · **Plan**: `specs/056-parita-asset-copilot/plan.md`

> **Revisione 2026-06-19 — redesign nativo.** I task della versione precedente (deposito in
> `.github/sertor/`, skill→custom-agent, `{SKILL_DIR}`) erano completati ma per il **meccanismo
> sbagliato**. Questi task rifanno la feature col **meccanismo nativo agent-skills** (`.github/skills/`).
> Working tree con modifiche `{SKILL_DIR}` da scartare. Ordine TDD: prima la guardia, poi
> deposito/neutralizzazione finché passa. `[P]` = parallelizzabile (file distinti).
>
> **Stato 2026-06-19:** T000–T041 ✅ fatti (ruff clean · sertor 292 · kit 131 · sertor-flow 120).
> T042 ✅ deposito verificato su dir temp pulita **e** su Spike reale (`.github/skills/wiki-author/**`,
> SKILL.md dispatcher, `wiki-curator` by-name, 0 `.github/sertor`, 0 leak, idempotente) — **resta solo
> la prova LIVE interattiva** `/skills` su Copilot CLI (utente). T043 (record/log/EXEC + PR) in corso.

## Fase 0 — Reset dell'approccio obsoleto

- **[ ] T000** — Scartare le modifiche non committate `{SKILL_DIR}` (working tree sporco) e isolare ciò
  che del commit `b6e85b7` va rimosso: `.github/sertor/`, placeholder `{SKILL_DIR}`, render
  skill/command→custom-agent. (Si rifà sopra: il reset è logico, non un `git revert` cieco.)

## Fase 1 — Foundational: guardia di parità (definisce il "done")

- **[ ] T001** — Aggiornare `packages/sertor/tests/test_assets_copilot_parity.py` alla topologia nativa:
  rende i piani Copilot (wiki+governance+rag) in tmp e verifica i 4 invarianti — (a) niente `.claude/`,
  (b) niente slash-command/`$ARGUMENTS` come invocazione, (c) niente "Claude Code", (d) **closure dei
  riferimenti** (ogni file citato da un body reso è un target del piano; relativi risolti rispetto alla
  cartella del referente — ora la cartella skill `.github/skills/wiki-author/`).
- **[ ] T002** — Estendere la closure (T001) **anche al piano Claude** (non-regressione neutralizzazione).
- **[ ] T003** — Test-del-test (R1): casi che distinguono `/wiki` comando da `wiki/` path/URL; un
  riferimento dangling deve far fallire (d) nominando il file; verificare che la skill nativa Copilot
  (SKILL.md + payload co-locato) soddisfi la closure. *Atteso ora:* la suite **FALLISCE** sugli asset
  correnti (post-reset) → baseline rossa che le fasi successive portano a verde.

## Fase 2 — US1/US2 (P1): wiki nativa funzionante + zero refs Claude

- **[ ] T010** — `install_wiki.py:_build_copilot_wiki_plan`: depositare l'albero skill in
  `.github/skills/wiki-author/**` via `iter_asset_dir("claude/skills/wiki-author")` byte-copy del payload;
  produrre `SKILL.md` come **dispatcher** (corpo da `commands/wiki.md` + frontmatter nativo
  `name`/`description`). **Rimuovere** il render skill→custom-agent, `_COPILOT_SKILL_SUPPORT_DIR`
  (`.github/sertor/`), `_WIKI_AGENT_DST` per la skill, e la riga del command come custom-agent.
- **[ ] T011** — Rimuovere `_skill_dir_for` / `_SKILL_DIR_PLACEHOLDER` e la sostituzione `{SKILL_DIR}` in
  `_render_for_target` (non più necessaria: riferimenti relativi co-locati).
- **[ ] T012** — `sertor_owned_paths` (ramo Copilot): dichiarare `.github/skills/wiki-author` come
  owned_dir (uninstall/upgrade in blocco). Il coverage `plan ⊆ owned` esistente deve restare verde.
- **[ ] T013 [P]** — Neutralizzare `assets/claude/skills/wiki-author/SKILL.md`: path `.claude/` playbook →
  riferimento relativo co-locato; `/wiki` → capability-neutro.
- **[ ] T014 [P]** — Neutralizzare `assets/claude/agents/wiki-curator.md` (path playbook → relativo).
- **[ ] T015 [P]** — Neutralizzare `assets/claude/commands/wiki.md` (path playbook, `/wiki`, `$ARGUMENTS`):
  è la **fonte unica** del dispatcher Copilot oltre che il command Claude.
- **[ ] T016 [P]** — Neutralizzare `assets/claude/skills/wiki-author/wiki-playbook.md`: `.claude/`
  auto-descrittivo + `/wiki`; mantenere i link interni **relativi** (`ops/<x>.md`, `../*-craft.md`).
- **[ ] T017 [P]** — Neutralizzare i moduli `assets/claude/skills/wiki-author/ops/*.md` + craft (menzioni
  `/wiki`, path playbook auto-descrittivo).
- **Checkpoint:** la guardia di parità su **wiki** passa; `test_assets_copilot_guard.py` (byte-identica)
  resta verde per `wiki-curator`; la skill nativa è ben formata (SKILL.md dispatcher + payload co-locato).

## Fase 3 — US3 (P2): full sweep governance + rag

- **[ ] T020** — Audit `packages/sertor-flow/.../assets/claude/**` + `install_governance.py`: neutralizzare
  i body di `requirements`/agenti (path `.claude/…` → relativo; `/requirements` → capability-neutro;
  `claude-md-block-sdlc.md`). Verificare se la skill `requirements` ha payload multi-file → se sì,
  deposito nativo analogo; altrimenti nessun deposito aggiuntivo.
- **[ ] T021** — Audit `packages/sertor/.../assets/rag/**`: verificare `claude-md-block-rag-usage.md`
  pulito (0 `.claude/`/slash/"Claude Code"); coperto dalla guardia nel piano rag.
- **Checkpoint:** la guardia di parità su **tutti** i piani (wiki+governance+rag) passa.

## Fase 4 — US5 (P3): governance dual-target

- **[ ] T030 [P]** — `assets/claude/skills/wiki-author/wiki-playbook.md`: sezione "Host-agnostic authoring"
  (no path d'assistente letterali, no slash/`$ARGUMENTS`, riferimenti relativi co-locati, skill native).
- **[ ] T031 [P]** — `wiki/tech/assistant-targeting.md`: sezione "Parità by construction (FEAT-001)" →
  aggiornata al **meccanismo nativo** (skill native per-host, contenitore tradotto) + la guardia come
  enforcement.
- **[ ] T032 [P]** — `assets/claude-md-block.md`: neutralizzato `/wiki` + voce DoD (toccare un asset
  distribuibile ⇒ verifica di parità).

## Fase 5 — Ri-sync dogfood + verifica end-to-end

- **[ ] T040** — Ri-sync `.claude/**` di questo repo dagli asset neutralizzati via `sertor_installer.sync`
  + `sertor_flow.sync` (coerenza dogfood↔asset; guard anti-drift verde). NB: il `CLAUDE.md` di Sertor è
  scritto a mano (non toccato dal blocco distribuibile).
- **[ ] T041** — Suite completa verde: parità (T001-003) + byte-identica + coverage owned + suite `sertor`
  / `sertor-flow` / `kit`; ruff pulito sui src/test toccati.
- **[ ] T042** — Verifica empirica su **Spike**: install wiki Claude (dir temp) → skill in `.claude/...`;
  install wiki Copilot → `.github/skills/wiki-author/**` presente, 0 `.claude/` nei resi; **`/skills`
  elenca `wiki-author`**; invocarla → la prima azione (Read playbook co-locato) riesce; ripulire l'even-
  tuale `wiki/playbook/wiki-playbook.md` STRAY su Spike; uninstall rimuove la cartella skill. Ripristinare.
- **[ ] T043** — Aggiornare il riferimento al piano in `CLAUDE.md` + record/log + EXEC roadmap
  (E10-FEAT-001 → done al merge); re-index dogfood post-merge; aggiornare/sostituire i commit di PR #80.

## Criteri di completamento (mappano gli SC)

SC-001 T010/T042 · SC-002/003 T013-017,T020-021,T001 · SC-004 T001/T002 · SC-005 T040/T041 (byte-identica
verde) · SC-006 T016/T042 · SC-007 T030-032 · SC-008 T042 (Spike, `/skills`).
