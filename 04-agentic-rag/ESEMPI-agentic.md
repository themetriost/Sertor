# ESEMPI — Agentic RAG (documentazione parlante, auto-generata)

> **File generato** da `04-agentic-rag/evaluate.py` (non modificare a mano). Mostra, per ogni
> domanda e per ogni motore, *cosa ho chiesto → cosa ha fatto l'agente → cosa mi ha risposto*.
> È la controparte divulgativa di [`ESEMPI.md`](../ESEMPI.md) per la Tappa 04.

## Riepilogo (a parità di tool e prompt)

| Motore | task | cita atteso | tool giusto | passi medi | tool medi |
|---|---|---|---|---|---|
| `vanilla` | 9 | 9/9 | 9/9 | 2.7 | 3.2 |
| `autogen` | 9 | 9/9 | 7/9 | 2.7 | 3.4 |

- **cita atteso**: la risposta finale nomina il file giusto (successo end-to-end).
- **tool giusto**: l'agente ha usato almeno uno strumento ideale per quel tipo di task.
- I motori condividono `tools.py` e il system prompt: le differenze sono di **orchestrazione**.
- ⚠️ I modelli locali non sono perfettamente deterministici: i numeri variano tra run; conta la *tendenza* (es. quale motore sceglie i tool giusti per i task doc vs codice).

---

## «In quale file è definita la classe APIRouter di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/routing.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `APIRouter` è definita in `fastapi/routing.py` alla riga 1005 (`fastapi/routing.py:1005`).

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `APIRouter` di FastAPI è definita in:
> 
> - `fastapi/routing.py#49`

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

---

## «Cos'è OAuth2PasswordBearer in FastAPI e in quale file è definito?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/security/oauth2.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `find_symbol`

**Ha risposto:**

> `OAuth2PasswordBearer` è una classe di FastAPI usata per definire uno **schema di sicurezza OAuth2 con flow “password”**: in pratica dice a FastAPI che l’endpoint si aspetta un token Bearer nell’header `Authorization`, e contribuisce anche alla documentazione OpenAPI. La documentazione lo descrive come uno dei tool di FastAPI per implementare la security e come schema che viene aggiunto a OpenAPI. [docs/en/docs/tutorial/security/first-steps.md#5](docs/en/docs/tutorial/security/first-steps.md#5) [docs/en/docs/tutorial/security/simple-oauth2.md#3](docs/en/docs/tutorial/security/simple-oauth2.md#3)
> 
> Nel codice della codebase è definito in:
> 
> - `fastapi/security/oauth2.py:433` — `class OAuth2PasswordBearer`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code` → `find_symbol`

**Ha risposto:**

> `OAuth2PasswordBearer` è una dipendenza di FastAPI per gestire l’autenticazione **OAuth2 con bearer token** ottenuto tramite **password flow**. In pratica, legge l’header `Authorization: Bearer <token>` dalla richiesta e fornisce il token alla tua dependency. È anche usato da FastAPI per dichiarare lo schema di sicurezza nell’OpenAPI.  
> Fonti: `docs/en/docs/tutorial/security/first-steps.md#5`, `docs/en/docs/tutorial/security/simple-oauth2.md#3`.
> 
> È definito nel file:
> 
> - `fastapi/security/oauth2.py#16-19`  
>   e il simbolo risulta anche a `fastapi/security/oauth2.py:433` per la definizione della classe.
> 
> Se vuoi, posso anche mostrarti un esempio minimo d’uso in una route FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

---

## «Dove è implementato Depends in FastAPI? Indica il file.»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/param_functions.py` o `fastapi/params.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> `Depends` è implementato in FastAPI qui:
> 
> - `fastapi/param_functions.py:2283` — funzione `Depends`
> - `fastapi/params.py:746` — classe `Depends`
> 
> Se vuoi, posso anche dirti **qual è il ruolo della funzione rispetto alla classe** e come viene usata nel dependency injection system di FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code` → `find_symbol`

**Ha risposto:**

> `Depends` è implementato in `fastapi/param_functions.py` alla linea 2283, come funzione `Depends`.  
> Esiste anche la classe correlata `Depends` in `fastapi/params.py` alla linea 746.  
> 
> Riferimenti:
> - `fastapi/param_functions.py:2283`
> - `fastapi/params.py:746`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

---

## «In quale file è definita la classe BackgroundTasks di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/background.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `find_symbol`

**Ha risposto:**

> La classe `BackgroundTasks` di FastAPI è definita in:
> 
> - `fastapi/background.py:11` — `class BackgroundTasks`
> 
> Se vuoi, posso anche mostrarti da dove viene importata/esposta nel package FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `BackgroundTasks` è definita in:
> 
> - `fastapi/background.py#1`
> 
> Se vuoi, posso anche indicarti dove viene esportata/importata nel package `fastapi` o mostrarti la gerarchia con `StarletteBackgroundTasks`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

---

## «In quale file del codice sorgente è definita la classe HTTPException?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/exceptions.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita in:
> 
> - `fastapi/exceptions.py:17`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita in:
> 
> - `fastapi/exceptions.py:17`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

---

## «In quale file è definita HTTPException e mostra qualche esempio del codice che la usa.»

> **Tipo:** multi-hop · **Atteso:** la risposta cita `fastapi/exceptions.py` · **strumenti ideali:** `find_symbol`, `who_calls`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `search_code` → `search_docs`

**Ha risposto:**

> `HTTPException` è definita in `fastapi/exceptions.py` alla riga 17.  
> Fonte: `fastapi/exceptions.py:17` (`class HTTPException`) e `fastapi/exceptions.py#2` (`class HTTPException(StarletteHTTPException)`)  
> 
> Ecco alcuni esempi di codice che la usa:
> 
> - `docs_src/app_testing/app_b_py310/main.py:3`  
>   ```python
>   if x_token != fake_secret_token:
>       raise HTTPException(status_code=400, ...)
>   ```
> 
> - `docs_src/app_testing/app_b_an_py310/main.py:3`  
>   ```python
>   if x_token != fake_secret_token:
>       raise HTTPException(status_code=400, ...)
>   ```
> 
> - `fastapi/security/http.py:6`  
>   ```python
>   def make_not_authenticated_error(self) -> HTTPException:
>       return HTTPException(status_code=HTTP_401_UNAUTHORIZED, ...)
>   ```
> 
> Se vuoi, posso anche mostrarti **tutti i punti del codice dove viene sollevata (`raise`)** oppure spiegarti la differenza tra **FastAPI `HTTPException`** e **Starlette `HTTPException`**.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `search_code` → `related_docs` → `search_code` → `search_docs`

**Ha risposto:**

> `HTTPException` è definita in:
> 
> - `fastapi/exceptions.py:17` — classe `HTTPException` (eredita da `StarletteHTTPException`)  
>   Citazione: `fastapi/exceptions.py#2: class HTTPException(StarletteHTTPException): ...`
> 
> Ecco alcuni esempi di codice che la usa:
> 
> 1. **Gestione errori in una dependency**
>    - `docs_src/dependencies/tutorial006_py310.py#1`
>    - Esempio:
>      ```py
>      async def verify_token(x_token: str = Header()):
>          if x_token != "fake-super-secret-token":
>              raise HTTPException(status_code=400, detail="X-Token header invalid")
>      ```
> 
> 2. **Esempio simile con Annotated**
>    - `docs_src/dependencies/tutorial006_an_py310.py#1`
>    - Esempio:
>      ```py
>      async def verify_token(x_token: Annotated[str, Header()]):
>          if x_token != "fake-super-secret-token":
>              raise HTTPException(status_code=400, detail="X-Token header invalid")
>      ```
> 
> 3. **Nel modulo di gestione degli errori**
>    - `fastapi/exception_handlers.py#1`
>    - Qui viene usata nella funzione handler:
>      ```py
>      async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
>      ```
> 
> La documentazione che la spiega è in:
> - `docs/en/docs/tutorial/handling-errors.md#0`
> - `docs/en/docs/tutorial/handling-errors.md#1`
> 
> Se vuoi, posso anche mostrarti **il contenuto completo** della classe `HTTPException` o altri esempi d’uso più vicini al codice applicativo.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 5 strumenti

---

## «Qual è la differenza tra una funzione di endpoint definita con def e una con async def in FastAPI?»

> **Tipo:** doc-concept · **Atteso:** la risposta cita `async.md` · **strumenti ideali:** `search_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code` → `find_symbol` → `find_symbol` → `search_code` → `search_docs`

**Ha risposto:**

> In FastAPI, la differenza principale è questa:
> 
> - **`async def`**: la funzione è una coroutine e viene eseguita nel **event loop**; puoi usare `await` dentro la funzione per chiamare operazioni asincrone. È la scelta giusta quando usi librerie/operazioni che supportano l’I/O asincrono.  
>   Fonte: `docs/en/docs/async.md#22` e `docs/en/docs/async.md#2`
> 
> - **`def`**: la funzione è sincrona; FastAPI la esegue **in un threadpool**, così non blocca il server mentre fa operazioni bloccanti.  
>   Fonte: `docs/en/docs/async.md#27`
> 
> Dal codice si vede anche che FastAPI distingue i due casi e, se l’endpoint non è coroutine, lo esegue tramite `run_in_threadpool`; se invece è coroutine, lo `await` direttamente.  
> Fonte: `fastapi/routing.py#22`
> 
> ### In pratica
> - Usa **`async def`** se fai I/O asincrono (es. client HTTP async, driver DB async).
> - Usa **`def`** se usi codice/librerie sincrone o bloccanti.
> 
> ### Nota importante
> Se dentro una funzione `async def` chiami codice bloccante senza `await`, puoi bloccare l’event loop e peggiorare le prestazioni.  
> Fonte: `docs/en/docs/async.md#1`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 5 passi · 6 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_docs` → `search_docs`

**Ha risposto:**

> In FastAPI, la differenza principale è questa:
> 
> - **`async def`**: l’endpoint è una coroutine asincrona. È adatto quando il codice fa I/O non bloccante, per esempio chiamate a database/HTTP supportate in async.
> - **`def`**: l’endpoint è sincrono. FastAPI lo esegue in un **threadpool**, così non blocca il event loop principale.
> 
> La documentazione FastAPI dice che una path operation function definita con `def` invece di `async def` viene eseguita in un threadpool; quindi va bene per codice sincrono o librerie non async. Viene anche suggerito di usare `async def` quando l’app “deve aspettare” altre risorse/servizi.  
> Fonti: `docs/en/docs/async.md#27`, `docs/en/docs/async.md#2`, `docs/en/docs/async.md#29`.
> 
> In pratica:
> 
> - usa **`async def`** se chiami funzioni async e fai molte operazioni di I/O non bloccanti;
> - usa **`def`** se hai codice sincrono/bloccante o librerie che non supportano async.
> 
> Nota importante: **non rende automaticamente il codice più veloce**. Se dentro un endpoint `async def` chiami operazioni bloccanti, blocchi comunque l’event loop; in quel caso meglio `def` o librerie realmente async.  
> Fonte: `docs/en/docs/async.md#27`, `docs/en/docs/advanced/stream-data.md#4`.
> 
> Se vuoi, posso anche farti un esempio concreto di due endpoint equivalenti, uno `def` e uno `async def`, con quando conviene usare ciascuno.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 3 strumenti

---

## «Come si dichiara un parametro di query in FastAPI? Mostra sia dove è implementato Query sia la documentazione che lo spiega.»

> **Tipo:** code+doc · **Atteso:** la risposta cita `fastapi/params.py` o `fastapi/param_functions.py` o `query-param` · **strumenti ideali:** `find_symbol`, `search_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_docs` → `find_symbol` → `find_symbol` → `related_docs` → `search_docs` → `search_code` → `search_code` → `search_docs`

**Ha risposto:**

> In FastAPI un parametro di query si dichiara usando `Query`, tipicamente con `Annotated`:
> 
> ```python
> from typing import Annotated
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> async def read_items(q: Annotated[str | None, Query(max_length=50)] = None):
>     return {"q": q}
> ```
> 
> Oppure, nello stile “vecchio”, come valore di default:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> async def read_items(q: str | None = Query(default=None, max_length=50)):
>     return {"q": q}
> ```
> 
> Dove è implementato:
> - La funzione helper `Query` è in `fastapi/param_functions.py:8` e serve a costruire il parametro con metadati/validazioni.
> - La classe `Query` vera e propria è in `fastapi/params.py:10-11`, dove viene impostato `in_ = ParamTypes.query`.
> 
> Documentazione che lo spiega:
> - Tutorial sui query params e validazioni: `docs/en/docs/tutorial/query-params-str-validations.md#0`
> - Sezione “Add `Query` to `Annotated` in the `q` parameter”: `docs/en/docs/tutorial/query-params-str-validations.md#3`
> - Sezione alternativa “`Query` as the default value”: `docs/en/docs/tutorial/query-params-str-validations.md#4`
> 
> Se vuoi, posso anche mostrarti un esempio completo con validazioni (`min_length`, `max_length`, `pattern`, ecc.) preso dalla documentazione.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 9 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_docs` → `search_code` → `search_docs` → `search_docs` → `search_code` → `find_symbol` → `related_docs` → `search_code` → `search_docs` → `search_docs`

**Ha risposto:**

> In FastAPI, un parametro di query si dichiara tipicamente con `Query()` come valore di default oppure con `Annotated`.
> 
> Esempio moderno:
> 
> ```python
> from typing import Annotated
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> async def read_items(q: Annotated[str | None, Query()] = None):
>     return {"q": q}
> ```
> 
> Esempio “vecchio stile” ancora valido:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> async def read_items(q: str | None = Query(default=None)):
>     return {"q": q}
> ```
> 
> Dove è implementato `Query`:
> - `fastapi/params.py#10` — `class Query(Param): ... in_ = ParamTypes.query`
> - `fastapi/param_functions.py:357` — funzione `Query`
> 
> Documentazione che lo spiega:
> - `docs/en/docs/tutorial/query-params.md#0` — spiega che i parametri non di path sono interpretati come query parameters
> - `docs/en/docs/tutorial/query-params-str-validations.md#1` — mostra l’import di `Query` e `Annotated`
> - `docs/en/docs/reference/parameters.md#0` — riferimento per i request parameters
> - `docs/en/docs/tutorial/query-param-models.md#0` — per casi con più query parameters correlati
> 
> Se vuoi, posso anche mostrarti un esempio con validazioni (`min_length`, `max_length`, `regex`, ecc.).

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 5 passi · 11 strumenti

---

## «A cosa servono le BackgroundTasks e dove sono documentate?»

> **Tipo:** code+doc · **Atteso:** la risposta cita `background-tasks.md` o `reference/background` o `background.md` · **strumenti ideali:** `search_docs`, `related_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_combined` → `find_symbol` → `search_docs` → `related_docs`

**Ha risposto:**

> Le `BackgroundTasks` servono per eseguire operazioni **dopo** che la risposta è già stata inviata al client, quindi sono utili per lavori non bloccanti come invio email, scrittura di log, notifiche, ecc. Lo dice sia il codice sia la documentazione: la classe è definita in `fastapi/background.py:11` con docstring “called after a response has been sent to the client”, e la guida spiega che puoi definire task da eseguire “after returning a response” in `docs/en/docs/tutorial/background-tasks.md#0` e nella reference `docs/en/docs/reference/background.md#0`.
> 
> In breve:
> - **Scopo**: posticipare attività leggere/non critiche alla risposta.
> - **Quando usarle**: quando non serve che il client aspetti il completamento dell’operazione.
> - **Dove sono documentate**:
>   - tutorial: `docs/en/docs/tutorial/background-tasks.md#0`
>   - reference: `docs/en/docs/reference/background.md#0`
>   - anche esempi: `docs_src/background_tasks/tutorial001_py310.py#0`, `docs_src/background_tasks/tutorial002_py310.py#0`
> 
> Nota: la documentazione avverte anche che per computazioni pesanti o distribuite potrebbe essere meglio usare un sistema di task queue esterno, non `BackgroundTasks` (`docs/en/docs/tutorial/background-tasks.md#4`).

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 4 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_combined` → `find_symbol` → `search_docs` → `related_docs`

**Ha risposto:**

> Le `BackgroundTasks` servono per eseguire operazioni **dopo** che la risposta è già stata inviata al client, quindi sono utili per lavori “leggeri” che non devono bloccare la request, ad esempio inviare email, scrivere log o fare piccole operazioni I/O. La classe è documentata come una collezione di task eseguiti dopo il response in `fastapi/background.py` e nei tutorial/reference FastAPI.  
> Cittazioni:
> - Implementazione: `fastapi/background.py#1` e simbolo `BackgroundTasks` in `fastapi/background.py:11`
> - Documentazione tutorial: `docs/en/docs/tutorial/background-tasks.md#0`
> - Dettagli tecnici: `docs/en/docs/tutorial/background-tasks.md#3`
> - Reference API: `docs/en/docs/reference/background.md#0`
> 
> Nota: la doc avverte che **non** è pensato per computazioni pesanti o lavoro distribuito; in quei casi è meglio usare un sistema di task queue esterno. Citazione: `docs/en/docs/tutorial/background-tasks.md#4`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 4 strumenti

---
