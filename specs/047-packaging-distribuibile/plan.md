# Implementation Plan: Packaging distribuibile (distribuzione interim `git+url`)

**Branch**: `047-packaging-distribuibile` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/047-packaging-distribuibile/spec.md` +
`requirements/sertor-cli/packaging-distribuibile/requirements.md` (FEAT-001, epica `sertor-cli`).

## Summary

Rende i 4 pacchetti del monorepo Sertor **distribuibili in modo coerente e verificato** via la
**distribuzione interim `git+url`** (no PyPI, FEAT-006). Tre lacune chiuse: (1) **licenza** — un file
`LICENSE` MIT in radice e in ogni package, incluso nelle wheel, coerente coi metadati; (2)
**versione+metadati** — una **versione unica** da `/VERSION` (letta dinamicamente dai 4 pyproject) e
metadati completi (`urls`/`classifiers`/`keywords`) per i due pacchetti user-facing (`sertor`,
`sertor-flow`); (3) **verifica ripetibile** — una suite pytest `@integration`
(`tests/integration/test_packaging.py`) che prova licenza+metadati (statico), build sdist+wheel
(`uv build`) e install pulito a un comando in venv effimero per `uv`/`uvx` (gate) e `pip` (best-effort).
Più la **documentazione** del percorso install (`docs/install.md`) coi due gestori e il confine PyPI
esplicito. Approccio tecnico risolto in Phase 0: versione = file unico letto da `[tool.hatch.version]`;
verifica = pytest stdlib+subprocess senza import di `sertor_core`; `pip`-workspace = limite documentato
(`xfail`) rinviato a FEAT-010.

## Technical Context

**Language/Version**: Python ≥ 3.11 (baseline progetto; ambiente locale Python 3.14.5, `uv 0.11.12`).

**Primary Dependencies**: nessuna nuova dipendenza runtime. Build backend **hatchling** (già in uso,
`requires = ["hatchling"]` ×4); gestori d'installazione **`uv`/`uvx`** (primario) e **`pip`**
(secondario). Verifica: **stdlib** (`tomllib`, `zipfile`, `email.parser`, `configparser`, `subprocess`).

**Storage**: N/A (nessuno storage runtime). Artefatti = `sdist`/`wheel` in dir temporanee di build;
fonte di verità versione = file `/VERSION` versionato.

**Testing**: pytest (marker `integration` già definito in `pyproject.toml`). Verifica di packaging =
`tests/integration/test_packaging.py`, **esclusa** dalla CI unit veloce (`tests/unit`, `-m "not cloud"`).

**Target Platform**: cross-platform (Windows/POSIX); la verifica usa `tmp_path`/venv effimeri e non
assume layout ospite (host-agnostico).

**Project Type**: monorepo `uv workspace` con 4 pacchetti (`sertor-core` root + `sertor`,
`sertor-install-kit`, `sertor-flow` in `packages/`); build hatchling per ciascuno.

**Performance Goals**: N/A funzionale. Vincolo operativo: la verifica è **deterministica** e
**offline rispetto a PyPI** per i pacchetti Sertor (NFR-1); la build/install reali sono lente → marker
`integration`, non in CI veloce.

**Constraints**: NFR-1 (ripetibile, no rete PyPI, no credenziali cloud) · NFR-2 (install in env
isolato) · NFR-3 (non-regressione: suite esistente verde) · NFR-4 (versione = unica fonte di verità)
· NFR-5 (doc portabile). Confini: no pubblicazione pubblica (FEAT-006), no versioning da tag, no
ergonomia avanzata `pip`/installer (FEAT-010).

**Scale/Scope**: 4 pacchetti, 2 user-facing; ~5 file `pyproject.toml`+`VERSION`+`LICENSE` toccati,
1 nuova suite di test, aggiornamento di `docs/install.md`. Nessuna modifica al runtime del core.

## Constitution Check

*GATE: superato PRIMA di Phase 0 e RI-VERIFICATO dopo Phase 1.* Gate dalla costituzione v1.2.0
(`.specify/memory/constitution.md`).

> **Natura della feature.** È una feature di **packaging/build/verifica/documentazione**, non di
> runtime RAG: non introduce entità di dominio, porte, adapter, motori, né tocca `composition.py`. La
> maggior parte dei principi è quindi soddisfatta *per non-applicabilità* (la feature non aggiunge SDK,
> non aggiunge retrieval, non emette log runtime). I principi *load-bearing* qui sono **III** (YAGNI),
> **IV** (errori espliciti = limiti non nascosti), **VI** (idempotenza/install≠run/non-distruttività),
> **X** (host-agnostico) e **XI** (no import diretto di `sertor_core` nella verifica). Sicurezza/segreti.

### Pre-design (dopo lettura spec+requirements)

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS — non si tocca il core; nessun nuovo
  import di SDK provider. La verifica esercita gli *artefatti distribuiti*, non aggiunge dipendenze al
  core (la libreria resta importabile e mock-testabile com'è).
- [x] **II — Boundary & local-first:** PASS (N/A) — nessuna dipendenza esterna runtime introdotta;
  nessun vector store. La verifica gira interamente in locale (no cloud).
- [x] **III — YAGNI & unità piccole:** PASS — soluzione versione = file unico + `[tool.hatch.version]`
  (backend già in uso, zero dipendenze nuove), **scartati** bump2version/hatch-vcs/script di sync
  (over-engineering). Verifica = stdlib, niente `pkginfo`/`build`/`twine`.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS — il limite `pip`-workspace è **dichiarato**
  (`xfail` con motivo + nota in `docs/install.md`), non un null silenzioso (Decision 3). Precondizioni
  mancanti → `skip` esplicito azionabile, non falso verde. Build error → referto con package+stage.
- [x] **V — Testabilità & misure:** PASS — la verifica È il test (F.I.R.S.T.: deterministica,
  indipendente in venv effimeri, ripetibile, self-validating). Metrica retrieval (hit@k/MRR) **N/A**
  (feature di packaging, non di qualità retrieval).
- [x] **VI — Idempotenza & non-distruttività:** PASS — `install ≠ run` preservato (REQ-050); la
  verifica opera in `tmp_path`/venv effimeri, non sovrascrive file ospite (REQ-052); ribuildare/
  reinstallare è stabile.
- [x] **VII — Leggibilità:** PASS — la suite usa nomi di intento (`test_license_in_wheel`,
  `test_versions_aligned`, `test_clean_install_uv`), guard clause/early skip.
- [x] **VIII — Configurabilità centralizzata:** PASS (N/A) — nessuna scelta operativa di runtime;
  la "config" toccata sono i metadati di packaging, per natura dichiarativi nei pyproject.
- [x] **IX — Osservabilità:** PASS (N/A) — nessuna operazione runtime nuova da loggare; la verifica
  produce un referto di test (package+stage) leggibile, non log di prodotto.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — packaging e verifica non assumono layout/OS
  dell'ospite oltre i prerequisiti dichiarati (REQ-053); install in env effimero, `docs/install.md`
  portabile (no path di una singola macchina).
- [x] **XI — Consumo via vehicles:** PASS — la verifica **non importa `sertor_core`**: ispeziona
  metadati/wheel via stdlib e build/install via subprocess `uv`/`pip`. (Non c'è runtime RAG da
  consumare; la regola è rispettata per costruzione.)

**Esito pre-design: PASS 11/11, nessuna deroga.**

### Post-design (dopo Phase 1 — research/data-model/contracts/quickstart)

Riconfermato dopo aver fissato il design: file `/VERSION` + `[tool.hatch.version]` (III); suite a 3
stage stdlib+subprocess, `pip` soft `xfail` documentato (IV); referto con package+stage (IV/VII);
nessun import di `sertor_core` nel contratto di verifica (XI); env effimeri/`tmp_path` (VI/X). Nessuna
nuova porta, adapter o modifica a `composition.py`/servizi → I/II/VIII/IX restano N/A-PASS. **Nessuna
violazione introdotta dal design.**

**Esito post-design: PASS 11/11, nessuna deroga.** "Complexity Tracking" non compilato (nessuna
violazione da giustificare).

## Project Structure

### Documentation (this feature)

```text
specs/047-packaging-distribuibile/
├── spec.md              # input (già presente)
├── plan.md              # questo file
├── research.md          # Phase 0 — 3 incognite risolte
├── data-model.md        # Phase 1 — entità di packaging (no runtime)
├── quickstart.md        # Phase 1 — bump/verifica/install
├── contracts/
│   └── packaging-verification.md   # contratto packaging.verify/1
└── checklists/          # (preesistente)
```

### Source Code / artifacts (repository root)

```text
Sertor/
├── VERSION                       # NUOVO — unica fonte di verità della versione
├── LICENSE                       # NUOVO — testo MIT (radice)
├── pyproject.toml                # MOD — version dinamica da VERSION; (consigliati urls/classifiers per core)
├── docs/
│   └── install.md                # MOD — comando ×2 gestori, confine PyPI, limite pip
├── packages/
│   ├── sertor/
│   │   ├── LICENSE               # NUOVO (copia MIT)
│   │   └── pyproject.toml         # MOD — version dinamica; urls/classifiers/keywords (user-facing)
│   ├── sertor-flow/
│   │   ├── LICENSE               # NUOVO (copia MIT)
│   │   └── pyproject.toml         # MOD — version dinamica; urls/classifiers/keywords (user-facing)
│   └── sertor-install-kit/
│       ├── LICENSE               # NUOVO (copia MIT)
│       └── pyproject.toml         # MOD — version dinamica (metadati user-facing ESONERATI, DA-P4)
└── tests/
    └── integration/
        └── test_packaging.py     # NUOVO — suite di verifica (stage 1-4 del contratto)
```

**Structure Decision**: la feature è **a livello di repository/packaging**, non di modulo `src/`.
Tocca i metadati dichiarativi dei 4 `pyproject.toml`, aggiunge i file `VERSION`/`LICENSE`, una suite di
test `integration` nella root (`testpaths = ["tests"]`, dove vivono già gli altri end-to-end), e la
guida `docs/install.md`. **Nessuna modifica** a `src/sertor_core/**`, alle porte, agli adapter o a
`composition.py`: il runtime del core resta invariato (NFR-3). La copia del `LICENSE` per-package
risolve la collocazione hatchling (la wheel di ciascun pacchetto deve includere il proprio testo).

## Implementation Notes (non-binding, per `/speckit-tasks`)

Ordine suggerito, dal più economico/fondante al più costoso:
1. **Versione unica** — crea `/VERSION`; converti i 4 `[project].version` in `dynamic = ["version"]` +
   `[tool.hatch.version] path` (radice + `../../VERSION` per i membri). Verifica `uv build` ×4 ancora OK.
2. **Licenza** — crea `/LICENSE` (MIT, `Copyright (c) 2026 Sertor`) + copia in ogni package; assicura
   l'inclusione nella wheel (PEP 639 `license-files` o force-include); coerenza `[project].license`.
3. **Metadati user-facing** — `urls.Repository`, `classifiers`, `keywords` su `sertor` e `sertor-flow`
   (Should ma a basso costo); `sertor-core` consigliato. `sertor-install-kit` esonerato (DA-P4).
4. **Suite di verifica** — `tests/integration/test_packaging.py` secondo il contratto (stage 1 statico
   → 2 build → 3a uv gate → 3b pip soft → 4 invarianti). stdlib+subprocess, niente import di
   `sertor_core`, niente segreti.
5. **Documentazione** — `docs/install.md`: comando esatto ×2 gestori, prerequisiti, nota limite `pip`
   (→ FEAT-010), dichiarazione "user-facing = sertor/sertor-flow; sertor-core/install-kit = interni",
   confine PyPI esplicito (→ FEAT-006).
6. **Non-regressione** — `uv run pytest -m "not cloud"` e `uv run ruff check .` verdi.

## Out-of-Scope tracking (promozione, NON sepoltura)

Voci rinviate da questa feature, già con casa durevole (nessuna nuova casa da creare):
- **Pubblicazione pubblica PyPI/TestPyPI + hardening supply-chain (firma/provenance/SBOM)** → **FEAT-006**
  (epica `sertor-cli`, Won't qui). Citata, non duplicata.
- **Ergonomia piena di `pip` (risoluzione workspace) + multi-target/portabilità installer** → **FEAT-010**
  (Could). Il limite `pip`-workspace è *documentato* qui e *risolto* lì.
- **Lifecycle `upgrade`/`uninstall`** → **FEAT-008**. **Wizard config provider** → **FEAT-003**.
- **Versioning automatico da git tag** = materia di *design* (Won't); il file `/VERSION` qui è il
  meccanismo manuale documentato, non preclude il tag-driven futuro.

> Nessun rinvio reale vive solo dentro `specs/047-…/`: tutti mappano su FEAT esistenti dell'epica
> `sertor-cli`. Nessuna riga nuova da aggiungere al backlog o alla roadmap per questa feature.
