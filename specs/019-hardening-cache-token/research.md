# Research — Cache embeddings + token nei log (feature 019)

Decisioni di design risolte prima dell'implementazione. Nessuna NEEDS CLARIFICATION residua.

## D1 — Forma: decoratore della porta `EmbeddingProvider`, non logica in `IndexingService`

- **Decision:** la cache è un **decoratore** (`CachingEmbedder`) che implementa `EmbeddingProvider`
  avvolgendo l'embedder reale. `services/indexing.py` resta invariato.
- **Rationale:** la regola architetturale del repo è "si sceglie l'implementazione solo in
  `composition.py`; per aggiungere un comportamento di provider si estende adapter+composition, non i
  servizi" (Principio I). Il decoratore è trasparente: la facade, il baseline e l'indexer continuano a
  chiamare `embed()`. Il pattern è lo stesso "sink iniettato dal composition root" già usato per BM25 e
  il code-graph.
- **Alternatives considered:** (a) cache dentro `IndexingService` — viola la separazione (il servizio
  conoscerebbe la cache) e non si riuserebbe; (b) cache dentro ciascun embedder — duplica logica in
  Azure/Ollama (anti-DRY) e mescola due responsabilità (chiamata provider ≠ memoizzazione).

## D2 — Persistenza: SQLite (`embed_cache.sqlite`), non un sidecar JSON

- **Decision:** store SQLite singolo file in `Settings.index_dir/embed_cache.sqlite`; tabella
  `embeddings(model TEXT, content_hash TEXT, vector BLOB, PRIMARY KEY(model, content_hash))`. Lettura
  per chiave (lookup batch via `SELECT ... WHERE content_hash IN (...)`), scrittura incrementale solo
  dei miss (`INSERT OR IGNORE`/`executemany`).
- **Rationale:** la cache cresce e va aggiornata **incrementalmente**. Il sidecar JSON atomico (pattern
  BM25) richiede di **riscrivere l'intero file** a ogni `index()`: con ~3.7k vettori da 3072 dim (~90 MB)
  il rewrite a ogni rebuild vanificherebbe in parte il guadagno di costo/tempo che la feature insegue.
  SQLite (stdlib, zero dipendenze) offre lookup/insert per chiave senza riscrivere tutto, transazioni
  atomiche e robustezza nativa. La costituzione (§Sicurezza) elenca "cache" tra gli artefatti
  git-ignored: la sede sotto `index_dir` è già coperta.
- **Alternatives considered:** sidecar JSON (coerenza col pattern BM25, ma full-rewrite costoso e
  memory-heavy → respinto perché contrario all'obiettivo di costo); un file per chunk (troppi inode,
  overhead FS). SQLite è il KV content-addressed naturale.

## D3 — Chiave: `(embedder.name, sha256(text))` — isolamento cross-modello

- **Decision:** chiave = `model = embedder.name` (es. `azure:text-embedding-3-large` / `ollama:nomic-embed-text`)
  + `content_hash = sha256(text.encode("utf-8")).hexdigest()`.
- **Rationale:** l'embedding dipende **solo** dal testo e dal modello. Includere `embedder.name` nella
  chiave impedisce che vettori di un modello (dimensione/spazio diverso) servano un altro (FR-002,
  SC-004) — stessa logica del namespacing `(corpus, provider)` delle collezioni (`collection_name`).
  sha256 rende le collisioni trascurabili e la chiave indipendente dalla posizione del chunk (due chunk
  con testo identico → stesso hash → un solo embed, dedup gratuito).
- **Alternatives considered:** hash più corti (md5/blake2 troncato) — sha256 è già veloce e standard,
  nessun motivo di rischiare collisioni; includere il `corpus` nella chiave — sbagliato: l'embedding non
  dipende dal corpus, includerlo impedirebbe il riuso cross-corpus (un chunk identico in due progetti).

## D4 — Serializzazione vettore: float64 esatto (`array('d')`)

- **Decision:** vettore persistito come `array("d", vector).tobytes()`; ricostruito con
  `array("d"); arr.frombytes(blob)`.
- **Rationale:** i vettori arrivano dal JSON del provider come `float` Python (= double/float64). Il
  round-trip `array('d')` è **esatto** → l'indice prodotto con cache è byte-identico a quello senza
  cache (FR-005, "indice equivalente con/senza cache"), nessuna deriva numerica da discutere.
- **Alternatives considered:** float32 (metà spazio, ma round-trip lossy → romperebbe l'equivalenza
  stretta di FR-005); numpy `tobytes` (dipendenza non necessaria, `array` stdlib basta).

## D5 — Token: `_embed_batch` → `(vettori, token | None)`, un evento `embeddings` per `embed()`

- **Decision:** `_embed_batch` di Azure/Ollama restituisce la tupla `(vettori, token)`; Azure legge
  `r.json().get("usage", {}).get("total_tokens")`, Ollama `r.json().get("prompt_eval_count")`
  (best-effort). `embed()` accumula i token tra i batch ed emette **un** evento
  `log_event(INFO, "embeddings", provider=…, texts=N, tokens=T)`; quando nessun batch riporta token, il
  campo `tokens` è **omesso** (non `0`/`None` finto — FR-009).
- **Rationale:** un evento per `embed()` (≈ una chiamata per `index()` o per query) è la granularità
  giusta: niente rumore per-batch, segnale di costo aggregato (Principio IX colma un gap odierno — il
  successo dell'embedding oggi non logga nulla). La porta `embed()` non cambia firma (FR-011): i token
  escono dal **log**, non dal valore di ritorno. `with_retry` è generico sul tipo → regge la tupla senza
  modifiche.
- **Alternatives considered:** cambiare la firma di `embed()` per restituire i token (rompe la porta e
  tutti i consumer — respinto); un evento per batch (rumoroso); accumulare i token in un attributo
  dell'embedder (stato mutevole nascosto, peggiore del log esplicito).

## D6 — Osservabilità della cache: evento `embeddings_cache` (hit/miss)

- **Decision:** `CachingEmbedder.embed` emette `log_event(INFO, "embeddings_cache", provider=…,
  hits=H, misses=M, total=H+M)`.
- **Rationale:** rende **misurabile** SC-001/002 (zero miss = 100% hit) e, insieme all'evento
  `embeddings` (token sui soli miss), quantifica il risparmio SC-006 dai log di due rebuild. È il
  segnale che lega US1 e US2 (FR-010).
- **Alternatives considered:** nessun log della cache (SC-003 non sarebbe osservabile da log); esporre
  metriche aggregate — è REQ-H10 (Could), fuori ambito.

## D7 — Wiring: cache **solo sul percorso d'indicizzazione**, default off

- **Decision:** `build_embedder(settings, *, cache: bool = False)`; `build_indexer` chiama
  `build_embedder(settings, cache=settings.embed_cache_enabled)`. Facade/baseline usano
  `build_embedder()` (cache=False). Manopola `Settings.embed_cache_enabled` (env `SERTOR_EMBED_CACHE`,
  default `False`).
- **Rationale:** l'obiettivo è il **costo d'indicizzazione** (OB-3). Cachare anche le query (facade)
  aggiungerebbe scritture sul percorso di ricerca con riuso basso (ogni query diversa) e farebbe
  crescere la cache con vettori effimeri — costo senza beneficio. Limitare al percorso d'indicizzazione
  è lo scoping corretto. Default off = retro-compatibile (FR-007/013): chi non abilita non cambia
  comportamento.
- **Alternatives considered:** wrappare in `build_embedder` per tutti (più semplice ma cacha le query —
  overhead sul percorso read-mostly); manopola separata per query-cache (YAGNI, nessun caso d'uso oggi).

## D8 — Dedup in-call + ricostruzione ordine

- **Decision:** dentro `CachingEmbedder.embed(texts)`: calcola gli hash, interroga la cache in blocco,
  raccoglie i **miss unici** (un testo duplicato nello stesso batch si embedda una volta), chiama
  `inner.embed(miss_unici)`, scrive i nuovi in cache, poi **ricostruisce l'output nell'ordine
  originale** mappando hash→vettore. `dim` del decoratore = lunghezza del primo vettore prodotto (hit o
  miss), così `IndexReport.embedding_dim` resta corretto anche con 100% cache-hit (l'inner non viene
  chiamato e il suo `dim` resterebbe `None`).
- **Rationale:** preserva l'ordine (contratto `embed`) e ottiene dedup gratuito; gestisce il caso
  all-hit senza rompere il report.
- **Alternatives considered:** non deduplicare (semplice ma ri-embedda duplicati interni — spreco);
  delegare `dim` all'inner sempre (rotto sul caso all-hit).

## Degrado non-fatale (trasversale, FR-004)

`EmbeddingCache` cattura `sqlite3.Error` (db corrotto/illeggibile/lock): in lettura → tratta come miss
(ritorna nessun hit) + `log_event(WARNING, "embeddings_cache_unavailable", reason=…)`; in scrittura →
salta la scrittura con lo stesso warning. **Mai** solleva: un guasto della cache non fa fallire
l'indicizzazione (la cache è un'ottimizzazione, non una fonte di verità). Questo è coerente con
Principio IV (non è "null silenzioso": un miss è un esito legittimo, esplicitamente loggato).
