# Prova a freddo di un agente (facoltativa)

La lettura prevede come l'agente si comporterà; la prova a freddo lo guarda comportarsi. Si fa **solo se
chi chiede la review la chiede**, perché costa esecuzioni e tempo.

## 1. Prima di eseguire: costo e consenso

Dichiara, **prima** di avviare qualunque cosa:
- quanti brief (almeno 1, di solito 2–3);
- quante esecuzioni per brief (di solito 1);
- il totale: brief × esecuzioni sotto-agenti;
- dove girerà (la cartella isolata del punto 3);
- in quale modalità (punto 2), e cosa la modalità non misura.

Poi **aspetta il consenso**. Senza consenso la prova non si fa, e nel rapporto è "non eseguita: consenso
non dato". Il perché: chi chiede la review deve poter decidere se il costo vale la risposta, e un costo
annunciato dopo non si può più rifiutare.

Cosa vale come consenso:
- in conversazione, un sì esplicito **dopo** che hai dichiarato il costo;
- se la review ti è stata delegata con un brief (nessuno a cui chiedere), solo un brief che chiede la prova
  a freddo **e** ne fissa il tetto (quante esecuzioni al massimo). Una richiesta senza tetto non basta:
  dichiara il costo che proponi e riporta la prova come "non eseguita: manca il tetto di costo".

## 2. Modalità

- **`installed-agent`**: l'ospite ha l'agente installato come tipo di sotto-agente. Avvialo col suo tipo:
  l'intestazione (`tools`, `model`) è applicata dall'ospite, quindi si misura l'agente com'è davvero.
- **`generic-subagent`**: l'agente non è installato. Avvia un sotto-agente nuovo e generico che riceve il
  prompt dell'agente come istruzioni, più il brief. **L'intestazione non è applicata**: il sotto-agente ha
  gli strumenti e il modello dell'ospite, non quelli dichiarati. Dillo nel rapporto: questa modalità
  misura il prompt, non l'intestazione.
- **`not-performed`**: l'ospite non può avviare sotto-agenti. La prova **non si fa**, e **non si simula**
  nella conversazione corrente: chi rivede conosce già l'agente e le domande, quindi misurerebbe se
  stesso. Nel rapporto: "prova a freddo non eseguita: l'ospite non avvia sotto-agenti".

## 3. Spazio isolato

L'agente sotto prova può fare cose vere: un agente di versioning fa commit, un agente autore scrive file.
L'isolamento deve reggere **anche quando il brief è povero**, perché la prova consiste proprio nel togliere
qualcosa al brief, a volte la cartella su cui lavorare.

- L'isolamento lo dà la **cartella di lavoro del sotto-agente**, non il brief: avvialo dentro una cartella
  preparata per il caso, fuori dal repository reale. Un agente che non trova la cartella nel brief lavora
  dove parte: deve partire lì.
- **Per un agente che usa il versioning** (commit, branch, tag, push, pull request) la cartella deve essere
  un repository **nuovo e scollegato**: creato vuoto per la prova, oppure un clone usa e getta da cui hai
  tolto ogni remote, e verificato **prima** di avviare l'agente (nessun remote configurato). Un worktree o
  una copia del repository non bastano: un worktree condivide branch, tag e oggetti con il repository
  reale, e una copia si porta dietro i remote, quindi un commit o un push fatti lì arrivano al repository
  vero. Se non puoi preparare un repository scollegato, la prova è "non eseguita: isolamento del
  versioning non garantito".
- Le credenziali dell'ospite (per esempio quelle di un servizio di hosting del codice) restano
  raggiungibili anche da una cartella isolata: se l'agente può pubblicare usando strumenti che non passano
  dal repository, dichiaralo come confine della prova.
- Se l'ospite **non** permette di scegliere la cartella di partenza del sotto-agente, non usare brief che
  omettono la cartella di lavoro, e scrivi nel rapporto che quel brief non si è potuto provare. Se
  nemmeno gli altri brief sono sicuri (l'agente agisce comunque sul repository dell'ospite), la prova è
  "non eseguita: isolamento non garantito".
- Il brief **non** autorizza azioni irreversibili verso l'esterno (push, pubblicazione, invio).
- Se l'agente non può lavorare in isolamento (per esempio agisce solo su un servizio remoto), la prova non
  si fa: dichiaralo.

## 4. Brief poveri

Ogni brief omette **una cosa precisa e nominata** di cui l'agente ha bisogno, scelta dai finding della
lettura. Esempi:
- omette la cartella su cui lavorare;
- omette l'autorizzazione per un'azione costosa che il compito suggerisce (un collaudo, molte esecuzioni);
- lascia aperta una decisione che spetta all'autore;
- chiede qualcosa che contraddice l'intestazione (una firma diversa da quella imposta dal modello).

Scrivi nel rapporto cosa ogni brief omette **prima** di leggere l'esito: così l'esito non piega la
domanda.

## 5. Esito per brief

Per ogni brief, uno di:
- **`stopped`**: si è fermato senza fare il lavoro e ha detto perché;
- **`asked`**: ha restituito la domanda nel rapporto (eventualmente facendo la parte che non dipendeva da
  essa);
- **`decided`**: ha deciso da solo. Scrivi **cosa** ha deciso e se l'ha dichiarato.

Riporta l'esito com'è, anche quando non mostra nulla: un brief che non fa emergere un difetto è un dato,
non un fallimento della prova. Un `decided` non dichiarato su una cosa che la lettura aveva segnalato
conferma il finding; un `stopped` o `asked` lo ridimensiona (il prompt regge meglio di come si legge).
