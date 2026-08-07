---
title: Il difetto che solo un ospite nuovo può vedere
type: concept
tags: [dipendenze, lock, installazione, guardie, dogfood, e10]
created: 2026-08-07
updated: 2026-08-07
sources: ["pyproject.toml", "uv.lock", "src/sertor_mcp/server.py", "wiki/log/2026-08-07.md"]
---

# Il difetto che solo un ospite nuovo può vedere

Un vincolo di dipendenza **senza tetto** non è un difetto nel momento in cui lo scrivi. Diventa un
difetto nel momento in cui **qualcun altro risolve** quel vincolo, e solo per lui.

> **La regola:** un difetto che nasce in fase di *risoluzione* delle dipendenze è invisibile a
> chiunque abbia già risolto. Il suo lock lo protegge — e nel proteggerlo, glielo nasconde.

La popolazione che può incontrarlo non è «tutti gli ospiti». È **esattamente quelli che installano
dopo l'uscita a monte**, cioè i più nuovi. Chi era già installato ha nel proprio `uv.lock` la
versione vecchia, che continua a funzionare finché non rigenera. Non gli capita niente, e non ha
niente da segnalare.

## La misura che ha prodotto la pagina

`sertor-core` dichiarava `mcp>=1.2` senza limite superiore (`pyproject.toml`, extra `mcp` e `dev`).

| Data | Fatto |
|---|---|
| 2026-07-28 | `mcp` **2.0.0** esce su PyPI — «major rework of the SDK»; `mcp.server.fastmcp` sparisce |
| — | il nostro `uv.lock` resta a **1.27.2**: il dogfood non se ne accorge |
| 2026-08-07 | il nodo **Vestiger** installa da zero, risolve **2.0.0**, e il server MCP **non parte** |

`src/sertor_mcp/server.py:25` importa `mcp.server.fastmcp` prima di qualunque altra cosa: il
processo muore in partenza. Non «alcuni tool mancanti» — **nessun tool**. E un `sertor-rag doctor`
verde su tutto, perché la riga `mcp` guarda la registrazione in `.mcp.json`, non l'avvio
([[guardia-verde-non-e-una-misura]]).

## Perché è lo specchio di una pagina che avevamo già

[[esito-sull-host-vs-forma-dell-asset]] descrive l'asimmetria opposta: difetti che **richiedono
un'installazione preesistente più vecchia** per manifestarsi, e che un host pulito non può vedere
*per costruzione*. È la misura che ha riorientato il modo in cui rilasciamo — 13 difetti su 14
arrivavano dal campo, e tutti e sette quelli d'installer erano di quella famiglia.

Questa pagina nomina l'angolo **opposto e complementare**:

| | serve per vederlo | chi non lo vede mai |
|---|---|---|
| [[esito-sull-host-vs-forma-dell-asset]] | un'installazione **vecchia** che aggiorna | un host pulito |
| **questa pagina** | un'installazione **nuova** che risolve da zero | ogni host già installato |

Il fatto scomodo è che **il dogfood non sta in nessuno dei due**. Il runtime `.sertor/` insegue HEAD
con un re-lock a ogni merge: passa da un commit al successivo, mai da una versione alla successiva
(il *terzo limite* di [[dogfood-fidelity]]) — e non installa mai da zero, quindi non ri-risolve mai
le dipendenze. Le due estremità dell'arco sono entrambe cieche per noi, e per ragioni diverse.

## Cosa ne segue

- **Un tetto non è pessimismo sull'upstream: è una scelta su *quando* scoprirlo.** Senza tetto, la
  major nuova la scopre un ospite in produzione, nel momento peggiore. Con il tetto, la scopriamo noi
  aggiornandolo di proposito. La differenza non è il rischio — è chi lo corre.
- **Il lock è un anestetico.** Rende il difetto invisibile proprio a chi avrebbe gli strumenti per
  diagnosticarlo bene (noi, che conosciamo il codice) e lo lascia intatto per chi ne ha di meno
  (chi ha appena installato). È il contrario della distribuzione utile del dolore.
- **Chi lo incontra è chi ci conosce meno.** Il primo contatto con Sertor di un nodo nuovo è un
  vehicle su due che non parte. Non è un costo tecnico, è un costo di fiducia.
- **La domanda che nessuna guardia pone oggi:** *quali nostri vincoli ammettono una major non ancora
  uscita?* È deterministica e a costo quasi zero — si legge dai metadati del pacchetto — e nessun
  test la fa. `textual>=8,<9` il tetto ce l'ha; `mcp>=1.2` no. La differenza era discrezione di chi
  scriveva la riga, non una regola.

## Collegate

- [[esito-sull-host-vs-forma-dell-asset]] — l'asimmetria opposta, e la ragione del gate d'aggiornamento
- [[guardia-verde-non-e-una-misura]] — perché `doctor` ha detto `pass` mentre niente funzionava
- [[dogfood-fidelity]] — i limiti strutturali di ciò che il dogfood può esercitare
- [[il-rimedio-ricade-nel-difetto]] — la famiglia dei rimedi che rientrano nel problema che chiudono
