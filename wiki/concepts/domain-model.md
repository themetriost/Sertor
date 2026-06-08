---
title: Domain model (entità del retrieval-core)
type: concept
tags: [domain-model, entities, sertor-core, clean-architecture, idempotenza, retrieval]
created: 2026-06-08
updated: 2026-06-08
sources: ["src/sertor_core/domain/entities.py", "src/sertor_core/domain/ports.py"]
---

# Domain model (entità del retrieval-core)

Il **domain model** del [[retrieval-core]] è l'insieme delle **entità dati pure** che attraversano la
pipeline di retrieval — vivono in `domain/entities.py` e **non importano alcun SDK esterno** (Principio I
della [[constitution|Costituzione]]): sono `dataclass` `frozen` condivise da servizi e adapter. Due idee le
governano: **identificatori stabili** (derivati da path/posizione) e **idempotenza** (stesso input → stessi
id), che insieme rendono il rebuild dell'indice ripetibile (Principio VI).

## Le entità

| Entità | Cos'è | Campi chiave |
|---|---|---|
| **`Document`** | un file ingerito (codice o doc) | `id` (= path relativo POSIX), `text`, `doc_type`, `language`, `path` |
| **`Chunk`** | porzione **indicizzabile** di un documento | `id` (= `f"{document_id}#{index}"`), `document_id`, `text`, `doc_type`, `metadata` |
| **`ChunkMetadata`** | metadati strutturali del chunk | `chunker` (provenienza), `qualname`/`symbol`/`node_type`/`start_line`/`end_line` (codice), `heading_path` (markdown) |
| **`EmbeddedChunk`** | record persistito nel vector store | `chunk_id`, `vector`, `payload` (testo + metadati) |
| **`RetrievalResult`** | un hit restituito dalla facade | `text`, `path`, `chunk_id`, `doc_type`, `score`, `metadata` |
| **`IndexReport`** | esito di un'indicizzazione (osservabilità) | `collection`, `documents`, `chunks`, `skipped`, `embedding_dim`, `elapsed_ms` |

Due enum (`StrEnum`) tipizzano le scelte ricorrenti: **`DocType`** (`code` | `doc`) classifica il documento e
abilita il filtro di ricerca; **`ChunkerKind`** (`syntactic` | `markdown` | `size_fallback`) registra **come**
un chunk è stato prodotto — utile per osservabilità e analisi di qualità.

## I due principi nel dato

- **Identificatori stabili.** `Document.id` è il **path relativo POSIX** rispetto alla radice del repo: la
  re-ingestione di un file invariato produce lo stesso id, su qualunque OS. `Chunk.id` è
  `f"{document_id}#{index}"`, con `index` ordinale posizionale nell'ordine di emissione del chunker. Vedi
  [[chunking-dispatch]] per come nasce l'`index`.
- **Idempotenza.** Poiché gli id non dipendono dal tempo né dall'ordine di scoperta (l'ingestione è
  **ordinata** per path), un full re-index su corpus invariato riproduce **lo stesso insieme di id** →
  l'`upsert` sovrascrive senza duplicare (SC-005). È la base del rebuild-from-scratch di
  [[indexing-and-retrieval]].

## Perché entità pure

Tenere il modello **senza dipendenze da SDK** è ciò che permette alle porte ([[ports-adapters]]) di parlare
in termini di queste entità (`EmbeddedChunk`, `RetrievalResult`) e agli adapter concreti di tradurle verso
Chroma/Azure/Ollama **senza** che il dominio sappia nulla di loro. Il `payload` di `EmbeddedChunk` è un
`dict` proprio per non vincolare il dominio allo schema di un backend specifico.

## Vedi anche
- Architettura che le contiene: [[retrieval-core]].
- Chi le produce/consuma: [[chunking-dispatch]] (Document→Chunk), [[indexing-and-retrieval]] (Chunk→EmbeddedChunk→RetrievalResult).
- Le astrazioni che le scambiano: [[ports-adapters]].
