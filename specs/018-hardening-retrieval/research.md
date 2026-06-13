# Research — 018 Hardening retrieval

Decisioni di design risolte studiando il codice reale (dogfooding via Read/MCP). Ogni voce: Decision /
Rationale / Alternatives.

## D1 — Retry: helper condiviso, non duplicazione per-adapter

**Decision.** Un modulo `src/sertor_core/adapters/embeddings/_retry.py` con `RetryPolicy`
(dataclass: `max_attempts`, `base_backoff_s`) e una funzione `with_retry(fn, policy, *, sleep, rng)`.
Gli embedder (`AzureEmbedder`, `OllamaEmbedder`) accettano `retry: RetryPolicy | None = None` e
`sleep`/`rng` iniettabili (default reali) e avvolgono **la chiamata per-batch** `self._embed_batch(...)`
dentro `embed()`. Il composition root costruisce la `RetryPolicy` da `Settings` e la passa.

**Rationale.** `azure.py` e `ollama.py` hanno `_embed_batch`/`embed` **identici** nella struttura e
sollevano entrambi `EmbeddingError(retriable=...)`: la logica di retry è identica → DRY (Principio III),
una sola implementazione testata. Il retry avvolge il **batch** (non l'intero `embed()`): un retry
dell'intero `embed()` ri-embedderebbe i batch già riusciti (spreco). `with_retry` cattura
`EmbeddingError`, e ritenta **solo se `exc.retriable`**; non-ritentabile → ri-solleva subito (FR-004).
Esauriti i tentativi → ri-solleva l'ultimo `EmbeddingError` (FR-003: tipo preservato).

**Alternatives.** (a) *Decorator-embedder* `RetryingEmbedder` che avvolge la porta `EmbeddingProvider`:
scartato perché vede solo `embed()` (tutti i batch), non il singolo batch → retry a grana sbagliata.
(b) *Duplicare il ciclo di retry in ogni adapter*: viola DRY/Principio III. (c) *Libreria esterna
(tenacity/backoff)*: viola YAGNI (Principio III) e aggiunge una dipendenza per ~15 righe.

## D2 — Backoff: esponenziale + jitter, limite = numero di tentativi (nessun cap nascosto)

**Decision.** Attesa al tentativo *i* (0-based): `base_backoff_s * (2 ** i) * (0.5 + rng())`, con `rng`
in [0,1) iniettabile. Nessun cap costante separato: il **tetto del tempo totale** è il numero di
tentativi (`max_attempts`). Default conservativi in `Settings`: `max_attempts=3`, `base_backoff_s=0.5`
→ attese ~0.5s, ~1.0s (+jitter), totale ≲ ~2.5s (SC-002, tempo limitato e prevedibile).

**Rationale.** Un cap costante (es. 30s) sarebbe un **default hardcoded** nel componente → violerebbe
il Principio VIII; con `max_attempts` piccolo il tempo è già naturalmente limitato, quindi il cap è
inutile. Il jitter evita il *thundering herd* su rate-limit condivisi. `rng`/`sleep` iniettabili →
test **senza attese reali** e **deterministici** (SC-005): in test si passa un `sleep` che registra le
durate senza dormire e un `rng` fisso.

**Alternatives.** Cap esplicito come terza manopola `Settings`: rimandato (YAGNI) — riapribile se
emerge un caso con `max_attempts` alto. Backoff lineare: scartato (standard di settore = esponenziale).

## D3 — Segnale di confidenza: soglia su similarità + lista filtrata vuota + log `low_confidence`

**Decision.** Manopola `Settings.retrieval_min_score: float | None = None` (env `SERTOR_MIN_SCORE`).
La soglia è una **soglia di similarità** (coseno): si applica ai risultati il cui `score` è una
similarità — facade percorso denso (`_search`), `_search_multi`, `BaselineEngine.query`. I risultati
con `score < soglia` sono **esclusi**; se dopo il filtro la lista è vuota (c'erano candidati ma nessuno
supera la soglia) si emette un log strutturato `low_confidence` (best score visto, soglia). Soglia
`None` (default) → nessun filtro, nessun log: **comportamento odierno identico** (FR-013).

**Forma del segnale (FR-011/014).** Il segnale è la **lista (filtrata) vuota** + il log `low_confidence`
— lo spec ammette esplicitamente «empty result and/or an explicit flag». Il contratto
`RetrievalResult` e le firme `search_*`/`query` (→ `list[RetrievalResult]`) **non cambiano**: i consumer
che ignorano il segnale continuano a ricevere liste e a funzionare (FR-014 banalmente soddisfatto). Un
oggetto-esito ricco con `.confidence` (per distinguere «fuori dominio» da «indice vuoto») è un possibile
incremento **Could differito**, non ora (YAGNI III).

**Rationale.** Per l'agente l'azione su lista vuota è l'astensione, identica sia per «indice assente»
sia per «tutto sotto soglia»; distinguere la *causa* è una raffinatezza. Lista-vuota + log è il minimo
additivo, corretto e testabile che dà all'agente il materiale per astenersi (B1 dell'audit).

**Alternatives.** (a) Cambiare il tipo di ritorno in un wrapper `RetrievalOutcome{results, low_confidence}`:
**romperebbe tutti i consumer** (facade, MCP, CLI, test) → viola FR-014. (b) Solo log, nessun filtro:
l'agente riceverebbe comunque chunk rumorosi e potrebbe allucinare → non soddisfa FR-010.

## D4 — Hybrid: la soglia agisce sul ramo DENSO, non sullo score RRF

**Decision.** In `HybridEngine.retrieve`, quando `retrieval_min_score` è impostata, si filtra il **pool
denso** (`dense = store.query(...)`, score = similarità coseno) per `score ≥ soglia` **prima** della
fusione RRF; se il pool denso si svuota, l'esito è vuoto + log `low_confidence`. Con soglia `None`
(default) nulla cambia.

**Rationale.** Lo `score` finale dell'ibrido è **RRF** (rank-based, valori ~`Σ 1/(c+rank)`), **non**
una similarità: applicare una soglia di coseno alla lista RRF finale sarebbe **semanticamente errato**.
L'unica grandezza commensurabile «quanto il corpus è vicino alla query» è la **similarità coseno del
ramo denso**, che l'ibrido già calcola. Filtrare il ramo denso prima della fusione mantiene la soglia
coerente (sempre = coseno) in tutti i motori. Questa **asimmetria** (denso filtrato, RRF no) è
deliberata e va documentata — analoga all'asimmetria voluta tollerante/strict che la guida dice di
**non uniformare**.

**Alternatives.** Filtrare la lista RRF finale per la soglia: scartato (score non commensurabile).
Saltare del tutto l'ibrido dalla feature: scartato (lascerebbe scoperto il motore di **default**).

## D5 — Collocazione del filtro soglia: helper puro condiviso

**Decision.** Funzione pura `apply_min_score(results, min_score) -> tuple[list[RetrievalResult], bool]`
(ritorna lista filtrata + flag `low_confidence`) in `services/retrieval.py`, importata da
`engines/baseline.py` e usata nell'ibrido sul ramo denso. Il **log** `low_confidence` resta al call
site (ha già il contesto: collection, provider).

**Rationale.** DRY (Principio III): una sola regola di filtro/decisione, testabile in isolamento.
Baseline ed engine importano già da `services` (es. `services.indexing`), nessuna inversione di
dipendenza. La policy errori di ciascun motore resta intatta: la soglia è un **filtro sui risultati**,
NON tocca la semantica «indice assente» (baseline resta strict con `IndexNotFoundError`; facade resta
tollerante con `no_index` warning).

## D6 — Manopole in `Settings` (Principio VIII) e wiring in `composition` (Principio I)

**Decision.** Tre nuove manopole in `Settings` con default SOLO lì:
`embed_retry_attempts: int = 3` (`SERTOR_EMBED_RETRY_ATTEMPTS`),
`embed_retry_base_s: float = 0.5` (`SERTOR_EMBED_RETRY_BASE`),
`retrieval_min_score: float | None = None` (`SERTOR_MIN_SCORE`).
`build_embedder` costruisce `RetryPolicy(max_attempts=…, base_backoff_s=…)` e la passa agli embedder;
`build_facade` passa `min_score=settings.retrieval_min_score` alla facade; baseline e hybrid leggono
`self._settings.retrieval_min_score` (già detengono `Settings`, nessun nuovo parametro costruttore).

**Rationale.** Le scelte operative vivono nell'unica config (VIII); il cablaggio degli adapter concreti
vive solo nel composition root (I). Costruzioni dirette degli embedder senza `retry` (test esistenti,
consumer) restano valide: `retry=None` ⇒ nessun ritentativo ⇒ comportamento odierno. `attempts=1`
disattiva esplicitamente (FR-006).

## D7 — Osservabilità (Principio IX): nuovi eventi, nessun segreto

**Decision.** Due nuovi eventi `log_event`: `embeddings_retry` (provider, tentativo, motivo,
attesa_ms) a ogni ritentativo; `low_confidence` (collection, provider, soglia, best_score, candidati)
quando la soglia svuota l'esito. Entrambi passano da `redact()` (nessuna chiave/segreto).

**Rationale.** Diagnosi senza leggere il codice (IX). `reason` riusa la classificazione già presente
(`http {status}` / nome eccezione di rete), nessun payload sensibile.
