---
title: LLM-facing retrieval contract
type: concept
tags: [retrieval, code-graph, api-design, agent-context, contratto, design-note]
created: 2026-07-24
updated: 2026-07-24
sources: ["src/sertor_core/services/retrieval.py", "src/sertor_core/engines/hybrid.py", "src/sertor_core/services/eval/runner.py", "src/sertor_core/domain/ports.py", "src/sertor_mcp/server.py"]
status: in-review
---

# Come presentare a un LLM il risultato di una ricerca eterogenea

> **Nota per chi legge da fuori.** Scritta per essere **valutata senza conoscere il sistema da cui
> nasce**: il §1 stabilisce il contesto necessario, da lì in poi il ragionamento è autoportante. I
> riferimenti al progetto d'origine sono confinati in fondo. Chi rivede attacchi il §8.
>
> **Stato:** quattro giri di revisione esterna. Il corpo espone la **posizione corrente**; la
> *Storia della revisione* in fondo traccia come ci si è arrivati, con l'esito di ogni rilievo —
> accolto, respinto o rinviato. **Il prossimo passo non è un altro giro di prosa: sono le misure di
> §8.**

## 1. Il problema, in astratto

Un sistema di retrieval espone a un **agente LLM**, tramite un'interfaccia a tool, due famiglie di
interrogazione **strutturalmente diverse**:

**A — Retrieval per similarità.** La query diventa un vettore; si cercano i frammenti (*chunk*) più
vicini, eventualmente fusi con un indice lessicale tipo BM25. Restituisce una **classifica** di
frammenti con un punteggio. Il corpus contiene sia codice sia documentazione.

**B — Navigazione strutturale.** Un grafo costruito dall'AST risponde a domande esatte: *dove è
definito X* · *chi lo chiama* · *cosa chiama* · *quali documenti lo menzionano*. Restituisce un
**insieme** di riferimenti (path, riga, nome qualificato), senza punteggio di similarità.

Le due famiglie sono **ortogonali**: rispondono a domande di natura diversa. Oggi l'agente le
raggiunge con tool separati e sceglie lui.

**La domanda:** se si vuole una singola chiamata che restituisca entrambi i segnali, **che forma deve
avere la risposta** perché un LLM la sfrutti bene — e non ne tragga conclusioni false?

Non è una questione estetica. La forma determina cosa l'agente può concludere, e soprattutto **cosa
può concludere per sbaglio**.

## 2. Il vincolo di fondo: le due cose non hanno la stessa forma

|  | Risultato di similarità | Risultato di grafo |
|---|---|---|
| **campi** | testo · path · id-chunk · tipo · punteggio | path · riga · genere · nome qualificato |
| **natura** | **classifica** — l'ordine *è* il segnale | **insieme** — l'appartenenza è il segnale |
| **completezza** | top-k arbitrario, tagliato | esaustivo per costruzione |
| **semantica del vuoto** | nessun chunk abbastanza simile | il simbolo non esiste nel grafo |

> **Fondere le due liste in una classifica unica è un errore di categoria.** Gli elementi di grafo
> possono avere ordinamenti fondati — centralità, distanza dall'ingresso, frequenza di chiamata — ma
> **non un punteggio commensurabile con quello del ramo di similarità**: non esiste una scala comune.
> Ordinarli insieme richiede di inventarla. Il numero inventato non misura niente, ma l'LLM lo
> tratterà come se misurasse.

La regola generale, tesi centrale della pagina:

> **Etichetta, non fondere.** Segnali indipendenti si consegnano **separati e nominati**. Collassarli
> in un unico numero o in un'unica lista distrugge informazione e ne fabbrica di falsa.

**Un'istanza controllata, dichiarata.** Il sistema d'origine inventa un punteggio in un punto: il
motore di valutazione assegna `score = 1.0` agli hit di grafo per farli entrare in una struttura che
un punteggio lo pretende. La difesa «è confinato al percorso di misura» **non basta**: alcune
metriche di quel percorso pesano il rango (MRR), e hit di grafo *mescolati* ai risultati di
similarità con punteggio massimo dominerebbero l'ordinamento, facendo misurare una politica di
fusione inesistente in produzione. La difesa valida richiede **due condizioni**:

1. **instradamento totale** — per una domanda strutturale la lista contiene *solo* hit di grafo;
2. **consumo del solo path** — l'ordine viene dal grafo, il punteggio è un segnaposto mai letto.

Entrambe valgono nel sistema d'origine, ma **una verifica una tantum non è una garanzia**: sono
invarianti che un refactoring può rompere in silenzio, e vanno **asserite da un test**, non
riverificate a mano quando qualcuno se lo ricorda.

## 3. Cinque proprietà che il contratto deve avere

### 3.1 Le relazioni valgono; il punteggio dipende dal motore

Un LLM non ha una calibrazione per `0.83` contro `0.79`. Sa invece usare benissimo un'etichetta di
**relazione**: «qui è **definito**» · «qui viene **chiamato**» · «questo documento lo **menziona**».
Il contenuto informativo di un hit di grafo **è il tipo di arco**; una lista piatta di path lo butta
via.

**Sul punteggio, la distinzione che serve** è fra due letture:

| Lettura | Cosa richiede | Utilizzabile? |
|---|---|---|
| **assoluta** — «`0.83` è buono?» | la distribuzione di *questa* query su *questo* corpus | **no** |
| **relativa entro una lista** — «il primo stacca?» | un'idea di quanto sia grande un gap *su quella scala* | **dipende dal motore** (sotto) |

La lettura relativa non è priva di calibrazione: per dire che `0.91` stacca `0.34` serve sapere che
ampiezza abbia un gap significativo su quella scala, e le similarità coseno si addensano in bande
strette. Il guadagno rispetto alla lettura assoluta è **di grado, non di natura**.

**E il grado dipende dal motore** — al punto che la decisione sul payload deve esserlo anch'essa:

| Motore | Cos'è il punteggio | Decisione sul payload |
|---|---|---|
| **vettoriale puro** | una **similarità**; la forma della distribuzione ha il senso descritto sopra | **esporlo** |
| **ibrido a fusione per rango (RRF)** | un valore derivato dalle **posizioni** nelle liste sorgente, in banda stretta e meccanica (`0.0323, 0.0320, 0.0161`) | **non esporlo**: è in larga parte l'ordine, trasformato — e l'ordine è già nella lista |

Sotto RRF il numero misura **il grado di accordo fra le gambe del retrieval**, che è informazione
reale ma **diversa** dalla confidenza, e in buona parte già implicita nell'ordinamento. Esporlo
invita a una lettura che non regge. Se quell'accordo si vuole consegnare, va consegnato per quello
che è — un'**etichetta di accordo** (`concorde` / `solo-densa` / `solo-lessicale`), non un numero che
somiglia a una similarità.

> **Contratto di comparabilità** (quando il punteggio è esposto). Confrontabile **solo entro la
> propria lista**. Mai fra flussi diversi, mai fra query diverse, mai come misura assoluta.

**Dove vive la dichiarazione: nella descrizione del tool, non nel payload.** È una proprietà *del
tool*, costante in ogni risposta; un campo ripetuto a ogni chiamata è documentazione travestita da
dato, pagata in token. Con un vincolo implementativo che ne discende: **il motore è configurazione di
deployment**, quindi la descrizione del tool va **generata dalla configurazione**, non scritta
staticamente — altrimenti dichiara un contratto che l'istanza non rispetta.

E con un limite da non nascondere:

> **Dichiarare l'ambito non lo impone.** I punteggi di due flussi restano fianco a fianco, e nulla
> impedisce all'agente di confrontarli ignorando l'etichetta. Che la dichiarazione basti è
> **un'affermazione empirica** (n. 9 di §8), non una garanzia strutturale. **Se cade, la risposta
> coerente con la tesi di questa pagina è togliere il punteggio dal payload, non normalizzarlo:**
> normalizzare ogni lista al proprio massimo non rende vacuo il confronto cross-flusso, lo rende
> *fuorviante in una direzione precisa* — tutte le liste partirebbero da `1.00`, e il vertice di un
> flusso debolissimo apparirebbe pari a quello di un flusso forte. Sarebbe il fallimento di §3.3
> riprodotto dal rimedio, proprio nell'ipotesi (agente che ignora le dichiarazioni) in cui il rimedio
> scatta.

**Il segnale di confidenza è un numero diverso, e va detto.** Un indicatore per-flusso «questi
risultati sono deboli, valuta di astenerti» è il complemento giusto. Nel sistema d'origine esiste
come soglia opzionale, **spenta di default** e visibile **solo nei log**, mai nel payload — quindi va
*costruita*, non cablata. E porta con sé un'asimmetria che il contratto deve dichiarare: sotto
motore ibrido la soglia è applicata al **pool denso prima della fusione** (perché il punteggio finale
è RRF, non una similarità), quindi **il numero su cui si decide l'astensione e il numero eventualmente
esposto nel payload sono su scale diverse**. Consegnarli affiancati senza dirlo è esattamente il tipo
di silenzio che questa pagina combatte.

### 3.2 L'ordine è un segnale, perché l'attenzione non è uniforme

La posizione nel contesto influenza il peso che il modello dà al materiale. L'ordine dei blocchi è
parte del contratto, non una scelta di presentazione.

**Ordine proposto:** materiale **esatto e corto** (definizioni: path e riga) → il **perché** (chunk
di documentazione) → il **come** (chunk di codice) → le relazioni estese (chiamanti, chiamati). Gli
ancoraggi esatti danno al modello uno **scheletro** su cui appendere il materiale fuzzy che segue.

> **Questo interlaccia i flussi — ed è compatibile con il §6, che l'interlacciamento lo scarta.** La
> distinzione è l'**unità minima che non si spezza**: il §6 respinge l'interlacciamento **degli
> item**, dove frammenti di provenienza diversa si alternano senza che il lettore sappia cosa sta
> leggendo. Qui si alternano **blocchi etichettati**, ciascuno che dichiara la propria natura. Il
> blocco etichettato è l'atomo; l'ordine dei blocchi è libero, l'ordine *dentro* un blocco no, e un
> item non compare mai fuori dal proprio blocco.
>
> Ne segue che **la resa smembra il bundle per-simbolo** di §5.1: le definizioni vanno in testa, i
> chiamanti in coda. Struttura e ordine sono assi diversi — la struttura serve al contratto dati,
> l'ordine alla lettura — ed è una scelta di serializzazione (§5.3), non una contraddizione.

*Nota onesta:* è la proprietà **meno solida** delle cinque. Previsione plausibile, non misurata (§8).

### 3.3 L'assenza deve essere tipizzata — la proprietà più importante

Tre stati vuoti, tipicamente indistinguibili, che **devono** essere distinti:

| Stato | Significato | Cosa deve concludere l'LLM |
|---|---|---|
| **non tentato** | nessun punto d'ingresso individuato | «non lo so, non ho guardato» |
| **tentato, vuoto** | il simbolo non è nel grafo | «non c'è» — conclusione **legittima** |
| **non tentabile** | grafo non costruito, dipendenza mancante, errore | «non lo so, lo strumento è rotto» |

Se il ramo grafo restituisce una lista vuota perché la libreria di navigazione non è installata,
l'LLM conclude *«nessuno chiama questa funzione»* e **lo afferma all'utente**.

> È il fallimento peggiore che un contratto di retrieval possa produrre: **fabbricare
> un'affermazione falsa** e farla sembrare fondata. Non è un errore dell'LLM — è il contratto che gli
> ha mentito.

Un'API che distingue già le due semantiche di assenza **deve preservare quella distinzione
nell'aggregazione**: è il punto in cui il collasso avviene più facilmente e più silenziosamente.

**Il fallimento parziale è il caso normale.** Con più punti d'ingresso e quattro tipi di relazione,
lo stato misto è la regola: chiamanti calcolati ma indice delle menzioni non disponibile; simbolo A
risolto e simbolo B no. Uno stato unico per l'intero ramo grafo **ricrea la non-distinguibilità che
questa proprietà vieta**. Lo stato scende al **singolo simbolo** e alla **singola relazione** (§5.1).

### 3.4 Il troncamento va dichiarato — ma solo gli insiemi possono mentire

«Chi chiama X» su un simbolo popolare restituisce decine di risultati. Mostrarne 8 senza dirlo fa
rispondere all'LLM *«ci sono 8 chiamanti»*: un'affermazione falsa prodotta dal contratto.

**La proprietà però non è uniforme sui due tipi di risultato**, e la differenza è sostanziale:

| Tipo | Il taglio mente? | Perché |
|---|---|---|
| **insieme** (relazioni di grafo) | **sì** | l'insieme è esaustivo per costruzione: troncarlo senza dirlo fa passare un sottoinsieme per il tutto → serve `{mostrati, totali}` |
| **classifica** (flussi di similarità) | **no** | il top-k è **costitutivo**: su un corpus intero *ogni* documento ha una similarità, «totali» non ha senso insiemistico e la classifica non finge esaustività |

Quindi il campo di troncamento appartiene alle relazioni di grafo, non ai flussi di similarità —
non per svista, ma perché per una classifica non c'è nulla di vero da dichiarare. Resta valido il
**budget separato per flusso**: se i tre condividono un unico top-k, uno affama gli altri in modo
dipendente dalla query, e la stessa domanda posta due volte restituisce composizioni diverse senza
che nulla lo segnali.

### 3.5 Ogni elemento deve essere citabile, in un formato solo

Riferimento stabile e verificabile: `path#chunk` per i frammenti, `path#simbolo` per i nodi di grafo.
Uniforme, così l'agente cita allo stesso modo qualunque cosa abbia usato.

## 4. Il costo del fan-out

Le cinque proprietà dicono **che forma** dare ai flussi, non **se convenga mandarli tutti**. Il
contesto dell'agente è la risorsa scarsa attorno a cui ruota l'intero §3.2, e un fan-out paga su
**tutte** le query, incluse quelle che del ramo strutturale non avevano bisogno.

**Diluizione del contesto** — il costo dominante. Materiale non pertinente non è neutro: occupa
posizioni, spinge il materiale pertinente verso il centro (dove l'attenzione è minore) e offre
appigli a ragionamenti fuori strada. Su una query concettuale, un elenco di chiamanti è rumore che
*sembra* segnale, perché è preciso e strutturato.

**Latenza** — la voce meno preoccupante con un grafo in memoria già caricato: lookup, non calcolo. Da
misurare comunque, non da assumere.

**Token** — contenibile per costruzione, se i limiti per relazione sono nel contratto (§3.4) e il
ramo grafo consegna prevalentemente **puntatori** (§5.2).

**La mitigazione strutturale.** Con una selezione precisa dei punti d'ingresso, il costo è
**auto-correlato alla rilevanza**: nessun ingresso individuato ⇒ `not_attempted` ⇒ costo prossimo a
zero. Una query concettuale che non implica alcun simbolo non paga quasi nulla. Questo **alza la
posta sulla qualità della selezione** (§7): un ingresso troppo generoso aggancia simboli irrilevanti
proprio dove il beneficio è nullo. La parsimonia dell'ingresso è una proprietà del contratto.

**Conseguenza sulla validazione:** il test non può misurare solo il beneficio. Va **simmetrizzato**
(§8).

## 5. La forma proposta

### 5.1 Lo schema

```
docs  : { items         : [ {path, chunk_id, text, score?, corroborated_by?: [qualname]} ]
          low_confidence: bool }              score? presente solo sotto motore vettoriale (§3.1)
code  : { ... }                               idem

graph : {
    entry_points : [ {symbol, source: symbol_table_match | extracted_from_query
                                    | expanded_from_code | caller_supplied} ]
    symbols      : [ { qualname,
                       definitions : {items: [ {…, corroborated_by?: [chunk_id]} ],
                                      status: …, truncated: {mostrati, totali}},
                       callers     : { … },
                       callees     : { … },
                       docs        : { … } } ]
    status       : ok | partial | not_attempted | unavailable:<motivo>   ← CALCOLATO, mai impostato
}
```

**Lo `status` di livello superiore è derivato.** Sommario calcolato dagli stati sottostanti:
`partial` significa «guarda i livelli sotto». Non può essere impostato a mano, o torna a essere la
sede unica della verità che §3.3 vieta. La regola di derivazione è parte del contratto.

**Invariante:** `status = not_attempted` **se e solo se** `entry_points` è vuoto. Sono la stessa
informazione vista da due lati; poterle contraddire ricrea l'ambiguità che §3.3 elimina.

**`corroborated_by` è bilaterale e nominativo.** Un booleano direzionale (*«questo chunk sta anche
nel grafo»*) porta metà del segnale: non dice **quale** simbolo corrobora, e il ramo grafo non vede
la corroborazione inversa. La lista di riferimenti la porta intera, in entrambe le direzioni, e
aggancia i due flussi invece di limitarsi a segnalarli.

**Il contratto di comparabilità non è un campo** (§3.1): vive nella descrizione del tool.

### 5.2 Duplicazione fra flussi: intenzionale, e marcata

La definizione trovata dal grafo comparirà quasi certamente **anche** fra i chunk di codice. **Scelta:
nessun dedup cross-flusso, sovrapposizione marcata** (`corroborated_by`):

1. **La coincidenza è informazione.** Due metodi *indipendenti* che convergono sulla stessa posizione
   sono un segnale di rilevanza — la stessa intuizione della fusione per rango. Deduplicare la
   nasconde.
2. **Il costo è contenuto:** il ramo `code` porta il **testo**, il ramo grafo un **puntatore**.

**Via intermedia, rinviata:** il ramo grafo potrebbe non essere uniforme — **testo per le
`definitions`** (poche, corte, ad alto valore: vedere una firma senza un secondo round-trip) e
**puntatori per `callers`/`callees`** (molti, e il valore è l'elenco, non il corpo). Compromesso
plausibile fra il costo di §4 e l'utilità, da decidere con una misura.

### 5.3 La serializzazione non è neutra

La struttura arriva al consumatore **resa**: JSON annidato, sezioni markdown, o una mescolanza. È il
luogo in cui si consuma la divergenza fra §3.2 e §5.1.

- **L'invariante è che le etichette sopravvivano.** Ogni resa che conservi «questo è una definizione,
  questo un chiamante» soddisfa la tesi; ogni resa che le appiattisca la tradisce, per quanto pulita
  fosse la struttura a monte.
- **La profondità di annidamento è un costo.** `graph.symbols[0].callers.items[2]` richiede di tenere
  a mente una gerarchia mentre si legge. Uno schema corretto ma profondo può essere peggiore, all'uso,
  di uno leggermente ridondante ma piatto.

Quale resa concreta funzioni meglio, e se privilegiare l'ordine di §3.2 o l'annidamento di §5.1, sono
questioni **empiriche** (§8), non da decidere per gusto.

## 6. Alternative considerate e scartate

**Classifica unica fusa** — richiede una scala che non esiste (§2), e nasconde la fusione dentro un
ordinamento che sembra oggettivo.

**Un numero sintetico di «copertura»** (*coperto se ho sia doc sia codice*) — scartata su **evidenza
diretta** (§9): implementata come congiunzione, produsse una metrica bassissima che sembrava dire «la
fusione non funziona». Era un artefatto: i segnali erano indipendenti e sani, il booleano li aveva
distrutti. **La congiunzione di segnali indipendenti non misura la loro combinazione, misura la loro
coincidenza.**

**Riassunto in prosa generato dal sistema** — sposta la generazione dentro il retrieval. Chi consuma è
già un LLM ed è lui il posto giusto per sintetizzare; un riassunto intermedio è un passaggio lossy e
non ispezionabile fra evidenza e ragionamento.

**Interlacciare gli item** in una sequenza unica — il modello perde traccia di quale segnale sta
leggendo. *(Distinto dall'alternanza di blocchi etichettati di §3.2, che è ammessa: l'atomo è il
blocco.)*

**Un router che sceglie il metodo al posto dell'agente** — scartata per confine, non per fattibilità:
decidere se una domanda sia strutturale o semantica è **giudizio**, e l'agente ha il contesto della
conversazione che il retrieval non ha. La proposta di questa pagina **non è un router**: fa fan-out e
consegna tutti i flussi, la scelta resta al consumatore.

## 7. Come si entra nel grafo da una query in linguaggio naturale

| # | Via | Copre | Eredita difetti da |
|---|---|---|---|
| 1 | **Simboli dichiarati dal chiamante** | quando l'agente sa già cosa cerca | nulla |
| 2 | **Match lessicale contro la tabella dei nomi qualificati** | query il cui **vocabolario si sovrappone ai sottotoken** dell'identificatore | il *lexical gap* |
| 3 | **Estrazione di identificatori dalla query** | query che nominano già l'identificatore | nulla (deterministico) |
| 4 | **Espansione dai primi risultati di codice** | query puramente concettuali | **la qualità del ramo semantico** |

**Il raggio della via 2 va dichiarato con precisione.** Non copre «il concetto»: copre i casi in cui
le parole della query si sovrappongono ai **sottotoken** dell'identificatore. «La classe che fa
caching degli embedding» → `CachingEmbedder` funziona perché *caching* ed *embedding* compaiono
letteralmente nel nome. Fuori di lì c'è il **lexical gap**: sinonimia e perifrasi («la cosa che evita
di ricalcolare i vettori») non contengono alcun sottotoken, e il **disallineamento di lingua** — query
in italiano, identificatori in inglese, il caso *normale* in un progetto italiano — riduce la via 2
alla fortuna dei prestiti linguistici.

**Il buco fra via 2 e via 4 è reale:** le query concettuali senza sovrapposizione lessicale sono
raggiungibili **solo** dalla via fragile. Una via 5 semantica (embedding dei nomi qualificati e dei
loro docstring) lo chiuderebbe, ma reintrodurrebbe la dipendenza dalla similarità che le vie 2 e 3
evitavano: **rinviata**, non scartata.

**La via 1 è la meno giustificata.** Se l'agente sa già quale simbolo lo interessa può chiamare il
tool di navigazione dedicato; resta utile solo per ottenere **entrambi** i segnali su un simbolo noto
in una chiamata. È la prima da tagliare se si volesse ridurre superficie.

**Quanti simboli per la via 4: 2–3, non il top-1.** Il costo di un'interrogazione in più è basso, gli
ingressi sbagliati sono visibili, e **il top-1 semantico è precisamente il punto in cui il §9
documenta hit@1 ≈ 0.18**.

*Aperto:* la soglia di match della via 2. Troppo permissiva aggancia simboli irrilevanti e paga il
costo di §4 dove il beneficio è nullo; troppo stretta ricade sulla via 3.

## 8. Come confutare — e cosa misurare per primo

| # | Affermazione | Come si confuta |
|---|---|---|
| 1 | Fondere classifica e insieme richiede una scala che non esiste | Esibire un ordinamento congiunto ben fondato che renda commensurabili similarità e struttura |
| 2 | Il vuoto non tipizzato fa produrre all'LLM affermazioni false | Risposte con lo strumento-grafo disabilitato: se il modello si astiene comunque, la proprietà è meno critica |
| 3 | Il troncamento non dichiarato fa asserire liste esaustive (per gli **insiemi**) | Stessa forma di test, su un simbolo con molti chiamanti |
| 4 | Uno stato unico non rappresenta il fallimento parziale | **Non** mostrando che i casi misti sono rari: il danno di §3.3 è la fabbricazione *silenziosa*, che anche un caso raro produce, e il costo della granularità è basso. Si confuta mostrando che l'agente si astiene comunque di fronte a uno stato aggregato |
| 5 | Le etichette di relazione sono più utili dei punteggi | A/B a parità di risultati: con etichette e senza punteggi vs il contrario |
| **6a** | **Sotto motore vettoriale, la forma della distribuzione è informazione usabile** | **A/B con e senza `score`, a parità di ordine. Non misurato** |
| **6b** | **Sotto RRF il punteggio è quasi peso morto** (l'ordine lo contiene già) | **A/B con e senza `score` sotto motore ibrido. Non misurato** |
| 7 | L'ordine ancore-prima batte chunk-prima | A/B sullo stesso materiale, solo ordine diverso. **Non misurato** |
| 8 | La resa piatta batte quella profonda a parità di struttura | A/B sulla serializzazione. **Non misurato** |
| **9** | **Dichiarare l'ambito di comparabilità previene i confronti cross-flusso** | **Payload con due flussi dai vertici molto diversi: se l'agente li confronta comunque, la dichiarazione non basta → togliere il punteggio (§3.1). Non misurato** |

**Da dove cominciare.** Le affermazioni **6a/6b** e **9** sono le più economiche da montare e le più
cariche di conseguenze sul contratto: decidono se il punteggio resta nel payload, sotto quale motore,
e se la dichiarazione d'ambito è sufficiente. Vanno misurate **prima** di un ulteriore giro di prosa —
il rendimento della revisione testuale è ormai calante, e le quattro affermazioni non misurate sono
il collo di bottiglia di tutte le altre.

**Criterio di successo complessivo, duplice — entrambe le metà vanno superate:**

- **Beneficio** — un agente che riceve i tre flussi risponde meglio sulle domande strutturali.
- **Non-regressione** — **non** risponde peggio sulle domande *non* strutturali, dove il ramo grafo è
  materiale non richiesto. Misurare latenza, token e qualità.

Se fallisce la seconda metà, la proposta si **degrada** (fan-out opt-in, o condizionato a ingressi ad
alta affidabilità: vie 1–3). Se fallisce la prima, si abbandona.

## 9. Evidenza da un sistema reale

Due esperienze, riportate perché sono la base empirica di §2 e §6 — e perché entrambe furono
**sorprese**, non conferme.

**La congiunzione che sembrava un difetto del retrieval.** Una metrica di «copertura della fusione»
implementata come `ha_doc AND ha_codice`, mediata sui casi: ≈ 0.17, letto come prova che la ricerca
combinata non funzionava. Era un artefatto della congiunzione: misurando per superficie i numeri
erano sani, e con l'unione la copertura risultava piena. **Il difetto era nella misura, non nel
sistema misurato.**

**Le domande da simbolo che affossavano la valutazione.** Una valutazione dava hit@1 ≈ 0.18. La suite
conteneva domande *«dov'è definito X»* — **strutturali** — misurate sul solo motore di similarità.
Instradandole al grafo: hit@1 ≈ 0.64, hit@10 = 1.00. **Il sistema composito era sano; era la misura a
essere parziale.**

Il secondo episodio è l'argomento più forte a favore della proposta: sulle domande da simbolo la
similarità è *genuinamente scarsa* e il grafo è *esatto*. Se l'unico modo di raggiungere il grafo è
che l'agente decida di chiamarlo, **la qualità del sistema dipende da una scelta che non misuriamo**.

---

## Storia della revisione

> **Protocollo.** Ogni rilievo compare con un esito esplicito — **accolto**, **respinto** o
> **rinviato** — e la sua ragione. Un rilievo che sparisce senza esito è il punto cieco del formato.

**Quarto giro.** Decisione sul punteggio resa **condizionale al motore** (§3.1) invece che
«provvisoria per entrambi» — la prudenza precedente era rinvio, dato che l'analisi interna già
diceva che sotto RRF il campo è quasi peso morto · affermazione 6 **sdoppiata** per motore ·
**normalizzazione per-lista respinta come rimedio**: non rende vacuo il confronto cross-flusso, lo
rende fuorviante (tutte le liste partirebbero da `1.00`, un flusso debole apparirebbe pari a uno
forte) — se la 9 cade si toglie il punteggio · §3.2 **riconciliato** con §6: l'atomo che non si
interlaccia è il **blocco etichettato**, non il flusso · §3.4 distingue **insiemi** (il taglio mente)
da **classifiche** (il top-k è costitutivo) · `also_in_graph` → **`corroborated_by`**, bilaterale e
nominativo · test dell'affermazione 4 **ridisegnato** (la rarità non confuta: il danno è la
fabbricazione silenziosa) · le due condizioni di §2 dichiarate bisognose di un **test di
regressione**, non di una verifica una tantum · descrizione del tool da **generare dalla
configurazione**, perché il motore è deployment · **corpo ripulito dalla propria biografia**: la
provenienza sta qui, il corpo asserisce.

*Rilievo respinto:* «il complemento `low_confidence` eredita il problema di RRF». **No** — verificato
sul codice: la soglia è applicata al **pool denso prima della fusione**, proprio perché il punteggio
finale non è una similarità (decisione registrata nel sistema d'origine). Il rilievo però ha portato
a una scoperta peggiore, ora in §3.1: **il numero su cui si decide l'astensione e quello esposto nel
payload sono su scale diverse**, e il contratto taceva.

*Correzione a un giro precedente:* la «scoperta» che il punteggio del motore di default non è una
similarità era una **riscoperta** — la decisione era già codificata nel gate di confidenza. La pagina
la presentava come ritrovamento.

**Terzo giro.** `score_scope` rimosso dal payload (documentazione travestita da dato) → descrizione
del tool · affermazione 9 aggiunta (dichiarare non impone) · nota di onestà in §3.1 allineata a §3.2 ·
lettura relativa: «guadagno di grado, non di natura» · §2: enunciate le **due condizioni** che rendono
innocuo il segnaposto `1.0` (instradamento totale + consumo del solo path), verificate sul codice ·
via 2 ridimensionata, lexical gap e disallineamento di lingua nominati · conflitto §3.2 ↔ §5.1
dichiarato · marcatura della sovrapposizione portata nello schema · `status` calcolato · invariante
`not_attempted` ⟺ `entry_points` vuoto · via 1 giustificata e dichiarata la prima da tagliare ·
*rinviato:* via intermedia puntatori/testo.

**Secondo giro (auto-correzione).** La rimozione del punteggio decisa al primo giro era **sbagliata**:
il sostituto su cui si contava è spento di default e visibile solo nei log, mai all'agente; e
l'argomento «l'LLM non sa se `0.83` è buono» colpisce la lettura *assoluta*, non quella *relativa*. Il
punteggio è tornato nel payload con un contratto di comparabilità. *Nota di metodo:* il rilievo era
corretto, la correzione no — **la verifica sul codice è arrivata dopo la decisione invece che prima**.

**Primo giro.** Aggiunti §4 (costo del fan-out) e §5.2/§5.3 · riformulato §2 («non commensurabile»
anziché «non può avere un punteggio») · stato per-simbolo e per-relazione · `source` in
`entry_points` · `truncated` strutturato · §7 portata a quattro vie · criterio di validazione
simmetrizzato.

## Contesto interno (non necessario alla valutazione)

Origine: analisi del 2026-07-24 sulla forma di ritorno di `search_combined`, che oggi restituisce una
tupla `(docs, code)` in cui **entrambi i rami provengono dallo stesso motore di similarità**, distinti
solo da un filtro sui metadata `doc_type` — il grafo non vi entra affatto.

**Esito: questa pagina è diventata un requisito.** Le quattro affermazioni non misurate di §8 hanno
rivelato che il progetto **non aveva lo strumento** per rispondere: la macchina di valutazione
esistente misura il *retrieval*, non il *comportamento dell'agente*. Da qui **E5-FEAT-012**
([`contratto-retrieval-agente/`](../../requirements/retrieval-qualita/contratto-retrieval-agente/requirements.md),
requisiti scritti il 2026-07-24), che costruisce l'harness agent-facing **prima** del fan-out e lo usa
come gate duplice. Le decisioni di questa pagina vi entrano come vincoli; **gli esiti delle misure
torneranno qui**, trasformando le righe «non misurato» di §8 in verdetti e portando il frontmatter
fuori da `in-review`.

Pagine collegate: [[retrieval-vs-graph]] · [[code-graph]] · [[hybrid-retrieval]] (il motore di
default, la cui natura RRF governa §3.1) · [[indexing-and-retrieval]] ·
[[valutazione-e-non-regressione]] (instradamento per tipo di domanda, numeri di §9, segnaposto di §2)
· [[retrieval-confidence]] (la soglia sul pool denso pre-fusione, §3.1) · [[dedup-risultati]] (dedup
*entro* un flusso, distinto dal cross-flusso di §5.2) · [[deterministic-vs-judgment]] (il confine che
motiva l'alternativa «router» scartata in §6).
