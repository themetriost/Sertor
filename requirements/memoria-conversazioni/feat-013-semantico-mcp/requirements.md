# E4-FEAT-013 — Ricerca semantica della memoria via MCP

**Epica:** [`memoria-conversazioni`](../epic.md) · **Tipo:** feature (parità MCP) · **Priorità:** Should
**Follow-up di** [FEAT-010](../feat-010-parita-mcp-lettura/requirements.md) (parità MCP lettura, full-text) e
[FEAT-004](../ricerca-semantica-opt-in/requirements.md) (ricerca semantica CLI).

## Contesto

FEAT-010 ha portato la lettura della memoria sul vehicle nativo dell'agente (MCP): `memory_search`
(full-text FTS5), `memory_list`, `memory_show`. La **ricerca semantica** (FEAT-004, per *significato* non
per parola) resta però **solo CLI** (`sertor-rag memory search --semantic`). Un agente che interroga via
MCP non può fare la ricerca semantica — asimmetria col principio «i consumatori esterni usano l'MCP, non la
CLI». Il gate è **a due strati** (`SERTOR_MEMORY` + `SERTOR_MEMORY_SEMANTIC`) e la CLI lo consuma via
`build_memory_semantic_index` → `None` se manca uno dei due (`src/sertor_core/cli/__main__.py:493`).

## Requisiti (EARS)

- **REQ-001** — Il tool MCP `memory_search` DEVE accettare un parametro **`semantic`** (bool, default
  `false`). Con `semantic=false` il comportamento è **invariato** (full-text FTS5, FEAT-010).
- **REQ-002** — QUANDO `semantic=true`, il sistema DEVE instradare alla ricerca **semantica** (per
  significato), consumando lo **stesso** gate a due strati della CLI (`build_memory_semantic_index` →
  `SemanticMemoryQuery` → `index.search`), senza reimplementare la logica.
- **REQ-003** — QUANDO `semantic=true` e la memoria è spenta (`SERTOR_MEMORY` off), il sistema DEVE
  ritornare `{"status": "disabled"}` che nomina `SERTOR_MEMORY` (parità con gli altri tool memoria).
- **REQ-004** — QUANDO `semantic=true`, `SERTOR_MEMORY` on ma `SERTOR_MEMORY_SEMANTIC` off, il sistema
  DEVE ritornare `{"status": "disabled"}` che nomina **`SERTOR_MEMORY_SEMANTIC`** e indica il backfill
  `memory index-semantic` — **mai** un fallback silenzioso al full-text (parità con la CLI, REQ-015 di
  FEAT-004).
- **REQ-005** — Gli hit semantici DEVONO usare la **stessa forma** del full-text (`session_key`,
  `captured_at`, `role`, `turn_index`, `snippet`, `score`), ordinati per similarità.
- **REQ-006** — La query NON DEVE mai comparire in chiaro nella telemetria (parità con `EpisodicSearch` e
  `SemanticMemorySearch`, che hashano la query).
- **REQ-007** — `sertor-core` NON DEVE cambiare: la feature vive in `src/sertor_mcp/server.py` (thin sopra
  i servizi core), come FEAT-010.

## Fuori scope

- Backfill dell'indice semantico via MCP (`memory index-semantic` resta CLI — è una scrittura, non lettura).
- Nuovi tool MCP: si **estende** `memory_search` (rispecchia il flag `--semantic` della CLI), non se ne
  aggiunge uno.

## Verifica

- Unit: `semantic=false` → full-text invariato; `semantic=true` gate-off (memoria) → disabled nomina
  `SERTOR_MEMORY`; gate-off (semantico) → disabled nomina `SERTOR_MEMORY_SEMANTIC`; gate-on → delega a
  `SemanticMemorySearch` (fake) e forma hit corretta; query hashata.
- LIVE (deferred al reconnect del server): `memory_search(query, semantic=true)` sull'archivio reale con
  entrambi i gate on + indice semantico backfillato.
