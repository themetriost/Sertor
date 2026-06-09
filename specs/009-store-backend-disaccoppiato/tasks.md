# Tasks: Disaccoppiamento store ↔ provider di embeddings (FEAT-009)

**Plan**: [plan.md](plan.md) · **Spec**: [spec.md](spec.md)

Ordinati per dipendenze. `[P]` = parallelizzabile (file distinti, nessuna dipendenza reciproca).

## Fase 1 — Configurazione (foundational)
- **T001** `config/settings.py`: aggiungi campo `store_backend` e leggi `SERTOR_STORE_BACKEND`
  (default = `RAG_BACKEND`). *(FR-001, FR-002)*

## Fase 2 — Cablaggio e adapter (dipende da T001)
- **T002** `composition.py`: `build_store` e `collection_name` keyano su `settings.store_backend`. *(FR-003)*
- **T003** `[P]` `adapters/embeddings/azure.py`: rileva la superficie v1 e ometti `api-version`. *(FR-004)*

## Fase 3 — Test (dipende dal codice)
- **T004** `[P]` `tests/unit/test_settings.py`: default `store_backend`=`RAG_BACKEND`; override env. *(US1 AS-2)*
- **T005** `[P]` `tests/unit/test_composition.py`: Azure embeddings + Chroma store; naming su `store_backend`.
  *(US1 AS-1/AS-3)*
- **T006** `[P]` `tests/unit/test_embeddings.py`: v1 omette `api-version`; classico lo invia. *(US2)*
- **T007** `tests/unit/test_mcp_server.py`: neutralizza `Settings.load` in `_use` (isolamento `os.environ`).

## Fase 4 — Documentazione e verifica
- **T008** `[P]` `.env.example`: documenta `SERTOR_STORE_BACKEND` + nota endpoint v1.
- **T009** Verifica: `uv run pytest -m "not cloud"` verde + `uv run ruff check src tests` pulito. *(SC-002)*

## Fase 5 — Attivazione (post-merge, non versionata)
- **T010** `.env` locale: `SERTOR_STORE_BACKEND=local`; costruisci `.index-sertor` con
  `build_indexer(Settings.load()).index('.', rebuild=True)`. *(SC-001)*
- **T011** Verifica end-to-end: `build_facade(...).search_combined('composition root')` → hit reali;
  tool MCP `sertor-rag` ritornano chunk del repo di produzione. *(SC-001)*

## Esecuzione parallela d'esempio
T003 in parallelo a T002; T004/T005/T006/T008 insieme dopo che il codice compila.
