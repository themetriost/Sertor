---
title: Sertor in parole semplici (panoramica per non tecnici)
type: explainer
tags: [non-tecnici, panoramica, prodotto, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/syntheses/roadmap.md", "wiki/concepts/retrieval-core.md", "README.md"]
---

# Sertor in parole semplici

> **A chi serve questa pagina.** È l'ingresso per chi vuole capire *cosa fa* Sertor e *perché*
> senza entrare nel codice. Niente gergo: ogni concetto è spiegato con un'immagine quotidiana. Da
> qui scendi alle singole capacità; ognuna ha un rimando «dettaglio tecnico» per chi vuole di più.

## Il problema che risolve

Un progetto software è fatto di tanto **codice** e tanta **documentazione**: spesso migliaia di file.
Quando qualcuno — una persona o un assistente AI — ha una domanda («dove si gestisce il login?»,
«come funziona questa parte?»), la risposta è lì dentro, ma **trovarla è una fatica**: bisogna sapere
dove cercare e leggere a mano.

**Sertor è il bibliotecario di quel progetto.** Legge tutto in anticipo, lo organizza, e quando arriva
una domanda ti porta *le pagine giuste*, citando da dove vengono. Non *risponde* lui (a quello pensa
l'assistente AI): Sertor è quello che **trova e porge il materiale pertinente**, in fretta e con la
fonte.

## L'idea in una frase

> Dare a qualunque progetto una **memoria interrogabile**: una sola fonte dove convivono il *come*
> (il codice) e il *perché* (la documentazione), così che un assistente AI risponda basandosi su
> quel progetto e non su impressioni generiche.

## Perché conta

Un assistente AI senza Sertor risponde "a memoria", con il rischio di inventare. Con Sertor risponde
**ancorato a ciò che è davvero scritto nel progetto**, e può citare la fonte. È la differenza tra un
consulente che tira a indovinare e uno che ti mostra la pagina del manuale.

## Le capacità, una per una (in parole semplici)

| Capacità | In una riga | Spiegazione |
|---|---|---|
| **Cercare nel progetto** | Il bibliotecario che trova le pagine giuste | [[ricerca-codice-e-documenti]] |
| **I modi di cercare** | Quattro tecniche, dalla più semplice alla più furba | [[i-modi-di-cercare]] |
| **Il quaderno che cresce** | Una memoria scritta che si arricchisce a ogni sessione | [[wiki-che-cresce]] |
| **Il collegamento con l'assistente** | La presa a cui l'AI si attacca per usare Sertor | [[collegamento-con-l-assistente]] |
| **Metterlo su un progetto** | Installazione con un comando, senza disordine | [[installare-su-un-progetto]] |
| **Robusto ed economico** | Non si pianta e non spreca soldi | [[robusto-ed-economico]] |
| **Il pannello di controllo** 🚧 | Vederci dentro: costo, risparmio, salute (in sviluppo) | [[il-pannello-di-controllo]] |

## Due parole sul "come ci fidiamo"

Sertor **usa sé stesso** per documentarsi (lo chiamiamo *dogfooding*): tiene un proprio quaderno e lo
interroga con i propri strumenti. È il modo migliore per accorgersi se qualcosa non funziona — lo
proviamo addosso tutti i giorni.

---

*Dettaglio tecnico:* l'architettura del prodotto è in [[retrieval-core]]; lo stato e la direzione in
[[roadmap]].
