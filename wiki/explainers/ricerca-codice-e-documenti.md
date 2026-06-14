---
title: Cercare nel progetto (in parole semplici)
type: explainer
tags: [non-tecnici, ricerca, retrieval, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/concepts/retrieval-core.md", "wiki/concepts/indexing-and-retrieval.md"]
---

# Cercare nel progetto

## Il punto di partenza

Cercare con le parole esatte (come `Ctrl+F`) funziona solo se sai **già** come è scritta la cosa che
cerchi. Ma le domande vere sono per concetto: «dove si controlla la password?». Magari nel codice non
compare mai la parola "password" — si chiama `credenziali` o `auth`. La ricerca letterale fallisce.

## Come fa Sertor

Sertor capisce le cose **per significato**, non per parola esatta. Funziona in due tempi:

1. **Prima (una volta sola): mette in ordine la biblioteca.** Legge tutto il progetto, lo taglia in
   pezzi sensati (una funzione, una sezione di un documento) e a ogni pezzo associa una specie di
   *impronta del significato*. È come schedare ogni pagina non per titolo, ma per *di cosa parla*.
2. **Poi (a ogni domanda): trova i pezzi più vicini.** Quando arriva una domanda, ne calcola
   l'impronta e restituisce i pezzi il cui significato le somiglia di più — anche se usano parole
   diverse. E ti dice **da quale file e punto** arrivano, così la risposta è verificabile.

## L'immagine

Pensa a un bibliotecario che ha letto tutti i libri e li ha schedati per argomento. Tu chiedi «cerco
qualcosa sui motori a vapore» e lui ti porta i tre libri giusti — anche quelli che in copertina dicono
"locomotive" o "macchine termiche". La parola non coincide, l'argomento sì.

## Perché è utile

- Trovi le cose **anche senza sapere come sono state chiamate**.
- Ogni risposta arriva **con la fonte**: niente "fidati", c'è il riferimento.
- È **veloce**: il lavoro pesante (schedare) è fatto in anticipo; la ricerca è istantanea.

---

*Dettaglio tecnico:* il nucleo che fa tutto questo è il [[retrieval-core]]; le due fasi (schedare e
cercare) sono in [[indexing-and-retrieval]]. I "modi di cercare" più o meno furbi: [[i-modi-di-cercare]].
