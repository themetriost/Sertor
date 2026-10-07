# Tasks: Embedding con l'API OpenAI diretta

**Input**: Design documents from `specs/137-provider-openai/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openai-embedding-provider.md, quickstart.md

**Tests**: inclusi — il Principio V li richiede e SC-004 misura la non-regressione sui test Azure
esistenti. Tutti senza rete (`httpx.MockTransport`) salvo T020 (`cloud`).

**Organization**: per user story (spec.md). US1 e US2 sono entrambe P1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza da task incompleti)
- **[Story]**: US1…US4 della spec

---

## Phase 1: Setup

- [x] T001 Misurare la baseline: eseguire `uv run pytest tests/unit/test_embeddings.py tests/unit/test_embed_retry.py tests/unit/test_embedding_token_log.py -q` e annotare il numero di test verdi (gate di non-regressione per T003)

---

## Phase 2: Foundational (bloccante per tutte le story)

**Purpose**: base di protocollo condivisa (research D-1) e configurazione (D-2).

- [x] T002 Creare `src/sertor_core/adapters/embeddings/_openai_protocol.py` con la classe base `OpenAIProtocolEmbedder` estratta da `azure.py`: costruttore che riceve `name`, `url`, `headers`, `params`, `model`, `batch_size`, `client`, `retry`, `sleep`, `rng`; metodi `_embed_batch`, `_embed_batch_resilient`, `embed` con comportamento identico all'attuale (ordinamento per `index`, `dim` dalla prima risposta, token in `usage.total_tokens`, eventi `embeddings`/`embeddings_error`, classificazione errori 429/5xx retriable, `httpx.HTTPError` retriable)
- [x] T003 Ridurre `src/sertor_core/adapters/embeddings/azure.py` a sottoclasse di `OpenAIProtocolEmbedder`: conserva firma del costruttore, messaggio «incomplete Azure configuration» con `reason="endpoint/api_key/deployment missing"`, intestazione `api-key`, `api-version` solo se l'endpoint non contiene `/openai/v1`, nome `azure:<deployment>`. Gate: i test di T001 verdi **senza modifiche** e in numero uguale
- [x] T004 In `src/sertor_core/config/settings.py`: aggiungere la costante pubblica `EMBED_PROVIDERS = ("glove", "hash", "ollama", "azure", "openai")`; i campi `openai_api_key: str = field(default="", repr=False)`, `openai_embed_model: str = "text-embedding-3-large"`, `openai_base_url: str = "https://api.openai.com/v1"`; aggiornare il commento di `embed_provider`
- [x] T005 In `Settings.load()` (`src/sertor_core/config/settings.py`) leggere `OPENAI_API_KEY` (default `""`), `OPENAI_EMBED_MODEL` e `OPENAI_BASE_URL` con fallback **al default del campo** (`os.getenv(X) or cls.<campo>`, mai il letterale ripetuto), così una variabile vuota vale come assente
- [x] T006 In `src/sertor_core/config/settings.py` aggiungere `missing_provider_keys()` (chiavi mancanti del solo provider di embedding: `AZURE_OPENAI_*` per `azure`, `OPENAI_API_KEY` per `openai`, nessuna altrimenti) e ricomporre `validate_backend()` come `missing_provider_keys()` + chiavi dello store, aggiornando il docstring (fonte unica)
- [x] T007 [P] Test in `tests/unit/test_settings_validate_backend.py`: `openai` senza chiave → `["OPENAI_API_KEY"]`; `openai` con chiave → `[]`; `openai` non richiede `AZURE_OPENAI_*`; `missing_provider_keys()` esclude le chiavi dello store; `validate_backend()` invariato per `azure`/`glove` (+ store azure)
- [x] T008 [P] Test in `tests/unit/test_settings.py`: default di modello e URL; `OPENAI_EMBED_MODEL=""`/`OPENAI_BASE_URL=""` → default; valori impostati letti; la chiave non compare in `repr(Settings)`

**Checkpoint**: base pronta, Azure invariato, configurazione completa.

---

## Phase 3: User Story 1 — Indicizzare e cercare con una chiave OpenAI (P1) 🎯 MVP

**Goal**: `SERTOR_EMBED_PROVIDER=openai` + chiave ⇒ index e search funzionano senza variabili Azure.

**Independent Test**: test di contratto con trasporto finto + `build_embedder` restituisce `OpenAIEmbedder`.

- [x] T009 [US1] Creare `src/sertor_core/adapters/embeddings/openai.py` con `OpenAIEmbedder(base_url, api_key, model, batch_size=64, client=None, retry=None, sleep=time.sleep, rng=random.random)`: sottoclasse di `OpenAIProtocolEmbedder`, URL `base_url.rstrip("/") + "/embeddings"`, intestazione `Authorization: Bearer <key>`, nessun parametro di query, nome `openai:<model>`; campi vuoti → `EmbeddingError(provider="openai", reason="<campi> missing", retriable=False)`
- [x] T010 [US1] In `src/sertor_core/composition.py`: ramo `elif provider == "openai"` in `build_embedder` (import lazy, `retry=retry`, `batch_size=settings.embed_batch_size`); sostituire `_VALID_EMBED_PROVIDERS` con `EMBED_PROVIDERS` importato dalle settings; aggiornare il docstring («FIVE branches»); aggiornare il docstring di `src/sertor_core/adapters/embeddings/__init__.py`
- [x] T011 [P] [US1] Creare `tests/unit/test_openai_embedder.py`: URL con e senza barra finale; intestazione `Authorization: Bearer`; assenza di `api-key` e di `api-version`; payload `{"model", "input"}`; ordine dei vettori ripristinato da `index`; lotti da `batch_size`; `dim` dalla prima risposta; nome `openai:<model>`; chiave/modello/URL vuoti → `EmbeddingError` non retriable che nomina i campi (FR-014)
- [x] T012 [P] [US1] Test in `tests/unit/test_embedder_local_composition.py`: `embed_provider="openai"` → istanza `OpenAIEmbedder` con modello e URL dalle settings; valore sconosciuto → `ConfigError` il cui messaggio contiene `openai`; `EMBED_PROVIDERS` contiene i cinque provider; con `embed_provider="openai"` e variabili `azure_openai_*` valorizzate si ottiene comunque `OpenAIEmbedder` (FR-005)

**Checkpoint**: MVP — il provider si seleziona e produce vettori.

---

## Phase 4: User Story 2 — Capire subito cosa non va (P1)

**Goal**: chiave mancante/rifiutata/servizio irraggiungibile ⇒ diagnosi che nomina il problema, mai la chiave.

**Independent Test**: si provocano i tre guasti e si leggono errore, evento e output di `doctor`.

- [x] T013 [US2] In `src/sertor_core/cli/__main__.py`: calcolare le chiavi del provider con `settings.missing_provider_keys()` e rimuovere l'insieme hardcoded `_PROVIDER_ENV_KEYS` (research D-3); verificare che l'area *config* riceva ancora le chiavi dello store
- [x] T014 [P] [US2] Test in `tests/unit/test_openai_embedder.py`: 401 → `EmbeddingError` non retriable con `reason="http 401"` e `provider="openai:<model>"`; 429 e 503 retriable; `httpx.ConnectError` retriable; retry per lotto senza ri-embeddare lotti riusciti (stessa forma di `test_embed_retry.py`); la stringa della chiave non compare in `str(err)`, nella `reason` né nei campi degli eventi registrati
- [x] T015 [P] [US2] Test in `tests/unit/test_openai_embedder.py`: evento `embeddings` con `tokens` quando `usage` presente e senza il campo quando assente (stessa forma di `test_embedding_token_log.py`)
- [x] T016 [P] [US2] Test in `tests/unit/test_cli_doctor.py`: provider `openai` con chiave vuota → area *provider* `fail` che nomina `OPENAI_API_KEY`; con chiave → `pass`; provider `azure` invariato
- [x] T017 [P] [US2] Test della sonda: `build_provider_probe` con `openai` e trasporto che risponde 401 → `unreachable` con motivo che non contiene la chiave (in `tests/unit/test_doctor.py` o nel file dei test della sonda esistente)

**Checkpoint**: tutti i guasti sono diagnosticati senza esporre la chiave.

---

## Phase 5: User Story 3 — Indici separati per provider e modello (P2)

**Goal**: cambiare provider/modello non mescola collezioni né cache.

- [x] T018 [P] [US3] Test in `tests/unit/test_composition.py`: `collection_name` per `openai:text-embedding-3-large` ≠ `openai:text-embedding-3-small` ≠ `azure:<dep>` ≠ `glove`; test in `tests/unit/test_embedding_cache.py`: vettori in cache per un modello non serviti a un altro

---

## Phase 6: User Story 4 — Servizio compatibile OpenAI (P3)

- [x] T019 [P] [US4] Test in `tests/unit/test_openai_embedder.py`: `OPENAI_BASE_URL` personalizzato (es. `http://localhost:8080/v1`) → richiesta a `http://localhost:8080/v1/embeddings`, passando da `build_embedder` con le settings

---

## Phase 7: Polish & cross-cutting

- [x] T020 [P] Creare `tests/integration/test_openai_live.py` con marker `cloud`: salta senza `OPENAI_API_KEY`; embedda due testi e verifica due vettori di dimensione 3072
- [x] T021 [P] `.env.example`: sezione «embeddings: provider cloud (OpenAI), solo se SERTOR_EMBED_PROVIDER=openai» con le tre variabili commentate e i default; elencare `openai` fra i valori del selettore
- [x] T022 [P] `docs/install.md`: provider `openai` nell'elenco dei provider (§2) con le tre variabili, default, costo indicativo, avviso «cambiare provider richiede `sertor-rag index .`», e nota che il wizard `sertor configure` non lo conosce ancora (attivazione **manuale** in `.sertor/.env`; `--set` lo ignora)
- [x] T023 Gate pre-merge (2026-10-07: 1520 passed/3 skipped; packages sertor 595, sertor-install-kit 207, sertor-flow 149, speclift 122, specaudit 59; ruff pulito; test Azure 24/24 invariati): `uv run pytest -m "not cloud"` e `uv run ruff check .` verdi; confrontare il numero di test Azure con la baseline di T001
- [ ] T024 Quickstart sul dogfood (`specs/137-provider-openai/quickstart.md`): se l'utente fornisce una chiave OpenAI, `doctor --online`, `sertor-rag index .`, ricerca CLI e — dopo il reconnect MCP — smoke `search_code`/`search_docs`/`find_symbol`; altrimenti dichiararlo non eseguito
- [ ] T025 Aggiornare la riga FEAT-012 in `requirements/sertor-core/epic.md` (✅ + «vedi EXEC» a merge avvenuto) e preparare la pubblicazione per Kaelen in bacheca (cablaggio wizard + i tre silenzi di research D-7)

---

## Dependencies & Execution Order

- **T001 → T002 → T003** (estrazione con gate di non-regressione).
- **T004 → T005 → T006**; T007/T008 dopo T006.
- **US1** (T009–T012) dipende da Phase 2. **US2** dipende da US1 (T009/T010). **US3/US4** dipendono da
  US1, indipendenti fra loro.
- **Polish**: T021/T022 indipendenti dal codice; T023 dopo tutti i task di codice; T024 dopo T023.

## Parallel Example

```text
Dopo T006: T007, T008 in parallelo.
Dopo T010: T011, T012, T014, T015, T016, T017, T018, T019 in parallelo (file di test diversi
           salvo test_openai_embedder.py: T011/T014/T015/T019 vanno in sequenza sullo stesso file).
Sempre: T021, T022.
```

## Copertura (analyze)

| FR | Task | | FR | Task |
|---|---|---|---|---|
| 001 | T009, T010, T012 | | 010 | T015 |
| 002 | T010, T012 | | 011 | T014 |
| 003 | T004, T005, T008 | | 012 | T014 |
| 004 | T004, T005, T008 | | 013 | T014 |
| 005 | T012 | | 014 | T009, T011 |
| 006 | T006, T007 | | 015 | T008, T014, T017 |
| 007 | T013, T016 | | 016 | T018 |
| 008 | T011 | | 017 | T003, T023 |
| 009 | T011 | | 018 | T021, T022 |

Nessun FR senza task, nessun task senza FR o gate. Nessuna contraddizione fra spec, plan e task.

## Implementation Strategy

MVP = Phase 1–3 (provider selezionabile e funzionante). Poi US2 (diagnosi, obbligatoria per una consegna
P1), US3/US4 (solo test, il comportamento esiste già), documentazione e gate. Unica PR.
