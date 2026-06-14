---
title: Il quaderno che cresce (in parole semplici)
type: explainer
tags: [non-tecnici, wiki, memoria, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/concepts/architettura-wiki-llm.md", "wiki/concepts/diary-vs-graph.md"]
---

# Il quaderno che cresce

## Il problema

Ogni volta che si lavora su un progetto si capiscono cose, si prendono decisioni, si scoprono perché.
Se tutto questo resta solo "in testa", alla sessione dopo si riparte da zero — e un assistente AI, che
non ricorda nulla tra una volta e l'altra, ancora di più.

## L'idea

Sertor tiene un **quaderno scritto del progetto** (lo chiamiamo *wiki*) che **non si riscrive ogni
volta da capo: cresce**. A ogni lavoro significativo si annota cosa si è fatto e perché. Col tempo il
quaderno diventa la memoria del progetto: il *perché* dietro le scelte, non solo il *cosa* del codice.

Questo quaderno ha due parti che lavorano insieme:

- **Il diario** — la cronaca, in ordine di tempo: «in questa data abbiamo fatto questo». Non si
  cancella, è la testimonianza.
- **Le pagine tematiche** — una scheda per argomento, sempre aggiornata a *com'è vero adesso*. Quando
  qualcosa cambia, si aggiorna la scheda (non si accumula confusione).

## Perché è prezioso

- Il sapere **non si disperde**: resta scritto e cumulativo.
- L'assistente AI, all'inizio di ogni sessione, **rilegge il quaderno** e riparte sapendo già dove
  siamo — invece di ricostruire tutto a freddo.
- Il quaderno stesso diventa **materiale che Sertor può cercare**: le spiegazioni scritte rendono le
  risposte più precise.

## L'immagine

È il diario di bordo di una nave: chi prende il turno legge le ultime pagine e sa subito rotta, meteo e
problemi aperti — non deve chiedere tutto da capo.

---

*Dettaglio tecnico:* l'architettura del wiki è in [[architettura-wiki-llm]]; le due memorie (diario e
schede) in [[diary-vs-graph]]; la disciplina d'uso in [[step-ritual]].
