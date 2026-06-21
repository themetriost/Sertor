# Quickstart — Misurare e migliorare la fusione code+doc (FEAT-003)

Percorso utente end-to-end della capacità. Tutto **local-first e deterministico** (zero LLM nel run;
l'unico modello è l'embedder). Vehicle: `sertor-rag eval` (Principio XI).

> **Prerequisito:** il progetto è **già indicizzato** (`sertor-rag index .`). La genesi assistita
> richiede un indice popolato.

## 1. Costruire il set NL multi-superficie (giudizio — skill o a mano)

Aggiungi casi NL con l'intento esplicito. L'`intent` decide la superficie misurata e i tipi attesi:

```powershell
# caso code-oriented ("dove è definito/implementato") → search_code, atteso CODE
sertor-rag eval add-case --kind nl --intent code `
  --query "where the hybrid engine fuses BM25 and dense results" `
  --expected "src/sertor_core/engines/hybrid.py"

# caso doc-oriented ("perché/come funziona") → search_docs, atteso DOC
sertor-rag eval add-case --kind nl --intent doc `
  --query "why combined search merges results by score across collections" `
  --expected "src/sertor_core/services/retrieval.py"

# caso cross-artefatto (requisito→implementazione) → search_combined, atteso DOC E CODE
sertor-rag eval add-case --kind nl --intent both `
  --query "requirements of the fused code+doc quality feature and where measured" `
  --expected "requirements/retrieval-qualita/qualita-search-code-nl/requirements.md,src/sertor_core/services/eval/fusion.py"
```

Un path atteso assente dall'indice → warning + richiede `--confirm` (nessuno stato parziale).

**Genesi assistita (consigliata, US5/P2):** invece di scrivere a mano, delega all'agente via la skill
`eval-suite-author` (estesa): legge il corpus via MCP/CLI, **propone** candidati `query → expected +
intent` (inclusi i «needs both»), tu approvi, e **solo gli approvati** sono persistiti via il vehicle. Il
run resta deterministico (confine D↔N).

## 2. Registrare le baseline per-superficie (prima di ogni intervento)

```powershell
sertor-rag eval run --fused --record-baseline
```
Registra in `eval/baseline.toml` (sezione `[fused_baseline]`) hit@k/MRR distinti per
`search_code`/`search_docs`/`search_combined` + la **fusion coverage** del combined. Non tocca la
baseline IR esistente né i casi.

## 3. Misurare (hit@k/MRR per-superficie + fusion coverage)

```powershell
sertor-rag eval run --fused
```
Output: per-superficie hit@k/MRR + **fusion coverage** riportata **accanto**. Un caso `both` che è
`hit@k` ma trova **solo doc** (o solo codice) è marcato come **GAP** (REQ-022): hit@k non nasconde la
lacuna.

```
fusion coverage: 0.50  (3/6 covered;  2 hit@k but NOT covered ← one type drowns the other)
  [covered] requirements of FEAT-003 and where implemented   doc+code
  [GAP    ] how the hybrid engine fuses BM25 and dense        doc only  (missing CODE)
```

Ri-eseguire a parità di indice/set → **numeri identici** (determinismo, SC-004).

## 4. Gate di non-regressione

```powershell
sertor-rag eval run --fused          # exit 1 se una superficie o la fusion coverage scende sotto baseline
```
Una misura sotto una baseline per-superficie (o sui casi IR esistenti) oltre `SERTOR_EVAL_TOLERANCE`
(default 0.0) → **exit non-zero** ed è respinta (gate, REQ-040). Una leva che migliora una superficie ma
**rompe la fusione** è respinta dal gate sul combined/fusion coverage (R-3).

## 5. Valutare una leva (giudizio — guidato da misura, P2/Should)

1. Abilita **una** leva opt-in (filtro metadata / contextual retrieval / query transformation — le loro
   manopole arrivano con FEAT-005/006/007; qui la leva è un seam opt-in, **spenta di default**).
2. Ri-misura: `sertor-rag eval run --fused`.
3. Confronta il delta per-superficie e di fusion coverage con la baseline. Una leva è un
   «miglioramento» **solo** con un lift misurato (≥ +0.05 sulla superficie rilevante o sulla fusion
   coverage — criterio di adozione, non gate). Una leva senza lift **non** si adotta; una con lift resta
   **spenta di default** finché un cambio di default non è deciso esplicitamente.
4. A leva spenta, numeri e **costo** tornano identici alla baseline (additività, SC-009).

## 6. JSON per automazione

Ogni comando accetta `--json` (equivalenza informativa col testo) per CI/script.

---

**Cosa NON fa qui:** non calibra `SERTOR_MIN_SCORE` (FEAT-004), non gira su cloud (FEAT-002), non
implementa le tecniche a regime (FEAT-005/006/007) — qui sono leve candidate valutate per misura.
