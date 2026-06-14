# Quickstart — Ricerca episodica full-text locale (feature 033)

Come esercitare la ricerca episodica come **libreria** (Principio I: nessuna CLI/UI necessaria).
Tutto in locale, offline, su `tmp_path` con archivio sintetico — nessun cloud, nessuna rete.

## Prerequisiti

- Archivio di FEAT-001 presente: `<index_dir>/memory.sqlite` con `sessions` + `turns`. Per il test
  basta scrivere righe sintetiche (o usare `MemoryArchive.upsert` di FEAT-001).
- `SERTOR_MEMORY=true` per abilitare la memoria (privacy-by-default: senza opt-in nessun file aperto).
- `sqlite3` con FTS5 (verificato nel venv del progetto: Python 3.12, SQLite 3.50 → disponibile).

## Uso come libreria

```python
from sertor_core.composition import build_episodic_search
from sertor_core.services.episodic_search import SearchQuery

search = build_episodic_search()          # None se SERTOR_MEMORY=false
if search is not None:
    results = search.search(SearchQuery(text="Azure"))
    for hit in results.hits:
        print(hit.captured_at, hit.role, f"[{hit.session_key}#{hit.turn_index}]", hit.snippet)
```

### Finestra temporale (FR-005/006)

```python
import time
week_ago = time.time() - 7 * 86400
# solo da una settimana fa in poi
search.search(SearchQuery(text="deciso", since=week_ago))
# solo fino a una data
search.search(SearchQuery(text="deciso", until=week_ago))
# since > until → InvalidTimeWindowError
```

### Ordinamento e limite (FR-008/009/010)

```python
search.search(SearchQuery(text="retrieval", order="recency"))   # più recenti prima
search.search(SearchQuery(text="retrieval", limit=5))           # al più 5 risultati
```

## Test offline (pattern del core)

Archivio sintetico in `tmp_path`, nessun mock di rete necessario (la ricerca è puro SQLite locale):

```python
def test_finds_turn_by_keyword(tmp_path):
    from sertor_core.adapters.memory.archive import MemoryArchive
    from sertor_core.domain.memory import ArchivedSession, TranscriptTurn
    from sertor_core.services.episodic_search import EpisodicSearch, SearchQuery

    MemoryArchive(tmp_path).upsert(ArchivedSession(
        session_key="s1", project_id="p", captured_at=1000.0, adapter_kind="x",
        turns=(TranscriptTurn(index=0, role="user", text="decidiamo Azure", ts=1000.0),),
    ))
    results = EpisodicSearch(tmp_path).search(SearchQuery(text="Azure"))
    hit = results.hits[0]
    assert hit.session_key == "s1" and hit.turn_index == 0
    assert "Azure" in hit.snippet         # C-CITE / C-SNIP

def test_missing_archive_is_empty_not_error(tmp_path):
    from sertor_core.services.episodic_search import EpisodicSearch, SearchQuery
    assert EpisodicSearch(tmp_path / "nope").search(SearchQuery(text="x")).hits == ()  # P-NOARCH
```

## Verifiche chiave (mappate ai criteri)

- **SC-001/SC-002**: il turno con la parola compare, con tutti i campi di citazione.
- **SC-003**: con finestra, zero turni fuori intervallo.
- **SC-004**: nessun traffico di rete (è solo SQLite locale — niente da mockare).
- **SC-005**: archivio assente/vuoto/voce malformata → stato vuoto/skip, mai eccezione.
- **SC-006**: latenza percettivamente immediata (misurato <0.1 ms su 5062 turni dogfood; budget
  < 200 ms p95).
- **SC-007**: stessa ricerca su archivi di provenienza/host diversi → equivalente (host-agnostico).
- **SC-008**: sessione appena archiviata ricercabile alla prima `search` (trigger di sync).

## Note operative

- L'indice FTS5 vive **dentro** `memory.sqlite` (git-ignored); cancellarlo non perde dati — si
  ricostruisce da `turns`.
- Manopole: `SERTOR_EPISODIC_LIMIT` (20), `SERTOR_EPISODIC_SNIPPET_TOKENS` (12).
- La query nel log dell'evento `episodic_search` è **hashata**, mai in chiaro.
