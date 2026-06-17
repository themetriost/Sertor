---
title: Chunking e dispatch (Document → Chunk)
type: concept
tags: [chunking, tree-sitter, dispatch, code-aware, markdown, fallback, sertor-core]
created: 2026-06-08
updated: 2026-06-17
sources: [
  "src/sertor_core/services/chunking/dispatch.py",
  "src/sertor_core/services/chunking/code.py",
  "src/sertor_core/services/chunking/markdown.py",
  "src/sertor_core/services/chunking/fallback.py",
  "src/sertor_core/services/chunking/_tokens.py"
]
---

# Chunking e dispatch (Document → Chunk)

Il **chunking** del [[retrieval-core]] trasforma un [[domain-model|`Document`]] nei suoi [[domain-model|`Chunk`]]
indicizzabili, smistando per **tipo di documento e linguaggio** verso la strategia giusta. Il punto d'ingresso
è `chunk_document(doc, settings)` in `services/chunking/dispatch.py`; il chunker scelto è registrato in
`ChunkMetadata.chunker` (`ChunkerKind`) per osservabilità.

## Il dispatch (tre strategie)

```
doc_type == DOC      → markdown_chunks   (confini di heading)         → ChunkerKind.MARKDOWN
doc_type == CODE     → code_chunks(...)  (confini sintattici, AST)    → ChunkerKind.SYNTACTIC
   └─ se la lingua non è chunkabile → None → size_chunks (finestra)   → ChunkerKind.SIZE_FALLBACK
```

A ogni chunk emesso il dispatcher assegna l'id stabile `f"{document_id}#{index}"` (ordinale posizionale): è la
sorgente dell'**idempotenza** del [[domain-model]].

## Chunking sintattico (code-aware)

`code.py` spezza il codice **ai confini sintattici** via [[tree-sitter-language-pack]]: ogni
funzione/metodo/classe diventa un chunk coerente con metadati strutturali (`symbol`, `node_type`, `qualname`,
righe **1-based**); il codice a livello modulo (import, costanti) è raggruppato in chunk propri; le unità
troppo grandi sono sotto-divise per righe (`max_chars`, default 1600). Il `qualname` ricostruisce la gerarchia
(`Classe.metodo`) navigando classi annidate.

> **Nota sul mapping dei nomi.** Il raw chunk di `code.py` espone il campo **`symbol_kind`**; è il dispatcher
> a rinominarlo in **`node_type`** quando costruisce il [[domain-model|`ChunkMetadata`]] (`dispatch.py`,
> `node_type=raw.get("symbol_kind")`). Chi legge `code.py` cerca `symbol_kind`, chi legge i metadati trova
> `node_type`: stesso dato, due nomi ai due lati del dispatch.

**Solo i linguaggi con node-type validati sono chunkati sintatticamente** — i 10 di `_LANG`: Python,
JavaScript, TypeScript, Java, C#, Go, C, C++, PHP, Ruby. Per gli altri `code_chunks` ritorna `None` e il
dispatcher fa il **fallback dimensionale** (REQ-009).

### Esclusione deliberata (R-N2)

PowerShell e i dialetti SQL **hanno** una grammatica nel pack ed sono mappati come linguaggi
dall'[[indexing-and-retrieval|ingestione]], ma sono **volutamente esclusi** dal set sintattico al 1° rilascio:
i loro node-type non sono ancora validati, quindi finiscono in fallback finché non lo saranno (estensione
incrementale). È una scelta di **rischio**, non un buco: meglio un fallback corretto che metadati sintattici
inaffidabili.

## Fallback dimensionale e Markdown

- **`size_chunks`** (`fallback.py`) — finestra dimensionale con overlap, per i linguaggi fuori dal set
  sintattico e per ogni testo non riconosciuto. Garantisce che **nessun documento resti non indicizzato**.
- **`markdown_chunks`** (`markdown.py`) — spezza ai confini di **heading**, popolando `heading_path` (la
  gerarchia di sezione) nei metadati.

## Tetto di dimensione del chunk (token cap)

I chunker strutturali (markdown per heading, codice per simbolo) producono chunk **coerenti** ma di dimensione **non limitata**: una sezione/funzione enorme diventa un singolo chunk. Gli embedder hanno un **budget di token per input** (text-embedding-3-large: 8192) e rifiutano gli input più grandi (`http 400`).

Per questo `chunk_document` applica un **tetto in token** (`Settings.max_chunk_tokens`, env `SERTOR_MAX_CHUNK_TOKENS`, default **8191**): un chunk oltre il tetto è **sub-splittato** (helper `services/chunking/_tokens.py`, `cap_to_tokens`) preservando i metadati strutturali (heading_path/qualname), gli altri restano interi. Il default 8191 **usa quasi tutta la finestra del modello large** (non frammenta le sezioni coerenti), restando entro il limite.

Conteggio token: **preciso con tiktoken** (`cl100k_base`) dietro l'**extra opzionale `tokenizer`** (import lazy); senza l'extra, **fallback conservativo per carattere** (~2 char/token) → il core resta installabile e **offline-safe** (Principio II).

Il tetto entra nella `_logic_version` dell'indice (cambiare il tetto invalida il manifest e forza il re-chunk — FR-013, refresh incrementale).

**Vedi anche:** [[indexing-and-retrieval]] (l'embedding nella pipeline) · [[ports-adapters]] (l'EmbeddingProvider).

## Vedi anche
- Cosa produce: [[domain-model]] (`Chunk`, `ChunkMetadata`).
- Su cosa si appoggia il sintattico: [[tree-sitter-language-pack]].
- Dove si inserisce nella pipeline: [[indexing-and-retrieval]].
- L'architettura complessiva: [[retrieval-core]].
