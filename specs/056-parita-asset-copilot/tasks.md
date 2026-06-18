# Tasks: Parità funzionale completa su Copilot CLI + governance dual-target

**Branch**: `056-parita-asset-copilot` · **Plan**: `specs/056-parita-asset-copilot/plan.md`

Ordine guidato dalle dipendenze e da un approccio **TDD**: prima la guardia di parità (fallirà sugli
asset attuali), poi neutralizzazione + deposito finché passa. `[P]` = parallelizzabile (file distinti).

## Fase 1 — Foundational: guardia di parità (definisce il "done")

- **[X] T001** — Scrivere `packages/sertor/tests/test_assets_copilot_parity.py`: rende i piani Copilot
  (wiki+governance+rag) in tmp e verifica i 4 invarianti — (a) niente `.claude/`, (b) niente
  slash-command come invocazione, (c) niente "Claude Code", (d) **closure dei riferimenti** (ogni file
  citato da un body reso è un target del piano; relativi risolti rispetto al container del referente).
- **[X] T002** — Estendere la closure (T001) **anche al piano Claude** (non-regressione neutralizzazione).
- **[X] T003** — Test-del-test (R1): casi che distinguono `/wiki` comando da `wiki/` path/URL; un riferimento
  dangling deve far fallire (d) nominando il file. *Atteso ora:* la suite **FALLISCE** sugli asset
  correnti (è il bug) → baseline rossa che le fasi successive portano a verde.

## Fase 2 — US1/US2 (P1): wiki funzionante + zero refs Claude

- **[X] T010** — Deposito payload: in `install_wiki.py:_build_copilot_wiki_plan`, dopo lo `SKILL.md`,
  aggiungere il loop `iter_asset_dir("claude/skills/wiki-author")` (escluso `SKILL.md`) →
  `.github/sertor/wiki-author/<rel>` come `ArtifactKind.FILE` byte-copy.
- **[X] T011** — `sertor_owned_paths` (ramo Copilot): dichiarare `.github/sertor/wiki-author` come owned_dir
  (uninstall/upgrade in blocco). Il coverage `plan ⊆ owned` esistente deve restare verde.
- **[X] T012 [P]** — Neutralizzare `assets/claude/skills/wiki-author/SKILL.md`: path playbook → riferimento
  per nome host-agnostico; `/wiki` → capability-neutro. (byte-identico Claude↔Copilot preservato)
- **[X] T013 [P]** — Neutralizzare `assets/claude/agents/wiki-curator.md` (path playbook).
- **[X] T014 [P]** — Neutralizzare `assets/claude/commands/wiki.md` (path playbook). *(NB: comando solo-Claude,
  ma il body alimenta anche altre superfici — neutralizzare per coerenza.)*
- **[X] T015 [P]** — Neutralizzare `assets/claude/skills/wiki-author/wiki-playbook.md`: `.claude/`
  auto-descrittivo + `/wiki`; mantenere i link interni **relativi** (`ops/<x>.md`, `../*-craft.md`).
- **[X] T016 [P]** — Neutralizzare i moduli `assets/claude/skills/wiki-author/ops/*.md` (menzioni `/wiki`).
  *(+ `log-craft.md` path playbook auto-descrittivo)*
- **Checkpoint:** la guardia di parità su **wiki** passa; `test_assets_copilot_guard.py` (byte-identica)
  resta verde.

## Fase 3 — US3 (P2): full sweep governance + rag

- **[X] T020** — Audit `packages/sertor-flow/.../assets/claude/**` + `install_governance.py`: neutralizzati i
  body di `requirements`/agenti (`requirements-analyst.md` path `.claude/…` → per-nome; `SKILL.md`
  `/requirements` → capability-neutro; `claude-md-block-sdlc.md` `.claude/skills/speckit-*` → per-nome).
  Nessun payload multi-file governance scoperto → nessun deposito aggiuntivo necessario.
- **[X] T021** — Audit `packages/sertor/.../assets/rag/**`: `claude-md-block-rag-usage.md` già pulito
  (0 `.claude/`/slash/"Claude Code"); coperto dalla guardia nel piano rag.
- **Checkpoint:** la guardia di parità su **tutti** i piani (wiki+governance+rag) passa.

## Fase 4 — US5 (P3): governance dual-target

- **[X] T030 [P]** — `assets/claude/skills/wiki-author/wiki-playbook.md`: sezione "Host-agnostic authoring"
  (regole no-path-assistente, no-slash, riferimento-per-nome).
- **[X] T031 [P]** — `wiki/tech/assistant-targeting.md`: sezione "Parità by construction (FEAT-001)" + la
  guardia come enforcement + pattern payload-per-host.
- **[X] T032 [P]** — `assets/claude-md-block.md`: neutralizzato `/wiki` (riga ~37) + voce DoD (toccare un
  asset distribuibile ⇒ verifica di parità).

## Fase 5 — Ri-sync dogfood + verifica end-to-end

- **[X] T040** — Ri-sync `.claude/**` di questo repo dagli asset neutralizzati via
  `sertor_installer.sync` + `sertor_flow.sync` (coerenza dogfood↔asset; guard anti-drift verde). NB: il
  blocco `claude-md-block.md` riguarda gli ospiti; il `CLAUDE.md` di Sertor è scritto a mano (non toccato).
- **[X] T041** — Suite completa verde: parità (T001-003, 9 test) + byte-identica + coverage owned + suite
  `sertor` (290) / `sertor-flow` (120) / `kit` (131); ruff pulito sui src/test toccati.
- **T042** — Verifica empirica su **Spike**: install wiki Claude (dir temp) → payload in `.claude/...`;
  install wiki Copilot → `.github/sertor/wiki-author/**` presente, 0 `.claude/` nei resi; **invocare
  l'agente wiki su Copilot CLI 1.0.63**: la prima azione (Read playbook) riesce; verificare che
  `.github/sertor/` **non** generi agenti-fantasma (R4); uninstall rimuove i container. Ripristinare Spike.
- **T043** — Aggiornare il riferimento al piano in `CLAUDE.md` (convenzione SpecKit) + record/log + EXEC
  roadmap (E10-FEAT-001 → done al merge); re-index dogfood post-merge.

## Criteri di completamento (mappano gli SC)

SC-001 T010/T042 · SC-002/003 T012-016,T020-021,T001 · SC-004 T001/T002 · SC-005 T040/T041 (byte-identica
verde) · SC-006 T015/T042 · SC-007 T030-032 · SC-008 T042 (Spike).
