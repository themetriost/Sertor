# Contract — `packaging.verify/1` (verifica di build/install ripetibile)

**Feature**: `047-packaging-distribuibile` | **Date**: 2026-06-17

Contratto della **verifica ripetibile di packaging** (REQ-022). Non è un'interfaccia di rete né una
porta `Protocol`: è il **contratto comportamentale** della suite `tests/integration/test_packaging.py`
(marker `@pytest.mark.integration`). Definisce *input*, *precondizioni*, *check eseguiti*, *esito*, e
*invarianti* — così che chi implementa i task non possa derivare in silenzio. Mappa 1:1 sui requisiti.

> **Confine architetturale.** La verifica usa **solo stdlib** per l'ispezione (`tomllib`, `zipfile`,
> `email.parser`, `configparser`) e **subprocess** per build/install (`uv`, `pip`, `git`). **Non
> importa `sertor_core`** (Principio XI: esercita gli artefatti distribuiti, non la libreria). Gira in
> `tmp_path`/venv effimeri (NFR-2): non tocca il repo ospite (REQ-052).

---

## Input / precondizioni

| Voce | Valore | Requisito |
|------|--------|-----------|
| Workspace | i 4 `pyproject.toml` + `/VERSION` + `LICENSE` presenti | REQ-001, REQ-011 |
| Toolchain | `uv` su PATH; Python ≥ 3.11; `git` su PATH | NFR-1 |
| Rete | GitHub raggiungibile (per `git+url`); **PyPI NON richiesto** per i pacchetti Sertor | NFR-1, REQ-032 |
| Credenziali | **nessuna** credenziale cloud | NFR-1 |

Se una precondizione manca (es. `uv` assente), la verifica **salta in modo esplicito** lo stage
dipendente con messaggio azionabile (`pytest.skip("uv non in PATH")`) — niente falso verde, niente
errore opaco (Principio IV).

---

## Stage 1 — Coerenza statica di metadati e licenza (no build)

**Input:** i 4 `pyproject.toml`, `/VERSION`, i file `LICENSE`. **Costo:** veloce, offline-totale.

| Check | Asserzione | Req | Fail → |
|-------|------------|-----|--------|
| C1.1 licenza presente | `LICENSE` esiste in radice **e** in ogni package dir | REQ-001 | `fail(stage=license, package=…)` |
| C1.2 licenza coerente | `[project].license` == MIT in ogni pkg, e il `LICENSE` è testo MIT | REQ-002 | `fail(stage=license)` |
| C1.3 licenza-senza-testo | se un pkg dichiara `license=MIT` ma manca `LICENSE` → **fail** | REQ-004 | `fail(stage=license)` |
| C1.4 versione allineata | `version` dei 4 (risolta) == contenuto di `/VERSION` | REQ-011, SC-007 | `fail(stage=metadata)` |
| C1.5 requires-python | ogni pkg dichiara `requires-python >= 3.11` | REQ-012 | `fail(stage=metadata)` |
| C1.6 metadati user-facing | `sertor`, `sertor-flow` espongono `name/version/description/authors/license` + `urls` (repository) | REQ-010 | `fail(stage=metadata, package=…)` |
| C1.7 campo mancante | se un campo di C1.6 manca in un user-facing → **fail** | REQ-014 | `fail(stage=metadata)` |
| C1.8 classifiers/keywords (Should) | user-facing dichiarano `classifiers` + `keywords` | REQ-013 | `warn` (Should, non gate) |

---

## Stage 2 — Build dell'artefatto (`uv build`, offline)

**Input:** ogni package distribuibile (4). **Azione:** `uv build` → `<tmp>/dist`. **Costo:** lento,
GitHub/PyPI **non** contattati (build da sorgente locale).

| Check | Asserzione | Req | Fail → |
|-------|------------|-----|--------|
| C2.1 sdist+wheel | per ogni pkg, build produce **sia** `.tar.gz` **sia** `.whl` senza errori | REQ-020, SC-003 | `fail(stage=build, package=…)` exit≠0 |
| C2.2 build error → referto | se la build di un pkg fallisce → identifica il pkg + esce non-zero | REQ-024 | `fail(stage=build, package=…)` |
| C2.3 licenza in wheel | la wheel di ogni pkg contiene `LICENSE` (zipfile) | REQ-003, SC-001 | `fail(stage=wheel-contents)` |
| C2.4 assets in wheel | la wheel di **`sertor`** contiene `assets/**` (package-data) | REQ-021 | `fail(stage=wheel-contents, package=sertor)` |
| C2.5 entry-points dichiarati | la wheel dichiara i console-script attesi (`entry_points.txt`/METADATA): `sertor`→`sertor`; `sertor-flow`→`sertor-flow`; `sertor-core`→`sertor-rag`,`sertor-wiki-tools` | REQ-023 | `fail(stage=entry-points, package=…)` |
| C2.6 metadati in METADATA | la wheel user-facing ha `License`, `Project-URL`, (Should) `Classifier` nei METADATA | REQ-010/013 | `fail(stage=metadata)` |

---

## Stage 3 — Install pulito a un comando (venv effimero)

**Input:** `InterimSource` (`git+url` + `#subdirectory`). **Azione:** install in **venv effimero** sotto
`tmp_path`, poi invoca l'entry-point (`--help`/`--version`). **Costo:** lento, GitHub contattato (clona
il checkout), **PyPI non richiesto** per i pacchetti Sertor.

### 3a — Percorso primario `uv`/`uvx` (GATE)

| Check | Asserzione | Req | Fail → |
|-------|------------|-----|--------|
| C3.1 install sertor | `uvx --from "git+<url>#subdirectory=packages/sertor" sertor --help` rende disponibile l'entry-point | REQ-030 | **fail(stage=clean-install, manager=uv, package=sertor)** |
| C3.2 install sertor-flow | analogo per `sertor-flow` | REQ-031 | **fail(stage=clean-install, manager=uv, package=sertor-flow)** |
| C3.3 deps interne dal workspace | `sertor-core`/`sertor-install-kit` risolti dal checkout, **senza** PyPI | REQ-032 | **fail(stage=clean-install)** |
| C3.4 entry-point invocabile | l'entry-point installato risponde a help/version con **exit 0** | REQ-034, SC-005 | **fail(stage=clean-install)** |
| C3.5 entry-point mancante | se il percorso primario non fornisce un entry-point dichiarato → **fail** identificando pkg+manager | REQ-035 | **fail** |

### 3b — Percorso secondario `pip` (SOFT, best-effort)

| Check | Comportamento | Req |
|-------|---------------|-----|
| C3.6 install pip tentato | `pip install "git+<url>#subdirectory=packages/sertor"` viene **tentato** | REQ-033 |
| C3.7 esito pip | se risolve → asserisce entry-point (bonus). Se **non** risolve le deps di workspace → `xfail(reason="pip non risolve il workspace uv — FEAT-010", strict=False)`, **non** blocca il Must | DA-P2, REQ-035, R-2 |
| C3.8 limite documentato | il limite è dichiarato in `docs/install.md` (non solo nel test) | REQ-040, Decision 3 |

**Invariante DA-P2:** `pip`-workspace è `known-limitation`, mai un rosso che blocca il merge; il
percorso primario `uv` resta l'unico gate dell'install (REQ-035).

---

## Stage 4 — Invarianti preservati (gruppo F)

| Check | Asserzione | Req |
|-------|------------|-----|
| C4.1 install ≠ run | nessuno stage di install avvia ingestione RAG / creazione indice | REQ-050 |
| C4.2 nessun segreto | né i file versionati (`LICENSE`/pyproject) né gli artefatti contengono segreti; la verifica non scrive segreti | REQ-051, SC-009 |
| C4.3 non-distruttivo | la verifica opera in `tmp_path`/venv effimeri; non sovrascrive file dell'ospite | REQ-052 |
| C4.4 host-agnostico | la verifica non assume layout ospite/OS oltre i prerequisiti dichiarati | REQ-053 |

---

## Esito complessivo

- **PASS** ⇔ tutti i check `gate` (Stage 1 hard, Stage 2, Stage 3a, Stage 4) sono verdi; gli Should
  (C1.8) e il `pip` soft (C3.7) possono essere `warn`/`xfail` senza far fallire.
- **FAIL** ⇔ almeno un check gate fallisce; il referto nomina **package + stage (+ manager)** e la
  suite esce non-zero (REQ-024, REQ-035).
- **Determinismo (NFR-1):** stessi input → stesso esito; nessuna dipendenza da stato di macchina (venv
  effimeri), nessuna rete verso PyPI per i pacchetti Sertor, nessuna credenziale.

**Selezione/esecuzione.**
```powershell
uv run pytest -m integration tests/integration/test_packaging.py        # intera verifica
uv run pytest tests/integration/test_packaging.py -k "stage1 or metadata"  # solo statico veloce
```
La verifica **non** entra nella CI unit veloce (`tests/unit`, `-m "not cloud"`): è `integration`
(lenta, rete GitHub). Resta eseguibile localmente e in una CI che accetti `integration`.
