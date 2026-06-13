# Tasks: Hardening di produzione del livello retrieval (Must)

**Feature**: 018-hardening-retrieval | **Branch**: `018-hardening-retrieval`
**Input**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/library-contract.md](./contracts/library-contract.md)

Test inclusi: la feature è interamente verificata da test offline (SC-005); ogni storia ha i suoi.
Convenzioni: `[P]` = parallelizzabile (file diversi, nessuna dipendenza pendente); `[US1]`/`[US2]` =
storia di appartenenza.

---

## Phase 1: Setup

- [x] T001 Verificare l'ambiente di sviluppo: `uv sync --extra dev` e baseline verde
  `uv run pytest -m "not cloud" -q` (fotografia pre-feature per la regressione SC-004/006).

## Phase 2: Foundational (prerequisiti bloccanti per entrambe le storie)

Le manopole vivono nell'unico `Settings` (Principio VIII): entrambe le storie ne dipendono. Stesso file
→ task sequenziali.

- [x] T002 In `src/sertor_core/config/settings.py`: aggiungere i campi al dataclass `Settings`
  `embed_retry_attempts: int = 3`, `embed_retry_base_s: float = 0.5`, `retrieval_min_score: float | None = None`
  (sezioni "embeddings" e "retrieval"), con docstring di intento.
- [x] T003 In `src/sertor_core/config/settings.py`: helper `_float_or_none_env(name)` (assente→None,
  presente→float) e popolare i tre campi in `Settings.load()` da `SERTOR_EMBED_RETRY_ATTEMPTS`,
  `SERTOR_EMBED_RETRY_BASE`, `SERTOR_MIN_SCORE`. Default invariati quando le env sono assenti.
- [x] T004 [P] In `tests/unit/test_settings.py` (o file settings esistente): test che le tre env si
  mappano sui campi e che, assenti, restano ai default (`retrieval_min_score is None`,
  `embed_retry_attempts == 3`, `embed_retry_base_s == 0.5`).

**Checkpoint:** `Settings` espone le tre manopole; default = comportamento odierno.

---

## Phase 3: User Story 1 — Resilienza embedding (P1)

**Goal:** una chiamata di embedding sopravvive agli errori transitori (retry+backoff), fallisce
esplicita a esaurimento, non ritenta i non-ritentabili, è disattivabile (`attempts=1`).
**Independent test:** `tests/unit/test_embed_retry.py` con provider fittizio 429→200 e sempre-429.

- [x] T010 [US1] Creare `src/sertor_core/adapters/embeddings/_retry.py`: dataclass `RetryPolicy`
  (`max_attempts`, `base_backoff_s`; normalizza `max_attempts<1`→1) e funzione
  `with_retry(fn, policy, *, sleep, rng)` — cattura `EmbeddingError`, ritenta solo se `retriable` e
  tentativi residui, attesa `base*2**i*(0.5+rng())` via `sleep`, log `embeddings_retry`
  (provider opzionale, attempt, reason, wait_ms), a esaurimento ri-solleva l'ultimo `EmbeddingError`.
- [x] T011 [P] [US1] In `tests/unit/test_embed_retry.py`: test di `with_retry` in isolamento —
  successo al 2° tentativo (429→ok); esaurimento → `EmbeddingError`; `retriable=False` → ri-solleva
  subito senza attese; `max_attempts=1` → una sola chiamata; backoff/jitter deterministico (`rng` fisso,
  `sleep` che registra le durate, nessuna attesa reale).
- [x] T012 [US1] In `src/sertor_core/adapters/embeddings/azure.py`: aggiungere al costruttore
  `retry: RetryPolicy | None = None`, `sleep=time.sleep`, `rng=random.random`; in `embed()` avvolgere
  `self._embed_batch(batch)` in `with_retry(... )` quando `retry` ha `max_attempts>1`, altrimenti
  chiamata diretta (zero overhead). Import locali `time`/`random`.
- [x] T013 [US1] In `src/sertor_core/adapters/embeddings/ollama.py`: stessa aggiunta di T012 (identica
  logica condivisa via `with_retry`).
- [x] T014 [US1] In `src/sertor_core/composition.py` `build_embedder`: costruire
  `RetryPolicy(max_attempts=settings.embed_retry_attempts, base_backoff_s=settings.embed_retry_base_s)`
  e passarla a `AzureEmbedder` e `OllamaEmbedder` (parametro `retry=`).
- [x] T015 [P] [US1] In `tests/unit/test_embed_retry.py`: test a livello di embedder — `AzureEmbedder`
  con `client` fittizio 429→200 e `RetryPolicy(3, 0.5)` completa `embed(["q"])`; sempre-429 → solleva
  `EmbeddingError` dopo 3 tentativi; verificare che il retry è **per-batch** (un batch fallito non
  ri-embedda batch precedenti). Analogo smoke per `OllamaEmbedder`.

**Checkpoint US1:** retry attivo e disattivabile, errori espliciti, test offline verdi.

---

## Phase 4: User Story 2 — Segnale di confidenza (P2)

**Goal:** con soglia configurata, i risultati deboli sono esclusi e si emette `low_confidence`; soglia
assente = comportamento odierno; segnale additivo (contratto invariato), coerente su facade/baseline/hybrid.
**Independent test:** `tests/unit/test_confidence_threshold.py` con store/embedder mock e score controllati.

- [x] T020 [US2] In `src/sertor_core/services/retrieval.py`: funzione pura module-level
  `apply_min_score(results, min_score) -> tuple[list[RetrievalResult], bool]` (None→`(results, False)`;
  altrimenti `kept = [r for r in results if r.score >= min_score]`,
  `low = bool(results) and not kept`).
- [x] T021 [US2] In `src/sertor_core/services/retrieval.py` `RetrievalFacade`: aggiungere
  `min_score: float | None = None` al costruttore; nel percorso denso proprio di `_search` (ramo
  **senza** retriever) e in `_search_multi` applicare `apply_min_score` ai risultati; se `low` →
  `log_event(WARNING, "low_confidence", collection/collections, provider, min_score, best_score,
  candidates)` e ritornare `[]`. NON applicare sul ramo `retriever` (lo fa l'ibrido).
- [x] T022 [US2] In `src/sertor_core/engines/baseline.py` `query()`: dopo `store.query`, applicare
  `apply_min_score(results, self._settings.retrieval_min_score)`; se `low` → log `low_confidence`
  (collection, provider, soglia, best_score) e ritornare `[]`. `ensure_index()`/`IndexNotFoundError`
  invariati (FR-015).
- [x] T023 [US2] In `src/sertor_core/engines/hybrid.py` `retrieve()`: quando
  `self._settings.retrieval_min_score is not None`, filtrare il **pool denso** (`dense`) per
  `score >= soglia` **prima** di RRF (sia nel ramo degradato dense-only sia nel ramo ibrido pieno); se
  il denso si svuota → log `low_confidence` e ritornare `[]`. Lo score finale resta RRF (research D4).
- [x] T024 [US2] In `src/sertor_core/composition.py` `build_facade`: passare
  `min_score=settings.retrieval_min_score` a `RetrievalFacade`. (Baseline/Hybrid leggono già da
  `self._settings`: nessuna modifica al loro wiring.)
- [x] T025 [P] [US2] In `tests/unit/test_confidence_threshold.py`: test di `apply_min_score`
  (pura: None passthrough; filtro; low quando tutti sotto). Test facade (single + multi) con store mock:
  in-dominio → risultati; fuori-dominio (tutti < soglia) → `[]` + evento `low_confidence`; soglia None →
  regressione (= oggi). Test baseline (strict resta strict; filtro su indice esistente). Test hybrid
  (filtro sul denso prima di RRF; degradazione dense-only filtrata; soglia None invariato).

**Checkpoint US2:** soglia/segnale coerenti sui tre punti d'ingresso, additivi, test offline verdi.

---

## Phase 5: Polish & cross-cutting

- [x] T030 Eseguire l'intera suite offline `uv run pytest -m "not cloud" -q`: deve restare **verde**,
  inclusi i test pre-esistenti (SC-006, retro-compatibilità).
- [x] T031 [P] `uv run ruff check .` (e `--fix` se serve): nessun errore (line-length 100, regole E,F,I,UP,B).
- [x] T032 [P] Verifica retro-compatibilità mirata (SC-004): un test che, con `Settings` ai default
  (`min_score=None`, `attempts=3` ma provider sano), gli esiti di retrieval sono identici a prima
  (nessun filtro applicato, nessun evento `low_confidence`).
- [x] T033 Aggiornare `quickstart.md` se le firme reali divergono dagli esempi (allineamento doc↔codice).

---

## Dipendenze ed esecuzione

- **Ordine storie:** Setup → Foundational (T002–T004) → US1 (P1) → US2 (P2) → Polish.
- US1 e US2 sono **indipendenti** dopo il Foundational (file diversi), ma si consegnano in ordine di
  priorità. Dentro una storia, i `[P]` (test) corrono in parallelo all'implementazione dei file diversi.
- **MVP:** US1 (resilienza) da sola è già un incremento di valore consegnabile.

### Esempi di parallelizzazione
- Dopo T010: T011 (test helper) ∥ T012/T013 (adapter) — file diversi.
- Dopo T020: T025 (test) può iniziare sulla parte pura mentre si fanno T021–T024.
