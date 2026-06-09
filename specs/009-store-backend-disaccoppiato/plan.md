# Implementation Plan: Disaccoppiamento store ↔ provider di embeddings (FEAT-009)

**Branch**: `spec/009-store-backend-disaccoppiato` · **Spec**: [spec.md](spec.md)

## Sintesi tecnica

Modifica chirurgica al nucleo `sertor-core`: (1) nuovo selettore `store_backend` nella configurazione
centralizzata, **distinto** dal provider di embeddings (`backend`), così che `build_store` e
`collection_name` ne dipendano; (2) `AzureEmbedder` compatibile con la superficie **v1** dell'endpoint
(niente `api-version`). Abilita la combinazione *embeddings Azure + store Chroma locale* necessaria per
l'indice di dogfooding del corpus `sertor`. Nessuna nuova dipendenza, offline-testabile.

Il design riusa quello già abbozzato su una branch sperimentale stale (`feat/decouple-store-backend`), che
**non viene mergiata** (divergente: regredisce la rotazione log FEAT-008 e rimuove `wiki_tools`).
**Escluso** dal port: `build_llm`/porta LLM (riguarda la distillazione, non l'indice).

## Constitution Check

| Principio | Esito | Nota |
|---|---|---|
| I — Dipendenze verso l'interno | ✅ | la scelta resta nel composition root; nessun SDK nel domain/servizi |
| II — Boundary & local-first | ✅ **rafforzato** | lo store locale diventa scegliibile a prescindere dal provider di embeddings (cloud↔locale indipendenti) |
| III — YAGNI | ✅ | un campo di config + 2 riferimenti + un flag nell'adapter; nessuna nuova astrazione |
| IV — Errori espliciti | ✅ | invariato; `AzureEmbedder` continua ad avvolgere gli errori in `EmbeddingError` |
| V — Testabilità | ✅ | unit test offline con client httpx iniettato e mock; F.I.R.S.T. |
| VI — Idempotenza & non-distruttività | ✅ | invariato; `collection_name` resta deterministico |
| VII — Leggibilità | ✅ | naming di dominio (`store_backend`); commenti d'intenzione |
| VIII — Config centralizzata | ✅ **rafforzato** | nuova manopola `SERTOR_STORE_BACKEND` in `Settings`, nessun default hard-coded nei componenti |
| IX — Osservabilità | ✅ | il log di `index`/`retrieve` già riporta provider/backend |
| X — Host-agnostico (NON-NEG.) | ✅ | la scelta è pura configurazione; nessuna assunzione d'ospite nel corpo |

**Complexity Tracking:** vuoto (nessuna violazione; la modifica *aumenta* la conformità a II e VIII).

## Design

### Configurazione (`config/settings.py`)
- Nuovo campo `store_backend: str = "local"` (provider embeddings = `backend`; store = `store_backend`).
- `load()`: `store_backend = os.getenv("SERTOR_STORE_BACKEND", os.getenv("RAG_BACKEND", "local"))` —
  default = `RAG_BACKEND` (retro-compatibile; il decoupling si attiva solo settando la variabile).

### Composition root (`composition.py`)
- `build_store`: seleziona su `settings.store_backend` (invece di `backend`).
- `collection_name`: il vincolo di naming è una proprietà dell'**Azure Search index** → key su
  `settings.store_backend`.

### Adapter embeddings (`adapters/embeddings/azure.py`)
- `_v1 = "/openai/v1" in endpoint`; in `_embed_batch`: `params=None if self._v1 else {"api-version": …}`.

### Test (`tests/unit/`)
- `test_settings.py`: default `store_backend` = `RAG_BACKEND`; override via `SERTOR_STORE_BACKEND`.
- `test_composition.py`: `backend=azure`+`store_backend=local` → `ChromaStore`; `collection_name` keya su
  `store_backend` (no lowercasing quando store=local).
- `test_embeddings.py`: endpoint v1 → niente `api-version`; endpoint classico → `api-version` presente.
- **Fix d'isolamento** (`test_mcp_server.py`): `_use` neutralizza `Settings.load` — `_facade()` lo invocava
  col default `env_file=".env"` (`override=True`), inquinando `os.environ` globale e rompendo i test che
  verificano i default (emerso ora che `.env` ha `RAG_BACKEND=azure`).

### Documentazione
- `.env.example`: documenta `SERTOR_STORE_BACKEND` e la nota endpoint v1 (niente `api-version`).

## Attivazione (post-merge, non versionata)
- `.env` locale: `SERTOR_STORE_BACKEND=local` (resta `RAG_BACKEND=azure`).
- Build one-off via `build_indexer(Settings.load()).index('.', rebuild=True)` → `.index-sertor/`
  (esclusioni già in `SERTOR_EXCLUDE_PATTERNS`). L'artefatto è git-ignored.

## Rischi e mitigazioni
- **Retro-compatibilità**: default = `RAG_BACKEND` ⇒ nessun cambio per chi non usa la nuova variabile (SC-003).
- **Pollution dei test**: fix dell'isolamento in `test_mcp_server`; suite verde con `.env` azure.

## Artefatti
- [tasks.md](tasks.md) — task ordinati per dipendenze.
