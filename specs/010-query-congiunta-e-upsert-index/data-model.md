# Data Model — Query congiunta multi-collezione & `upsert-index` in CLI

**Feature**: `010-query-congiunta-e-upsert-index` · **Date**: 2026-06-10

Nessuna nuova entità di dominio: la feature **estende** porte, configurazione, errori e contratti
esistenti. Qui il delta completo.

## Entità riusate (invariate)

| Entità | Dove | Uso nella feature |
|---|---|---|
| `RetrievalResult` | `domain/entities.py` | unità del merge; `score: float` è la chiave d'ordinamento, `chunk_id` il tie-break |
| `DocTypeFilter` | `domain/ports.py` | la ricerca combinata multi-collezione interroga con `"both"` |

## Porte (delta)

### `VectorStore` — nuovo metodo `list_collections`

```python
def list_collections(self) -> list[str]:
    """Nomi delle collezioni esistenti nel backend (per il rilevamento provider, FR-009)."""
```

- **Implementazioni**: `ChromaStore` → `client.list_collections()`; `AzureSearchStore` →
  `SearchIndexClient.list_index_names()` (import lazy); `InMemoryStore` (mock) → chiavi del dict.
- **Errori**: backend irraggiungibile → `VectorStoreError` (coerente con gli altri metodi).

## Configurazione (delta)

### `Settings.extra_corpora: tuple[str, ...] = ()`

- Letta da `SERTOR_EXTRA_CORPORA` (lista separata da virgole, helper `_split_env` esistente).
- Semantica: corpora **aggiuntivi** che la ricerca combinata interroga oltre al corpus primario
  (`Settings.corpus`). Default vuoto = comportamento odierno (FR-006/SC-003).
- Le collezioni si derivano in `composition.build_facade()` con la `collection_name()` esistente
  applicata a `replace(settings, corpus=c)` — il provider è quello dell'embedder della facade.

## Servizi (delta)

### `RetrievalFacade` — fan-out e merge

- Costruttore esteso (keyword-only, retro-compatibile):
  `extra_collections: Mapping[str, str] | None = None` — mappa **corpus → collezione attesa**
  (serve il nome del corpus per il messaggio di `ProviderMismatchError` e per il rilevamento via
  prefisso `{corpus}__`).
- `search_combined()`: se `extra_collections` è vuota → percorso odierno invariato; altrimenti
  fan-out: 1 embed della query → `store.query(coll, vector, k, "both")` per ogni collezione
  disponibile → merge ordinato per `(-score, chunk_id)` → troncamento a `k`.
- Stato per-collezione nel fan-out:
  - attesa **esiste** → contribuisce al merge;
  - attesa **assente**, nessuna collezione `{corpus}__*` → degradazione morbida (warning, FR-004);
  - attesa **assente**, esiste `{corpus}__<altro-provider>` → `ProviderMismatchError` (FR-009).
- `search_code` / `search_docs`: **invariati** (FR-006bis).

## Errori (delta)

### `ProviderMismatchError(SertorError)` — `domain/errors.py`

```python
ProviderMismatchError(message, *, corpus: str, expected: str, found: list[str])
```

Sollevata dalla ricerca combinata quando un corpus bersaglio è indicizzato con un provider diverso
da quello corrente. Messaggio azionabile: indica il corpus, la collezione attesa e quelle trovate
(es. «reindicizzare il corpus con il provider corrente o cambiare provider»).

## Contratti wiki (delta)

### `UpsertIndexResult` — `wiki_tools/contracts.py`, schema `wiki.upsert_index/1`

| Campo | Tipo | Semantica |
|---|---|---|
| `written` | `bool` | `True` se l'indice è stato modificato |
| `action` | `str` | `"insert"` \| `"update"` \| `"noop"` |
| `page` | `str` | identità della riga (path relativo POSIX della pagina) |
| `schema` | `str` | `"wiki.upsert_index/1"` |

### `registry.upsert_index` — firma aggiornata

`upsert_index(profile, page, summary) -> UpsertIndexResult` (prima: `bool`; nessun consumatore
esterno esistente). **Validazione** (FR-018): `summary` viene trimmato; se vuoto/solo whitespace o
con newline interni → `ConfigError` (nessuna scrittura). Idempotenza e update-in-place invariati.

## Transizioni di stato (riga d'indice)

```
assente ──insert──▶ presente(S) ──update (S'≠S)──▶ presente(S')
                      │ ▲
                      └─noop (stesso S)─┘
```
