# Tasks: parità MCP per la lettura della memoria

**Branch**: `115-feat-010-memory-mcp-parity` · **Plan**: `./plan.md`

Ordine dipendency-aware. `[P]` = parallelizzabile.

## Implementazione (server MCP)
- [ ] **T-1** — In `src/sertor_mcp/server.py`: import di `build_memory_reader`/`build_episodic_search`
  (da `sertor_core.composition`) e `SearchQuery` (da `episodic_search`); builder memoizzati `_memory_reader()`
  e `_episodic()` (`lru_cache`, memoizza anche `None`). (REQ-005)
- [ ] **T-2** — Helper: costante `_DISABLED` (envelope `status:"disabled"` + hint) + `_session_summary_dict`
  / `_turn_dict` / `_episodic_hit_dict` per la formattazione. (REQ-007)
- [ ] **T-3** — `@mcp.tool() memory_list(limit=0)` → `{status, sessions:[…]}`; `limit<=0` ⇒
  `Settings.memory_list_limit`; gate `None` → `_DISABLED`; `_guard`+`log_event`. (REQ-001/004/008)
- [ ] **T-4** — `@mcp.tool() memory_show(session_key)` → `{status, session:{…, turns:[…]}}`; `get()==None`
  → `session:None`; testo pieno dei turni; gate + `_guard`+`log_event`. (REQ-002/004/006/008)
- [ ] **T-5** — `@mcp.tool() memory_search(query, k=0)` → `{status, hits:[…]}`; `k<=0` ⇒ `episodic_limit`;
  `SearchQuery(text, limit, snippet_tokens=episodic_snippet_tokens)`; gate + `_guard` (la query è già
  hashata dall'evento di `EpisodicSearch`). (REQ-003/004/008/009)
- [ ] **T-6** — Aggiornare la stringa `instructions` di `FastMCP`: menziona la superficie memoria
  (list/show/search) e il gate `SERTOR_MEMORY` (opt-in). (REQ-004)

## Test
- [ ] **T-7 [P]** — `tests/unit/test_mcp_server.py`: registrazione dei 3 tool (10 totali) + non-regressione
  `test_three_search_tools_registered`. (REQ-001/002/003)
- [ ] **T-8 [P]** — Gate OFF (default): i 3 tool → `{status:"disabled"}` (nessun file aperto). (REQ-004)
- [ ] **T-9** — Gate ON (archivio SQLite in tmp, 1-2 sessioni via `MemoryArchive.upsert`): `memory_list`
  ordinata recency · `memory_show` turni in ordine + `session:None` su chiave assente · `memory_search`
  hit con snippet/score + `hits:[]` su query non-matchante · **parità** coi servizi core diretti.
  (REQ-001/002/003/005/007)
- [ ] **T-10** — Degrado: archivio assente con memoria ON → `status:"ok"` collezione vuota, no crash;
  `memory_search` non logga il testo di query in chiaro. (REQ-008/009)

## Doc utente & DoD host-facing
- [ ] **T-11** — Doc utente (`docs/install.md` sezione MCP / `docs/reference.md`): superficie MCP **7 → 10**
  tool, con la triade memoria e il gate `SERTOR_MEMORY` (opt-in, privacy). (REQ-010)

## Gate & consegna
- [ ] **T-12** — `uv run pytest -m "not cloud"` verde + `uv run ruff check .` pulito; conferma `sertor-core`
  invariato (solo `sertor_mcp` + doc/test).
- [ ] **T-13** — Prova LIVE: con `SERTOR_MEMORY=true` su archivio reale, i 3 tool via server MCP vs CLI
  coerenti; memoria spenta → `status:"disabled"`. *(Il server MCP va riavviato per servire i tool nuovi:
  la registrazione avviene all'avvio.)*
- [ ] **T-14** — Commit branch + PR (configuration-manager); a valle merge: EXEC + epic.md (FEAT-010 ✅) +
  re-lock + re-index + smoke MCP + wiki (record/distill/lint).
