---
title: DA-W1 — Ruolo di prodotto dell'LLM Wiki (corpus × superficie)
type: concept
tags: [wiki, rag, da-w1, prodotto, requisiti]
created: 2026-05-31
updated: 2026-05-31
sources: [requirements/sertor-core/epic.md]
---

# DA-W1 — Ruolo di prodotto dell'LLM Wiki (corpus × superficie)

**DA-W1** è la domanda di prodotto, aperta nell'epica primaria `requirements/sertor-core/epic.md`, su **COME il wiki viene usato nel prodotto Sertor** e come si relaziona al RAG e all'MCP.

Risolta in discussione il **2026-05-31**.

È propedeutica alla decomposizione delle feature wiki del core:
- **FEAT-003** (Must): creare/indicizzare nel RAG
- **FEAT-007** (Should): spider/lint e manutenzione
- **FEAT-008** (Could): arricchimento bidirezionale

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
tra i documenti ingeriti e spezzati in chunk. **Già verificato:** interrogando il RAG di
dogfooding con `search_docs`, tornano pagine del wiki (`log.md`, `index.md`, `syntheses/...`).
Quindi è **GIÀ ATTIVO**.

**SUPERFICIE** (di accesso / retrieval surface) = l'INTERFACCIA con cui si raggiunge la
conoscenza: quali operazioni e che FORMA hanno i risultati. Esempi:
- Superficie **semantica/RAG** → ritorna **chunk** per somiglianza
- Superficie **wiki-nativa** → *"apri la pagina intera"*, *"segui i backlink"*, *"parti dall'indice"*
  → ritorna **pagine intere** dentro la loro mappa

### Tabella concettuale: corpus × superficie

|  | Superficie semantica/RAG | Superficie wiki-nativa |
|---|---|---|
| **Corpus codice** | ✓ Attiva (chunk di codice nel RAG) | ✗ N/A (codice senza indice/backlink) |
| **Corpus wiki** | ✓ Già attiva (chunk nel RAG) | ◇ Da costruire (indice→pagina→backlink) |

Intuizione: **corpus e superficie sono ORTOGONALI** (cosa × come). Lo STESSO contenuto (il wiki)
può essere raggiunto da **DUE superfici** (chunk semantici OPPURE pagine navigabili).
La STESSA superficie (RAG) può stare sopra **PIÙ corpora** (codice + wiki).

## I tre ruoli del wiki

### 1. **Contesto iniettato (push)**

Il wiki prepara il contesto dell'agente **PRIMA di qualunque query** (oggi: hook `SessionStart`
di Claude Code, vedi pagina dedicata [[hook-sessionstart-wiki]]).

Usa la superficie **strutturata** in modalità **PUSH**: mappa e log recente vengono iniettati
automaticamente in sessione.

### 2. **Query precisa (pull strutturato)**

Chiedere **AL wiki** *"cosa abbiamo deciso su X"* e ottenere la **pagina curata/autorevole intera**
+ backlink, NON chunk fuzzy.

Distinto da `search_docs` (similarità semantica): qui si sfrutta la **struttura** (lookup per nome/indice,
segui i link, naviga per data/sezione).

### 3. **Ingestion nel RAG (input)**

Il wiki → parte documentale del RAG, quindi **corpus** del sistema di retrieval.

**GIÀ ATTIVO** nel dogfood.

## Le decisioni (DA-W1 risolta 2026-05-31)

### Identità: wiki = CORPUS + SUPERFICIE (entrambi)

Il wiki è ingerito nel RAG **E** navigabile per struttura. Non è uno o l'altro; è entrambi
a livelli diversi.

### Autorità nel ranking: PARITARIO sull'asse corpus

Un chunk di wiki pesa come uno di codice nel ranking semantico. Nessun boost specifico.

L'**autorevolezza del wiki** deriva dalla **SUPERFICIE strutturata** (come ci si accede),
non dal ranking RAG. _Non è in tensione_ con l'identità corpus+superficie: il wiki è speciale
per **COME ci si accede**, non per quanto pesa nella similarità semantica.

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
- [[hook-sessionstart-wiki]] (prova vivente del ruolo 1 oggi, implementato nell'host).
