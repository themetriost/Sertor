# Contract — Library: `FusedResults` + `RetrievalFacade.search_combined` (070)

Contratto della **superficie di libreria** (consumata dai vehicles, esercitata dai test — Principio
XI). Breaking change volontario, circoscritto a `search_combined`.

## Entità `FusedResults` (`sertor_core.domain.entities`)

```python
@dataclass(frozen=True)
class FusedResults:
    docs: tuple[RetrievalResult, ...] = ()
    code: tuple[RetrievalResult, ...] = ()
    def flatten(self) -> list[RetrievalResult]: ...
```

- **Frozen, hashable-by-value**, nessun import SDK (Principio I).
- `docs`/`code` rank-ordered, **ciascuna col proprio top-k** (budget separato).
- `flatten()` **deterministico**: interleave per rank `docs[0],code[0],docs[1],code[1],…`; avanzi
  della lista più lunga in coda nel loro ordine.

### Garanzie `flatten()`

| Input | Output |
|---|---|
| `docs=[d0,d1]`, `code=[c0,c1]` | `[d0,c0,d1,c1]` |
| `docs=[d0,d1,d2]`, `code=[c0]` | `[d0,c0,d1,d2]` |
| `docs=[]`, `code=[c0,c1]` | `[c0,c1]` |
| `docs=[]`, `code=[]` | `[]` |
| stesso input, ri-eseguito | **stessa** lista (FR-002/SC-003) |

## `RetrievalFacade.search_combined`

```python
def search_combined(self, query: str, k: int | None = None) -> FusedResults
```

| Aspetto | Contratto |
|---|---|
| Ritorno | `FusedResults` (mai `list[RetrievalResult]`) — **breaking** vs prima |
| Budget | `docs` e `code` ciascuna fino a `k` (o `default_k`); **separato**, mai condiviso (FR-001) |
| Composizione | `docs` = percorso `doc`; `code` = percorso `code` (stessi percorsi di `search_docs`/`search_code`) |
| Indice assente (primario) | coppia con liste vuote + warning `no_index` (policy tollerante invariata) |
| Una sola superficie ha hit | coppia con una lista popolata, l'altra `()` (Edge Cases) |
| `extra_collections` (010) | fan-out per-tipo: ogni lista filtra `doc_type` su tutte le target; `ProviderMismatchError` conservato |
| Determinismo | stessa query + indice → stessa coppia (Principio VI) |
| `search_code`/`search_docs` | **invariati** (FR-003/SC-002) |

## Test attesi (unit, F.I.R.S.T.)

- `flatten()`: i 4 casi della tabella + determinismo (ri-esecuzione).
- `search_combined` ritorna `FusedResults`; `docs` solo `DocType.DOC`, `code` solo `DocType.CODE`.
- budget separato: con un indice in cui i doc hanno score più alti, `code` **non** è vuota (la
  causa-radice del budget condiviso non si ripresenta) — SC-001/US1.
- indice senza codice → `code=()`, `docs` popolata (Edge Cases).
- `search_code`/`search_docs` invariati (stesso tipo e valori di prima) — SC-002.
