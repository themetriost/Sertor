---
title: Chunking e dispatch (Document → Chunk)
type: concept
tags: [chunking, tree-sitter, dispatch, code-aware, markdown, fallback, sertor-core]
created: 2026-06-08
updated: 2026-10-12
sources: [
  "src/sertor_core/services/chunking/dispatch.py",
  "src/sertor_core/services/chunking/aspnet.py",
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

## Il dispatch (quattro strategie)

```
doc_type == DOC      → markdown_chunks   (confini di heading)         → ChunkerKind.MARKDOWN
pagina ASP.NET       → page_raws(...)    (C# proiettato + markup)     → SYNTACTIC + SIZE_FALLBACK
doc_type == CODE     → code_chunks(...)  (confini sintattici, AST)    → ChunkerKind.SYNTACTIC
   └─ se la lingua non è chunkabile → None → size_chunks (finestra)   → ChunkerKind.SIZE_FALLBACK
```

Le **pagine ASP.NET** (`webforms`: `.aspx .ascx .master .asmx .ashx`; `razor`: `.cshtml .razor`, dal
2026-10-12) sono l'unico caso in cui **un documento mescola due chunker**: i chunk sintattici del C# lato
server, alle righe reali del file, **seguiti** dai chunk dimensionali del markup senza il codice. Il
meccanismo è la [[vista-che-conserva-le-righe]]; per questo il dispatcher associa la funzione dei metadati
**a ogni raw**, non al documento.

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
  sintattico. Garantisce che **nessun documento ingerito** resti senza chunk. Attenzione al confine: il
  chunker vede solo ciò che l'ingestione gli passa, e l'ingestione legge **solo le estensioni di
  `_EXT_LANG`** — un file con un'altra estensione non arriva mai qui, e oggi nessuno lo segnala
  (E10-FEAT-079, [[omissione-che-diventa-risposta]]). *(Corretto il 2026-10-12: la pagina diceva «nessun
  documento resti non indicizzato», la stessa affermazione falsa che stava nel README del core.)*

### Contenitori trasparenti: namespace ed `export` (E10-FEAT-082)

Alcuni nodi **avvolgono** le definizioni senza esserlo: il `namespace Demo { … }` a blocco del C# (la forma
più comune fino a C# 10), `namespace`/`extern "C"` del C++, il namespace a graffe del PHP, `export` in
TypeScript/JavaScript (`export class X`, `export default function f`), il `namespace N { }` di TypeScript.
Fino al 2026-10-12 `code_chunks` guardava solo i figli **diretti** della radice, quindi un file così
diventava **un solo chunk `module`** — il grafo trovava i metodi, il retrieval riceveva il file intero senza
qualname. Ora la mappa `_SCOPES` dichiara per linguaggio questi contenitori e il chunker **ci scende
dentro**, come già faceva la visita del grafo:

- il contenitore **non entra nel qualname** (`Default.BindGrid`, non `Demo.Default.BindGrid`): chunker e
  grafo devono nominare il simbolo allo stesso modo, o il grafo avrebbe due nodi per un metodo;
- l'intestazione (`namespace Demo {`, gli `using`) resta testo del chunk `module`;
- la firma di `_SCOPES` entra nel `_logic_version` dell'indice, così il primo re-index incrementale
  ri-spezza anche i file non modificati.

Tipi di nodo **misurati** con un probe sulle grammatiche reali, non dedotti. Un linguaggio assente da
`_SCOPES` non ha contenitori trasparenti noti (Python, Java, Go, Ruby: `module` di Ruby è già una classe).
- **`markdown_chunks`** (`markdown.py`) — spezza ai confini di **heading**, popolando `heading_path` (la
  gerarchia di sezione) nei metadati.

## Tetto di dimensione del chunk (token cap)

I chunker strutturali (markdown per heading, codice per simbolo) producono chunk **coerenti** ma di dimensione **non limitata**: una sezione/funzione enorme diventa un singolo chunk. Gli embedder hanno un **budget di token per input** (text-embedding-3-large: 8192) e rifiutano gli input più grandi (`http 400`).

Per questo `chunk_document` applica un **tetto in token** (lo stesso che dal 2026-10-20 usa anche la
memoria semantica, vedi [[budget-ingresso-embedding]]) (`Settings.max_chunk_tokens`, env `SERTOR_MAX_CHUNK_TOKENS`, default **8191**): un chunk oltre il tetto è **sub-splittato** (helper `services/chunking/_tokens.py`, `cap_to_tokens`) preservando i metadati strutturali (heading_path/qualname), gli altri restano interi. Il default 8191 **usa quasi tutta la finestra del modello large** (non frammenta le sezioni coerenti), restando entro il limite.

Conteggio token: **preciso con tiktoken** (`cl100k_base`) dietro l'**extra opzionale `tokenizer`** (import lazy); senza l'extra, **fallback conservativo per carattere** (~2 char/token) → il core resta installabile e **offline-safe** (Principio II).

Il tetto entra nella `_logic_version` dell'indice (cambiare il tetto invalida il manifest e forza il re-chunk — FR-013, refresh incrementale).

**Vedi anche:** [[indexing-and-retrieval]] (l'embedding nella pipeline) · [[ports-adapters]] (l'EmbeddingProvider).

## Vedi anche
- Cosa produce: [[domain-model]] (`Chunk`, `ChunkMetadata`).
- Su cosa si appoggia il sintattico: [[tree-sitter-language-pack]].
- Dove si inserisce nella pipeline: [[indexing-and-retrieval]].
- L'architettura complessiva: [[retrieval-core]].
