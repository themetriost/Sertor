# Implementation Plan: `doctor` ancorato alla radice del progetto

**Branch**: `106-feat-038-doctor-ancorato-root` · **Spec**: `./spec.md` · **Requisiti**: `../../requirements/debito-tecnico/feat-038-doctor-ancorato-root/requirements.md`

**Date**: 2026-07-18

## Summary

`_cmd_doctor` (`src/sertor_core/cli/__main__.py:574`) fissa `root = Path.cwd()` e lo passa a
`current_source_stats(manifest, root)` e `read_mcp_registration(root)`. Il manifest carica bene da ogni
cwd (via `settings.index_dir` self-localizing), ma le sorgenti e `.mcp.json` vengono ri-risolte contro il
cwd → da una sottocartella il verdetto è falso (`index_stale`, `registered=False`). **Fix:** derivare la
radice del progetto dalla **stessa** ancora self-localizing che già risolve `.env`/`.index`, non dal cwd.

## Technical Context

- **Linguaggio:** Python ≥ 3.11, stdlib only (nessuna nuova dipendenza).
- **File toccati:**
  - `src/sertor_core/config/settings.py` — nuova risoluzione `project_root` in `Settings.load`
    (accanto a `index_dir`), riusando l'ancora di `_resolve_env_path`.
  - `src/sertor_core/cli/__main__.py` — `_cmd_doctor`: `root = Path.cwd()` → `root = settings.project_root`,
    fail-loud se `None`.
- **Ancora della radice (precedenza, deterministica):**
  1. `CLAUDE_PROJECT_DIR` se impostato a una dir esistente → parità con gli hook (FEAT-031).
  2. altrimenti il genitore della `.sertor/` che possiede l'indice risolto: quando
     `resolved_index_dir` è `<root>/.sertor/.index` (il layout FEAT-013, ancorato via `env_path`
     trovato da `sys.prefix` → cwd-indipendente), `project_root = resolved_index_dir.parent.parent`.
  3. altrimenti `None` → `doctor` fallisce a voce alta (FR-006), **non** ripiega sul cwd.
- **Perché questa ancora:** `index_dir` è già assoluto e cwd-indipendente (deriva da
  `Path(sys.prefix).parent` per il runtime installato/dogfood). La sua `.sertor/`.parent è la directory
  che è stata indicizzata → esattamente la root rispetto a cui il manifest ha registrato i path relativi.
- **Invarianti da preservare:** schema `doctor.report/1`, exit-code gate, evento `doctor` metrics-only,
  sola-lettura (SC-009), comportamento dalla radice (oggi corretto).
- **Testing:** unit test d'invarianza al cwd (radice vs sottocartella → stesso verdetto), fail-loud fuori
  progetto, guard test host-agnostico, non-regressione suite `doctor`.

## Constitution Check (gate)

| # | Principio | Esito | Nota |
|---|---|---|---|
| — | **Missione / North Star** | ✅ PASS | Rafforza la **qualità del segnale reso all'agente**: `doctor` è la superficie «ha funzionato?» del RAG (fusione code+doc); un verdetto vero (non artefatto del cwd) serve direttamente la fiducia nel retrieval. |
| I | Core a dipendenze verso l'interno | ✅ PASS | La risoluzione vive in `config`/`composition` (interno); il CLI resta thin. |
| II | Provider/backend dietro boundary | ✅ N/A | Nessun provider/store toccato. |
| III | Semplicità (YAGNI), unità piccole | ✅ PASS | Un solo resolver riusato; niente astrazioni nuove; `--root` esplicito **rinviato** (non serve ora). |
| IV | Errori espliciti, niente null silenzioso | ✅ PASS | Root irrisolvibile → fail-loud (non un verdetto su cwd). Coerente con la degradazione onesta esistente (manifest assente → `None`). |
| V | Testabilità / qualità provata | ✅ PASS | Invarianza al cwd testabile deterministicamente (SC-001/002); guard test (SC-005). |
| VI | Idempotenza, determinismo, non-distruttività | ✅ PASS | Sola lettura preservata (SC-004); risoluzione deterministica. |
| VII | Leggibilità, lascia il codice più pulito | ✅ PASS | Rimuove un `Path.cwd()` fuorviante; centralizza la root accanto a `index_dir`. |
| VIII | Config centralizzata | ✅ PASS | La root nasce in `Settings` (unica fonte), non hardcodata nel comando. |
| IX | Osservabilità | ✅ PASS | Evento `doctor` invariato; il fail-loud è un errore visibile. |
| X | Host-agnostico | ✅ PASS | Nessun path host-specifico: si riusa il marker generico `.sertor/` + `CLAUDE_PROJECT_DIR`; guard test (SC-005). |
| XI | Consumo via vehicle | ✅ PASS | Il fix è nel core dietro il CLI `doctor`; nessun accesso diretto alla libreria introdotto. |
| XII | Fail Loud, Fix the Cause | ✅ PASS | È **il cuore della feature**: si elimina la causa (cwd) invece di sopprimere il sintomo; root assente → fail-loud. |

**Esito gate: 12/12 + missione PASS.** Nessuna deviazione da giustificare.

## Design

### `Settings.project_root` (nuovo)
In `Settings.load`, dopo aver risolto `resolved_index_dir`, calcola `resolved_project_root`:
```
env CLAUDE_PROJECT_DIR (se dir esistente)          → quello
elif resolved_index_dir.parent.name == ".sertor"   → resolved_index_dir.parent.parent (resolve absolute)
else                                               → None
```
Aggiungi il campo `project_root: Path | None` alla dataclass. Nessuna rottura: campo nuovo con default.

### `_cmd_doctor` (wiring)
```
root = settings.project_root
if root is None:
    raise DoctorCheckFailed("cannot resolve the project root (.sertor/ not found; "
                            "set CLAUDE_PROJECT_DIR or run inside an installed project)")
```
(oppure un errore dedicato con exit non-zero + messaggio azionabile; NON stampare la tabella dei verdetti
se la root è indeterminata — REQ-004). Il resto del comando invariato.

### Test
- `test_settings_project_root.py` — derivazione: layout `.sertor/.index` → root corretta; `CLAUDE_PROJECT_DIR`
  override; assenza → `None`.
- `test_doctor_cwd_invariance.py` — costruisci un progetto fittizio con `.sertor/.index` + manifest +
  sorgenti; esegui la risoluzione da root e da sottocartella → stesso set di stat / stesso verdetto (SC-001/002).
- fail-loud fuori progetto (SC-003); sola-lettura (SC-004); guard host-agnostico (SC-005).
- Non-regressione: suite `doctor` esistente verde (SC-006).

## Out of scope (rinviato)
- Flag `--root` esplicito (Could — vedi requirements §10; utile a FEAT-034 se servirà passare la root).
- Spiegabilità del verdetto `index` / naming `last_index` (E10-FEAT-037).
- Rimisura post-riparazione di `rag-freshness` (E10-FEAT-034, a valle).

## Phase completion
- [x] requirements · [x] specify · [x] clarify (forcella ancoraggio sciolta) · [x] plan (+ Constitution Check 12/12)
- [x] tasks · [x] implement

## Verifica (implement)
- **Unit test verdi** (5 nuovi): `test_settings_runtime.py` (derivazione root: da ogni cwd via
  `sys.prefix=.sertor/.venv` → root = parent di `.sertor/`; `CLAUDE_PROJECT_DIR` override; assenza → `None`)
  + `test_cli_doctor.py` (helper ancorati a `settings.project_root` non a `Path.cwd()`; fail-loud +
  nessun verdetto se root `None`). Fixture `wired` aggiornata (installazione sana = root risolvibile).
- **Gate:** `uv run pytest -m "not cloud"` → **1193 passed** (1 xfail packaging noto); `ruff check .` pulito.
- **Live end-to-end:** `doctor` gira dalla root (verdetto emesso); da `src/` col workspace venv (privo
  dell'ancora `.sertor/.venv`) → **fail-loud** `exit 1` «cannot resolve the project root» (REQ-004 provato).
- **Nota onesta (limite del venv workspace):** l'invarianza «stesso verdetto da ogni cwd» vale per il
  **runtime installato** (`.sertor/.venv`, il path reale via `uv run --project .sertor`), dove `index_dir`
  **e** `project_root` si ancorano via `sys.prefix` da qualunque cwd — provato dai unit test. Il workspace
  venv (`.venv`) da sottocartella non trova l'ancora → fail-loud onesto, non un falso verdetto. La consegna
  reale all'utente/dogfood (runtime installato) va verificata LIVE dopo merge + re-lock.
