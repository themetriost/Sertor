# Implementation Plan: Cache embeddings per content-hash + token nei log

**Branch**: `019-hardening-cache-token` | **Date**: 2026-06-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-hardening-cache-token/spec.md`

## Summary

Due Should del gruppo C dell'hardening di produzione (costo dell'indicizzazione), entrambi **additivi** e
a default retro-compatibile:

1. **Cache embeddings per content-hash (REQ-H4, US1/P1).** Un **decoratore** della porta
   `EmbeddingProvider` — `CachingEmbedder` in `adapters/embeddings/cache.py` — consulta una cache
   persistente chiave→vettore (`(provider/model, sha256(text))` → embedding) **prima** di delegare i
   miss all'embedder reale, e aggiorna la cache coi nuovi vettori. `services/indexing.py` resta
   invariato (chiama `embedder.embed(...)` come oggi): il wiring del decoratore vive **solo** nel
   composition root, sul percorso d'indicizzazione. Default **disabilitato** (`SERTOR_EMBED_CACHE=false`).
2. **Token nei log (REQ-H5, US2/P2).** `_embed_batch` di Azure/Ollama estratto a restituire
   `(vettori, token | None)`; `embed()` accumula i token tra i batch ed emette **un** evento di log
   `embeddings` per chiamata con il conteggio token (campo omesso quando il provider non lo espone).
   Additivo: il contratto della porta non cambia.

L'osservabilità lega i due: `CachingEmbedder` emette un evento `embeddings_cache` (hit/miss) e, poiché
solo i miss raggiungono l'embedder reale, l'evento `embeddings` mostra **meno token** sul rebuild a
cache calda → il risparmio (SC-006) è misurabile.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: stdlib soltanto per la novità — `sqlite3` (persistenza cache), `hashlib`
(sha256), `array` (serializzazione vettori float64). Nessuna nuova dipendenza di terze parti, nessun
extra. `httpx` già presente per gli embedder.

**Storage**: cache embeddings = file SQLite `embed_cache.sqlite` dentro `Settings.index_dir` (già
namespaced per runtime e git-ignored come "cache" — costituzione §Sicurezza). Tabella keyed
`(model, content_hash)`; il vettore è persistito come `array('d').tobytes()` (float64, round-trip esatto).

**Testing**: pytest, offline. Fake inner embedder che **conta le chiamate** (cache hit/miss) e fake che
riporta un conteggio token noto; `tmp_path` per la cache SQLite. Marker `not cloud`.

**Target Platform**: libreria `sertor-core` (Win/Linux/macOS); consumata da CLI `sertor-rag` e server MCP.

**Project Type**: libreria di retrieval in Clean Architecture (domain/services/adapters/engines/config).

**Performance Goals**: SC-001 = zero chiamate di embedding sul rebuild di corpus invariato; lookup cache
O(1) per chunk via indice primario SQLite; nessuna regressione percepibile con cache off.

**Constraints**: offline-capable (tutto testabile senza rete); contratto `RetrievalResult`/porte
invariato (additivo); default retro-compatibili; degrado non-fatale su guasto cache; import lazy del
modulo cache dove pesa (qui leggero: solo stdlib).

**Scale/Scope**: corpora tipici < 50k chunk; dogfood `sertor` ~3.7k chunk × 3072 dim (Azure
`text-embedding-3-large`). SQLite regge comodamente; il vettore float64 ≈ 24 KB/chunk → ~90 MB di cache
per il dogfood (artefatto cache, accettabile e cancellabile).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* — Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la cache è un **adapter** (`adapters/embeddings/cache.py`) dietro la porta `EmbeddingProvider`; `domain`/`services` non la conoscono. Wiring solo in `composition.py`. Esercitabile con embedder mock, senza cloud. **PASS**
- [x] **II — Boundary & local-first:** `sqlite3` (stdlib, locale) dietro l'adapter; nessun servizio esterno. La cache funziona identica in locale e cloud (è a valle del provider). **PASS**
- [x] **III — YAGNI & unità piccole:** un decoratore + un piccolo store SQLite; nessuna nuova dipendenza/extra. SRP (cache ≠ embedder ≠ indexer); DRY (token-logging estratto una volta, condiviso da Azure/Ollama via il pattern `_embed_batch` già comune). **PASS**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** la cache **degrada non-fatale** by-design (REQ-H4/FR-004: miss → embed normale + warning), che NON è "null silenzioso": è una cache, la cui assenza è semanticamente un miss legittimo (come l'indice lessicale assente per l'ibrido). Gli errori del provider restano `EmbeddingError` invariati. **PASS**
- [x] **V — Testabilità & misure:** test F.I.R.S.T. con fake embedder che conta le chiamate (SC-001/002/004) e fake con token noti (SC-005); nessuna rete. Non è una feature di qualità-retrieval → no hit@k/MRR. **PASS**
- [x] **VI — Idempotenza & non-distruttività:** la cache **rafforza** l'idempotenza (stesso input → stessi vettori, da cache); rebuild atomico invariato (reset dopo embed); cache cancellabile senza perdita di correttezza (solo ri-embedding). Il principio cita esplicitamente il "costo/latenza delle chiamate LLM da considerare": è proprio l'obiettivo. **PASS**
- [x] **VII — Leggibilità:** naming di dominio (`CachingEmbedder`, `EmbeddingCache.get/put`, evento `embeddings_cache`, `content_hash`). **PASS**
- [x] **VIII — Configurabilità centralizzata:** nuove manopole **solo** in `Settings` (`embed_cache_enabled`, default off; sede derivata da `index_dir`), nessun default hardcoded nei componenti. **PASS**
- [x] **IX — Osservabilità:** nuovo evento `embeddings` (provider, conteggio testi, **token**) + `embeddings_cache` (hit/miss); nessun segreto (redazione invariata). Colma un gap odierno (l'embedding di successo non logga i token). **PASS**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** nessuna assunzione d'ospite; la sede della cache deriva da `index_dir` (config), non da path fissi. Gira su qualunque corpus (code+doc/solo-doc/solo-code) senza modifiche al corpo. **PASS**

**Esito: PASS 10/10 senza deroghe.** Nessuna voce in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/019-hardening-cache-token/
├── plan.md              # questo file
├── research.md          # Phase 0 — decisioni di design (D1..D8)
├── data-model.md        # Phase 1 — entità (voce cache, eventi di log, manopola)
├── quickstart.md        # Phase 1 — come abilitare e verificare il risparmio
├── contracts/
│   ├── embedding-cache.md   # contratto del decoratore + store cache
│   └── log-events.md        # schema eventi `embeddings` / `embeddings_cache`
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/sertor_core/
├── adapters/embeddings/
│   ├── cache.py          # NUOVO: CachingEmbedder (decoratore porta) + EmbeddingCache (store SQLite)
│   ├── azure.py          # MODIF: _embed_batch → (vettori, token); embed() logga evento `embeddings`
│   ├── ollama.py         # MODIF: idem (best-effort su prompt_eval_count)
│   └── _retry.py         # invariato (with_retry è generico sul tipo di ritorno → regge la tupla)
├── config/settings.py    # MODIF: + embed_cache_enabled (SERTOR_EMBED_CACHE, default False)
├── composition.py        # MODIF: build_embedder(..., cache=False); build_indexer wrappa se abilitato
└── services/indexing.py  # INVARIATO (chiama embedder.embed; il decoratore è trasparente)

tests/unit/
├── test_embedding_cache.py        # NUOVO: hit/miss, dedup, cross-model, degrado non-fatale, equivalenza
├── test_embedding_token_log.py    # NUOVO: evento `embeddings` con/ senza token
└── test_settings_hardening.py     # MODIF/estendi: manopola embed_cache_enabled
```

**Structure Decision**: libreria singola in Clean Architecture (struttura esistente). La novità vive
**solo** in `adapters/` (cache) + `composition.py` (wiring) + `config/settings.py` (manopola); i
servizi e il dominio non cambiano — coerente con la regola "si estende composition + adapter, non i
servizi".

## Complexity Tracking

Nessuna violazione costituzionale: tabella non compilata.
