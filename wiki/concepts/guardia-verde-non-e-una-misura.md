---
title: Una guardia verde non è una misura
type: concept
tags: [guardie, verifiche, vacuita, fixture, misura, e15]
created: 2026-07-30
updated: 2026-08-07
sources: ["specs/125-smoke-di-upgrade/spec.md", "scripts/smoke.ps1", "scripts/smoke.sh", ".github/workflows/ci.yml", "wiki/log/2026-07-30.md", "tests/unit/test_vcs_worktree.py", "src/sertor_core/services/doctor.py", "src/sertor_core/composition.py"]
---

# Una guardia verde non è una misura

[[potere-retrospettivo-di-una-guardia]] chiede, **prima** di costruire una verifica: *applicata ai
difetti già avvenuti, quanti ne avrebbe fermati?* È la domanda di progetto. Questa pagina è la
domanda di **esecuzione**, e si pone dopo, a ogni giro:

> **In questa esecuzione, la guardia poteva diventare rossa?**

Un verde risponde a *«è andata bene?»*. Non risponde a *«ha guardato?»*. Sono due fatti diversi, e
solo il secondo dice se il verde vale qualcosa. Una guardia che non poteva fallire ha prodotto
esattamente lo stesso output di una che ha verificato tutto — e nessuno dei due output lo distingue.

## Le tre forme, tutte incontrate in un giorno

Il gate d'aggiornamento (**E15-FEAT-012**) le ha mostrate tutte e tre mentre veniva costruito, il che
è il dato interessante: non sono difetti esotici, sono il modo normale in cui una verifica smette di
verificare.

### 1. La fixture troppo povera per contenere il difetto

`health-green` esegue `doctor` dopo l'aggiornamento. Il percorso installava la release precedente e
aggiornava subito, senza mai **costruire un indice** — così `doctor` riportava `index_absent`, che era
vero della fixture e **di nessun host reale**: un ospite che aggiorna un RAG lo sta usando, quindi un
indice ce l'ha.

La guardia era rossa, ma per la ragione sbagliata. E la riparazione allettante — smettere di chiedere
a `doctor` dell'indice — avrebbe reso l'esito verde **e vuoto per sempre**. È *risolvere nascondendo*,
il terzo vincolo della regola del boy scout ([[step-ritual]]).

Il rimedio giusto ha aggiunto valore invece di toglierne: indicizzare **con la release precedente**
trasforma `health-green` in una domanda che lo smoke d'installazione non può nemmeno porre —
*la versione nuova legge ancora l'indice che ha scritto la vecchia?* Un manifest diventato illeggibile
costerebbe all'ospite il suo indice **in silenzio**.

#### La variante che si vede solo da due piattaforme (2026-07-31)

La forma 1 ha una versione più insidiosa: la fixture arriva nello stato del difetto **su un sistema
operativo e non sull'altro**, quindi la stessa riga di test è una misura di là e un verde vuoto di qua.

Il caso reale sta in [[ritual-check]]. Un test fissa la proprietà per cui un file le cui uniche
differenze sono le **terminazioni di riga** non entra nel perimetro dello step — la derivazione usa
`git diff` (content-aware) e non `git status` proprio per questo. La fixture scriveva la base con
`Path.write_text("x = 1\n")` e la modifica con `write_bytes(b"x = 1\r\n")`. Su Windows `write_text`
**traduce** `\n` in `\r\n`: base e modifica erano **byte-identiche**, non c'era alcuna differenza da
non-riportare, e il test passava avendo verificato nulla. Su Linux i due byte differiscono davvero, e
lì il test è diventato rosso — ma per una terza ragione ancora: senza attributi git, un cambio di
terminazioni **è** un cambio di contenuto (`--numstat` dà `1 1`), quindi riportarlo era corretto e
l'asserzione era semplicemente falsa.

Il difetto vero è a monte di entrambi gli esiti: **la fixture ereditava dall'ambiente la condizione
che il test dichiarava di verificare**, invece di dichiararla. La proprietà presidiata esiste solo dove
git *normalizza* (un `.gitattributes` come quello di questo repo, o `core.autocrlf`) — è lì che
`status` vede il file e `diff` no. Un test che non stabilisce quella configurazione non misura il
prodotto: misura la macchina su cui gira.

Due cose valgono per la prossima volta:

- **La matrice multi-OS non è ridondanza.** È stata l'unica cosa a rendere visibile la vacuità: il
  rosso su una piattaforma ha rivelato che il verde sull'altra non significava niente. Un gate
  eseguito su un solo sistema non poteva porsi la domanda.
- **Il rimedio ha la stessa forma della forma 2** — piantare la condizione e poi verificare che ci
  sia: la fixture ora committa il `.gitattributes` che attiva la normalizzazione e **asserisce che i
  byte su disco differiscano dal blob** prima di chiedere l'assenza dal perimetro. Se un domani quella
  differenza sparisse, il test diventa rosso invece di tornare verde a vuoto.

### 2. Le due fonti che concordano per costruzione

L'esito `version-derived-from-runtime` presidia il falso `behind` di **E2-FEAT-021**: lo stato
dichiarato veniva letto dallo *stamp* d'installazione invece che **derivato** dal lock del runtime.

Ma sulla fixture stamp e lock **dicono la stessa cosa**, perché lo stesso ref ha prodotto installer e
runtime. Un'asserzione letta su due fonti che già concordano passa **gratis**: non c'è modo di
sbagliare, quindi non c'è nulla da misurare. Il difetto vive esattamente nella condizione in cui le
due divergono — la condizione che la fixture non produce da sé.

Il rimedio è **piantare la condizione**: scrivere di proposito uno stamp che *resta indietro* rispetto
al runtime — cioè ricreare la situazione del campo — e poi chiedere quale fonte ha vinto. Cancella la
piantagione e l'esito **resta verde**: è per questo che a sorvegliarla c'è un test separato, il quale
diventa rosso proprio quando l'esito smetterebbe di significare qualcosa. *Quell'inversione è il punto.*

### 3. Il verde che non mostra cosa ha asserito

Un run verde stampava `1 passed` e nulla su **quali** esiti avessero retto. Ogni esito sta dietro una
precondizione (`.sertor/` esiste? l'hook è stato depositato?) e stampa un `n/a` quando manca: un run in
cui **tutti** sono finiti nel ramo `n/a` esce 0 e si legge **identico** a un run in cui tutti hanno
tenuto.

**E qui il primo rimedio è stato quello sbagliato — vale la pena registrarlo.** La diagnosi ovvia era
«`pytest` ingoia l'output su PASS» e la cura ovvia `-s`. Non ha cambiato nulla: l'output non lo
catturava `pytest`, lo catturava il **wrapper** (`capture_output=True`), che lo mostra solo in caso di
fallimento. Ma anche a diagnosi corretta, `-s` sarebbe stata la **cura sbagliata per la malattia
giusta**:

> **La vacuità non si cura rendendola visibile.** Rendere leggibile l'interno di una guardia sposta
> l'onere su qualcuno che *legga i log di un run verde* — cioè su nessuno. Il verde esiste apposta per
> non farli leggere.

Il rimedio vero **toglie il ramo silenzioso**: il wrapper esige ora ogni esito **per nome**, e va rosso
se un esito manca dall'output — vacuo e fallito diventano lo stesso stato, che è l'unico modo perché
qualcuno se ne accorga. `-s` resta, ma declassato al suo ruolo onesto: rendere leggibile la prova
**dopo**, non produrla.

La classe resta più grande della cura: **una verifica di cui non si può guardare l'interno è
indistinguibile da una assente** — la tesi stessa per cui il gate esiste, applicata al gate.

## La quarta forma: la guardia misura una procura, e la procura non è la domanda

Le tre sopra sono nate insieme, costruendo il gate d'aggiornamento. La quarta è arrivata dal campo
(nodo **Vestiger**, 2026-08-07) e ha una radice diversa: qui la guardia **poteva** diventare rossa, la
fixture è reale, l'output è leggibile. Il verde è perfettamente valido — **di un'altra domanda**.

`sertor-rag doctor` riporta `mcp pass (registered=True)` su un host dove il server MCP **non parte**.
L'affermazione è vera: il server *è* scritto in `.mcp.json`. Ma chi lancia `doctor` non sta chiedendo
*«l'ho registrato?»* — sta chiedendo *«funziona?»*, e fra le due c'è tutto lo spazio in cui il difetto
si è nascosto ([[difetto-che-solo-un-ospite-nuovo-puo-vedere]]: un `import` in cima al modulo che
esplode, quindi **nessun** tool servito).

**La forma è più insidiosa delle altre tre perché il verde non è vuoto: è pieno di un altro
contenuto.** Nelle forme 1-3 c'è sempre un momento in cui si può chiedere *«questa esecuzione poteva
fallire?»* e la risposta è no. Qui la risposta è sì — l'esito `mcp_not_registered` esiste e scatta — e
la domanda giusta è un'altra: *sto misurando la cosa, o un suo indizio?*

Due cose la rendono riconoscibile, e vale la pena tenerle:

- **Il confine è spesso dichiarato in chiaro, e passa per prudenza.** `read_mcp_registration` porta
  scritto *«Sola lettura: never starts the server»*, e `doctor.py` codifica che «MCP never has a
  critical outcome». Non è una svista: è un confine deciso, che nessuno ha più riletto dal lato di chi
  legge il verde. Le decisioni di non-guardare invecchiano peggio dei difetti, perché non falliscono.
- **La cura non è misurare tutto: è dire cosa non si è guardato.** Sulla riga accanto, `provider pass
  (probe=skipped)` fa esattamente la cosa giusta — dichiara la propria astensione. È la stessa
  disciplina del proxy dichiarato di [[ritual-check]], e la differenza fra le due righe dello stesso
  report è la lezione intera: *una procura dichiarata è onesta, una procura taciuta è una bugia
  strutturale*.

Vale anche la provenienza: Vestiger nomina **tre occorrenze in due giorni su tre strumenti diversi**
(il nostro `doctor`, l'`install` di Acta che dichiara `config: scritto` su una bacheca inesistente, e
un terzo caso). Quando la stessa forma esce da tre codebase indipendenti non è un incidente ripetuto —
è il modo normale in cui si scrive una verifica: *si misura ciò che è comodo misurare, e si chiama
come la domanda che si voleva porre*.

## Le due parenti già scritte, e il confine

- [[il-rimedio-ricade-nel-difetto]] — lì una riparazione riproduce ciò che ripara; qui una verifica
  smette di verificare restando verde. Stessa radice (chi interviene è la persona più esposta a fare
  lo stesso errore), superfici diverse.
- [[identita-per-presenza-o-per-contenuto]] — «esiste qualcosa di questo tipo?» invece di «esiste
  qualcosa di **giusto**?». Là il no-op sembra un successo; **qui il verde sembra una misura**. Stessa
  malattia (si controlla il segno invece della sostanza), superficie diversa: quella riguarda
  l'*idempotenza*, questa la *verifica*.
- [[product-plane-vs-fixture-plane]] — Principio XIII. La forma 1 obbliga alla cerimonia: prima di
  chiamare «buco di fixture» un fallimento, va escluso che sotto ci sia una domanda di prodotto.
  Nel caso reale l'esclusione è stata **positiva** e verificabile — `host-config-preserved` passava,
  quindi l'`.env` dell'ospite era preservato e il provider era rimasto quello di default per scelta
  dell'install, non per un tocco dell'upgrade.
- [[esito-sull-host-vs-forma-dell-asset]] — asserire l'**esito su un host**, non la forma dell'asset
  spedito. È il prerequisito: senza esiti su host non c'è nemmeno il rischio qui descritto, perché non
  si sta misurando niente di reale.

## La domanda da porsi, e quando

> **Se il difetto che questa guardia presidia fosse presente adesso, questa esecuzione lo vedrebbe?**

Va posta **quando la guardia diventa verde la prima volta**, che è il momento in cui nessuno la fa —
il verde chiude la questione invece di aprirla. Quattro risposte tipiche, e tutte e quattro sono un no:

- *«la fixture non arriva nello stato in cui il difetto vive»* → **forma 1**
- *«le fonti che confronto concordano già»* → **forma 2**
- *«non posso vedere quali asserzioni sono state eseguite»* → **forma 3**
- *«sì, ma sto guardando un indizio della cosa, non la cosa»* → **forma 4**

La quarta ha bisogno di una domanda sua, perché sfugge alla prima: non *«poteva fallire?»* (poteva),
ma **«la domanda a cui rispondo è quella che si sta ponendo chi legge?»**

E, sulla forma 3, una domanda in più — perché è quella su cui si sbaglia rimedio: *sto rendendo la
vacuità **visibile** o **impossibile**?* Solo la seconda è una riparazione; la prima delega a un
lettore che il verde ha appena congedato.

Il corollario operativo: **una guardia che al primo giro non trova niente, di solito non sta
guardando**. Il gate d'aggiornamento, al primo giro, ha trovato quattro difetti — tutti **in sé
stesso**, nessuno nel prodotto. È il segno che guardava davvero.
