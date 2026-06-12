# Contract — Porta `CodeGraph`

Settima porta del dominio (Protocol, structural typing). Il core dipende SOLO da questa porta;
l'adapter concreto (`NetworkxCodeGraph`, JSON + networkx) vive in `adapters/graph/`.

## Metodi

### `build(corpus: str, data: GraphData) -> None`
- Sostituzione integrale dell'artefatto del corpus (snapshot intero, idempotente: stessi input
  → stesso artefatto, FR-008).
- Scrittura atomica (tmp + rename); un fallimento non lascia artefatti corrotti.
- NON richiede la libreria di grafi (pura serializzazione): `index()` produce sempre il grafo
  anche senza l'extra installato (research G1).
- `data` vuoto → artefatto vuoto valido.

### `find_symbol(name) / who_calls(name) / related_docs(name) / get_context(name)`
- Precondizione comune: grafo presente — assente → `GraphNotFoundError` («costruisci il grafo
  (index) prima di interrogare», FR-007); extra `graph` non installato → `ConfigError`
  azionabile con l'istruzione d'installazione (DA-5, import pigro nei metodi di query).
- Simbolo assente → risultato vuoto esplicito (liste/bundle vuoti), MAI eccezione (FR-017).
- Match esatto sul `name` (kinds: class/function/method); risultati ordinati
  deterministicamente (per `ref`); ogni hit è citabile: `ref = path#qualname` (FR-018).
- `get_context`: sezioni (definitions/callers/callees/bases/docs) limitate dai knob di
  Settings (default 10/8/8, FR-016).

### `exists(corpus: str) -> bool`
- True ⟺ artefatto presente; formato sconosciuto/corrotto NON è una risposta silenziosa:
  la query successiva solleva `ConfigError`.

### `reset(corpus: str) -> None`
- Elimina l'artefatto; assente = no-op.

## Namespacing

Per **solo corpus** (`<index_dir>/graph/<corpus>.json`): il grafo non dipende dal provider di
embeddings (deliberatamente diverso da collezioni vettoriali e sidecar lessicale — research G5).

## Mock di test

`FakeCodeGraph` in `tests/fixtures/mocks.py`: dict in memoria, stessa semantica, nessun file
system né networkx (NFR-03).
