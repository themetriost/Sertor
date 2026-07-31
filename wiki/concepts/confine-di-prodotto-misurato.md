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

### 4. La duplicazione che nessuna guardia poteva vedere

Sciogliendo le decisioni sul piano è emerso un quarto fatto, e il più istruttivo: la conoscenza
*«dove va una skill per Claude e per Copilot»* era **già scritta due volte**, in due repo e in due
linguaggi — `Agent::install_subpath()` in Rust (`.claude/skills`, `.github/prompts`) e
`AssistantId`/`Surface` in Python. Nessuno l'aveva notato, e non per disattenzione:

> **Nessuna guardia di un singolo repo può vedere una duplicazione che attraversa due repo e due
> linguaggi.** Il parity guard confronta asset dentro il progetto; il lint confronta claim con il
> codice *locale*; la CI conosce un repo solo. Una verità scritta in Rust a Kaelen e in Python a
> Sertor non è vista da nessuno dei due — è invisibile **per costruzione**, non per caso.

La cosa da portarsi via non è «attenzione alle duplicazioni»: è che **l'atto di misurare un confine
per separarlo ha rivelato un accoppiamento che l'uso quotidiano non poteva mostrare**. Il piano di
separazione è servito da rilevatore prima ancora di essere eseguito.

Il rimedio adottato è lo stesso di ogni altra decisione presa quel giorno: **il contratto diventa un
dato** (uno schema di manifest letto da entrambi i linguaggi), così la duplicazione non viene gestita
— smette di poter esistere.

### 5. La cartella non è la proprietà — e l'aggregato non lo può vedere

Le prime quattro scoperte vengono da una misura **aggregata** (conteggi di import, di righe, di test).
La quinta viene dall'aver rifatto la stessa classificazione **file per file**, su richiesta — e ha
smentito l'aggregato **al primo colpo**:

| Affermazione aggregata | Verifica file-per-file |
|---|---|
| «i 20 file del wiki del prototipo viaggiano col prototipo» | **9 su 20** appartengono ad altri: 6 sono *metodo*, 3 sono *prodotto* |
| «4 riferimenti operativi da ripulire» | **5** — e il quinto era **rotto da due mesi** |
| «`--path prototype/` preserva la storia» | preserva **3 commit su 36**: l'isolamento fu una *rinomina* |

La causa è una sola, e vale oltre il caso:

> **Un file sta in una cartella per la storia che l'ha portato lì, non per ciò che è.** La proposta di
> costituzione stava in `prototype/wiki/syntheses/` perché nel maggio 2026 *tutto* stava lì — non
> perché appartenga al prototipo. La cartella registra **quando** una cosa è nata, la proprietà dice
> **cosa serve**: coincidono solo finché il progetto non si divide.

E il corollario che riguarda il metodo di misura:

> **L'aggregato può solo confermare la collocazione, mai contraddirla.** Contare per cartella eredita
> l'assunzione che la cartella sia la proprietà — l'ipotesi che dovrebbe verificare. Solo leggere il
> singolo file può smentirla, perché è l'unico livello in cui il contenuto parla al posto del percorso.
> È [[riuso-che-eredita-il-presupposto]] applicato agli **strumenti di misura**: un conteggio giusto
> per «quanto c'è qui dentro» è sbagliato per «a chi appartiene».

**Il costo di scoprirlo tardi è asimmetrico:** un file assegnato male viene *spostato* — e dopo lo
spostamento la sua storia sta in un repo, il file in un altro. Riparare significa ripetere la
migrazione, non correggere una riga.

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
