# Implementation Plan: la registrazione copre un changeset, non una data

**Branch**: `124-copertura-changeset-scan` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/124-copertura-changeset-scan/spec.md`

## Summary

`scan` azzera `pending` per la **sola presenza** della partizione di giornale di oggi fra le modifiche
non consegnate (`scan.py:286-292`, `recorded_today`). Otto scenari misurati di lavoro non registrato
riportano `0`; un nono difetto, indipendente, fa degradare **in silenzio** verso l'insieme vuoto ogni
invocazione git fallita, mentre l'esito continua a dichiarare `anchor_kind: "git"`.

**Approccio:** sostituire *presenza* con **copertura**. `append-log` **deriva** l'insieme di elementi
che la voce copre — al momento della scrittura, dallo stato reale del progetto — e lo persiste **dentro
la voce stessa**; `scan` calcola `pending = lavoro_in_perimetro − copertura`. La **data sparisce dalla
logica**: una voce di ieri è semplicemente una voce che non copre nulla di nuovo. In parallelo, ogni
fallimento di determinazione viene **dichiarato** in un campo additivo invece di produrre un «pulito».

## Technical Context

**Language/Version**: Python 3.11+ (`sertor-core`); asset hook Python **stdlib-only** (girano via
`uv run --no-project`).

**Primary Dependencies**: nessuna nuova. Solo `git` come processo esterno (già usato da
`wiki_tools/vcs.py`) e stdlib.

**Storage**: il **giornale stesso** (`wiki/log/YYYY-MM-DD.md`). Nessun file di stato nuovo, nessun
database — la copertura vive nell'artefatto che descrive (vincolo del Principio XIV).

**Testing**: `pytest`. Suite root `tests/unit/test_wiki_tools_scan*.py` (esistenti, da estendere) +
suite `packages/sertor/tests` per gli asset host-facing. Matrice comportamentale già scritta come
strumento di misura.

**Target Platform**: host-agnostico — Windows/macOS/Linux, progetti con e **senza** sistema di
versionamento, assistenti Claude e Copilot.

**Project Type**: libreria + CLI (`sertor-wiki-tools`) + asset distribuiti (hook, playbook).

**Performance Goals**: costo end-to-end di `scan` entro **+15%** del riferimento misurato (~330 ms,
7 spawn di git), perché è pagato a **ogni fine turno** (SC-008).

**Constraints**:
- **`wiki.scan/1` NON si bumpa** — i due hook consumatori la confrontano per uguaglianza e vanno in
  **fail-open**: un bump non romperebbe il gate, lo farebbe **sparire in silenzio** sugli ospiti non
  aggiornati. Solo campi **additivi**.
- Offline, deterministico, zero LLM (confine D↔N invariato).
- `append-log` e il playbook sono **host-facing** → regola «installabile su un ospite» + regola
  «documentazione utente nello stesso step».

**Scale/Scope**: giornali reali di ~500 righe/giorno; insiemi di copertura da 1 a ~50 elementi per
voce. Un ospite osservato ne ha otto progetti sullo stesso host.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno:** **PASS.** Tutto dentro `sertor_core/wiki_tools/`, che non
  importa SDK di provider. Nessun contatto con embeddings/vector store.
- [x] **II — Boundary & local-first:** **PASS.** L'unica dipendenza esterna è `git`, già dietro
  `wiki_tools/vcs.py`. Nessuna rete.
- [x] **III — YAGNI & unità piccole:** **PASS.** Nessuna astrazione nuova: si **estende** il calcolo
  esistente e si **riusa** il parser d'intestazione già scritto. La granularità `(path, blob)` è
  giustificata da un requisito (FR-011) e da un costo misurato, non da simmetria.
- [x] **IV — Errori espliciti:** **PASS.** È il cuore della Storia 2: si **rimuove** un ritorno
  silenzioso di insieme vuoto e lo si sostituisce con una condizione dichiarata.
- [x] **V — Testabilità & misure:** **PASS.** SC-001/002 sono verificabili contro **misure già prese**
  (matrice di 15 scenari + 3 race). I test si scrivono **prima** (vedi Fase 2).
- [x] **VI — Idempotenza & non-distruttività:** **PASS.** `scan` resta sola lettura; `append-log`
  resta append-only. Ri-eseguire `scan` sullo stesso stato dà lo stesso esito (non dipende più da
  orologi **né** dal fatto che il giornale risulti «toccato»).
- [x] **VII — Leggibilità:** **PASS.** Nomi di dominio: *copertura*, *lavoro in perimetro*,
  *determinazione*. Il commento spiega **perché** due enumerazioni sono separate, non cosa fa il codice.
- [x] **VIII — Configurabilità centralizzata:** **PASS.** Nessun default nuovo hardcodato; il perimetro
  continua a venire da `wiki.config.toml`.
- [x] **IX — Osservabilità:** **PASS.** L'evento `scan` esistente si estende con l'esito della
  determinazione (metrics-only, nessun contenuto, nessun segreto).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS.** Nessun percorso cablato; il blocco di
  copertura usa path **relativi al progetto**; il ripiego per progetti senza versionamento resta e
  continua a dichiarare la causa tipizzata.
- [x] **XI — Consumo via vehicles:** **PASS.** I consumatori restano CLI e hook; nessun import diretto
  di `sertor_core` fuori dai test. `append-log` **non** chiama `scan` via subprocess: entrambi sono
  funzioni della stessa libreria, e la composizione avviene **dentro** il vehicle.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS.** Si rimuove la causa (l'azzeramento globale), non si
  silenzia il sintomo. Il degrado resta ammesso **solo** dichiarandolo (FR-006/007).
- [x] **XIII — Product Plane vs. Fixture Plane:** **PASS.** Cerimonia **acuta**, perché il prodotto
  **scrive stato nell'asset** che il dogfood usa: il nostro giornale acquisirà blocchi di copertura.
  La decisione di formato è giustificata dal **caso ospite** (un giornale leggibile e verificabile da
  chi lo riceve), non dalla comodità del dogfood. La transizione delle voci esistenti (Q1/C) è una
  **decisione di prodotto** registrata nella spec, non un aggiustamento di fixture.
- [x] **XIV — Derived State, Not Declared:** **PASS, ed è il principio guida.** La copertura è
  **derivata** dallo stato reale al momento della scrittura, mai chiesta a chi scrive. Dove la
  derivazione è impossibile — le voci **preesistenti**, che nessuno può retro-derivare — non si finge:
  si applica una regola di compatibilità **e la si dichiara** nell'esito (`legacy_coverage`), che è il
  «riconciliatore nominato» richiesto dal principio.
- [x] **Allineamento alla missione:** **PASS.** La missione è **contesto dell'agente sempre reale**. Un
  gate che smette di vedere il lavoro lascia il wiki alla deriva, e il wiki è metà del corpus fuso
  code+doc: questa feature protegge la **freschezza** del lato documentale, che è esattamente la
  qualità resa all'agente.

**Esito gate: 14/14 PASS + missione PASS.** Nessuna voce in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/124-copertura-changeset-scan/
├── plan.md              # questo file
├── spec.md              # /speckit-specify
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   ├── wiki.scan.1.md          # campi additivi, stringa di schema invariata
│   └── sertor-covers.1.md      # formato del blocco di copertura nella voce
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── scan.py          # copertura al posto di recorded_today; determinazione dichiarata
├── registry.py      # append_log: deriva e persiste la copertura
├── coverage.py      # NUOVO: parsing/serializzazione del blocco, unione delle coperture
├── vcs.py           # + identità di contenuto (un solo spawn per N path)
└── contracts.py     # ScanResult: campi additivi

tests/unit/
├── test_wiki_tools_scan_git.py       # esteso: gli 8 scenari + le non-regressioni
├── test_wiki_tools_coverage.py       # NUOVO: unità del formato e dell'unione
└── test_wiki_tools_log_rotation.py   # non-regressione append-log

packages/sertor/src/sertor_installer/assets/claude/
├── hooks/wiki-guard.py               # non tratta come «pulito» una determinazione fallita
├── hooks/wiki-pending-check.py       # idem, non bloccante
└── skills/wiki-author/wiki-playbook.md   # formato della voce: documenta il blocco

docs/                                  # regola 3: documentazione utente nello stesso step
```

**Structure Decision**: singolo progetto, estensione di un modulo esistente. La sola unità nuova è
`coverage.py`, che isola il **formato** (serializza/parsa/unisce) da chi lo **usa** (`scan` legge,
`append_log` scrive): senza quella separazione le due parti si scambierebbero il presupposto — il
difetto che questa feature chiude.

## Complexity Tracking

> Nessuna violazione del Constitution Check: tabella non compilata.
