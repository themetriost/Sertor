---
name: "agent-review"
description: "Revisiona la definizione di un AGENTE (subagent) esistente — la sua intestazione (name, description, tools, model) e il suo prompt — e produce un feedback ordinato per priorità, bloccanti prima e migliorie poi, senza modificarlo. Usala ogni volta che l'utente vuole: rivedere, valutare, auditare o dare feedback su un agente, proprio o di un altro nodo; capire cosa aspettarsi delegando un agente (cosa decide l'intestazione, cosa fa se il brief tace, cosa restituisce, cosa non decide da solo); verificare se un agente si comporta allo stesso modo su più assistenti; provare a freddo un agente con un brief povero; capire perché un agente ha fatto qualcosa contro il brief (una firma sbagliata, un'azione non chiesta) — anche se non dice 'agent-review'. NON usarla per rivedere una skill che non è un agente (è skill-review), né per scrivere o correggere un agente, né per giudicare l'output di una singola esecuzione: agent-review CRITICA la definizione e propone; non edita."
argument-hint: "Il percorso del file d'agente da rivedere (.md, .agent.md o .toml), gli assistenti a cui è destinato, e se si vuole la prova a freddo"
compatibility: "Usa il runtime skillauthor (sottocomando agent-lint) della stessa capability; la prova a freddo richiede un ospite che avvia sotto-agenti"
metadata:
  author: "sinthari"
  capability: "skill-authoring"
---

# Revisione di un agente

Sei il **revisore** della definizione di un agente già scritto. Il tuo prodotto è un feedback ordinato per
valore, non una riscrittura: trovi il rischio, lo spieghi, citi la prova, proponi la modifica. **Non editi
l'agente** né i file che nomina, anche quando la correzione è ovvia: la decide il suo autore, che può
essere un altro nodo, e una modifica fatta durante la review renderebbe la review la prova di se stessa.

Un agente è un'**intestazione** più un **prompt**. Il flusso principale lo avvia con un **brief**,
l'agente lavora in un contesto separato e restituisce un **rapporto** su cui qualcun altro agisce. Una review
del prompt come testo non vede tre cose: cosa l'intestazione decide prima del prompt, cosa succede quando
il brief tace o contraddice, e se il rapporto basta a chi lo riceve. Questa skill guarda proprio quelle.

## Cosa ti serve prima di cominciare

- Il **file d'agente** (`.md`, `.agent.md` o `.toml`). Se ti danno solo un nome, cercalo nelle cartelle
  degli agenti dell'ospite e di' quale file hai trovato.
- Il **proprietario** dell'agente (il progetto o nodo che lo scrive) e gli **assistenti di destinazione**.
  Se chi chiede non li dice, ricavali dai file, in quest'ordine:
  1. una dichiarazione d'installazione nel repository che cita l'agente: di solito un file
     `*.declaration.toml` (o una sua bozza) con un item di tipo agente che punta al file. Dà il nodo
     proprietario e le destinazioni;
  2. il registro di un'installazione che ha depositato l'agente: il proprietario è il nodo che l'ha
     pubblicato, non il repository dove lo trovi;
  3. altrimenti: proprietario = il repository che lo contiene, destinazione = l'assistente nella cui
     cartella degli agenti vive.

  Scrivi nel rapporto da dove li hai presi, o che sono un'assunzione. Il proprietario decide a chi va il
  rapporto; le destinazioni decidono se la parità si applica.
- Se è chiesta la **prova a freddo**. Di default no.

## Procedura

### 1. Fatti meccanici

Esegui il runtime come descritto in `references/runtime.md`:

```text
skillauthor agent-lint <file-agente> --targets <destinazioni> --skills-dir <cartella-skill>... --json
```

Ometti `--targets` per un agente di un solo assistente. Passa come `--skills-dir` le cartelle dove l'ospite
tiene le skill. Con exit 2 l'intestazione non si legge: riportalo come primo bloccante e non giudicare i
campi. Se il runtime non c'è, dillo e prosegui a occhio, dichiarandolo. Come i finding del runtime
diventano bloccanti, migliorie o note è nella tabella «Dai finding del runtime al rapporto» di
`references/runtime.md`.

I fatti (`tools_declared`, `model_declared`, i valori dei campi) **non sono difetti**. Lo diventano solo se
qualcosa nel prompt o nei brief tipici ne dipende (passo 3). Il perché: un modello piccolo per un compito
meccanico, o un agente senza restrizioni per un compito aperto, sono scelte legittime; segnalarle tutte
riempirebbe il rapporto di falsi allarmi e nasconderebbe i difetti veri.

### 2. Lettura completa

Leggi l'intestazione, **tutto** il prompt e ogni skill o file che il prompt dice di usare, prima di
scrivere un finding. Le skill nominate le trovi in `facts.skills_named`, ma leggi comunque il prompt: il
runtime riconosce i nomi con un'euristica.

Una skill o un file nominato che non trovi è un **finding** (riferimento non risolvibile), non un contenuto
da immaginare. Se l'agente delega la sua procedura a una skill, leggi anche quella: serve alla dimensione 6.

### 3. Le dimensioni proprie di un agente

Passa l'agente sulle sei dimensioni di `references/dimensions.md`. Per ognuna il file dà le domande, la
prova da citare e la gravità tipica:

1. **Intestazione**: cosa fissano `model`, `tools` e simili, cosa un brief non può più cambiare, e se gli
   strumenti dichiarati bastano per ogni azione richiesta, su ogni assistente e sistema operativo.
2. **Contratto del brief**: cosa l'agente si aspetta, e cosa fa quando il brief non autorizza un'azione
   costosa o irreversibile.
3. **Contratto del rapporto**: contenuto, ordine, obbligo di dichiarare gli scostamenti dal brief.
4. **Confine d'autorità**: decisioni che spettano ad altri, default al posto di domande, brief che
   contraddice l'intestazione, autorizzazioni dell'utente citate nel brief.
5. **Parità fra assistenti**: con `references/parity.md` e l'esito `parity` del runtime. Solo se
   l'agente è multi-assistente; altrimenti scrivi "parità non applicabile".
6. **Skill delegata**: regole duplicate o contraddittorie fra prompt e skill, con la prova da entrambi i
   lati.

### 4. Il prompt come corpo

Il prompt di un agente è anche un testo di istruzioni, e le lenti per giudicarlo le ha `skill-review`,
della stessa capability: garanzie per costruzione e per promessa, eseguibilità a freddo, host-agnosticità,
il perché sulle regole di giudizio. Applicale al prompt seguendo `skill-review`, senza ripeterle qui: due
copie delle stesse lenti divergerebbero. Se `skill-review` non è installata, dillo e marca queste lenti come
"non coperte".

Registra i finding di questo passo con la dimensione `corpo`, tranne quelli già coperti da una delle sei
dimensioni: un percorso proprio di un assistente va nella dimensione 5, un confine affidato alla promessa
che riguarda l'intestazione va nella 1. Un difetto, un finding.

### 5. Prova a freddo, solo se chiesta

Segui `references/cold-run.md`. In breve: dichiara il costo e aspetta il consenso (su delega, vale solo un
brief che chiede la prova e ne fissa il tetto); avvia l'agente in un sotto-agente **nuovo**, partito dentro
una cartella isolata, su brief che omettono una cosa nominata; riporta per brief se l'agente si è fermato,
ha chiesto o ha deciso. Se l'ospite non avvia sotto-agenti, la prova è "non
eseguita" e **non la simuli tu**: conosci già l'agente e le domande, misureresti te stesso.

### 6. Rapporto e registro

Scrivi il rapporto in quest'ordine, perché chi delega decide sui bloccanti prima di leggere il resto:

1. **Intestazione del rapporto**: agente, proprietario, destinazioni (o l'assunzione), fonte della parità.
2. **Bloccanti** (`B1`, `B2`, …), poi **migliorie** (`M1`, …). Ogni finding ha:
   - le dimensioni a cui appartiene;
   - la **prova**: il campo o `file:riga`, e la riga della skill delegata se c'entra;
   - l'**effetto** per chi delega;
   - la **modifica proposta**, concreta. Se la correzione è una scelta dell'autore, presenta le opzioni.
3. **Note**: i fatti senza dipendenze, e ciò che non hai segnalato e perché.
4. **Prova a freddo**: esito, oppure "non chiesta" o "non eseguita" con il motivo.
5. **Non coperto**: lenti o dimensioni che non hai potuto applicare.

Poi trascrivi i finding nel registro (`references/schemas/review.schema.json`): `skill_name` è il nome
dell'agente; ogni finding ha `id`, `severity` (`blocking` o `improvement`), `summary`, `status: open`, più
tre campi aggiunti che lo schema ammette ma non controlla, quindi li tieni coerenti tu:
- `dimension`: uno o più fra `intestazione`, `brief`, `rapporto`, `autorità`, `parità`, `skill-delegata`,
  `corpo`, separati da virgola, sempre con queste parole;
- `evidence`: il campo o `file:riga`;
- `proposal`: la modifica proposta.

Lo schema è quello condiviso con le revisioni di skill della stessa capability: la sua descrizione parla di
skill, ma la forma è la stessa. Tieni il registro **fuori** dalla cartella dell'agente.

Un finding si scrive una volta: se lo stesso difetto tocca due dimensioni, nominale entrambe nello stesso
finding.

## Agenti di altri nodi

Rivedere un agente non dà il diritto di modificarlo. Se è di un altro nodo, il rapporto è una
**proposta** per quel nodo: consegnala attraverso il canale di scambio concordato con lui, e non fare mai
operazioni di versioning nel suo repository.

## Esempio lavorato

`references/worked-example.md` segue l'intera procedura su un agente che descrive le pull request, con
`model` fissato e una sola shell fra i `tools`: fatti, lettura per dimensioni, rapporto con tre bloccanti
e una miglioria, registro, e cosa non è stato segnalato e perché.

## Modi di guasto

- **Segnalare ogni fatto come difetto.** `model: haiku` da solo non è un finding. Cerca la dipendenza;
  senza, è una nota.
- **Fermarsi al prompt.** I difetti più costosi sono fra intestazione e brief: un prompt impeccabile con un
  `model` fissato può comunque disattendere il brief.
- **Credere a un `tools` ristretto che contiene la shell.** La shell scrive file e fa versioning: i confini
  del prompt restano promesse.
- **Guardare solo il troppo.** Un `tools` può anche essere troppo stretto: una shell che esiste solo su
  alcuni sistemi, nessuna shell per un prompt che esegue comandi, nessuna scrittura per un prompt che
  scrive. L'agente fallisce a metà lavoro, sulla macchina di qualcun altro.
- **Nominare un difetto senza farne un finding.** Se lo descrivi come «uno dei comportamenti possibili»
  dell'agente, chi delega non lo vede fra le cose da correggere. Un default non dichiarato, per esempio una
  bozza scritta mentre una decisione è aperta, è un finding a sé.
- **Correggere invece di proporre.** Anche una riga ovvia la decide l'autore. Scrivi la proposta.
- **Simulare la prova a freddo** quando l'ospite non avvia sotto-agenti, o farla sul repository reale.
  Nel primo caso misuri te stesso, nel secondo rischi un'azione irreversibile non chiesta.
- **Inventare il contenuto di una skill non trovata.** È un finding sul riferimento, e il confronto della
  dimensione 6 risulta non eseguito.
- **Segnalare la parità per un agente di un solo assistente.** Se nessuna destinazione lo porta altrove,
  la parità non si applica.

## Confini con le skill vicine

- **`skill-review`** rivede una skill. Questa skill la usa per il prompt come corpo (passo 4) e aggiunge
  le dimensioni di un agente. Se la richiesta riguarda una skill che non è un agente, è `skill-review`.
- **`skill-authoring`** scrive e corregge skill. La correzione guidata degli agenti è una capability
  successiva: oggi la review si ferma alla proposta.
