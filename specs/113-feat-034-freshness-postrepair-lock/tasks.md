# Tasks: `rag-freshness` post-riparazione + auto-heal del lock stantio

**Branch**: `113-feat-034-freshness-postrepair-lock` · **Plan**: `./plan.md`

Ordine dipendency-aware. `[P]` = parallelizzabile.

## Parte A — verdetto post-riparazione (hook asset)
- [ ] **T-A1** — Riordina `_worker()` in `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.py`:
  re-index (cattura `reindex_failed`) → `doctor --json` → verdetto (degraded se area warn/fail **o** exit≠0
  **o** `reindex_failed`) → scrittura atomica. (REQ-001/002/003/005)
- [ ] **T-A2** — `reason` accumula **tutte** le aree degradate + eventuale «re-index failed» (no più
  `if not reason`). (REQ-004)
- [ ] **T-A3** — Sync bundle→dogfood: `uv run python -m sertor_installer.sync`; verifica byte-parity
  `.claude/hooks/rag-freshness.py`. (REQ-012)

## Parte B — auto-heal del lock stantio (core)
- [ ] **T-B1** — Aggiungi `_pid_alive(pid)` in `src/sertor_core/services/indexing.py`: POSIX `os.kill(pid,0)`
  (ESRCH→False, EPERM→True); Windows `OpenProcess`+`GetExitCodeProcess` via `ctypes` (mai `os.kill`).
  (REQ-006/010)
- [ ] **T-B2** — In `_IndexLock`: `_create_exclusive()` + `_try_reclaim_stale()` (reclama solo su PID
  decimale confermato morto; conservativo su vuoto/garbage) + retry singolo in `__enter__`. (REQ-007/008)
- [ ] **T-B3** — `log_event(WARNING, "index.lock.reclaimed", index_dir=…, dead_pid=…)` al reclamo. (REQ-009)

## Parte C — test
- [ ] **T-C1 [P]** — `test_install_rag_freshness.py`: inverti l'ordine atteso
  (`test_freshness_worker_reindex_before_doctor_before_state`, `index<doctor<state`); estendi
  `test_freshness_hook_content` per l'accumulo multi-area; nuovo guard sull'**esito d'upgrade** (REQ-011).
- [ ] **T-C2 [P]** — nuovo `tests/unit/test_index_lock_autoheal.py`: PID morto→procede · PID vivo→locked ·
  vuoto/garbage→locked · reclamo emette l'evento · `_pid_alive` su PID noti.
- [ ] **T-C3** — Verifica non-regressione: `test_incremental_index.py::test_concurrent_run_raises_index_locked`
  resta verde (lock tenuto dal processo di test = vivo).

## Parte D — doc utente & DoD host-facing
- [ ] **T-D1** — `docs/install.md` §10.1: descrivi l'ordine post-riparazione (re-index → doctor → verdetto);
  rimuovi/riformula «at most one session behind»; aggiungi l'auto-heal del lock (nessun blocco manuale).
- [ ] **T-D2** — `CHANGELOG.md`: nota utente (allarme freschezza affidabile + lock auto-guarente).

## Parte E — gate & consegna
- [ ] **T-E1** — `uv run pytest -m "not cloud"` verde + `uv run ruff check .` pulito (gate pre-merge).
- [ ] **T-E2** — Prova LIVE: (B) simula `.index.lock` con PID morto → `sertor-rag index .` procede + warning;
  (A) esegui l'hook worker → `.rag-health.json` con verdetto post-riparazione.
- [ ] **T-E3** — Commit branch + PR (configuration-manager); a valle merge: EXEC + epic.md + re-lock +
  re-index + smoke MCP + wiki (record/distill/lint).
