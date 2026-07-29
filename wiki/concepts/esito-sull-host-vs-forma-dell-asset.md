---
title: L'esito sull'host, non la forma dell'asset
type: concept
tags: [testing, guardie, installer, asset, upgrade, fedelta, principio-xii, e10]
created: 2026-07-17
updated: 2026-07-27
sources: ["packages/sertor-install-kit/tests/unit/test_settings_merge_identity.py", "packages/sertor/tests/test_claude_hook_wiring_anchored.py", "requirements/debito-tecnico/epic.md", "wiki/log/2026-07-16.md", "wiki/log/2026-07-17.md"]
---

# L'esito sull'host, non la forma dell'asset

Una guardia può essere **verde e cieca**. È la lezione che E10-FEAT-031/032 hanno pagato sul campo, ed
è più generale degli hook: vale per **ogni artefatto che distribuiamo a un ospite**.

## Il buco

Testare un asset distribuito ha due punti d'osservazione possibili, e **non sono lo stesso**:

| Cosa si asserisce | Domanda a cui risponde | Cosa non vede |
|---|---|---|
| **La forma dell'asset** | «il file che spediamo dichiara il wiring giusto?» | se quel wiring **arriva** all'ospite |
| **L'esito sull'host** | «un ospite che aggiorna finisce nello stato giusto?» | — |

FEAT-031 aveva guardie verdi sulla **forma**: gli asset `settings*.json` dichiaravano correttamente il
path ancorato. Ma su un ospite che **aggiornava**, il merge duplicava la voce (Claude) o scartava la
nuova (Copilot) — vedi [[identita-hook-nel-merge]]. **Il fix non arrivava, e nessun test lo diceva**:
il difetto viveva esattamente **nello spazio fra le due colonne**.

## Perché è insidioso

- **La guardia verde dà una falsa quietanza.** Non un errore, un errore *taciuto*: la CI conferma
  «l'asset è giusto», e si legge come «gli ospiti ce l'hanno». Sono due affermazioni diverse.
- **Il difetto è invisibile all'install pulito.** Su un ospite nuovo il merge parte da zero e produce lo
  stato giusto — il bug esiste **solo lungo la transizione**, cioè solo per chi *ha già* la versione
  vecchia. Chi testa installando da zero non lo vedrà **mai**.
- **La forma è ciò che controlliamo, l'esito è ciò che conta.** L'asset è il nostro output; lo stato
  dell'ospite è il nostro *risultato*. Asserire l'output è comodo e sembra sufficiente.

## La regola

> Per ogni asset host-facing, una guardia deve asserire l'**esito su un host che aggiorna** — partendo
> dallo stato **vecchio**, non dal vuoto — non solo la forma dell'asset spedito.

Concretamente, le 10 guardie di `test_settings_merge_identity.py` partono tutte da un host **già
cablato in una forma precedente** e asseriscono lo stato **finale**: `.ps1`→`.py`, relativo→ancorato,
`cwd` aggiunto, host già duplicato che si **ricompatta**, tre generazioni che collassano, hook
dell'utente **preservato**, idempotenza al secondo giro.

## Il grado peggiore: la guardia che **benedice** il difetto (2026-07-25)

Una guardia cieca non vede. Ce n'è una peggiore: quella che **asserisce la forma sbagliata come
giusta**, con una motivazione scritta. Non tace il difetto — lo **certifica**, e chi passa dopo legge
una scelta deliberata dove c'è un errore.

Il caso (E2-FEAT-022). Il template `.mcp.json` spediva `uv run --directory .sertor`, che sposta la
working directory: il server MCP risolveva l'indice **dentro** `.sertor/` invece che nel progetto e
rispondeva `[]` a ogni query. A presidiarlo c'era questo test:

```python
def test_mcp_server_template_keeps_directory():
    """Sanity: the MCP server template legitimately keeps `--directory` (no path argument)."""
    assert '"--directory"' in body
```

Verde per mesi. La motivazione — «nessun argomento di path, quindi la cwd non conta» — è ragionata
sul **testo del template**, non su cosa fa il server su un ospite: nessun path relativo passa dalla
riga di comando, ma il server risolve comunque il corpus dal proprio ambiente, e prima che `Settings`
diventasse self-localizing quella risoluzione seguiva la cwd. Il nodo *Kaelen* ha avuto un RAG cieco
per un mese esattamente per quella entry.

**Il segnale che avrebbe dovuto insospettire c'era, ed era enorme:** la nostra documentazione diceva
in **cinque punti** — `getting-started`, `install`, `install-claude`, `troubleshooting`, `tutorial` e
persino l'asset `sertor-cli-reference.md` che *spediamo* — «usa `--project`, **mai** `--directory`».
Documentavamo il contrario di ciò che installavamo, e nessuna guardia confrontava i due.

Da qui due regole che estendono quella sopra:

> Una guardia che asserisce la **presenza** di una forma sta codificando una decisione. Scrivi
> **perché quella forma è giusta in termini di esito sull'ospite** — se la motivazione parla del
> contenuto del file e non di cosa succede a chi lo riceve, la guardia sta proteggendo sé stessa.

> Quando la documentazione e l'asset dicono cose diverse, **uno dei due è un difetto** — e senza
> qualcosa di deterministico che li confronti, vince quello che nessuno legge. *(È la richiesta del
> nodo Acta → **E13-FEAT-014**, guardia anti-drift della doc utente.)*

Corollario colto nello stesso lavoro: la correzione stessa ha rischiato di **reintrodurre il danno**.
Riconciliare l'entry `.mcp.json` per contenuto azzerava `SERTOR_CORPUS` al nome della cartella su ogni
upgrade — puntando il server a una collezione inesistente, cioè di nuovo un RAG che non risponde. Chi
ripara un artefatto d'ospite deve separare **ciò che possiede** (l'invocazione) da **ciò che è
dell'ospite** (la configurazione): falliscono in direzioni opposte, e una regola sola non può
governarli. Trovato eseguendo l'installer vero su un host usa-e-getta, non dai test unitari — stessa lezione
del «testa il componente reale, non solo il fake».

## Il perimetro della guardia: chiudere un caso credendo di chiudere una classe (2026-07-26)

Terzo modo di sbagliare una guardia, dopo il *cieca* e il *complice*: darle un **perimetro più stretto
della regola che difende**. La guardia è corretta, verde e onesta — copre però **il file in cui
l'errore è stato notato**, non l'insieme dei file che la regola tocca. Il caso si chiude, la classe no.

**Formulato dal nodo Acta**, che ce l'ha girato dopo averlo pagato: una loro regola `.gitignore`
versionava **due** file (`pyproject.toml` **e** `uv.lock`); un path assoluto della macchina di sviluppo
era stato trovato nel primo e la guardia che ne era nata copriva **solo quello**. Il difetto è
riemerso dal secondo. Come lo dicono loro: *«non era tornato — non era mai stato coperto per intero»*.

> Una guardia va posata sul **perimetro della regola** che protegge, non sul **file** in cui l'errore
> è stato notato.

**Ed è la nostra stessa storia, vista da un'altra angolazione.** La guardia contro `--directory`
esisteva già (`_FOOTGUN_BANNED_ASSETS`) e girava verde: il suo perimetro era una **lista di asset**, e
il template `.mcp.json` non solo ne era fuori — ne era **esentato per iscritto**, con motivazione. Due
difetti sovrapposti sullo stesso presidio: perimetro troppo stretto *e* l'esenzione che lo benediceva.
Domanda operativa che ne segue, da porsi quando si scrive una guardia: *quali file tocca la regola che
sto difendendo?* — e non: *dove ho visto il bug?*

*Verificato sul nostro caso gemello (2026-07-26): i due file `.acta` che la stessa regola versiona da
noi sono puliti, perché installiamo da git e non in editable. La classe non ci mordeva; la lezione sì.*

**Precisazione pagata scrivendo una guardia (2026-07-27): il perimetro va fatto combaciare in
ENTRAMBE le direzioni.** Applicando la lezione sopra ho scritto una guardia che **scopre** i propri
soggetti invece di elencarli — giusto contro il perimetro stretto — e l'ho fatta **troppo larga**: ha
raccolto ogni confronto di `schema` fra gli hook, quindi anche `distill-floor`, che ne confronta
legittimamente un altro (`wiki.distill_audit/1`). **Ha fallito su un file corretto.** Un perimetro
troppo largo non è più prudente di uno troppo stretto: il primo accusa l'innocente, il secondo assolve
il colpevole, e **entrambi fanno perdere fiducia nella guardia** — che è il vero danno, perché una
guardia di cui ci si fida poco viene disattivata. La domanda giusta ha due metà: *quali file tocca la
regola che sto difendendo* **e** *quali file NON tocca*.

*Corollario adottato nella stessa guardia:* se la scoperta non trova **nessun** soggetto, il test deve
**fallire**. Una guardia che ispeziona zero file passa a vuoto — ed è di nuovo *verde e cieca*, per la
via più banale.

## La guardia che si spegne da sola: quando *fail-open* rende invisibile il cambio di contratto (2026-07-27)

Quarto modo, e il più difficile da vedere, perché **non c'è nessun errore**: la guardia si **disattiva
da sola**, per una politica che è **giusta**, e il suo silenzio è indistinguibile dal via libera.

Un presidio che non deve mai intrappolare l'utente si progetta **fail-open**: se non riesce a
determinare la situazione, **lascia passare**. È la scelta corretta per i nostri hook — un gate di fine
turno che si inceppasse bloccherebbe la sessione per sempre. Ma la stessa politica, applicata alla
**negoziazione di contratto**, produce un esito che nessuno vorrebbe: i due consumatori installati
verificano l'identificativo di schema **per uguaglianza** (`wiki-guard.py:101`, `schema !=
"wiki.scan/1"` → `return`), quindi il giorno in cui il produttore bumpasse quell'identificativo, il
gate **non si romperebbe: sparirebbe** — su ogni ospite che ha aggiornato la libreria ma non gli asset.
Nessun errore, nessun breadcrumb, nessun `pending`. Solo una sessione che chiude sempre.

> `fail-open` è una risposta corretta a **«non so»**. Diventa un difetto quando la stessa risposta
> copre anche **«tu e io non parliamo più la stessa lingua»** — perché il secondo caso è un fatto
> noto, e un fatto noto va **dichiarato**, non degradato in silenzio (Principio XII).

**Distinzione da tenere ferma**, per non confondere questa sezione con le altre tre: là la guardia
**gira** e non vede (cieca · complice · perimetro stretto); qui **non gira affatto**, e la ragione per
cui non gira è la stessa che la rende sicura. Non è nemmeno il [[default-masked-defect]]: lì una
manopola spenta chiude il percorso e **maschera un bug**; qui non c'è un bug mascherato — c'è una
**capacità assente**, e l'assenza somiglia al successo.

**Conseguenza operativa** (adottata come vincolo in `specs/123-feat-045-ancora-derivata-scan`, FR-012):
finché esistono consumatori che si spengono su mismatch, l'evoluzione del contratto è **additiva** —
campi nuovi, identificativo invariato — e questo va **verificato da una guardia**, non affidato
all'attenzione di chi modifica. La domanda da porsi quando si tocca un contratto versionato è:
*se un consumatore vecchio incontrasse questa versione, se ne accorgerebbe qualcuno?*

**E la stessa domanda va posta al contrario**, perché libreria e asset **si aggiornano
separatamente**: un ospite può ritrovarsi con il **consumatore nuovo e il produttore vecchio**. Quel
consumatore non deve errare né tacere: deve **degradare al comportamento precedente**. Nel caso
concreto, la resa che nomina i file restituisce stringa vuota quando i campi nuovi non ci sono, così
un host non ancora ri-locckato vede il messaggio di prima invece di un errore — *verificato dal vivo,
non dedotto*. Le due metà insieme sono la regola completa: **il produttore non rompe i consumatori
vecchi, il consumatore tollera i produttori vecchi.** Presidiarne una sola lascia scoperta la metà
delle transizioni reali.

## Tre istanze dal campo (2026-07-24) — dove il punto cieco è l'installer

Quattro nodi della federazione — *VM-WorkingFolder*, *Sinthari*, *Kaelen*, *Acta* — hanno segnalato
indipendentemente lo stesso schema in tre forme. Non riguardano una guardia: riguardano **l'installer
stesso**, che è l'asset più host-facing che abbiamo.

**1. Il runtime non si muove, e l'upgrade dichiara successo.** Su *Sinthari*: stamp `.sertor-version`
a `0.1.5`, `sertor-core` nel lock fermo a **`0.1.0`** — un solo commit, quello d'installazione del 24
giugno, sopravvissuto a **tre** upgrade tutti riusciti. Causa: dipendenza senza vincolo di versione e
sorgente git **senza ref**, quindi `uv` non ha alcuna ragione di ri-risolvere il commit. L'upgrade
sposta gli **asset** e conclude di aver spostato tutto. Come lo riassume Sinthari: *«non è un
incidente della 0.1.5, è il comportamento normale dell'upgrade su host già installati, che non era
stato visto perché niente lo dichiara»*.

**2. Il comando pubblicato non è mai stato eseguito.** L'avviso dell'auto-updater suggerisce
`uvx --refresh sertor`, che fallisce perché risolve il pacchetto root, il quale non fornisce quella
console-script. Il testo è stato scritto e revisionato, mai **lanciato** su un host. Vedi
[[auto-update-version-check]].

**3. Una configurazione rotta sopravvive a ogni upgrade.** Su *Kaelen*, un `.mcp.json` con
`--directory` invece di `--project` ha reso il RAG **cieco per un mese** — ogni query `[]`,
indistinguibile da un corpus povero — e l'installer **salta** quel file perché «già registrato»:
ragiona per **presenza**, non per **contenuto**. La configurazione sbagliata è quindi *immune* agli
aggiornamenti.

**Una quarta istanza, trovata correggendo le prime tre (2026-07-24).** Il test che presidiava
l'avviso d'aggiornamento asseriva `"​`sertor upgrade`" in r.stdout`: cioè che il messaggio
**contenesse quella stringa**, non che il comando **funzionasse**. È rimasto verde per mesi mentre il
comando falliva su ogni host. Una guardia sulla forma del messaggio non poteva accorgersene — e quel
test era, formalmente, la copertura di quel comportamento. Ora pinna il frammento
`#subdirectory=packages/sertor` e **vieta** la forma nuda.

**Il filo comune.** In tutti e quattro i casi qualcosa di nostro era **formalmente corretto** — l'asset,
il testo, la registrazione — e l'**esito sull'host** era sbagliato. Nessuna sarebbe emersa da un test
sulla forma; tutte sono emerse da nodi che hanno **eseguito** ciò che spediamo. Il rimedio proposto da
*Sinthari* è la regola di questa pagina in una riga: l'upgrade deve riportare **la versione
effettivamente risultante, letta dal runtime**, non «ho fatto».

> **La causa ricorrente, generalizzata:** in due delle tre istanze qui sopra il meccanismo che
> avrebbe dovuto aggiornare non ha fatto nulla perché *«c'era già qualcosa»* — l'installer salta la
> `.mcp.json` registrata, l'upgrade non tocca un pin che esiste. È un pattern a sé, con una terza
> istanza fuori dall'installer (l'idempotenza dell'osservabilità): vedi
> [[identita-per-presenza-o-per-contenuto]].

## La misura, finalmente (2026-07-29): *testiamo l'installazione, spediamo aggiornamenti*

Questa pagina è del 17/07 e per dodici giorni è rimasta una **tesi**. Il 29/07 è diventata un
**conteggio**, contando i riscontri della federazione dal 16/07 — 20 riscontri, ~14 difetti reali:

| Dove sta il difetto | Quanti |
|---|---|
| installer · upgrade · pin · version-check | **7** |
| hook (freschezza, duplicazione) | 3 |
| wiki tooling (scan · gate · lint) | 3 |
| asset distribuiti | 1 |
| **core (retrieval, memoria)** | **1** |

**Un difetto su quattordici nel prodotto; tredici nella superficie di consegna.** E i test stanno
dall'altra parte: 1385 sotto `tests/`, quasi tutti sul core.

**La forma esatta del punto cieco**, che è il contributo nuovo: uno smoke end-to-end **esiste**, gira in
CI su quattro matrici, ed è onesto — ma **installa su un host pulito**. Non esiste alcun test che parta
dalla **release precedente** e aggiorni. E tutti e sette i difetti dell'installer **richiedono
un'installazione preesistente più vecchia** per manifestarsi: il pin che non si muove, il comando
d'upgrade rotto su chi pinna, gli hook duplicati al ri-cablaggio, `--directory` conservato perché
«c'era già», il present-divergent che blocca fix già rilasciati, il falso *behind*.

> Un'installazione da zero non può vederne **nessuno**, per costruzione. Testare l'**esito su un host
> che aggiorna** non è una raffinatezza di questa pagina: è **l'unico** modo in cui quei difetti
> diventano visibili prima dell'ospite.

E chiude il cerchio sul perché li trova sempre un nodo a valle: **nemmeno il dogfood aggiorna** — il suo
runtime insegue HEAD con un re-lock, non passa mai da versione a versione (terzo limite di
[[dogfood-fidelity]]). L'unico che esegue la cosa che spediamo è chi la riceve.

Rimedio tracciato come **E15-FEAT-012**: smoke di **upgrade** come gate di **rilascio**. Sui difetti in
mano ne avrebbe intercettati **cinque su sette**.

## Parentele

- È il complemento di [[dogfood-fidelity]]: quella chiede *«giriamo su ciò che gira un ospite?»*,
  questa chiede *«ciò che spediamo ci arriva davvero, anche a chi aggiorna?»*. Entrambe difendono
  la stessa cosa da lati diversi — e il dogfood, da solo, non basta come prova: il bug FEAT-032 è
  stato colto da un **re-install reale** e confermato da un **nodo indipendente** (Noetix), perché il
  nodo che scrive il fix è un teste contaminato.
- È [[constitution|Principio XII]] «Fail Loud» applicato ai **test**: un path che fallisce in silenzio
  è il difetto; una guardia che non guarda dove il silenzio accade lo **istituzionalizza**.
- La ragione per cui il difetto è emerso dal **campo** e non dalla suite è la stessa già vista con
  l'adapter Chroma (FEAT-004 memoria): **un test fedele a metà del contratto nasconde i bug** — lì il
  fake accettava metadata che il componente reale scartava, qui la guardia accettava un asset giusto
  su un host che non lo riceveva.

## Riferimenti

- Origine: E10-FEAT-032 (merge `ddbfb27`/PR #192, 2026-07-17) — meccanismo in [[identita-hook-nel-merge]].
- Scoperta: re-install reale sul dogfood (2026-07-16), **non** dai test — che erano tutti verdi.
