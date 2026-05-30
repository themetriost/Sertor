# Epica — Sertor CLI (toolkit installabile per RAG + governance + LLM Wiki)

> Livello: **epica** (requisito di alto livello). Le feature del backlog (§8) verranno
> decomposte una per una in `requirements/sertor-cli/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

Oggi la conoscenza maturata in questo workspace — i motori RAG (baseline vettoriale, hybrid,
graph, agentico), la configurazione di agenti/skill, e il pattern dell'**LLM Wiki** — vive
**dentro un singolo repository** e va ricostruita a mano ogni volta che la si vuole portare
altrove. Manca un modo **riproducibile e portabile** per installare e configurare questi
elementi su un progetto qualsiasi.

L'epica introduce un **pacchetto installabile** (via `uv` o `pip`) che espone una **command line**.
Il CLI permette di **scegliere e installare** in modo selettivo le capacità (motori RAG, configurazione
di governance, LLM Wiki) su un repository — **nuovo o esistente** — e di **configurarle** (provider
LLM, vector DB) **senza far partire automaticamente** la creazione/ingestione del RAG: l'installazione
e l'esecuzione sono **comandi distinti**. Il fine è trasformare l'esperienza del prototipo in uno
**strumento riusabile e repo-agnostico**, riutilizzabile in contesto enterprise.

## 2. Ambito

### In ambito
- Un **pacchetto installabile** (`uv`/`pip`) che fornisce un **CLI** come punto di ingresso unico.
- **Setup selettivo**: l'utente sceglie *cosa* installare; nulla parte da solo.
- **Installazione dei motori RAG** definiti nell'esempio: baseline vettoriale, hybrid/reranking,
  graph, agentico — selezionabili indipendentemente.
- **Configurazione del RAG**: scelta del **provider LLM** (obbligatorio) e del **vector DB**
  (opzionale, e se presente con scelta locale/cloud).
- **Comando separato** per la creazione/esecuzione del RAG (ingestione/indicizzazione), distinto
  dall'installazione.
- **LLM Wiki**: setup e gestione di un wiki in formato Markdown che indicizza le informazioni del
  progetto, documenta in modo continuo, archivia e indicizza le conversazioni.
- **Spider/Lint del wiki**: una manutenzione che tiene vivo il wiki (rigenera indice, valida i
  collegamenti, distilla "conversazione grezza → voce di wiki").
- **Arricchimento bidirezionale Wiki↔RAG**: il wiki alimenta la parte *documentale* del RAG; i
  sorgenti (e le loro modifiche) alimentano la parte *codice* del RAG e le fondamenta del wiki.
- **Setup della configurazione di governance** (skill/agenti per le fasi di progetto + skill di
  gestione requisiti) come capacità installabile.
- Funzionamento **agnostico rispetto al repository**: applicabile sia a un progetto nuovo sia a uno
  già avviato.

### Fuori ambito (per ora)
- **Pubblicazione pubblica su PyPI** e relativo hardening (versioning pubblico, licenza, sicurezza
  supply-chain): rimandata; il design *non deve precludervi* (vedi §6, §8 Won't).
- Definizione del *come* (stack interno, API, schema dati, struttura del codice): è materia della
  **fase di design** a valle, non dei requisiti.
- Creazione dei *contenuti* RAG/Wiki di uno specifico progetto target (è uso dello strumento, non
  costruzione dello strumento).
- Interfaccia grafica/web: il deliverable è una **command line**.

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (installabilità):** un utente installa il pacchetto con un singolo comando `uv`/`pip` e ha
  il CLI disponibile a riga di comando, su una macchina pulita, senza passi manuali aggiuntivi.
- **CS-2 (install ≠ run):** in **0** casi l'installazione o l'aggiunta di un componente avvia
  automaticamente l'ingestione/creazione del RAG; serve sempre un comando esplicito separato.
- **CS-3 (selettività):** l'utente può installare un **qualsiasi sottoinsieme** delle capacità
  (almeno: motori RAG, governance, wiki) e ottenere solo quelle.
- **CS-4 (agnosticità):** lo stesso CLI completa con successo il setup sia su un **repo nuovo** sia
  su un **repo esistente** (≥2 scenari verificati) senza sovrascrivere silenziosamente file utente.
- **CS-5 (configurabilità LLM):** la configurazione supporta **≥1 provider cloud** (default) **e**
  un'opzione **locale (Ollama)**; senza un LLM configurato le operazioni RAG sono bloccate.
- **CS-6 (vector DB a scelta):** la configurazione consente di scegliere tra **≥2** opzioni di
  vector DB (locale vs cloud) oppure di **ometterlo** quando non richiesto.
- **CS-7 (wiki vivo):** lo spider/lint può essere rieseguito in modo **idempotente** (re-run senza
  divergenze) e produce un indice rigenerato e collegamenti validi.
- **CS-8 (arricchimento):** una sessione di aggiornamento RAG può usare **sia** i sorgenti **sia** il
  wiki come input, in modo dimostrabile (entrambe le sorgenti contribuiscono al risultato).

## 4. Stakeholder e attori
- **Owner/maintainer (tu):** utente primario interno; decide cosa installare e configurare.
- **Team interno (futuro prossimo):** utenti dello strumento in altri repository.
- **Utenti pubblici (futuro):** destinatari di una eventuale release PyPI (oggi Won't).
- **Agente LLM (es. Claude Code):** attore non umano che *consuma* la configurazione, il wiki e il
  RAG installati (li usa come contesto/strumenti).
- **Repository target:** il progetto (nuovo o esistente) su cui il CLI opera.

## 5. Vincoli, assunzioni e dipendenze
- **Linguaggio/distribuzione:** Python ≥ 3.11; installabile con **`uv`** (preferito) o **`pip`**.
- **LLM obbligatorio:** deve esistere un target LLM configurato; **default = provider cloud**
  (API key, es. OpenAI/Anthropic/Azure Foundry/…); **Ollama locale supportato** come scelta.
- **Vector DB opzionale/a scelta:** può non essere presente; se presente, scelta tra locale (Chroma)
  e cloud (PGVector/MongoDB su Azure).
- **Segreti:** chiavi/API mai persistite in file versionati (coerente con la policy `.env`).
- **Idempotenza/non distruttività:** il setup su repo esistente non deve sovrascrivere
  silenziosamente configurazioni dell'utente.
- **Assunzione:** "local-first / everything local" è **supportato** ma **non** è il default.
- **Dipendenza:** alcune capacità (es. motore graph) hanno dipendenze pesanti/conflittuali → vanno
  isolabili per evitare conflitti.

## 6. Rischi
- **R-1 — Conflitti di dipendenze** tra motori RAG (es. graph) installati insieme: rischio di ambienti
  non risolvibili. *Mitigazione concettuale:* isolamento/opzionalità per motore.
- **R-2 — Drift Wiki↔codice:** se lo spider non è robusto/idempotente, il wiki diverge dalla realtà
  del progetto e degrada il RAG documentale.
- **R-3 — Sicurezza segreti:** rischio di scrivere API key in file versionati durante la config.
- **R-4 — Avvio non voluto:** un'installazione che fa partire ingestione costosa (viola CS-2).
- **R-5 — Sovrascrittura su repo esistente:** perdita di config utente (viola CS-4).
- **R-6 — Scope creep verso il pubblico** prima della maturità interna.

## 7. Requisiti trasversali (EARS)
<!-- solo i pochi requisiti davvero trasversali a tutta l'epica -->
- **REQ-E1 (Optional):** *Where the user runs the setup command, the system shall let the user select
  which capabilities to install and install only the selected subset.*
- **REQ-E2 (Unwanted):** *If a component is installed or added, then the system shall not
  automatically start RAG ingestion or index creation.*
- **REQ-E3 (Ubiquitous):** *The system shall require a configured LLM target before performing any
  RAG operation.*
- **REQ-E4 (Optional):** *Where the user selects a local-only configuration, the system shall operate
  without requiring any cloud service.*
- **REQ-E5 (Unwanted):** *If a configuration value is a secret (e.g., an API key), then the system
  shall not persist it in a version-controlled file.*
- **REQ-E6 (Event-driven):** *When the setup runs against an existing repository, the system shall not
  overwrite user-modified files without explicit confirmation.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **CLI installabile** (pacchetto `uv`/`pip`, entry-point, struttura comandi, principio install≠run) | Spina dorsale: senza il CLI nessuna capacità è raggiungibile | **Must** | da decomporre |
| FEAT-002 | **Installazione selettiva dei motori RAG** (baseline vettoriale, hybrid, graph, agentico) | Portare i 4 approcci RAG su un repo, a scelta, senza eseguirli | **Must** | da decomporre |
| FEAT-003 | **LLM Wiki — setup & gestione** (indicizza progetto in MD, documenta in continuo, archivia/indicizza conversazioni) | Conoscenza persistente e cumulativa del progetto | **Must** | da decomporre |
| FEAT-004 | **Wiki Spider / Lint** (rigenera indice, valida link, rileva orfani/contraddizioni, distilla raw→concept) | Mantiene il wiki vivo e coerente (idempotente) | **Must** | da decomporre |
| FEAT-005 | **Configurazione del RAG** (provider LLM obbligatorio con default cloud + Ollama; vector DB opzionale/a scelta locale vs Azure) | Adatta il RAG all'ambiente target senza toccare codice | **Should** | da decomporre |
| FEAT-006 | **Comando di creazione/esecuzione del RAG** (ingestione/indicizzazione, separato dall'install) | Costruire/aggiornare effettivamente gli indici su richiesta esplicita | **Should** | da decomporre |
| FEAT-007 | **Setup configurazione di governance** (skill/agenti di fase + skill gestione requisiti) | Replicare la configurazione di lavoro su altri repo | **Should** | da decomporre |
| FEAT-008 | **Arricchimento bidirezionale Wiki↔RAG** (wiki → RAG documentale; sorgenti → RAG codice + fondamenta wiki) | Loop virtuoso doc/codice che migliora retrieval e documentazione | **Could** | da decomporre |
| FEAT-009 | **Distribuzione pubblica su PyPI** (versioning pubblico, licenza, hardening supply-chain) | Apertura a utenti esterni | **Won't (per ora)** | rinviata |

> **Nota sull'MVP:** il primo taglio (Must) installa i **motori RAG** e mette in piedi il **wiki vivo**
> (setup + spider). La **configurazione** (FEAT-005) e l'**esecuzione** (FEAT-006) del RAG completano
> il ciclo subito dopo (Should): logicamente la config precede il run, ma il confine MVP scelto mette
> prima l'installabilità e il loop del wiki. Vedi domanda aperta DA-2.

## 9. Domande aperte
<!-- ogni punto irrisolto resta [DA CHIARIRE] -->
- **DA-1 — Nome ufficiale** del pacchetto e del comando CLI (es. `sertor`?). *[DA CHIARIRE: naming]*
- **DA-2 — Confine install/config/run:** confermi che l'MVP **installa** i motori RAG ma **configura
  ed esegue** in una fase successiva (FEAT-005/006 = Should), accettando che senza config il RAG non
  sia ancora eseguibile? *[DA CHIARIRE: accettazione del confine]*
- **DA-3 — Governance come Should:** ok che il setup di skill/agenti+requisiti (FEAT-007) **non** sia
  nel primo taglio, pur essendo la config con cui lavoriamo ora? *[DA CHIARIRE]*
- **DA-4 — Distribuzione interna interim:** come si distribuisce internamente prima di PyPI (indice
  privato, `git+url`, wheel locale)? Incide su CS-1. *[DA CHIARIRE: canale di distribuzione interno]*
- **DA-5 — Vector DB obbligatorio o no:** lasciamo il vector DB **realmente opzionale** (alcuni motori
  potrebbero richiederlo)? Se un motore selezionato lo richiede, la config lo rende obbligatorio
  *solo per quel motore*? *[DA CHIARIRE: regola di obbligatorietà condizionale]*
- **DA-6 — Set di provider LLM del primo taglio:** quali provider cloud sono supportati da subito
  (OpenAI, Anthropic, Azure Foundry, …)? (Dettaglio da rifinire a livello di FEAT-005.) *[DA CHIARIRE]*
