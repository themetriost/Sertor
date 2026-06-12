# Tasks: `sertor install rag` — installer della capacità RAG

**Feature dir**: `specs/015-sertor-install-rag/` · **Branch di lavoro**: `master` (bugfix installer,
autorizzato) · **Fonti**: spec.md (26 FR, US1..US4), plan.md, research.md (R1..R6), data-model.md,
contracts/cli-install-rag.md, quickstart.md.

**Convenzioni**: `[P]` = parallelizzabile (file diversi, nessuna dipendenza su task incompleti).
`[USn]` = task di una user story. I test sono richiesti (convenzione del pacchetto: vedi
`packages/sertor/tests/`). Base path: `packages/sertor/`. **Zero modifiche al core.**

---

## Phase 1 — Setup (prerequisiti condivisi)

- [ ] T001 Estendere gli enum in `packages/sertor/src/sertor_installer/artifacts.py`: aggiungere a `ArtifactKind` i valori `DEPENDENCIES`, `ENV_MERGE`, `MCP_MERGE`, `GITIGNORE_APPEND` e a `WriteStrategy` i valori `BOOTSTRAP_DEPS`, `MERGE_ENV`, `MERGE_JSON`, `APPEND_LINES`. Verifica: import ok, test esistenti `test_install_wiki.py` ancora verdi (enum additivi). *(enabler FR-006..019)*
- [ ] T002 [P] Creare la directory asset `packages/sertor/src/sertor_installer/assets/rag/` (con i template nei task foundational). Verifica: `resources.iter_asset_dir("rag")`/`read_asset_text` la trovano (package-data già incluso da hatch, `pyproject.toml` member). *(enabler FR-014/017)*

## Phase 2 — Foundational (bloccante per tutte le user story)

- [ ] T003 [P] Creare `packages/sertor/src/sertor_installer/command_runner.py`: `CommandResult(returncode, stdout, stderr)`, Protocol `CommandRunner` (`is_available(tool)`, `run(cmd, cwd)`), impl `SubprocessRunner` (usa `subprocess.run` + `shutil.which`). Nessun import pesante. Verifica: istanziabile, `is_available("uv")` non lancia. *(R3, FR-008/012)*
- [ ] T004 [P] Aggiungere `FakeCommandRunner` (scriptabile: registra i comandi, restituisce esiti predefiniti incl. "uv assente" e "uv add fallito") in `packages/sertor/tests/conftest.py` come fixture. Verifica: usabile da un test fittizio. *(NFR-5)*
- [ ] T005 [P] Creare `packages/sertor/src/sertor_installer/rag_profile.py`: `RagInstallOptions` (frozen), `RagHostProfile`, funzione pura `compose_extras(backend, include_graph, include_rerank) -> list[str]` (sempre `mcp`; `azure` solo se backend azure; `graph`/`rerank` salvo opt-out), default corpus = nome dir sanitizzato. Verifica: T009. *(FR-003/004/006/009, R5)*
- [ ] T006 [P] Creare l'asset `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl`: chiavi Azure (`RAG_BACKEND=azure`, `SERTOR_STORE_BACKEND=local`, endpoint/key/embed-deployment, `SERTOR_CORPUS`), **segreti vuoti**, `SERTOR_EXCLUDE_PATTERNS` = default-excludes del core **+ `.sertor`** (R2). Verifica: il file ha `*_API_KEY=` vuoto. *(FR-014/015/023, REQ-282)*
- [ ] T007 [P] Creare l'asset `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl`: `RAG_BACKEND=local`, `OLLAMA_HOST`, `SERTOR_CORPUS`, stesso `SERTOR_EXCLUDE_PATTERNS`. Verifica: nessuna chiave Azure. *(FR-014/023)*
- [ ] T008 [P] Creare l'asset `packages/sertor/src/sertor_installer/assets/rag/mcp.server.json.tmpl`: frammento `sertor-rag` (`command="uv"`, `args=["run","--directory",".sertor","python","-m","sertor_mcp.server"]`, `env={"SERTOR_CORPUS": ...}`). Verifica: JSON valido parametrizzabile. *(FR-017, REQ-281)*
- [ ] T009 [P] Creare `packages/sertor/tests/test_rag_profile.py`: `compose_extras` (azure/local, opt-out `--no-graph`/`--no-rerank`, `mcp` sempre), default corpus sanitizzato, validazioni opzioni. Verifica: verde. *(FR-009, US4 parziale)*

## Phase 3 — User Story 1 (P1, MVP): un-comando-RAG-pronto

**Goal**: `sertor install rag --backend azure` su un target lascia `.sertor/` con dipendenze +
`.env`/`.mcp.json`/`.gitignore` coerenti, senza indicizzare. **Test indipendente**: SC-001/002.

- [ ] T010 [P] [US1] Creare `packages/sertor/src/sertor_installer/env_merge.py`: scrive il template `.env` se assente; se presente, merge additivo per-chiave (mai sovrascrive valori), mai scrive segreti. Ritorna `(Outcome, detail)`. Verifica: T015. *(FR-014/015/016)*
- [ ] T011 [P] [US1] Creare `packages/sertor/src/sertor_installer/mcp_merge.py`: scrive/merge `.mcp.json` (radice host) aggiungendo il server `sertor-rag`, preservando gli altri server; se già presente → skip/merged; JSON malformato → `ConfigError`. Pattern di `settings_merge.py`. Verifica: T015. *(FR-017/018, REQ-231/232)*
- [ ] T012 [P] [US1] Creare `packages/sertor/src/sertor_installer/gitignore_append.py`: append dedup di `.sertor/.venv/`, `.sertor/.index*`, `.sertor/.env` nel `.gitignore` host; nessun duplicato. Verifica: T015. *(FR-019, REQ-240/241)*
- [ ] T013 [US1] Creare `packages/sertor/src/sertor_installer/install_rag.py`: `build_rag_plan(profile, with_deps) -> list[Artifact]` (ordine: DEPENDENCIES→ENV_MERGE→MCP_MERGE→GITIGNORE_APPEND, salta DEPENDENCIES se `with_deps=False`) e `execute_rag_plan(plan, profile, runner) -> InstallReport` (fail-fast no-rollback come `install_wiki.execute_plan`; ramo DEPENDENCIES = `uv init --bare` se manca `.sertor/pyproject.toml` + `uv add "sertor-core[extras] @ git+url"` dentro `.sertor/`; `detail` riflette il comando `uv`). Mai indicizza. Verifica: T016. *(FR-006/007/008/010/011/013/020/021/022/023)*
- [ ] T014 [US1] Estendere `packages/sertor/src/sertor_installer/__main__.py`: aggiungere al sub-parser `rag` i flag `--target/--backend/--corpus/--no-graph/--no-rerank/--no-deps/--json`, l'handler `_cmd_install_rag` (valida target, costruisce options/profile, esegue il piano col `SubprocessRunner`, stampa report) e instradare `rag` nell'handler in `_dispatch` **rimuovendo lo stub** `CapabilityNotAvailableError` per `rag`. Verifica: T017. *(FR-001/002/003/004/005/012)*
- [ ] T015 [P] [US1] Creare `packages/sertor/tests/test_env_merge.py`, `test_mcp_merge.py`, `test_gitignore_append.py`: creazione + merge additivo + idempotenza, in `tmp_path`. Verifica: verdi. *(FR-014..019)*
- [ ] T016 [US1] Creare `packages/sertor/tests/test_install_rag.py`: con `FakeCommandRunner`, `--backend azure` su target vuoto → `.sertor/.env`, `.mcp.json`, `.gitignore` creati, comandi `uv init`/`uv add` registrati (mai `index`), report `created`. Verifica: SC-001/002. *(FR-006..023)*
- [ ] T017 [US1] Estendere `packages/sertor/tests/test_cli.py`: dispatch `install rag` (exit 0), uso errato (exit 2, es. `--backend foo`), `--json` valido. Verifica: verde. *(FR-005)*

**Checkpoint US1**: MVP consegnabile — il comando installa la capacità RAG (con `uv` simulato nei test).

## Phase 4 — User Story 2 (P2): idempotenza e non distruttività

**Goal**: re-run sicuro, contenuti utente preservati. **Test indipendente**: SC-003.

- [ ] T018 [P] [US2] In `test_install_rag.py`: re-run sullo stesso target → stato identico, esiti solo `skipped`/`merged`, zero duplicati. Verifica: SC-003. *(FR-026/REQ-271)*
- [ ] T019 [P] [US2] In `test_mcp_merge.py`/`test_env_merge.py`/`test_gitignore_append.py`: target con `.mcp.json` (server `altro`), `.env` (`SERTOR_CORPUS=mio`), `.gitignore` preesistenti → contenuti utente preservati, `sertor-rag`/chiavi aggiunti accanto. Verifica: REQ-222/231/241. *(FR-016/018/019)*
- [ ] T020 [P] [US2] In `test_install_rag.py`: `FakeCommandRunner` con `uv add` fallito → `execute_rag_plan` si ferma, `InstallReport.failed_step` valorizzato, artefatti già scritti restano (no rollback); `uv` assente → errore di dominio leggibile. Verifica: FR-012/013/023. *(REQ-214/215/251)*

## Phase 5 — User Story 3 (P3): fix di distribuzione / `uvx`

**Goal**: `sertor` eseguibile standalone senza fallire la risoluzione di `sertor-core`. **Test
indipendente**: SC-005.

- [ ] T021 [US3] Applicare il fix in `packages/sertor/pyproject.toml`: aggiungere `[tool.uv.sources]` con `sertor-core = { git = "https://github.com/themetriost/Sertor.git" }` (R1). Verifica: file valido. *(FR-024/REQ-260/261)*
- [ ] T022 [US3] Validazione DEV (locale, senza rete esterna): `uv lock` e `uv run pytest` dalla **root** del monorepo restano verdi → la risoluzione workspace di `sertor-core` non è rotta. Verifica: SC-005 (parte dev), FR-025/REQ-262.
- [ ] T023 [US3] ⚠️ Validazione STANDALONE **RICHIEDE PUSH** (non bloccante per gli altri task): dopo il push su `origin`, da ambiente pulito `uvx --from "git+https://github.com/themetriost/Sertor.git#subdirectory=packages/sertor" sertor --help` → exit 0. Da eseguire come passo finale post-merge. Verifica: SC-005 (parte standalone). *(FR-024)*

## Phase 6 — User Story 4 (P4): backend locale e controllo via flag

**Goal**: `--backend local` + opt-out extra + `--no-deps` + `--corpus` + `--json`. **Test
indipendente**: SC-006.

- [ ] T024 [P] [US4] In `test_install_rag.py`: `--backend local` → `.env` con chiavi local (no `azure`), extra `sertor-core[mcp,graph,rerank]` (no azure). Verifica: SC-006. *(FR-009/014)*
- [ ] T025 [P] [US4] In `test_install_rag.py`/`test_cli.py`: `--no-graph`/`--no-rerank` (extra esclusi, `mcp` resta), `--no-deps` (nessun `uv add` registrato), `--corpus mio` (in `.env` e `.mcp.json`), `--json` (report JSON valido). Verifica: FR-004/007/009.

## Phase 7 — Polish & cross-cutting

- [ ] T026 [P] Docstring d'intenzione nei moduli nuovi (`install_rag.py`, `rag_profile.py`, `command_runner.py`, `env_merge.py`, `mcp_merge.py`, `gitignore_append.py`), stile dei moduli esistenti.
- [ ] T027 [P] Aggiornare `docs/install.md`: nuova sezione "`sertor install rag`" (un comando via `uvx`, runtime `.sertor/`, flag, install ≠ run, il successivo `sertor-rag index ..`).
- [ ] T028 [P] Aggiornare il README dell'installer (`packages/sertor/` se presente, o nota in `src/sertor_core/README.md`) per togliere "install rag = pianificato/stub".
- [ ] T029 Suite verde: `uv run pytest packages/sertor` e `uv run pytest` (root) verdi; `uv run ruff check packages/sertor` pulito. Verifica: zero fail, zero lint.

---

## Coverage FR → task

| FR | Task |
|---|---|
| FR-001 (sottocomando, no stub) | T014 |
| FR-002 (`--target`, validazione) | T014, T017 |
| FR-003 (`--backend`) | T005, T014 |
| FR-004 (flag opt-out/`--corpus`/`--no-deps`/`--json`) | T005, T014, T025 |
| FR-005 (exit 0/1/2) | T014, T017 |
| FR-006 (runtime `.sertor/`) | T013 |
| FR-007 (`uv init` se manca pyproject) | T013 |
| FR-008 (`uv add` extras, in `.sertor/`) | T003, T013 |
| FR-009 (extra default + opt-out) | T005, T009, T024, T025 |
| FR-010 (solo add, mai rimuove) | T013 |
| FR-011 (install ≠ run) | T013, T016 |
| FR-012 (`uv` assente) | T003, T014, T020 |
| FR-013 (`uv add` fallito, fail-fast) | T013, T020 |
| FR-014/015/016 (`.env` template/segreti vuoti/merge) | T006, T007, T010, T015 |
| FR-017/018 (`.mcp.json` radice/merge) | T008, T011, T015, T019 |
| FR-019 (`.gitignore` dedup) | T012, T015, T019 |
| FR-020 (indicizza host escl. `.sertor`) | T006/T007 (excludes), T013 |
| FR-021 (wiki fuori ambito) | T013 (non scrive artefatti wiki) |
| FR-022/023 (report/fail-fast no-rollback) | T013, T016, T020 |
| FR-024/025 (fix distribuzione/dev intatto) | T021, T022, T023 |
| FR-026 (idempotenza/non distruttività) | T018, T019 |

## Dipendenze & ordine
- **Setup (T001-T002)** prima di tutto.
- **Foundational (T003-T009)** blocca le user story. T003/T005 sono prerequisiti di T013/T014.
- **US1 (T010-T017)** = MVP. T010/T011/T012 [P] → T013 → T014; test T015 [P], T016/T017 dopo.
- **US2/US3/US4** dipendono da US1 ma sono **indipendenti tra loro** (parallelizzabili). US3 (T021)
  tocca solo il `pyproject` → eseguibile anche subito; T023 è differito (richiede push).
- **Polish (T026-T029)** alla fine.

## Percorso critico
`T001 → T003/T005 → T010/T011/T012 → T013 → T014 → T016/T017 → T029` (~10 task). US2/US3/US4
agganciano dopo US1 senza allungare il critico.

## Parallelizzabile
- Setup/Foundational: T002, T003, T004, T005, T006, T007, T008, T009 tutti `[P]`.
- US1: T010/T011/T012 `[P]`, poi T013 sequenziale; T015 `[P]`.
- US2/US4 test `[P]`; US3 T021/T022 indipendenti dal resto.

## MVP
**Solo US1 (Phase 1-3, T001-T017)**: il comando `sertor install rag` funziona end-to-end (con `uv`
simulato nei test). US3 (fix `uvx`) è il complemento per l'uso standalone reale.

**Prossimo passo**: `/speckit-analyze` (verifica trasversale spec/plan/tasks), poi `/speckit-implement`.
