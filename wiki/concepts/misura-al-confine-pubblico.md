---
title: Una compatibilità si misura al confine pubblico
type: concept
tags: [misura, compatibilità, dipendenze, interfaccia-pubblica, mcp, e10, e15]
created: 2026-09-13
updated: 2026-09-13
sources: ["src/sertor_mcp/server.py", "tests/contract/test_mcp_protocol_e2e.py", "specs/128-porting-mcp-sdk-v2/spec.md", "requirements/debito-tecnico/epic.md", "wiki/log/2026-09-13.md"]
---

# Una compatibilità si misura al confine pubblico

Quando è necessario verificare se il codice funziona con una versione nuova di una dipendenza, la
domanda che conta non è se l'API interna risponde. **La domanda è: cosa arriva a chi ci consuma?**

Tra la domanda interna e quella del consumatore c'è un piano intermedio — gli helper interni della
libreria — che risponde volentieri, in fretta, e **con un'altra risposta**. Una misura presa su quel
piano intermedio è valida per quel piano, non per il confine pubblico che i consumatori attraversano.

> **La regola:** misura sul piano che i consumatori attraversano davvero. È il **Principio XI letto dal
> lato della misura**.

## La misura che ha prodotto la pagina

Il porting del server MCP dall'SDK v1 al v2 (**E10-FEAT-070**) è stato misurato due volte, con conclusioni
discordanti.

**Primo giro** — sull'helper interno `call_tool`: conclusione «il porting richiede due differenze fra le
versioni». Superficie: il docstring di due tool, il ritorno della funzione helper.

**Secondo giro** — al confine pubblico, con un **client MCP reale** sul transport stdio: conclusione
«una sola differenza». Handshake vero, 10 tool, payload, diagnostica di errore.

La riga che appariva nel primo giro come differenza era **falsa** — perché l'helper cambia forma di
ritorno fra le major. In v1 ritorna una tupla, in v2 un `CallToolResult`. Comparare due oggetti diversi
per forma produce differenze che stanno nell'oggetto, non nel contratto. **Il difetto era reale** e
identico su entrambe le linee dell'SDK, ma **non era conseguenza del porting**: fu promosso a
**E10-FEAT-076** come lavoro separato.

## Perché sfugge, e perché sfugge a chi ha misurato

L'helper interno è raggiungibile, facile da testare, e la sua forma è quella che il codice del server
tocca ogni giorno. È naturale leggervi una misura. Il confine pubblico è uno strato sopra, meno diretto,
e molti degli ospiti che usano Sertor non sono nemmeno lì — hanno delegato al server, e il server
gestisce i dettagli.

La conseguenza è che una misura presa al piano sbagliato *è valida* (risponde a una domanda vera) e
*fuorviante* (risponde a una domanda sbagliata). Nessun errore la segnala: il test passa, la forma è
corretta, la conclusione è presentata con sicurezza.

## Cosa ne segue

- **Progetta il test con il consumatore in mente, non con la superficie disponibile.** Se il test è una
  unit test su un helper interno, nomina la domanda che sta rispondendo. Se la domanda di affidabilità
  è *«regge su una versione nuova della dipendenza?»*, il test deve attraversare il confine pubblico.
  
- **Se il confine pubblico non è testabile dal dogfood, nomina quel fatto.** I test di porting del
  nostro server MCP girano con `mcp 2.2.0` in CI, e includono il contratto di handshake: è quello che
  un ospite vede. Se il confine non fosse testabile, l'accettazione di qualunque misura interna
  dovrebbe portare il disclaimer.
  
- **Il Principio XI vale anche per le sonde.** Il principio dice di consumare Sertor solo via vehicles
  pubblici per non bypassare osservabilità ed errori; la stessa asimmetria vale per le misure — misurare
  per via interna bypassa le scelte di design che avvengono al confine.

## Il parente stretto, e le somiglianze

[[punto-di-partenza-non-verificato]] chiede: *stavo misurando gli stati che credo?* — qui, a monte,
il punto di partenza della misurazione. Questa pagina chiede la stessa cosa, a valle: *il piano di
misurazione è quello che conta?* — cioè, gli stati che misuro sono quelli che il consumatore
attraversa?

[[guardia-verde-non-e-una-misura]] chiede: *il meccanismo della guardia poteva fallire?* — è di
progetto e di *esecuzione*. Qui chiediamo: *la domanda della misura è la domanda che conta?* — è di
*fondamento*.

## Collegate

- [[punto-di-partenza-non-verificato]] — l'altra metà della stessa disciplina: verificare da dove si
  parte
- [[guardia-verde-non-e-una-misura]] — il meccanismo che non guarda; qui, il piano di osservazione che
  sbaglia
- [[difetto-che-solo-un-ospite-nuovo-puo-vedere]] — il difetto per cui questa misurazione era
  necessaria
- [[Principio XI]] della costituzione — misurare come si consuma, non come si costruisce
