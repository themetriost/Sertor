# Data Model — FEAT-011 CLI di esecuzione RAG `sertor-rag`

**Feature**: `011-cli-esecuzione-rag` | **Fase**: Phase 1 (Design) | **Data**: 2026-06-11

La CLI è un **layer sottile**: non introduce nuove entità di dominio persistenti. Le entità che
gestisce sono (a) strutture del core già esistenti, che proietta in output, e (b) piccole strutture
di configurazione/argomenti che vivono solo nel processo CLI. Le entità del core **non vanno
ridefinite** (Principio I/III): la CLI le importa e le formatta.

---

## 1. Entità del core riusate (non ridefinite)

### `Settings` (`sertor_core/config/settings.py`)
Configurazione centralizzata, frozen dataclass. La CLI la carica con `Settings.load()` e, per
`--corpus`, ne deriva una copia con `dataclasses.replace(settings, corpus=...)`.

**Campi aggiunti da questa feature** (additivi, default centralizzati — Principio VIII):

| Campo | Tipo | Default | Env | Uso |
|-------|------|---------|-----|-----|
| `preview_chars` | `int` | `240` | `SERTOR_PREVIEW_CHARS` | lunghezza max anteprima in `search` (D5) |

**Metodo aggiunto** (additivo, puro):

| Metodo | Firma | Ritorno | Uso |
|--------|-------|---------|-----|
| `validate_backend()` | `(self) -> list[str]` | nomi dei campi/env richiesti e mancanti per il backend selezionato (lista vuota = config valida) | FR-015 validazione statica |

Regole di `validate_backend()` (D3):
- `backend == "azure"` → mancano se vuoti: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`,
  `AZURE_OPENAI_EMBED_DEPLOYMENT`.
- `store_backend == "azure"` → mancano se vuoti: `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`.
- `local` (embeddings e/o store) → nessun campo richiesto (sempre completo).
- Restituisce i **nomi delle variabili d'ambiente** (azionabili per l'utente), non i nomi dei campi
  dataclass.

### `IndexReport` (`sertor_core/domain/entities.py`)
Esito di `index`. La CLI lo proietta nel report (US1). Campi rilevanti per l'output:
`collection`, `documents`, `chunks`, `embedding_dim`, `elapsed_ms`, `skipped`.

### `RetrievalResult` (`sertor_core/domain/entities.py`)
Hit di `search`. Campi: `text`, `path`, `chunk_id`, `doc_type` (`DocType`), `score`, `metadata`.
La CLI ne produce la **vista** (sezione 2).

### Eccezioni di dominio (`sertor_core/domain/errors.py`)
`SertorError` (radice), `ConfigError`, `IngestionError`, `EmbeddingError`, `VectorStoreError`,
`IndexNotFoundError`, `ProviderMismatchError`. La CLI le cattura come `SertorError` → messaggio
leggibile + exit `1` (D8). Hanno già `__str__` ricchi.

**Metodo aggiunto al motore** (refactor, non nuova entità):

| Metodo | Firma | Comportamento | Uso |
|--------|-------|---------------|-----|
| `BaselineEngine.ensure_index()` | `(self) -> None` | solleva `IndexNotFoundError` se la collezione non esiste, altrimenti ritorna | check strict pre-search per qualunque `--type` (D6) |

---

## 2. Strutture di vista/CLI (vivono solo nel processo)

Queste **non** sono entità di dominio: sono proiezioni di output. Si possono realizzare come
funzioni di formattazione pure (`cli/output.py`) senza dataclass dedicate, oppure con piccole
dataclass locali al package CLI. Documentate come contratto di output.

### Report di indicizzazione (vista CLI)
Proiezione di `IndexReport`. Campi emessi:

| Campo | Origine | Umano | JSON |
|-------|---------|-------|------|
| collezione | `IndexReport.collection` | sì | `collection` |
| documenti | `IndexReport.documents` | sì | `documents` |
| chunk | `IndexReport.chunks` | sì | `chunks` |
| dimensione embedding | `IndexReport.embedding_dim` | sì | `embedding_dim` |
| tempo (ms) | `IndexReport.elapsed_ms` | sì (opz.) | `elapsed_ms` |

### Risultato di ricerca (vista CLI)
Proiezione di `RetrievalResult`. Campi emessi:

| Campo | Origine | Default (troncato) | Con `--full` |
|-------|---------|--------------------|--------------|
| `path` | `RetrievalResult.path` | sì | sì |
| `doc_type` | `RetrievalResult.doc_type` (`code`/`doc`) | sì | sì |
| `chunk_id` | `RetrievalResult.chunk_id` | sì | sì |
| `score` | `RetrievalResult.score` | sì | sì |
| `preview` | `RetrievalResult.text` troncato a `Settings.preview_chars` (+ `…`) | sì | — |
| `text` | `RetrievalResult.text` integrale | — | sì |

Vincoli:
- Anteprima troncata in **entrambi** i formati salvo `--full` (FR-013).
- Output umano e `--json` informativamente equivalenti (SC-002): stessi campi, stessa proiezione.
- Ordine: per `score` decrescente (già garantito dal core).

### Evento di log strutturato (vista, non persistito dalla CLI)
Prodotto da `log_event` nel core; la CLI ne governa solo emissione/formato. Campi minimi per
operazione documentati in `contracts/log-events.md`. Mai segreti (`redact()` applicato in
`log_event`).

---

## 3. Argomenti CLI (modello degli input)

Struttura logica del parsing (argparse, sub-parser per `index`/`search`). Non è un'entità
persistita: è il modello degli input del processo.

### Globali (precedono il sottocomando, o per-sottocomando, vedi contratto)
| Flag | Tipo | Default | Requisito |
|------|------|---------|-----------|
| `-v`, `--verbose` | bool | off (`WARNING`) | FR-017 |
| `--log-json` | bool | off | FR-018 |
| `--log-config <file>` | path | none | FR-019 |

### `index`
| Arg/Flag | Tipo | Default | Requisito |
|----------|------|---------|-----------|
| `path` (posizionale) | path | — (obbligatorio) | FR-005/006 |
| `--corpus <nome>` | str | da `Settings` | FR-009 |
| `--json` | bool | off (output umano) | (output report JSON) |

### `search`
| Arg/Flag | Tipo | Default | Requisito |
|----------|------|---------|-----------|
| `query` (posizionale) | str | — (obbligatorio, non vuoto) | FR-010 |
| `-k <n>` | int | `Settings.default_k` | FR-011 |
| `--type code\|doc\|both` | enum | `both` | FR-011 |
| `--full` | bool | off (anteprima troncata) | FR-010/013 |
| `--json` | bool | off (output umano) | FR-013 |
| `--corpus <nome>` | str | da `Settings` | FR-009 |

Validazioni d'input (errore d'uso → exit non-zero):
- `query` vuota o solo spazi → errore leggibile (edge case spec).
- `--type` fuori da `{code,doc,both}` → argparse `choices` → errore d'uso.
- `path` inesistente / non directory → `IngestionError` dal core o check pre-volo (FR-006).

---

## 4. Relazioni e flusso (testuale)

```
Args (argparse)
  │  parse + validazione d'uso (FR-003)
  ▼
logging_setup (D4)  ── -v / --log-json / --log-config → configura logger "sertor_core"
  │
  ▼
Settings.load()  ── --corpus → replace(corpus=...)
  │
  ▼
Settings.validate_backend()  ── lista non vuota → ConfigError (FR-015, blocco pre-servizio)
  │
  ├─ index:  build_indexer(settings).index(path, rebuild=True) → IndexReport → vista
  │
  └─ search: build_baseline_engine(settings).ensure_index()  (strict, FR-012)
             ├─ both → build_facade(settings).search_combined / baseline.query
             ├─ code → build_facade(settings).search_code
             └─ doc  → build_facade(settings).search_docs
                              → list[RetrievalResult] → vista (troncata / --full / --json)
  │
  ▼
SertorError → "errore: ..." su stderr, exit 1 (D8)
```

Nessuno stato persistente nuovo: la persistenza (vector store) è interamente del core; la CLI
orchestra e formatta.
