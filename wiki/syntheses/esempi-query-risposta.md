---
title: Vetrina di esempi — query → risposta per motore
type: synthesis
tags: [RAG, retrieval, examples, demo, comparison]
created: 2026-05-28
updated: 2026-05-28
sources: [ESEMPI.md]
---

# Vetrina di esempi — query → risposta per motore

Una sintesi pratica di **cosa fa e come risponde ciascun motore di retrieval** che abbiamo costruito.
Per gli esempi completi e il runbook tecnico, vedi [`../../ESEMPI.md`](../../ESEMPI.md) e [`../../DEMOS.md`](../../DEMOS.md).

## I quattro motori: una scelta consapevole

| Motore | Specialità | Quando usarlo | Costo | Tipo risposta |
|---|---|---|---|---|
| **[[01-baseline]]** (denso) | Ricerca per **significato**; capisce il senso della domanda | Domande a parole tue ("come si fa...") | Gratis/embedding | File/chunk più pertinenti |
| **[[02-hybrid-reranking]]** | Significato **+ parole/simboli esatti** | Cerchi nomi precisi (`OAuth2PasswordBearer`) | Gratis/embedding + rerank | Chunk ordinati per relevance |
| **Grafo del codice (AST)** | Conosce la **struttura**: chi-definisce-cosa, chi-chiama-chi | Navigare il codice con precisione (dov'è?, chi usa?) | **Gratis**, deterministico | File:riga + relazioni esatte |
| **[[03-graphrag]]** (GraphRAG) | **Risponde** sintetizzando in linguaggio naturale | Vuoi una spiegazione, non un elenco | LLM ($ per query) | Risposta scritta con citazioni |

---

## Insight dal testa-a-testa

Abbiamo interrogato tutti e quattro sui problemi reali e scoperto che **nessuno domina tutto**:

### "Come gestisce FastAPI l'autenticazione?"
- **Baseline / Hybrid** → file giusti (`tutorial/security/oauth2-jwt.md`, `reference/security/index.md`)
- **Grafo AST** → struttura: `OAuth2PasswordBearer` definita in `security/oauth2.py:433`; chi la usa
- **GraphRAG** → **spiegazione completa** (OAuth2 / JWT / HTTP Basic / API key / OpenID Connect / hashing)
  - *→ Vince per "capire il concetto"*

### "Chi chiama `HTTPException` nel codice?"
- **Baseline / Hybrid** → testo generico su error handling (non la lista vera)
- **Grafo AST** → **lista esatta: 10 funzioni + file:riga**
  - *→ Unico che risponde davvero (il vettoriale restituisce "testo correlato", non la risposta strutturale)*
- **GraphRAG** → lo capisce, ma non è il suo punto di forza

### "Voglio abilitare CORS"
- **Baseline / Hybrid** → `tutorial/cors.md` ✅ (la pagina giusta)
- **GraphRAG** → spiega *come* (middleware, origini consentite…)
- *→ Per trovare la pagina bastano Baseline/Hybrid; per una spiegazione GraphRAG*

---

## Conferma della tesi dual-RAG

L'osservazione critica: ogni motore eccelle in un aspetto diverso e gli altri hanno un limite onesto.

1. **Vettoriale (Baseline):** preciso sul significato, ma non "conosce" il codice strutturalmente.
2. **Ibrido (Hybrid):** aggiunge le parole esatte, ma comunque non sa "chi chiama chi".
3. **Grafo AST:** perfetto per domande di struttura (dov'è?, chi chiama?), ma cieco sul significato ("perché?" e spiegazioni).
4. **GraphRAG:** risponde con sintesi, ma richiede indicizzazione e costo LLM; non è sempre preciso sugli aspetti strutturali (la re-export da Starlette lo confonde).

**Conclusione:** Né un unico motore basta. Il progetto prevede un **retrieval orchestrato** (vedi [[architettura-target]])
che **fonde struttura (grafo AST) + semantica (vettoriale) + sintesi (GraphRAG)** in un unico assistente.

---

## Nella pratica (scelta per caso d'uso)

- **Cerchi "background tasks"?** → [[01-baseline]] troverà subito la pagina.
- **Cerchi il nome della funzione `jsonable_encoder`?** → [[02-hybrid-reranking]] aggiunge la corrispondenza testuale.
- **Ti chiedi "dov'è definito `OAuth2PasswordBearer`" o "chi chiama `HTTPException`"?** → Grafo AST è deterministico e preciso.
- **Vuoi imparare come FastAPI gestisce la sicurezza?** → [[03-graphrag]] ti dà una spiegazione coerente.

---

## Per approfondire

- Esempi completi (10+ query concrete): [`../../ESEMPI.md`](../../ESEMPI.md)
- Runbook e comandi eseguibili: [`../../DEMOS.md`](../../DEMOS.md)
- Dettagli tecnici di ogni motore:
  - [[01-baseline]] — chunking, embedding, similarity search
  - [[02-hybrid-reranking]] — BM25 + dense + reranking
  - [[03-graphrag]] — AST custom (Tappa 3A) + Microsoft GraphRAG (Tappa 3C)
- Architettura target e roadmap: [[architettura-target]]
