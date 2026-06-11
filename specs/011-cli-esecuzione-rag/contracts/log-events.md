# Contratto — Schema degli eventi di log strutturati

**Feature**: `011-cli-esecuzione-rag` | **Fase**: Phase 1 (Contracts) | **Data**: 2026-06-11

Soddisfa **FR-021/REQ-054** (documentare l'insieme dei campi di log per operazione) e
**FR-020/REQ-053** (evento strutturato sui fallimenti ai boundary). Tutti gli eventi sono emessi dal
core via `sertor_core.observability.logging.log_event(level, operation, **fields)` sul logger
nominato `sertor_core`. La CLI configura solo livello/formato/appender (D4). I segreti sono
**redatti** prima dell'emissione (`redact()`, FR-022/REQ-055): mai chiavi/token nei record.

Ogni record ha `operation` (in `extra`) + i campi sotto. Con `--log-json` ogni evento è un oggetto
JSON con questi campi; con dictConfig l'utente sceglie il formatter.

---

## Eventi esistenti nel core (riusati)

### `index` (INFO) — indicizzazione completata (`services/indexing.py`)
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"index"` |
| `collection` | str | collezione namespaced |
| `provider` | str | nome+modello provider embeddings |
| `documents` | int | documenti ingeriti |
| `chunks` | int | chunk indicizzati |
| `embedding_dim` | int | dimensione del vettore |
| `elapsed_ms` | float | durata |

### `retrieve` (INFO/WARNING) — ricerca via facade (`services/retrieval.py`)
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"retrieve"` |
| `collection` / `collections` | str / list | bersaglio/i |
| `provider` | str | provider embeddings (assente nel warning `no_index`) |
| `doc_type` | str | `code` / `doc` / `both` |
| `k` | int | top-k |
| `results` | int | hit restituiti |
| `elapsed_ms` | float | durata |
| `status` | str | `"no_index"` sul WARNING di indice assente (facade tollerante) |

### `baseline_query` (INFO) — query del motore baseline (`engines/baseline.py`)
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"baseline_query"` |
| `collection` | str | collezione |
| `provider` | str | provider embeddings |
| `k` | int | top-k |
| `results` | int | hit |
| `elapsed_ms` | float | durata |

---

## Eventi nuovi (estensione additiva, FR-020/REQ-053)

Emessi **prima** che l'eccezione di dominio sia propagata, ai boundary degli adapter
(`adapters/embeddings/*`, `adapters/vectorstores/*`) e/o dove l'errore viene avvolto. Livello
`ERROR`. Non alterano il comportamento d'errore (l'eccezione resta): aggiungono solo l'osservabilità
del fallimento.

### `embeddings_error` (ERROR)
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"embeddings_error"` |
| `provider` | str | provider embeddings (es. `ollama`, `azure`) |
| `reason` | str | causa sintetica (da `EmbeddingError.reason`) |
| `retriable` | bool | ritentabilità |

### `store_error` (ERROR)
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"store_error"` |
| `backend` | str | backend store (es. `chroma`, `azure_search`) |
| `reason` | str | causa (da `VectorStoreError.reason`) |

### `index_error` (ERROR) — fallimento durante l'indicizzazione al boundary
| Campo | Tipo | Note |
|-------|------|------|
| `operation` | str | `"index_error"` |
| `provider` / `backend` | str | componente che ha fallito |
| `collection` | str | collezione interessata |
| `reason` | str | causa |

> Nota implementativa: `index_error` può essere derivato componendo `embeddings_error`/`store_error`
> con il contesto dell'operazione `index`; la decisione fine (un evento dedicato vs i due di
> boundary) è di implementazione, purché ogni fallimento ai tre boundary (embeddings, store,
> indexing) produca **almeno** un evento strutturato con `operation`, `provider`/`backend` e
> `reason` (FR-020).

---

## Garanzie trasversali

- **Nessun segreto** in alcun campo: `redact()` sostituisce con `***` i valori delle chiavi che
  contengono `key|api_key|apikey|token|secret|password|authorization` (FR-022/REQ-055).
- **Stabilità dei nomi di campo**: questo schema è il contratto che gli appender esterni
  (file/syslog/Splunk/ELK) possono indicizzare (FR-021/SC-006).
- **Logger unico**: `sertor_core`; configurabile interamente dalla CLI senza toccare il codice del
  core (Principio IX, FR-017..019).
