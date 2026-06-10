---
title: Diary vs Graph — le due memorie del wiki
type: concept
tags: [wiki, memoria, log, record, distill, llm-wiki]
created: 2026-06-10
updated: 2026-06-10
sources: [".claude/skills/wiki-author/ops/distill.md", ".claude/skills/wiki-author/log-craft.md", "CLAUDE.md"]
---

# Diary vs Graph — le due memorie del wiki

L'LLM Wiki tiene la conoscenza su **due superfici di memoria** con regole opposte:

- **Il diario** — il registro (`log/`, un file al giorno) e i record datati (`experiments/`). Risponde a
  *«cosa è successo, quando, perché»*. È **append-only**: la voce di ieri resta vera come testimonianza
  anche quando è superata; una correzione è una **nuova voce**, mai un edit della precedente.
- **Il grafo** — le pagine-entità (`concepts/`, `tech/`) e le sintesi. Risponde a *«cosa è vero adesso»*.
  Si **aggiorna in place**: qui una pagina stale è un difetto (bersaglio del lint B), non una testimonianza.

## Perché due memorie (e non una)

Una superficie sola fallisce in entrambe le direzioni. Se tutto è diario, la conoscenza durevole resta
**sepolta nelle voci datate** e ogni sessione la riscava da capo — l'antitesi del wiki cumulativo. Se tutto
è grafo, si perde la **provenienza** (chi ha deciso cosa, quando, in quale contesto) e la storia diventa
irricostruibile. Le due memorie si completano: il grafo dà lo stato, il diario dà la traccia che lo
giustifica.

## I tre strati operativi

La domanda ricorrente «ma la distillazione non assomiglia alla funzione che scrive il log?» si scioglie
distinguendo tre strati, non due:

| Strato | Natura | Chi lo fa | Operazione |
|---|---|---|---|
| **scrivano** | D (meccanico) | CLI [[wiki-tools]] | `append-log` / `upsert-index`: piazzano testo già curato, zero giudizio |
| **cronaca** | N (giudizio) | `record` | dal brief di uno step → voce di diario + record datato magro |
| **travaso** | N (giudizio) | `distill` | dal materiale di sessione → pagine-entità del grafo |

`record` e `distill` sono **duali**: lavorano sullo stesso materiale grezzo (il lavoro di sessione) ma
scrivono su memorie opposte — `record` cronicizza nel diario, `distill` consolida nel grafo. Per questo il
rituale di step li esegue **in sequenza** (punto 1 e punto 2), e per questo la delega li separa: la cronaca
è trascrizione rette dal brief (delegabile al curator), il travaso è giudizio (resta nel flusso
principale) — il confine di [[deterministic-vs-judgment]] applicato dentro la metà N.

## I tre ingressi di `distill`

Il travaso ha un solo giudizio (filtrare il durevole dall'effimero) ma tre provenienze dell'input
(generalizzazione del 2026-06-10, che chiude N2/REQ-030..033 di FEAT-003):

1. **di step** — il caso tipico del rituale: il record appena scritto, le entità in pagine;
2. **da backlog** — un vecchio record già grasso da assottigliare;
3. **da conversazione** — il *brief condensato* di una sessione intera (anche vecchia, mai registrata in
   tempo reale, o avvenuta altrove). Mai il transcript grezzo: chi invoca condensa prima. È il
   **paracadute** per quando il diario non è stato tenuto: il rituale è il tempo reale, questo ingresso è
   il recupero a posteriori.

## Vedi anche

- [[step-ritual]] — la disciplina che esegue cronaca e travaso a ogni step.
- [[deterministic-vs-judgment]] — il confine D↔N che fonda la separazione scrivano/cronaca-travaso.
- [[architettura-wiki-llm]] — dove i tre strati vivono nell'architettura del sistema-wiki.
- [[wiki-tools]] — lo scrivano deterministico (CLI).
