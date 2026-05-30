# Esempi — "ho cercato questo, mi ha restituito quello"

Una vetrina concreta di **cosa fa ciascun motore di ricerca** che abbiamo costruito, con
domande reali e risposte reali sul codice e la documentazione di FastAPI. Niente comandi qui:
per quelli c'è il runbook tecnico [`DEMOS.md`](DEMOS.md).

I quattro motori, in una riga:

| Motore | In parole semplici | Bravo quando… |
|---|---|---|
| **Baseline (denso)** | cerca **per significato** (capisce il senso della domanda) | fai una domanda a parole tue |
| **Hybrid** | significato **+ parole/simboli esatti** | cerchi un nome preciso (`OAuth2PasswordBearer`) |
| **Grafo del codice (AST)** | conosce la **struttura**: chi-definisce-cosa, chi-chiama-chi | vuoi navigare il codice con precisione |
| **GraphRAG** | **risponde** sintetizzando, in linguaggio naturale | vuoi una spiegazione, non un elenco di file |

> Gli esempi di Baseline e Hybrid usano il provider di embedding migliore (`azure-large`).

---

## 1) Baseline — ricerca "per significato"

Faccio una domanda a parole mie; mi restituisce i pezzi di documentazione/codice più pertinenti.

**Ho cercato:** *"run a background task after returning the response"*
**Mi ha restituito:**
- `docs/en/docs/tutorial/background-tasks.md` ✅ (la pagina giusta, in cima)

**Ho cercato:** *"enable CORS for cross-origin requests"*
**Mi ha restituito:**
- `docs/en/docs/tutorial/cors.md` ✅ (i primi 3 risultati sono tutti da questa pagina)

**Ho cercato:** *"return a custom HTML response"*
**Mi ha restituito:**
- `fastapi/openapi/docs.py` e `docs/en/docs/advanced/custom-response.md` ✅

> 👍 Capisce domande in linguaggio naturale anche se non contengono le parole esatte del testo.
> 👎 Non garantisce il nome esatto di un simbolo e la qualità dipende molto dal modello di
> embedding (col modello locale debole a volte restituisce rumore — vedi nota in `DEMOS.md`).

---

## 2) Hybrid — significato **+** parole esatte

Unisce la ricerca per significato con quella per parole letterali (utile per i **nomi esatti**
del codice).

**Ho cercato:** *"jsonable_encoder"* (nome esatto di una funzione)
**Mi ha restituito:**
- `docs/en/docs/reference/encoders.md`, `fastapi/exception_handlers.py`, l'esempio `docs_src/encoder/…` ✅

**Ho cercato:** *"split a large app into multiple routers"* (domanda a parole mie)
**Mi ha restituito:**
- `docs/en/docs/tutorial/bigger-applications.md` ✅ (la guida su come spezzare l'app con `APIRouter`)

> 👍 Il meglio dei due mondi: trova sia per concetto sia per termine esatto. È il più robusto
> per un codebase, dove contano i nomi precisi di classi/funzioni.

---

## 3) Grafo del codice (AST) — la **struttura**

Non cerca testo: conosce com'è fatto il codice. Risponde con precisione a "dov'è definito",
"chi lo chiama", "quali doc ne parlano".

**Ho chiesto:** *dov'è definito `OAuth2PasswordBearer`?*
**Mi ha risposto:**
- `fastapi/security/oauth2.py:433` — *class OAuth2PasswordBearer* ✅ (file **e riga**)

**Ho chiesto:** *chi chiama `HTTPException`?*
**Mi ha risposto:**
- 10 funzioni, es. `create_item`, `read_main` in `docs_src/app_testing/…` ✅ (lista esatta)

**Ho chiesto:** *quali documenti parlano di `APIRouter`?*
**Mi ha risposto:**
- `advanced/custom-response.md`, `advanced/openapi-callbacks.md`, … ✅

**Ho chiesto:** *dammi il contesto di `BackgroundTasks`* (vista d'insieme)
**Mi ha risposto:**
- **Definizione:** `fastapi/background.py:11` (class)
- **Chi la usa:** `solve_dependencies` in `fastapi/dependencies/utils.py:598`
- **Doc collegati:** `tutorial/background-tasks.md`, `reference/background.md`

> 👍 Preciso, deterministico, gratis: dà file:riga e relazioni esatte.
> 👎 Non capisce domande a parole tue e non "spiega": è una mappa, non un narratore.

---

## 4) GraphRAG — **risponde** in linguaggio naturale

Non ti dà una lista di file: ti dà una **risposta scritta**, sintetizzando codice e
documentazione, con citazioni alle fonti.

**Ho chiesto:** *cos'è `OAuth2PasswordBearer`?*
**Mi ha risposto (sintesi):**
> «È una classe di sicurezza di FastAPI (sottoclasse di `OAuth2`) che estrae il **token Bearer**
> dall'header `Authorization`. Si usa come dependency con `Depends()` e un `tokenUrl` (es.
> l'endpoint `/token` con `OAuth2PasswordRequestForm`); se il token manca risponde **401**.
> Da sola **non valida né decodifica** il token: quella logica la scrivi tu.»

**Ho chiesto:** *come funziona la dependency injection con `Depends`?*
**Mi ha risposto (sintesi):**
> «`Depends()` dichiara ciò di cui una path operation ha bisogno e FastAPI lo fornisce a runtime.
> Serve per logica riusabile (parsing, autenticazione, header/cookie/token). Supporta
> **sub-dependencies** (un albero risolto automaticamente), il caching (`use_cache=False` per
> disattivarlo), uno `scope`, e dipendenze con `yield` per setup/teardown.»

**Ho chiesto:** *come gestisce FastAPI l'autenticazione e la sicurezza?*
**Mi ha risposto (sintesi):**
> «Tutto ruota attorno alla **dependency injection** (`Depends`/`Security`). Approcci principali:
> **OAuth2** password-bearer, **JWT** (PyJWT), schemi **HTTP** (Basic/Bearer/Digest), **API key**
> (header/query/cookie), **OpenID Connect**, scope di autorizzazione, hashing delle password
> (Argon2), e gestione errori con `HTTPException`/`401`.» *(con citazioni ai report delle community)*

> 👍 Dà una risposta pronta da leggere, collegando concetti sparsi su più file.
> 👎 Costa (chiamate a un LLM) ed è più lento; serve un'indicizzazione preventiva.

---

## 5) Stessa domanda, motori diversi (testa a testa)

Qui si capisce **quale scegliere quando**: la stessa domanda data ai quattro motori.

### ❓ "Come gestisce FastAPI l'autenticazione?"
| Motore | Cosa restituisce |
|---|---|
| Baseline | i chunk giusti: `tutorial/security/index.md`, `tutorial/security/oauth2-jwt.md` |
| Hybrid | idem, + `reference/security/index.md` (aggancia anche il riferimento tecnico) |
| Grafo AST | la **struttura**: `OAuth2PasswordBearer` definita in `security/oauth2.py:433`, chi la usa, doc collegati |
| **GraphRAG** | una **spiegazione** completa (OAuth2/JWT/HTTP/API key/OpenID/hashing) — *la più adatta a "capire"* |

→ Per **leggere e capire** vince GraphRAG; per **andare al file giusto** bastano Baseline/Hybrid.

### ❓ "Chi usa `HTTPException` nel codice?"
| Motore | Cosa restituisce |
|---|---|
| Baseline | testo correlato: `tutorial/handling-errors.md` (parla di errori, **non** la lista dei chiamanti) |
| **Grafo AST** | la **lista esatta**: 10 funzioni che la chiamano, con file e riga — *l'unico che risponde davvero* |

→ Per le domande **strutturali** ("chi chiama", "dov'è definito") solo il grafo AST è preciso.

### ❓ "Voglio abilitare CORS"
| Motore | Cosa restituisce |
|---|---|
| Baseline / Hybrid | `tutorial/cors.md` ✅ (la pagina giusta) |
| Grafo AST | poco utile: non è una domanda di struttura del codice |
| GraphRAG | spiega *come* si fa (middleware CORS, origini consentite…) |

→ Per **trovare la pagina** bastano Baseline/Hybrid; per **una spiegazione** GraphRAG.

---

## 6) Agentic RAG — l'**agente** sceglie da solo gli strumenti

I motori 1–4 li scegli tu. Nella Tappa 04 un **agente LLM** riceve la domanda e decide da
sé quali strumenti usare, itera, e risponde **citando i file**. Esempi reali (uno per
motore di orchestrazione, a parità di strumenti) sono generati automaticamente in
[**ESEMPI-agentic.md**](04-agentic-rag/ESEMPI-agentic.md) dall'eval `04-agentic-rag/evaluate.py`.

## In sintesi: quale uso, quando?

- **So cosa cerco a parole mie** → Baseline.
- **Cerco un nome/simbolo preciso** → Hybrid.
- **Voglio navigare il codice** (definizioni, chiamanti) → Grafo AST.
- **Voglio una risposta spiegata** → GraphRAG.
- **Voglio solo fare la domanda e lasciar lavorare l'agente** → Agentic RAG (Tappa 04).

Nessuno vince su tutto: l'idea del progetto (vedi [`wiki/syntheses/architettura-target.md`](wiki/syntheses/architettura-target.md))
è **combinarli** — struttura del grafo + ricerca semantica + sintesi — in un unico assistente.
L'Agentic RAG è il passo che li orchestra automaticamente.
