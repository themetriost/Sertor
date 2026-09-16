---
title: Il potere retrospettivo di una guardia
type: concept
tags: [guardie, verifiche, criteri-accettazione, misura, e10, e15]
created: 2026-07-29
updated: 2026-09-16
sources: ["specs/124-copertura-changeset-scan/spec.md", "specs/125-smoke-di-upgrade/spec.md", "requirements/fedelta-dogfood/smoke-di-upgrade/requirements.md", "wiki/log/2026-07-29.md", "scripts/smoke.sh", "scripts/smoke.ps1", "tests/integration/test_host_smoke.py", "wiki/log/2026-09-16.md"]
---

# Il potere retrospettivo di una guardia

Quando si costruisce una verifica — un test, un gate, un controllo automatico — la domanda che decide
se serve non è *«copre abbastanza?»*. È:

> **Applicata ai difetti che sono GIÀ avvenuti, quanti ne avrebbe fermati?**

È una domanda con una risposta numerica, verificabile **prima** che la guardia esista. Trasforma
*«aggiungiamo un test»* — un proposito che nessuno può contraddire — in un'affermazione falsificabile.

## Perché la domanda ovvia è quella sbagliata

*«Copre abbastanza?»* si risponde immaginando. Si finisce per costruire l'elenco di ciò che
**potrebbe** rompersi, che è infinito, ordinato per quanto è facile verificarlo — non per quanto
accade. Una guardia così protegge da **difetti immaginati**, ed è indistinguibile da una che protegge
davvero finché non arriva quello vero.

Calibrarla sulla **storia** ribalta la costruzione: l'elenco degli esiti da verificare non si inventa,
si **deriva** dai guasti occorsi, uno per uno, ciascuno con il suo caso reale accanto.

## Due istanze, lo stesso giorno, in due feature diverse

| Feature | Criterio | Base |
|---|---|---|
| **E10-FEAT-062** (gate del wiki) | gli **otto** scenari di non-rilevazione misurati devono essere tutti rilevati | una matrice comportamentale **eseguita**, non una lista di ipotesi |
| **E15-FEAT-012** (smoke di upgrade) | dei **sette** difetti d'aggiornamento occorsi, almeno **cinque** rilevati | i riscontri della federazione, contati uno per uno |

Nel secondo caso l'elenco degli esiti da asserire è nato **per derivazione**: il pin che non si muove
(tre nodi), l'automatismo duplicato, la configurazione azzerata, la forma dell'invocazione conservata
perché «c'era già». Nessuno di questi sarebbe finito in un elenco costruito per completezza — sono
troppo specifici per essere immaginati, e troppo frequenti per essere ignorati.

## Il prerequisito scomodo: bisogna aver contato

Il criterio funziona solo se i difetti **sono stati contati**. La maggior parte dei progetti non lo fa:
li ripara e li dimentica, quindi non ha una base contro cui misurare una guardia nuova. Qui la base è
esistita perché i riscontri arrivano da nodi che pubblicano, e sono rimasti scritti.

> Il potere retrospettivo si può calcolare **solo** se qualcuno ha tenuto il conto. Contare i propri
> guasti non è contabilità: è ciò che rende costruibile la difesa successiva.

## Il corollario che rende il criterio onesto: dichiarare il residuo

«Cinque su sette» dice anche **due no**. Se il residuo resta implicito, il criterio produce la falsa
sicurezza che voleva togliere: la guardia è verde e due difetti noti restano scoperti.

Quindi la coppia è inseparabile — **il bersaglio e il residuo si scrivono insieme**. Una guardia che
dichiara cosa non copre è più utile di una che tace, perché chi la legge sa dove guardare a mano.

## Come si usa, in pratica

1. **Conta** i guasti reali di quella superficie, con il caso concreto accanto.
2. **Deriva** da lì l'elenco delle cose da verificare, invece di inventarlo.
3. **Fissa il bersaglio** come numero: *«di questi N, almeno M»*.
4. **Dichiara il residuo**: quali degli N restano fuori, e perché.
5. Quando arriva un guasto nuovo, **aggiungerlo deve essere una riga in più** — se richiede una
   ristrutturazione, l'elenco invecchierà e la guardia proteggerà solo il passato.

## La prima applicazione ha colto il suo autore (2026-07-29, stesso giorno)

Scritto il criterio, l'ho applicato all'implementazione che avevo appena dichiarato finita. Risultato:
**4 su 7** — sotto il bersaglio di 5. Le cinque asserzioni che avevo scelto coprivano i difetti che
ricordavo meglio, non i sette che erano avvenuti.

Il difetto scoperto (#5) era invisibile alle asserzioni esistenti per una ragione precisa: l'artefatto
restava **presente una volta** ma **stantio**, e contare le occorrenze non distingue *«c'è»* da *«è
quello giusto»* — cioè [[identita-per-presenza-o-per-contenuto]], nella verifica costruita per
misurare gli altri. Il rimedio è stato leggere il **report dell'aggiornamento**, dove il segnale già
c'era.

> Il valore del criterio non è nel numero che produce: è che **si può non raggiungerlo**. Un criterio
> che passa sempre non ha mai misurato niente.

E la parte scomoda: senza calcolarlo avrei consegnato **4 su 7 chiamandolo fatto**, con cinque
asserzioni che *sembravano* esaustive. Il conteggio è costato dieci minuti e ha cambiato il risultato.

## La guardia che muore del proprio successo (2026-09-16)

Il criterio di questa pagina — *ancora la guardia ai difetti già avvenuti* — ha un rovescio che si paga
più tardi, e va scritto qui perché **colpisce esattamente chi lo applica bene**.

Ancorare una verifica a un difetto reale significa, spesso, **riprodurne la condizione**: piantare lo
stato rotto e asserire che il rimedio lo guarisca. È la forma più onesta di guardia — nessuna vacuità
possibile, perché se la condizione non si pianta l'asserzione non c'è. Ma la condizione appartiene al
**mondo non riparato**, e il rilascio del rimedio la cancella. Da quel momento la guardia non misura
più: *non può*.

**L'istanza, misurata.** L'esito `mcp-server-imports` del gate d'aggiornamento (E10-FEAT-070) pianta la
condizione dell'ospite colpito dalla major 2.0.0 dell'SDK MCP — runtime pinnato alla release precedente,
SDK forzato alla major nuova — e asserisce che dopo l'`upgrade` il server parta. Ha funzionato
perfettamente **una volta**: sul salto `v0.4.1 → master`, dove la release di partenza era davvero
affetta. Poi è uscita la **v0.4.2**, che *porta il tetto*. Da lì la release precedente non è più
affetta, la condizione è **impiantabile per costruzione**, l'esito esce `n/a` — e la lista anti-vacuità
del wrapper, che lo pretende **per nome**, lo legge come esito mancante. Risultato: **`master` rosso a
ogni push**, su un difetto che non esiste.

Il dettaglio che rende la trappola difficile da vedere: **il rilascio che l'ha rotta non ha eseguito la
guardia**. Il tag `v0.4.2` è stato creato *dopo* l'ultimo run verde, quindi nulla ha girato con la
release nuova come punto di partenza. Il primo push successivo — una modifica al `README`, che con tutto
questo non c'entra nulla — è stato il primo a rivelarlo, e sembrava esserne la causa.

**La distinzione che scioglie il nodo.** L'esito confondeva due affermazioni:

| Affermazione | Natura | Vive quanto |
|---|---|---|
| «un ospite affetto è stato **guarito** da questo upgrade» | storica | fino al rilascio del rimedio |
| «dopo l'upgrade il server **parte**» | permanente | per sempre, e coglie una regressione |

Il rimedio è **asserire sempre la permanente** e *annotare* quale delle due si è osservata — non
scegliere quale asserire. La guardia mantiene i denti, l'annotazione resta onesta su cosa ha misurato
davvero (`not plantable: la release di partenza porta già il tetto — questo asserisce NESSUNA
REGRESSIONE, non una riparazione`), e non c'è più nulla che scada.

> **La regola operativa, da aggiungere ai cinque passi qui sopra:**
> **6. Pretendi solo affermazioni che SOPRAVVIVONO al difetto.** Se ciò che la guardia esige esiste solo
> finché il difetto non è riparato, la guardia ha una data di scadenza che nessuno ha scritto — e scade
> nel momento del successo, quando meno la si guarda.

**Nota su come ci si arriva comunque.** Questa forma era stata **vista e scartata** il 2026-09-13, fra i
candidati distill respinti: *«una riparazione rende irriproducibile il difetto che ripara — vero, ma è un
corollario di [[punto-di-partenza-non-verificato]], non un'entità a sé»*. Tre giorni dopo ha tenuto rossa
la CI del ramo principale. Il giudizio non era sbagliato sul *contenuto* — è davvero un corollario — ma lo
era sulla **conseguenza**: un corollario che rompe un gate non è una nota a piè di pagina. *Scartare un
candidato è una decisione che va rivista quando il candidato si presenta con un conto.*

## Parentele

- [[esito-sull-host-vs-forma-dell-asset]] — dice **dove** guardare (l'esito sull'ospite, non la forma
  spedita); questa pagina dice **come sapere se stai guardando abbastanza**. La misura che ha reso
  quella una tesi verificata è la stessa che alimenta questo criterio.
- [[dogfood-fidelity]] — perché la base di difetti su cui calcolare il potere retrospettivo arriva
  quasi tutta da **fuori**: il dogfood è una configurazione, e la più favorevole.
- [[deterministic-vs-judgment]] — contare i guasti e derivarne l'elenco è meccanico; decidere quale
  bersaglio sia accettabile è **giudizio**.
- [[daily-distill-floor]] — parente per la lezione sul costo: una guardia troppo cara si impara ad
  aggirarla, quindi il bersaglio va scelto anche in funzione di quanto la verifica costa a ogni giro.
- [[guardia-verde-non-e-una-misura]] — il guasto speculare: là il verde non ha verificato nulla, qui il
  **rosso** non segnala nulla. Entrambi consumano la fiducia nel gate, e un gate stabilmente rosso è
  quello che si impara a ignorare per primo.
- [[il-rimedio-ricade-nel-difetto]] — là il rimedio riproduce la forma del difetto; qui il rimedio
  **cancella la condizione** su cui la guardia poggiava. Due modi diversi in cui una riparazione si
  ritorce su ciò che la verifica.
