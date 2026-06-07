---
title: Piano SpecKit FEAT-001 — Nucleo di Retrieval Condiviso
type: experiment
tags: [FEAT-001, nucleo-retrieval, spec, architettura, design]
created: 2026-06-03
updated: 2026-06-03
sources: [
  "specs/001-nucleo-retrieval/plan.md",
  "specs/001-nucleo-retrieval/research.md",
  "specs/001-nucleo-retrieval/data-model.md",
  "specs/001-nucleo-retrieval/contracts/",
  ".specify/memory/constitution.md"
]
---

# Piano SpecKit FEAT-001 — Nucleo di Retrieval Condiviso

Sintesi degli artefatti di design generati da SpecKit `/speckit-plan` per [[decomposizione-must-core|FEAT-001]] — il
[[retrieval-core]]: la fondazione production-grade di retrieval, shared da tutti i motori RAG (FEAT-002/004/005/006) e dalle skill wiki (FEAT-003).
*(NB: questo è il design al 2026-06-03; la struttura finale a codice differisce in alcuni nomi — vedi [[retrieval-core]] per l'architettura corrente.)*

## Visione

Il nucleo ingerisce un repository qualsiasi (codice + documentazione), effettua chunking **code-aware su 14 linguaggi MVP** (Python, JS/TS, Java, C#, Go, C/C++, PHP, Ruby, Bash, PowerShell, T-SQL, PL/SQL), produce embeddings via **provider intercambiabili** (Ollama locale / Azure OpenAI), persiste i chunk nel **vector store** (Chroma embedded locale / Azure AI Search optionale), ed espone una **facade di retrieval unica**, importabile come libreria Python.

**Stack:** Python ≥ 3.11 · `tree-sitter` + `tree-sitter-language-pack` (405+ grammatiche precompilate, portabilità Win/Linux) · `httpx` (REST verso LLM/embeddings) · `chromadb` (backend default) · stdlib `logging` (osservabilità strutturata).

## Architettura — Clean Architecture (Principio I vincolante)

### Struttura del codice

```
src/sertor_core/
├─ domain/
│  ├─ entities.py          # Document, Chunk, ChunkMetadata, EmbeddedChunk, RetrievalResult
│  ├─ errors.py            # SertorError (gerarchia), IngestionError, EmbeddingError, VectorStoreError, ConfigError
│  └─ ports/               # Astrazioni (ZERO SDK esterni)
│     ├─ embedding_provider.py    # EmbeddingProvider (embed, dim, name, batch_size)
│     ├─ vector_store.py          # VectorStore (upsert, query, delete, count)
│     └─ chunker.py               # Chunker (chunk_document)
├─ services/
│  ├─ ingestion_service.py        # Ingestione repo, building Document list
│  ├─ chunking_service.py         # Dispatch linguaggio → chunker sintattico/fallback
│  ├─ embedding_service.py        # Batching, retry logic, error handling
│  ├─ vector_store_service.py     # Upsert, queryng facciata
│  └─ retrieval_facade.py         # Facade unica: ingest → retrieve pipeline
├─ adapters/
│  ├─ embeddings/
│  │  ├─ ollama_provider.py       # Ollama REST (locale)
│  │  └─ azure_openai_provider.py # Azure OpenAI REST (cloud, extra opzionale)
│  ├─ vector_stores/
│  │  ├─ chroma_store.py          # Chroma embedded (default)
│  │  └─ azure_search_store.py    # Azure AI Search (extra opzionale)
│  └─ chunkers/
│     ├─ syntactic_chunker.py     # tree-sitter, parametrizzato per linguaggio
│     └─ size_fallback_chunker.py # Dimensionale per fallback / Markdown
├─ config/
│  └─ settings.py                 # Settings dataclass: env + file .env, nessun hardcode
├─ observability/
│  └─ logger.py                   # Logging strutturato stdlib + redazione segreti
└─ composition.py                 # Composition root: factory guidato da Settings
```

### Principi di dominio

1. **Nessun import di SDK di provider nel domain.** Porte + errori di dominio puri.
2. **Adapters dipendono dalle porte** (inversione di controllo). Config → factory → injection.
3. **Idempotenza garantita:** `doc_id` = path relativo POSIX; `chunk_id` = `{doc_id}#{indice_posizionale}`.
4. **Errors as first class.** Gerarchia `SertorError` → sottoclassi specifiche (causa, retriable, messaggio).
5. **No `None` silenzioso.** File illeggibile → warning + skip; indice vuoto → risultato vuoto, non eccezione.

## Decisioni Tecniche (R1–R8)

Consolidate in `specs/001-nucleo-retrieval/research.md`. Estratto:

| Decisione | Risolve | Soluzione MVP |
|-----------|---------|---|
| **R1: Chunking sintattico multilinguaggio** | REQ-006/007/009 | `tree-sitter-language-pack` wheel precompilati (305+ linguaggi, Win/Linux nativo); set MVP: 10 sintattici + 4 fallback (PowerShell, Bash, T-SQL, PL/SQL) al 1° rilascio, migliorabili incrementalmente (REQ-011). Dispatcher parametrizzato per linguaggio. |
| **R2: Astrazione minimale vector store** | REQ-017/019/027 | Porta `VectorStore`: `upsert(chunks, vectors)`, `query(vector, k, filter)`, `delete(ids)`, `count()`. Namespacing per collezione = `{corpus}-{provider}-{dim}`, non directory separate. Backend: Chroma embedded (default), Azure AI Search (extra opzionale). |
| **R3: Provider embeddings intercambiabili** | REQ-012/013/014/015/016 | Porta `EmbeddingProvider`: `embed(texts) -> list[vector]`, proprietà `dim`/`name`/`batch_size`. Adapter: Ollama (REST locale), Azure OpenAI (REST cloud, extra). Local-only via config (`RAG_BACKEND=local`). Errori strutturati (`EmbeddingError` retriable). |
| **R4: ID stabili & idempotenza** | REQ-004/010, NFR-02 | `doc_id` = path relativo POSIX dalla radice repo; `chunk_id` = `{doc_id}#{ordinale}` stabile. Re-run → stessi ID → idempotenza (già testata nel prototipo). Mitiga rischio R-N3. |
| **R5: Osservabilità strutturata** | REQ-031, Principio IX | Logging `stdlib` con record arricchiti (path, linea, severity); redazione segreti (no API key nei log). Nessun framework imposto al chiamante. |
| **R6: Configurazione centralizzata** | REQ-030/032, Principio VIII | `Settings` dataclass unica (env + file `.env`). Parametri provider, backend, percorsi, chunking, batch, esclusioni. Nessun segreto su file versionati. |
| **R7: Extra opzionali & import lazy** | NFR-04, rischio R-N4 | Base locale (Chroma + Ollama) senza dipendenze cloud. Azure SDK installato solo se extra `[azure]` attivo; import lazy. Evita conflitto dipendenze con CLI. |
| **R8: Soglie performance/qualità misurate** | SC-004, NFR-05/06, DA-003 | Baseline = prototipo (corpus dogfooding, 57 doc, 670 chunk): retrieval < 2 s, precision@5 ≈ 0.67 locale. Soglie non fissate a priori; misurate in fase design/test. |

## Modello Dati

Entità di dominio in `specs/001-nucleo-retrieval/data-model.md`:

- **`Document`:** File ingerito (code | doc), `id` = path relativo, `language` rilevato, `text` UTF-8.
- **`Chunk`:** Porzione indicizzabile, `id` = `{doc_id}#{ordinale}`, `metadata` strutturale (simbolo, riga, node_type, heading_path).
- **`EmbeddedChunk`:** Record nel vector store (chunk_id, vettore, payload metadati, collezione).
- **`RetrievalResult`:** Hit di ricerca (chunk, score, metadati contextualizzati).
- **`ChunkMetadata`:** Strutturata diversamente per codice (symbol, qualname, start_line, node_type) vs Markdown (heading_path).

## Constitution Check (Principio I + IV NON-NEGOZIABILI)

✅ **PASS** su tutti e 9 i principi della [[costituzione-v1|Costituzione di Sertor v1.0.0]]:

- **I — Dipendenze verso l'interno (✅ NON-NEGOZIABILE):** Domain puro (no SDK provider); adapters dipendono da porte; composition.py wiring via config. Core mockabile senza cloud/CLI.
- **II — Boundary & local-first:** ✅ Ollama/Azure dietro porta; Chroma/Azure dietro porta; default locale, cloud via extra.
- **III — YAGNI:** ✅ Solo 2 porte richieste dai requisiti; no reranking/grafo (FEAT-002/003).
- **IV — Errori espliciti (✅ NON-NEGOZIABILE):** Gerarchia `SertorError` con identità+causa+retriable; no `None` silenzioso; indice vuoto → risultato vuoto, non eccezione.
- **V — Testabilità:** ✅ Porte mockabili; test F.I.R.S.T. previsti; precision@k misurata su corpus ground-truth.
- **VI — Idempotenza & non-distruttività:** ✅ ID stabili; full re-index idempotente; namespacing non distruttivo per corpus.
- **VII — Leggibilità:** ✅ Nomi di dominio (ingest, chunk, embed, retrieve); naming chiaro.
- **VIII — Configurabilità centralizzata:** ✅ `Settings` unico, no hardcode; scelte provider/backend via config.
- **IX — Osservabilità:** ✅ Logging strutturato stdlib; no framework imposto.

**Complexity Tracking:** vuoto (nessuna violazione).

## Contratti del Design

Specifici in `specs/001-nucleo-retrieval/contracts/`:

- **`embedding_provider.py`:** `async embed(texts: list[str]) -> list[list[float]]`, proprietà `dim`/`name`/`batch_size`, errore `EmbeddingError`.
- **`vector_store.py`:** `upsert(ids, vectors, payloads)`, `query(vector, k, filter)`, `delete(ids)`, `count(collection)`.
- **`chunker.py`:** `chunk_document(doc: Document) -> list[Chunk]` sintattico/fallback per linguaggio.

## Scope MVP vs Post-MVP

**MVP (FEAT-001/002):**
- Ingestione repo-agnostica (REQ-001/002/003).
- Chunking 14 linguaggi (10 sintattico, 4 fallback).
- Embeddings Ollama locale (defalt).
- Vector store Chroma embedded.
- Full re-index idempotente.
- Facade + test.

**Post-MVP (FEAT-004/005/006/007, backlog):**
- Estensione linguaggi (PowerShell, Bash, T-SQL, PL/SQL sintattico).
- Re-index incrementale (FEAT-009, soddisfa sorgenti dinamiche FEAT-007).
- Formati non-testo (PDF, DOCX).
- Reranking, ibrido, grafo, agentico.

## Dipendenze e Compatibilità

- **Min Python:** 3.11 (vincolo EARS V-4).
- **tree-sitter-language-pack:** wheel precompilati, Python 3.9–3.13, Py311 supported.
- **httpx:** REST REST per Ollama/Azure, versione ≥ 0.24.
- **chromadb:** embedded, nessun server esterno locale (default).
- **Azure SDK** (opzionale via extra `[azure]`): `azure-search-documents`, `azure-identity`, `openai` (Azure OpenAI); lazy import evita conflitti con CLI.

## Linkage al Workflow di Produzione

- **Confine con FEAT-002:** FEAT-001 consegna la facade di ingestione+retrieval; FEAT-002 aggiunge ranking/valutazione pertinenza.
- **Confine con FEAT-003:** FEAT-001 alimenta il RAG di wiki (indice corpus_wiki + provider config).
- **Confine con sertor-cli:** CLI importa la libreria sertor_core, non dipende da adapters Azure (via extra).
- **Constitution gate:** Phase 0 research PASS ✅; Phase 1 design re-check dopo implementation spike.

## Prossimi Step

1. **Implmenetazione Phase 2:** codifica domain + adapters locali (Ollama, Chroma), composition root.
2. **Test Phase 2:** F.I.R.S.T. + idempotenza + precision@5 baseline prototipo.
3. **Revisione Constitution:** gate PASS post-Phase 1 prima di merge.
4. **Integrazione FEAT-002:** connettore baseline retrieval (BM25 / ranking).
