---
title: tree-sitter-language-pack — Binding Rust e Grammar Multilingua
type: tech
tags: [tree-sitter, parsing, syntax-trees, grammar, multi-language, rust, binding]
created: 2026-06-03
updated: 2026-06-03
sources: [
  "https://github.com/tree-sitter/tree-sitter",
  "https://pypi.org/project/tree-sitter-language-pack/",
  "src/sertor_core/adapters/chunkers/syntactic_chunker.py",
  "src/sertor_core/services/chunking/code.py"
]
---

# tree-sitter-language-pack — Binding Rust e Grammar Multilingua

Tecnologia fondamentale per [[implementazione-nucleo-retrieval|FEAT-001 (Nucleo Retrieval)]], usata per chunking sintattico code-aware su 14 linguaggi MVP. Approfondimento: architettura del binding Rust, quirk dell'API Python, strategie di parsing robusto.

## Overview

**tree-sitter** è un parser incrementale e robusto basato su Rust, in grado di parsare codice sorgente anche parziale/scorretto, generando un Abstract Syntax Tree (AST) stabile e ricercabile.

**tree-sitter-language-pack** è il wheel Python che distribuisce precompilato:
- Binding Rust ufficiale per Python 3.9–3.13 (via PyO3).
- 305+ grammatiche tree-sitter per linguaggi diversi (compilate in `.so` / `.pyd`).
- Portabilità nativa: Windows, Linux, macOS (no dipendenza da compilatore C/C++).

## Architettura Binding

### Python FFI via PyO3

```
tree-sitter-language-pack wheel
├─ _tree_sitter (estensione PyO3)
│  └─ Parser → Language → Query → Tree → Node
└─ languages/ (305+ .so/.pyd per grammar)
   ├─ python.so
   ├─ javascript.so
   ├─ ...
   └─ powershell.so (no sintassi validata ancora)
```

**PyO3** espone l'API Rust come metodi Python (non attributi). Questo è uno **specifico design choice** del binding ufficiale.

### API Python (Metodo-based)

Ecco come **non** funziona (tentativo attribuibile):

```python
# ❌ SBAGLIATO: tree-sitter-language-pack usa METODI
node.kind       # AttributeError: no attribute 'kind'
node.start_byte # AttributeError
node.children   # AttributeError
node.text       # AttributeError
```

Ecco come **funziona realmente**:

```python
# ✅ CORRETTO: tutto è via metodi/call
node.kind()                    # Returns: str (ex. "function_definition")
node.byte_range()              # Returns: (start_byte: int, end_byte: int)
node.start_position()          # Returns: (row: int, column: int) — 0-indexed
node.end_position()            # Returns: (row: int, column: int) — 0-indexed
node.child_count               # Property: int
node.child(index: int)         # Method: Node | None
node.parent()                  # Returns: Node | None
node.next_sibling()            # Returns: Node | None
node.prev_sibling()            # Returns: Node | None

# Iterazione figli
for i in range(node.child_count):
    child = node.child(i)
    # ...
```

### Impact Pratico (Wrapper `_Node`)

Nel codice di FEAT-001, il binding Rust avrebbe reso il traversal AST **tremendamente verboso**:

```python
# ❌ SENZA WRAPPER: ripetizione estenuante
def traverse(node, source):
    kind = node.kind()
    start, end = node.byte_range()
    row, col = node.start_position()
    text = source[start:end]
    # ... ripetere per ogni node
```

**Soluzione:** wrapper `_Node` in `src/sertor_core/services/chunking/code.py`:

```python
class _Node:
    """Adapter per l'API metodo-based di tree-sitter-language-pack."""
    
    def __init__(self, raw_node):
        self._node = raw_node
    
    @property
    def kind(self):
        """Ex: 'function_definition', 'class_definition', 'method_declaration'."""
        return self._node.kind()
    
    @property
    def byte_range(self):
        """(start_byte, end_byte) per slicing source."""
        return self._node.byte_range()
    
    @property
    def start_position(self):
        """(row, col) — 0-indexed da tree-sitter."""
        r, c = self._node.start_position()
        return (r, c)
    
    @property
    def start_line(self):
        """1-indexed riga per metadata; tree-sitter è 0-indexed."""
        return self._node.start_position()[0] + 1
    
    @property
    def child_count(self):
        return self._node.child_count
    
    def child(self, index):
        """Ritorna _Node wrapper, non raw node."""
        raw_child = self._node.child(index)
        return _Node(raw_child) if raw_child else None
    
    def iter_children(self):
        """Generatore comodo per iterazione."""
        for i in range(self.child_count):
            yield self.child(i)
```

Con il wrapper, il traversal diventa naturale:

```python
def traverse(node: _Node, source: str):
    kind = node.kind                    # Proprietà (clean)
    start, end = node.byte_range        # Proprietà
    line = node.start_line              # 1-indexed (conveniente)
    text = source[start:end]
    
    for child in node.iter_children():  # Iterazione pulita
        traverse(child, source)
```

## Linguaggi e Node-Type

### 10 Linguaggi Sintattico MVP (Validati)

tree-sitter-language-pack contiene grammatiche per 305+ linguaggi. In FEAT-001, abbiamo scelto 10 **sintattico** (parsing AST completo, metadata ricco):

| Linguaggio | Grammar | Node-Type Chiavi | Qualname Support | Fallback |
|---|---|---|---|---|
| **Python** | `python` | `function_definition`, `async_function_definition`, `class_definition` | ✅ nested scope | Dimensionale |
| **JavaScript** | `javascript` | `function_declaration`, `arrow_function`, `class_declaration` | ✅ nested scope | Dimensionale |
| **TypeScript** | `typescript` | `function_declaration`, `arrow_function`, `class_declaration`, `interface_declaration` | ✅ nested scope | Dimensionale |
| **Java** | `java` | `method_declaration`, `class_declaration`, `interface_declaration` | ✅ nested | Dimensionale |
| **C#** | `c_sharp` | `method_declaration`, `class_declaration`, `interface_declaration` | ✅ nested | Dimensionale |
| **Go** | `go` | `function_declaration`, `method_declaration` | ✅ receiver type | Dimensionale |
| **C** | `c` | `function_definition` | Partial | Dimensionale |
| **C++** | `cpp` | `function_definition`, `method_definition`, `class_specifier` | ✅ namespace | Dimensionale |
| **PHP** | `php` | `function_declaration`, `method_declaration`, `class_declaration` | ✅ namespace | Dimensionale |
| **Ruby** | `ruby` | `method_definition`, `class_definition` | ✅ nested | Dimensionale |

### 3 Fallback Dimensionali (Validazione In Sospeso)

tree-sitter-language-pack contiene grammatiche per **PowerShell**, **T-SQL**, **PL/SQL**, ma:

- **Grammatica presente:** sì.
- **Validazione AST:** in-progress upstream tree-sitter.
- **Node-type stabile:** no ancora.

**Decisione FEAT-001 (R-N2):** usare fallback **dimensionale** per questi 3, rimandare sintattico a post-MVP.

```python
# Fallback dimensionale (chunk per size, no AST)
FALLBACK_LANGUAGES = {"powershell", "sql", "tsql", "plsql"}

def chunk_document(doc: Document) -> list[Chunk]:
    if doc.language.lower() in FALLBACK_LANGUAGES:
        return size_fallback_chunker.chunk_document(doc)  # 1k token chunks
    else:
        return syntactic_chunker.chunk_document(doc)
```

## Performance & Robustness

### Parsing Parziale e Errori

tree-sitter **consente parsing robusto** anche di codice scorretto:

```python
# Codice scorretto (syntax error)
def foo(x:
    return x + 1

# tree-sitter genera comunque un AST valido (con ERROR nodi per la parte non parsabile)
```

**Vantaggi:**
- Non crasha su file corrotti / incompleti.
- Permette chunking anche su WIP (work-in-progress) code.

**Svantaggio:**
- Metadata incomplete per nodi ERROR; di solito li ignoriamo nel traversal.

### Latenza

Su corpus tipico (57 doc FastAPI):

- **Parsing:** ~50 ms per file (media).
- **Tree-sitter overhead:** trascurabile (operazione C; binding PyO3 efficiente).
- **Bottleneck reale:** embedding, non parsing.

### Memoria

AST in memoria:
- Per file da 10 KB: ~1 MB (albero + nodi).
- Liberato subito dopo chunking.
- No accumulo.

## Extension Strategy (Post-MVP)

### Aggiungere Linguaggio Sintattico

1. **Verificare disponibilità in tree-sitter upstream:**
   - https://github.com/tree-sitter/tree-sitter/tree/master/grammars

2. **Se disponibile:**
   - `pip install tree-sitter-language-pack` (auto-include se nel wheel).
   - Aggiungi linguaggio a `SYNTACTIC_LANGUAGES` in `chunking_service.py`.
   - Identifica node-type chiave (funzione, classe, metodo).
   - Test: parsing su corpus noto, valida metadata.

3. **Se non disponibile:**
   - Fallback dimensionale indefinitamente.
   - Opzionalmente contribuisci grammatica a tree-sitter upstream.

### Linguaggi Futuri Candidati

- **PowerShell sintattico:** grammatica funzionante; aspettare stabilizzazione AST upstream.
- **T-SQL sintattico:** multiple dialetti (TSQL vs standard SQL); richiede disambiguazione.
- **PL/SQL sintattico:** idem.
- **Rust:** grammatica robusto; add post-MVP se richiesto.
- **Go Module Graph:** tree-sitter di Go non ha dependency tracking; usare AST per import statement.

## Trade-off vs Altre Soluzioni

### Linguaggi Specifici (espressi, antlr, parsec)

| Criterio | tree-sitter | Linguaggi Specifici |
|---|---|---|
| **Portabilità** | ✅ Wheel Win/Linux/Mac | ⚠️ Compilatore richiesto |
| **Robustezza** | ✅ Parsing parziale | ❌ Crash su errore |
| **Setup** | ✅ pip install | ❌ Build tools |
| **Copertura** | ✅ 305+ lingue | ❌ Tipicamente 1-5 |

tree-sitter vince per **MVP** (setup, coverage, portabilità).

### Lexer + Regex Custom

| Criterio | tree-sitter | Regex Custom |
|---|---|---|
| **Accuratezza** | ✅ AST completo | ⚠️ Euristiche |
| **Manutenzione** | ✅ Upstream-maintained | ❌ Custom indefinita |
| **Scope** | ✅ 305+ linguaggi | ❌ Uno per linguaggio |

tree-sitter scala meglio.

## Quirk & Gotcha Noti

### 1. Byte vs Caratteri

tree-sitter usa **byte offsets**, non character offsets. Per UTF-8:

```python
# Sorgente: "def foo(x: Stringa):"  (con accento)
node.byte_range()  # (0, 21) → byte range in UTF-8
source[0:21]       # Corretto iff slicing su byte

# ❌ SBAGLIATO (character slicing su UTF-8)
source[0:20]       # Potrebbe troncate multi-byte char
```

**Soluzione in FEAT-001:** sempre slicing su byte, no character index.

### 2. Row e Column 0-indexed

tree-sitter ritorna **0-indexed** row/column; linguaggi di solito usano **1-indexed**.

```python
node.start_position()  # (3, 5) = riga 4, colonna 6 per editor
# Wrapper _Node.start_line converte a 1-indexed
```

### 3. No `.text` Diretto

tree-sitter node non ha `.text`. Bisogna slicciare il sorgente:

```python
# ❌ node.text (non esiste)
# ✅ source[start:end] su byte
```

### 4. Grammar nel Wheel Precompilato

tree-sitter-language-pack wheel è **precompilato** (Python 3.9–3.13). Non dipende da compilatore, ma versione Python deve corrispondere.

```python
# ✅ Python 3.12 + tree-sitter-language-pack 1.8.1 = ok
# ❌ Python 3.8 + tree-sitter-language-pack = incompatible
```

## References Interne

- **Implementazione:** `src/sertor_core/adapters/chunkers/syntactic_chunker.py` (load_language, parse, traverse, extract_chunks).
- **Wrapper:** `src/sertor_core/services/chunking/code.py` (_Node class, traversal helpers).
- **Test:** `tests/test_chunking.py` (test per linguaggi sintattico, fallback, idempotenza).
- **Config:** `config/settings.py` (SYNTACTIC_LANGUAGES, chunk size).

## Conclusione

tree-sitter-language-pack è la scelta di chunking sintattico per FEAT-001 per:
- ✅ Portabilità (wheel Win/Linux/Mac, no compilatore).
- ✅ Copertura multilingua (305+ linguaggi, 10 sintattico MVP + fallback).
- ✅ Robustezza (parsing parziale, indenne a codice scorretto).
- ✅ Performance (embedding è bottleneck, non parsing).

Il binding Rust espone **metodo-based API** (non attributi); il wrapper `_Node` risolve elegantemente per leggibilità codice.

---

**Cross-refs:** [[implementazione-nucleo-retrieval|Implementazione FEAT-001]] · [[piano-nucleo-retrieval|Piano FEAT-001]]
