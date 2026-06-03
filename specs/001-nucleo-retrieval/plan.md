# Implementation Plan: Nucleo di retrieval condiviso

**Branch**: `spec/001-nucleo-retrieval` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-nucleo-retrieval/spec.md` (deriva da FEAT-001,
fonte EARS `requirements/sertor-core/nucleo-retrieval/requirements.md`)

## Summary

Il nucleo è la **fondazione production-grade** su cui poggiano tutti i motori RAG (FEAT-002/004/005/006)
e le skill wiki (FEAT-003): legge un repository qualunque, ne chunka codice e documentazione,
produce embeddings via provider intercambiabili, persiste e interroga i chunk via un'astrazione di
vector store, ed espone una **facade di retrieval unica e importabile come libreria**.

L'approccio tecnico estrae e rende production-grade le cinque capacità già dimostrate (in forma
esplorativa e Python-only) nel motore `prototype/shared/`, applicando la **Clean Architecture** della
costituzione: un *core* di entità + porte (astrazioni) senza alcun SDK di provider, *adapter* che
dipendono dalle porte, e un *composition root* che fa il wiring guidato dalla configurazione. Le
decisioni di ambito MVP (14 linguaggi con fallback testuale, full re-index idempotente, locale↔cloud
via config, soglie misurate sul prototipo come baseline) sono già fissate nella spec; questo piano le
traduce in struttura, contratti e modello dati.

## Technical Context

**Language/Version**: Python ≥ 3.11 (vincolo V-4 d'epica).

**Primary Dependencies**:
- *Chunking*: `tree-sitter` (binding) + `tree-sitter-language-pack` (grammatiche precompilate, 305+
  linguaggi, wheel multi-piattaforma) per il chunking sintattico; splitter dimensionale interno per
  il fallback Markdown/testo (nessuna dipendenza pesante per il fallback).
- *Embeddings / vector store*: `httpx` (REST verso Ollama e Azure OpenAI, come nel prototipo);
  `chromadb` (backend locale embedded, default). Backend cloud (Azure AI Search, Cosmos DB for NoSQL)
  dietro **extra opzionali** del pacchetto (NFR-04), non installati di default.
- *Config*: `python-dotenv` + dataclass/`pydantic` per il caricamento centralizzato da env/file.
- *Osservabilità*: logging strutturato su `logging` della stdlib con record arricchiti (no framework
  imposto al chiamante, REQ-031).

**Storage**: file system locale (Chroma embedded + indici namespaced per corpus, `.index-<corpus>`);
backend cloud opzionali. Nessuna persistenza di segreti su path versionati (REQ-032).

**Testing**: `pytest`. Test F.I.R.S.T.; core esercitabile con **provider/store mock** senza cloud né
rete (NFR-01). Test di idempotenza dedicati (NFR-02); misura `precision@k` su corpus con ground-truth.

**Target Platform**: Linux e Windows senza modifiche al codice (NFR-03; il prototipo gira già su
Windows 11). Tree-sitter via wheel precompilati per garantire la portabilità.

**Project Type**: libreria Python importabile (`src/sertor_core/`) — *componente*, non applicazione né
CLI (la CLI è l'epica `sertor-cli`, fuori ambito). Single project.

**Performance Goals**: soglie **non fissate a priori** (DA-003): si misurano in fase di design/test sul
corpus di dogfooding (il prototipo stesso) come baseline. Valori orientativi: retrieval < 2 s su backend
locale (NFR-06); indicizzazione di un repo ≤ 50k LOC in tempo ragionevole misurato (NFR-05).

**Constraints**: local-only senza alcuna chiamata di rete cloud (V-3, REQ-014/016/022); nessun segreto
su file versionati (V-2, REQ-032); il core non dipende da `sertor-cli` (V-1, REQ-029).

**Scale/Scope**: ≥ 2 codebase distinte indicizzabili senza modifiche (SC-001); un solo indice attivo per
corpus alla volta (A-5); corpus di testo (codice + Markdown), no formati binari/non-testo (A-2).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.0.0). Marcare PASS/FAIL;
ogni FAIL va risolto o giustificato in "Complexity Tracking".

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** il design del core non importa SDK di
  provider (LLM/embeddings/vector store) né la CLI; gli adapter dipendono dalle astrazioni del core;
  il wiring sta in un componente main/config. Il core è esercitabile con provider mock, senza cloud/CLI.
  → **PASS.** Layout `domain/` (entità + porte `EmbeddingProvider`/`VectorStore`, errori di dominio) senza
  import esterni; `adapters/` importano gli SDK e implementano le porte; `composition.py` (factory) fa il
  wiring da `Settings`. La facade dipende solo dalle porte. Mock degli adapter nei test.
- [x] **II — Boundary & local-first:** ogni dipendenza esterna è dietro un'astrazione di Sertor;
  scelta locale↔cloud guidata da config; vector store solo dove la modalità lo richiede.
  → **PASS.** Ollama/Azure dietro `EmbeddingProvider`; Chroma/Azure dietro `VectorStore`; default locale,
  cloud via extra opzionali e `Settings`.
- [x] **III — YAGNI & unità piccole:** niente astrazioni/dipendenze senza evidenza presente; SRP/DRY;
  dipendenze pesanti isolabili.
  → **PASS.** Solo le 2 porte richieste dai requisiti (no reranking/grafo: fuori ambito §4). Dipendenze
  cloud e grammatiche pesanti isolate in extra opzionali (NFR-04).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** error handling a eccezioni di dominio; niente
  `None` silenzioso né stato parziale/corrotto.
  → **PASS.** Gerarchia `SertorError` → `IngestionError`/`EmbeddingError`/`VectorStoreError`/`ConfigError`
  con identità+causa+ritentabilità (REQ-015/021). File illeggibile → warning + skip, non None (REQ-003).
  Indice vuoto → risultato vuoto + warning strutturato, non eccezione (REQ-028).
- [x] **V — Testabilità & misure:** test F.I.R.S.T. previsti; core testabile con mock; qualità
  retrieval misurata (hit@k/MRR, baseline=prototipo).
  → **PASS.** Porte mockabili; suite per capacità; idempotenza verificata (SC-005/NFR-02);
  `precision@k` su corpus ground-truth con baseline prototipo (SC-004).
- [x] **VI — Idempotenza & non-distruttività:** re-run stabile (ID stabili); install≠run; nessuna
  sovrascrittura silenziosa.
  → **PASS.** `doc_id` = path relativo (REQ-004); `chunk_id` = `doc_id` + indice posizionale stabile
  (REQ-010); full re-index idempotente (A-4/DA-004); namespacing non distruttivo per corpus (REQ-019).
- [x] **VII — Leggibilità:** naming di dominio (retrieve/rank/fuse/…); commenti solo per l'intenzione.
  → **PASS.** Nomi di dominio: `ingest`/`chunk`/`embed`/`store`/`retrieve`; entità `Document`/`Chunk`/
  `RetrievalResult`.
- [x] **VIII — Configurabilità centralizzata:** scelte (provider/backend/parametri) via config unica,
  nessun default hardcoded.
  → **PASS.** `Settings` unico legge provider/backend/percorsi/chunking/`k`/batch/esclusioni da env+file
  (REQ-030); i componenti ricevono i parametri, non li hardcodano.
- [x] **IX — Osservabilità:** retrieval e creazione embeddings/indicizzazione emettono log strutturati
  (operazione, provider, conteggi, tempi, errori); nessun segreto.
  → **PASS.** Logger strutturato stdlib con campi: operazione, provider/backend, conteggi doc/chunk, dim
  embedding, tempi, errori; redazione segreti (REQ-031/032).

**Esito gate (pre-Phase 0):** ✅ PASS su tutti i 9 principi, inclusi i due NON-NEGOZIABILI (I, IV).
Nessuna violazione → Complexity Tracking vuoto.

## Project Structure

### Documentation (this feature)

```text
specs/001-nucleo-retrieval/
├── plan.md              # Questo file (/speckit-plan)
├── research.md          # Phase 0 — decisioni tecniche e alternative
├── data-model.md        # Phase 1 — entità, campi, regole di stabilità ID
├── quickstart.md        # Phase 1 — come usare il nucleo come libreria
├── contracts/           # Phase 1 — contratti delle porte/facade
│   ├── embedding-provider.md
│   ├── vector-store.md
│   └── retrieval-facade.md
├── checklists/
│   └── requirements.md  # checklist di qualità della spec (già ✅)
└── tasks.md             # Phase 2 (/speckit-tasks — NON creato qui)
```

### Source Code (repository root)

Layout a **Clean Architecture** (Principio I), single project. Le dipendenze puntano verso l'interno:
`adapters` → `domain` ← `services`; il `composition root` è l'unico punto che conosce gli adapter
concreti e la config.

```text
src/sertor_core/
├── domain/                 # CUORE — nessun import di SDK esterni
│   ├── entities.py         # Document, Chunk, RetrievalResult
│   ├── ports.py            # EmbeddingProvider, VectorStore (Protocol/ABC)
│   └── errors.py           # SertorError e sottoclassi di dominio
├── services/               # logica applicativa, dipende solo da domain
│   ├── ingestion.py        # scoperta/lettura/esclusione/doc_id (REQ-001..005)
│   ├── chunking/
│   │   ├── code.py         # tree-sitter, set 14 linguaggi (REQ-006/007/011)
│   │   ├── markdown.py     # confini heading + gerarchia (REQ-008)
│   │   ├── fallback.py     # chunking dimensionale (REQ-009)
│   │   └── dispatch.py     # selezione chunker per linguaggio + chunk_id (REQ-010)
│   └── retrieval.py        # facade: search_code/docs/combined (REQ-023..028)
├── adapters/               # implementano le porte; importano gli SDK
│   ├── embeddings/
│   │   ├── ollama.py       # locale (REQ-013/016)
│   │   └── azure.py        # cloud (REQ-013)
│   └── vectorstores/
│       ├── chroma.py       # locale embedded, default (REQ-018/022)
│       └── azure_search.py # cloud, extra opzionale (REQ-018)
├── config/
│   └── settings.py         # Settings unico, env+file (REQ-030/032)
├── observability/
│   └── logging.py          # logger strutturato + redazione segreti (REQ-031)
└── composition.py          # composition root: Settings -> adapter -> facade

tests/
├── unit/                   # per-capacità, con mock (NFR-01)
├── integration/            # ingest->chunk->embed->store->retrieve end-to-end locale
└── fixtures/               # mini-repo multi-linguaggio + corpus ground-truth (SC-004)
```

**Structure Decision**: scelto il **single project a libreria** con separazione netta
domain/services/adapters/composition. Motivazione: i requisiti chiedono un *componente importabile*
(REQ-029) con porte stabili e sostituibilità degli adapter (NFR-08), e la costituzione impone le
dipendenze verso l'interno (Principio I, non-negoziabile). Niente layout web/mobile (nessun
frontend/backend). La CLI e gli extra di packaging restano fuori (epica `sertor-cli`).

## Complexity Tracking

> Nessuna violazione del Constitution Check: tabella non necessaria.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
