# ESEMPI — Agentic RAG (documentazione parlante, auto-generata)

> **File generato** da `04-agentic-rag/evaluate.py` (non modificare a mano). Mostra, per ogni
> domanda e per ogni motore, *cosa ho chiesto → cosa ha fatto l'agente → cosa mi ha risposto*.
> È la controparte divulgativa di [`ESEMPI.md`](../ESEMPI.md) per la Tappa 04.

## Riepilogo (a parità di tool e prompt)

| Motore | task | cita atteso | tool giusto | passi medi | tool medi |
|---|---|---|---|---|---|
| `autogen` | 9 | 8/9 | 8/9 | 1.4 | 1.4 |
| `vanilla` | 9 | 9/9 | 9/9 | 2.2 | 1.3 |

- **cita atteso**: la risposta finale nomina il file giusto (successo end-to-end).
- **tool giusto**: l'agente ha usato almeno uno strumento ideale per quel tipo di task.
- I motori condividono `tools.py` e il system prompt: le differenze sono di **orchestrazione**.
- ⚠️ I modelli locali non sono perfettamente deterministici: i numeri variano tra run; conta la *tendenza* (es. quale motore sceglie i tool giusti per i task doc vs codice).

---

## «In quale file è definita la classe APIRouter di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/routing.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `APIRouter` di FastAPI è definita nel file `fastapi/routing.py` alla riga 1005.  
> Riferimento: `fastapi/routing.py:1005`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `APIRouter` di FastAPI è definita nel file **fastapi/routing.py** alla riga **1005**.  
> File: `fastapi/routing.py#1005`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 1 passo · 1 strumento

---

## «Cos'è OAuth2PasswordBearer in FastAPI e in quale file è definito?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/security/oauth2.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> <answer>
> OAuth2PasswordBearer è una classe di sicurezza in FastAPI utilizzata per implementare il flusso OAuth2 "password" (o "resource owner password credentials"), che permette ai client di ottenere un token di accesso inviando credenziali direttamente (username e password). È comunemente usato per autenticare utenti tramite un endpoint di login.
> 
> È definita nel file **fastapi/security/oauth2.py#433** (linea 433).
> 
> Per ulteriori dettagli, la documentazione ufficiale spiega che questa classe si occupa di gestire il flusso OAuth2 password e di validare i token ricevuti nei header HTTP (es. `Authorization: Bearer <token>`).
> </answer>

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> OAuth2PasswordBearer è una classe utilizzata in FastAPI per gestire l'autenticazione tramite il flusso OAuth2 "password" (in cui il client invia credenziali direttamente). È definita nella classe `OAuth2PasswordBearer` all'interno del file `fastapi/security/oauth2.py` alla riga 433.
> 
> File: fastapi/security/oauth2.py#433

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 1 passo · 1 strumento

---

## «Dove è implementato Depends in FastAPI? Indica il file.»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/param_functions.py` o `fastapi/params.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> Il simbolo `Depends` è implementato come classe nel file `fastapi/params.py` alla riga 746.  
> Riferimento: `fastapi/params.py#746`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `search_code` → `find_symbol`

**Ha risposto:**

> La classe `Depends` è implementata in `fastapi/params.py#746`.
> 
> File sorgente: `fastapi/params.py` (linea 746)

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

---

## «In quale file è definita la classe BackgroundTasks di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/background.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `BackgroundTasks` è definita nel file `fastapi/background.py` alla riga 11.
> 
> **Risposta:**  
> `fastapi/background.py#11`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `BackgroundTasks` è definita nel file `fastapi/background.py:#11`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 1 passo · 1 strumento

---

## «In quale file del codice sorgente è definita la classe HTTPException?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/exceptions.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita nel file `fastapi/exceptions.py` alla riga 17.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita nel file `fastapi/exceptions.py` alla linea 17.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 1 passo · 1 strumento

---

## «In quale file è definita HTTPException e mostra qualche esempio del codice che la usa.»

> **Tipo:** multi-hop · **Atteso:** la risposta cita `fastapi/exceptions.py` · **strumenti ideali:** `find_symbol`, `who_calls`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `search_code`

**Ha risposto:**

> HTTPException è definita nel file `fastapi/exceptions.py#17` (classe `HTTPException`).
> 
> Esempi di utilizzo nel codice:
> 
> 1. **Esempio di uso in un endpoint** (da `docs_src/handling_errors/tutorial004_py310.py#0`):
> ```python
> from fastapi import FastAPI, HTTPException
> 
> app = FastAPI()
> 
> @app.get("/items/{item_id}")
> async def read_item(item_id: str):
>     if item_id not in items:
>         raise HTTPException(
>             status_code=404,
>             detail="Item not found",
>             headers={"X-Error": "There was an error"},
>         )
>     return items[item_id]
> ```
> 
> 2. **Esempio di gestione di errori** (da `docs_src/handling_errors/tutorial004_py310.py#0`):
> ```python
> from fastapi import HTTPException
> 
> def get_user(user_id: int):
>     if user_id not in users:
>         raise HTTPException(
>             status_code=404,
>             detail="User not found",
>         )
>     return users[user_id]
> ```
> 
> Questi esempi mostrano come `HTTPException` venga utilizzato per generare risposte HTTP con codici di stato specifici e dettagli personalizzati.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 2 strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `who_calls`

**Ha risposto:**

> HTTPException è definita nel file `fastapi/exceptions.py#17` come classe:
> 
> ```python
> class HTTPException(Exception):
> ```
> 
> Esempi di utilizzo in altri file (con riferimento alle linee di codice specifiche):
> 
> - Gestione di errori nell'endpoint `/items/{item_id}` (error handling tutorial):  
>   `docs_src/handling_errors/tutorial001_py310.py:9`
>   
> - Implementazione di dipendenze con errori personalizzati:  
>   `docs_src/dependencies/tutorial006_py310.py:6` e `docs_src/dependencies/tutorial006_py310.py:11`
>   
> - Richiesta non autenticata nel sistema di sicurezza OAuth2:  
>   `fastapi/security/oauth2.py:401` (dove `OAuth2.make_not_authenticated_error` utilizza HTTPException)
> 
> Tutti gli esempi citati sono presenti nella documentazione ufficiale di FastAPI come casi d'uso realistici dell'eccezione.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

---

## «Qual è la differenza tra una funzione di endpoint definita con def e una con async def in FastAPI?»

> **Tipo:** doc-concept · **Atteso:** la risposta cita `async.md` · **strumenti ideali:** `search_docs`, `search_combined`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `search_docs`

**Ha risposto:**

> La differenza principale tra una funzione di endpoint definita con `def` e una con `async def` in FastAPI riguarda il modello di esecuzione e la gestione delle operazioni I/O (Input/Output):
> 
> 1. **`async def`**:  
>    - Permette l'uso di `await` per operazioni asincrone (es. chiamate a database, API esterne).  
>    - Non blocca il thread principale durante le operazioni I/O, migliorando le prestazioni in scenari ad alto carico.  
>    - Richiede che le dipendenze e le operazioni interne siano compatibili con il modello asincrono.  
>    - *Esempio*:  
>      ```python
>      @app.get("/data")
>      async def get_data():
>          result = await database.query()  # Operazione asincrona
>          return result
>      ```
> 
> 2. **`def`**:  
>    - Funzione sincrona: blocca l'esecuzione fino al completamento di ogni operazione (es. chiamate a database sincrone).  
>    - Non può usare `await`, quindi è adatta solo per operazioni non I/O-bound (es. calcoli CPU-bound).  
>    - FastAPI eseguirà automaticamente la funzione in un pool di thread per evitare blocchi, ma ciò è meno efficiente rispetto all'asincrono.  
>    - *Esempio*:  
>      ```python
>      @app.get("/data")
>      def get_data():
>          result = database.query_sync()  # Operazione sincrona
>          return result
>      ```
> 
> **Documentazione rilevante**:  
> - `async def` è necessario per usare `await` (vedi [docs/en/docs/async.md#22](docs/en/docs/async.md#22)).  
> - FastAPI richiede che le dipendenze siano compatibili con il modello asincrono se l'endpoint è definito con `async def` (vedi [docs/en/docs/tutorial/dependencies/index.md#10](docs/en/docs/tutorial/dependencies/index.md#10)).  
> - Anche se non si usa `await`, è possibile definire funzioni con `async def` (vedi [docs/en/docs/async.md#2](docs/en/docs/async.md#2)), ma il vantaggio principale è la gestione asincrona delle operazioni I/O.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `search_docs`

**Ha risposto:**

> La differenza tra una funzione di endpoint definita con `def` (sincrona) e `async def` (asincrona) in FastAPI riguarda la gestione del flusso di esecuzione e l'efficienza nell'elaborazione delle richieste:
> 
> 1. **Endpoint sincrono (`def`)**:
>    - Blocca il thread durante operazioni di I/O (es. chiamate a database, API esterne).
>    - Gestisce una richiesta alla volta, non è adatta per scenari ad alto carico con operazioni lente.
>    - Utilizza il pattern standard di Python (senza `async`/`await`).
> 
> 2. **Endpoint asincrono (`async def`)**:
>    - Utilizza **coroutine** e l'evento loop per evitare blocchi durante le operazioni I/O (es. `await` su chiamate asincrone).
>    - Permette di gestire **diverse richieste contemporaneamente** (concorrenza), migliorando l'efficienza per operazioni lente di I/O.
>    - Richiede l'utilizzo di `async`/`await` e restituisce un oggetto *awaitable*.
> 
> **Riferimento alla documentazione**:
> - La spiegazione tecnica è fornita in [docs/en/docs/async.md#3](docs/en/docs/async.md#3), che descrive i dettagli sull'uso delle coroutine e il supporto per codice asincrono in Python moderno.
> - La sezione "Other forms of asynchronous code" ([docs/en/docs/async.md#24](docs/en/docs/async.md#24)) illustra come l'implementazione asincrona ottimizza il parallelismo in FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 1 passo · 1 strumento

---

## «Come si dichiara un parametro di query in FastAPI? Mostra sia dove è implementato Query sia la documentazione che lo spiega.»

> **Tipo:** code+doc · **Atteso:** la risposta cita `fastapi/params.py` o `fastapi/param_functions.py` o `query-param` · **strumenti ideali:** `find_symbol`, `search_docs`, `search_combined`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `search_docs`

**Ha risposto:**

> Il parametro di query in FastAPI si dichiara utilizzando la classe `Query` dal modulo `fastapi`. 
> 
> **Implementazione nel codice:**  
> La classe `Query` è definita in `fastapi/params.py#221`:
> ```python
> class Query:
>     # Implementazione per gestire parametri di query con validazioni e default
> ```
> 
> **Documentazione esplicativa:**  
> La documentazione spiega l'uso di `Query` per dichiarare parametri di query con validazioni e valori predefiniti. Esempio pratico:
> ```python
> from fastapi import Query
> 
> @app.get("/items/")
> async def read_items(q: str = Query(..., min_length=3)):
>     return {"q": q}
> ```
> Questa sintassi è descritta in:
> - `docs/en/docs/tutorial/query-params-str-validations.md#4` (spiegazione dell'uso di `Query` come valore predefinito)
> - `docs/en/docs/tutorial/query-params-str-validations.md#5` (esempio con validazione `min_length`)
> 
> La documentazione conferma che `Query` permette di definire parametri opzionali, impostare vincoli (es. `min_length`), e gestire valori predefiniti, come mostrato negli esempi.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 2 strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `related_docs`

**Ha risposto:**

> Per dichiarare un parametro di query in FastAPI utilizzando `Query`, ecco gli elementi richiesti:
> 
> 1. **Implementazione di `Query` nel codice**:
>    - La classe `Query` è definita qui: `fastapi/params.py:221`
>    - La funzione `Query` è implementata qui: `fastapi/param_functions.py:357`
> 
> 2. **Documentazione che spiega l'uso**:
>    - Spiegazione dettagliata nell'[Riferimento Parametri](docs/en/docs/reference/parameters.md)
>    - Esempi pratici nella [Guida Query Parameters](docs/en/docs/tutorial/query-params.md)
> 
> Esempio di utilizzo nella route:
> ```python
> from fastapi import Query
> 
> @app.get("/items/")
> async def read_items(q: str = Query(..., min_length=3, max_length=50)):
>     return {"q": q}
> ```
> (Questa sintassi è illustrata nel file `docs/en/docs/tutorial/query-params.md`.)

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

---

## «A cosa servono le BackgroundTasks e dove sono documentate?»

> **Tipo:** code+doc · **Atteso:** la risposta cita `background-tasks.md` o `reference/background` o `background.md` · **strumenti ideali:** `search_docs`, `related_docs`, `search_combined`

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `search_code` → `search_docs`

**Ha risposto:**

> Le `BackgroundTasks` in FastAPI servono per eseguire operazioni in background (ad esempio, invio email, elaborazione dati) dopo aver inviato la risposta HTTP al client, evitando di ritardare la risposta principale. Questo è utile per operazioni non critiche che non richiedono una risposta immediata.
> 
> Sono documentate nel file **docs/en/docs/reference/background.md#0** (sezione "Background Tasks"), che spiega come dichiarare un parametro di tipo `BackgroundTasks` in una funzione di path operation o in una dipendenza, e come aggiungere compiti da eseguire in background tramite il metodo `.add_task()`.
> 
> Esempio di utilizzo dal codice:
> ```python
> from fastapi import BackgroundTasks, FastAPI
> 
> app = FastAPI()
> 
> def send_email(email: str):
>     # Logica per inviare email
>     pass
> 
> @app.post("/send-email/")
> def send_email_endpoint(background_tasks: BackgroundTasks, email: str):
>     background_tasks.add_task(send_email, email)
>     return {"message": "Email sent in background"}
> ```

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `search_code`

**Ha risposto:**

> BackgroundTasks sono utilizzati per gestire operazioni in background (ad esempio, invio email o elaborazione dati) dopo che la risposta HTTP è stata inviata al client. Questo evita di bloccare la risposta principale con operazioni lente.
> 
> Sono documentati nel tutorial di esempio:  
> `docs_src/background_tasks/tutorial001_py310.py`#0
> 
> Questo file mostra l'uso tipico:
> ```python
> from fastapi import BackgroundTasks, FastAPI
> app = FastAPI()
> 
> def send_email(email: str):
>     # Invio email in background
>     pass
> 
> @app.post("/send-email/")
> def send_email_background(email: str, background_tasks: BackgroundTasks):
>     background_tasks.add_task(send_email, email)
>     return {"message": "Email scheduled"}
> ```
> 
> La definizione implementativa è nel file:  
> `fastapi/background.py`#11

**Esito:** ❌ non ha citato il file atteso · strumento giusto ❌ · 2 passi · 2 strumenti

---
