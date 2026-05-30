---
title: EARS — Easy Approach to Requirements Syntax
type: concept
tags:
  - ears
  - requirements
  - methodology
  - atomic-requirements
created: 2026-05-30
updated: 2026-05-30
sources:
  - Alistair Mavin (Easy Approach to Requirements Syntax)
  - NASA/ESA best practices
---

# EARS — Easy Approach to Requirements Syntax

**EARS** è una metodologia pubblica e indipendente di **Alistair Mavin** (NASA/ESA)
per scrivere requisiti atomici, testabili e univoci in linguaggio naturale.

## Problema che risolve

Requisiti scritti male:
- Ambigui ("il sistema deve essere veloce") → difficili da testare.
- Accoppiati ("il sistema deve fare A, B e C") → difficili da tracciare isolatamente.
- Informali ("tipo un chatbot") → non verificabili.

EARS fornisce una **sintassi semplice e strutturata** (non pseudo-codice, linguaggio naturale)
che rende ogni requisito:
- **Atomico** — un'affermazione per requisito.
- **Testabile** — il test è implicito nella forma sintattica.
- **Tracciabile** — ID univoco per linkare codice/test/design.

## I 5 Pattern Fondamentali + Complex

### 1. Ubiquitous (U)

```
The system SHALL ALWAYS <action>.
```

Applicabile **sempre**, senza condizioni esterne.

**Esempi:**
- "REQ-001: The retriever SHALL ALWAYS return results sorted by relevance score."
- "REQ-002: The system SHALL ALWAYS validate API tokens on every request."

**Test:** verifica che il comportamento sussiste in qualunque condizione.

### 2. State-driven (S)

```
WHEN <condition/state>, the system SHALL <action>.
```

Il comportamento dipende da uno **stato** del sistema (o mondo esterno).

**Esempi:**
- "REQ-003: WHEN embedding model changes, the index SHALL be invalidated."
- "REQ-004: WHEN cache is full, the system SHALL evict least-recently-used entries."

**Test:** testa la transizione di stato; verifica azione nella nuova condizione.

### 3. Event-driven (E)

```
IF <event>, THEN the system SHALL <action>.
```

Il comportamento è **triggered** da un evento esterno.

**Esempi:**
- "REQ-005: IF a user query arrives, THEN the orchestrator SHALL route to appropriate tool."
- "REQ-006: IF Azure connectivity fails, THEN the system SHALL fall back to local LLM."

**Test:** simula evento; verifica azione entro SLA.

### 4. Optional Feature (O)

```
The system MAY <action> IF <condition>.
```

Comportamento **opzionale**, abilitabile da config o feature flag.

**Esempi:**
- "REQ-007: The system MAY cache embeddings IF RAG_BACKEND=azure."
- "REQ-008: The system MAY compress responses IF response_size > 1MB."

**Test:** verifica che il comportamento è disponibile se condizione sussiste; che non
rompe se feature è disabilitato.

### 5. Unwanted Behaviour (UB)

```
The system SHALL NOT <action> IF <condition>.
```

Controlla **cosa NON deve accadere**.

**Esempi:**
- "REQ-009: The system SHALL NOT expose API keys in logs."
- "REQ-010: The system SHALL NOT retry indefinitely on permanent errors."

**Test:** crea scenario che farebbe fallare il requite; verifica che il sistema lo previene.

### 6. Complex (C)

```
<descrizione libera con ID atomico, usando pattern multipli>.
```

Quando un requisito ha logica articolata (multi-fattoriale, OR/AND, condizioni nested).

**Esempi:**
- "REQ-011 (Complex): The retriever SHALL return top-k results from (dense retrieval
  AND BM25 sparse retrieval), merged via RRF and re-ranked by cross-encoder,
  UNLESS RAG_BACKEND=azure (in which case Azure AI Search hybrid is used)."

**Test:** scomponilo in sub-step e test.

## Proprietà EARS

1. **Atomico**
   - Un'affermazione logica per requisito (non "e" / "ma" / elenchi).
   - Facilita tracing isolato e test isolato.

2. **Unambiguo**
   - Verbi normativi chiari: SHALL (must), MAY (optional), SHALL NOT (forbidden).
   - Niente "dovrebbe", "potrebbe", "forse".

3. **Formale ma leggibile**
   - Non pseudo-codice; linguaggio naturale strutturato.
   - Chiunque (tecnico, PM, stakeholder) lo capisce.

4. **Testabile**
   - La sintassi suggerisce il test: condizione / azione / verifica.
   - Niente "misure" nebose (es. "veloce", "sicuro").

5. **Tracciabile**
   - ID REQ-NNN → linkabile in codebase (commenti, issue, test suite).
   - Design a valle referenzia i REQ; test sanno quali REQ coprono.

## Design Patterns con EARS

### Gerarchie di requisiti

Requisiti di alto livello (epic/user story) si scompongono in atomic EARS:
- **Epic:** "REQ-100: Authentication system"
- **User Story:** "REQ-101: Bearer token extraction"
- **EARS atomic:**
  - REQ-101a (U): "The auth module SHALL ALWAYS extract Bearer token from Authorization header."
  - REQ-101b (UB): "The auth module SHALL NOT accept malformed tokens."
  - REQ-101c (S): "WHEN token expires, the system SHALL return 401 Unauthorized."

### Acceptance Criteria

Ogni REQ-NNN ha colonna "Acceptance Criteria" (testablità esplicita):

| REQ ID | Pattern | Requirement | Acceptance Criteria |
|--------|---------|-------------|-------------------|
| REQ-001 | U | The retriever SHALL ALWAYS return results sorted by score | Top result score >= second result score for all queries |
| REQ-002 | S | WHEN cache is full, the system SHALL evict LRU | Oldest entry removed when capacity exceeded |

### Linking a Test & Code

Nel codebase:

```python
# REQ-001: The retriever SHALL ALWAYS return results sorted by score.
def retrieve(query, k=5):
    # Implementation ensures sorted output
    results = hybrid_search(query, k)
    # verify sorted by score [REQ-001]
    assert all(results[i].score >= results[i+1].score 
               for i in range(len(results)-1))
    return results
```

Nel test:

```python
def test_req_001_retriever_sorted_by_score():
    """REQ-001: The retriever SHALL ALWAYS return results sorted by score."""
    results = retrieve("OAuth2", k=5)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
```

## EARS in Context di RAG

### Example Set per RAG

**REQ-001 (Ubiquitous):** The retriever SHALL ALWAYS return results with non-zero relevance score.

**REQ-002 (Event-driven):** IF query contains code-specific symbols, THEN the orchestrator SHALL use symbol-based tool (find_symbol).

**REQ-003 (State-driven):** WHEN embedding model is swapped (e.g., nomic-embed-text → text-embedding-3-large), the index SHALL be rebuilt.

**REQ-004 (Optional):** The system MAY cache query embeddings IF RAG_BACKEND=azure.

**REQ-005 (Unwanted Behaviour):** The system SHALL NOT expose raw API keys in retrieved documents or logs.

**REQ-006 (Complex):** The dual-RAG fusion SHALL combine code context (from AST graph) and documentation context (from vector search), prioritizing exact symbol matches (AST) when score > threshold, falling back to semantic search otherwise.

## Best Practices

1. **Una riga = un requisito.** Se stai scrivendo "and"/"or" al primo livello, separa.

2. **Verbi normativi:** SHALL (obbligo), MAY (opzionale), SHALL NOT (proibito).
   - **Non usare:** "dovrebbe", "potrebbe", "è necessario", "si raccomanda" (ambigui).

3. **Condizioni esplicite.** Se c'è una condizione (WHEN/IF), mettila nel pattern, non nel testo.

4. **Metriche concrete.** "Veloce" → "response time < 1s". "Accurato" → "MRR@10 > 0.85".

5. **Testabilità first.** Se non sai come testarlo, il requisito è vago.

6. **Precedenza:** ordina per priorità (MoSCoW: Must, Should, Could, Won't) e traccia dipendenze.

## Link

- [[requirements-engineering]] — come usare EARS nel workspace.
