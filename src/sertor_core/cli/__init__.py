"""Pacchetto CLI di esecuzione RAG `sertor-rag` (FEAT-011).

Layer **sottile** (Principio I): consuma il core (`build_indexer`, `build_facade`,
`build_baseline_engine`, `Settings`) via composition root e formatta l'output. Nessuna logica di
retrieval qui dentro e **nessun side-effect a import-time** (install ≠ run, FR-023): ogni operazione
richiede l'invocazione esplicita di un sottocomando.
"""
