# Operation `rag-sync` — re-index the wiki in the RAG

> **Operation module.** Executor: **main flow only** (NOT the curator).
> For the **shared substrate** (D↔N boundary §2, log entry §6) see the playbook
> `wiki-playbook.md`. Only the specific procedure is described here.

Makes the wiki queryable via RAG (the wiki's "corpus" role).

1. Run `sertor-wiki-tools index --config wiki/wiki.config.toml --root .`. The CLI reads `[rag]` (isolated corpus,
   default `wiki`) and performs an idempotent rebuild-from-scratch; the backend (local Chroma / Azure AI Search)
   depends on `RAG_BACKEND` in `.env`. **Do not** launch Python interpreters manually.
2. If the CLI reports an unconfigured embeddings provider (e.g. `RAG_BACKEND=azure` without credentials),
   **stop and report** (do not fail silently).
3. Append a log entry `rag-sync` with `documents`/`collection` from the `wiki.index/1` contract.
4. **Cost:** with the azure backend, embeddings are billable.
