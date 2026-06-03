# Contratto — Indicizzazione del wiki nel RAG (`index_wiki`)

Gruppo E: indicizza le pagine del wiki nel corpus documentale del RAG **riusando il nucleo**
(FEAT-001/002). Non reimplementa ingestione/chunking/embeddings/store.

## Interfaccia

```python
def index_wiki(wiki_root: Path | str, settings: Settings | None = None) -> IndexReport:
    """Full rebuild idempotente del wiki nel corpus RAG configurato."""
```

Internamente: costruisce embedder+store dal composition root del nucleo e invoca
`IndexingService(...).index(wiki_root, rebuild=True)`.

## Contratto comportamentale

| # | Precondizione | Comportamento | Postcondizione | Req |
|---|---------------|---------------|----------------|-----|
| 1 | wiki + RAG configurato | ingerisce tutti i `.md` sotto la radice wiki, metadati doc/markdown | `IndexReport` con n. documenti; query doc pertinente trova pagine wiki | REQ-040/042, SC-004 |
| 2 | corpus con chunk wiki esistenti | **full rebuild** | nessun duplicato per lo stesso file | REQ-041 |
| 3 | re-index file invariato | id chunk = path relativo | stessa identità del chunk | REQ-051 |
| 4 | chunk wiki vs sorgenti | nessun boost di ranking | peso paritario | REQ-044 |
| 5 | RAG non configurato/irraggiungibile | abort | `VectorStoreError`/`EmbeddingError`; indice esistente non corrotto | REQ-043 |
| 6 | radice vuota / senza Markdown | warning, nessuna modifica all'indice | indice immutato | REQ-045 |

## Invarianti

- Riuso del nucleo: le proprietà (rebuild idempotente, id=path, errore esplicito, peso paritario) sono
  **ereditate** da FEAT-001/002, non reimplementate (DRY).
- Le pagine wiki entrano come corpus `doc` paritario (DA-W1, REQ-044).

## Distinzione errore vs avviso (Principio IV)

- **Radice vuota** = avviso, nessun errore, indice immutato (REQ-045).
- **RAG irraggiungibile** = errore esplicito, abort, indice non corrotto (REQ-043).

## Test (integration, su sandbox)

Indicizza un wiki sandbox (`FakeEmbedder`+`ChromaStore` temp) → query documentale trova una pagina
wiki (#1); re-index senza duplicati (#2/#3); radice vuota → warning + indice immutato (#6); store
rotto → errore (#5).
