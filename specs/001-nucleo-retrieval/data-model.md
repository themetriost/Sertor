# Phase 1 — Data Model: Nucleo di retrieval condiviso

Entità di dominio del nucleo (in `src/sertor_core/domain/entities.py`), derivate dalle *Key Entities*
della spec e dai requisiti EARS. Nessuna entità importa SDK esterni (Principio I). I tipi indicati sono
orientativi (dataclass frozen dove l'immutabilità aiuta la stabilità degli ID).

---

## Document

Unità ingerita da un repository: un file di codice o documentazione.

| Campo | Tipo | Vincoli / Note | Requisito |
|-------|------|----------------|-----------|
| `id` | `str` | **Stabile**: path relativo POSIX dalla radice del repo. Univoco nel corpus. | REQ-004 |
| `text` | `str` | Contenuto testuale letto in UTF-8 (`errors="ignore"`). | REQ-001 |
| `path` | `str` | = `id` (path relativo); ridondante per leggibilità nei metadati. | REQ-005 |
| `doc_type` | `enum {code, doc}` | Tipo di documento. | REQ-005 |
| `language` | `str` | Linguaggio di programmazione (es. `python`) o markup (`markdown`). Rilevato da estensione. | REQ-005 |

**Regole.**
- File che matchano la lista di esclusione configurabile **non** diventano `Document` (REQ-002).
- File illeggibili → **nessun** `Document`, ma warning strutturato (path+causa) e prosecuzione (REQ-003).
- Repo senza file indicizzabili → lista di `Document` vuota, **senza** errore (edge case spec).

---

## Chunk

Porzione indicizzabile di un `Document`: unità sintattica (codice), sezione (Markdown) o finestra
dimensionale (fallback).

| Campo | Tipo | Vincoli / Note | Requisito |
|-------|------|----------------|-----------|
| `id` | `str` | **Stabile**: `f"{document_id}#{index}"`, `index` = ordinale posizionale nell'ordine di emissione. | REQ-010 |
| `document_id` | `str` | FK → `Document.id`. | REQ-010 |
| `text` | `str` | Testo del chunk (per i metodi include il contesto di classe in testa). | REQ-006 |
| `doc_type` | `enum {code, doc}` | Ereditato dal documento; usato come filtro retrieval. | REQ-027 |
| `metadata` | `ChunkMetadata` | Metadati strutturali (sotto). | REQ-007/008 |

### ChunkMetadata (per codice — REQ-007)

| Campo | Tipo | Note |
|-------|------|------|
| `path` | `str` | Path relativo del file sorgente. |
| `qualname` | `str \| None` | Nome qualificato dell'unità (es. `Classe.metodo`). |
| `symbol` | `str \| None` | Nome del simbolo. |
| `node_type` | `enum {function, class, method, module}` | Tipo di nodo sintattico. |
| `start_line` | `int` | Riga iniziale 1-based. |
| `end_line` | `int` | Riga finale 1-based. |
| `language` | `str` | Linguaggio sorgente. |
| `chunker` | `enum {syntactic, size_fallback}` | Come è stato prodotto (osservabilità/qualità). |

### ChunkMetadata (per Markdown — REQ-008)

| Campo | Tipo | Note |
|-------|------|------|
| `path` | `str` | Path relativo del file. |
| `heading_path` | `list[str]` | Gerarchia di sezione (es. `["H1", "H2"]`). |
| `chunker` | `=markdown` | — |

**Regole.**
- Codice in linguaggio del set MVP con grammatica matura → chunk ai confini sintattici, `chunker=syntactic` (REQ-006).
- Linguaggio fuori set o grammatica non disponibile → `chunker=size_fallback`, size/overlap da config, **senza errore** (REQ-009).
- Unità sintattica troppo grande → sotto-divisa per righe, `qualname` annotato `(parte N)` (eredità prototipo).
- Re-chunking dello stesso documento invariato → stessi `id` (REQ-010, idempotenza).

---

## EmbeddedChunk (Vettore + metadati)

Rappresentazione del chunk nel vector store. Non sempre un'entità Python materializzata: è il record
persistito (id, vettore, payload di metadati) dentro una collezione namespaced.

| Campo | Tipo | Vincoli / Note | Requisito |
|-------|------|----------------|-----------|
| `chunk_id` | `str` | = `Chunk.id`. Chiave nel vector store. | REQ-017 |
| `vector` | `list[float]` | Embedding; dimensione = `EmbeddingProvider.dim`. | REQ-012 |
| `payload` | `dict` | Testo + metadati del chunk + `doc_type` (per filtro). | REQ-017/025 |
| `collection` | `str` | Namespace = `{corpus}` (o `{corpus}-{provider}-{dim}`). | REQ-019 |

**Regole.**
- Una collezione è coerente per **(corpus, provider, dimensione)**: vettori di dimensioni diverse non si mescolano (R2/R3).
- Collezioni di corpora diversi non interferiscono nelle query (REQ-019, SC-001).

---

## RetrievalResult

Risultato restituito dalla facade per ogni hit.

| Campo | Tipo | Vincoli / Note | Requisito |
|-------|------|----------------|-----------|
| `text` | `str` | Testo del chunk. | REQ-025 |
| `path` | `str` | Path relativo del sorgente. | REQ-025 |
| `chunk_id` | `str` | Identificatore del chunk. | REQ-025 |
| `doc_type` | `enum {code, doc}` | Tipo. | REQ-025 |
| `score` | `float` | Punteggio di pertinenza (similarità). | REQ-025 |
| `metadata` | `dict \| None` | Metadati strutturali opzionali (qualname, righe, heading). | REQ-007/008 |

**Regole.**
- `k` configurabile per query (REQ-026); `k` > chunk disponibili → restituisce tutti i disponibili, **senza** errore (edge case).
- Filtro per `doc_type` (code/doc/both) senza indici separati (REQ-027).
- Indice vuoto/non inizializzato → **lista vuota** + warning strutturato, **non** eccezione (REQ-028).

---

## Settings (Configurazione)

Insieme centralizzato di scelte (in `config/settings.py`). Singola fonte di verità (Principio VIII).

| Gruppo | Chiavi (orientative) | Requisito |
|--------|----------------------|-----------|
| Backend/corpus | `backend` (local\|azure), `corpus` | REQ-030 |
| Embeddings | `embed_provider`, `ollama_host`/`ollama_embed_model`, `azure_endpoint`/`azure_key`/`azure_embed_deployment`, `batch_size` | REQ-013/014 |
| Vector store | `store_backend`, percorsi indice locali, credenziali cloud (da env) | REQ-018 |
| Chunking | `chunk_size`, `chunk_overlap`, `code_languages` (set MVP) | REQ-011 |
| Ingestione | `exclude_patterns` (lista configurabile) | REQ-002 |
| Retrieval | `default_k` | REQ-026 |

**Regole.**
- Caricata da env + file; **nessun default hardcoded nei componenti** (solo in `Settings`) (REQ-030).
- I segreti provengono solo da env/file non versionato; **mai** scritti su path versionati (REQ-032/V-2).

---

## Relazioni

```text
Repository (path radice)
   └─ Document (1..N)          id = path relativo            [REQ-004]
        └─ Chunk (1..N)        id = document_id#index        [REQ-010]
             └─ EmbeddedChunk  in Collection namespaced      [REQ-019]
                                  │ query(vector, k, filter)
                                  ▼
                            RetrievalResult (0..k)           [REQ-025]

Settings ──(governa)──> Ingestione · Chunking · Embeddings · VectorStore · Facade   [REQ-030]
```

## Errori di dominio (entità trasversale)

Gerarchia in `domain/errors.py` (Principio IV).

| Eccezione | Quando | Campi |
|-----------|--------|-------|
| `SertorError` | base | `message` |
| `ConfigError` | config mancante/incoerente | chiave, causa |
| `IngestionError` | radice inaccessibile | path, causa |
| `EmbeddingError` | provider non disponibile/errore | `provider`, `reason`, `retriable` (REQ-015) |
| `VectorStoreError` | backend non disponibile | `backend`, `reason` (REQ-021) |

> Il file illeggibile (REQ-003) e l'indice vuoto (REQ-028) **non** sono errori: producono warning
> strutturati e proseguono / restituiscono vuoto.
