---
title: Indicizzazione e retrieval (le due pipeline)
type: concept
tags: [indexing, retrieval, facade, pipeline, idempotenza, sertor-core, thin-consumer, incremental-indexing, feat-009]
created: 2026-06-08
updated: 2026-06-16 (+ refresh incrementale, manifest persistito, FEAT-009)
sources: [
  "src/sertor_core/services/indexing.py",
  "src/sertor_core/services/retrieval.py",
  "src/sertor_core/services/ingestion.py",
  "src/sertor_core/adapters/embeddings/cache.py",
  "src/sertor_core/services/index_manifest.py",
  "requirements/sertor-core/refresh-incrementale/requirements.md"
]
---

# Indicizzazione e retrieval (le due pipeline)

Il [[retrieval-core]] ha due flussi simmetrici che si incontrano sulla **collezione namespaced**:
**indicizzazione** (scrive l'indice) e **retrieval** (lo legge). Entrambi cablano [[domain-model|entità di
dominio]] dietro le [[ports-adapters|porte]] — non conoscono né lo store né il provider concreti.

## Pipeline di indicizzazione

`IndexingService.index(root, rebuild)` esegue la catena completa **ingest → chunk → embed → store**:

1. **`discover(root)`** (`ingestion.py`) — scoperta repo-agnostica e **ordinata** per path (determinismo):
   estensione → linguaggio, esclusione configurabile di artefatti/segreti, skip dei file illeggibili con
   warning, `Document.id` = path relativo POSIX.
2. **`chunk_document`** per ogni documento → [[chunking-dispatch|i Chunk]].
3. **`embed`** dei testi via [[ports-adapters|`EmbeddingProvider`]] → `EmbeddedChunk`.
4. **`upsert`** nello [[ports-adapters|`VectorStore`]]; ritorna un `IndexReport` (conteggi, dimensione,
   `elapsed_ms`) e un log strutturato.

**Atomicità del rebuild (decisione).** Con `rebuild=True` il `reset` della collezione avviene **dopo**
l'embedding e **prima** dell'upsert: così se il provider fallisce durante l'embed (rete, rate-limit) l'indice
preesistente **resta intatto**. Il rebuild è idempotente (gli id stabili del [[domain-model]] fanno coincidere
i chunk a corpus invariato). `installazione ≠ esecuzione`: l'indice si costruisce **solo** quando `index()` è
chiamato (Principio VI).

**Costo dell'embedding: la cache per content-hash (019, REQ-H4).** Il rebuild è *full* by-design (rilegge e
ri-chunka tutto), e con un provider a pagamento (Azure) ri-paga l'embedding di ogni chunk a ogni
ricostruzione — un attrito reale, dato che il [[step-ritual|rituale di step]] rende i re-index frequenti.
La cache lo neutralizza **a valle, sul passo di embedding**: un decoratore della porta
[[ports-adapters|`EmbeddingProvider`]] (`CachingEmbedder`) consulta uno store persistente
`(model, sha256(testo)) → vettore` (SQLite `<index_dir>/embed_cache.sqlite`) **prima** di chiamare il
provider, e gli passa **solo i chunk il cui contenuto è cambiato o nuovo**. `IndexingService` resta
**invariato** (il decoratore è trasparente): il wiring vive nel composition root e **solo sul percorso
d'indicizzazione** (le query hanno riuso basso). È **additivo e opt-in** (`SERTOR_EMBED_CACHE`, default off =
rebuild full odierno) e **non-fatale**: un guasto dello store è un cache-miss loggato, mai un errore
d'indicizzazione. La chiave include il modello → cambiare provider non serve mai vettori di uno spazio
diverso. È il **mitigante immediato** del refresh incrementale (FEAT-009 d'epica, ancora da decomporre):
non evita di rileggere/ri-chunkare, ma evita di ri-embeddare. Vettori serializzati float64 esatti → indice
byte-equivalente con/senza cache.

## Refresh incrementale dell'indice (FEAT-009)

L'**indice incrementale** rende l'indicizzazione proporzionale al **delta reale** delle sorgenti, non all'intera
codebase — cruciale per il [[step-ritual|rituale di step]] su ospiti grandi (il full rebuild avrebbe costo in minuti/euro).

**Il meccanismo: manifest persistito.** L'indice porta con sé un **ledger SQLite** namespaced per `(corpus, provider)`
(`<index_dir>/index_manifest.sqlite`, gitignored), che ricorda per ogni file: `mtime`, `content_hash`, `chunk_id`,
`versione-logica`. All'invocazione di `index()` (FEAT-009 di DEFAULT):

1. **Rilevamento delta** — scoperta ordinata (come oggi); per ogni file, controllo `mtime` (pre-filtro veloce) + hash
   (conferma); classificazione in 4 classi: `UNCHANGED` (skip), `NEW` (embed+store), `MODIFIED` (delete vecchi chunk,
   embed+store i nuovi), `DELETED` (delete dallo store).
2. **Upsert mirati** — il vettore store riceve solo i chunk NEW/MODIFIED; BM25 e code-graph si **ricostruiscono dal
   manifest** (i chunk-id sono persistiti) invece di rileggere i file invariati. Così il lavoro è **O(delta)**, non
   O(corpus).
3. **Safeguard** — fallback automatico al full se il manifest è assente/incompatibile; invalidazione su cambio-logica
   (versionamento dei chunker); conteggi delta osservabili (added/updated/removed/unchanged/cache-hits) nel log.

**Decisioni utente incorporati (F1+F2 del clarify).** L'incrementale è **il default** (`SERTOR_INDEX_INCREMENTAL=true`,
default). Override: `--full` in CLI o `SERTOR_INDEX_INCREMENTAL=false` forzano il reset+rebuild completo. Un altro
switch `SERTOR_INDEX_RECONCILE_EVERY=N` (default off) **riconcilia** ogni N invocazioni (riabilita il full per
rilevare i drift del ledger — non necessario in normale operazione, ma asimmetria voluta: il costo della riconciliazione
non è pagato da chiunque).

**Nessuna nuova porta.** Il manifest è uno **store concreto** (come `EmbeddingCache`), non una astrazione dietro un
`Protocol` — ha un unico consumatore e YAGNI preclude di farne una porta.

## La facade di retrieval

`RetrievalFacade` è il **punto d'accesso unico e stabile** al corpus indicizzato, ed è ciò che i
[[thin-consumer|consumatori sottili]] (server MCP, motori, CLI) importano via `build_facade()` **senza**
conoscere store/embeddings. Espone tre ricerche, distinte solo dal filtro `DocTypeFilter`:

- `search_code(query, k)` → solo codice
- `search_docs(query, k)` → sola documentazione
- `search_combined(query, k)` → entrambi; con **corpora extra** configurati fa anche il **fan-out
  multi-collezione** (vedi sotto)

Ogni ricerca embedda la query, interroga lo store per il top-k, emette un log e ritorna
`list[RetrievalResult]`.

**Fan-out multi-collezione ([[spec-010-query-congiunta-e-upsert-index|feature 010]]).** Se `Settings.extra_corpora` (`SERTOR_EXTRA_CORPORA`)
dichiara corpora aggiuntivi, `search_combined` interroga **tutte** le collezioni bersaglio (la
query è embeddata una sola volta) e **fonde i top-k per score**, con tie-break deterministico per
`chunk_id` e al più `k` risultati totali. Solo la combinata fa fan-out: `search_code`/`search_docs`
restano a singola collezione. I consumatori non cambiano: `build_facade()` deriva le collezioni extra
dalla config con lo stesso naming `(corpus, provider)`.
**Quando usarlo (D-21):** è la capacità per ospiti con corpora **davvero disgiunti** (es. un doc-repo
esterno al repository indicizzato). Il **caso standard è a corpus unico**: il wiki vive *dentro*
l'ospite by design ([[corpus-index-naming]]) → è già documentazione del corpus primario, e la combinata
vede tutto senza fan-out né duplicati. Sul dogfood Sertor `extra_corpora` non è configurata.

**Tolleranza sull'indice assente (policy voluta).** Se la collezione non esiste, la facade ritorna **`[]` con
un warning**, senza eccezioni (REQ-028): è la faccia *tollerante* del nucleo, pensata per la composabilità —
da non confondere con la policy *strict* del motore [[vector-retrieval|baseline]] (che invece solleva), scelta
per l'usabilità del consumatore. La differenza è [[deterministic-vs-judgment|deliberata e non va uniformata]].
**Unica deroga** (decisa nel clarify della feature 010): un corpus extra indicizzato con un **altro
provider** di embeddings fa fallire la combinata con `ProviderMismatchError` — gli score di spazi
vettoriali diversi non si fondono; meglio nessuna risposta che una fusione fuorviante.

## Vedi anche
- Le entità in transito: [[domain-model]].
- Le astrazioni cablate: [[ports-adapters]].
- Come nascono i chunk: [[chunking-dispatch]].
- Chi consuma la facade: [[thin-consumer]] · prima modalità RAG: [[vector-retrieval]].
- Il refresh incrementale: [[indexing-and-retrieval#refresh-incrementale-dellindice-feat-009]] (FEAT-009, requisiti in `requirements/sertor-core/refresh-incrementale/`).
