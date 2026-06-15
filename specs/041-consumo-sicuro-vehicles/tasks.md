# Tasks: Consumo sicuro per costruzione (Gruppo A, Principio XI)

**Feature**: 041-consumo-sicuro-vehicles · **Branch**: `041-consumo-sicuro-vehicles`
**Input**: [plan.md](plan.md) · [spec.md](spec.md)

Cambio chirurgico (composition root + un test). Design in `plan.md` (D1-D4). Constitution PASS 11/11.

## Tasks

- [x] T001 Helper `_wire_runtime(settings)` in `src/sertor_core/composition.py` — chiama
  `enable_observability(settings)` (idempotente, no-op se off); home dei concern trasversali.
- [x] T002 Chiamata `_wire_runtime(settings)` nelle 5 factory consumer-entry di `composition.py`:
  `build_indexer`, `build_facade`, `build_engine`, `build_baseline_engine`, `build_graph_service`.
- [x] T003 Test gap-closure `tests/unit/test_composition.py::test_consumer_factories_wire_runtime` —
  ogni factory consumer-entry cabla il runtime (osservabilità), con `enable_observability` mockato.
- [x] T004 Non-regressione: `test_index_wires_observability` (CLI) e `test_main_wires_observability`
  (MCP) restano verdi (CLI/MCP invariati; attivazione idempotente).
- [x] T005 Gate: intera suite root verde (**564 passed**, 1 deselected cloud) + ruff pulito.
- [ ] T006 Post-merge: re-index del corpus `sertor` **via la CLI** (`sertor-rag index .`, Principio XI/
  rituale §5) — verificare che ora l'evento `index` finisce in telemetria (chiusura del gap end-to-end).

## Note
- FR-007 (restringimento `__init__`) NON eseguito (Should rinviato).
- `research.md` non separato: il design (D1-D4) è in `plan.md` (cambio compatto).
