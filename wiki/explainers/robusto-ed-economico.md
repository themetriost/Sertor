---
title: Robusto ed economico (in parole semplici)
type: explainer
tags: [non-tecnici, hardening, affidabilità, costo, cache, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/concepts/retrieval-confidence.md", "wiki/concepts/indexing-and-retrieval.md"]
---

# Robusto ed economico

Uno strumento che funziona "in laboratorio" non basta: nell'uso vero deve **non piantarsi** e **non
sprecare soldi**. Questo gruppo di migliorie (lo chiamiamo *hardening*, cioè "irrobustimento") serve
esattamente a questo. Quattro accorgimenti, in parole semplici.

## 1. Non si arrende al primo intoppo

Sertor, per schedare i testi, si appoggia a un servizio esterno. Ogni tanto quel servizio fa i
capricci per un istante (è occupato, la rete fa un singhiozzo). Prima questo bastava a far fallire
tutto. Ora Sertor **riprova qualche volta, con pause crescenti**, prima di dichiarare un errore: i
singhiozzi passeggeri non rovinano più il lavoro.

*L'immagine:* se il telefono dà occupato, riprovi tra poco invece di rinunciare alla chiamata.

## 2. Sa dire «non lo so»

A volte la risposta giusta a una domanda **non c'è** nel progetto. Uno strumento ingenuo restituirebbe
comunque qualcosa di vagamente simile — cioè, di fatto, una risposta sbagliata. Ora Sertor può misurare
quanto i risultati sono *davvero* pertinenti e, se sono troppo deboli, **non li propone**: dà
all'assistente il segnale per dire onestamente «su questo non ho materiale». Meglio un «non lo so» di
una risposta inventata.

*L'immagine:* un bibliotecario serio che, se non ha il libro, te lo dice — invece di rifilarti un libro
a caso.

## 3. Non ripaga due volte lo stesso lavoro *(nuovo — 2026-06-14)*

Schedare i testi costa (è un servizio a pagamento). Prima, a ogni aggiornamento, Sertor rifaceva il
lavoro **su tutto**, anche sulle parti rimaste identiche — come fotocopiare di nuovo un intero libro per
una virgola corretta. Ora tiene una **memoria**: «questo identico pezzo l'ho già elaborato, ecco il
risultato». La volta dopo rielabora **solo le parti cambiate** e le altre le ripesca gratis. Aggiornare
un progetto invariato non costa quasi più nulla.

È una memoria **prudente**: è spenta finché non la accendi tu, e se per qualche motivo si rovinasse,
Sertor semplicemente rifà il lavoro come prima — non si rompe mai per colpa sua.

*L'immagine:* un traduttore che tiene un quadernetto delle frasi già tradotte: le ripete a colpo
d'occhio, e si concentra solo sulle frasi nuove.

## 4. Mostra quanto costa *(nuovo — 2026-06-14)*

Prima, dopo un'elaborazione, non si sapeva quanto fosse costata. Ora Sertor **annota il consumo** (i
"gettoni" con cui il servizio misura e fattura). Così si vede a colpo d'occhio quanto costa un
aggiornamento e, soprattutto, **quanto fa risparmiare la memoria** del punto 3.

*L'immagine:* lo scontrino in fondo alla spesa: sai quanto hai speso e dove.

## In sintesi

| Accorgimento | A cosa serve |
|---|---|
| Riprova sugli intoppi | Non fallire per un singhiozzo passeggero |
| Sa dire «non lo so» | Niente risposte inventate quando il materiale manca |
| Memoria del già fatto | Non ripagare il lavoro già svolto |
| Mostra il costo | Vedere e misurare la spesa (e il risparmio) |

---

*Dettaglio tecnico:* il «sa dire non lo so» è il [[retrieval-confidence|segnale di confidenza]]; la
«memoria del già fatto» e il «mostra il costo» sono la [[indexing-and-retrieval|cache per content-hash
e i token nei log]].
