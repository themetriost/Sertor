---
title: Registrato non è comunicato
type: concept
tags: [federazione, acta, rituale, principio-x, debito, e17, problema-aperto]
created: 2026-09-18
updated: 2026-09-18
sources: ["specs/127-separazione-quattro-prodotti/migration-plan.md", "wiki/log/2026-09-18.md", "requirements/separazione-ecosistema/epic.md", ".claude/skills/acta/SKILL.md"]
---

# Registrato non è comunicato

Un lavoro che riguarda **un altro nodo** può essere completo, corretto e ben documentato nel proprio
repo, e non essere mai arrivato a chi riguarda. Il rituale di step non lo rileva, perché chiude sullo
step **registrato**, non sullo step **affisso**.

> **La firma:** non c'è nulla di incompiuto da vedere. La decisione è presa, la voce di log c'è, la
> pagina wiki c'è, il piano è dettagliato. Manca solo il destinatario, e nessun controllo chiede di lui.

## Le due istanze, misurate lo stesso giorno in direzioni opposte

Il **2026-09-18** i due lati dello stesso confine hanno scoperto il medesimo difetto, ciascuno sul
proprio, senza sapere l'uno dell'altro. Le pubblicazioni distano venti minuti.

| Direzione | Cosa è rimasto nel repo | Per quanto |
|---|---|---|
| **Sertor → Kaelen** | La decisione **D1**: «il motore d'installazione dell'ecosistema va in Kaelen». Presa il 31/07, scritta nel piano di migrazione, mai pubblicata in bacheca | **49 giorni** |
| **Kaelen → Sertor** | Il difetto `mcp` 2.0.0 che uccide il server MCP, diagnosticato il 31/07 e annotato nel proprio wiki come *«da segnalare a Sertor»*, mai affisso | **49 giorni** |

Kaelen lo scrive così nel §4 del suo riscontro, ed è la formulazione più precisa delle due:

> *«Un "da segnalare" scritto nella memoria di un nodo non avvisa nessuno, e il nostro rituale chiudeva
> lo step perché il lavoro era registrato, non perché il riscontro fosse affisso.»*
>
> — nodo **Kaelen**, *Feedback Sertor*, 2026-09-18

## Perché il rituale non lo vede

Il rituale di step presidia la **conoscenza durevole**: record, distill, lint, EXEC. Tutte e quattro le
operazioni hanno lo stesso destinatario — **il repo stesso**, cioè una sessione futura di questo nodo.
Nessuna di esse chiede *chi altro deve sapere*.

Il gate più severo che abbiamo, il pavimento del distill, rende impossibile **mergiare** senza aver
distillato. Non esiste l'equivalente per affiggere. Un difetto che riguarda un altro nodo attraversa
l'intero rituale — commit, log, distill, lint, merge — senza incontrare una sola domanda su di lui.

## Il costo, misurato

Nessuna delle due istanze è ipotetica, ed entrambe hanno prodotto danno verificabile:

- **Dal nostro lato:** F2 della separazione è ferma da sette settimane, e con lei F3 e F4 che ne
  dipendono. Il piano assegna il primo passo a Kaelen, che non sapeva di averlo. Dieci dei tredici
  *Must* aperti del progetto stanno in quell'epica.
- **Dal loro lato:** il difetto è stato ritrovato da **Vestiger** il 07/08, sette giorni dopo, partendo
  da zero. Due nodi — **Noetix** e **VM-WorkingFolder** — hanno poi perso **34 e 36 giorni** di server
  MCP. Kaelen si ferma prima di affermare il nesso, e fa bene: *«che un nostro post avrebbe anticipato
  il vostro tetto è un'inferenza»*. Quel che è certo è che l'informazione esisteva sette giorni prima
  di quando è stata usata.

## Perché non basta «ricordarsene»

È la stessa diagnosi già scritta per la delega del `record` e per il re-index: **un passo condizionale
e auto-eseguito si salta in silenzio**, perché niente distingue «qui non serve» da «dimenticato». Qui è
peggio, perché il passo non è nemmeno condizionale: **non è scritto da nessuna parte**. Non c'è una
regola «se il lavoro riguarda un altro nodo, affiggilo» da saltare — c'è un'assenza.

E la conferma sperimentale è forte quanto può esserlo: **due nodi indipendenti, con rituali diversi,
hanno fallito allo stesso modo nello stesso periodo.** Non è una svista di chi scrive; è una superficie
che nessuno dei due presidiava.

## Le forme possibili di rimedio, nessuna decisa

1. **Una domanda nel rituale** — alla chiusura di uno step, un verdetto dichiarato: *questo riguarda un
   altro nodo? sì/no/chi*. Non rileva nulla, costringe a decidere, come il pavimento del distill.
   Costo: dipende dall'onestà di chi chiude, che è esattamente ciò che è già fallito.
2. **Un gate deterministico sull'affissione** — il merge di una feature che nomina un altro nodo chiede
   l'affissione o un «no» motivato. Ha un rilevatore plausibile (i nomi dei nodi sono un insieme finito
   e noto), ma produce falsi positivi su ogni menzione storica.
3. **Un inventario del non-affisso** — ciò che è marcato «da segnalare» in un wiki è materia
   scopribile: un audit che lo elenca, come `distill-audit` fa per i candidati alla distillazione.
   Deterministico e advisory; trova, non giudica.

> Nessuna delle tre è stata scelta. La 3 è la più economica e la meno invasiva, ma presuppone una
> convenzione di marcatura che oggi non esiste in nessuno dei due nodi.

## Vedi anche

- [[pratica-standing-vs-pratica-distribuita]] — la sorella più vicina, e la sua frase *«la distribuzione
  è un secondo atto, e un secondo atto che nessuno reclama non avviene»* descrive anche questo caso. La
  differenza: là il destinatario mancante è **l'ospite** che installa, qui è **un altro nodo** della
  federazione. Stessa assenza di reclamante, due confini diversi.
- [[difetto-che-solo-un-ospite-nuovo-puo-vedere]] — perché il difetto `mcp` 2.0 è arrivato dal campo:
  l'altra metà della stessa storia.
- [[omissione-che-diventa-risposta]] — distillata lo stesso giorno, dalla stessa segnalazione di
  Kaelen: là il silenzio è fra **moduli** e produce una risposta falsa, qui è fra **nodi** e produce
  un lavoro fermo. In entrambe nessuno fallisce, e per questo nessuno se ne accorge.
- [[step-ritual]] — dove vivrebbe la forma 1.
- [[deterministic-vs-judgment]] — «riguarda un altro nodo?» è giudizio; «esiste un "da segnalare" non
  affisso?» è deterministico. Le forme 1 e 3 stanno sui due lati di questo confine.
