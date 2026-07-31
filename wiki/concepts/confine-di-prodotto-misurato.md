---
title: Un confine di prodotto si misura, non si deduce
type: concept
tags: [separazione, accoppiamento, dipendenze, metodo, migrazione, debito]
created: 2026-07-31
updated: 2026-07-31
sources: ["specs/127-separazione-quattro-prodotti/migration-plan.md", "src/sertor_core/wiki_tools/", "packages/"]
---

# Un confine di prodotto si misura, non si deduce

Quando si decide di **separare** un sistema in prodotti distinti, la tentazione è disegnare il confine
dall'**intenzione**: *«questo è il wiki, quello è il RAG, quest'altro è il metodo»*. L'intenzione è una
buona ipotesi di partenza e una pessima base per un piano, perché il costo della separazione non sta
dove sta il significato: sta dove stanno gli **import**.

> **La domanda giusta non è «di chi è questo modulo?» ma «quante righe lo legano a ciò che resta, e
> quali?»** — ed è una domanda con risposta numerica, ottenibile in minuti.

## Cosa succede quando la misuri davvero

Applicando la misura alla separazione di Sertor in quattro prodotti (piano del 2026-07-31), tutte e
tre le aspettative si sono rivelate sbagliate — **nessuna nella direzione prudente**:

### 1. La maggior parte dei confini era già tagliata

| Candidato alla separazione | Accoppiamento atteso | Accoppiamento **misurato** |
|---|---|---|
| `sertor-flow` (governance) | «dipende dal core» | **zero** — dipende solo dal kit d'installazione |
| `prototype/` (il congelato) | «usa il motore» | **zero import** di `sertor_core` |
| `install-kit` (motore d'installazione) | «è parte del core» | **zero** — le due occorrenze del nome sono commenti che *dichiarano* l'indipendenza |
| `wiki_tools` (il sistema-wiki) | «intrecciato col RAG» | **quattro** punti: logging ×11, errori ×5, `Settings` ×1 **lazy**, `build_indexer` ×1 **lazy** |

Il taglio più costoso non era architetturale: era il **logging**. Undici chiamate a una funzione di
osservabilità — la cosa meno interessante del sistema — pesavano più di tutta la separazione
concettuale fra wiki e retrieval.

### 2. Il debito non vive dove dice il suo indirizzo

L'epica «debito tecnico» sta nel repo che si chiama Sertor, quindi si legge come debito di Sertor.
Classificate le sue 67 voci per contenuto: **43 nominano il wiki**, 13 il RAG, 11 la governance. Il
prodotto che deve ancora nascere **eredita la maggioranza del debito aperto**.

**Perché nessuno se n'era accorto:** un backlog trasversale ospitato da un prodotto viene attribuito a
quel prodotto per **default di collocazione**, e nulla lo misura finché non arriva una domanda che
costringe a contare. È la stessa forma di [[riassunto-invecchia-senza-riconciliatore]] — un fatto
derivabile che nessuno deriva — applicata alla **proprietà** invece che al contenuto.

### 3. Le guardie non appartengono alle parti, ma al meccanismo

Dei 58 test dell'installer, solo 21 riguardano una capability (16 RAG, 5 wiki). Gli altri **37 sono
guardie di meccanismo**: parità fra assistenti, forma delle superfici, portabilità degli hook, schema
del frontmatter, merge dei settings, policy dei modelli.

È il dato che ha deciso il design: **la promessa "host-agnostico su Claude e Copilot" non vive in
nessuno dei prodotti, vive nel motore che li installa.** Duplicare quel motore significa triplicare le
guardie o spartirle a caso — e allora la promessa diventa tre promesse indipendenti che nessuno
riconcilia, che è [[pratica-standing-vs-pratica-distribuita]] introdotta di proposito.

## Il metodo, in quattro domande

Da porre **prima** di scrivere qualsiasi piano di separazione, su ogni candidato:

1. **Quanti import lo legano a ciò che resta?** (`grep "from <pacchetto>"`) — e di questi, quanti sono
   **lazy** o già iniettabili? Un import lazy dietro un factory parametrico *non è* un accoppiamento:
   è una dipendenza già invertita da chi l'ha scritta.
2. **Le occorrenze del nome sono codice o prosa?** Un modulo che *nomina* un altro in un commento per
   dichiarare di non dipenderne è il contrario di un accoppiamento — ma un `grep` ingenuo lo conta
   uguale.
3. **A chi appartiene il debito aperto**, riga per riga? Non l'epica: le **voci**.
4. **Le verifiche esistenti cosa proteggono** — una capability, o il meccanismo che le accomuna? Le
   seconde vanno dove va il meccanismo, non spartite fra i prodotti.

## Il corollario che vale il metodo

**Misurare cambia l'ordine del lavoro, non solo la sua descrizione.** Sapere che tre nodi su quattro
hanno accoppiamento zero permette di ordinare le fasi per **rischio crescente** e di pagare la
procedura rischiosa (riscrittura della storia git, verifica su host pulito) sul caso più semplice,
dove un errore costa poco. Un piano scritto sull'intenzione avrebbe iniziato dal pezzo "più
importante" — che è anche quello con quattro suture e un gate bloccante che ci gira sopra.

Parente di [[potere-retrospettivo-di-una-guardia]]: là la domanda con risposta numerica è *«quanti
difetti già avvenuti avrebbe fermato?»*, qui è *«quante righe legano davvero questo pezzo al resto?»*.
Stessa mossa — **sostituire una stima con un conteggio** — su una decisione diversa.
