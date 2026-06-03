# Quickstart — Nucleo di retrieval condiviso

Come il nucleo si **installa, configura e usa come libreria**. Riflette il design del piano
([plan.md](plan.md)); i percorsi di codice sono il layout target, non ancora implementato.

## 1. Installazione

```bash
# base: core + backend locale (Chroma) + provider locale (Ollama)
uv pip install sertor-core

# con backend cloud Azure (extra opzionale, NFR-04)
uv pip install "sertor-core[azure]"
```

> Le grammatiche di chunking arrivano con `tree-sitter-language-pack` (wheel precompilati, nessuna
> toolchain C richiesta su Windows/Linux).

## 2. Configurazione (unica, centralizzata)

Tutte le scelte vivono in `Settings`, lette da **env + file** (REQ-030). I segreti **solo** da
env/file non versionato (`.env` in `.gitignore`, REQ-032).

```bash
# --- backend & corpus ---
RAG_BACKEND=local            # local | azure
SERTOR_CORPUS=mio-repo       # namespace della collezione

# --- embeddings (locale) ---
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBED_BATCH_SIZE=64

# --- embeddings (cloud, solo se RAG_BACKEND=azure) ---
# AZURE_OPENAI_ENDPOINT=...
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_EMBED_LARGE_DEPLOYMENT=...

# --- chunking & ingestione ---
CHUNK_SIZE=1600
CHUNK_OVERLAP=200
# EXCLUDE_PATTERNS letta da file di config (lista lunga)
```

Modalità **local-only**: con `RAG_BACKEND=local` nessun adapter cloud è istanziato → **zero** chiamate
di rete cloud (SC-006, REQ-014/022).

## 3. Indicizzare un repository qualunque (repo-agnostico)

```python
from sertor_core.composition import build_indexer

indexer = build_indexer()                 # cablato da Settings
report = indexer.index("/path/al/repo")   # scopre, esclude, chunka, embedda, persiste
print(report.documents, report.chunks)    # conteggi (log strutturati emessi, REQ-031)
```

- Scopre codice + Markdown sotto la radice, **senza** configurazione hardcoded (REQ-001).
- Esclude virtualenv/artefatti/segreti via lista configurabile (REQ-002).
- File illeggibile → warning + skip, prosegue (REQ-003).
- Re-index su corpus invariato → **stessi** chunk id (idempotenza, SC-005).

## 4. Interrogare (facade come libreria)

```python
from sertor_core.composition import build_facade

facade = build_facade()                              # nessun accesso a store/embeddings (REQ-029)

facade.search_code("validazione input", k=5)         # solo codice
facade.search_docs("come configurare il backend")    # solo doc
facade.search_combined("retrieval ibrido", k=6)      # codice + doc
```

Ogni risultato espone `text`, `path`, `chunk_id`, `doc_type`, `score` (REQ-025). Indice vuoto →
lista vuota + warning, **non** eccezione (REQ-028).

## 5. Commutare locale ↔ cloud (solo config)

```bash
# da locale...                      # ...a cloud, senza toccare il codice (SC-002/003)
RAG_BACKEND=local                   RAG_BACKEND=azure
```

Embeddings e vector store cambiano backend dietro le porte: il codice consumatore resta identico.

## 6. Verifica rapida (accettazione)

| Verifica | Atteso | Criterio |
|----------|--------|----------|
| Indicizza 2 repo distinti senza modifiche al codice | nessun errore, due collezioni isolate | SC-001 |
| `RAG_BACKEND=local` | 0 chiamate di rete cloud | SC-006 |
| Re-index stesso corpus | stesso insieme di chunk id | SC-005 |
| Query su corpus campione | `precision@5` ≥ baseline prototipo | SC-004 |
| Ispezione log di index/query | campi: operazione, provider/backend, conteggi, dim, tempi; nessun segreto | SC-007 |

## 7. Per i test (mock, senza cloud né rete)

Il core è esercitabile con adapter mock delle porte (`EmbeddingProvider`, `VectorStore`) — nessun
servizio esterno richiesto (NFR-01):

```python
facade = RetrievalFacade(embedder=FakeEmbedder(dim=8), store=InMemoryStore(),
                         collection="test", default_k=5)
```
