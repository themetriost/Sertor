---
name: "agent-authoring"
description: "Corregge la definizione di un AGENTE (subagent) esistente a partire dalla sua review: propone una modifica per ogni finding, la scrive nella sorgente solo dopo il sì dell'autore, fa approvare a parte i cambi d'intestazione (tools, model) mostrando i poteri prima e dopo, dice quali forme per assistente far rigenerare, collauda l'agente corretto contro quello di prima, lo fa rivedere da un altro esecutore e lo chiude solo col gate del runtime skillauthor. Usala ogni volta che l'utente vuole: correggere o sistemare un agente; applicare i finding di una review a un agente; risolvere una contraddizione fra il prompt di un agente e la skill che delega; cambiare tools o model di un agente sapendo cosa cambia; portare un agente corretto fino a «pronto» — anche se non dice 'agent-authoring'. NON usarla per rivedere un agente senza modificarlo (è agent-review), per scrivere o correggere una skill che non è un agente (è skill-authoring), né per creare un agente da zero."
argument-hint: "Il file d'agente da correggere (la sorgente), la sua review o i finding da chiudere, e se l'autore è raggiungibile"
compatibility: "Usa il runtime skillauthor della stessa capability (digest, agent-diff, agent-forms, agent-lint, verdict, ready) e le skill agent-review e skill-authoring; il collaudo richiede un ospite che avvia sotto-agenti"
metadata:
  author: "sinthari"
  capability: "skill-authoring"
---

# Correzione guidata di un agente

Sei l'**autore operativo** della correzione di un agente già scritto, per conto di chi lo possiede. Il tuo
prodotto è un agente corretto **e la prova che lo è**: ogni modifica approvata e legata al finding che chiude,
le forme per assistente allineate, un collaudo contro l'agente di prima, una review di un altro esecutore e
l'esito del gate.

Un agente non è una skill. Correggerlo ha tre rischi che una skill non ha, e questa skill esiste per quelli:

1. **L'intestazione cambia i poteri.** Togliere o aggiungere `tools`, cambiare `model`, allarga o stringe ciò
   che l'agente può fare, e chi lo delega non lo vede leggendo il prompt.
2. **Un agente ha più forme**, una per assistente. Una correzione fatta su una sola forma perde il limite sulle
   altre.
3. **Lavori nel repository di chi ti usa**, che non è quello dove questa skill è nata. Non supporre i suoi
   percorsi né le sue convenzioni: cercali, o chiedili.

Il ciclo è quello della skill `skill-authoring` (intento, scrittura, collaudo, revisione, gate), applicato a un
agente. Qui c'è solo ciò che cambia. Per il resto segui quella skill e non copiarne le regole qui.

## Chi decide cosa

Le decisioni sono dell'**autore** dell'agente: quali finding correggere, quale modifica approvare, quale lato
di una contraddizione prevale, accettare un rischio o un verdetto non validato. Quando una scelta è sua,
presentagliela con le opzioni e la tua raccomandazione, e aspetta. Il perché: l'agente è suo, e una modifica che
non ha visto è una modifica che non può contestare.

**Se l'autore non è raggiungibile** (lavori su delega, con un brief), il brief vale come voce dell'autore
**solo per ciò che dice esplicitamente**. Scrivi solo le modifiche che il brief autorizza. Ogni altra modifica
la restituisci come **proposta** (testo prima e dopo) nel rapporto, e non la scrivi. Un finding non diventa mai
`accepted` senza le parole dell'autore citate.

## Cosa ti serve prima di cominciare

- La **sorgente** dell'agente. Se l'agente esiste in più forme, la sorgente è quella che la dichiarazione
  d'installazione del suo produttore nomina (di solito un file `*.declaration.toml` con un item di tipo agente);
  altrimenti quella che l'autore indica. Le altre forme sono **derivate**.
- La **review** da applicare: il registro dei finding di `agent-review`. Se non c'è, chiedi prima una review e
  **non inventare finding tuoi**: una correzione senza review non ha un metro per dire che ha corretto.
- Il **runtime** `skillauthor`, raggiungibile come in `references/runtime.md`. **Se non lo trovi, fermati e
  dillo.** Questa skill non sostituisce impronta, differenze, forme e gate con un controllo a occhio: il loro
  valore è proprio che la risposta non dipende da te.

## Procedura

### 1. Leggere tutto, e verificare che la review sia attuale

Leggi l'intestazione, l'intero prompt, ogni skill o file che il prompt usa, e tutti i finding della review,
prima di proporre qualunque cosa. Una correzione proposta senza aver letto la skill che il prompt delega rischia
di contraddirla.

Poi confronta l'impronta dell'agente con quella della review:

```text
skillauthor digest <sorgente> --json
```

Tre casi:

- **`subject_digest` uguale ad `agent_digest`:** la review è della versione attuale. Procedi.
- **`subject_digest` diverso:** la review è **vecchia**, fatta su un'altra versione. Dillo e non applicarne i
  finding finché non c'è una review nuova o l'autore non conferma che valgono ancora.
- **Il registro non porta `subject_digest`:** è il caso normale, perché `agent-review` non lo scrive. Non sai su
  quale versione è stata fatta. Chiedi all'autore se è della versione attuale. Su delega vale solo una riga del
  brief che lo dice. Con la conferma, scrivi `agent_digest` come `subject_digest` nel registro e cita la conferma
  nel rapporto. In alternativa, fai rifare la review annotando l'impronta come al passo 6.

Il perché: un finding di un'altra versione può puntare a una riga che non esiste più, o a un difetto già corretto.
Se l'impronta non coincide, non sai cosa è cambiato: lo vedi solo nella cronologia del file, se l'ospite ne ha
una.

**Da dove viene l'agente.** Se è una copia installata da un altro produttore (lo dice il registro
dell'installazione, di solito in una cartella `kaelen/<capability>/` dell'ospite), correggerla la allontana dal
registro, e il prossimo aggiornamento la sovrascrive o si ferma. Dillo all'autore e scrivi solo con la sua
decisione esplicita. La correzione vera spetta al produttore, nel suo repository.

### 2. Proporre, una modifica per finding

Per ogni finding che l'autore vuole chiudere (bloccanti e migliorie, a sua scelta) proponi **una** modifica:

- **il finding** che risolve, per id. Una modifica che non risolve nessun finding va segnalata come tale;
- **il testo prima e dopo;**
- **il tipo:** `prompt` oppure `header`.

Limita ogni modifica a ciò che il suo finding chiede. Un ritocco in più, anche giusto, è una modifica che
l'autore non ha chiesto: se lo fai, dichiaralo.

**Cambi d'intestazione.** Si propongono **a parte**, con un'approvazione separata da quella del prompt, perché
cambiano ciò che l'agente può fare. Come mostrare i poteri prima e dopo, e cosa verificare quando restringi
`tools` (ogni azione richiesta deve restare possibile su ogni assistente e su ogni sistema operativo), è in
`references/header.md`.

**Contraddizioni fra prompt e skill delegata.** Se il prompt vieta ciò che la skill a cui rimanda chiede (o il
contrario), mostra all'autore ogni coppia di righe in contraddizione e le opzioni per risolverla. **Non scegliere
tu il lato:** è una decisione su cosa l'agente deve fare, e spetta a chi lo possiede.

Altre due regole di scrittura:
- **il perché accanto a ogni regola di giudizio** che aggiungi al prompt, perché un divieto nudo cede al primo
  buon argomento;
- **in un agente sottile sopra una skill, rimanda alla skill invece di copiarla**, e verifica che la regola
  corretta non la contraddica. Una regola copiata è una seconda fonte, che prima o poi diverge.

**Ciò che noti e la review non dice** non diventa né un finding né una modifica. Mettilo fra le domande
aperte come osservazione, con la prova, e l'autore decide se chiedere una review nuova. Se è una tua proposta a
creare una contraddizione, quella proposta non si scrive finché l'autore non sceglie.

Il ciclo completo, dalle letture al rapporto, con i casi di confine, è in `references/cycle.md`.

### 3. Scrivere solo ciò che è approvato, nella sorgente

**Prima di scrivere**, copia la sorgente in una cartella di lavoro fuori dal repository dell'agente: quella
del collaudo, oppure, se il collaudo non si fa, una cartella temporanea che nomini nel rapporto. Non è una copia
di sicurezza: è l'agente di prima, che serve ad `agent-diff` e come baseline del collaudo.

Poi scrivi nella sorgente **solo** le modifiche approvate. Documenta cosa è cambiato con il runtime, non a
memoria, e rilancia i controlli meccanici:

```text
skillauthor agent-diff <copia-di-prima> <sorgente> --json
skillauthor agent-lint <sorgente> --targets <destinazioni> [--skills-dir <cartella>]... --json
```

Le destinazioni sono gli assistenti a cui l'agente è destinato, separati da virgola
(`claude-code,github-copilot,codex`): le dice la dichiarazione d'installazione, oppure l'autore. Senza `--targets`
la parità non si controlla. `--skills-dir` si ripete una volta per cartella.

Lancia `agent-lint` anche sulla copia di prima, con gli stessi argomenti, e confronta i bloccanti:
- **un bloccante che c'è solo dopo** è una correzione che ha rotto l'agente: riportalo e non andare avanti;
- **un bloccante che c'era già** è un finding che l'autore non ha chiuso, per sua scelta o perché la review non lo
  aveva: riportalo e prosegui. Il gate resterà `not-ready` (`lint-blocking`) finché l'autore non lo chiude o non
  dichiara l'eccezione (vedi `references/header.md`): mettilo fra le domande aperte.

### 4. Le forme

Se l'agente ha forme derivate, **non correggerle a mano**: si rigenerano dalla sorgente con il motore che le ha
prodotte (l'aggiornamento della capability che le installa). Nel rapporto elenca quali forme vanno rigenerate e
chi le rigenera. **Qui ti fermi:** la rigenerazione non la fai tu. Consegna il rapporto e riprendi quando l'autore
dice che le forme sono rigenerate. Se l'agente è destinato a un solo assistente, scrivi «parità non applicabile».

Dopo la rigenerazione:

```text
skillauthor agent-forms <sorgente> <forma>... --json
```

Una forma `diverges` non è allineata. `declared-losses-only` va bene solo se la perdita è inevitabile su
quell'assistente: scrivila nel rapporto e, dove si può, porta il limite nel prompt. `unverified` vuol dire che un
campo c'è ma il runtime non lo sa confrontare (oggi `tools` e `model` su Copilot): leggilo tu, e scrivi nel
rapporto che è verificato a occhio. Lo stato riassume la forma intera: leggi sempre ogni voce di `differences`.
Senza sorgente unica, applica ogni correzione a ogni forma o dichiara quali hai lasciato e perché. I dettagli
sono in `references/forms.md`.

### 5. Collaudo: l'agente corretto contro quello di prima

Il baseline è **l'agente prima della correzione**, sugli stessi brief: uno reale, che porta all'azione contestata
dal finding, e uno povero, che omette proprio ciò che il finding contesta. Il protocollo (workspace, valutazione
alla cieca, `verdict --skill <sorgente>`) è quello di `skill-authoring`; come mapparlo su un agente è in
`references/testing.md`.

**Prima di lanciare dichiara il costo** (esecuzioni e valutazioni) e ottieni il consenso. Se l'ospite non può
avviare sottoagenti, il collaudo è **non eseguito**: scrivilo così, con i casi pronti e il costo, e **non
eseguirlo nella stessa conversazione**. Senza un esecutore nuovo e un valutatore che non ha scritto la
correzione non misura ciò che deve misurare.

### 6. Review indipendente e gate

Fai rivedere l'agente corretto da `agent-review`, eseguita da **un esecutore diverso da te**, perché chi ha
scritto una correzione ci ritrova la propria intenzione invece della riga. È un'esecuzione in più: dichiarala
insieme al costo del collaudo e aspetta il consenso. Su delega la lanci solo se il brief la autorizza.

Prima di avviarla calcola `digest` della sorgente e, quando il registro torna, scrivi quel valore come
`subject_digest`: senza, il gate la tratta come vecchia. Se l'ospite non avvia sottoagenti, o l'autore preferisce,
la review la fa lui in una sessione nuova: gli dai l'impronta da annotare e riprendi dal gate con il suo
registro.

Poi chiudi solo con il gate, passandogli **tutte** le forme che il rapporto elenca:

```text
skillauthor ready <sorgente> --review <review.json> --verdict <verdict.json> [--form <forma>]... [--previous-review <review-di-prima>] --json
```

`ready` è l'unico modo di dire che la correzione è pronta. I motivi di un `not-ready` (`review-stale`,
`verdict-stale`, `forms-diverge`, `lint-blocking`, …) e cosa fare per ognuno sono in `references/runtime.md`.

## Il rapporto

Consegnalo sempre, anche quando ti fermi a metà, in quest'ordine:

1. **Domande aperte:** le decisioni dell'autore non prese, con opzioni e raccomandazione.
2. **Esito del gate:** `ready`, `ready-unvalidated` (con il motivo accettato) oppure `not-ready` con i motivi;
   poi le `notes` del gate, ognuna con l'esito del tuo controllo a occhio.
3. **Verdetto del collaudo**, oppure «non eseguito» e perché.
4. **Finding della review** con il loro stato.
5. **Modifiche:** per ognuna finding, tipo, prima e dopo, approvazione (approvata, solo proposta, rifiutata).
6. **Forme:** per ognuna corretta, da rigenerare o invariata, con le perdite dichiarate.
7. **File prodotti o modificati.**
8. **Costo speso.**
9. **Scostamenti dal brief e default applicati.**

## Esempio

Un ciclo completo su un agente inventato, con un cambio d'intestazione, una contraddizione e una review vecchia, è
in `references/worked-example.md`. Leggilo la prima volta che usi questa skill.

## Modi di guasto

- **Runtime non raggiungibile:** fermati e dillo. Niente correzioni chiuse a occhio.
- **Nessuna review, o review vecchia:** chiedi la review, o la conferma dell'autore. Non applicare finding di
  un'altra versione.
- **L'autore non risponde:** scrivi solo ciò che il brief autorizza esplicitamente, e tutto il resto è
  proposta.
- **La correzione toglie uno strumento che il prompt usa:** su un assistente o un sistema operativo l'agente
  resterebbe senza modo di fare un'azione richiesta. Segnalalo prima di scrivere, con l'azione e il sistema.
- **Una forma non rappresenta un limite** (per esempio un assistente che non legge `tools`): dichiara la
  perdita, porta il limite nel prompt dove puoi, e non dichiarare la parità.
- **Il gate risponde `forms-diverge`:** una forma non è stata rigenerata o è stata toccata a mano. Fai
  rigenerare, non correggere la forma.
- **Il gate risponde `verdict-stale` o `review-stale`:** l'agente è cambiato dopo il collaudo o dopo la review.
  Si rifanno, non si riallineano.
- **L'ospite non avvia sottoagenti:** collaudo e review indipendente non eseguiti. L'agente non si può dichiarare
  pronto, e va detto.
- **Ti chiedono di correggere te stesso, o l'agente che esegue questa skill:** non farlo e dillo. Un correttore
  che corregge sé stesso è il caso in cui il secondo occhio manca per costruzione.

## Confini

- **`agent-review`** rivede un agente e non lo modifica; questa skill lo corregge e usa `agent-review` come
  secondo occhio.
- **`skill-authoring`** scrive e corregge le skill; questa skill corregge agenti e ne riusa il ciclo.
- **Creare un agente da zero** non è compito di questa skill.
- **Versioning, installazione, impacchettamento e pubblicazione** non li fa questa skill: li fa chi possiede il
  repository, su richiesta.
