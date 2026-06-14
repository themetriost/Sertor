---
title: Il pannello di controllo (in parole semplici)
type: explainer
tags: [non-tecnici, osservabilita, pannello, costo, cache, spiegazione]
created: 2026-06-14
updated: 2026-06-14 (MVP F1→F4 ✅ su master — `sertor-rag observe`)
sources: ["requirements/osservabilita/epic.md"]
---

# Il pannello di controllo

> **Stato: fatto (MVP).** Il pannello c'è ed è usabile: `sertor-rag observe`. Restano migliorie
> opzionali (il costo in **euro**, l'invio dei dati a strumenti esterni). La pagina lo racconta in
> parole semplici.

## Il problema

Sertor lavora — legge il progetto, lo scheda, risponde alle domande — ma è una **scatola muta**: non
ti dice *quanto sta spendendo*, *quanto gli sta facendo risparmiare la memoria*, *quanto è in salute il
suo archivio*. Tutti questi numeri li produce già, ma **scorrono via e si perdono**: come un'auto senza
cruscotto, vai avanti ma non sai a che velocità né quanta benzina resta.

## Cosa abbiamo costruito

Un **pannello di controllo dentro il terminale** (`sertor-rag observe`): ti ci affacci e vedi, a colpo
d'occhio, come sta andando Sertor — e i numeri ora **restano**, così puoi anche guardare indietro e
fare confronti.

L'immagine: il **cruscotto dell'auto** (velocità, benzina, spie) **più il libretto di bordo** che puoi
sfogliare per vedere com'è andata nei giorni scorsi.

## I quattro pezzi (in parole semplici)

1. **La memoria dei numeri** — oggi i numeri lampeggiano e spariscono. Il primo pezzo li **conserva**
   in un archivio locale, così esistono ancora domani. È la base: senza, non c'è niente da mostrare né
   da confrontare.
2. **I conti** — trasforma i numeri grezzi in **risposte**: «quanto ho speso questa settimana?»,
   «quanto mi ha fatto risparmiare la memoria della cache?», «quanto è in salute l'archivio?».
3. **Il cruscotto dal vivo** — la schermata che mostra **cosa sta facendo Sertor adesso** e si aggiorna
   mentre lavora: ultimo aggiornamento dell'archivio, quanti pezzi, consumo, stato della cache.
4. **I report sfogliabili** — le **viste storiche** da scorrere: il risparmio della cache nel tempo, il
   costo (anche in **euro**, non solo in gettoni tecnici), la salute e la freschezza dell'archivio.

## E la privacy?

Una riga, decisa in partenza: **di default il pannello conserva solo numeri, mai ciò che scrivi tu**
(le tue domande, le conversazioni). Se un domani vorrai tenere anche il testo, sarà una **scelta
esplicita** tua, non un comportamento di default. Tutto resta sul tuo computer.

## Perché conta

È la differenza tra usare uno strumento **alla cieca** e **vederci dentro**: capire quanto costa, dove
risparmi, e se qualcosa non va — senza dover installare strumenti esterni.

---

*Dettaglio tecnico:* l'epica e le sue feature in `requirements/osservabilita/epic.md`; lo stato e la
direzione in [[roadmap]]. Il risparmio della cache di cui sopra è [[robusto-ed-economico|la "memoria del
già fatto"]].
