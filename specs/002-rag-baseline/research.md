# Phase 0 — Research: Motore RAG vettoriale (baseline)

Decisioni tecniche per FEAT-002. Formato: **Decisione / Razionale / Alternative**. Ancoraggio:
`prototype/01-baseline/` (comportamento di riferimento) + interfaccia reale di FEAT-001 (in `master`).

---

## R1 — Posizionamento e confine: motore come consumatore del nucleo (D-1, R-N1)

**Decisione.** Il motore è un nuovo sottopacchetto `sertor_core/engines/` con una classe
`BaselineEngine` che orchestra le primitive **pubbliche** del nucleo: `discover` (ingestione),
`chunk_document` (chunking), `EmbeddingProvider`/`VectorStore` (porte), `collection_name`
(namespacing) e l'`IndexingService`/`RetrievalFacade` esistenti. Nessuna logica di
ingestione/chunking/embeddings/store viene riscritta nel motore.

**Razionale.** D-1: FEAT-002 è il primo consumatore e serve a **validare l'interfaccia** del nucleo
(R-N1 di FEAT-001). Tenere il motore sottile rispetta DRY (Principio III) e mantiene il confine §4
("usa, non ridefinisce"). I motori RAG fanno parte del *core* per costituzione → stanno dentro
`sertor_core`, non in un pacchetto separato.

**Alternative.** (a) Pacchetto separato `sertor_rag`: spezzerebbe il core in due senza necessità →
respinta. (b) Reimplementare la pipeline nel motore: viola DRY/§4 → respinta.

---

## R2 — Rebuild-from-scratch idempotente: estensione `reset()` + `rebuild` (REQ-002, R-N1)

**Decisione.** Aggiungere alla porta `VectorStore` un metodo **`reset(collection)`** (svuota/elimina
la collezione) e all'`IndexingService.index()` un flag **`rebuild: bool = False`** che, quando vero,
esegue `reset(collection)` **dopo** l'embedding e **prima** dell'`upsert`. Implementare `reset` in
Chroma (`delete_collection`), `AzureSearchStore` e `InMemoryStore`. `BaselineEngine.index()` chiama
l'indexer con `rebuild=True`.

**Razionale.** REQ-002 chiede di "scartare l'indice precedente e ricostruirlo da zero": il solo
upsert idempotente (id stabili) non rimuove i chunk di file cancellati. `reset()` è la primitiva
mancante emersa proprio implementando il primo consumatore (la validazione d'interfaccia di R-N1).
È un'estensione **additiva e non-breaking**: gli adapter e i chiamanti esistenti non cambiano.

**Alternative.** (a) Solo upsert (no reset): lascerebbe chunk obsoleti → non soddisfa REQ-002 →
respinta. (b) Enumerare e cancellare tutti gli id: la porta non espone "list ids" e sarebbe più
fragile/lento di un reset → respinta. (c) Mettere `reset` solo nell'adapter Chroma senza toccare la
porta: violerebbe il Principio I (il motore dipenderebbe dall'adapter concreto) → respinta.

---

## R3 — Atomicità del rebuild rispetto agli errori di provider (REQ-004, NFR-004)

**Decisione.** Ordine della pipeline di indicizzazione in modalità rebuild:
`discover → chunk → embed (può fallire) → reset → upsert`. L'embedding (passo costoso e soggetto a
errore di provider) avviene **prima** del `reset`: se solleva `EmbeddingError`, l'indice preesistente
resta intatto (nessun parziale/corrotto). Il `reset`+`upsert` finali sono rapidi e locali.

**Razionale.** REQ-004/NFR-004 richiedono che un errore di provider non lasci un indice
parziale/corrotto. Resettare prima di embeddare distruggerebbe l'indice vecchio anche in caso di
fallimento. L'ordine "embed-then-swap" dà atomicità pratica senza transazioni distribuite.

**Alternative.** (a) reset → embed → upsert: a rischio di indice vuoto se l'embed fallisce →
respinta. (b) Indicizzare in una collezione temporanea e fare swap atomico dei nomi: più robusto ma
richiede rename di collezione (non supportato uniformemente da Chroma/Azure) → over-engineering per
l'MVP (Principio III), riconsiderabile post-MVP.

---

## R4 — Policy di errore esplicito su indice mancante (REQ-009 vs nucleo)

**Decisione.** `BaselineEngine.query()` controlla `store.exists(collection)`; se l'indice non esiste
solleva **`IndexNotFoundError`** (nuova eccezione di dominio) con messaggio azionabile ("costruisci
l'indice prima di interrogare"). Provider non disponibile in query → l'`EmbeddingError` del nucleo
si propaga (REQ-010).

**Razionale.** È una **differenza voluta** rispetto alla `RetrievalFacade` del nucleo, che su indice
assente restituisce `[]` + warning (REQ-028 di FEAT-001): a livello di *libreria/nucleo* l'assenza è
uno stato lecito; a livello di *motore baseline* (REQ-009) è un errore d'uso che va segnalato
esplicitamente all'operatore. Il motore quindi **non** delega questo caso alla facade ma lo gestisce
prima. Coerente con Principio IV (errori espliciti, niente vuoto silenzioso fuori contesto).

**Alternative.** (a) Riusare la facade e restituire `[]`: violerebbe REQ-009 → respinta. (b) Far
cambiare comportamento alla facade del nucleo: romperebbe REQ-028 di FEAT-001 e gli altri consumatori
→ respinta (la policy è del motore, non del nucleo).

---

## R5 — Valutazione della pertinenza: hit-rate@k e MRR@10 (REQ-011)

**Decisione.** Modulo `engines/evaluation.py` con una funzione `evaluate(engine, ground_truth,
ks=(1,3,5,10)) -> EvalReport`. `ground_truth` = lista di `(query, expected_paths)`. Per ogni query
si prende il top-10 dal motore; **hit@k** = frazione di query in cui almeno un `expected_path` compare
nei primi k risultati; **MRR@10** = media dei reciproci del rango del primo risultato pertinente
(0 se assente nei primi 10). Un risultato è pertinente se il suo `path` è tra gli `expected_paths`.

**Razionale.** Replica le metriche di `prototype/01-baseline/evaluate.py` (hit@1/3/5/10, mrr@10),
rendendole una capacità testabile del motore (Principio V: qualità misurata). Il ground-truth è un
input esterno (A-4): il motore non lo genera.

**Alternative.** (a) precision/recall completi: utili ma il prototipo usa hit-rate/MRR come standard →
allinearsi al baseline (REQ-011). (b) Soglie hardcoded di accettazione: contro DA-1/DA-3 ("misurare
prima") → le soglie si fissano alla misura, non nel codice.

---

## R6 — Identità della modalità (REQ-013/014)

**Decisione.** `BaselineEngine` espone un attributo di classe `name = "baseline"` (nome stabile) e,
per costruzione, usa **solo** retrieval per similarità vettoriale (nessuna chiamata a meccanismi
ibridi/grafo/agentici, che non esistono ancora). La selezione/composizione delle modalità è demandata
a `build_baseline_engine()` nel composition root; un registro di modalità completo è **fuori MVP**
(YAGNI) e arriverà quando esisteranno più motori (FEAT-004/005/006).

**Razionale.** REQ-013 chiede un nome stabile e indipendenza dalle altre modalità; REQ-014 che la
baseline usi solo il vettoriale. Con un solo motore esistente, un attributo `name` + il composition
root bastano. Evita un framework di modalità prematuro (Principio III).

**Alternative.** (a) Registry/plugin di modalità ora: over-engineering senza altri motori → respinta,
rinviato a quando servirà (FEAT-004+). (b) Enum globale delle modalità: idem, prematuro.

---

## R7 — Soglie di pertinenza/performance: misurate, baseline prototipo (DA-1/DA-3, SC-002)

**Decisione.** Nessuna soglia numerica fissata nel codice/piano: la valutazione (R5) **misura**
hit-rate@k/MRR su un corpus con ground-truth; la soglia di accettazione si fissa alla misura, con il
**prototipo come baseline** (azure-small hit@5 ≈ 0.80/MRR ≈ 0.83; ollama hit@5 ≈ 0.67) e soglia
ridotta ammessa per il provider locale (DA-3). Il test di soglia resta `xfail` finché il ground-truth
reale non è disponibile (come in FEAT-001).

**Razionale.** DA-1/DA-3 risolte con "misurare prima"; SC-002 chiede pertinenza *misurata*, non un
numero arbitrario.

**Alternative.** Fissare soglie ora → arbitrario, contro DA-1 → respinta.

---

## Sintesi NEEDS CLARIFICATION risolti

| Tema | Risolto in | Esito |
|------|-----------|-------|
| Confine motore↔nucleo | R1 | engines/ consuma il nucleo, niente duplicazione |
| Rebuild-from-scratch | R2 | `reset()` su porta + flag `rebuild` (additivo) |
| Atomicità su errore provider | R3 | embed-then-swap (reset dopo embed) |
| Indice mancante in query | R4 | `IndexNotFoundError` esplicito (policy del motore) |
| Metriche di qualità | R5 | hit-rate@k + MRR@10 su ground-truth |
| Identità modalità | R6 | nome stabile `baseline`, no registry (YAGNI) |
| Soglie | R7 | misurate, baseline prototipo (DA-1/3) |

Tutti i NEEDS CLARIFICATION tecnici sono risolti → si procede alla Phase 1.
