---
title: tree-sitter-language-pack (binding e wrapper _Node)
type: tech
tags: [tree-sitter, parsing, ast, binding, multi-language, chunking, sertor-core]
created: 2026-06-03
updated: 2026-07-23
sources: ["https://pypi.org/project/tree-sitter-language-pack/", "src/sertor_core/services/chunking/code.py"]
---

# tree-sitter-language-pack (binding e wrapper _Node)

**tree-sitter-language-pack** è il wheel Python che distribuisce **precompilate** centinaia di grammatiche
[tree-sitter](https://tree-sitter.github.io/) (parser incrementale e robusto, scritto in Rust). In Sertor è
la base del [[chunking-dispatch|chunking sintattico code-aware]] del [[retrieval-core]]: da esso si ottiene un
**parser per linguaggio** e si naviga l'AST per spezzare il codice ai confini di funzione/classe/metodo. Questa
pagina è il *binding* (la tecnologia); *come* Sertor lo usa per produrre i chunk sta in [[chunking-dispatch]].

## Perché questo pacchetto

- **Precompilato e portabile** — il wheel non richiede compilatore C/C++: gira su Windows/Linux/macOS. La
  grammatica giusta si ottiene con `get_parser(name)`, senza build locale.
- **Robusto** — tree-sitter produce un AST anche su codice **parziale o sintatticamente errato** (nodi
  `ERROR` per le parti non parsabili), quindi il chunking non crasha su file WIP/corrotti.
- **Ampia copertura** — centinaia di grammatiche; Sertor ne usa **10** col chunking sintattico (vedi
  [[chunking-dispatch]]), il resto va in fallback dimensionale.

## Il quirk del binding: API a **metodi**, non attributi

Il binding Rust espone i nodi dell'AST come **chiamate di metodo**, non come attributi/proprietà. È la cosa
che sorprende: `node.kind` (attributo) **non esiste**, serve `node.kind()`. Allo stesso modo
`node.start_position()` (→ oggetto con `.row`/`.column`, **0-indexed**), `node.byte_range()` (→ oggetto con
`.start`/`.end`, in **byte** UTF-8, non caratteri), `node.child_by_field_name(name)`, `node.named_child(i)`.

## Il wrapper `_Node` (l'adapter di leggibilità)

Per non costellare il traversal di chiamate-metodo, `services/chunking/code.py` avvolge il nodo grezzo in un
piccolo `_Node` (`__slots__ = ("n", "src")`) che espone un'interfaccia pulita e fa le conversioni una volta
sola:

| Membro di `_Node` | Cosa fa (sul nodo grezzo) |
|---|---|
| `kind` (property) | `n.kind()` |
| `start_row` / `end_row` | `n.start_position().row` / `n.end_position().row` (0-indexed; +1 a valle per le righe 1-based) |
| `field(name)` | `n.child_by_field_name(name)` → `_Node` o `None` |
| `named_children()` | lista di `_Node` su `n.named_child(i)` |
| `name()` | il testo del figlio-campo `name` (identificatore del simbolo) |
| `text()` | slice di `src[byte_range.start : .end]` decodificato UTF-8 |
| `body()` | il campo `body`/`declaration_list` (il corpo di funzione/classe) |

Il wrapper porta in `src` i **byte** del sorgente (`text.encode("utf-8")`), perché lo slicing dei nodi è su
**byte-range**: tagliare su indici di carattere romperebbe il multi-byte UTF-8.

## Note operative

- **Righe 1-based a valle.** tree-sitter dà righe/colonne 0-indexed; i metadati dei chunk le riportano
  1-based (`start_row + 1`).
- **Wheel legato alla versione di Python** — essendo precompilato, la versione del wheel deve combaciare con
  l'interprete (Sertor: Python >=3.11).
- **Fallback su qualunque errore** — se la grammatica non c'è o il parse fallisce, `code_chunks` ritorna
  `None` e il dispatcher passa al fallback dimensionale (degradazione sicura, mai un crash).

## Vedi anche
- Come si usa per chunkare: [[chunking-dispatch]] (i 10 linguaggi, module/class/method, oversize split).
- Cosa produce a valle: [[domain-model]] (`Chunk`, `ChunkMetadata`).
- L'architettura che lo contiene: [[retrieval-core]].
