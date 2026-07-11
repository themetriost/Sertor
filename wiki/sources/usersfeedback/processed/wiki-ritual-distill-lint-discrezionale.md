---
title: "Segnalazione utente — Wiki Ritual (record→distill→lint) puramente discrezionale, rischio di skip silenzioso"
type: source
tags: [usersfeedback, wiki-ritual, claude-md, distill, lint, drift, definition-of-done]
created: 2026-07-01
updated: 2026-07-02
source: utente progetto hermes-nunzio-ha (segnalazione, 2026-07-01)
status: elaborata (→ E10-FEAT-026 «Rituale wiki resistente allo skip silenzioso di distill/lint», 2026-07-02)
---

# Segnalazione: il Wiki Ritual (record → distill → lint → explainer) è puramente discrezionale

> **Fonte:** utente del progetto `hermes-nunzio-ha` (installazione Sertor via Claude Code),
> 2026-07-01. Riportata qui la segnalazione + l'analisi fatta insieme all'assistente nella
> stessa sessione in cui il fenomeno è stato osservato. Da elaborare → eventuale backlog/FEAT;
> poi spostare in `processed/`.

## Segnalazione (cosa è successo)

Il blocco `<!-- SERTOR:WIKI-RITUAL START/END -->` iniettato in `CLAUDE.md` definisce un
"Definition of Done" a 4 passi da eseguire alla chiusura di ogni step significativo di
lavoro:

1. **record** — pagine/backlink/`index.md`/log entry (esplicitamente delegabile all'agente `wiki-curator`)
2. **distill** — identificare entità/concetti durevoli e dar loro una pagina dedicata in `concepts/`/`tech/` (dichiarato "judgment → stays in the main flow")
3. **semantic lint** (livello B) — verificare che il wiki non sia scollegato dalla realtà del repo/codice/VCS (dichiarato "judgment → stays in the main flow")
4. **explainer** — sintesi in linguaggio semplice per capacità significative (idem, "judgment")

In una sessione di lavoro reale, l'assistente ha chiuso due step significativi (due
amendment SpecKit a una feature già in produzione) delegando **solo** l'operazione
`record` all'agente `wiki-curator`, due volte di fila. In entrambi i casi:

- **distill** è stato oggetto di un giudizio ("non serve una pagina concept/tech dedicata,
  sono refinement di una feature esistente, non nuove entità") ma **quel giudizio è stato
  scritto solo dentro il brief per il sub-agente**, mai dichiarato all'utente né tracciato
  in un posto visibile.
- **lint** **non è stato eseguito affatto**, per nessuna delle due chiusure di step.

L'utente si è accorto dell'anomalia solo ispezionando manualmente l'output del wiki
("vedo i log ma non vedo creazione di nuove pagine, non vedo nuovi concetti, non vedo
lint, perché?"). Quando l'assistente ha eseguito il lint su richiesta esplicita, ha
trovato una contraddizione reale e non banale **proprio nel blocco Executive Summary**
di `wiki/syntheses/roadmap.md` (`<!-- EXEC:START/END -->`) — il blocco che il proprio
hook di avvio sessione mostra automaticamente all'utente a ogni conversazione:

- Affermava ancora una versione/numero-test della skill (v1.1.0, 48 test) superati da ore
  dallo stesso lavoro appena fatto nella sessione (v1.1.2, 80 test).
- Affermava che una capacità (consultazione mobile via un plugin di sync) fosse
  disponibile/funzionante, quando nella **stessa sessione** l'utente aveva verificato che
  non lo era ed era stata esplicitamente rimandata.
- Il "prossimo passo consigliato" indicava un'attività già completata da giorni.

La contraddizione è rimasta nel wiki per l'intera sessione — nonostante due cicli di
`record` "completati" — semplicemente perché nessuno dei due passi di giudizio (distill,
lint) è mai stato eseguito, e **nulla lo ha segnalato come mancante**. Il fallimento è
stato silenzioso: nessun errore, nessun warning, nessun output mancante evidente.

## Causa (analisi dell'utente + assistente)

Il rituale vive **solo come prosa** dentro `CLAUDE.md`: è una lista puntata da
"ricordarsi di fare", senza alcun meccanismo strutturale che forzi la dichiarazione o il
completamento di ciascun passo. Delegare `record` a `wiki-curator` è facile da scambiare
(anche per l'assistente stesso) per "aver coperto il rituale", perché non esiste una
checklist tracciata che distingua "fatto" da "saltato in silenzio".

## Domanda per il team Sertor

C'è qualcosa che si può fare, lato distribuzione del rituale (il testo/meccanismo
iniettato in `CLAUDE.md` e/o gli strumenti collegati, es. `wiki-curator`), per **renderlo
meno discrezionale** e più resistente a questo tipo di skip silenzioso? Alcune idee
emerse in sessione (da valutare, non prescrittive):

1. **Checklist tracciata esplicitamente.** Alla chiusura di uno step, generare/suggerire
   automaticamente 3–4 task tracciabili (uno per record/distill/lint/explainer) invece di
   lasciare il rituale come prosa nel prompt — un passo saltato diventerebbe un task
   aperto/non chiuso e visibile, non un'assenza silenziosa.
2. **Il sub-agente di record segnala sempre candidati per distill/lint.** `wiki-curator`
   ha già gli strumenti (Read/Grep/Bash) per confrontare le pagine toccate con lo stato
   attuale del repo e restituire, come output esplicito della propria run, sia candidati
   a "entità durevole" (per distill) sia contraddizioni potenziali (per lint). Il giudizio
   finale (creare la pagina o no, correggere o no) resterebbe nel main flow, ma la
   *scoperta* dei candidati smetterebbe di dipendere dalla memoria/discrezione
   dell'assistente.
3. **Formato di dichiarazione obbligatorio a fine step.** Richiedere che la chiusura di
   ogni step produca una riga sintetica tipo `Rituale: record ✅ · distill: <verdetto> ·
   lint: <verdetto>` — anche un giudizio "non necessario" andrebbe bene, ma dichiarato,
   non omesso.
4. **Lint periodico indipendente dalla sessione.** Un controllo di coerenza wiki↔repo
   schedulabile (es. via uno strumento CLI dedicato tipo `sertor-wiki-tools lint`), che
   non dipenda dal fatto che l'assistente se ne ricordi durante una sessione di lavoro.

## Perché sembra rilevante

Il wiki è pensato come "fonte di verità cumulativa" che sostituisce la ricostruzione a
memoria del contesto a ogni sessione (golden rule del rituale stesso). Se i passi di
giudizio (distill, lint) restano discrezionali e silenziosamente saltabili, il wiki può
accumulare drift silenzioso proprio nel punto in cui gli utenti ripongono più fiducia
(l'Executive Summary mostrato automaticamente a ogni avvio) — un rischio che sembra
contraddire l'obiettivo dichiarato della capacità.
