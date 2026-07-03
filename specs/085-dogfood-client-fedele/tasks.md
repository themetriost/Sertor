# Tasks — dogfood client-fedele (E10-FEAT-027)

**Input:** plan.md · research.md · spec.md · quickstart.md · requirements. **Branch:** `087-a05-dogfood-client-debt`.
Legenda: `[P]` parallelizzabile (file distinti, nessuna dipendenza) · **🔒 GATED** = richiede autorizzazione
utente + auto-mode (integra codice esterno in config / cancella config).

## Fase 1 — Foundational (tooling, sicuro/committabile)

- **T001** [P] — Scrivi `scripts/dev/materialize-speckit.ps1` (D-1/D-2): risolve una temp dir; lancia
  `uvx --from git+…spec-kit@v<SPECKIT_VERSION> specify init . --here --ai claude --script ps --no-git --force
  --ignore-agent-tools` con overlay `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`; copia nel repo **solo** la
  machinery rigenerabile (D-4); **verifica** che `constitution.md`/`plan-template.md`/`feature.json` restino
  invariati e **fallisce loud** (exit ≠0) se cambierebbero; idempotente. Il pin `SPECKIT_VERSION` va letto/
  citato da fonte unica (no hardcode duplicato — VIII). *File inerte finché non eseguito.*
- **T002** [P] — Aggiungi a `.gitignore` il blocco machinery rigenerabile (D-4): `.claude/skills/speckit-*/`,
  `.specify/scripts/`, `.specify/workflows/`, `.specify/integrations/`, `.specify/init-options.json`,
  `.specify/integration.json`, `.specify/templates/{checklist,constitution,spec,tasks}-template.md`. Commento
  che spiega il perché (rigenerabile come `.venv`, non vendorata — NFR-1). *Inerte finché la machinery non esiste.*
- **T003** [P] — Aggiungi a `CLAUDE.md` (sezione **Sviluppo**, accanto a `uv sync`) lo step di setup:
  «materializza la machinery SpecKit con `scripts/dev/materialize-speckit.ps1` (rigenerabile, non in git)»
  (D-6/REQ-007). *(Il puntatore-piano è già aggiornato a 085.)*

## Fase 2 — Core (chiude lo special-case) — 🔒 GATED

- **T004** 🔒 — Rimuovi i 9 `.claude/agents/speckit-*.md` (D-3/REQ-005). *(auto-mode: cancellazione config.)*
- **T005** 🔒 — Esegui `scripts/dev/materialize-speckit.ps1` per materializzare localmente la machinery
  (Q4/REQ-001): rende la sessione fedele. *(auto-mode: integra codice esterno spec-kit in `.claude/`/`.specify/`.)*
  Dipende da T001.
- **T006** — Scrivi `tests/unit/test_dogfood_speckit_fidelity.py` (D-5/REQ-006): asserisce **(1)** 0 file
  `.claude/agents/speckit-*.md`; **(2)** nessuna machinery rigenerabile **tracciata** (`git ls-files` non
  elenca `.claude/skills/speckit-*` né `.specify/scripts/**`). Offline, senza rete, senza dipendere dalla
  machinery locale. **Verde solo dopo T004.** Dipende da T004 (per l'asserzione 1).

## Fase 3 — Verifica & chiusura

- **T007** — Verifica accettazione (quickstart): SC-1..SC-6 / AS-1..AS-7. In particolare: le 9 skill +
  `setup-plan.ps1` esistono (post-T005); 0 agenti speckit; `git status`/`git ls-files` puliti sulla machinery;
  `constitution.md`/`plan-template.md`/`feature.json` **byte-identici** (`git diff --quiet`); `sertor-core`
  invariato. Dipende da T004-T006.
- **T008** — Guardia + suite: `uv run pytest tests/unit/test_dogfood_speckit_fidelity.py -q` verde;
  `test_assets_sync`/`test_no_vendored_speckit` invariati; `ruff check` pulito. Dipende da T006.
- **T009** — Record + roadmap/epica (FEAT-027 → ✅), voce di log, smoke MCP (il server va **riavviato** per
  servire le skill nuove come corpus/skill, non serve al rituale). Dipende da T007-T008.
- **T010** — Commit branch + (su ok utente) PR. Delegato al `configuration-manager`. Dipende da T009.

## Note d'esecuzione
- **Ordine consigliato:** T001+T002+T003 (paralleli, sicuri, committabili subito) → **checkpoint/autorizzazione**
  → T004+T005 (gated) → T006 → T007-T008 → T009-T010.
- **MVP incrementale:** T001-T003 forniscono già il *tooling* di fedeltà; T004-T006 **chiudono** lo special-case.
- `implement` (T004/T005) è **gated**: l'auto-mode esige review per integrazione-codice-esterno + cancellazione config.
