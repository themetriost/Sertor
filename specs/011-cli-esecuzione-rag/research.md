# Research — FEAT-011 CLI di esecuzione RAG `sertor-rag`

**Feature**: `011-cli-esecuzione-rag` | **Fase**: Phase 0 (Outline & Research) | **Data**: 2026-06-11

Questo documento risolve le decisioni di design aperte della spec (zero `NEEDS CLARIFICATION`: la
spec e i requisiti EARS sono già clarified). Le decisioni sotto sono ancorate alla codebase in
`master` (`src/sertor_core/`) e alla costituzione v1.1.0. Formato: Decision / Rationale /
Alternatives considered.

---

## D1 — Collocazione del modulo CLI

**Decision.** Il modulo CLI vive **dentro il pacchetto `sertor_core`**, in
`src/sertor_core/cli/` (package con `__init__.py`, `__main__.py`, e moduli di supporto
`output.py`, `logging_setup.py`). Il console-script `sertor-rag` punta a
`sertor_core.cli.__main__:main`, aggiunto in `pyproject.toml [project.scripts]` accanto a
`sertor-wiki-tools`.

**Rationale.**
- Il precedente diretto `sertor-wiki-tools` vive in `src/sertor_core/wiki_tools/__main__.py` dentro
  il pacchetto core: stesso pattern, stessa distribuzione (`A-1`).
- La CLI usa **solo il core** — `build_indexer()`, `build_facade()`, `build_baseline_engine()`,
  `Settings`, le eccezioni di dominio — senza alcuna dipendenza extra. Non c'è la motivazione che
  ha spinto `sertor_mcp` in un package separato (isolare l'SDK `mcp`, extra opzionale `[mcp]`):
  qui non si introduce nessuna nuova dipendenza, quindi nessun package separato e nessun extra
  in `pyproject.toml`.
- `argparse` (stdlib) basta: nessuna dipendenza nuova (Principio III, YAGNI). Coerente con
  `wiki_tools` che usa già `argparse`.
- Confine netto Principio I: `cli/` è un consumatore del core (dipende verso l'interno), il core
  non importa `cli/`.

**Alternatives considered.**
- *Package separato `src/sertor_rag/`* (come `sertor_mcp`): rifiutato — `sertor_mcp` è separato per
  isolare la dipendenza pesante/opzionale `mcp`; qui non c'è dipendenza extra, separare creerebbe
  un secondo top-level package senza guadagno e contro YAGNI.
- *Estendere `wiki_tools/__main__.py`*: rifiutato — `sertor-rag` (RAG: index/search) e
  `sertor-wiki-tools` (nucleo wiki deterministico) sono due console-script distinti per dominio
  (DA-8, REQ-001); mescolarli confonderebbe la superficie.
- *Libreria `click`/`typer`*: rifiutato — nuova dipendenza non giustificata (Principio III); il
  pattern `argparse` con sub-parser è già rodato e sufficiente.

---

## D2 — Via "strict" per `search` su indice assente (FR-012)

**Decision.** Per la ricerca, la CLI usa il **motore baseline** (`build_baseline_engine()`), il cui
`.query()` è **strict**: solleva `IndexNotFoundError` se la collezione non esiste. La CLI mappa
quell'eccezione in un messaggio leggibile ("indice inesistente: esegui prima `sertor-rag index
<path>`") + exit code non-zero.

**Rationale.**
- La policy errori del core è **deliberatamente non uniforme** (CLAUDE.md, da NON uniformare): la
  facade è *tollerante* (indice assente → `[]` + warning, per composabilità), il motore baseline è
  *strict* (`IndexNotFoundError`, per usabilità del consumatore). FR-012/REQ-022 chiede esattamente
  l'errore esplicito "nessun risultato vuoto silenzioso" → la via strict.
- Riusare il motore evita di duplicare nella CLI una verifica `store.exists()` (che richiederebbe di
  conoscere lo store concreto → violerebbe il confine sottile, Principio I). Il check vive già nel
  core (`BaselineEngine.query`, `baseline.py:61-65`).
- Il motore baseline interroga in modalità `"both"` (`baseline.py:68`), coerente col default
  `both` di FR-011; per i filtri `--type code|doc` si usa invece la **facade** (vedi D6) che è
  tollerante — ma la CLI applica comunque un check esplicito di esistenza prima, per mantenere la
  via strict anche su `code`/`doc` (vedi D6).

**Alternatives considered.**
- *Usare la facade + check `store.exists()` nella CLI*: rifiutato come via primaria — esporrebbe lo
  store concreto alla CLI o richiederebbe un metodo nuovo; il motore baseline incapsula già il
  check strict.
- *Usare la facade e trattare `[]` come "indice assente"*: rifiutato — ambiguo: `[]` può anche
  significare "indice presente ma zero hit" (caso lecito). Confondere i due viola la chiarezza
  d'errore (NFR-04) e SC: "no silent empty result".

**Nota di design per i filtri di tipo (vedi D6).** Per realizzare `--type code|doc|both` su una
sola via strict senza duplicare lo store nella CLI, il piano introduce nel core un metodo di
verifica esistenza esposto in modo astratto: si riusa il fatto che `BaselineEngine` espone già
`query`. La CLI fa così: per `both` usa `BaselineEngine.query` (strict nativo); per `code`/`doc`
usa `RetrievalFacade.search_code/search_docs`, ma **prima** chiama `BaselineEngine.query` con `k=1`
non è idoneo (consumerebbe un embedding inutile). La soluzione adottata è D6.

---

## D3 — Validazione statica dei parametri di backend (FR-015) senza duplicare default

**Decision.** Si aggiunge al core un **validatore di configurazione** puro:
`Settings.validate_backend()` (metodo sull'oggetto `Settings`, in `config/settings.py`) che ritorna
la lista dei campi richiesti **mancanti** per il backend/store selezionato, **senza** contattare
servizi. La CLI lo invoca prima di ogni operazione RAG; se la lista non è vuota, blocca con
`ConfigError` leggibile che **nomina i campi mancanti**.

Regole di validazione (derivate dai campi che `composition.build_embedder/build_store` leggono):
- `backend == "azure"` (embeddings Azure): richiede `azure_openai_endpoint`,
  `azure_openai_api_key`, `azure_openai_embed_deployment` non vuoti.
- `store_backend == "azure"` (Azure AI Search): richiede `azure_search_endpoint`,
  `azure_search_api_key` non vuoti.
- `backend == "local"` / `store_backend == "local"`: sempre formalmente completo (Ollama/Chroma
  hanno default validi) → nessun campo richiesto, mai bloccato (edge case spec: il default `local`
  non viene mai bloccato staticamente).

**Rationale.**
- Il validatore vive in `Settings` (l'**unica** fonte di default e di conoscenza dei campi di
  backend, Principio VIII): la CLI non duplica né i default né la mappa "quali campi servono per
  azure". La CLI conosce solo l'esito (lista di mancanti).
- È puro e deterministico → testabile senza rete (NFR-02), riusabile anche da `sertor_mcp` o altri
  consumatori in futuro.
- Validazione **statica** ≠ raggiungibilità: l'irraggiungibilità (Ollama spento, endpoint errato)
  resta errore a runtime (FR-007/REQ-012, `EmbeddingError`/`VectorStoreError`). La distinzione è
  esplicita nella spec (edge case).

**Alternatives considered.**
- *Validazione nella CLI con if hardcoded sui campi azure*: rifiutato — duplica la conoscenza dei
  campi di backend e i default, violando Principio VIII/NFR-06.
- *Lasciar fallire a runtime al primo contatto col servizio*: rifiutato — viola FR-015/SC-004
  (blocco **prima** di contattare qualunque servizio, 100% dei casi) e darebbe un errore di rete
  poco leggibile invece di "manca AZURE_OPENAI_ENDPOINT".
- *Validatore standalone in `composition.py`*: accettabile, ma `Settings` è il posto canonico (è
  l'oggetto che porta i campi); si è scelto il metodo su `Settings` per coesione.

---

## D4 — Design dell'osservabilità a runtime

**Decision.** Tre leve CLI + un'estensione additiva del core.

Leve CLI (modulo `cli/logging_setup.py`, applicate prima di eseguire il comando):
- `-v/--verbose` → configura il logger `sertor_core` a livello `INFO` con un `StreamHandler` su
  stderr (formato umano `op=... k=v`). Default senza `-v`: `WARNING` (gli eventi INFO restano
  silenziati, com'è oggi).
- `--log-json` → lo `StreamHandler` usa un formatter che emette **un record JSON per evento**
  serializzando i campi strutturati di `log_event` (campo `extra`: `operation` + i field). Si può
  combinare con `-v` per il livello.
- `--log-config <file>` → carica un **dictConfig** (YAML o JSON, autodetect per estensione/parse)
  via `logging.config.dictConfig`; ha precedenza sulle altre due leve (l'utente governa tutto:
  handler, appender file/syslog, livelli). YAML letto con `pyyaml` **se installato**, JSON con
  stdlib; se `--log-config` è YAML e `pyyaml` manca → errore leggibile.

Estensione additiva del core (FR-020/REQ-053): negli adapter al boundary
(`adapters/embeddings/*`, `adapters/vectorstores/*`) e/o nei punti dove gli errori vengono avvolti,
**prima** di sollevare `EmbeddingError`/`VectorStoreError` si emette `log_event(logging.ERROR,
<op>, provider=..., backend=..., reason=...)`. È additivo: non cambia il comportamento d'errore
(le eccezioni restano), aggiunge solo l'evento di log. La redazione segreti è già garantita da
`redact()` in `log_event`.

Documentazione dei campi (FR-021/REQ-054): uno **schema dei campi di log per operazione** è
documentato in `contracts/log-events.md` (questa feature) e referenziato da
`src/sertor_core/observability/README` o docstring; elenca per ogni `operation` (`index`,
`retrieve`, `baseline_query`, e i nuovi `*_error`) i campi emessi.

**Rationale.**
- `log_event` (`observability/logging.py`) emette già `extra={"operation": ..., **safe}`: il
  formatter JSON ha già i campi strutturati a disposizione, senza riscrivere il core.
- Il core **non impone** handler/livello (scelta voluta, requirements §1): la CLI è il consumatore
  che li configura — confine corretto (Principio I/IX). Il dictConfig dà l'aggancio ad appender
  esterni "senza modificare il codice" (SC-006/LSC-7).
- `pyyaml` è una dipendenza **opzionale leggera**: JSON dictConfig funziona con la sola stdlib; si
  introduce `pyyaml` solo se si vuole YAML — valutazione nel plan (vedi Technical Context). Per non
  introdurre dipendenze non necessarie, l'MVP supporta JSON via stdlib e YAML se `pyyaml` è
  presente (degradazione esplicita con messaggio).

**Alternatives considered.**
- *Logging configurato dentro il core*: rifiutato — violerebbe la scelta del core di non imporre
  framework al chiamante e il confine Principio I.
- *Solo `-v` senza JSON/dictConfig*: rifiutato — non soddisfa REQ-051/052 (Should) e SC-006.
- *Forzare `pyyaml` come dipendenza core*: rifiutato — peso non necessario quando JSON basta; resta
  opzionale.

---

## D5 — Formato output di `search`: umano vs `--json`, anteprima troncata, `--full`

**Decision.**
- **Anteprima troncata** di default in entrambi i formati. La lunghezza dell'anteprima è un nuovo
  parametro di configurazione **centralizzato** `preview_chars` su `Settings` (default 240),
  letto da env `SERTOR_PREVIEW_CHARS` — così non si hardcoda un numero nella CLI (Principio
  VIII/NFR-06). La troncatura aggiunge un'ellissi (`…`) quando il testo è più lungo.
- `--full` → emette il **testo completo** del chunk (`RetrievalResult.text`), nessuna troncatura.
- Output **umano** (default): blocco per risultato con `score`, `path`, `doc_type`, `chunk_id` e
  anteprima; ordinati per score decrescente (già garantito dal core).
- `--json` → **array JSON** di oggetti con campi `path`, `doc_type`, `chunk_id`, `score`,
  `preview` (o `text` con `--full`); equivalenza informativa con l'output umano (SC-002).

**Rationale.**
- DA-C5 risolta: testo di default + `--json`, anteprime troncate in entrambi per contenere il
  consumo di token quando un agente usa la CLI (FR-010/013/REQ-020/023).
- La troncatura è una **scelta operativa** → vive in `Settings` (Principio VIII), non come costante
  nel codice CLI. Aggiunge un default centralizzato in più nel posto giusto.
- `RetrievalResult` (`domain/entities.py:97-106`) porta già `text`, `path`, `chunk_id`, `doc_type`,
  `score`, `metadata`: la "vista CLI" è una pura proiezione/formattazione, nessuna logica nel CLI.

**Alternatives considered.**
- *Lunghezza anteprima hardcoded nel CLI*: rifiutato — viola Principio VIII (default fuori dalla
  config centralizzata).
- *Default `--full`*: rifiutato — contro DA-C5 (economia token per uso da agente).
- *Output umano senza `--json`*: rifiutato — REQ-023/SC-002 chiedono il consumo programmatico.

---

## D6 — `--type code|doc|both`: una via strict unica per tutti i filtri

**Decision.** La verifica "indice esistente" è **unica e strict per tutti i tipi**. Si aggiunge al
core un metodo astratto di esistenza esposto dal motore o si riusa il check del baseline così:
- La CLI costruisce **sia** il `BaselineEngine` **sia** la `RetrievalFacade` dalla stessa
  `Settings`/composition.
- Esegue **prima** un check di esistenza strict: chiama un nuovo metodo
  `BaselineEngine.ensure_index()` (estrazione del check `IndexNotFoundError` già presente in
  `query`, senza embeddare nulla). Se l'indice manca → `IndexNotFoundError` → messaggio leggibile,
  exit non-zero (FR-012, per **qualunque** `--type`).
- Poi instrada per tipo: `both` → `facade.search_combined` (o `baseline.query`, equivalenti);
  `code` → `facade.search_code`; `doc` → `facade.search_docs`.

`ensure_index()` è un'estrazione pura del controllo già scritto in `baseline.py:61-65` (refactor
che lascia il codice più pulito, Boy Scout Rule / Principio VII), non nuova logica.

**Rationale.**
- Garantisce la via strict (FR-012) per `code` e `doc`, che altrimenti passerebbero dalla facade
  tollerante (`[]` silenzioso) — il che violerebbe "no silent empty result".
- Non duplica lo store nella CLI: il check resta nel core. La facade serve i filtri di tipo (che il
  baseline non distingue: interroga sempre `both`).
- Cambiamento minimo e coerente con la policy errori voluta (non la uniforma: la facade resta
  tollerante per gli altri consumatori).

**Alternatives considered.**
- *Solo `BaselineEngine.query` per tutto*: rifiutato — il baseline non filtra per `doc_type`
  (`baseline.py:68` interroga `"both"`); servirebbe estendere il motore, fuori scope.
- *Solo facade + interpretare `[]` come assenza*: rifiutato — ambiguo (D2).
- *Esporre `store.exists()` alla CLI*: rifiutato — espone lo store concreto, viola il confine
  sottile (Principio I).

---

## D7 — `--corpus` e namespacing (FR-009/REQ-014)

**Decision.** La CLI accetta un flag `--corpus <nome>` su `index` e `search`. Quando presente,
**prevale** sulla configurazione (`SERTOR_CORPUS`): la CLI costruisce la `Settings` e poi applica
`dataclasses.replace(settings, corpus=<nome>)` prima di passarla a `build_indexer()`/`build_facade()`.
Il namespacing della collezione è già gestito da `collection_name(settings, embedder)`
(`composition.py:58-69`): nessuna logica nuova nella CLI.

**Rationale.**
- `Settings` è frozen e `composition` deriva la collezione da `settings.corpus`: basta sostituire
  il campo (pattern già usato in `build_facade` per gli extra corpora, `composition.py:97-100`).
- "Il flag esplicito prevale sulla configurazione" (FR-009) → override locale via `replace`.
- Corpora distinti restano isolati in collezioni namespaced (DA-C2), nessuna mescolanza.

**Alternatives considered.**
- *Solo via env, nessun flag*: rifiutato — REQ-014 chiede esplicitamente l'opzione `--corpus` con
  precedenza sul config.

---

## D8 — Mappatura eccezioni di dominio → exit code e messaggi (FR-003/004/NFR-04)

**Decision.** `main()` cattura `SertorError` (radice di tutte le eccezioni di dominio) come
`wiki_tools/__main__.py:184` già fa: stampa `errore: <messaggio leggibile>` su stderr, exit `1`. Le
eccezioni di dominio (`ConfigError`, `IngestionError`, `EmbeddingError`, `VectorStoreError`,
`IndexNotFoundError`, `ProviderMismatchError`) hanno già `__str__` ricchi e leggibili
(`domain/errors.py`) → non serve mappare caso per caso. `argparse` gestisce nativamente
sottocomando ignoto / argomento mancante con exit `2` e messaggio d'uso (FR-003). Lo stack trace
grezzo non è mostrato salvo verbosità elevata (NFR-04).

**Rationale.**
- Pattern identico e già rodato in `wiki_tools` (consistenza, riuso). Le eccezioni del core sono
  progettate per essere leggibili (Principio IV).
- Exit code: `0` successo, `1` errore di dominio, `2` errore d'uso argparse → scriptabilità
  (FR-004).

**Alternatives considered.**
- *Mappa esplicita eccezione→messaggio nella CLI*: rifiutato — le eccezioni portano già contesto
  azionabile; mappare duplicherebbe il messaggio e divergerebbe.

---

## Riepilogo dipendenze e impatti

| Elemento | Posizione | Tipo |
|----------|-----------|------|
| `sertor_core/cli/` (nuovo) | package CLI sottile | nuovo, consuma il core |
| `Settings.validate_backend()` | `config/settings.py` | additivo (puro) |
| `Settings.preview_chars` + `SERTOR_PREVIEW_CHARS` | `config/settings.py` | additivo (default centralizzato) |
| `BaselineEngine.ensure_index()` | `engines/baseline.py` | refactor (estrazione check esistente) |
| `log_event(ERROR, ...)` ai boundary | `adapters/embeddings/*`, `adapters/vectorstores/*` | additivo (osservabilità) |
| `sertor-rag` console-script | `pyproject.toml [project.scripts]` | additivo |
| `pyyaml` (opzionale, per `--log-config` YAML) | dipendenza opzionale | da valutare nel plan |

Nessuna dipendenza nuova **obbligatoria**: la CLI usa `argparse` (stdlib) e il core. `pyyaml`
resta opzionale (JSON dictConfig copre lo stdlib-only).
