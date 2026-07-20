# Implementation Plan: parità MCP per la lettura della memoria

**Branch**: `115-feat-010-memory-mcp-parity` · **Spec**: `./spec.md` · **Requisiti**: `../../requirements/memoria-conversazioni/feat-010-parita-mcp-lettura/requirements.md`

**Date**: 2026-07-20

## Summary

Aggiungere **tre tool MCP di sola lettura** in `src/sertor_mcp/server.py` — `memory_list`, `memory_show`,
`memory_search` — thin sopra i servizi core esistenti (`build_memory_reader` → `MemoryArchive.list_recent`/
`get`; `build_episodic_search` → `EpisodicSearch.search`), gated da `SERTOR_MEMORY` come la CLI. Nessun
cambio a `sertor-core` (solo consumo dei builder esistenti); nessun cambio ai 7 tool o allo startup.

## Technical Context

- **Linguaggio:** Python ≥ 3.11, stdlib + `mcp` (già dipendenza del server). Nessuna nuova dipendenza.
- **File toccati:**
  - `src/sertor_mcp/server.py` — 3 nuovi `@mcp.tool()` + helper di formattazione + builder memoizzati.
  - `docs/install.md` (o la sezione MCP dei doc) — elenco tool aggiornato (7 → 10) con la superficie memoria.
  - Test: `tests/unit/test_mcp_server.py` — registrazione dei 3 tool + comportamento (gate off/on, delega,
    formattazione, degrado).
- **Builder consumati (esistenti, gated → `None` se `SERTOR_MEMORY=false`):**
  - `build_memory_reader(settings)` → `MemoryArchive | None` (list_recent/get).
  - `build_episodic_search(settings)` → `EpisodicSearch | None` (search).
- **Default (da `Settings`, nessun nuovo):** `memory_list_limit`, `episodic_limit`, `episodic_snippet_tokens`.
- **Invarianti da preservare:** i 7 tool, warm-up/`_self_test`, schema `memory.sqlite`, gate CLL, builder di
  composition, formato risultati esistenti.

## Constitution Check (gate)

| # | Principio | Esito | Nota |
|---|---|---|---|
| — | **Missione / North Star** | ✅ PASS | Rende la **memoria episodica interrogabile nativamente dall'agente** via il vehicle nativo (MCP): rafforza il segnale reso all'agente (fusione code+doc + **memoria**) senza subprocess. |
| I | Core a dipendenze verso l'interno | ✅ PASS | Superficie **thin**: i tool delegano ai servizi core, zero logica di lettura/ricerca riscritta (come i 7 tool). |
| II | Provider/backend dietro boundary | ✅ N/A | Nessun provider/store nuovo (full-text = SQLite FTS5 esistente; nessun embedder). |
| III | Semplicità (YAGNI), unità piccole | ✅ PASS | 3 tool + 2 helper; nessuna astrazione nuova; semantico **rinviato** (non serve ora). |
| IV | Errori espliciti, niente null silenzioso | ✅ PASS | Memoria spenta → `status:"disabled"` esplicito (non `[]`); archivio assente → stato vuoto esplicito; guasto reale → `mcp.<tool>.error` via `_guard`. |
| V | Testabilità / qualità provata | ✅ PASS | Gate off/on, delega, formattazione, degrado → tutti unit-testabili (archivio SQLite in tmp). |
| VI | Idempotenza, determinismo, non-distruttività | ✅ PASS | Sola lettura: nessuna scrittura sull'archivio, nessun side-effect (il full-text crea l'indice FTS derivato lazily, come già la CLI). |
| VII | Leggibilità, lascia il codice più pulito | ✅ PASS | Segue lo stampo `_fmt`/`_guard`/`log_event` dei tool esistenti; la memoria diventa un blocco coeso nel server. |
| VIII | Config centralizzata | ✅ PASS | Nessun nuovo default; gate e limiti da `Settings` (unica fonte), come la CLI. |
| IX | Osservabilità | ✅ PASS | `log_event` per-tool; `memory_search` logga la query **hashata** (parità con `EpisodicSearch`). |
| X | Host-agnostico | ✅ PASS | Nessun path host-specifico; i tool viaggiano col server → installabili per costruzione. |
| XI | Consumo via vehicle | ✅ PASS | **È il cuore della feature:** porta la lettura memoria sul vehicle MCP (contratto pubblico), così i consumatori (specie esterni) non dipendono dalla CLI. |
| XII | Fail Loud, Fix the Cause | ✅ PASS | Il gate spento è **dichiarato** (`status:"disabled"`), non mascherato; il guasto reale resta visibile via `_guard`. |

**Esito gate: 12/12 + missione PASS.** Nessuna deviazione da giustificare.

## Design

### Builder memoizzati (come `_facade`/`_graph`)
```python
@lru_cache(maxsize=1)
def _memory_reader():   # MemoryArchive | None (gate SERTOR_MEMORY)
    return build_memory_reader(Settings.load())

@lru_cache(maxsize=1)
def _episodic():        # EpisodicSearch | None (gate SERTOR_MEMORY)
    return build_episodic_search(Settings.load())
```
Nota: `lru_cache` memoizza anche `None` (gate spento) → nessun rebuild ripetuto; a gate spento non si apre
alcun file (i builder tornano `None` senza toccare l'archivio) → **nessun costo d'avvio** (i tool non sono
esercitati nel warm-up; lo startup resta invariato).

### I tre tool (envelope con `status`)
```python
_DISABLED = {"status": "disabled",
             "hint": "set SERTOR_MEMORY=true in .sertor/.env to enable conversation memory"}

@mcp.tool()
def memory_list(limit: int = 0) -> dict:
    """List recent archived conversation sessions (most recent first)."""
    def _body():
        reader = _memory_reader()
        if reader is None:
            return _DISABLED
        lim = limit if limit and limit > 0 else Settings.load().memory_list_limit
        sessions = [{"session_key": s.session_key,
                     "captured_at": s.captured_at,
                     "turn_count": s.turn_count} for s in reader.list_recent(lim)]
        log_event(logging.INFO, "mcp.memory_list", results=len(sessions))
        return {"status": "ok", "sessions": sessions}
    return _guard("memory_list", _body)

@mcp.tool()
def memory_show(session_key: str) -> dict:
    """Show one archived session by key: its turns (index, role, ts, text)."""
    # reader is None → _DISABLED; get() → None → {"status":"ok","session":None}; else full turns
    ...

@mcp.tool()
def memory_search(query: str, k: int = 0) -> dict:
    """Full-text search the conversation archive: 'have we talked about X before?'."""
    # search is None → _DISABLED; else EpisodicSearch.search(SearchQuery(text=query, limit=..., snippet_tokens=...))
    # hits → {session_key, captured_at, role, turn_index, snippet, score}; query hashed in the event (EpisodicSearch already does)
    ...
```
- **`limit`/`k` = 0** ⇒ usa il default di `Settings` (evita un `None` nel tipo MCP; 0 = «non specificato»).
- **`memory_show`**: testo **pieno** del turno (è «mostra la sessione»). **`memory_search`**: snippet da
  `EpisodicSearch` (`snippet_tokens`), niente troncamento aggiuntivo lato server.
- **`captured_at`**: epoch float, come dal core (il client formatta; parità coi dati CLI).

### Instructions del server
Aggiornare la stringa `instructions` di `FastMCP` per menzionare la superficie memoria (list/show/search)
e il gate privacy, così l'agente sa che esiste ed è opt-in.

## Test (`tests/unit/test_mcp_server.py`)
- **registrazione:** `list_tools()` include `memory_list`/`memory_show`/`memory_search` (10 tool totali).
- **gate OFF** (default): ogni tool → `{"status":"disabled", ...}` (monkeypatch `SERTOR_MEMORY` assente).
- **gate ON** (archivio SQLite in tmp con 1-2 sessioni): `memory_list` → sessioni ordinate recency;
  `memory_show(key)` → turni in ordine con role/text; `memory_show(assente)` → `session:None`;
  `memory_search("parola")` → hit con snippet/score; query non-matchante → `hits:[]`.
- **delega/parità:** i dati coincidono con quelli dei servizi core diretti (stesso archivio).
- **degrado:** archivio assente → `status:"ok"` con collezione vuota, nessun crash.
- **osservabilità:** `memory_search` non logga il testo di query in chiaro (query hashata).
- **non-regressione:** `test_three_search_tools_registered` resta verde.

## Out of scope (rinviato)
- Ricerca **semantica** via MCP (doppio gate) → nuova FEAT dell'epica se emerge il bisogno.
- Scrittura via MCP; cambi di schema; parità di *scrittura*.

## Phase completion
- [x] requirements · [x] specify · [x] clarify (scope sciolto: list+show+search full-text) · [x] plan (+ Constitution 12/12)
- [x] tasks · [x] implement

## Verifica (implement)
- **Unit test verdi** (7 nuovi in `tests/unit/test_mcp_server.py`): registrazione dei 3 tool (10 totali) ·
  **gate OFF** → `status:"disabled"` su tutti e tre · **gate ON** (archivio SQLite reale in tmp) list
  recency-first / show turni ordinati + `session:null` su chiave assente / search hit con snippet+score +
  `hits:[]` su non-match · **parità** coi servizi core · **degrado** su archivio assente · **query hashata**
  (nessun testo in chiaro nei log). Non-regressione `test_three_search_tools_registered` verde.
- **Gate:** `uv run pytest -m "not cloud"` → **1212 passed** (1 xfail packaging noto; **2 fail ambientali**
  `test_clean_install_uv[sertor|sertor-flow]`: HEAD al SHA di master pre-commit → nome-branch non su origin,
  **skippano post-commit**, verdi in CI). `ruff check .` pulito. **`sertor-core` INVARIATO** (solo
  `src/sertor_mcp/server.py` + test + doc).
- **Prova LIVE (ON, archivio reale del dogfood, `memory.sqlite` 14MB, `SERTOR_MEMORY=true`):** `memory_list`
  → 3+ sessioni (fino a 387 turni), `memory_show` → sessione a 224 turni pieni, `memory_search("sertor")` →
  hit con score; l'evento d'osservabilità mostra `query_hash=… query_len=6` (**query hashata, mai in
  chiaro** — REQ-009 provato LIVE). Path **OFF** provato dal unit test (sul dogfood la memoria è accesa).
- **Doc utente:** `docs/retrieval.md` (7 → 10 tool + sezione *Conversation memory* + righe tabella) +
  `docs/reference.md` (superficie MCP).
- **Deferred a post-merge (come per ogni cambio di codice MCP):** LIVE end-to-end **over-stdio** via il client
  MCP — richiede il **riavvio/riconnessione** del server (i tool si registrano all'avvio); il runtime `.sertor`
  serve i tool nuovi dopo il re-lock post-merge + reconnect.
