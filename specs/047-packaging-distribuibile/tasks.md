# Tasks — Packaging distribuibile (FEAT-001 epica sertor-cli)

**Branch**: `047-packaging-distribuibile` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Convenzioni: `[P]` = parallelizzabile (file/aree diversi, nessuna dipendenza reciproca). Ogni task
cita i file reali. Gate: il criterio cardine è SC-007 (versione unica) + SC-001 (licenza in wheel) +
SC-004/SC-005 (install pulito + entry-point invocabili via `uv`). REQ citati = gruppi A/B/C/D/E/F
di `spec.md`.

---

## Fase 1 — Setup (fondante, prereq di tutto)

- [ ] **T001** — `VERSION` (NUOVO, radice repo): crea il file con il contenuto `0.1.0` (stringa, newline
  finale). Questo è l'**unico** punto di verità della versione (FR-011, SC-007, NFR-4). [P]

- [ ] **T002** — `pyproject.toml` (radice, `sertor-core`): sostituisci `version = "0.1.0"` con
  `dynamic = ["version"]` sotto `[project]`; aggiungi la sezione:
  ```toml
  [tool.hatch.version]
  path = "VERSION"
  pattern = "^(?P<version>.+?)\\s*$"
  ```
  Verifica che `uv build` (dalla radice) produca ancora sdist+wheel senza errori. [P]

- [ ] **T003** — `packages/sertor/pyproject.toml`: stessa trasformazione di T002 (rimuovi `version`
  statico, aggiungi `dynamic = ["version"]` + `[tool.hatch.version] path = "../../VERSION"`). Verifica
  `uv build --package sertor`. [P rispetto a T004/T005 — file diversi]

- [ ] **T004** — `packages/sertor-flow/pyproject.toml`: stessa trasformazione (path `../../VERSION`).
  Verifica `uv build --package sertor-flow`. [P rispetto a T003/T005]

- [ ] **T005** — `packages/sertor-install-kit/pyproject.toml`: stessa trasformazione (path `../../VERSION`).
  Verifica `uv build --package sertor-install-kit`. [P rispetto a T003/T004]

> **Gate Setup**: dopo T001–T005, `uv build` per tutti e 4 i pacchetti deve riuscire e la versione
> estratta deve coincidere con il contenuto di `VERSION`. Prerequisito obbligatorio per tutte le
> fasi successive.

---

## Fase 2 — User Story 2 · Licenza e metadati (P1)

**Criterio di test indipendente US2**: per ogni prodotto distribuibile, la wheel deve contenere
`LICENSE` (C2.3); i metadati `sertor` e `sertor-flow` devono esporre `name/version/description/
authors/license/urls.Repository` (C1.6); la verifica statica (Stage 1) deve essere tutta verde.
Copertura: FR-001, FR-002, FR-003, FR-004, FR-010, FR-011, FR-013, SC-001, SC-002, SC-007.

- [ ] **T006** — `LICENSE` (NUOVO, radice repo): crea il file con il testo MIT canonico:
  ```
  MIT License

  Copyright (c) 2026 Sertor

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
  ```
  Nessun dato personale/segreto. [P rispetto a T007/T008/T009]

- [ ] **T007** — `packages/sertor/LICENSE` (NUOVO): copia identica di T006. [P]

- [ ] **T008** — `packages/sertor-flow/LICENSE` (NUOVO): copia identica di T006. [P]

- [ ] **T009** — `packages/sertor-install-kit/LICENSE` (NUOVO): copia identica di T006. [P]

- [ ] **T010** — `pyproject.toml` (radice, `sertor-core`): assicura che hatchling includa `LICENSE` nella
  wheel. Aggiorna il campo `license` in `[project]` da `{ text = "MIT" }` a `"MIT"` (espressione SPDX
  PEP 639), oppure mantieni `{ text = "MIT" }` e aggiungi in `[tool.hatch.build.targets.wheel]` la
  voce `include = ["LICENSE"]` (o `force-include = { "LICENSE" = "LICENSE" }`). Verifica con
  `uv build` e ispezione zip della wheel che `LICENSE` sia presente. [P rispetto a T011/T012/T013]

- [ ] **T011** — `packages/sertor/pyproject.toml`: stesso trattamento di T010 per includere
  `packages/sertor/LICENSE` nella wheel di `sertor`; aggiorna `[project].license`; aggiungi:
  ```toml
  [project]
  urls = { Repository = "https://github.com/themetriost/Sertor" }
  classifiers = [
      "License :: OSI Approved :: MIT License",
      "Programming Language :: Python :: 3.11",
      "Programming Language :: Python :: 3.12",
      "Intended Audience :: Developers",
  ]
  keywords = ["rag", "retrieval", "installer", "wiki", "sertor"]
  ```
  (FR-010, FR-013, SC-002). [P rispetto a T010/T012/T013]

- [ ] **T012** — `packages/sertor-flow/pyproject.toml`: stesso trattamento di T011 per `sertor-flow`; stessa
  inclusione `LICENSE`; `urls`, `classifiers`, `keywords` (adatta `keywords` al contesto governance/SDLC:
  `["sdlc", "governance", "speckit", "installer", "sertor"]`). (FR-010, FR-013, SC-002). [P]

- [ ] **T013** — `packages/sertor-install-kit/pyproject.toml`: includi `LICENSE` nella wheel (hatchling
  force-include o `license-files`). Metadati user-facing **ESONERATI** (DA-P4): non aggiungere
  `urls`/`classifiers`/`keywords`. Solo la licenza è obbligatoria anche per i pacchetti interni
  (FR-001, FR-002, FR-003). [P]

---

## Fase 3 — User Story 3 · Suite di verifica (P1)

**Criterio di test indipendente US3**: `uv run pytest -m integration tests/integration/test_packaging.py`
deve essere verde (o con solo `xfail` noti per `pip`); su lacuna introdotta artificialmente (es.
`LICENSE` rimosso) la suite deve fallire nominando package + stage. Copertura: FR-004, FR-014, FR-020,
FR-021, FR-022, FR-023, FR-024, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035, SC-003, SC-004, SC-005,
SC-008, SC-009.

- [ ] **T014** — `tests/integration/test_packaging.py` (NUOVO): implementa la **suite di verifica** secondo
  il contratto `packaging.verify/1` (`contracts/packaging-verification.md`). Struttura obbligatoria:

  **Stage 1 — Coerenza statica** (no build, veloce, offline-totale):
  - `test_license_files_present`: C1.1 — `LICENSE` in radice e in ogni package dir (FR-001, SC-001)
  - `test_license_coherent`: C1.2 — `[project].license` == MIT; testo `LICENSE` è MIT (FR-002)
  - `test_license_without_text_fails`: C1.3 — se package dichiara MIT senza file → fail (FR-004)
  - `test_versions_aligned`: C1.4 — versione dei 4 pyproject (risolta) == contenuto `VERSION` (FR-011,
    SC-007); usa `tomllib` (stdlib Python 3.11+)
  - `test_requires_python`: C1.5 — ogni pkg dichiara `requires-python >= 3.11` (FR-012)
  - `test_user_facing_metadata`: C1.6/C1.7 — `sertor` e `sertor-flow` hanno `name/version/description/
    authors/license` + `urls.Repository` (FR-010, FR-014, SC-002)
  - `test_classifiers_keywords` (Should, C1.8): `sertor`/`sertor-flow` dichiarano `classifiers` +
    `keywords`; fallisce con `pytest.warns` o asserisce senza gate (FR-013)

  **Stage 2 — Build dell'artefatto** (`uv build`, offline):
  - `test_build_produces_artifacts`: C2.1 — per ogni pkg, `uv build` → sdist + wheel senza errori
    (FR-020, SC-003); precondizione: `uv` su PATH → `pytest.skip` esplicito se assente
  - `test_license_in_wheel`: C2.3 — wheel di ogni pkg contiene `LICENSE` (zipfile, FR-003, SC-001)
  - `test_assets_in_sertor_wheel`: C2.4 — wheel di `sertor` contiene `assets/**` (FR-021)
  - `test_entry_points_declared`: C2.5 — wheel dichiara i console-script attesi: `sertor`→`sertor`;
    `sertor-flow`→`sertor-flow`; `sertor-core`→`sertor-rag`,`sertor-wiki-tools` (FR-023, `configparser`
    per `entry_points.txt`)
  - `test_user_facing_wheel_metadata`: C2.6 — METADATA wheel user-facing ha `License`, `Project-URL`
    (`email.parser`, FR-010)
  - `test_build_error_identifies_package`: C2.2 — su build failure → package + stage nominati nel
    messaggio (FR-024)

  **Stage 3a — Install pulito `uv`/`uvx` (GATE)**:
  - `test_clean_install_uv_sertor`: C3.1 — `uvx --from "git+<url>#subdirectory=packages/sertor" sertor
    --help` → exit 0 (FR-030, SC-004); precondizione: GitHub raggiungibile → `pytest.skip` se non lo è
  - `test_clean_install_uv_sertor_flow`: C3.2 — analogo per `sertor-flow` (FR-031, SC-004)
  - `test_entry_points_invocable_uv`: C3.4 — entry-point risponde con exit 0 (FR-034, SC-005)
  - `test_uv_install_failure_identifies_package`: C3.5 — se `uv` non fornisce entry-point → fail con
    pkg + manager (FR-035)

  **Stage 3b — Install `pip` (soft, best-effort)**:
  - `test_clean_install_pip_sertor`: C3.6/C3.7 — tenta `pip install "git+<url>#subdirectory=packages/
    sertor"` in venv effimero; se `pip` non risolve le dipendenze interne → `pytest.xfail(reason="pip
    non risolve il workspace uv — FEAT-010", strict=False)` (DA-P2, FR-033, FR-035, REQ-decision-3)

  **Stage 4 — Invarianti preservati**:
  - `test_no_secrets_in_artifacts`: C4.2 — nessun segreto in `LICENSE`/pyproject/artefatti (FR-051, SC-009)
  - `test_install_does_not_start_indexing`: C4.1 — install non avvia ingestione (FR-050); verificato
    by-construction (solo check testuale/statico)
  - `test_tmp_path_isolation`: C4.3/C4.4 — la verifica opera in `tmp_path`, non tocca file repo (FR-052,
    FR-053)

  **Vincoli implementativi obbligatori** (dal contratto):
  - NESSUN import di `sertor_core` (Principio XI)
  - NESSUN segreto/credenziale nel file (SC-009)
  - stdlib pura per ispezione: `tomllib`, `zipfile`, `email.parser`, `configparser`
  - subprocess per build/install: `uv`, `pip`, `git` — mai import diretti
  - `@pytest.mark.integration` su ogni test o su tutta la classe/modulo
  - Fallback esplicito su precondizione assente: `pytest.skip("uv non in PATH")`, non falso verde

---

## Fase 4 — User Story 4 · Documentazione (P2)

**Criterio di test indipendente US4**: leggere `docs/install.md` deve trovare: (a) comando esatto per
`uv`/`uvx`, (b) comando per `pip` con nota sul limite workspace, (c) dichiarazione "user-facing =
sertor/sertor-flow; dipendenze interne = sertor-core/sertor-install-kit", (d) dichiarazione confine
PyPI → FEAT-006. Copertura: FR-040, FR-041, FR-042, SC-006.

- [ ] **T015** — `docs/install.md` (MOD): aggiorna la sezione `§1. Package installation` (o crea una nuova
  sezione `§0. Distribuzione interim (git+url)` in cima) con:

  **Percorso primario `uv`/`uvx` (gate)**:
  ```powershell
  uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor --help
  uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow --help
  ```

  **Percorso secondario `pip` (best-effort, documentato)**:
  ```powershell
  pip install "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor"
  ```
  Con nota esplicita: `pip` non conosce il workspace `uv` — la risoluzione di `sertor-core` e
  `sertor-install-kit` non è garantita; usa `uv`/`uvx`; ergonomia piena rinviata a FEAT-010.

  **Prerequisiti**: Python >= 3.11; `uv` (raccomandato); rete verso GitHub; nessun account PyPI.

  **Chiarezza sui due insiemi** (FR-041): "I pacchetti a install diretto sono `sertor` (installer
  wiki/RAG) e `sertor-flow` (governance/SDLC). `sertor-core` e `sertor-install-kit` sono dipendenze
  interne, risolte automaticamente dalla sorgente — non si installano direttamente."

  **Confine PyPI** (FR-042): dichiarazione esplicita che la pubblicazione pubblica (PyPI/TestPyPI) è
  fuori ambito (FEAT-006) e che `git+url` è il canale corrente.

---

## Fase 5 — User Story 1 · Install a un comando (P1) e non-regressione

**Criterio di test indipendente US1**: su venv/ambiente effimero, eseguire il comando `uvx --from
"git+<url>#subdirectory=packages/sertor" sertor --help` deve restituire exit 0 e rendere disponibile
l'entry-point. Questo test di accettazione manuale è coperto automaticamente da T014 (Stage 3a).
Copertura: FR-030, FR-031, FR-032, FR-034, SC-004, SC-005.

- [ ] **T016** — Verifica manuale (o esecuzione di Stage 3a della suite T014) su ambiente pulito:
  `uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor --help`
  e analogo per `sertor-flow`. Atteso: exit 0, entry-point disponibile senza passi aggiuntivi.
  (Copertura accettazione US1 / SC-004/SC-005.)

- [ ] **T017** — **Non-regressione**: `uv run pytest -m "not cloud"` verde (tutta la suite unit root — nessuna
  regressione introdotta dalla feature). Nota: la suite di packaging è `integration`, non `cloud`; non
  blocca la CI veloce. (NFR-3, SC-003 transitivo.)

- [ ] **T018** — **Lint**: `uv run ruff check .` verde (nessun errore di lint nella suite `test_packaging.py`
  e nei pyproject toccati). [P con T017]

---

## Fase 6 — Polish / cross-cutting

- [ ] **T019** — `.gitignore` (radice): verifica che gli artefatti di build (`dist/`, `*.whl`, `*.tar.gz`
  temporanei) siano già ignorati o aggiungi le voci mancanti. I file `VERSION` e `LICENSE` sono
  **versionati** (non da ignorare). [P]

- [ ] **T020** — Verifica allineamento `docs/install.md` ↔ `quickstart.md` della feature: i comandi
  documentati in `quickstart.md` (sezione §4) devono essere coerenti con quelli introdotti in `docs/
  install.md` (T015). Nessun path hardcoded di macchina, nessun segreto. [P]

- [ ] **T021** — Ispezione finale della wheel di `sertor` con `zipfile` (manuale o da Stage 2 della suite):
  conferma che `assets/**` sia presente (FR-021, SC-003). Gate di completamento US2/US3.

---

## Grafo delle dipendenze

```
Fase 1: T001 ─┐
              ├─► T002 ─┐
              ├─► T003  │
              ├─► T004  ├─► Fase 2 (T006..T013)
              └─► T005  │
                        │
Fase 2 (T006..T013) ───►├─► Fase 3 (T014) ─► T016 (US1 manuale)
                        │                  └─► T017/T018 (non-regressione)
Fase 4 (T015) ──────────┘
                              Fase 6 (T019..T021) — parallelo a Fase 5
```

Ordine vincolante: Fase 1 → Fase 2 + Fase 4 (parallele tra loro) → Fase 3 → Fase 5 → Fase 6.

**Parallelizzazioni esplicite:**
- T001–T005 (Fase 1): tutti paralleli (file diversi)
- T006–T009 (copie LICENSE): tutti paralleli (file diversi)
- T010–T013 (pyproject per hatchling): tutti paralleli (file diversi)
- T014 (suite) e T015 (docs): paralleli (file diversi)
- T017 e T018 (non-regressione + lint): paralleli

---

## Dipendenze critiche

1. **T001 (VERSION) blocca tutto**: senza il file, i 4 pyproject con `dynamic` falliscono la build.
2. **T002–T005 (pyproject dinamici) bloccano T010–T013 e T014**: la suite Stage 2 dipende da `uv build`
   funzionante con versione dinamica.
3. **T006–T009 (copie LICENSE) bloccano T014 Stage 1 C1.1 e Stage 2 C2.3**: senza file LICENSE, la suite
   fallisce in modo atteso ma il verde richiede che i file siano presenti.
4. **T014 (suite) blocca la verifica formale di US1/US2/US3**: è il gate automatico.
5. **T015 (docs) non blocca T014** ma chiude US4 e SC-006; può procedere in parallelo con la suite.

---

## Strategia MVP / incrementale

**MVP (Fase 1 + 2 + parte Fase 3):**
Passi T001–T013 sono determinici, economici e offline-totali: creano `VERSION`, convertono i 4
pyproject a versione dinamica, creano i 5 file `LICENSE`, aggiornano i metadati user-facing. Dopodiché
T014 Stage 1 (statico) è eseguibile immediatamente per verificare la coerenza senza bisogno di build
reali. Questo da solo chiude US2 (licenza + metadati coerenti) e SC-007 (versione unica).

**Fase build** (T014 Stage 2): dipende da `uv` su PATH; è locale e offline rispetto a PyPI; può essere
eseguito in una seconda sessione o subito dopo il MVP. Chiude US3 parzialmente.

**Fase install** (T014 Stage 3): dipende da GitHub raggiungibile; è il passo più costoso (clona il
checkout). Gate del Must per US1. Da eseguire come verifica finale prima del merge.

**Documentazione (T015)**: basso costo, indipendente; può procedere in parallelo con qualsiasi fase.
