---
title: Budget d'ingresso dell'embedding (un tetto, due consumatori)
type: concept
tags: [embedding, chunking, memoria, robustezza, token]
created: 2026-10-20
updated: 2026-10-20
sources: ["src/sertor_core/services/chunking/_tokens.py", "src/sertor_core/services/memory_semantic.py", "src/sertor_core/config/settings.py", "specs/145-memoria-semantica-turni-grandi/"]
---

# Budget d'ingresso dell'embedding

Ogni modello di embedding accetta un testo fino a un certo numero di token
(`text-embedding-3-large`: 8.192). Oltre, il servizio **rifiuta la richiesta intera** con `http 400`
— non solo il testo troppo lungo, ma tutti quelli che viaggiavano con lui nello stesso invio.

## Un tetto solo, condiviso

Sertor ha **un** tetto: `Settings.max_chunk_tokens` (env `SERTOR_MAX_CHUNK_TOKENS`, default 8191), con
**un** misuratore: `cap_to_tokens` in `services/chunking/_tokens.py` (`tiktoken` se installato, altrimenti
una stima prudente a ~2 caratteri per token che sovrastima e quindi non sbaglia mai per difetto). Lo usano
due consumatori:

| Consumatore | Unità | Cosa succede oltre il tetto | Dal |
|---|---|---|---|
| Indice del corpus ([[chunking-dispatch]]) | chunk strutturale (sezione, simbolo) | sub-split, metadati strutturali conservati | E10 |
| Memoria semantica ([[memoria-conversazioni]]) | turno di conversazione | pezzi `session#turno/p`, **un** risultato per turno in ricerca | 145 (E4-FEAT-016) |

Il limite è del **modello**, non del tipo di contenuto: sullo stesso nodo corpus e memoria usano lo stesso
embedder, quindi una seconda manopola sarebbe un doppione destinato a divergere ([[constitution]], XIV).

## Perché la memoria l'ha scoperto tardi

Il corpus lo aveva perché i chunker strutturali producono unità grandi per natura (una sezione markdown,
una classe intera). La memoria è nata ([[feat-004-ricerca-semantica-memoria]]) con l'idea che un turno
fosse piccolo. Ma un turno non lo è: una **skill caricata** in conversazione o un file incollato vengono
registrati come un messaggio `user` da centinaia di migliaia di caratteri. Il caso reale (nodo Kaelen,
2026-10-20): un turno da ~290.000 caratteri, dieci volte il limite.

## La seconda metà: quanto costa un rifiuto

Il tetto toglie la causa nota, ma il danno dipendeva da un'altra cosa: **quanto lontano arriva un
rifiuto**. Le due superfici rispondono in modo diverso, e la differenza è voluta:

- **Corpus — strict.** Un rifiuto interrompe l'indicizzazione senza toccare l'indice esistente
  (`test_index_aborts_without_corrupting_existing_index`): l'errore è visibile e l'operatore lo vede
  subito.
- **Memoria — non-fatale per requisito** (REQ-008: l'archiviazione non si ferma mai per l'embedding).
  Proprio perché non si ferma, deve **confinare** il danno: prima un rifiuto costava tutti i turni nuovi
  della sessione (181 su 181), ora costa solo il turno rifiutato, che compare per nome nell'esito
  (`rejected session=… turn=… reason=http 400`) e viene ritentato al run successivo.

La regola che ne esce: **una superficie che degrada in silenzio per scelta deve rendere il danno piccolo
e nominato**. Se non può fermarsi per dire «qualcosa non va», deve dire *cosa* e *dove*, e far perdere
il meno possibile. È la forma che il principio *Fail Loud, Fix the Cause* prende dove il «loud»
non può essere un'interruzione.

## Il conteggio è una stima; l'accettazione è un fatto

Senza l'extra `tokenizer` il conteggio dei token è una **sovrastima** prudente (~2 caratteri/token):
giusto per decidere *prima* se spezzare, sbagliato per rimettere in discussione *dopo* ciò che il
provider ha già accettato. La verifica sul dogfood (2026-10-20) lo ha mostrato: la prima versione della
correzione ri-spezzava turni già indicizzati interi (62 ri-embedding, record orfani). Da allora un turno
presente **intero** nell'indice è indicizzato, qualunque cosa dica oggi la stima o un tetto abbassato.
La regola generale: **una misura approssimata può decidere il nuovo, non smentire un esito già
osservato.**

## Distinguere «questo testo» da «il servizio»

Il ripiego per turno scatta solo sui motivi che significano *input rifiutato*: `http 400`, `413`, `422`.
Un `401` (chiave sbagliata) è altrettanto non ritentabile, ma fallirebbe per ogni turno: ripiegare
moltiplicherebbe chiamate destinate a fallire e registrerebbe come «rifiutato» un turno innocente. La
classificazione `reason=f"http {status}"` è già uniforme negli adapter `openai`, `azure` e `ollama`.

## Collegamenti

- [[chunking-dispatch]] — dove il tetto è nato, per il corpus.
- [[memoria-conversazioni]] — il tier semantico della memoria.
- [[feat-004-ricerca-semantica-memoria]] — la feature d'origine della memoria semantica.
- Spec della correzione: `specs/145-memoria-semantica-turni-grandi/`.
