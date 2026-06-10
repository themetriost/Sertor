---
title: Karpathy — LLM Wiki (gist originale)
type: source
tags: [llm-wiki, karpathy, pattern, fonte-fondativa]
created: 2026-06-10
updated: 2026-06-10
sources: ["https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"]
---

# Karpathy — LLM Wiki (gist originale)

La **fonte fondativa** del nostro sistema-wiki: il gist di Andrej Karpathy (post su X, aprile 2026, 16M+
view; 5.000+ star in pochi giorni) che definisce il pattern "LLM Wiki". Fino a oggi era citato ovunque
nel wiki di seconda mano ("pattern Karpathy"); questa pagina è l'àncora di prima mano.

## La tesi

Invece di un RAG che ri-deriva la conoscenza a ogni query dai documenti grezzi, l'LLM **costruisce e
mantiene incrementalmente un wiki persistente** — markdown strutturato e interlinkato che siede tra
l'utente e le fonti. «The wiki is a persistent, compounding artifact»: la conoscenza si sintetizza una
volta e si tiene aggiornata. Il perché funziona: «the tedious part of maintaining a knowledge base is not
the reading or the thinking — it's the bookkeeping» — e per un LLM il costo del bookkeeping è ~zero (non
si annoia, non dimentica un cross-reference, tocca 15 file in un passaggio).

## Architettura a tre strati

1. **Raw sources** (immutabili) — l'LLM legge, mai modifica;
2. **Il wiki** (di proprietà dell'LLM) — pagine entità/concetto interlinkate; l'utente legge, l'LLM scrive;
3. **Lo schema** (contratto comportamentale, es. `CLAUDE.md`) — struttura, convenzioni, workflow;
   **co-evoluto** con l'utente nel tempo.

## Operazioni, indice, log

Tre operazioni: **ingest** (fonte → pagina-riassunto + aggiornamento di indice e pagine correlate — una
fonte può toccare 10-15 pagine), **query** (risposte con citazioni; le buone risposte si archiviano come
pagine — il compounding), **lint** (salute periodica: contraddizioni, claim stantii, orfani, gap).
`index.md` è il catalogo (una riga per pagina, letto per primo); `log.md` è il registro append-only con
prefissi greppabili (`## [data] ingest | titolo`).

## Il claim sul RAG (rilevante per noi)

Sotto **~50-100k token** (~150-200 pagine dense) il wiki-in-contesto **batte il RAG**: retrieval al 100%
(nessun chunk perso), zero infrastruttura, ragionamento globale sul corpus intero. Il RAG diventa
necessario solo a milioni di token. → **Tensione col nostro design** segnalata in [[wiki-role-da-w1]]:
noi indicizziamo il wiki nel RAG (corpus unico, D-21). Non è una contraddizione secca — il nostro corpus
include il *codice* (ben oltre la soglia) e DA-W1 dà già alla *superficie strutturata* (indice iniettato
a inizio sessione) il ruolo primario per il wiki — ma il gist conferma che per il wiki da solo il canale
giusto è la superficie, non il ranking semantico.

## Cosa conferma del nostro design

Quasi tutto, in modo quasi imbarazzante: l'indice-letto-per-primo, il log append-only con heading
datati, lo schema in `CLAUDE.md`, le tre operazioni (le nostre 9 sono un'estensione), Obsidian come IDE,
il wiki come repo git, il filing delle risposte di query (la nostra op `query`), e la radice filosofica
(il **Memex** di Vannevar Bush, 1945: archivio personale curato con "associative trails" — il pezzo che
Bush non poteva risolvere era la *manutenzione*, ed è quello che l'LLM risolve). Il gist è
**intenzionalmente astratto**: «it describes the idea, not a specific implementation» — istanziarlo col
proprio LLM secondo le proprie esigenze è il modo d'uso previsto. Sertor è una di queste istanze,
industrializzata (nucleo deterministico [[wiki-tools]] + operazioni-giudizio).

## Vedi anche

- [[llm-wiki-v2-agentmemory]] — l'estensione "grassa" del pattern (lifecycle, grafo tipizzato, automazione).
- [[architettura-wiki-llm]] — come Sertor istanzia il pattern; [[diary-vs-graph]] — le due memorie.
- [[wiki-role-da-w1]] — la decisione corpus×superficie, dove vive la tensione RAG-vs-contesto.
