---
title: Il riuso che eredita il presupposto
type: concept
tags: [riuso, guardie, difetti, pattern-diagnostico, dry, e10]
created: 2026-07-29
updated: 2026-07-29
sources: ["src/sertor_core/wiki_tools/collect.py", "src/sertor_core/wiki_tools/lint.py", "packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md", "wiki/log/2026-07-29.md"]
---

# Il riuso che eredita il presupposto

Riusare qualcosa di corretto non produce qualcosa di corretto. Ogni artefatto — una funzione, una frase
d'istruzione, un insieme filtrato — è stato costruito per rispondere a **una** domanda, e porta con sé i
**presupposti** di quella domanda. Se lo si riusa per rispondere a un'altra, quei presupposti viaggiano
con lui, invisibili, e diventano il difetto.

> L'artefatto è **giusto per il suo scopo** e **sbagliato per lo scopo per cui è stato preso in
> prestito**. Non c'è un errore da nessuna delle due parti: c'è un errore **nel prestito**.

È la ragione per cui questa classe sopravvive alle revisioni. Chi legge il punto di riuso vede una cosa
corretta; chi legge la definizione vede una cosa corretta. Il difetto **non sta in nessuno dei due
posti** — sta nel salto.

## Due istanze, lo stesso giorno, dallo stesso segnalatore

**1. `iter_pages` usata per «cosa si può linkare»** (E10-FEAT-065). La funzione risponde a *«è una pagina
di contenuto?»* — cosa deve avere frontmatter, cosa può essere orfano — e per questo **esclude
correttamente** l'indice e le partizioni di giornale. Il `lint` costruiva da lì anche l'indice dei
bersagli linkabili, cioè la rispondeva a *«esiste, e quindi si può puntare?»*. Il presupposto ereditato —
*«ciò che non è pagina non conta»* — diventava *«ciò che non è pagina non è linkabile»*, e la guardia
dichiarava **rotto** un link a un file che esiste. Fino a `[[index]]`, l'indice del wiki stesso.

**2. La frase «bundled with the `wiki-author` skill»** (E10-FEAT-064). Nella `SKILL.md` la formula è
*«same folder»* e risolve, perché **chi la legge è dentro quella cartella**. Riusata nell'agente e nel
comando, ha perso la sola parte che la rendeva una coordinata: il presupposto ereditato era **la
posizione del lettore**. L'agente si fermava con `STOP — Missing Asset` su un file presente.

In entrambi i casi il riuso era **motivato e ragionevole** — non duplicare un'enumerazione, non
duplicare una frase. È DRY applicato correttamente al **testo** e scorrettamente al **significato**.

## La terza istanza, colta **prima** di spedirla (2026-07-29, stesso giorno)

Le prime due sono state trovate da un nodo a valle, a difetto già rilasciato. La terza è stata evitata
in fase di `plan`, ponendo alla lettera la domanda di questa pagina.

**Il riuso proposto**: per riconoscere che «una voce di giornale è stata aggiunta», riusare la regex
`^## \[[^\]]*\]\s+(?P<op>\S+)` che vive in `distill-floor.py` — codice nostro, funzionante, testato.

**Il presupposto che avrebbe portato con sé**: che l'intestazione di una voce **abbia quella forma**.
Verificando invece di assumere: `registry.py:87` costruisce l'intestazione con
`profile.log_format.format(date=…, op=…, title=…)`, e **`log_format` è un campo del profilo
dell'ospite**. La regex è corretta *per il nostro giornale* e falsa per chiunque configuri il proprio.

**Perché sarebbe stato il peggiore dei tre**: nessun errore. Su un ospite con un formato diverso non
sarebbe esploso nulla — semplicemente **zero voci riconosciute**, quindi copertura sempre vuota, quindi
**gate cieco**. Cioè il difetto che quel lavoro stava chiudendo, reintrodotto dal proprio rimedio, e
invisibile esattamente sugli ospiti e non su di noi.

> Il riuso più pericoloso non è quello sciatto: è quello di un artefatto **buono**, preso da un
> contesto in cui una variabile era **una costante**.

**Come è finita**: il disegno è cambiato per evitarlo del tutto. Fondando la copertura sull'**identità
del contenuto** invece che sui path, una copertura vecchia porta un contenuto vecchio che non combacia
e **scade da sé** — quindi non serve più sapere quali voci siano recenti, e non serve leggere le
intestazioni. Il presupposto non è stato reso esplicito: è stato reso **non necessario**, che è la
terza via oltre a *separare* e *dichiarare*.

*Nota utile a chi rilegge:* `distill-floor.py` conserva la regex cablata e quindi lo **stesso difetto
latente** su un ospite con `log_format` diverso. È rimasto fuori scope per deliberazione, non per
distrazione.

### La terza via, confermata in esercizio — e dove va messo il compromesso

La pagina proponeva due rimedi, *separare* e *rendere esplicito*. Dall'istanza sopra ne è emersa una
terza: **rendere il presupposto non necessario**. Implementando si è visto **quanto** paga — fondare la
copertura sull'identità del contenuto ha fatto cadere insieme, senza una riga per ciascuno, il bisogno
di riconoscere «quali voci sono recenti», il parsing delle intestazioni e tre casi limite distinti.

> Quando un presupposto non si può dichiarare onestamente, spesso il disegno che non ne ha bisogno è
> anche **più piccolo** di quello che lo gestisce.

Ma il presupposto è **tornato, ristretto**, e la restrizione è il vero contenuto: distinguere «voce che
precede la capacità» da «nessuna voce» richiede pur sempre di sapere che forma ha un'intestazione. Non
era eliminabile del tutto — era eliminabile **dalla logica principale** e confinabile nel **shim di
compatibilità**, dove è *derivato* dalla configurazione dell'ospite invece che cablato. Stessa sorte per
la data: sparita dal cuore, sopravvive solo nel shim, che per definizione deve riprodurre il
comportamento vecchio.

Non è un compromesso mancato: è **dove un compromesso va messo** — in un pezzo che si estingue da sé,
non nel meccanismo che resta.

## Perché è difficile da vedere

- **Nessuna delle due parti è sbagliata**, quindi né una code review della definizione né una del punto
  d'uso lo trova. Serve tenere in mente **entrambe insieme**, che è esattamente ciò che il riuso invita a
  non fare.
- **Il presupposto non è scritto.** `iter_pages` non dichiarava «e quindi ciò che escludo non è
  linkabile»: era una conseguenza tacita del filtro. Un presupposto tacito non si eredita
  consapevolmente.
- **Il sintomo compare lontano.** Il `lint` sbagliava su una pagina che non c'entrava; l'agente si
  fermava prima di iniziare.
- **Peggiora con la qualità del riuso.** Più l'artefatto originale è buono e generale, più è invitante
  riusarlo, e più i suoi presupposti sono impliciti perché «ovvi» nel contesto d'origine.

## La domanda da porsi

> Prima di riusare qualcosa, chiedersi **a quale domanda è stato costruito per rispondere** — e se è la
> stessa che sto ponendo io.

Se non è la stessa, le vie sono due, e **non** includono «adattarlo un po'»:

- **Separare** — due domande, due artefatti, ciascuno col proprio presupposto **dichiarato**. È il
  rimedio applicato a `iter_pages` / `iter_linkable_files`: il secondo nasce con un docstring che dice
  *quale domanda* risponde e perché non è la prima.
- **Rendere esplicito ciò che era implicito** — se l'artefatto resta uno, il presupposto va scritto nel
  punto di riuso. È il rimedio applicato alla frase del playbook: dal nome nudo alla **coordinata**
  (suffisso stabile + istruzione a cercare), che è il presupposto reso esplicito.

## Il segno che vale la pena presidiare

Quando un rimedio consiste nel **separare due cose che erano una**, quasi sempre non si sta aggiungendo
una capacità: si sta **nominando una distinzione che esisteva già** ed era rimasta implicita. La prova
è che il nome della nuova cosa suona ovvio dopo, e non prima — *pagine* contro *file linkabili*.

## Parentele

- [[host-agnostico-non-e-risolvibile]] — l'istanza 2 in dettaglio: cosa serve perché una coordinata
  resti tale quando cambia lettore.
- [[identita-per-presenza-o-per-contenuto]] — parente stretto e distinzione utile: là si sceglie **il
  criterio sbagliato** per una domanda che si sta ponendo davvero; qui il criterio è **giusto per la
  domanda originale** e viene portato su un'altra.
- [[deterministic-vs-judgment]] — accorgersi che due domande sono diverse è **giudizio**; una volta
  separate, entrambe tornano meccaniche.
- [[dogfood-fidelity]] — entrambe le istanze sono arrivate dal nodo *Acta*, non da noi: sono difetti
  che si vedono **usando**, non rileggendo.
