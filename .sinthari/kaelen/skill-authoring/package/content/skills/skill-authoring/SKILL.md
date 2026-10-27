---
name: "skill-authoring"
description: "Scrive o modifica una skill (SKILL.md + allegati) e la porta fino a «pronta da distribuire»: chiarisce l'intento con l'autore, scrive applicando subito le regole di Sinthari (corpo host-agnostico, allegati che viaggiano, il perché accanto a ogni regola di giudizio), decide con l'autore cosa spostare in un runtime, collauda la skill contro un baseline con un valutatore che non l'ha scritta, la fa rivedere da skill-review e la chiude solo col gate del runtime `skillauthor`. Usala ogni volta che l'utente vuole: creare una skill nuova (per sé o per un altro workspace); modificare o correggere una skill esistente; applicare i finding di una revisione; collaudare una skill con casi di prova; capire se una skill vale più di un agente senza skill; preparare una skill da distribuire — anche se non dice 'skill-authoring'. NON usarla per rivedere una skill senza modificarla (è skill-review), per scrivere il codice di un runtime, né per impacchettare o pubblicare."
argument-hint: "Cosa vuoi: «crea una skill che…» oppure «modifica la skill <cartella> applicando <revisione>»; dove sta (o deve stare) la cartella sorgente"
compatibility: "Richiede il runtime `skillauthor` (vedi references/runtime.md) e la skill skill-review. Il collaudo richiede che l'ospite possa avviare sottoagenti; l'ottimizzazione della description funziona solo su Claude Code"
metadata:
  author: "sinthari"
  capability: "skill-authoring"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

`$ARGUMENTS` è la richiesta dell'autore: una skill da creare (l'idea, il compito, chi la userà) oppure una
skill da modificare (la cartella, più di solito i finding di una revisione), e la cartella sorgente dove la
skill vive o deve vivere.

## Cosa sei, in questo flusso

Sei l'**autore operativo** di una skill per conto di chi la vuole. Il tuo prodotto è una skill che un altro
agente, che riceve **solo** il corpo e gli allegati, sa eseguire bene, e che vale di più di un agente capace
senza la skill. Due cose ti distinguono da chi scrive una skill "a mano":

1. **Le regole di Sinthari le applichi mentre scrivi**, non le scopri dopo come finding. Sono in
   `references/sinthari-rules.md`: leggile all'inizio di ogni lavoro.
2. **Ciò che non richiede giudizio non lo decidi tu.** Lo decide il runtime `skillauthor` (lint, costo,
   verdetto, gate). Come si invoca sul tuo ospite è spiegato in `references/runtime.md`. Se il runtime non è
   raggiungibile, fermati e dillo, invece di sostituirlo con un controllo a occhio: il suo valore è proprio
   che la risposta non dipende da te. Il runtime lo conosci **solo** attraverso `--help`,
   `references/runtime.md` e gli schemi in `references/schemas/`. Non leggere il suo codice, anche se ce l'hai
   a portata di mano: se un esito non si spiega con quei documenti, è un difetto della documentazione, e lo
   riporti nel rapporto come finding per chi mantiene il runtime.

Le decisioni sono dell'autore: scopo, perimetro, compromessi, accettare un rischio. Quando una scelta è
sua, chiedigliela con le opzioni e la tua raccomandazione. Non deciderla al posto suo, perché una skill
costruita su un'ipotesi sbagliata si riscrive da capo.

### Se l'autore non è raggiungibile

Capita quando lavori su delega, con un brief, o quando nessuno risponde. Il **brief** prende il posto
dell'autore solo per ciò che dice esplicitamente.

- **Le decisioni non le prendi:** intento, confini, approvare una modifica, accettare un rischio o un verdetto
  non validato, il tipo di un'asserzione. Vanno fra le domande aperte del rapporto, con le opzioni e la tua
  raccomandazione.
- **Puoi procedere** con ciò che non decide niente: leggere, scrivere una **bozza**, `skillauthor lint`,
  `skillauthor cost`. La bozza vale per `create`. In `modify` le correzioni che l'autore non ha approvato
  restano **proposte** nel rapporto (testo o diff), e non si scrivono nella cartella sorgente: quella skill
  è sua.
- **Il collaudo lo lanci solo se il brief lo autorizza e ne fissa il tetto di costo.** Altrimenti riporti il
  costo e ti fermi.
- **Il gate non lo forzi mai:** niente `--accept-unvalidated` e niente finding `accepted` senza le parole
  dell'autore nel brief.

Il perché: ciò che costa (le esecuzioni) e ciò che impegna l'autore (le accettazioni) non si annulla dopo,
mentre una bozza si butta.

## Il ciclo, in sei passi

Il ciclo è lo stesso per `create` e per `modify`; dove cambia, è detto.

### 1. Intento

- **`create`:** raccogli quattro cose, prima di scrivere una riga del corpo:
  1. **cosa fa** la skill;
  2. **quando deve attivarsi** (le frasi naturali di chi la userà);
  3. **cosa produce**;
  4. **dove finisce** rispetto alle skill vicine (cosa *non* fa, e quale skill lo fa).

  Se la conversazione contiene già il flusso da catturare, estrailo da lì e chiedi solo i buchi. Riassumi e
  fai **confermare** all'autore.
- **`modify`:** leggi **tutta** la skill (il `SKILL.md` e ogni allegato) e tutta la revisione da applicare,
  prima di proporre qualunque cosa. Una correzione proposta senza aver letto l'allegato che la contraddice è
  un nuovo difetto.

Chiedi anche dove vive la cartella sorgente e se esiste una copia installata. Non indovinarlo: i layout
cambiano da progetto a progetto.

### 2. Scrittura

Scrivi corpo e allegati applicando le regole di `references/sinthari-rules.md`. Le più facili da
dimenticare mentre si scrive:

- il **perché** accanto a ogni regola lasciata al giudizio dell'agente (un MUST senza motivo cede al primo
  buon argomento);
- gli **allegati che viaggiano**: ogni schema, contratto o riferimento citato sta dentro la cartella della
  skill e si cita per nome;
- **un esempio lavorato** e una sezione sui **modi di guasto**;
- nessuna regola dura che contraddica un passo operativo della stessa skill.

**`modify`:** proponi le modifiche **finding per finding**, ognuna con l'id del finding a cui risponde, e
scrivi **solo** ciò che l'autore ha approvato. La skill è sua, e una modifica non vista è una modifica che
non può contestare.

Poi:

```
skillauthor lint <cartella-skill>
```

Correggi ogni bloccante prima di proseguire. Se un bloccante è un falso positivo (per esempio una skill che
*parla* di percorsi di assistenti per spiegarli), non piegare il testo: dichiara l'eccezione in
`metadata.lint-allow`, col suo perché. Resterà visibile nell'esito.

### 3. Confine fra skill e runtime

Per **ogni** regola lasciata al giudizio dell'agente, chiedi all'autore: *si può garantire con un runtime,
uno schema o un controllo meccanico?* Come riconoscere i candidati (estrarre, verificare, nascondere,
tenere stato) e cosa produrre è in `references/runtime-boundary.md`.

- Registra ogni risposta fra le **decisioni di scrittura**: la regola, se è garantibile, cosa ha deciso
  l'autore e perché.
- Se la skill si appoggia a un runtime, il corpo ne riporta l'**invocazione pubblica**, e gli **schemi** di
  ingresso e uscita sono allegati.
- **Non scrivere il codice del runtime.** Un runtime nato dentro la stesura di una skill nasce senza test e
  senza contratto, cioè senza ciò che lo rende una garanzia. Lo scrive il processo di sviluppo del progetto.

### 4. Collaudo

Una skill si giustifica per ciò che **garantisce**, non per ciò che suggerisce: un agente capace senza la
skill il suggerimento lo trova da solo. Il collaudo misura proprio questo.

1. **Casi:** scrivi o aggiorna `<cartella-skill>/evals/evals.json` (schema in `references/schemas/evals.schema.json`). Di
   default sono 3 casi realistici, come li scriverebbe un utente vero. Ogni asserzione dichiara il suo
   tipo: `merit` (il risultato è migliore per l'utente) oppure `protocol` (la procedura è stata seguita).
   Ogni caso ha almeno un'asserzione di **merito**, perché le asserzioni misurano ciò che sai già di voler
   misurare, e il protocollo è quello che hai in mente mentre scrivi. Se la skill ha anche un agente
   delegato, i suoi casi stanno in un file a parte (per esempio `<cartella-skill>/evals/agent-evals.json`)
   e si passano ai comandi con `--evals`. Per i casi dell'agente:
   - usa un **workspace separato**, perché gli id dei due file possono coincidere e un `eval-<id>/` si
     sovrascriverebbe;
   - l'esecutore "con" riceve la **definizione dell'agente** oltre alla skill, altrimenti si collauda la
     skill e non l'agente. La definizione non sta dentro la cartella della skill: chiedi all'autore dove si
     trova, oppure cercala per il suffisso stabile `agents/<nome-agente>.md`;
   - il **gate** prende il verdetto della skill. Quello dell'agente va nel rapporto, con il suo esito così
     com'è.
2. **Costo:** esegui `skillauthor cost <cartella-skill>` e di' all'autore quante esecuzioni costerà, prima di
   lanciarle. Di default sono 3 casi × 1 giro, cioè 6 esecuzioni più 6 valutazioni. L'autore può aumentarlo
   o ridurlo. Digli anche che il costo vale **per un giro**: se dopo il collaudo la skill cambia (per
   esempio per correggere un bloccante della revisione), il collaudo si ripete.
3. **Esecuzioni:** ogni caso gira **due volte**, ognuna in un sottoagente nuovo:
   - **con la skill:** l'esecutore riceve il compito, il percorso della cartella della skill e l'istruzione
     di leggerla e seguirla;
   - **baseline:** riceve lo stesso compito e gli stessi file, e nessun riferimento alla skill.

   Disposizione di ogni giro, nel workspace, che sta **fuori** dalla cartella della skill:
   `<workspace>/eval-<id>/<with_skill|without_skill>/run-<n>/` con dentro `outputs/` (ciò che l'esecutore
   produce), `transcript.md` (i passi e il rapporto, li scrive l'esecutore) e, dopo, `grading.json`.
   - **File d'ingresso:** copia i file di ogni caso nel workspace e passa quei percorsi a **entrambe** le
     configurazioni. Mai percorsi dentro la cartella della skill: il baseline potrebbe risalire alla skill.
     Se il prompt del caso cita dei percorsi, riscrivili su quelli copiati, così il prompt non porta verso
     la skill.
   - **Copia installata:** se la skill sotto collaudo (o una sua versione vecchia, in `modify`) è installata
     sull'ospite, il baseline può attivarla da solo e il confronto si sporca. Esegui il baseline dove non è
     attivabile; se non si può, dillo nel rapporto come limite del confronto.

   Lancia tutte le esecuzioni insieme, così finiscono insieme.
4. **Valutazione, alla cieca:** ogni esecuzione la valuta un sottoagente **diverso da chi ha scritto**, con
   il prompt in `vendor/skill-creator/agents/grader.md`. Il valutatore non deve vedere né la skill, né questa
   conversazione, né la configurazione, e il percorso `with_skill`/`without_skill` gliela rivelerebbe.
   Quindi:
   1. copia `outputs/` e `transcript.md` di ogni giro in `<workspace>/blind/<id-opaco>/`, togliendo dal
      transcript i nomi delle configurazioni;
   2. tieni la mappa `id-opaco → eval/configurazione/giro` in un file che il valutatore non riceve;
   3. copia in `<workspace>/blind/` anche il prompt del valutatore e lo schema
      `references/schemas/grading.schema.json`, e passagli quei percorsi: se la skill sotto collaudo è
      proprio questa, un percorso dentro la skill lo porterebbe a leggerla;
   4. il valutatore lavora solo su `blind/<id-opaco>/` (transcript, `outputs/`) e scrive lì `grading.json`;
   5. riporti ogni `grading.json` nel suo `run-<n>/`.

   Il motivo: chi ha scritto un testo ci ritrova la propria intenzione invece della riga, e chi conosce la
   configurazione valuta l'etichetta invece dell'output. **Confine:** la cecità la tiene questa procedura,
   non il gate. `verdict` non può sapere che cosa ha visto il valutatore, e il transcript di un'esecuzione
   con la skill la nomina comunque, perché l'ha usata.
5. **Verdetto:**
   ```
   skillauthor verdict <workspace> --evals <cartella-skill>/evals/evals.json
   ```
   Il verdetto registra l'**impronta** della skill collaudata (`skill_digest`), cioè tutta la cartella della
   skill, `evals/` compreso. Se `--evals` non sta dentro la cartella della skill, indica la skill con
   `--skill <cartella-skill>`. Prima di lanciare le esecuzioni annota l'impronta con
   `skillauthor digest <cartella-skill>`, e dopo il verdetto controlla che `skill_digest` coincida: se è
   cambiata, qualcosa ha toccato la skill durante il collaudo, e il verdetto non descrive le esecuzioni.
   - **`validated`:** almeno un'asserzione di merito separa la skill dal baseline.
   - **`protocol-only` o `no-separation`:** dillo all'autore così come sono. Non presentarli come un
     successo. Spesso significano che l'asserzione era debole, oppure che la skill aggiunge poco a un agente
     capace. L'autore decide se rafforzare i casi, cambiare la skill o accettare.
   - **`incomplete`:** completa le valutazioni mancanti.
   - Le contestazioni del valutatore sul tipo di un'asserzione (`kind_challenges`) portale all'autore: è lui
     che decide l'etichetta.

**Se l'ospite non può avviare sottoagenti:** il collaudo è **non eseguito**, e così va scritto nel rapporto.
Non eseguire i casi da solo nella stessa conversazione per poi chiamarlo collaudo: senza baseline
indipendente e senza secondo occhio non misura ciò che deve misurare.

### 5. Revisione

Esegui la skill `skill-review` sulla skill. Poi trascrivi **ogni** finding in `review.json` (schema in
`references/schemas/review.schema.json`), con l'id e la gravità che gli ha dato la revisione:

- `severity`: `blocking` per i bloccanti, `improvement` per le migliorie;
- `status`: `open`, poi `resolved` quando la correzione è confermata, oppure `accepted` con
  `acceptance_reason`, solo se l'autore accetta il rischio.

`review.json`, `verdict.json` e il workspace stanno **fuori** dalla cartella della skill: tutto ciò che sta
dentro entra nell'impronta, e un file scritto lì renderebbe vecchio il verdetto.

Per i bloccanti torna al passo 2: in `modify` con una proposta per finding, in `create` correggendo. Dopo
le correzioni fai un **secondo giro** di revisione, in un nuovo `review.json` con `round` incrementato. È il
solo modo di sapere che un bloccante è risolto e non solo spostato. Una correzione cambia la skill, quindi
il verdetto del passo 4 non vale più: il collaudo si ripete (vedi `verdict-stale` al passo 6).

La trascrizione è il punto debole che il gate non può controllare: il gate si fida di ciò che scrivi qui.
Un bloccante trascritto come miglioria, o non trascritto, passa il gate. Per questo trascrivi tutto, così
com'è.

### 6. Chiusura

```
skillauthor ready <cartella-skill> --review <review.json> --verdict <verdict.json> [--previous-review <review del giro prima>]
```

È l'**unico** modo di dichiarare pronta una skill: non dire "è pronta" se il gate non ha risposto `ready`.
Sotto pressione ("va bene così, chiudi") il bloccante è la prima cosa che si salta, e il gate esiste per
questo.

- **`not-ready`:** riporta i motivi all'autore e torna al passo indicato.
- **`verdict-stale`:** la skill, o i suoi casi, è cambiata dopo il collaudo. Si rifanno le **esecuzioni e
  le valutazioni**, non solo `verdict`: rilanciare `verdict` sulle valutazioni vecchie certificherebbe una
  versione che nessuno ha collaudato. Se l'autore decide di non ricollaudare, la skill non si può dichiarare
  pronta, e va detto.
- **Verdetto `protocol-only` o `no-separation`:** la skill può chiudersi solo come `ready-unvalidated`,
  passando `--accept-unvalidated "<motivo>"`. Fallo solo se l'autore l'ha accettato esplicitamente, e nel
  motivo **cita le sue parole** fra virgolette: il gate controlla che un motivo ci sia, non da chi viene. Un
  esempio di motivo: la skill vale per il protocollo che garantisce, anche se il risultato lo troverebbe
  anche un agente senza skill.
- **Un finding bloccante** si chiude solo se l'autore lo risolve o lo accetta (`accepted` con motivo).

Dopo un `ready`:

1. **Copia installata:** se esiste, copia la sorgente e verifica con
   `skillauthor parity <sorgente> <copia>`.
2. **Description:** se l'autore lo chiede, ottimizzala. È un passo facoltativo, e funziona solo su Claude
   Code, perché gli script lanciano la sua riga di comando, e **non su Windows**, perché leggono l'output
   dei sottoprocessi in un modo che lì non è supportato. Altrove il passo è **non eseguibile qui**, e va
   detto. Come si lancia:
   - **casi di attivazione:** un file JSON con una lista di oggetti `{"query": "<frase dell'utente>",
     "should_trigger": true|false}`, circa metà che devono attivare la skill e metà che non devono. Lo
     scrivi nel workspace, fuori dalla cartella della skill, e lo fai approvare all'autore;
   - **comando:** dalla cartella `vendor/skill-creator/`, `python -m scripts.run_loop --eval-set <file>
     --skill-path <cartella-skill> --model <modello>`. `--model` è obbligatorio: chiedi all'autore quale
     usare. Aggiungi `--results-dir <workspace>` e `--report none`: senza, lo script scrive il rapporto in
     una cartella temporanea e apre il browser. Ogni domanda gira più volte, quindi di' all'autore il costo
     prima di partire;
   - **cosa scrive sull'ospite:** per misurare l'attivazione lo script crea un comando temporaneo nella
     cartella dei comandi di Claude Code del primo antenato della cartella corrente che ne ha una. Se
     nessun antenato ce l'ha, la crea sotto la cartella corrente, cioè dentro `vendor/` della skill. Dillo
     all'autore prima di lanciarlo, e alla fine controlla che non sia rimasto nulla;
   - **esito:** lo script propone una description, ma non la scrive nella skill. Se l'autore la accetta, la
     modifica cambia la skill e vale il passo 6: il verdetto diventa vecchio. Per questo, se l'autore la
     vuole, conviene ottimizzarla **prima** del collaudo.
3. **Rapporto:** consegnalo all'autore (forma sotto). Le decisioni di scrittura vanno nel wiki del progetto
   che scrive la skill, se ne ha uno; altrimenti restano nel rapporto, e lo dici. **Non** mettere le
   decisioni dentro la skill: servono a chi la mantiene, non a chi la usa.

## Il rapporto finale

Consegna sempre, anche quando ti fermi a metà, in quest'ordine:

1. **Domande aperte:** le decisioni che spettano all'autore e non sono state prese.
2. **Esito del gate:** `ready`, `ready-unvalidated` (con il motivo accettato) oppure `not-ready` (con i
   motivi).
3. **Verdetto del collaudo,** con le asserzioni che separano e le contestazioni del tipo; oppure "non
   eseguito" e perché.
4. **Finding della revisione,** con il loro stato.
5. **Decisioni di scrittura:** per ogni regola di giudizio, se è garantibile e cosa si è deciso; il confine
   skill↔runtime.
6. **File prodotti o modificati.**
7. **Costo eseguito:** esecuzioni e valutazioni.

## Modi di guasto

- **Il runtime `skillauthor` non si trova:** fermati e dillo. Non sostituire lint, verdetto o gate con un
  controllo a occhio.
- **L'ospite non avvia sottoagenti:** collaudo "non eseguito", mai "superato". Il gate risponderà
  `verdict-missing`: la skill non è pronta, e va detto.
- **`skill-review` non è disponibile:** la skill non si può dichiarare pronta (`review-missing`). Fa parte
  della stessa capability, quindi probabilmente è stata rimossa: dillo.
- **L'autore non è raggiungibile:** vedi la sezione apposita. Bozza, lint e costo sì; decisioni, collaudo
  non autorizzato e accettazioni no.
- **Il gate risponde `verdict-stale`:** la skill è cambiata dopo il collaudo. Rifai esecuzioni e valutazioni;
  rilanciare solo `verdict` non basta.
- **Il collaudo costa troppo per l'autore:** proponi meno casi, ma non meno di uno con un'asserzione di
  merito. Un collaudo senza merito misura solo il protocollo.
- **Il lint segnala qualcosa di legittimo:** eccezione dichiarata in `metadata.lint-allow` con il perché,
  mai testo piegato per zittire il controllo.
- **La skill appartiene a un altro progetto:** produci le proposte e i file nella cartella indicata, ma non
  fare operazioni di versioning nel loro repository. Lì si depositano file, nient'altro.
- **Il progetto non ha un wiki:** le decisioni di scrittura restano nel rapporto, e lo dici.
- **Una regola dura blocca un passo della skill che stai scrivendo:** è un difetto di scrittura. Riconcilia
  il testo prima della consegna, distinguendo i due casi.

## Esempi

Due cicli completi, una creazione e una modifica, sono in `references/worked-example.md`. Leggili la prima
volta che usi questa skill.

## Confini

- **`skill-review`** critica e non modifica; questa skill scrive e usa `skill-review` come secondo occhio.
  Se l'utente vuole solo un parere su una skill, è `skill-review`.
- **Il codice del runtime** non lo scrive questa skill.
- **Impacchettare e pubblicare** la skill sono passi successivi, fuori da questa skill.
