# Research — Motore RAG ibrido + reranking (013)

**Input**: `spec.md` (32 FR), fonte EARS `requirements/sertor-core/motore-ibrido/requirements.md`,
prototipo `prototype/02-hybrid-reranking/` (letto direttamente: `hybrid.py`, `rerank.py`),
codice di produzione su `master` (baseline, porte, composition, Settings, facade, indexing,
evaluation, errori, mocks).

Nessun NEEDS CLARIFICATION residuo nella spec: le decisioni qui sotto fissano il *come*.

---

## D1 — Indice lessicale: porta nuova + sidecar persistito nell'index dir

**Decision**: nuova porta `LexicalIndex` (Protocol in `domain/ports.py`) con un adapter BM25
in `adapters/lexical/bm25.py`. L'adapter **persiste un sidecar JSON** per collezione
(`<index_dir>/lexical/<collection>.json`) scritto al momento dell'indicizzazione e caricato
(+ tokenizzato + BM25 costruito in memoria) alla prima query.

**Rationale**:
- REQ-034 richiede di **rilevare l'assenza** dell'indice lessicale (corpus pre-ibrido) per
  degradare con warning: un artefatto su disco rende il check banale (`exists()` = file presente).
- REQ-072 chiede esplicitamente che l'indice lessicale viva «nella stessa directory di indici
  namespaced dello store vettoriale» → `Settings.index_dir`, nome file = nome collezione
  (che già codifica `(corpus, provider)` → REQ-005 namespacing gratis).
- Funziona con **qualunque** store backend (anche `store_backend=azure`): il sidecar è locale,
  il core resta store-agnostico (D2 dei requirements).
- V-1 rispettato: le porte `EmbeddingProvider`/`VectorStore` restano **invariate**.

**Alternatives considered**:
- *Caricare i documenti dalla collezione vettoriale a runtime* (lettura "get all" dallo store):
  richiederebbe un'estensione della porta `VectorStore`, renderebbe l'assenza dell'indice
  lessicale **non rilevabile** (contraddice REQ-034: i corpora pre-ibrido diventerebbero
  silenziosamente ibridi con tokenizzazione implicita), e su store cloud il dump completo è
  costoso. Scartata.
- *SQLite FTS5 (stdlib)*: persistente e senza dipendenze, ma il controllo del tokenizer
  (sotto-token snake_case, il differenziatore chiave) è macchinoso e il ranking è BM25 variante
  FTS5, non confrontabile col prototipo. Scartata.
- La **persistenza scalabile** (indice invertito su disco per corpora enormi) resta fuori ambito
  (→ FEAT-009): il sidecar è una serializzazione semplice, non un indice su disco.

## D2 — BM25: libreria `rank-bm25` come dipendenza base

**Decision**: `rank-bm25` (BM25Okapi) aggiunta alle **dipendenze base** di `sertor-core`;
stessa libreria del prototipo.

**Rationale**: l'indice lessicale è Must (il default `hybrid` lo richiede sempre); la libreria è
minuscola, pura Python (unica dipendenza transitiva: numpy, già presente via chromadb), provata
nel prototipo 02 (MRR 0.13→0.94 sulle query a simbolo con embedder debole). Scriverla in casa
(~40 righe) è fattibile ma è reinventare una ruota già testata (Principio III).

**Alternatives considered**: implementazione in-house (più controllo, più superficie da testare);
`bm25s`/`tantivy` (più veloci ma dipendenze native, overkill per <10k chunk).

## D3 — Tokenizer: parità col prototipo

**Decision**: tokenizer del prototipo (`hybrid.py:26-35`): lowercase, parole `[a-z0-9_]+`, e per
ogni token con `_` si aggiungono anche i sotto-token. Vive nell'adapter lessicale come funzione
pura testabile; versione registrata nel sidecar (`tokenizer_version`).

**Rationale**: è il differenziatore misurato sulle query a simbolo (REQ-001); parità col
prototipo = confrontabilità dei numeri. Lo split camelCase è una rifinitura possibile, non
necessaria per il corpus Python/Markdown attuale (YAGNI; annotabile in futuro).

## D4 — Fusione RRF client-side nel motore

**Decision**: RRF come funzione pura in `engines/hybrid.py`: `score(id) = Σ 1/(c + rank)` sulle
due liste (formula del prototipo `hybrid.py:38-43`); `c` e `pool` da `Settings` (default 60 e 30,
REQ-011). Ordinamento: score RRF decrescente, pareggi per `chunk_id` crescente (stesso pattern del
merge multi-collezione, `services/retrieval.py:131`) → determinismo (REQ-012). Lo score esposto
nel `RetrievalResult` fuso è lo score RRF.

**Rationale**: la fusione per ranghi (non per score) evita di confrontare similarità coseno e
punteggi BM25 incommensurabili; il `RetrievalResult` resta l'entità di dominio invariata (REQ-013).

**Alternatives considered**: normalizzazione min-max degli score e somma pesata (fragile, dipende
dalle distribuzioni); delega nativa per-store (resta Could, Gruppo E — il seam c'è, vedi D6).

## D5 — Filtro `doc_type` sulla via lessicale

**Decision**: il sidecar registra `doc_type` per entry; la query lessicale filtra per `doc_type`
**prima** del taglio a `pool` (come il prototipo filtra per `source`). La via densa usa il filtro
nativo dello store (`store.query(..., doc_type)`).

**Rationale**: `search_code`/`search_docs` della facade richiedono pool filtrati coerenti su
entrambe le vie, altrimenti la fusione mescola tipi che il consumatore ha escluso.

## D6 — Integrazione nella facade: strategia di retrieval iniettata dal composition root

**Decision**: `RetrievalFacade` acquisisce un parametro keyword **opzionale e additivo**
`retriever` (porta `RetrieverStrategy`: `retrieve(query, k, doc_type) -> list[RetrievalResult]`).
Se assente → percorso denso attuale, byte-per-byte invariato. `build_facade()` lo inietta quando
`Settings.engine == "hybrid"`; `HybridEngine` implementa la strategia. La facade **mantiene la sua
policy tollerante**: il check `exists()` + warning `no_index` + `[]` resta nella facade, la
strategia è invocata solo a collezione esistente.

**Rationale**: REQ-032 (interfaccia facade invariata per i consumatori: parametro opzionale del
costruttore usato solo dal composition root), REQ-031 (la scelta sta SOLO in `composition.py`),
A-5 (MCP e CLI consumano la facade → beneficiano senza modifiche, LSC-3). La policy errori
non uniforme del core (facade tollerante ↔ motore strict) resta intatta per costituzione del
workspace.

**Fan-out multi-collezione (feature 010)**: con `extra_corpora` configurati, `search_combined`
mantiene il percorso denso esistente (fusione per score coseno tra collezioni omogenee). Gli score
RRF non sono fondibili con score coseno di altre collezioni; estendere l'ibrido al fan-out è
rifinitura futura. Il comportamento è dichiarato (log `engine=baseline-fanout` nell'evento) e
documentato nel quickstart — nessun cambio silenzioso: il fan-out oggi è dense-only e tale resta.

**Alternatives considered**: facade che importa i motori (viola REQ-031/Principio I); flag
per-chiamata (scartata in DA-1 dei requirements).

## D7 — Semantica strict vs degradazione (riconciliazione REQ-004 ↔ REQ-034)

**Decision** (già in spec, qui fissata nel design):
- **Collezione vettoriale assente** (corpus mai indicizzato) → `IndexNotFoundError` via
  `ensure_index()` (identico al baseline). Vale per il motore (strict); la facade resta tollerante
  (warning + `[]`) come oggi.
- **Collezione presente, sidecar lessicale assente** (corpus pre-ibrido) → degradazione a
  dense-only con evento WARNING `lexical_index_missing` (collection, hint: re-index abilita
  l'ibrido); la query NON fallisce. La degradazione non è silenziosa: è loggata (Principio IX) —
  deroga al Principio IV deliberata e decisa dall'utente (DA-1b), tracciata in Complexity Tracking
  del plan.

## D8 — Reranker: extra `rerank` con FlashRank, errore esplicito se configurato e assente

**Decision**: porta `Reranker` (Protocol: `model: str`, `rerank(query, results, k)`); adapter
`adapters/rerank/flashrank.py` (FlashRank ONNX, niente torch, come `prototype/02/rerank.py`);
extra `rerank = ["flashrank>=0.2"]` in pyproject; import **lazy nel composition root** (pattern
identico ad `azure`/`mcp`). `Settings.rerank_enabled` default **False** (R-3: su embedder forte
può peggiorare). Se `rerank_enabled=True` e l'import fallisce → `ConfigError` azionabile
(«installa l'extra: `uv add "sertor-core[rerank]"`»), mai fallback silenzioso (REQ-022).

**Rationale**: NFR-02/Principio III (dipendenza pesante isolata), REQ-020..024. Il pool passato al
reranker è il pool fuso troncato a `Settings.rerank_pool` (default 15 ≈ 3×k, REQ-024).

## D9 — Selezione motore e wiring dell'indicizzazione

**Decision**:
- `Settings.engine` (env `SERTOR_ENGINE`, default `"hybrid"`); valore non ammesso → `ConfigError`
  con i valori validi, sollevata dal composition root (`build_engine`).
- Nuova factory `build_engine(settings)` in `composition.py` (ritorna `BaselineEngine` o
  `HybridEngine`); `build_baseline_engine` resta invariata (REQ-070; consumatori espliciti).
- `IndexingService` acquisisce un parametro opzionale `lexical: LexicalIndex | None = None`:
  se presente, dopo l'upsert vettoriale scrive il sidecar **dagli stessi chunk** (REQ-003,
  coerenza by construction; default None → pipeline identica a oggi).
- `build_indexer()` inietta l'adapter lessicale quando `engine == "hybrid"`: così il re-index
  rituale e `sertor-rag index` producono il sidecar senza cambiare i consumatori. Con
  `SERTOR_ENGINE=baseline` la pipeline è identica a oggi (REQ-071).

**Rationale**: REQ-030/031/033; il rebuild congiunto vettoriale+lessicale in un solo passaggio
della pipeline è il modo più semplice di garantire la coerenza dei due indici.

## D10 — Ground-truth e chiusura dei 2 xfail senza rete

**Decision**: fixture versionata `tests/fixtures/ground_truth.py` con le coppie
(query → path relativi attesi). I 2 test `xfail` diventano **strict** e girano **senza rete**:
indicizzano `src/sertor_core/` con `FakeEmbedder` + `InMemoryStore` + indice lessicale reale, poi
confrontano baseline vs ibrido sullo stesso ground-truth (`evaluate()` esteso a entrambe le
modalità). Con embedder finto la via densa è ~casuale e la via lessicale reale: il delta sulle
query a simbolo (LSC-1, +10 pp) è dimostrabile in CI locale — è esattamente il fenomeno misurato
dal prototipo (Ollama debole: MRR 0.13→0.94). Le misure con provider reali (Azure) restano nel
dogfood (REQ-051, smoke/`cloud`).

**Le 6 coppie fissate in design** (simbolo → file; si completano a ≥10 in implementazione con
query NL):

| Query | Path atteso |
|---|---|
| `EmbeddingProvider` | `src/sertor_core/domain/ports.py` |
| `IndexNotFoundError` | `src/sertor_core/domain/errors.py` |
| `collection_name` | `src/sertor_core/composition.py` |
| `log_event` | `src/sertor_core/observability/logging.py` |
| `ensure_index` | `src/sertor_core/engines/baseline.py` |
| `ProviderMismatchError` | `src/sertor_core/domain/errors.py` |

Candidate NL (da fissare in implementazione): «dove si scelgono gli adapter concreti» →
`composition.py`; «rebuild atomico dell'indice» → `services/indexing.py`; «fusione dei risultati
multi-collezione» → `services/retrieval.py`; «redazione dei segreti nei log» →
`observability/logging.py`.

**Rationale**: REQ-050/052/053 (path relativi, host-agnostico), LSC-5/6 (senza rete), Principio V.
`evaluate()` generalizza il type hint dal `BaselineEngine` concreto a un Protocol con
`query`/`provider` (cambiamento solo di annotazione, non di comportamento).

## D11 — Osservabilità e latenza

**Decision**: eventi via `log_event` esistente (redazione inclusa):
- `hybrid_query` (INFO): `engine, provider, collection, lexical_hits, dense_hits, fused_k,
  rerank_applied, elapsed_ms` (REQ-060).
- `rerank` (INFO): `reranker_model, pool_size, top_k, elapsed_ms` (REQ-061).
- `lexical_index_missing` (WARNING): `collection, hint` (REQ-034).

Latenza (NFR-04, qualitativa): il costo aggiunto è il caricamento pigro del sidecar + costruzione
BM25 in memoria **una volta per processo** (≈ sub-secondo a 2k chunk; il server MCP è long-lived,
la CLI paga una tantum per invocazione) e lo scoring BM25 per query (millisecondi). La misura
empirica avviene nel dogfood leggendo `elapsed_ms` degli eventi.

## D12 — Percorso nativo per-store (Gruppo E): solo seam, nessuna implementazione

**Decision**: in questa feature si implementa SOLO l'ibrido client-side. Il seam per la delega
nativa esiste by design: la strategia di retrieval è scelta nel composition root (D6) — un futuro
`AzureNativeHybridStrategy` si aggancia lì senza toccare facade/consumatori (REQ-042). Documentato
nel plan; FR-020/021/022 restano dichiarati (Could) e non testati in questa iterazione.

**Rationale**: D2 dei requirements (core store-agnostico; la delega si implementa quando lo store
sarà in uso); YAGNI.
