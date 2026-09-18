---
title: Un'omissione non dichiarata diventa una risposta
type: concept
tags: [retrieval, ingestione, code-graph, fail-loud, mission, e10, e7, problema-aperto]
created: 2026-09-18
updated: 2026-09-18
sources: ["src/sertor_core/services/ingestion.py", "src/sertor_core/domain/ports.py", "requirements/debito-tecnico/epic.md", "requirements/ingestione-estesa/epic.md", "wiki/log/2026-09-18.md"]
---

# Un'omissione non dichiarata diventa una risposta

Ogni strato che **omette senza dirlo** consegna allo strato successivo un dato che sembra completo. Lo
strato successivo ci lavora correttamente, e il risultato finale è **sintatticamente corretto e
semanticamente falso**: non un errore, una risposta. Chi la riceve non ha modo di accorgersene, perché
nessuno strato ha fallito.

> Non è il caso di [[guardia-verde-non-e-una-misura]], dove una verifica passa senza verificare. Qui
> non c'è alcuna verifica in gioco: il sistema **funziona**, e produce una risposta sbagliata mentre
> funziona.

## L'istanza misurata: tre strati, tre silenzi, una risposta falsa

Trovata il **2026-09-18** dal nodo **Kaelen**, che ha interrogato il proprio codice Rust e ha ricevuto
zero risultati senza alcuna diagnosi.

| Strato | Cosa omette | Cosa dice | Voce |
|---|---|---|---|
| **Ingestione** | `ingestion.py:91-93`: se l'estensione non è in `_EXT_LANG` (16 voci), il file è saltato con un `continue` | nulla. `index` riporta un conteggio di documenti che sembra completo | `E10-FEAT-079` |
| **Code-graph** | costruito sui soli documenti sopravvissuti: 220 nodi, **0 simboli, 0 archi** | nulla. Il file del grafo esiste, quindi nessun errore | — |
| **Navigazione** | `find_symbol` torna `[]` | «quel simbolo non c'è» | `E10-FEAT-080` |

L'ospite ha chiesto *«dov'è `main`?»* e ha ricevuto *«non esiste»*. La risposta vera era *«i tuoi 104
file Rust non sono nel corpus, e nessuno te l'ha detto»*.

## Perché ogni strato, da solo, è difendibile

È questo che rende il difetto difficile da vedere in revisione:

- **L'ingestione** ha una allowlist per una ragione buona: non indicizzare binari e formati non-testo.
  Un `continue` su estensione ignota è la scelta ovvia.
- **Il code-graph** costruisce ciò che trova. Zero simboli su zero file di codice è il risultato
  corretto del suo input.
- **`find_symbol`** rispetta il proprio contratto (`domain/ports.py:151`), che dichiara **due**
  semantiche d'assenza: grafo non costruito → errore esplicito; simbolo assente → lista vuota. Il caso
  reale è un **terzo stato** — grafo costruito e vuoto — che il contratto non prevede, quindi cade
  nella seconda casella.

Nessuno dei tre è un bug isolato. **Il difetto è la composizione**, e la composizione non ha un
proprietario: sta fra i moduli, dove nessuna revisione di modulo guarda.

## Il dettaglio che dimostra che è una svista e non una scelta

In `ingestion.py`, il file saltato per **estensione ignota** non produce alcun evento. Il file saltato
perché **illeggibile** produce `ingest_skip`. Le due righe distano **tre righe**. La stessa funzione
tratta due omissioni in modo opposto, e solo una delle due è dichiarata.

## Perché conta più qui che altrove

La missione di questo prodotto è che **il contesto reso all'agente sia reale**. Un retrieval che omette
in silenzio non degrada la qualità della risposta: la **inverte**. L'agente riceve un'assenza e conclude
un fatto — *«questo simbolo non esiste nel progetto»* — e su quella conclusione ragiona, scrive codice,
decide. Un errore esplicito lo avrebbe fermato; una lista vuota no.

È lo stesso meccanismo di [[default-masked-defect]] portato di uno strato più in su: là una manopola che
non solleva nasconde l'errore, qui un'assenza che non si dichiara **prende il posto** di un'informazione.

## La forma generale, per riconoscerla altrove

Tre condizioni insieme:

1. uno strato **scarta** input per un criterio legittimo;
2. lo scarto **non è dichiarato** in alcun canale (né evento, né conteggio, né campo di risposta);
3. uno strato più in alto **interpreta l'assenza** invece di propagarla.

Quando le tre coesistono, il sistema non ha un modo di distinguere *«non c'è»* da *«non l'ho guardato»*.
La riparazione non sta nel terzo strato: sta nel **primo che tace**.

## Cosa manca

- `E10-FEAT-079` (*Should P1*) — l'ingestione dichiara ciò che omette. Chiude la **classe**: vale per
  qualunque linguaggio fuori dalla allowlist, non solo Rust.
- `E10-FEAT-080` (*Should P1*) — il contratto riconosce il terzo stato d'assenza.
- `E7-FEAT-005` (*Should*) — Rust nel corpus. Chiude il **caso** che ha fatto emergere la classe.

> Le tre sono tenute separate apposta: aggiungere Rust farebbe sparire il sintomo di Kaelen e
> lascerebbe intatto il meccanismo per il prossimo ospite scritto in un linguaggio non previsto.

## Vedi anche

- [[guardia-verde-non-e-una-misura]] — la parente: là una verifica passa senza verificare, qui un
  sistema risponde senza sapere. In entrambe il verde non significa quel che sembra.
- [[default-masked-defect]] — lo stesso mascheramento uno strato più in basso.
- [[registrato-non-e-comunicato]] — distillata lo stesso giorno, dalla stessa segnalazione: là il
  silenzio è fra nodi, qui fra moduli.
- [[constitution]] — *Fail Loud, Fix the Cause*: questa pagina è il caso in cui non c'è nulla che
  fallisca, quindi il principio va applicato a un'**omissione**, non a un errore.
