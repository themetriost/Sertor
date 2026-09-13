---
title: Una compatibilità si misura al confine pubblico
type: concept
tags: [misura, dipendenze, contratto, metodo, compatibilita, e10]
created: 2026-09-13
updated: 2026-09-13
sources: ["src/sertor_mcp/server.py", "tests/contract/test_mcp_protocol_e2e.py", "requirements/debito-tecnico/feat-070-porting-mcp-sdk-v2/requirements.md", "wiki/log/2026-09-13.md"]
---

# Una compatibilità si misura al confine pubblico

Quando bisogna sapere se il codice regge su una versione nuova di una dipendenza, la domanda non è
*«l'API risponde?»* ma **«cosa arriva a chi ci consuma?»**. Fra le due c'è un piano intermedio — gli
helper interni della libreria — che risponde volentieri, in fretta, e **con un'altra risposta**.

> **La regola:** misura sul piano che i consumatori attraversano davvero. Ogni piano più interno ha il
> **diritto** di cambiare fra una major e l'altra, quindi un confronto fatto lì misura la libreria, non
> il contratto.

## La misura che ha prodotto la pagina

Il 2026-09-13, valutando il porting del server MCP all'SDK v2 (**E10-FEAT-070**), la compatibilità è
stata misurata **due volte**, e le due misure hanno dato risposte diverse.

**Primo giro — l'helper interno.** Una sonda ha istanziato il server e invocato `call_tool()`, l'helper
che l'SDK usa internamente per eseguire un tool. Conclusione: *due* differenze fra le versioni.

**Secondo giro — il protocollo.** Un client MCP vero, connesso sullo stdio, ha fatto l'handshake,
elencato i tool e chiamato gli stessi tre casi. Conclusione: **una** differenza.

| Fatto | Misurato sull'helper | Misurato sul protocollo |
|---|---|---|
| payload dei tool che ritornano `list[dict]` | identico | identico ✔ concorda |
| payload dei tool che ritornano `dict` | **«v2 regredisce»** | `None` su **entrambe** → *non è il porting, è il nostro design* |
| messaggio dell'errore al client | perso in v2 | perso in v2 ✔ concorda |

La riga centrale era **falsa**, e non per un errore di esecuzione: l'helper `call_tool` **cambia forma di
ritorno** fra le due major (`tuple` in v1, `CallToolResult` in v2). Confrontare due oggetti diversi
produce differenze che esistono nell'oggetto e non nel contratto. Il difetto era reale — metà dei nostri
tool non consegna contenuto strutturato — ma **preesistente e identico sulle due linee**: una proprietà
del nostro design, non una conseguenza del porting. Attribuirlo al porting avrebbe messo in quella
feature un lavoro che non le appartiene, e lasciato il difetto vero senza casa. Ora è
**E10-FEAT-076**.

## Perché il piano sbagliato è quello che si prova per primo

Non è distrazione: è che il piano interno è **più facile da raggiungere**. Un `await srv.call_tool(...)`
sta in tre righe; un handshake vero richiede due processi, un transport e un client. Con l'aggravante
che la sonda facile **funziona**: produce numeri, tabelle, una conclusione dall'aria definitiva. Nulla
nel suo output dice *«ho guardato un piano che i tuoi consumatori non attraversano»*.

È la **quarta forma** di [[guardia-verde-non-e-una-misura]] applicata a una sonda invece che a una
guardia: *sto misurando la cosa, o un suo indizio?* Con una differenza che vale la pena tenere distinta —
lì il verde era valido *di un'altra domanda*; qui la misura è **positivamente fuorviante**, perché
produce una differenza inesistente al confine. Un indizio che tace è meno dannoso di un indizio che
afferma.

## Il confine, per Sertor, è già scritto

La cosa notevole è che questa regola **non è nuova**: è il **Principio XI** letto dal lato della misura.
Il principio dice che a runtime si accede a Sertor *solo via vehicles* (CLI, MCP), mai importando
`sertor_core`, perché i vehicles cablano configurazione, osservabilità ed errori, e l'accesso diretto li
bypassa in silenzio. La simmetria è esatta:

| | consumare | misurare |
|---|---|---|
| **piano giusto** | il vehicle (CLI / MCP) | il protocollo / l'output del comando |
| **piano interno** | `build_facade()` a mano | un helper interno della libreria |
| **cosa si perde** | osservabilità, config, policy d'errore | la validità della conclusione |

Chi non attraversa il confine pubblico ottiene *qualcosa* — un risultato, o un numero — e perde
esattamente ciò che il confine garantisce. Ce n'è un precedente scritto in casa:
`specs/073-cattura-copilot-cli/research.md` dichiara che `events.jsonl` di Copilot CLI *«è un dettaglio
interno, non un contratto pubblico»*, e ne deriva un parsing tollerante. Lì il confine è stato
riconosciuto nel **design**; qui si è dovuto riconoscerlo nel **metodo di misura**, che è il posto in cui
sfugge più facilmente.

## Come si applica, in pratica

- **Chiediti chi è il consumatore, e imita lui.** Per un server MCP è un client sul transport; per una
  CLI è un processo che legge stdout e l'exit code; per una libreria, il codice che importa solo la
  superficie pubblica. Se la sonda fa qualcosa che nessun consumatore fa, la sua conclusione vale per
  nessuno.
- **Quando una sonda interna e una al confine divergono, vince il confine** — e la divergenza è essa
  stessa un'informazione: dice che stai guardando un dettaglio che la libreria è libera di cambiare.
- **Se al confine c'è un costo, pagalo una volta e tienilo.** L'handshake end-to-end era il buco
  dichiarato in E10-FEAT-070 (*«manca l'handshake stdio con un client vero»*): scriverlo è costato una
  sonda e ha **cambiato le conclusioni**. Per questo diventa un requisito permanente (FR-007), non una
  verifica una volta sola: una misura vale il giorno in cui la fai.
- **Dichiara il perimetro.** La sonda al confine ha coperto handshake, elenco dei tool, forma dei
  risultati ed errori. **Non** ha coperto cancellazione, timeout, payload grandi e concorrenza — scritto
  nella spec come *non misurato*, invece di lasciarlo presumere equivalente.

## Collegate

- [[guardia-verde-non-e-una-misura]] — la quarta forma: misurare una procura al posto della cosa
- [[punto-di-partenza-non-verificato]] — l'altra metà: verificare *da dove* parte la misura, non solo su quale piano
- [[confine-di-prodotto-misurato]] — parente sull'oggetto vicino: *dove* passa un confine si misura, non si deduce
- [[difetto-che-solo-un-ospite-nuovo-puo-vedere]] — il difetto che ha reso necessaria questa misura
- [[constitution]] — Principio XI: si consuma solo via vehicles, di cui questa pagina è il lato-misura
- [[mcp-server]] — il server misurato
