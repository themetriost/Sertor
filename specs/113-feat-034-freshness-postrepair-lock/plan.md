# Implementation Plan: `rag-freshness` post-riparazione + auto-heal del lock stantio

**Branch**: `113-feat-034-freshness-postrepair-lock` · **Spec**: `./spec.md` · **Requisiti**: `../../requirements/debito-tecnico/feat-034-freshness-postrepair-lock/requirements.md`

**Date**: 2026-07-20

## Summary

Due fix nello stesso hook `rag-freshness`, layer diversi:
- **A (hook asset, `sertor-core` invariato):** invertire l'ordine di `_worker()` in
  `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.py` → **re-index (ripara) →
  `doctor` (rimisura) → scrittura atomica del verdetto post-riparazione**; `reason` accumula **tutte** le
  aree degradate; re-index fallito ⇒ `degraded`.
- **B (`sertor-core`):** auto-heal del single-writer lock in `_IndexLock.__enter__`
  (`src/sertor_core/services/indexing.py:345`) → su `FileExistsError`, se il PID nel lockfile è
  **confermato morto**, rimuovi il lockfile stantio e ritenta; altrimenti fail-loud come oggi. Nuovo helper
  `_pid_alive()` cross-OS stdlib. Reclamo → `log_event(WARNING, "index.lock.reclaimed", …)`.

## Technical Context

- **Linguaggio:** Python ≥ 3.11, **solo stdlib** (nessuna nuova dipendenza).
- **File toccati:**
  - `packages/sertor/src/sertor_installer/assets/rag/hooks/rag-freshness.py` — riordino `_worker()` + `reason` completo.
  - `.claude/hooks/rag-freshness.py` — copia dogfood, allineata via `uv run python -m sertor_installer.sync`.
  - `src/sertor_core/services/indexing.py` — `_pid_alive()` + auto-heal in `_IndexLock.__enter__`.
  - `docs/install.md` §10.1 — descrizione dell'ordine (ora post-riparazione) + rimozione «at most one session behind».
  - `CHANGELOG.md` — nota utente.
  - Test: `packages/sertor/tests/test_install_rag_freshness.py` (inverti l'ordine atteso + guard upgrade) ·
    `tests/unit/test_incremental_index.py` (auto-heal PID morto/vivo) · nuovo `tests/unit/test_index_lock_autoheal.py`.
- **Invarianti da preservare:** schema `rag.health/1`; hook `exit 0` sempre, no LLM, solo vehicle
  (Principio XI); worker detached non-bloccante; contratto `IndexLockedError` (messaggio + uso su PID vivo);
  protezione single-writer contro run **vivi** concorrenti; byte-parity bundle↔dogfood.

## Constitution Check (gate)

| # | Principio | Esito | Nota |
|---|---|---|---|
| — | **Missione / North Star** | ✅ PASS | Entrambi i fix servono la **freschezza/affidabilità del segnale reso all'agente**: A rende credibile l'allarme di staleness; B impedisce che il RAG resti bloccato e serva contesto stantio. |
| I | Core a dipendenze verso l'interno | ✅ PASS | B vive in `services/indexing` (interno), dietro nessun vehicle nuovo; A è un asset host-facing che consuma solo il vehicle. |
| II | Provider/backend dietro boundary | ✅ N/A | Nessun provider/store toccato. |
| III | Semplicità (YAGNI), unità piccole | ✅ PASS | A = scambio d'ordine + accumulo lista; B = un helper + un ramo di reclamo. Niente astrazioni nuove (no lease/mtime-lock). |
| IV | Errori espliciti, niente null silenzioso | ✅ PASS | B fail-loud sull'ambiguità (lockfile non-PID → non reclamato → `IndexLockedError`); A forza `degraded` su re-index fallito. |
| V | Testabilità / qualità provata | ✅ PASS | A: ordine + `reason` testabili sul corpo installato; B: auto-heal deterministico (PID morto simulato vs PID vivo). |
| VI | Idempotenza, determinismo, non-distruttività | ✅ PASS | B reclama **solo** un lock il cui owner è morto (conservativo); A resta idempotente (rebuild-from-scratch invariato). Scrittura stato atomica. |
| VII | Leggibilità, lascia il codice più pulito | ✅ PASS | A rende l'ordine leggibile come «ripara-poi-misura»; B centralizza la liveness in un helper documentato. |
| VIII | Config centralizzata | ✅ PASS | Nessun nuovo default; nessuna manopola nuova (l'auto-heal non è opzionale by design). |
| IX | Osservabilità | ✅ PASS | B emette `index.lock.reclaimed` (WARNING strutturato); A smette di scrivere breadcrumb-rumore nel caso normale. |
| X | Host-agnostico | ✅ PASS | A: asset portabile via `uv run` (nessun path host-specifico); byte-parity garantita dal guard. B: nel pacchetto, nessun assunto host. |
| XI | Consumo via vehicle | ✅ PASS | A usa solo `doctor`/`index` (mai import di `sertor_core`); B è nel core, esposto via il vehicle `index`. |
| XII | Fail Loud, Fix the Cause | ✅ PASS | **Cuore della feature:** A ripara la causa dell'allarme falso (misura pre-riparazione) invece di silenziarlo; B auto-guarisce ma **visibilmente** (warning), mai in silenzio. |

**Esito gate: 12/12 + missione PASS.** Nessuna deviazione da giustificare.

## Design

### A — riordino di `_worker()` (rag-freshness.py)

Ordine nuovo:
1. **Re-index (la riparazione)** — `uv run --project .sertor sertor-rag index .`; cattura `reindex_failed`.
2. **`doctor --json` (la rimisura)** — post-riparazione; deriva `verdict`/`areas`/aree-degradate.
3. **Verdetto:** `degraded` se qualunque area è `warn`/`fail`, o `doctor` exit≠0, **o** `reindex_failed`.
   `reason = "; ".join(<tutte le aree degradate + eventuale re-index fallito>)` (REQ-004).
4. **Scrittura atomica** di `.rag-health.json` (temp + `os.replace`) col verdetto **post-riparazione**.
5. Breadcrumb su `reason` non vuoto (semantica esistente preservata; nel caso normale ora non scatta).

Nota DA-6/CS-7: la scrittura resta atomica → mai lacera. Rispetto a oggi lo stato è scritto *dopo* il
re-index: alla primissima esecuzione è assente per la finestra di re-index → lo start-hook tratta l'assenza
come no-op (sicuro). Nelle esecuzioni successive persiste lo stato della sessione precedente (accettabile).

### B — auto-heal del lock (`indexing.py`)

```python
def _pid_alive(pid: int) -> bool:
    """True se un processo con `pid` è vivo. Stdlib, cross-OS, NON perturba il processo (REQ-010).
    POSIX: os.kill(pid, 0) — ESRCH→morto, EPERM→vivo. Windows: OpenProcess+GetExitCodeProcess
    (os.kill(pid,0) su Windows TERMINEREBBE il processo → vietato)."""
```

`_IndexLock.__enter__`: estrai la creazione esclusiva in `_create_exclusive()`; su `FileExistsError`
prova `_try_reclaim_stale()` (reclama **solo** se il lockfile contiene un PID decimale confermato morto,
poi `unlink`), quindi ritenta una volta `_create_exclusive()`; se ancora presente → `IndexLockedError`.
Al reclamo, `log_event(logging.WARNING, "index.lock.reclaimed", index_dir=str(self._dir), dead_pid=pid)`.

Conservativo (R-1): lockfile vuoto/garbage/illeggibile → **non** reclamato (fail-loud).

## Test
- **A:** in `test_install_rag_freshness.py` invertire `test_freshness_worker_doctor_before_state_before_index`
  → `test_freshness_worker_reindex_before_doctor_before_state` (asserisce `index_pos < doctor_pos <
  state_write_pos`); nuovo guard che l'`upgrade` consegna il corpo con l'ordine nuovo (REQ-011);
  `test_freshness_hook_content` esteso (accumulo multi-area).
- **B:** nuovo `tests/unit/test_index_lock_autoheal.py` — (a) lockfile con PID morto → `index()` procede;
  (b) lockfile con PID vivo (il proprio) → `IndexLockedError`; (c) lockfile vuoto/garbage → `IndexLockedError`
  (conservativo); (d) reclamo emette `index.lock.reclaimed` (caplog); `_pid_alive` su PID vivo/morto noti.
- **Non-regressione:** `test_incremental_index.py::test_concurrent_run_raises_index_locked` deve restare
  verde (il lock del test tiene il PID del processo di test = vivo).
- **Sync/parità:** `tests/unit/test_assets_rag_dogfood_sync.py` verde dopo `sertor_installer.sync`.

## Out of scope (rinviato)
- Rimisura nel SessionStart; spiegabilità `index`/`last_index` (E10-FEAT-037); lease/mtime-lock; PID-reuse.

## Phase completion
- [x] requirements · [x] specify · [x] clarify (nessuna forcella aperta) · [x] plan (+ Constitution 12/12)
- [x] tasks · [x] implement

## Verifica (implement)
- **Unit test verdi:** nuovo `tests/unit/test_index_lock_autoheal.py` (10) — `_pid_alive` reale su
  PID vivo/morto (**esercita il path ctypes/OpenProcess Windows LIVE su questa macchina**),
  reclamo su PID morto + evento `index.lock.reclaimed`, PID vivo → `IndexLockedError`, lockfile
  ambiguo → non reclamato, acquire/release pulito. `test_install_rag_freshness.py` (26): ordine
  invertito (`index<doctor<state`), accumulo multi-area, **guard sull'esito d'upgrade** (REQ-011).
  Non-regressione `test_incremental_index.py` verde.
- **Gate:** `uv run pytest -m "not cloud"` → **1205 passed** (1 xfail packaging noto; **2 fail
  ambientali** `test_clean_install_uv[sertor|sertor-flow]`: HEAD ancora al SHA di master pre-commit
  → `_branch_reachable`=True ma il nome-branch non è su origin → `uvx@branch` fallisce; **skippano
  dopo il commit**, passano a PR pushata). sertor **535** · kit **194** · `ruff check .` pulito.
- **Sync bundle↔dogfood** (`sertor_installer.sync`) + guard byte-parity `test_assets_rag_dogfood_sync`
  (12) verdi.
- **Prova LIVE (auto-heal, via vehicle CLI reale, provider `hash` offline):** lock con **PID morto**
  → `sertor-rag index` procede (`exit 0`); lock con **PID vivo** (persistente via `Start-Process`) →
  `IndexLockedError` (`exit 1`, «index is locked … another process»). Discriminazione provata LIVE.
- **Doc utente:** `docs/install.md` §10.1 (ordine post-riparazione + auto-heal lock) + `CHANGELOG.md`.
- **Deferred a post-merge (come gemelle):** LIVE del **worker-hook** Parte A sul **runtime installato**
  (richiede re-lock `.sertor/` dopo merge) — l'ordine è già asserito deterministicamente sul corpo
  installato; il caso normale → `healthy` è garantito per costruzione (doctor dopo re-index).
