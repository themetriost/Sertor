# Phase 1 — Data Model: CLI esecuzione

La CLI non introduce entità di dominio nuove: orchestra il core e formatta l'output. Le "entità" qui
sono strutture di interfaccia (argomenti, opzioni, vista dei risultati, configurazione del logging).

---

## Comando (invocazione)

`sertor <subcommand> [args] [opzioni]` → esegue e ritorna un **exit code** (0 ok / non-zero errore).

| Sottocomando | Argomenti | Opzioni principali |
|--------------|-----------|--------------------|
| `index` | `<path>` | `--corpus <nome>` (namespace) |
| `search` | `<query>` | `-k <int>`, `--type code\|doc\|both`, `--json`, `--full`, `--corpus` |
| `wiki index` | `<wiki-path>` | `--corpus <nome>` |
| *(globali)* | — | `-v/--verbose`, `--log-json`, `--log-config <file>` |

---

## Vista risultato di ricerca (output)

Mappatura del `RetrievalResult` del core per l'output CLI:

| Campo | Origine | Note |
|-------|---------|------|
| `path` | `RetrievalResult.path` | — |
| `doc_type` | `RetrievalResult.doc_type` | code/doc |
| `chunk_id` | `RetrievalResult.chunk_id` | — |
| `score` | `RetrievalResult.score` | arrotondato in testo |
| `preview` | `RetrievalResult.text` | **troncato** a lunghezza limite; intero se `--full` |

- **Testo**: una riga d'intestazione per hit + anteprima indentata.
- **JSON** (`--json`): array di oggetti con i campi sopra.

---

## Report d'indicizzazione (output)

Mappatura dell'`IndexReport` del core: `collection`, `documents`, `chunks`, `embedding_dim`,
`elapsed_ms`. Stampato come riga di riepilogo (o JSON se `--json`).

---

## Configurazione del logging (input opzionale)

| Sorgente | Effetto |
|----------|---------|
| `-v/--verbose` | livello INFO su handler base |
| `--log-json` | formatter JSON (un record per evento) |
| `--log-config <file>` | `dictConfig` da YAML/JSON: handler/appender arbitrari (file, syslog, Splunk) |

Precedenza: `--log-config` prevale; altrimenti `-v`/`--log-json`.

---

## Estensione del core (additiva)

| Elemento | Modifica | Requisito |
|----------|----------|-----------|
| `observability/logging.py` | `+ log_error(operation, exc, **fields)` (evento di log strutturato per un errore) | REQ-053 |
| boundary core (adapter embeddings/store, indexing) | chiamano `log_error(...)` **prima** di rilanciare | REQ-053 |
| README/doc | tabella dei **campi di log per operazione** | REQ-054 |

---

## Mapping eccezioni → exit code / messaggio (REQ-003/004)

| Eccezione di dominio | Messaggio CLI | Exit |
|----------------------|---------------|------|
| `IndexNotFoundError` | "indice inesistente: esegui prima `sertor index`" | ≠0 |
| `EmbeddingError` | "provider di embeddings non disponibile: <reason>" | ≠0 |
| `VectorStoreError` | "vector store non disponibile: <reason>" | ≠0 |
| `IngestionError` | "path non accessibile: <path>" | ≠0 |
| `LLMNotConfiguredError` | "LLM non configurato (richiesto per la distillazione)" | ≠0 |
| `ConfigError` | "configurazione mancante/incoerente: <key>" | ≠0 |
| (successo) | output del comando | 0 |
