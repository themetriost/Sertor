# Implementation Plan: Query congiunta multi-collezione & `upsert-index` in CLI

**Branch**: `010-query-congiunta-e-upsert-index` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-query-congiunta-e-upsert-index/spec.md`

## Summary

Due capacità deterministiche residue della feature Wiki (FEAT-003), nello stesso branch:

- **A — Query congiunta multi-collezione**: `RetrievalFacade.search_combined()` oggi interroga una
  sola collezione; la feature aggiunge il **fan-out su più collezioni** (codice + wiki) con **merge
  dei top-k per score**, orchestrato nella facade (porta `VectorStore.query` invariata), governato
  dalla nuova manopola `Settings.extra_corpora` (`SERTOR_EXTRA_CORPORA`). Provider eterogenei tra i
  corpora → `ProviderMismatchError` esplicita (decisione clarify #1), rilevata con la nuova capacità
  di porta `list_collections()`. Default vuoto → comportamento odierno identico.
- **B — `upsert-index` in CLI**: cabla la funzione pura `upsert_index()` (già esistente in
  `wiki_tools/registry.py`) come operazione della CLI `sertor-wiki-tools`, sul modello di
  `append-log` (`--page`, `--summary` o stdin UTF-8), con nuovo contratto versionato
  `UpsertIndexResult` (insert/update/noop) e validazione esplicita del sommario (vuoto/multilinea →
  `ConfigError`).

Decisioni di design in [research.md](research.md) (R1–R8); modello dati in
[data-model.md](data-model.md); contratti in [contracts/](contracts/).

## Technical Context

**Language/Version**: Python >= 3.11 (gestito con `uv`, lockfile `uv.lock`)

**Primary Dependencies**: nessuna nuova. Esistenti: `chromadb` (store locale), `python-dotenv`
(Settings); SDK Azure (`azure-search-documents`) solo nell'extra `azure`, import lazy negli adapter

**Storage**: vector store dietro porta `VectorStore` (Chroma locale di default; Azure AI Search via
`SERTOR_STORE_BACKEND=azure`); indice wiki = file Markdown (`index.md` del wiki dell'ospite)

**Testing**: pytest (suite `not cloud` senza rete, mock in `tests/fixtures/mocks.py`); ruff
(E,F,I,UP,B; line-length 100)

**Target Platform**: libreria Python cross-platform (sviluppo su Windows; CI locale)

**Project Type**: libreria (`sertor-core`) + CLI `sertor-wiki-tools` (entry-point sottile esistente)

**Performance Goals**: nessun target nuovo; il fan-out aggiunge ~1 query vettoriale per corpus extra
(k piccolo, default 5) — trascurabile rispetto alla chiamata di embedding

**Constraints**: estensioni **non-breaking** (firme retro-compatibili); zero LLM; nessuna rete nei
test; nessun nuovo import nel `domain`

**Scale/Scope**: 2 corpora nel caso reale (codice + wiki); il design generalizza a N corpora extra
senza lavoro aggiuntivo (la mappa `corpus → collection` è già una lista)

## Constitution Check

*GATE: superato pre-Phase 0 (2026-06-10) e ri-verificato post-Phase 1 (2026-06-10).*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.1.0).

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** PASS. Il fan-out vive in
  `services/retrieval.py` e dipende solo dalle porte; `ProviderMismatchError` e l'estensione della
  porta stanno nel `domain` (zero SDK); il wiring di `extra_corpora` sta solo in `composition.py`.
  Tutto esercitabile con `FakeEmbedder`/`InMemoryStore`, senza cloud/CLI.
- [x] **II — Boundary & local-first:** PASS. Nessun tipo di terze parti trapela;
  `list_collections()` è implementata da ogni adapter dietro la porta; tutto gira in locale
  (Chroma + mock).
- [x] **III — YAGNI & unità piccole:** PASS. Niente dedup cross-collezione, niente normalizzazione
  score, niente multi-store: ogni astensione è motivata in research (R1, R5). L'estensione della
  porta è giustificata da un requisito presente (FR-009).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** PASS. `ProviderMismatchError` ricca di contesto
  (corpus, collezione attesa, trovate); sommario non valido → `ConfigError`; nessun `None`
  silenzioso (la degradazione morbida su collezione assente è la policy *esistente* della facade,
  documentata e loggata — non un'assenza silenziosa).
- [x] **V — Testabilità & misure:** PASS. Tutto testabile con mock F.I.R.S.T.; la qualità del
  *ranking* fuso non introduce un nuovo spazio di score (stesso provider per costruzione) — le
  misure hit@k/MRR esistenti del motore baseline restano valide; xfail di misura invariati.
- [x] **VI — Idempotenza & non-distruttività:** PASS. Merge deterministico (tie-break per
  `chunk_id`, R5); `upsert_index` resta idempotente (insert/update/noop); nessuna scrittura su
  input non valido.
- [x] **VII — Leggibilità:** PASS. Vocabolario di dominio: *fan-out*, *merge*, *fuse* nel naming
  delle nuove unità.
- [x] **VIII — Configurabilità centralizzata:** PASS. Unico default nuovo: `extra_corpora=()` in
  `Settings` (da `SERTOR_EXTRA_CORPORA`); nessun default hardcodato nei componenti.
- [x] **IX — Osservabilità:** PASS. Evento `retrieve` esteso con `collections` e conteggio fuso
  (R8); warning per collezione degradata; gli esiti CLI già loggano via `log_event("registry",…)`.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS. La manopola è *generica* (`extra_corpora`,
  non "wiki"); nessun percorso/nome dell'ospite nel corpo; il caso dogfood (`wiki`) vive solo nella
  configurazione dell'ospite. La CLI resta governata da `wiki.config.toml`.

## Project Structure

### Documentation (this feature)

```text
specs/010-query-congiunta-e-upsert-index/
├── plan.md              # questo file
├── spec.md              # specifica (con Clarifications 2026-06-10)
├── research.md          # decisioni R1–R8
├── data-model.md        # delta del modello dati/porte/contratti
├── quickstart.md        # come usare le due capacità
├── contracts/
│   ├── combined-search.md   # contratto della ricerca combinata multi-collezione
│   └── cli-upsert-index.md  # contratto del sottocomando CLI
├── checklists/requirements.md
└── tasks.md             # (output di /speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── ports.py             # VectorStore: + list_collections()
│   └── errors.py            # + ProviderMismatchError
├── services/
│   └── retrieval.py         # RetrievalFacade: fan-out multi-collezione + merge top-k
├── adapters/vectorstores/
│   ├── chroma.py            # + list_collections() (client.list_collections)
│   └── azure_search.py      # + list_collections() (list_index_names, lazy)
├── config/
│   └── settings.py          # + extra_corpora (SERTOR_EXTRA_CORPORA)
├── composition.py           # build_facade: deriva e cabla le collezioni extra
└── wiki_tools/
    ├── contracts.py         # + UpsertIndexResult (wiki.upsert_index/1)
    ├── registry.py          # upsert_index -> UpsertIndexResult + validazione sommario
    └── __main__.py          # + op "upsert-index" (--page, --summary | stdin)

tests/
├── fixtures/mocks.py        # InMemoryStore: + list_collections()
└── unit/
    ├── test_retrieval_facade.py   # (esteso) fan-out, merge, degradazione, mismatch
    ├── test_composition.py        # (esteso) wiring extra_corpora
    ├── test_settings.py           # (esteso) parsing SERTOR_EXTRA_CORPORA
    ├── test_wiki_registry.py      # (esteso) UpsertIndexResult + validazione
    └── test_wiki_cli.py           # (esteso) op upsert-index end-to-end su tmp_path
```

**Structure Decision**: nessun modulo nuovo: la feature estende unità esistenti lungo la Clean
Architecture (domain → services → adapters → composition; wiki_tools per la parte B). I nomi reali
dei file di test esistenti vanno verificati in fase tasks (la suite attuale ha 135 test verdi).

## Complexity Tracking

Nessuna violazione da giustificare: il Constitution Check passa su tutti i gate.
