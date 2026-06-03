# Requisiti — CLI: esecuzione delle capacità del core
<!-- Deriva da: FEAT-CLI-001 (backbone entry-point) + FEAT-CLI-004 (esecuzione RAG) + fetta minima di FEAT-CLI-003 (config provider) -->

## 1. Contesto e problema (perché)

Le capacità del core (`sertor-core`, FEAT-001/002/003, ora in `master`) sono usabili **solo come
libreria Python**: per indicizzare un repository o interrogarlo bisogna scrivere codice
(`build_indexer().index(...)`, `build_facade().search_code(...)`, `index_wiki(...)`). Manca un
**punto d'ingresso eseguibile** che permetta di lanciare queste operazioni da riga di comando.

Inoltre il core emette **log strutturati** (Principio IX) ma di default **non sono visibili**: usa la
`logging` stdlib senza configurare handler/livello (scelta voluta, per non imporre un framework al
chiamante). Serve un consumatore che **renda osservabili** i log e permetta di collegarvi appender
esterni (file, syslog, Splunk/ELK).

Questa feature copre il **primo taglio "run-centrico" della CLL**: i comandi che *eseguono* il core
su un repository, più la gestione dell'osservabilità a runtime. È il prerequisito per il *dogfooding
di produzione* (indicizzare il repo Sertor stesso con il motore nuovo).

*Ancora al core (in master):* `src/sertor_core/composition.py` (`build_indexer`, `build_facade`,
`build_baseline_engine`, `build_llm`); `src/sertor_core/wiki/indexing.py` (`index_wiki`);
`src/sertor_core/observability/logging.py` (logger nominato `sertor_core`, `log_event`, `redact`).

---

## 2. Obiettivi e criteri di successo

| ID | Criterio (misurabile, tech-agnostico) | Collegamento epica |
|----|----------------------------------------|--------------------|
| LSC-1 | Da riga di comando si indicizza un repository qualunque e si ottiene un report (n. chunk + dimensione embedding), senza scrivere codice. | CS-1, FEAT-CLI-004 |
| LSC-2 | Da riga di comando si interroga l'indice (codice/doc/combinata) e si ottengono i top-k risultati con metadati. | CS-1, FEAT-CLI-004 |
| LSC-3 | Da riga di comando si indicizza un wiki nel RAG come corpus documentale. | CS-1, FEAT-CLI-004 + FEAT-003 |
| LSC-4 | Nessun comando avvia operazioni RAG senza invocazione esplicita (install ≠ run). | CS-2 |
| LSC-5 | Senza un provider LLM/embeddings configurato, le operazioni RAG sono bloccate con errore esplicito. | CS-5 |
| LSC-6 | Le operazioni sono non distruttive sul repo target e funzionano su ≥2 repository diversi senza modifiche. | CS-4 |
| LSC-7 | I log strutturati sono resi visibili a richiesta e collegabili ad appender esterni (file/syslog/Splunk) senza modificare il codice. | Principio IX |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Owner/maintainer** | Lancia index/search/wiki dal terminale; configura la verbosità e gli appender di log. |
| **Agente LLM (es. Claude Code)** | Consumatore: può invocare la CLI come strumento (output scriptabile, exit code). |
| **Sistema di log esterno (Splunk/ELK/syslog)** | Destinatario dei log strutturati via appender configurato dall'utente. |
| **`sertor-core` (dipendenza a monte)** | Fornisce le capacità che la CLI esegue; la CLI non le duplica. |
| **Repository/Wiki target** | Oggetto su cui la CLI opera (path arbitrario). |

---

## 4. Ambito

### In ambito
- **Entry-point ed esecuzione** della CLI con sottocomandi: `index`, `search`, `wiki index`.
- **`index <path>`**: costruisce l'indice vettoriale del repo (riusa `build_indexer`), full rebuild,
  riportando conteggi e dimensione embedding.
- **`search <query>`**: interroga (codice/doc/combinata, oppure via motore `baseline`) con `k` e
  filtro tipo; output con path, tipo, id chunk, punteggio, anteprima.
- **`wiki index <wiki>`**: indicizza il wiki nel RAG (riusa `index_wiki` di FEAT-003).
- **Lettura della configurazione** (provider/backend/parametri) dal core (`Settings`, env/`.env`),
  senza modifiche al codice.
- **Osservabilità a runtime**: verbosità (`-v/--verbose`), output JSON (`--log-json`), caricamento di
  una configurazione di logging esterna (`--log-config`) per collegare appender (file/syslog/Splunk).
- **Completamento dell'osservabilità del core**: logging strutturato degli **errori** sui boundary
  (embeddings/store/index) e **documentazione dei campi** di log.
- **Repo-agnosticità, non distruttività, install ≠ run, exit code** per la scriptabilità.

### Fuori ambito
- **Pacchetto installabile e distribuzione** (`uv pip install sertor`, comando globale `sertor`,
  `git+url`, PyPI): rinviato (FEAT-CLI-001 parte packaging, FEAT-CLI-006). Nell'MVP la CLI si esegue
  nell'ambiente di sviluppo (es. come modulo eseguibile).
- **Installazione selettiva delle capacità su ALTRI repo** (FEAT-CLI-002).
- **Wizard di configurazione interattivo** e gestione scrittura segreti (FEAT-CLI-003 completa): qui
  si **legge** soltanto la configurazione esistente.
- **Setup della governance** (skill/agenti) su un repo (FEAT-CLI-005).
- **Le capacità RAG/wiki in sé**: sono `sertor-core`; la CLI le **orchestra**, non le definisce.
- **GUI/web.**

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Entry-point e struttura comandi

**REQ-001 (Ubiquitous)** *The CLI shall expose a single command-line entry-point that dispatches to
the subcommands `index`, `search`, and `wiki index`.*

**REQ-002 (Ubiquitous)** *The CLI shall provide usage/help text for the entry-point and for each
subcommand, describing arguments and options.*

**REQ-003 (Unwanted behaviour)** *If an unknown subcommand or a required argument is missing, then the
CLI shall print a readable error and exit with a non-zero status, without performing any partial
operation.*

**REQ-004 (Ubiquitous)** *The CLI shall return exit code 0 on success and a non-zero exit code on any
error, to support scripting and automation.*

### Gruppo B — Comando `index`

**REQ-010 (Event-driven)** *When the user runs `index <path>`, the CLI shall build a vector index of
the repository rooted at `<path>` by invoking the shared core, and shall report the number of chunks
indexed and the embedding dimension.*

**REQ-011 (Unwanted behaviour)** *If `<path>` does not exist or is not a readable directory, then the
CLI shall print a readable error and exit non-zero without creating any index.*

**REQ-012 (Unwanted behaviour)** *If the configured embeddings provider/vector store is unavailable
during indexing, then the CLI shall abort, surface the core error in readable form, and not leave a
partial or corrupted index.*

**REQ-013 (Ubiquitous)** *The CLI `index` command shall be non-destructive on the target repository:
it shall not modify or overwrite the user's source files (it only writes to the index store).*

### Gruppo C — Comando `search`

**REQ-020 (Event-driven)** *When the user runs `search <query>`, the CLI shall return the top-k most
relevant results, each including at minimum: file path, document type (code/doc), chunk identifier,
relevance score, and a text preview.*

**REQ-021 (Optional feature)** *Where the user specifies a result count (`-k`) and/or a type filter
(code / doc / combined), the CLI shall honour them; otherwise it shall use the configured defaults.*

**REQ-022 (Unwanted behaviour)** *If the index does not exist when a search is requested, then the CLI
shall print a readable error indicating that the index must be built first, and exit non-zero (no
silent empty result).*

### Gruppo D — Comando `wiki index`

**REQ-030 (Event-driven)** *When the user runs `wiki index <wiki-path>`, the CLI shall ingest the
Markdown pages under `<wiki-path>` into the configured RAG corpus by invoking the core, and shall
report the number of wiki documents indexed.*

**REQ-031 (Unwanted behaviour)** *If the wiki path is empty or contains no Markdown files, then the
CLI shall print a warning and complete without modifying the existing index.*

### Gruppo E — Configurazione (lettura)

**REQ-040 (Ubiquitous)** *The CLI shall read all operational choices (embeddings/LLM provider,
backend, paths, chunking parameters, default k, exclusion patterns) from the core's centralized
configuration (environment variables and/or a configuration file), without requiring code changes.*

**REQ-041 (Unwanted behaviour)** *If no embeddings/LLM provider is configured, then the CLI shall block
any RAG operation (index/search/wiki) with an explicit, readable error.*

**REQ-042 (Ubiquitous)** *The CLI shall not write secret values (API keys, credentials) to any
version-controlled file.*

### Gruppo F — Osservabilità a runtime

**REQ-050 (Optional feature)** *Where the user passes a verbosity option (`-v/--verbose`), the CLI
shall enable emission of the core's structured INFO-level log events.*

**REQ-051 (Optional feature)** *Where the user requests JSON logging (`--log-json`), the CLI shall
emit log events as structured JSON records (one per event) suitable for ingestion by external log
systems.*

**REQ-052 (Optional feature)** *Where the user provides an external logging configuration
(`--log-config <file>`), the CLI shall load it so that arbitrary log handlers/appenders (e.g. file,
syslog, Splunk) can be attached without modifying the code.*

**REQ-053 (Unwanted behaviour)** *If an operation fails at a core boundary (embeddings, vector store,
indexing), then the system shall emit a structured log event describing the failure (operation,
provider/backend, reason) before the error is propagated.*
> Completa il Principio IX: oggi i fallimenti sono sollevati come eccezioni esplicite ma non emessi
> come evento di log. Tocca il core (`sertor-core`) in modo additivo.

**REQ-054 (Ubiquitous)** *The system shall document the set of structured log fields emitted per
operation, so that external log configurations can index them.*

**REQ-055 (Ubiquitous)** *The CLI and core shall never include secret values in emitted log records
(redaction applied before emission).*

### Gruppo G — Trasversali (install ≠ run, agnosticità)

**REQ-060 (Unwanted behaviour)** *If the CLI is installed, added, or merely imported, then it shall
not automatically start any indexing or RAG operation; every operation requires an explicit command.*

**REQ-061 (Ubiquitous)** *The CLI shall operate on any target repository or wiki provided as a path,
without hardcoded assumptions about its internal structure, language distribution, or size.*

---

## 6. Requisiti non funzionali

| ID | Categoria | Requisito |
|----|-----------|-----------|
| NFR-01 | **Dipendenza verso l'interno** | La CLI è un layer sottile che dipende da `sertor-core` (composition root + facce pubbliche); non duplica né reimplementa le capacità del core (Principio I). |
| NFR-02 | **Testabilità** | Ogni comando è testabile in automatico con provider/store **mock**, senza cloud né rete; gli esiti (output, exit code, log) sono verificabili. |
| NFR-03 | **Portabilità** | La CLI funziona su Linux e Windows senza modifiche. |
| NFR-04 | **Leggibilità degli errori** | I messaggi d'errore sono comprensibili e azionabili; gli errori di dominio del core sono presentati in forma leggibile, non come stack trace grezzo (a meno di verbosità elevata). |
| NFR-05 | **Osservabilità** | Tutte le operazioni emettono log strutturati con i campi richiesti; il livello/formato/appender è governato da opzioni o configurazione, non dal codice (Principio IX). |
| NFR-06 | **Configurabilità centralizzata** | La CLI non introduce default propri in conflitto col core: legge dalla configurazione centralizzata (Principio VIII). |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli
- **V-1**: La CLI non può funzionare senza `sertor-core` (FEAT-001/002/003); ne è un consumatore.
- **V-2**: Nessun segreto su file versionati (REQ-E5 epica).
- **V-3**: `install ≠ run` (REQ-E2 epica): nessuna operazione automatica all'installazione/import.
- **V-4**: Python ≥ 3.11 (vincolo d'epica).

### Assunzioni
- **A-1**: Nell'MVP la CLI si esegue nell'ambiente di sviluppo (modulo eseguibile); il pacchetto
  installabile e il comando globale `sertor` sono fuori ambito (FEAT-CLI-001 packaging / FEAT-CLI-006).
- **A-2**: La configurazione (provider/backend) è **definita** altrove (env/`.env`) e dal core; la CLI
  la **legge**, non la scrive (il wizard interattivo è FEAT-CLI-003, fuori ambito).
- **A-3**: Il provider reale (Ollama o Azure) è un prerequisito d'**esecuzione**, non di costruzione:
  i test usano mock; il dogfooding reale richiede un provider configurato.

### Dipendenze
- **D-1**: `sertor-core` in `master` (build_indexer/build_facade/build_baseline_engine/build_llm/index_wiki).
- **D-2**: `sertor-core/observability` per il logging strutturato (REQ-053/054 toccano il core in modo additivo).

---

## 8. Rischi

| ID | Rischio | Prob. | Impatto | Mitigazione |
|----|---------|-------|---------|-------------|
| R-C1 | **Logica del core nella CLI**: la CLI accumula logica che dovrebbe stare nel core (viola Principio I). | Media | Alto | Mantenere la CLI sottile (parse args → chiama composition → formatta output); review contro NFR-01. |
| R-C2 | **Logging invisibile/disallineato**: i log restano invisibili o senza i campi attesi dagli appender esterni. | Media | Medio | REQ-050/051/052 + REQ-054 (schema documentato); test che verificano l'emissione strutturata. |
| R-C3 | **Avvio non voluto** (viola install ≠ run). | Bassa | Alto | REQ-060: nessun side-effect su import; test dedicato. |
| R-C4 | **Errori del core opachi** all'utente (stack trace grezzo). | Media | Medio | REQ-003/NFR-04: mappare le eccezioni di dominio in messaggi leggibili + exit code. |
| R-C5 | **Provenienza dei corpora** (prototipo vs produzione) confusa in un'unica collezione durante il dogfooding. | Media | Medio | Domanda aperta DA-C2: namespacing per corpus / collezioni distinte; decisione in design. |

---

## 9. Prioritizzazione (MoSCoW)

| Priorità | Requisiti | Motivazione |
|----------|-----------|-------------|
| **Must** | REQ-001..004, REQ-010..013, REQ-020..022, REQ-040, REQ-041, REQ-060, REQ-061 | Entry-point + index + search + config-read + install≠run + agnosticità: il ciclo minimo eseguibile. |
| **Should** | REQ-030, REQ-031 (wiki index), REQ-050, REQ-051, REQ-052 (osservabilità a runtime), REQ-053 (log errori core) | Completano valore e osservabilità; il dogfooding del wiki e gli appender esterni. |
| **Could** | REQ-054 (doc schema campi), REQ-042/055 (esplicitati; in gran parte ereditati dal core) | Rifiniture di osservabilità/sicurezza. |
| **Won't (questa feature)** | packaging/distribuzione, install selettivo su altri repo, wizard config, governance | Rinviati ad altre feature dell'epica. |

---

## 10. Domande aperte

- **DA-C1 — Forma dell'entry-point nell'MVP.** *Proposta:* modulo eseguibile (`python -m sertor_cli`)
  senza packaging; il comando globale `sertor` arriva con la feature di distribuzione. Da confermare in design.
- **DA-C2 — Provenienza dei corpora.** Per il dogfooding (prototipo *vs* produzione): collezioni
  **namespaced distinte** o un'unica collezione con metadato `origin`? *Direzione:* namespacing per
  corpus (già supportato dal core via `collection_name`). Da fissare in design.
- **DA-C3 — Formato di `--log-config`.** dictConfig (YAML/JSON) vs fileConfig (INI). Da fissare in design.
- **DA-C4 — Default di `search`.** Modalità di default (combinata?) e `k` di default: ereditati dal
  `Settings` del core o esposti come opzioni con default propri? *Direzione:* ereditare dal core
  (Principio VIII). Da confermare in design.
- **DA-C5 — Formato di output di `search`.** Testo leggibile vs JSON (per consumo da agente). *Direzione:*
  testo di default + `--json` opzionale, coerente con `--log-json`. Da confermare in design.
