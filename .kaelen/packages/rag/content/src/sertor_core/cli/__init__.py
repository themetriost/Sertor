"""CLI package for RAG execution `sertor-rag` (FEAT-011).

**Thin** layer (Principio I): consumes the core (`build_indexer`, `build_facade`,
`build_baseline_engine`, `Settings`) via the composition root and formats the output. No retrieval
logic here and **no import-time side effects** (install ≠ run, FR-023): every operation requires
the explicit invocation of a subcommand.
"""
