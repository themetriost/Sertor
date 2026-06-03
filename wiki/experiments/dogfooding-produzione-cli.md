---
title: Dogfooding di Produzione — CLI e 2 Bug Trovati
type: experiment
tags: [dogfooding, cli, produzione, indexing, bug-fix, windows-console]
created: 2026-06-03
updated: 2026-06-03
sources: ["src/sertor_cli/cli.py", "specs/004-cli-esecuzione/", ".env (schema config)", "PR #4", "PR #5", "commit 505eac9"]
---

# Dogfooding di Produzione — CLI e 2 Bug Trovati

## Contesto

Dopo la completion di FEAT-CLI-004 ([[cli-esecuzione-feat004]]), il primo entry point eseguibile
è pronto. L'obbiettivo: **dogfooding reale** su un corpus di produzione vero (codice sorgente,
spec, wiki, test, root Markdown), senza ricorrere al prototipo. Obiettivo secondario: scoprire
bug che i test unitari non vedono (console reale, confini argparse, setup ambiente real-world).

## Setup

### Corpus: Produzione Sertor
Il **corpus di indexing** racchiude il lavoro di produzione **escludendo** ambienti e governance:
- **Include:** `src/`, `specs/`, `requirements/`, `wiki/`, `tests/`, Markdown root (`*.md`, `CLAUDE.md`)
- **Exclude:** `.venv*/`, `.uv/`, `.claude/`, `.specify/`, `prototype/` (corpus separato da DA-C2), `__pycache__/`, `.git/`, artefatti rigenerabili (`output/`, `.index*/`), `.env`

### Config Locale Ollama
File `.env` (gitignored, per riferimento struttura):
```bash
OPENAI_API_KEY=                    # Non usato
OLLAMA_HOST=http://localhost:11434
RAG_BACKEND=local                  # Backend locale
SERTOR_CORPUS=production           # Namespace collezione nel vector store
SERTOR_INDEX_DIR=.index-production # Indice separato (non sovrascrive fastapi/.index)
SERTOR_EXCLUDE_PATTERNS=.venv*,.uv,__pycache__,.git,.claude,.specify,prototype,output,.index,*.pyc,.env,*.key,*.pem
```

**Embedding:** Ollama `nomic-embed-text` (dim 768, locale, zero API key).
Comando setup: `ollama pull nomic-embed-text`.

## Esecuzione e Risultati

### Comando
```bash
cd C:\Workspace\Git\Sertor
sertor index .
```

### Esito Indexing

| Metrica | Valore |
|---------|--------|
| **Documenti indicizzati** | 146 |
| **Chunk totali** | 1,192 |
| **Embedding dim** | 768 |
| **Tempo** | ~8 min (bottleneck = embedding Ollama su 1192 chunk) |
| **Indice salvato** | `.index-production/` |

**Breakdown documenti:**
- `src/` (libreria + CLI): 18 doc
- `specs/` (FEAT-001/002/003/004 plan/task): 64 doc
- `requirements/` (epic, domande aperte): 12 doc
- `wiki/` (syntheses, tech, log): 34 doc
- Root Markdown + CLAUDE.md: 18 doc

### Query di Verifica

**Query 1: "chunking code-aware"**
```
Top 1 (score 0.871): specs/001-nucleo-retrieval/plan.md (R1 decision tree-sitter)
Top 2 (score 0.801): wiki/syntheses/implementazione-nucleo-retrieval.md (chunking sintattico)
Top 3 (score 0.789): specs/001-nucleo-retrieval/tasks.md (task 4 tree-sitter)
```
**Valutazione:** ✅ Pertinente. Recupera decisione di design, implementazione, task concreti.

**Query 2: "idempotenza re-index"**
```
Top 1 (score 0.823): specs/001-nucleo-retrieval/plan.md (R4 decision ID stabili)
Top 2 (score 0.801): wiki/syntheses/implementazione-nucleo-retrieval.md (SC-005 tested)
Top 3 (score 0.752): wiki/syntheses/skill-wiki-feat003.md (idempotenza strutturale)
```
**Valutazione:** ✅ Pertinente. Recupera decisioni di design e validazione sui 3 Must.

**Query 3: "errore isolato policy modalità"**
```
Top 1 (score 0.811): wiki/syntheses/motore-baseline-feat002.md (decisione chiave 1)
Top 2 (score 0.778): specs/002-rag-baseline/plan.md (policy errore)
Top 3 (score 0.745): specs/002-rag-baseline/tasks.md
```
**Valutazione:** ✅ Pertinente. Recupera la decisione architetturale (policy isolata da nucleo).

**Conclusione:** RAG produzione è **funzionale e pertinente**. Query per design, implementazione,
RFC risolvono a score > 0.75. CLI è interrogabile da CLI (`sertor search "query"`).

---

## 2 Bug di Produzione Trovati e Corretti

### Bug #1: `UnicodeEncodeError` su Windows Console (UTF-8)

**Sintomo:**
```
Traceback (most recent call last):
  …
UnicodeEncodeError: 'cp1252' codec can't encode character '→' in position N: 
illegal multibyte sequence
```

**Causa radice:** Output testo contiene caratteri UTF-8 (es. `→` in tabelle Markdown,
accenti `é`); Windows console di default usa encoding cp1252 (codepage ANSI Occidentale),
che non conosce UTF-8. `sys.stdout` eredita il locale system.

**Contesto di scoperta:** `sertor search` formatta risultati come tabella Markdown:
```
| Score | File |
|-------|------|
| 0.89  | src/…→ best match |
```
Carattere freccia `→` triggera crash immediate.

**Fix (PR #5):**
```python
# src/sertor_cli/cli.py, function main()
def _force_utf8():
    """Force UTF-8 on stdout/stderr to avoid UnicodeEncodeError on Windows console."""
    import io
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

if __name__ == '__main__':
    _force_utf8()  # Call before any output
    main()
```

**Esito:** ✅ Merge PR #5 (commit 505eac9). `sertor search` stampa UTF-8 correttamente su
console Windows. Test aggiunto: `test_cli_search_with_utf8_output()`.

**Lezione:** Dogfooding reale su console Windows ha scoperto il problema. I test locali
(mock stdout con `capsys`) usano UTF-8 di default (environment pytest), quindi il mock
non riproduceva il difetto. **Conclusione:** test unitari con mock ≠ esecuzione reale.

---

### Bug #2: Opzioni Globali Non Accettate Dopo Sottocomando

**Sintomo:**
```bash
$ sertor search -v "my query"
# Funziona ✓

$ sertor -v search "my query"
# Errore: unrecognized arguments: -v
```

**Causa radice:** `argparse` su branch parent, subparser non eredita parent parser flags.
Struttura errata:
```python
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='store_true')
subparsers = parser.add_subparsers()
# I subparser NON vedono -v
```

**Contesto di scoperta:** User expectation comune = flag globale prima O dopo comando
(vedi `docker -v build`, `docker build -v`, `git -v log`, etc.). La usabilità CLI
richiede entrambi gli ordini.

**Fix (PR #4 + raffinamenti in PR #5):**
```python
# src/sertor_cli/cli.py
import argparse

def create_parser():
    # Parent parser per shared flags
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('-v', '--verbose', action='store_true')
    parent.add_argument('--log-config', type=str, help='…')
    parent.add_argument('--log-json', action='store_true')
    
    # Main parser eredita parent (hidden da help, visibile in action)
    parser = argparse.ArgumentParser(
        parents=[parent],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Sertor CLI …'
    )
    parser.set_defaults(_suppress_parent_help=True)  # Suppress duplicate help
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Ogni subparser eredita parent
    search_parser = subparsers.add_parser('search', parents=[parent], 
                                           add_help=False, help='…')
    # …
    
    return parser
```

**Argparse quirk risolto:**
- Parent parser con `add_help=False` per evitare `-h` duplicato
- `argparse.SUPPRESS` per celare flag parent dall'help di subcommand
- Shared flags visibili in `args` namespace sia da `sertor -v search` che `sertor search -v`

**Esito:** ✅ Merge PR #4 (commit…) e raffinamenti. `sertor search -v "q"` e
`sertor -v search "q"` ora equivalenti. Test aggiunto: `test_cli_global_flags_order()`.

**Lezione:** Test unitari eseguivano comandi come lista `['search', 'query text']`,
saltando il parsing di flag globali. Test dovrebbe usare `shlex.split()` o
`subprocess.run()` per riprodurre CLI reale. **Scoperta da dogfooding interattivo,
non da test mock.**

---

## Impatto e Lezioni Apprese

### Impatto su Codebase
1. **Artefatti corretti:**
   - `src/sertor_cli/cli.py`: aggiunta `_force_utf8()` + refactor parser (parent + suppression)
   - `tests/test_cli_*.py`: 2 test di regressione
   
2. **Conformità Costituzione:** Entrambi i fix rispettano Principio VII (leggibilità) e IV
   (errore esplicito, non silent failure).

3. **Status MVP:** CLI e core sono ora **production-ready sul workflow locale** (Ollama +
   Chroma + Windows).

### Lezioni di Process

| Aspetto | Problema | Soluzione |
|---------|----------|-----------|
| **Test mock vs reale** | Capsys UTF-8 ≠ console Windows cp1252 | Esecuzione reale obbligatoria per platform-specific bugs |
| **Argparse parent flags** | Parser structure non testata end-to-end | Test con CLI reale (shlex.split o subprocess) |
| **Dogfooding timing** | Dopo implementation solo astratto | Dogfooding PRIMA di merge di fase finale (questo) |

### Prossimi Step (non MVP)
- Test cross-platform (Linux/Mac) una volta CI setup
- Documentazione CLI in `docs/` (help testo è minimo, serve user guide)
- Package installabile (`pip install sertor`) — attualmente `uv run src.sertor_cli…`

---

## Cross-References

- **FEAT-CLI-004:** [[cli-esecuzione-feat004]] — design e implementation di base CLI
- **FEAT-001:** [[implementazione-nucleo-retrieval]] — nucleo retrieval (riusato in `index`)
- **FEAT-002:** [[motore-baseline-feat002]] — motore ranking (riusato in `search`)
- **FEAT-003:** [[skill-wiki-feat003]] — skill wiki (riusato in `wiki index`)
- **Costituzione:** [[costituzione-v1]] — Principi I, IV, VII, IX confermati

