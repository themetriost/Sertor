# Le dimensioni proprie di un agente

Un agente è un'intestazione più un prompt. Il flusso principale lo avvia con un **brief**, l'agente lavora
in un contesto separato e restituisce un **rapporto** su cui qualcun altro agisce. Le sei dimensioni qui
sotto guardano quello che la review del prompt come testo non vede: cosa decide l'intestazione prima del
prompt, e cosa succede ai due capi della delega.

Per ogni dimensione: le domande, la prova da citare, quando un fatto diventa finding, la gravità tipica.
La gravità è un punto di partenza: un difetto è **bloccante** quando chi delega, fidandosi del prompt,
otterrebbe un comportamento diverso da quello che si aspetta senza poterlo vedere; è una **miglioria**
quando il comportamento è giusto ma si regge su una cosa non scritta.

Indice: 1 Intestazione · 2 Contratto del brief · 3 Contratto del rapporto · 4 Confine d'autorità ·
5 Parità fra assistenti · 6 Skill delegata · Cinque difetti noti.

---

## 1. Intestazione e suoi effetti

L'ospite legge l'intestazione **prima** del prompt e del brief. Un campo che fissa un comportamento
vince su qualunque cosa il brief chieda, e chi delega non lo vede: il brief arriva, ma l'agente è già
configurato.

**Domande**
- Per ogni campo che cambia il comportamento (`model`, `tools` e simili): cosa fissa? Cosa, di
  conseguenza, un brief non può più chiedere?
- Senza `tools`, l'agente riceve **tutti** gli strumenti dell'ospite: scrivere e cancellare file, eseguire
  comandi, avviare altri agenti, usare strumenti esterni. Il prompt ne ha bisogno? Il prompt dice di non
  usarne alcuni? Un divieto nel prompt è una promessa; un `tools` ristretto è una costruzione.
- Un `tools` ristretto rende vero un confine **solo se nessuno strumento ammesso lo scavalca**. Uno
  strumento generale, come la shell, scrive file, fa versioning e lancia programmi: con la shell fra i
  `tools`, «non scrivo file» e «git solo in lettura» tornano promesse. Controlla ogni confine contro lo
  strumento più potente della lista, non contro quelli che il prompt nomina.
- Con `model` fissato: c'è qualcosa, nel prompt o nei brief tipici, che dipende dal modello? Un'attribuzione
  o una firma ("firma con il modello che ti è indicato"), una lunghezza di contesto, una capacità di
  ragionamento che il compito richiede.
- **Gli strumenti bastano?** Le domande sopra guardano il rischio di troppi strumenti; questa guarda
  quello opposto. Elenca le azioni che il prompt o la skill delegata richiedono: eseguire comandi,
  scrivere o modificare file, versioning, avviare altri agenti, usare strumenti esterni. Per ognuna c'è
  uno strumento dichiarato che la permette **su ogni assistente di destinazione e su ogni sistema
  operativo** (Linux, macOS e Windows)? Il perché: un agente a cui manca lo strumento non fallisce in
  modo visibile alla definizione; fallisce a metà del lavoro, sulla macchina di qualcun altro. Alcuni
  agenti di un altro nodo dichiaravano `tools: Bash, …` e non giravano su Windows senza bash, dove
  l'ospite espone la shell con un altro nome.
  - **La shell cambia nome col sistema.** Su Claude Code `Bash` è garantita su Linux e macOS,
    `PowerShell` su Windows: una sola delle due lascia scoperti gli altri sistemi (fonte: comportamento
    osservato su Claude Code e segnalazione di un altro nodo, 2026-10-22; da riverificare se l'ospite
    cambia). Questo caso il runtime lo vede (regola T, fatto `shell_tools`, vedi `references/runtime.md`),
    ma è un difetto solo se il prompt esegue davvero comandi.
  - **Ogni sistema, sempre.** Un agente deve funzionare su Linux, macOS e Windows, anche quando chi lo
    scrive o chi chiede la review dice che «gira solo su Linux». Non declassare per questo un finding
    sulla shell a nota o a miglioria. Il perché: un agente distribuito non sa dove girerà, e un'eccezione
    dichiarata per un sistema è proprio la strada da cui il problema rientra.
  - **Due shell, una sintassi.** Dichiarare `Bash` e `PowerShell` non basta se i comandi del prompt
    sono scritti per una sola delle due: pipe verso utilità Unix (`| grep`, `| head`), `$(…)`, heredoc,
    `&&` su una PowerShell vecchia. I comandi devono girare su entrambe le shell, oppure il prompt deve
    dire come scegliere la forma giusta per il sistema. Un comando che su un sistema non gira è
    un'azione senza strumento su quel sistema.
  - **Il caso che il runtime non vede**, perché richiede di leggere il prompt: un `tools` senza shell
    mentre il prompt chiede di eseguire comandi (un `git log`, un test, un'installazione); un `tools`
    senza strumenti di scrittura o modifica mentre il prompt chiede di scrivere un file; un agente che
    deve avviare altri agenti senza lo strumento per farlo. Se la shell c'è, può supplire alla scrittura,
    ma solo dove la shell c'è.
  - **Su Copilot** il vocabolario di `tools` è diverso e non l'abbiamo verificato: non dire che uno
    strumento manca lì, dichiara l'incertezza (vedi `references/parity.md`).
  - **Su Codex** `tools` non arriva: l'agente riceve tutti gli strumenti dell'ospite, quindi lì il
    rischio è il primo (troppi), non questo.

**Prova:** il campo (`model: haiku`) e la riga del prompt o del brief tipico che ne dipende. Per gli
strumenti che mancano: il campo `tools` (con `facts.shell_tools`, che per un agente senza shell ha
`declared` vuoto) e la riga del prompt che chiede l'azione.

**Quando è un finding.** I fatti meccanici (`tools_declared`, `model_declared`) da soli **non** sono
difetti: un modello piccolo per un compito meccanico è una scelta di costo, un agente senza `tools` per un
compito aperto è una scelta di semplicità. Diventano finding quando qualcosa ne dipende:
- `model` fissato **e** il prompt o il brief si aspettano un comportamento legato al modello → bloccante;
- un confine **dichiarato** nel prompt («leggi soltanto», «niente versioning», «non pubblicare»)
  che l'agente può scavalcare, perché `tools` manca o perché uno strumento ammesso lo permette (la shell,
  `Write`) → **miglioria**: la promessa c'è, la costruzione manca. La correzione tipica: scrivere il
  perché del confine e cosa fare se il brief lo contraddice, e restringere `tools` dove si può. Un confine
  **non dichiarato**, con un agente che può compiere azioni irreversibili → **bloccante**. La scala è la
  stessa per qualunque forma di `tools` (assente, ristretto con la shell, ristretto con `Write`). Il
  perché: la gravità dipende da cosa sa chi delega, non da quanti strumenti ha l'agente. Un agente che per
  il suo compito deve usare uno strumento generale non può rendere veri per costruzione i confini che
  quello strumento scavalca: un bloccante lì non si chiuderebbe mai.
  Un confine è **non dichiarato** quando il compito o la `description` lo implicano (un agente «di sola
  lettura», «che non modifica», un agente che non ha motivo di toccare git o di pubblicare) e il prompt
  non lo scrive, **e** l'azione che resterebbe aperta è vicina al compito: versioning per chi legge git,
  pubblicazione per chi prepara contenuti da pubblicare, cancellazione per chi lavora sui file. Non si
  chiede un elenco esaustivo di divieti: «può fare `rm`» non basta. Prova: la riga del compito che rende
  l'azione vicina, e l'assenza del divieto;
- un'azione richiesta dal prompt o dalla skill delegata senza uno strumento che la permetta, su almeno
  un assistente di destinazione o un sistema operativo (compreso un comando scritto per una sola delle
  shell dichiarate) → **bloccante**. Qui la dipendenza è l'azione stessa: chi delega si aspetta che
  l'agente la compia. Un agente senza shell e senza comandi nel prompt non ha niente da segnalare;
- una shell dichiarata che né il prompt né la skill delegata usano → **miglioria**, con la proposta di
  toglierla: è uno strumento in più che nessuno chiede. Non è un bloccante sulla shell mancante su un
  sistema, anche se il runtime lo segnala (regola T): manca uno strumento che non serve;
- se nessuna dipendenza c'è, riportalo come **nota** (fatto registrato), non come finding.

---

## 2. Contratto del brief

L'agente non può fare domande mentre lavora: tutto ciò che sa del compito è nel brief. Il prompt deve dire
cosa il brief contiene e cosa fare quando non lo contiene.

**Domande**
- Cosa il prompt si aspetta di trovare nel brief? Elenca le aspettative scritte.
- Il prompt **usa** qualcosa che il brief dovrebbe dare ma non lo elenca? (Per esempio legge "la cartella
  sorgente" senza averla chiesta.) Ognuna è un finding.
- Per ogni azione **costosa o irreversibile** che il compito porta l'agente a compiere — molte
  esecuzioni o sotto-agenti, operazioni distruttive di versioning, pubblicare o inviare all'esterno,
  cancellare — il prompt dice cosa fare quando il brief **non** la autorizza? Fermarsi, chiedere nel rapporto, o
  procedere con un limite dichiarato.

**Prova:** la riga che elenca il contenuto del brief; la riga che nomina l'azione costosa; l'assenza di una
riga per il caso del brief che tace.

**Gravità tipica:** un'azione costosa o irreversibile senza regola per il brief che tace → **bloccante**.
Due esecuzioni dello stesso agente, nella stessa situazione, possono fare cose opposte (una si ferma, l'altra
lancia dodici esecuzioni) e nessun testo dice quale è giusta. Un'aspettativa usata ma non elencata →
miglioria, bloccante se senza di essa l'agente scrive nel posto sbagliato.

---

## 3. Contratto del rapporto

Chi riceve il rapporto deve poter agire senza rifare il lavoro. Se il formato del rapporto è lasciato alla
virtù del singolo agente, la qualità dipende dall'esecuzione.

**Domande**
- Il prompt definisce **contenuto e ordine** del rapporto? Prima le cose su cui chi delega deve decidere
  (domande aperte, esito), poi il resto.
- Chi delega potrebbe agire sul rapporto **senza rileggere** tutto il lavoro? Per esempio: file toccati,
  comandi eseguiti con esito, cosa è stato verificato e come.
- Il prompt obbliga a dichiarare gli **scostamenti dal brief**: cosa non è stato fatto, o è stato fatto
  diversamente, e perché? Senza questo obbligo, uno scostamento (una firma diversa da quella chiesta) si
  scopre per caso.
- Il rapporto arriva anche quando l'agente si ferma presto?

**Prova:** la sezione del prompt sul rapporto, o la sua assenza.

**Gravità tipica:** nessun obbligo di dichiarare gli scostamenti → **bloccante** se l'agente ha confini
che possono contraddire il brief (dimensione 4), altrimenti miglioria. Nessun formato → miglioria.

---

## 4. Confine d'autorità

Alcune decisioni non sono dell'agente: dell'utente, dell'autore, di chi delega. Il prompt deve dirle, e dire
cosa fa l'agente quando ne incontra una.

**Domande**
- Quali decisioni il prompt riserva a qualcun altro? Elencale.
- Quali decisioni il compito comporta che il prompt **non** nomina, e quindi lascia al giudizio
  dell'agente senza dirlo? (Scegliere fra due interpretazioni del brief, accettare un rischio, scegliere un
  nome o una destinazione.)
- Il prompt permette di applicare un **default** dove la decisione è di un altro? È accettabile solo se il
  prompt chiede anche di dichiarare il default e di restituirlo come domanda aperta nel rapporto.
- Il caso più comune è **implicito**: la procedura (del prompt o della skill delegata) permette di
  andare avanti, per esempio di scrivere una bozza, mentre una decisione è ancora aperta. Una bozza contiene
  per forza una scelta su quel punto. Se nulla obbliga a marcarla come provvisoria e a restituirla come
  domanda, è un default non dichiarato: **segnalalo come finding a sé**, non solo come uno dei comportamenti
  possibili dell'agente. Guarda in particolare i passi «puoi procedere con…» e «scrivi una bozza».
- Se il brief **contraddice** le regole dell'agente o la sua intestazione (chiede una firma diversa da
  quella che l'intestazione impone, chiede un'operazione che il prompt vieta), cosa prevale? E come lo
  dichiara l'agente?
- Se il brief **cita un'autorizzazione dell'utente** ("l'utente ha approvato il merge"), il prompt dice
  come trattarla? L'agente non può verificarla: il prompt deve dire se basta il brief, e che il rapporto la
  riporta come citata.

**Prova:** le righe che riservano decisioni; il punto del compito in cui una decisione non nominata cade;
l'assenza di una regola per brief contraddittori.

**Gravità tipica:** un default al posto di una decisione altrui, senza obbligo di dichiararlo →
**bloccante** (chi delega non può contestare un bivio che non vede). Nessuna regola per il brief che
contraddice l'intestazione → **bloccante** se l'intestazione fissa qualcosa che i brief toccano (dimensione
1), altrimenti miglioria.

---

## 5. Parità fra assistenti

Solo se l'agente è destinato a più assistenti. Il dettaglio di cosa porta ogni assistente è in
`references/parity.md`.

**Domande**
- Quali campi dell'intestazione una destinazione **perde** (`dropped`) o legge con un **altro significato**
  (`different`)? Il limite che quel campo esprime è ripetuto nel prompt, dove sopravvive?
- Il prompt contiene percorsi, nomi di strumenti o invocazioni propri di un solo assistente?

**Prova:** l'esito di parità del runtime (`parity.entries`, finding P e H) più la riga del prompt.

I percorsi e le invocazioni propri di un assistente nel prompt si registrano **qui**, in questa dimensione,
anche quando li trovi applicando le lenti di `skill-review` al prompt: un difetto, un finding.

**Gravità tipica:** un confine di sicurezza espresso **solo** in un campo che una destinazione perde (per
esempio `tools` senza scrittura su un assistente che lo scarta) → **bloccante**. Un campo `different` senza
conseguenze sul confine → miglioria o nota.

Se l'agente è per un solo assistente: scrivi "parità non applicabile" e non segnalare campi mancanti
altrove.

---

## 6. Skill delegata (agente sottile)

Solo se il prompt rimanda la propria procedura a una skill ("la tua procedura è la skill X").

**Domande**
- Il prompt **duplica** regole della skill? Una regola copiata è una seconda fonte: prima o poi diverge.
- Il prompt **contraddice** la skill? L'agente si troverà a scegliere quale seguire.
- Le regole proprie del prompt (quelle che la skill non ha, tipicamente sulla delega: brief, rapporto,
  autorità) sono coerenti con i passi della skill?

**Prova:** le due righe, una nel prompt e una nella skill.

**Gravità tipica:** contraddizione → **bloccante**. Duplicazione identica → miglioria (sostituirla con un
rimando). Skill delegata non trovata → **bloccante** sul riferimento, e il confronto risulta non eseguito.

---

## Cinque difetti noti (2026-10-20, il quinto 2026-10-22)

Esempi reali, utili per tarare la gravità.

1. **`model` fissato che prevale sul brief.** Un agente di versioning con `model: haiku` ha firmato i
   commit con il modello dell'intestazione, mentre il brief chiedeva un'altra firma. Il prompt non diceva
   cosa prevale né obbligava a dichiarare lo scostamento. Dimensioni 1, 3, 4.
2. **`tools` non dichiarati.** Due agenti sottili sopra una skill ricevevano tutti gli strumenti,
   compreso avviare altri agenti, mentre i loro prompt dichiaravano confini ("non fai versioning", "non
   installi"). Confini per promessa, non per costruzione. Dimensione 1.
3. **Comportamento non scritto quando il brief tace.** Senza autore raggiungibile, un esecutore ha
   lanciato un collaudo di dodici esecuzioni, un altro si è fermato a chiedere. Il prompt non diceva cosa
   fare con un'azione costosa non autorizzata dal brief. Dimensione 2.
4. **Default applicato al posto di una domanda.** Davanti a una decisione dell'autore, l'agente ha scritto
   un default provvisorio invece di restituirla come domanda; il prompt non chiedeva di dichiarare un
   default. Dimensione 4.
5. **Una sola shell.** Alcuni agenti di un altro nodo dichiaravano `tools: Bash, …` ed eseguivano
   comandi: su Windows senza bash non giravano, perché lì l'ospite espone la shell come `PowerShell`.
   Erano stati scritti su macchine con bash. Dimensione 1.
