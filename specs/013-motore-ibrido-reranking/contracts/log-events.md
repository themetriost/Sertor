# Contract — Eventi di log del motore ibrido

Emessi via `log_event` esistente (`observability/logging.py`): record `logging` con
`operation` + campi strutturati in `extra`, segreti redatti (REQ-062). Schema additivo:
gli eventi esistenti (`baseline_query`, `retrieve`, `index`, `embeddings_error`,
`store_error`) NON cambiano.

## `hybrid_query` (INFO) — REQ-060

Una emissione per ogni query ibrida (anche in degradazione).

| Campo | Tipo | Esempio | Note |
|---|---|---|---|
| `engine` | str | `hybrid` | nome del motore |
| `provider` | str | `azure:text-embedding-3-large` | provider embeddings |
| `collection` | str | `sertor__azure_text_embedding_3_large` | |
| `lexical_hits` | int | `30` | candidati dalla via lessicale (0 in degradazione) |
| `dense_hits` | int | `30` | candidati dalla via densa |
| `fused_k` | int | `5` | risultati restituiti |
| `rerank_applied` | bool | `false` | |
| `elapsed_ms` | float | `142.7` | tempo totale della query |

## `rerank` (INFO) — REQ-061

Solo quando il secondo stadio è applicato.

| Campo | Tipo | Esempio |
|---|---|---|
| `reranker_model` | str | `ms-marco-MiniLM-L-12-v2` |
| `pool_size` | int | `15` |
| `top_k` | int | `5` |
| `elapsed_ms` | float | `88.3` |

## `lexical_index_missing` (WARNING) — REQ-034

Una emissione per query in degradazione (corpus pre-ibrido).

| Campo | Tipo | Esempio |
|---|---|---|
| `collection` | str | `sertor__azure_text_embedding_3_large` |
| `hint` | str | `re-index del corpus per abilitare il retrieval ibrido` |

## Vincoli

- Nessun campo può contenere valori segreti; la redazione (`redact`) si applica comunque.
- I campi sono diagnostici sufficienti senza leggere il codice (Principio IX, NFR-07).
