---
title: "Segnalazione utente — passo distill del Wiki Ritual ignorato per un'intera sessione, nessun segnale strutturale"
type: source
tags: [usersfeedback, wiki-ritual, claude-md, distill, lint, drift, definition-of-done]
created: 2026-07-01
updated: 2026-07-02
source: utente progetto Noetix (segnalazione, 2026-07-01)
status: elaborata (→ E10-FEAT-026 «Rituale wiki resistente allo skip silenzioso di distill/lint», 2026-07-02)
---

# Segnalazione: il passo "distill" del Wiki Ritual è stato ignorato per un'intera sessione

> **Fonte:** utente del progetto `Noetix` (installazione Sertor via Claude Code / `wiki-author`
> clonato in una skill di dominio `noetix-pipeline`), 2026-07-01. Riportata qui la segnalazione +
> l'analisi fatta insieme all'assistente nella stessa sessione in cui il fenomeno è stato osservato.
>
> **Nota di convergenza:** questa segnalazione è **indipendente** da
> `wiki-ritual-distill-lint-discrezionale.md` (progetto `hermes-nunzio-ha`, stessa data), ma
> descrive **lo stesso fenomeno strutturale** — il passo `distill` che si salta senza alcun segnale
> — osservato con una dinamica diversa. Due progetti diversi, stesso giorno, stesso gap: rafforza
> il segnale che non sia un caso isolato.

## Segnalazione (cosa è successo)

In una sessione di lavoro lunga e multi-step (cattura di un'idea, handoff, correzione di un
handoff), l'assistente ha eseguito con costanza il passo **record** (pagine, backlink, `index.md`,
log entry) e anche il passo **lint semantico B** (verifica conteggi/claim contro la realtà del
repo, incluso il controllo diretto dello stato di due repo esterni prima di un handoff). Il passo
**distill** è stato invece **completamente saltato**, nonostante il criterio fosse soddisfatto in
modo particolarmente evidente:

- Durante una correzione architetturale di un'idea (`SpecAudit`), è emerso un pattern di design a
  due ruoli (generatore bottom-up + comparatore top-down, analogo alla *back-translation*). Il
  pattern è stato descritto in prosa dentro la pagina.
- **Nella stessa sessione**, l'utente ha chiesto di catturare una nuova idea (`IdeaAudit`) che
  **riapplica esplicitamente lo stesso pattern** su un dominio diverso (verifica di handoff invece
  che di codice). L'assistente stesso ha scritto, nella pagina della nuova idea, che si trattava
  "dello stesso primitivo generatore/comparatore" — quindi il pattern era stato **notato**.
- Nonostante questo, il pattern è rimasto **non distillato** — nessuna pagina `concepts/`/`tech/`
  dedicata — per il resto della sessione, attraverso diversi cicli `record` + `lint` "completati
  con successo".

L'utente si è accorto dell'anomalia solo chiedendo esplicitamente all'assistente "stai facendo
tutti gli step del rituale wiki?" — a quel punto l'assistente ha fatto un audit a ritroso e
confermato l'omissione. **Nessun segnale strutturale** (output del tool, lint, messaggio) aveva
segnalato il gap prima di quel momento.

## Causa (analisi dell'assistente, a posteriori)

L'assistente ha ricostruito la propria causa radice così: il modulo di operazione specifico
invocato per catturare la nuova idea (`/idea`, un modulo `ops/*.md` costruito sopra `wiki-author`
per il dominio "pipeline di idee") ha un proprio checklist meccanico stretto — vault-first,
creazione pagina, aggiornamento board, log — che **non richiama il rituale più ampio**
(`record → distill → lint → explainer`). L'assistente ha potuto seguire quel modulo, completarlo
"con successo" secondo i suoi stessi criteri, e non considerare mai `distill`, perché quel passo
vive **solo come prosa/giudizio** nel `CLAUDE.md` di livello superiore, non nel modulo che ha
effettivamente guidato l'azione in quel momento.

In sintesi: quando un modulo di dominio più stretto viene costruito sopra `wiki-author`, il rituale
più ampio rischia di "non ereditarsi" automaticamente — il modulo stretto diventa il percorso
seguito, e ciò che non è nel suo checklist locale si perde per costruzione, non per scelta.

## Domanda per il team Sertor

Stessa domanda della segnalazione `hermes-nunzio-ha`, con un angolo aggiuntivo dato dalla dinamica
osservata qui — la propagazione del rituale ai moduli derivati:

1. **Segnale strutturale euristico.** Un tool come `sertor-wiki-tools scan`/`append-log` potrebbe
   rilevare candidati a distillazione — es. N pagine toccate nella stessa sessione/branch che
   condividono ≥2 backlink incrociati nuovi e nessuna nuova pagina in `concepts/`/`tech/` — e
   stampare un prompt esplicito ("possibile entità condivisa non distillata: rivedi?").
2. **Propagazione esplicita del rituale ai moduli derivati.** Se un progetto costruisce un layer di
   operazioni più stretto sopra `wiki-author` (come qui `noetix-pipeline`, che ne clona
   l'architettura), i singoli moduli `ops/*.md` dovrebbero **richiamare esplicitamente** il
   rituale completo (anche solo un riferimento/link al passo `distill`), non lasciarlo implicito
   nel solo playbook di livello superiore.
3. **Checklist esplicita a fine step**, magari emessa dal tool stesso dopo un `append-log`, tipo:
   `☐ record fatto · ☐ distill valutato? · ☐ lint B fatto? · ☐ explainer valutato?` — costringe una
   risposta esplicita (anche "no, non serve qui") invece di lasciare il passo cadere per omissione
   silenziosa. (Stessa proposta della segnalazione `hermes-nunzio-ha`, punto 3 — convergenza anche
   sulla proposta, non solo sul problema.)

## Perché sembra rilevante

Il valore del wiki come "second brain" dipende dal fatto che le entità durevoli vengano
effettivamente estratte in nodi propri, non lasciate diffuse in prosa sparsa tra più pagine — è
esattamente il meccanismo che rende il wiki più utile di una cronologia di log. Un passo di
giudizio che si può saltare senza che nulla lo segnali è un **fallimento silenzioso e cumulativo**:
il costo si nota solo a retrieval-time, molto più tardi, quando un concetto che avrebbe dovuto
essere un nodo cercabile non esiste da nessuna parte in forma distillata. Il fatto che due progetti
indipendenti abbiano osservato varianti dello stesso gap nello stesso giorno suggerisce che non sia
un caso isolato di disattenzione, ma un punto strutturale del design del rituale.
