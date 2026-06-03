# Feature Specification: CLI — esecuzione delle capacità del core

**Feature Branch**: `spec/004-cli-esecuzione`

**Created**: 2026-06-03

**Status**: Draft

**Input**: Decomposizione di `requirements/sertor-cli/esecuzione/requirements.md` (deriva da
FEAT-CLI-001 backbone + FEAT-CLI-004 esecuzione + fetta di FEAT-CLI-003 lettura config). Dipende da
`sertor-core` (FEAT-001/002/003, in `master`). Vincoli architetturali:
`.specify/memory/constitution.md` (Principi I, IV, VIII, IX). Domande aperte DA-C1..C5 già risolte.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Indicizzare una codebase da riga di comando (Priority: P1) 🎯 MVP

Come maintainer (o agente), do un path a `sertor index` e ottengo un indice vettoriale del repo, con
un report (chunk indicizzati + dimensione embedding), senza scrivere codice. Il comando rispetta
*install ≠ run* (nulla parte da solo) ed è non distruttivo sui file del repo.

**Why this priority**: è l'entry point che rende usabile il core senza scrivere Python; senza
`index` non c'è nulla da interrogare. È il prerequisito del dogfooding di produzione.

**Independent Test**: eseguire `sertor index <repo>` su una codebase di prova con un provider
configurato (o mock) e verificare il report e l'esistenza dell'indice; verificare path inesistente →
errore + exit non-zero; provider assente → operazione bloccata.

**Acceptance Scenarios**:

1. **Given** un repo e un provider configurato, **When** si esegue `sertor index <path>`, **Then** il
   sistema costruisce l'indice (riusando il core) e riporta n. chunk e dimensione embedding.
2. **Given** un `--corpus <nome>`, **When** si indicizza, **Then** i chunk finiscono in una collezione
   namespaced dedicata (corpora distinti restano isolati).
3. **Given** un path inesistente/illeggibile, **When** si esegue `index`, **Then** errore leggibile +
   exit non-zero, nessun indice creato.
4. **Given** nessun provider configurato, **When** si esegue `index`, **Then** l'operazione è bloccata
   con errore esplicito (install ≠ run rispettato: nulla parte da solo).

### User Story 2 - Interrogare l'indice da riga di comando (Priority: P1)

Come maintainer o agente, eseguo `sertor search "<query>"` e ottengo i top-k chunk pertinenti con i
metadati per citare la fonte; posso scegliere tipo (`--type`) e numero (`-k`), e il formato (testo o
`--json`).

**Why this priority**: l'indice è utile solo se interrogabile; `index`+`search` sono il ciclo minimo.

**Independent Test**: con un indice popolato, `sertor search "<q>"` restituisce risultati con
path/tipo/chunk-id/score/anteprima; verificare `-k`, `--type`, `--json`, e indice mancante → errore.

**Acceptance Scenarios**:

1. **Given** un indice popolato, **When** `sertor search "<q>"`, **Then** restituisce fino a `k`
   risultati con path, tipo, chunk id, punteggio e **anteprima troncata**.
2. **Given** `-k`/`--type` omessi, **When** si interroga, **Then** usa i default del core (`default_k`,
   modalità `both`).
3. **Given** `--json`, **When** si interroga, **Then** l'output è un array JSON strutturato; senza, è
   testo leggibile. Con `--full`, l'anteprima è sostituita dal testo completo.
4. **Given** un indice inesistente, **When** si interroga, **Then** errore esplicito ("costruisci
   prima l'indice") + exit non-zero, nessun risultato vuoto silenzioso.

### User Story 3 - Indicizzare il wiki da riga di comando (Priority: P2)

Come maintainer, eseguo `sertor wiki index <wiki>` e le pagine del wiki entrano nel corpus
documentale del RAG (full rebuild), riportando il numero di documenti.

**Why this priority**: completa il dogfooding (wiki interrogabile), ma `index`/`search` bastano all'MVP.

**Independent Test**: con un wiki e un provider, `sertor wiki index <wiki>` riporta i documenti;
radice vuota → warning, indice immutato.

**Acceptance Scenarios**:

1. **Given** un wiki + provider, **When** `sertor wiki index <wiki>`, **Then** ingerisce i `.md` del
   wiki nel corpus e riporta il numero di documenti.
2. **Given** una radice wiki vuota/senza Markdown, **When** si esegue, **Then** warning e nessuna
   modifica all'indice esistente.

### User Story 4 - Osservabilità configurabile a runtime (Priority: P2)

Come operatore, rendo **visibili** i log strutturati e li collego ad appender esterni (file, syslog,
Splunk) senza modificare il codice: `-v/--verbose`, `--log-json`, `--log-config <file>` (dictConfig
YAML/JSON). Anche i fallimenti sui boundary del core sono emessi come eventi di log.

**Why this priority**: l'osservabilità è production-grade (Principio IX), ma le capacità funzionano
anche senza; per questo è P2.

**Independent Test**: eseguire un comando con `-v` e verificare l'emissione di eventi INFO; con
`--log-json` verificare record JSON; con `--log-config` verificare che un handler esterno riceva gli
eventi; forzare un errore di boundary e verificare l'evento di log dell'errore.

**Acceptance Scenarios**:

1. **Given** `-v`, **When** si esegue un comando, **Then** vengono emessi gli eventi INFO strutturati
   del core (operazione, provider/backend, conteggi, tempi).
2. **Given** `--log-json`, **When** si esegue, **Then** ogni evento è un record JSON.
3. **Given** `--log-config <file>` (dictConfig), **When** si esegue, **Then** gli handler/appender
   definiti (es. file/syslog/Splunk) ricevono gli eventi, senza modifiche al codice.
4. **Given** un fallimento su un boundary (embeddings/store/index), **When** avviene, **Then** è
   emesso un evento di log strutturato dell'errore **prima** della propagazione; nessun segreto nei log.

### Edge Cases

- Comando o argomento mancante/sconosciuto → messaggio d'uso leggibile + exit non-zero, nessuna azione parziale.
- `index`/`search`/`wiki` invocati senza provider configurato → bloccati con errore esplicito (CS-5).
- Import/installazione della CLI → nessuna operazione RAG automatica (install ≠ run).
- `k` maggiore dei risultati disponibili → restituisce tutti i disponibili.
- Repo/wiki target con struttura arbitraria → funziona (repo-agnostico), nessuna assunzione hardcoded.

## Requirements *(mandatory)*

### Functional Requirements

Sintesi (dettaglio EARS e ID in `requirements/sertor-cli/esecuzione/requirements.md`):

- **FR-001**: La CLI MUST esporre un entry-point `sertor` (console-script) con i sottocomandi
  `index`, `search`, `wiki index`, con help e exit code (0 ok / non-zero errore). *(REQ-001..004)*
- **FR-002**: `sertor index <path>` MUST costruire l'indice del repo riusando il core e riportare
  n. chunk + dimensione embedding; non distruttivo sui file. *(REQ-010, 011, 013)*
- **FR-003**: La CLI MUST selezionare il corpus namespaced (`--corpus`/config) così che corpora
  distinti restino isolati. *(REQ-014)*
- **FR-004**: `index` MUST annullare senza indice parziale se path inaccessibile o provider/store non
  disponibile, con errore leggibile. *(REQ-011, 012)*
- **FR-005**: `sertor search "<q>"` MUST restituire i top-k risultati con path, tipo, chunk id,
  punteggio e **anteprima troncata**. *(REQ-020)*
- **FR-006**: `search` MUST accettare `-k` e `--type` (code/doc/both); in assenza usa i default del
  core (`default_k`, `both`). *(REQ-021)*
- **FR-007**: `search` MUST offrire output testo (default) e `--json`; `--full` per il testo completo.
  *(REQ-023)*
- **FR-008**: `search` su indice inesistente MUST dare errore esplicito ("costruisci prima l'indice"),
  non un vuoto silenzioso. *(REQ-022)*
- **FR-009**: `sertor wiki index <wiki>` MUST ingerire i `.md` del wiki nel corpus (riuso `index_wiki`)
  e riportare i documenti; radice vuota → warning, indice immutato. *(REQ-030, 031)*
- **FR-010**: La CLI MUST leggere provider/backend/parametri dalla configurazione centralizzata del
  core (env/.env), senza modifiche al codice; senza provider, le operazioni RAG sono bloccate.
  *(REQ-040, 041)*
- **FR-011**: La CLI MUST supportare verbosità (`-v/--verbose`), `--log-json`, e `--log-config <file>`
  (dictConfig YAML/JSON) per collegare appender esterni. *(REQ-050, 051, 052)*
- **FR-012**: Il sistema MUST emettere un evento di log strutturato per i fallimenti sui boundary del
  core (embeddings/store/index) prima di propagare l'errore; nessun segreto nei log. *(REQ-053, 055)*
- **FR-013**: La CLI MUST NOT avviare operazioni RAG su installazione/import (install ≠ run) e MUST
  operare su qualunque repo/wiki target senza assunzioni hardcoded. *(REQ-060, 061)*
- **FR-014**: La CLI MUST essere un layer sottile sul core (composition root + facce pubbliche),
  senza duplicarne le capacità. *(NFR-01, Principio I)*

### Key Entities

- **Comando**: invocazione `sertor <subcommand> [args/opzioni]`; produce output + exit code.
- **Risultato di ricerca (vista CLI)**: path, tipo, chunk id, punteggio, anteprima (troncata o piena).
- **Configurazione di logging**: file dictConfig (YAML/JSON) che definisce handler/appender esterni.
- **Configurazione del core**: `Settings` letto da env/.env (provider, backend, `default_k`, corpus).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Da CLI si indicizza un repo e si ottiene un report (chunk + dim) senza scrivere codice.
- **SC-002**: Da CLI si interroga l'indice (code/doc/both) e si ottengono i top-k con metadati.
- **SC-003**: Da CLI si indicizza un wiki nel corpus documentale.
- **SC-004**: Nessun comando avvia operazioni RAG senza invocazione esplicita (install ≠ run).
- **SC-005**: Senza provider configurato, le operazioni RAG sono bloccate con errore esplicito.
- **SC-006**: Le operazioni sono non distruttive e funzionano su ≥2 repository diversi senza modifiche.
- **SC-007**: I log strutturati sono resi visibili a richiesta e collegabili ad appender esterni
  (file/syslog/Splunk) senza modificare il codice; i fallimenti sono loggati; nessun segreto nei log.

### Tracciabilità requisito → user story

| Requisito (EARS) | User Story | Criterio |
|------------------|-----------|----------|
| REQ-001..004 (entry-point, help, exit) | US1 (backbone) | SC-001/004 |
| REQ-010, 011, 013 (index + report + non-distr.) | US1 | SC-001/006 |
| REQ-012 (abort senza parziale) | US1 | SC-005 |
| REQ-014 (corpus namespaced) | US1 | SC-006 |
| REQ-040, 041 (config + blocco senza provider) | US1 | SC-005 |
| REQ-060, 061 (install≠run, agnostico) | US1 | SC-004/006 |
| REQ-020 (risultati + anteprima) | US2 | SC-002 |
| REQ-021 (default da core) | US2 | SC-002 |
| REQ-022 (indice mancante → errore) | US2 | SC-002 |
| REQ-023 (testo/--json/--full) | US2 | SC-002 |
| REQ-030, 031 (wiki index) | US3 | SC-003 |
| REQ-050, 051, 052 (verbosity/json/log-config) | US4 | SC-007 |
| REQ-053, 055 (log errori, redazione) | US4 | SC-007 |

## Assumptions

- L'entry-point `sertor` è un **console-script** installato con l'installazione editable del pacchetto
  nell'ambiente di sviluppo; la **distribuzione pubblica** (PyPI/git+url) è fuori ambito (DA-C1).
- La configurazione (provider/backend) è **definita** in env/.env e letta dal core; la CLI la **legge**,
  non la scrive (no wizard interattivo — DA-C2/FEAT-CLI-003).
- Il **provider reale** (Ollama o Azure) è prerequisito d'**esecuzione**, non di costruzione: i test
  usano mock; il dogfooding reale richiede un provider configurato (DA-C5/A-3 dei requisiti).
- La provenienza dei corpora è gestita via **collezioni namespaced distinte** (DA-C2).
- `sertor-core` (FEAT-001/002/003) è disponibile in `master` ed espone composition root e
  `index_wiki`; la CLI ne è consumatrice (Principio I).
