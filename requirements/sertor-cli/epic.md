# Epica — Sertor CLI (distribuzione e uso del core via command line)

> Livello: **epica SECONDARIA**. Veicola le capacità dell'epica primaria
> [`../sertor-core/epic.md`](../sertor-core/epic.md) (motori RAG + skill LLM Wiki) rendendole
> **installabili, configurabili ed eseguibili** su un repository qualunque. **Dipende dal core**:
> la CLI non *è* il prodotto, è il **modo per usarlo**. Le feature (§8) si decompongono in
> `requirements/sertor-cli/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Le capacità del **core** (creare RAG vettoriale/ibrido/grafico/agentico, creare e gestire l'LLM Wiki)
devono poter essere **portate su un progetto qualsiasi** senza ricostruirle a mano. Serve un
**pacchetto installabile** `sertor` (via `uv` o `pip`) che espone una **command line** (comando
`sertor`) per **scegliere e installare** in modo selettivo le capacità del core su un repository —
**nuovo o esistente** — **configurarle** (provider LLM, vector DB) ed **eseguirle** su richiesta.

Principio cardine: **installazione ≠ esecuzione**. Installare o aggiungere una capacità **non** avvia
da solo la creazione/ingestione del RAG: serve sempre un **comando esplicito** separato.

## 2. Ambito

### In ambito
- **Pacchetto installabile** (`uv`/`pip`) con **CLI** `sertor` come punto d'ingresso unico.
- **Setup selettivo** sul repo target: l'utente sceglie *quali* capacità del core installare; nulla parte da solo.
- **Configurazione** delle capacità installate: provider **LLM** (obbligatorio, default cloud) e
  **vector DB** (condizionale, locale vs cloud).
- **Comando di creazione/esecuzione del RAG** (ingestione/indicizzazione), distinto dall'installazione.
- **Setup della configurazione di governance** (skill/agenti di fase + skill gestione requisiti) su un repo.
- **Agnosticità rispetto al repository** (progetto nuovo o già avviato) e **non distruttività**.
- **Distribuzione** del pacchetto (interim via `git+url`).

### Fuori ambito
- **Le capacità in sé** (come si crea/interroga il RAG, come funzionano le skill del wiki): sono
  l'epica **primaria** `sertor-core`. La CLI le **orchestra e installa**, non le definisce.
- **Pubblicazione pubblica su PyPI** e relativo hardening: rinviata (§8 Won't); il design non deve precluderla.
- Definizione del *come* (stack, API, schema, struttura del codice): fase di **design**.
- GUI/web: il deliverable è una **command line**.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (installabilità):** un utente installa il pacchetto con un singolo comando `uv`/`pip` e ha il
  comando `sertor` disponibile, su una macchina pulita, senza passi manuali aggiuntivi.
- **CS-2 (install ≠ run):** in **0** casi l'installazione/aggiunta di una capacità avvia automaticamente
  l'ingestione/creazione del RAG; serve sempre un comando esplicito separato.
- **CS-3 (selettività):** l'utente può installare un **qualsiasi sottoinsieme** delle capacità del core
  (motori RAG, skill wiki, governance) e ottenere solo quelle.
- **CS-4 (agnosticità & non distruttività):** lo stesso CLI completa il setup sia su un **repo nuovo**
  sia su uno **esistente** (≥2 scenari) senza sovrascrivere silenziosamente file dell'utente.
- **CS-5 (configurabilità LLM):** la configurazione supporta **≥1 provider cloud** (default) **e**
  un'opzione **locale (Ollama)**; senza un LLM configurato le operazioni RAG sono bloccate.
- **CS-6 (vector DB a scelta):** la configurazione consente di scegliere tra **≥2** opzioni di vector DB
  (locale vs cloud) oppure di **ometterlo** quando la modalità scelta non lo richiede.

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** decide cosa installare/configurare sul repo target.
- **Team interno (futuro prossimo):** usa la CLI per portare il core su altri repository.
- **Utenti pubblici (futuro):** destinatari di una eventuale release PyPI (oggi Won't).
- **Epica `sertor-core` (dipendenza a monte):** fornisce le capacità che la CLI installa/esegue.
- **Repository target:** il progetto (nuovo o esistente) su cui la CLI opera.

## 5. Vincoli, assunzioni e dipendenze
- **Dipendenza dal core:** la CLI installa/configura/esegue le capacità di `sertor-core`; non le duplica.
- **Linguaggio/distribuzione:** Python ≥ 3.11; pacchetto e comando = **`sertor`**; installabile con
  **`uv`** (preferito) o **`pip`**. **Distribuzione interim (pre-PyPI): `git+url`**.
- **LLM obbligatorio:** target LLM configurato; **default = provider cloud**. Provider del primo taglio:
  **OpenAI, Anthropic, Azure OpenAI/Foundry, GitHub Copilot** e **Ollama** (locale, non-default);
  aggiuntivi proposti (max 3, da confermare): **Google Gemini/Vertex AI, AWS Bedrock, Mistral AI**.
- **Vector DB condizionale:** obbligatorio solo se la modalità RAG selezionata lo richiede; a scelta
  **Chroma** (locale) vs **PGVector/MongoDB su Azure** (cloud).
- **Segreti:** mai persistiti in file versionati.
- **Idempotenza/non distruttività** sul repo esistente; **local-first supportato** (non default).

## 6. Rischi
- **R-1 — Avvio non voluto:** un'installazione che fa partire ingestione costosa (viola CS-2).
- **R-2 — Sovrascrittura su repo esistente:** perdita di config utente (viola CS-4).
- **R-3 — Sicurezza segreti** in fase di configurazione.
- **R-4 — Conflitti di dipendenze** tra capacità del core installate insieme (es. motore grafico).
- **R-5 — Disallineamento col core:** se le capacità del core cambiano, la CLI deve restarvi allineata.
- **R-6 — Scope creep verso il pubblico** prima della maturità interna.

## 7. Requisiti trasversali (EARS)
<!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
- **REQ-E1 (Optional):** *Where the user runs the setup command, the system shall let the user select
  which core capabilities to install and install only the selected subset.*
- **REQ-E2 (Unwanted):** *If a capability is installed or added, then the system shall not automatically
  start RAG ingestion or index creation.*
- **REQ-E3 (Ubiquitous):** *The system shall require a configured LLM target before running any RAG operation.*
- **REQ-E4 (Optional):** *Where the user selects a local-only configuration, the system shall operate
  without requiring any cloud service.*
- **REQ-E5 (Unwanted):** *If a configuration value is a secret (e.g., an API key), then the system shall
  not persist it in a version-controlled file.*
- **REQ-E6 (Event-driven):** *When the setup runs against an existing repository, the system shall not
  overwrite user-modified files without explicit confirmation.*
- **REQ-E7 (Optional):** *Where a selected RAG modality requires a vector store, the system shall require
  a vector DB to be configured; otherwise it shall allow the setup to complete without one.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **CLI installabile** (pacchetto `uv`/`pip`, entry-point `sertor`, struttura comandi, principio install≠run) | Spina dorsale: senza il CLI nessuna capacità è raggiungibile | **Must** | parz. → backbone/comandi in `esecuzione`; packaging rinviato |
| FEAT-002 | **Installazione selettiva delle capacità del core** (motori RAG + skill wiki) su un repo target | Portare il core su un progetto, a scelta, senza eseguirlo | **Must** | da decomporre |
| FEAT-003 | **Configurazione** (provider LLM obbligatorio default cloud + Ollama; vector DB condizionale a scelta Chroma vs PGVector/MongoDB Azure) | Adatta le capacità all'ambiente target senza toccare codice | **Should** | parz. → lettura config in `esecuzione`; wizard rinviato |
| FEAT-004 | **Comando di creazione/esecuzione del RAG** (ingestione/indicizzazione, separato dall'install) | Costruire/aggiornare gli indici su richiesta esplicita | **Should** | decomposta → `esecuzione` |
| FEAT-005 | **Setup configurazione di governance** (skill/agenti di fase + skill gestione requisiti) | Replicare la configurazione di lavoro su altri repo | **Should** | da decomporre |
| FEAT-006 | **Distribuzione pubblica su PyPI** (versioning pubblico, licenza, hardening supply-chain) | Apertura a utenti esterni | **Won't (per ora)** | rinviata |

> **Feature decomposta:** `esecuzione` (`requirements/sertor-cli/esecuzione/requirements.md`) — taglio
> **run-centrico**: entry-point + comandi `index`/`search`/`wiki index` + osservabilità a runtime +
> lettura della configurazione. Copre la parte eseguibile di FEAT-001, tutta FEAT-004 e la lettura
> config di FEAT-003. Restano fuori: packaging/distribuzione, install selettivo su altri repo (FEAT-002),
> wizard di configurazione, governance (FEAT-005).

> **Nota sull'MVP della CLI:** il primo taglio (Must) rende il pacchetto **installabile** e capace di
> **installare selettivamente** le capacità del core su un repo. Configurazione (FEAT-003), esecuzione
> (FEAT-004) e governance (FEAT-005) completano il ciclo subito dopo (Should). La CLI è utile **solo
> insieme** al core: il suo MVP presuppone che il core esista (almeno baseline + creazione wiki).

## 9. Decisioni risolte (DA-1…DA-6)

Chiuse in elicitazione (2026-05-30); restano valide a livello di distribuzione/uso:

| # | Tema | Decisione |
|---|------|-----------|
| DA-1 | Naming | Pacchetto e comando = **`sertor`**. |
| DA-2 | Confine install/config/run | **Confermato**: l'MVP della CLI installa; configurazione (FEAT-003) ed esecuzione (FEAT-004) restano **Should**. |
| DA-3 | Governance | **Resta Should** (FEAT-005 fuori dall'MVP della CLI). |
| DA-4 | Distribuzione interim | **`git+url`** prima dell'eventuale PyPI pubblico. |
| DA-5 | Vector DB | **Obbligatorio in modo condizionale**: solo se la modalità lo richiede; solo-graph può ometterlo (REQ-E7). |
| DA-6 | Provider LLM | Primo taglio: **OpenAI, Anthropic, Azure OpenAI/Foundry, GitHub Copilot, Ollama**; aggiuntivi (max 3, da confermare): **Gemini/Vertex AI, AWS Bedrock, Mistral AI**. |

> Nessuna domanda aperta residua a livello di questa epica. Le rifiniture di dettaglio si chiudono
> alla **decomposizione** delle feature.
