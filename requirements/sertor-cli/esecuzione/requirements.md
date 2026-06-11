# Requisiti — CLI: esecuzione delle capacità del core
<!-- Deriva da: FEAT-CLI-001 (backbone entry-point) + FEAT-CLI-004 (esecuzione RAG) + fetta minima di FEAT-CLI-003 (config provider) -->
<!-- STATO: CONSEGNATA — implementata come `sertor-rag` (specs/011-cli-esecuzione-rag, PR #21, mergiata su master il 2026-06-11) -->
<!-- Revisione 2026-06-11: ridiscussione requisito-per-requisito post FEAT-003/FEAT-MCP/feature 010/D-21.
     Entry-point spostato sul core (`sertor-rag`, DA-8 epica); gruppo D (wiki index) rimosso; REQ-041 precisato. -->

> **Revisione 2026-06-11 (DA-8 epica).** Il comando `sertor` è riservato all'**installer**
> (`sertor install <capacità>`); l'esecuzione vive nei **console-script del core**: il nuovo
> **`sertor-rag`** (questa feature: `index`/`search`) accanto a `sertor-wiki-tools` (già su master).
> REQ-030/031 (`wiki index`) sono stati rimossi: superati da `sertor-wiki-tools index` e dal modello
> a corpus unico (D-21 epica: il wiki dell'ospite è documentazione del corpus primario, lo indicizza
> il normale `sertor-rag index`).

## 1. Contesto e problema (perché)

Le capacità RAG del core (`sertor-core`, ora in `master`) sono usabili **solo come libreria Python o
via server MCP**: per indicizzare un repository o interrogarlo dal terminale bisogna scrivere codice
(`build_indexer().index(...)`, `build_facade().search_code(...)`). Manca un **punto d'ingresso
eseguibile** che permetta di lanciare queste operazioni da riga di comando. Il precedente esiste già
nel pacchetto: `sertor-wiki-tools` (CLI sottile del nucleo wiki, `wiki_tools/__main__.py`) ha rodato
il pattern parse → chiama funzioni del core → output umano/JSON + exit code.

Inoltre il core emette **log strutturati** (Principio IX) ma di default **non sono visibili**: usa la
`logging` stdlib senza configurare handler/livello (scelta voluta, per non imporre un framework al
chiamante). Serve un consumatore che **renda osservabili** i log e permetta di collegarvi appender
esterni (file, syslog, Splunk/ELK).

Questa feature copre il **primo taglio "run-centrico"**: i comandi che *eseguono* il core su un
repository, più la gestione dell'osservabilità a runtime. È il prerequisito per il *dogfooding di
produzione via CLI* (indicizzare e interrogare il repo Sertor stesso dal terminale).

*Ancora al core (in master):* `src/sertor_core/composition.py` (`build_indexer`, `build_facade`,
`build_baseline_engine`); `src/sertor_core/config/settings.py` (`Settings.load`);
`src/sertor_core/observability/logging.py` (logger nominato `sertor_core`, `log_event`, `redact`);
`src/sertor_core/wiki_tools/__main__.py` (pattern CLI di riferimento, console-script in
`pyproject.toml [project.scripts]`).

---

## 2. Obiettivi e criteri di successo

| ID | Criterio (misurabile, tech-agnostico) | Collegamento epica |
|----|----------------------------------------|--------------------|
| LSC-1 | Da riga di comando (`sertor-rag index`) si indicizza un repository qualunque e si ottiene un report (n. chunk + dimensione embedding), senza scrivere codice. | CS-1, FEAT-CLI-004 |
| LSC-2 | Da riga di comando (`sertor-rag search`) si interroga l'indice (codice/doc/combinata) e si ottengono i top-k risultati con metadati. | CS-1, FEAT-CLI-004 |
| ~~LSC-3~~ | *Rimosso (2026-06-11):* l'indicizzazione del wiki in corpus dedicato è già coperta da `sertor-wiki-tools index`; nel modello a corpus unico (D-21) il wiki dell'ospite è indicizzato da `sertor-rag index` come documentazione. | — |
| LSC-4 | Nessun comando avvia operazioni RAG senza invocazione esplicita (install ≠ run). | CS-2 |
| LSC-5 | Senza un provider LLM/embeddings configurato, le operazioni RAG sono bloccate con errore esplicito. | CS-5 |
| LSC-6 | Le operazioni sono non distruttive sul repo target e funzionano su ≥2 repository diversi senza modifiche. | CS-4 |
| LSC-7 | I log strutturati sono resi visibili a richiesta e collegabili ad appender esterni (file/syslog/Splunk) senza modificare il codice. | Principio IX |

---

## 3. Stakeholder e attori

| Attore | Ruolo |
|--------|-------|
| **Owner/maintainer** | Lancia index/search dal terminale; configura la verbosità e gli appender di log. |
| **Agente LLM (es. Claude Code)** | Consumatore: può invocare la CLI come strumento (output scriptabile, exit code). |
| **Sistema di log esterno (Splunk/ELK/syslog)** | Destinatario dei log strutturati via appender configurato dall'utente. |
| **`sertor-core` (dipendenza a monte)** | Fornisce le capacità che la CLI esegue; la CLI non le duplica. |
| **Repository/Wiki target** | Oggetto su cui la CLI opera (path arbitrario). |

---

## 4. Ambito

### In ambito
- **Entry-point ed esecuzione** della CLI di esecuzione RAG **`sertor-rag`** (console-script del
  pacchetto `sertor-core`) con sottocomandi: `index`, `search`.
- **`index <path>`**: costruisce l'indice vettoriale del repo (riusa `build_indexer`), full rebuild,
  riportando conteggi e dimensione embedding.
- **`search <query>`**: interroga (codice/doc/combinata, oppure via motore `baseline`) con `k` e
  filtro tipo; output con path, tipo, id chunk, punteggio, anteprima.
- **Lettura della configurazione** (provider/backend/parametri) dal core (`Settings`, env/`.env`),
  senza modifiche al codice.
- **Osservabilità a runtime**: verbosità (`-v/--verbose`), output JSON (`--log-json`), caricamento di
  una configurazione di logging esterna (`--log-config`) per collegare appender (file/syslog/Splunk).
- **Completamento dell'osservabilità del core**: logging strutturato degli **errori** sui boundary
  (embeddings/store/index) e **documentazione dei campi** di log.
- **Repo-agnosticità, non distruttività, install ≠ run, exit code** per la scriptabilità.

### Fuori ambito
- **Il comando installer `sertor`** (`sertor install <capacità>`, DA-8): è FEAT-CLI-002/005, con
  elicitazione propria. Questa feature non lo tocca.
- **Indicizzazione del wiki in corpus dedicato**: già consegnata (`sertor-wiki-tools index`,
  FEAT-003-D); nel modello a corpus unico (D-21) il wiki dell'ospite passa da `sertor-rag index`.
- **Distribuzione del pacchetto** (`git+url`, PyPI, hardening): rinviata (FEAT-CLI-006). Nell'MVP il
  console-script `sertor-rag` è disponibile con l'installazione (anche editable) di `sertor-core`.
- **Installazione selettiva delle capacità su ALTRI repo** (FEAT-CLI-002).
- **Wizard di configurazione interattivo** e gestione scrittura segreti (FEAT-CLI-003 completa): qui
  si **legge** soltanto la configurazione esistente.
- **Setup della governance** (skill/agenti) su un repo (FEAT-CLI-005).
- **Le capacità RAG/wiki in sé**: sono `sertor-core`; la CLI le **orchestra**, non le definisce.
- **GUI/web.**

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Entry-point e struttura comandi

**REQ-001 (Ubiquitous)** *The CLI shall expose a single command-line entry-point named `sertor-rag`
(installed as a console-script of the `sertor-core` package) that dispatches to the subcommands
`index` and `search`.*
> Rev. 2026-06-11 (DA-8 epica, supera DA-C1): il comando `sertor` è riservato all'**installer**
> (`sertor install <capacità>`); l'esecuzione vive nei console-script del core — `sertor-rag`
> (RAG, questa feature) accanto a `sertor-wiki-tools` (wiki, già su master). La **distribuzione
> pubblica** (PyPI/git+url) resta fuori ambito.

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

**REQ-014 (Optional feature)** *Where the user selects a corpus namespace (via a `--corpus` option or
the centralized configuration), the CLI shall index into, and query from, the corresponding
namespaced collection, so that distinct repositories/corpora (e.g. prototype vs production) remain
isolated and individually addressable.*
> DA-C2 risolta: provenienza tramite **collezioni namespaced distinte** (già supportate dal core via
> `collection_name`); nessuna mescolanza dei corpora.

### Gruppo C — Comando `search`

**REQ-020 (Event-driven)** *When the user runs `search <query>`, the CLI shall return the top-k most
relevant results, each including at minimum: file path, document type (code/doc), chunk identifier,
relevance score, and a **truncated** text preview (bounded length), not the full chunk text.*
> DA-C5 risolta (economia di token): di default l'output usa **anteprime troncate**; un'opzione
> `--full` restituisce il testo completo del chunk on-demand.

**REQ-021 (Optional feature)** *Where the user specifies a result count (`-k`) and/or a type filter
(`--type code|doc|both`), the CLI shall honour them; otherwise it shall use the defaults from the
core configuration (`default_k` for `k`) and `both` as the default search mode.*
> DA-C4 risolta: default **ereditati dal core** (Principio VIII); nessun default duplicato nella CLI.

**REQ-022 (Unwanted behaviour)** *If the index does not exist when a search is requested, then the CLI
shall print a readable error indicating that the index must be built first, and exit non-zero (no
silent empty result).*
> Nota di design (2026-06-11): nel core la facade è *tollerante* (indice assente → `[]` + warning)
> mentre il motore baseline è *strict* (`IndexNotFoundError`) — policy voluta, da non uniformare.
> La CLI deve imboccare la via strict (motore o verifica esplicita); la scelta è di design.

**REQ-023 (Optional feature)** *Where the user requests JSON output (`--json`), the CLI shall print the
search results as a structured JSON array suitable for programmatic/agent consumption; otherwise it
shall print human-readable text. In both formats the preview is truncated unless `--full` is given.*
> DA-C5 risolta: **testo di default + `--json`**; anteprime troncate in entrambi i formati per
> contenere il consumo di token quando la CLI è usata da un agente.

### Gruppo D — ~~Comando `wiki index`~~ (rimosso, 2026-06-11)

> **REQ-030 e REQ-031 rimossi.** Superati dai fatti: (1) l'indicizzazione del wiki in **corpus
> dedicato** è già consegnata da `sertor-wiki-tools index` (FEAT-003-D), per gli ospiti con corpora
> davvero disgiunti; (2) nel **modello a corpus unico** (D-21 epica) il wiki dell'ospite è
> documentazione del corpus primario e viene indicizzato dal normale `sertor-rag index`
> (`doc_type=doc`). Il **bootstrap** del sistema-wiki sull'ospite (skill, rituale, config, struttura)
> appartiene alla feature **installer** (`sertor install wiki`, FEAT-CLI-002 — vedi epica, DA-8).

### Gruppo E — Configurazione (lettura)

**REQ-040 (Ubiquitous)** *The CLI shall read all operational choices (embeddings/LLM provider,
backend, paths, chunking parameters, default k, exclusion patterns) from the core's centralized
configuration (environment variables and/or a configuration file), without requiring code changes.*

**REQ-041 (Unwanted behaviour)** *If the configuration parameters required by the selected backend
are missing or incomplete (e.g. `azure` backend without endpoint/API key/deployment), then the CLI
shall block any RAG operation (index/search) with an explicit, readable error, before contacting any
service.*
> Rev. 2026-06-11: precisato il significato di "provider non configurato" — è una **validazione
> statica** dei parametri del backend scelto (il default `local`/Ollama è sempre formalmente
> completo). La **raggiungibilità** del provider (es. Ollama spento) resta un errore a runtime,
> coperto da REQ-012.

**REQ-042 (Ubiquitous)** *The CLI shall not write secret values (API keys, credentials) to any
version-controlled file.*

### Gruppo F — Osservabilità a runtime

**REQ-050 (Optional feature)** *Where the user passes a verbosity option (`-v/--verbose`), the CLI
shall enable emission of the core's structured INFO-level log events.*

**REQ-051 (Optional feature)** *Where the user requests JSON logging (`--log-json`), the CLI shall
emit log events as structured JSON records (one per event) suitable for ingestion by external log
systems.*

**REQ-052 (Optional feature)** *Where the user provides an external logging configuration
(`--log-config <file>`) in `dictConfig` form (YAML or JSON), the CLI shall load it so that arbitrary
log handlers/appenders (e.g. file, syslog, Splunk) can be attached without modifying the code.*
> DA-C3 risolta: formato **`dictConfig` (YAML/JSON)**.

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
- **A-1** *(rev. 2026-06-11)*: La CLI espone il comando **`sertor-rag`** come **console-script del
  pacchetto `sertor-core` esistente** (una riga in `pyproject.toml [project.scripts]`, accanto a
  `sertor-wiki-tools`); disponibile con l'installazione anche editable del pacchetto. La
  **distribuzione pubblica** (PyPI/git+url) e l'hardening del packaging restano fuori ambito
  (FEAT-CLI-006); l'eventuale pacchetto autonomo `sertor` riguarda l'**installer** (DA-8).
- **A-2**: La configurazione (provider/backend) è **definita** altrove (env/`.env`) e dal core; la CLI
  la **legge**, non la scrive (il wizard interattivo è FEAT-CLI-003, fuori ambito).
- **A-3**: Il provider reale (Ollama o Azure) è un prerequisito d'**esecuzione**, non di costruzione:
  i test usano mock; il dogfooding reale richiede un provider configurato.

### Dipendenze
- **D-1**: `sertor-core` in `master` (`build_indexer`/`build_facade`/`build_baseline_engine` in
  `composition.py`; `Settings.load` in `config/settings.py`).
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
| **Should** | REQ-050, REQ-051, REQ-052 (osservabilità a runtime), REQ-053 (log errori core) | Completano l'osservabilità: visibilità dei log e appender esterni. *(REQ-030/031 rimossi il 2026-06-11, vedi gruppo D.)* |
| **Could** | REQ-054 (doc schema campi), REQ-042/055 (esplicitati; in gran parte ereditati dal core) | Rifiniture di osservabilità/sicurezza. |
| **Won't (questa feature)** | packaging/distribuzione, install selettivo su altri repo, wizard config, governance | Rinviati ad altre feature dell'epica. |

---

## 10. Domande aperte (risolte)

Chiuse in elicitazione (2026-06-03) e codificate nei requisiti sopra.

- **DA-C1 — Forma dell'entry-point.** *Risolta, poi **superata da DA-8** (2026-06-11):* la prima
  risoluzione assegnava `index`/`search` al comando globale `sertor`; con DA-8 (epica §9) `sertor` è
  riservato all'**installer** (`sertor install <capacità>`) e l'esecuzione vive nel console-script
  del core **`sertor-rag`** (REQ-001 riscritto).
- **DA-C2 — Provenienza dei corpora.** *Risolta:* **collezioni namespaced distinte** (REQ-014); il
  corpus si seleziona via `--corpus`/configurazione; prototipo e produzione restano isolati.
- **DA-C3 — Formato di `--log-config`.** *Risolta:* **`dictConfig` (YAML/JSON)** (REQ-052).
- **DA-C4 — Default di `search`.** *Risolta:* **ereditati dal core** — `k` da `default_k`, modalità
  di default `both` (REQ-021).
- **DA-C5 — Output di `search`.** *Risolta:* **testo di default + `--json`**, con **anteprime
  troncate** in entrambi i formati e `--full` per il testo completo (REQ-020/023).
