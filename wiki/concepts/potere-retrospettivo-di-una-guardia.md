---
title: Il potere retrospettivo di una guardia
type: concept
tags: [guardie, verifiche, criteri-accettazione, misura, e10, e15]
created: 2026-07-29
updated: 2026-07-29
sources: ["specs/124-copertura-changeset-scan/spec.md", "specs/125-smoke-di-upgrade/spec.md", "requirements/fedelta-dogfood/smoke-di-upgrade/requirements.md", "wiki/log/2026-07-29.md"]
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
