---
title: Wiki role (DA-W1) — corpus × surface
type: concept
tags: [wiki, rag, da-w1, prodotto, requisiti]
created: 2026-05-31
updated: 2026-06-09
sources: [requirements/sertor-core/epic.md, wiki.config.toml, .claude/skills/wiki-author/ops/rag-sync.md]
---

# Wiki role (DA-W1) — corpus × surface

Nel prodotto Sertor il wiki ha una doppia natura: è insieme **corpus** (contenuto ingeribile nel RAG) e
**superficie** (struttura navigabile per indice/backlink). Corpus e superficie sono **assi ortogonali**:
lo stesso contenuto è raggiungibile da più superfici, e la stessa superficie può stare sopra più corpora.
Capire questa ortogonalità è ciò che permette di decidere *cosa* l'MVP del wiki deve fare e cosa no.

> **Origine.** È la risposta a **DA-W1**, la domanda di prodotto aperta in `requirements/sertor-core/epic.md`
> su come il wiki si relaziona a RAG/MCP (risolta in elicitazione, 2026-05-31). Propedeutica alla
> decomposizione delle feature wiki: FEAT-003 (Must, creare/indicizzare), FEAT-007 (Should, manutenzione),
> FEAT-008 (Could, arricchimento bidirezionale).

## Il modello concettuale: due assi ortogonali

Il nodo è che **wiki** e **RAG-sui-sorgenti** sono **DUE LAYER DI CONOSCENZA** diversi:

- **RAG sui sorgenti** = codice + documentazione GREZZI, ingeriti automaticamente, chunk piatti,
  accesso per **similarità semantica (fuzzy)**. Risponde a *"dove/come è implementato X"*.
  Non contiene il *"perché"*.

- **LLM Wiki** = conoscenza DISTILLATA (decisioni, concetti, sintesi, log, il *"perché"*),
  scritta da agente/umano (record/ingest), struttura navigabile (indice, frontmatter, wikilink,
  sezioni). Risponde a *"cosa sappiamo/abbiamo deciso, e perché"*.

### Definizioni chiave

**CORPUS** = l'insieme dei CONTENUTI che un sistema di retrieval ha ingerito e indicizzato.
Dire *"il wiki è nel corpus del RAG"* significa, letteralmente, che i file `.md` del wiki sono
tra i documenti ingeriti e spezzati in chunk. Il meccanismo esiste: l'operazione **`rag-sync`**
indicizza il wiki in un **corpus dedicato** (`[rag] corpus = "wiki"` in `wiki.config.toml`), separato dal
corpus del codice. Nota (aggiornata 2026-06-10, D-21 — *modello a corpus unico*): il dogfood di produzione
`sertor` indicizza **anche `wiki/`** come documentazione del corpus primario (il wiki vive dentro l'ospite
by design); il corpus `wiki` separato di `rag-sync` resta una capacità esercitabile per ospiti con corpora
davvero disgiunti, non il default.

**SUPERFICIE** (di accesso / retrieval surface) = l'INTERFACCIA con cui si raggiunge la
conoscenza: quali operazioni e che FORMA hanno i risultati. Esempi:
- Superficie **semantica/RAG** → ritorna **chunk** per somiglianza
- Superficie **wiki-nativa** → *"apri la pagina intera"*, *"segui i backlink"*, *"parti dall'indice"*
  → ritorna **pagine intere** dentro la loro mappa

### Tabella concettuale: corpus × superficie

|  | Superficie semantica/RAG | Superficie wiki-nativa |
|---|---|---|
| **Corpus codice** | ✓ Attiva (chunk di codice nel RAG, dogfood `sertor`) | ✗ N/A (codice senza indice/backlink) |
| **Corpus wiki** | ◇ Disponibile via `rag-sync` (corpus `wiki` separato) | ◇ Da costruire (indice→pagina→backlink) |

Intuizione: **corpus e superficie sono ORTOGONALI** (cosa × come). Lo STESSO contenuto (il wiki)
può essere raggiunto da **DUE superfici** (chunk semantici OPPURE pagine navigabili).
La STESSA superficie (RAG) può stare sopra **PIÙ corpora** (codice + wiki).

## I tre ruoli del wiki

### 1. **Contesto iniettato (push)**

Il wiki prepara il contesto dell'agente **PRIMA di qualunque query** (oggi: hook `SessionStart`
di Claude Code, vedi pagina dedicata [[sessionstart-hook]]).

Usa la superficie **strutturata** in modalità **PUSH**: mappa e log recente vengono iniettati
automaticamente in sessione.

### 2. **Query precisa (pull strutturato)**

Chiedere **AL wiki** *"cosa abbiamo deciso su X"* e ottenere la **pagina curata/autorevole intera**
+ backlink, NON chunk fuzzy.

Distinto da `search_docs` (similarità semantica): qui si sfrutta la **struttura** (lookup per nome/indice,
segui i link, naviga per data/sezione).

### 3. **Ingestion nel RAG (input)**

Il wiki → parte documentale del RAG, quindi **corpus** del sistema di retrieval.

Realizzato dall'operazione **`rag-sync`** (indice dedicato, corpus `wiki`). È il confine **Must** di
FEAT-003: creare le pagine e poterle indicizzare.

## Le decisioni (DA-W1 risolta 2026-05-31)

### Identità: wiki = CORPUS + SUPERFICIE (entrambi)

Il wiki è ingerito nel RAG **E** navigabile per struttura. Non è uno o l'altro; è entrambi
a livelli diversi.

### Autorità nel ranking: PARITARIO sull'asse corpus

Un chunk di wiki pesa come uno di codice nel ranking semantico. Nessun boost specifico.

L'**autorevolezza del wiki** deriva dalla **SUPERFICIE strutturata** (come ci si accede),
non dal ranking RAG. _Non è in tensione_ con l'identità corpus+superficie: il wiki è speciale
per **COME ci si accede**, non per quanto pesa nella similarità semantica.

> **Conferma dalla fonte fondativa (ingest 2026-06-10, [[karpathy-llm-wiki]]):** il gist originale
> sostiene che sotto ~50-100k token il wiki-in-contesto **batte il RAG** (retrieval 100%, zero
> infrastruttura, ragionamento globale) e che il RAG serve solo a scala molto maggiore. Per il wiki *da
> solo* la nostra scelta è coerente (il canale autorevole è la superficie: indice iniettato, pagine
> intere); l'ingestion nel RAG (ruolo 3) resta giustificata perché il **corpus unico include il codice**,
> che è oltre soglia — non per il retrieval del wiki in sé. Tensione segnalata, non contraddizione.

### Confine MVP (FEAT-003 Must): creare + indicizzare nel RAG

- **DEVE:** creare pagine wiki + indicizzarle nel RAG (ruolo 3 = ingestion).
- **NON deve (post-MVP):**
  - Superficie wiki-nativa (ruoli 1 e 2)
  - Spider/lint (FEAT-007)
  - Arricchimento bidirezionale (FEAT-008)

Questo risolve anche **DA-2**: l'MVP del wiki è la **sola creazione/indicizzazione**, niente spider
o manutenzione automatica.

### Ruolo 1 (contesto iniettato): competenza dell'HOST, non di Sertor

L'hook `SessionStart` che prepara il contesto è implementato dall'**HOST** (es. Claude Code),
**non** da Sertor nel MVP.

Sertor espone il wiki ben strutturato (`wiki/index.md`, `wiki/log.md`, pagine interlinkate).
L'host decide **cosa/quando iniettare** per preparare le sessioni.

Non preclude un futuro *"context payload"* generato direttamente da Sertor.

**Coerenza:** poiché ruoli 1 e 2 poggiano sulla **superficie wiki-nativa** (fuori MVP),
anche il ruolo 1 rimane **post-MVP** come responsabilità di Sertor in prima persona.

## Impatto sulla epica e sui requisiti

Sblocca:
- **FEAT-003 (MVP):** decomposizione in user story (crea, indicizza, esponi).
- **FEAT-007 (post-MVP):** manutenzione e superficie wiki-nativa.
- **FEAT-008 (post-MVP):** loop bidirezionale sorgenti → RAG → wiki → RAG.

Riferimenti:
- `requirements/sertor-core/epic.md` §9 (DA-W1, DA-2 risolte) e §6 (R-5 mitigato).
- [[epiche-sertor-core-e-cli]] (stato e sequenza prioritaria).
- [[sessionstart-hook]] (prova vivente del ruolo 1 oggi, implementato nell'host).
