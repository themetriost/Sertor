# Operation `rag-sync` — re-index the wiki in the RAG

> **Operation module.** Executor: **main flow only** (NOT the curator).
> For the **shared substrate** (D↔N boundary §2, log entry §6) see the playbook
> `wiki-playbook.md`. Only the specific procedure is described here.

Makes the wiki queryable via RAG (the wiki's "corpus" role).

1. Run `uv run --directory .sertor sertor-wiki-tools index --config wiki/wiki.config.toml --root .`. The CLI reads `[rag]` (isolated corpus,
   default `wiki`) and performs an idempotent rebuild-from-scratch; the embedding provider and the vector
   store are read from `.env` (see the env knobs documented in the install guide). **Do not** launch
   Python interpreters manually.
2. If the CLI reports an unconfigured embeddings provider (e.g. the cloud provider selected without
   credentials), **stop and report** (do not fail silently).
3. Append a log entry `rag-sync` with `documents`/`collection` from the `wiki.index/1` contract.
4. **Cost:** with the azure backend, embeddings are billable.
