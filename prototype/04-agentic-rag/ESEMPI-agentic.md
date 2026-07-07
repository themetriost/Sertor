# ESEMPI — Agentic RAG (documentazione parlante, auto-generata)

> **File generato** da `04-agentic-rag/evaluate.py` (non modificare a mano). Mostra, per ogni
> domanda e per ogni motore, *cosa ho chiesto → cosa ha fatto l'agente → cosa mi ha risposto*.
> È la controparte divulgativa di [`ESEMPI.md`](../ESEMPI.md) per la Tappa 04.

## Riepilogo (a parità di tool e prompt)

| Motore | task | cita atteso | tool giusto | passi medi | tool medi |
|---|---|---|---|---|---|
| `autogen` | 9 | 9/9 | 8/9 | 2.8 | 3.7 |
| `langgraph` | 9 | 9/9 | 7/9 | 2.8 | 3.3 |
| `sk` | 9 | 9/9 | 8/9 | 5.0 | 4.0 |
| `vanilla` | 9 | 9/9 | 7/9 | 2.8 | 3.3 |

- **cita atteso**: la risposta finale nomina il file giusto (successo end-to-end).
- **tool giusto**: l'agente ha usato almeno uno strumento ideale per quel tipo di task.
- I motori condividono `tools.py` e il system prompt: le differenze sono di **orchestrazione**.
- ⚠️ **`passi`**: per `vanilla`/`autogen` sono turni LLM reali; per `sk` è *approssimato* (SK non espone i confini dei turni: vale ≈ n° tool + 1). Per il **costo** confronta `tool medi`.
- ⚠️ I modelli non sono perfettamente deterministici: i numeri variano tra run; conta la *tendenza* (es. quale motore sceglie i tool giusti, e quanto è verboso).

---

## «In quale file è definita la classe APIRouter di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/routing.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `APIRouter` è definita in:
> 
> - `fastapi/routing.py#49`
> 
> Se vuoi, posso anche indicarti dove viene esportata/importata pubblicamente da `fastapi`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `APIRouter` è definita nel file:
> 
> - `fastapi/routing.py#49`
> 
> Se vuoi, posso anche mostrarti la firma della classe o i simboli correlati.

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `search_code` → `search_docs`

**Ha risposto:**

> La classe `APIRouter` è definita in `fastapi/routing.py` alla riga 1005.  
> Fonte: `fastapi/routing.py:1005`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 3 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `APIRouter` è definita in:
> 
> - `fastapi/routing.py#49`
> 
> Se vuoi, posso anche indicarti dove viene esportata/importata da `fastapi` (`from fastapi import APIRouter`).

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

---

## «Cos'è OAuth2PasswordBearer in FastAPI e in quale file è definito?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/security/oauth2.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `find_symbol`

**Ha risposto:**

> `OAuth2PasswordBearer` è una classe di FastAPI usata per definire uno **schema di sicurezza OAuth2 con flusso password bearer**: in pratica dice a FastAPI che l’endpoint si aspetta un token Bearer nell’header `Authorization`, e contribuisce anche alla documentazione OpenAPI. La documentazione lo descrive come uno dei tool di FastAPI per implementare la sicurezza OAuth2 e mostra che viene usato come dipendenza con `Depends` (`docs/en/docs/tutorial/security/first-steps.md#5`, `docs/en/docs/tutorial/security/simple-oauth2.md#3`).
> 
> Nel codice, è definito in:
> 
> - `fastapi/security/oauth2.py:433`
> 
> Se vuoi, posso anche mostrarti un esempio minimo di utilizzo in un endpoint FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_docs` → `find_symbol` → `search_code` → `search_docs`

**Ha risposto:**

> `OAuth2PasswordBearer` è una classe di FastAPI per il flusso OAuth2 con **password grant** che recupera un **bearer token** dall’header `Authorization` e la usa come dipendenza (`Depends`) per proteggere gli endpoint. Inoltre fa sì che FastAPI la riconosca come **security scheme** e la includa in OpenAPI.  
> Fonti: `fastapi/security/oauth2.py:16` e `docs/en/docs/tutorial/security/simple-oauth2.md#3`.
> 
> È definito in `fastapi/security/oauth2.py` alla classe `OAuth2PasswordBearer` (con riferimento trovato a `fastapi/security/oauth2.py:433` e definizione iniziale in `fastapi/security/oauth2.py:16`).  
> Fonti: `fastapi/security/oauth2.py:16`, `fastapi/security/oauth2.py:433`.
> 
> Se vuoi, posso anche mostrarti un esempio minimo di utilizzo.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 4 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `find_symbol`

**Ha risposto:**

> `OAuth2PasswordBearer` è una classe di FastAPI usata per definire uno **schema di sicurezza OAuth2 con flow “password”**. In pratica, serve a dire a FastAPI che l’app usa un bearer token OAuth2: FastAPI lo integra anche nella documentazione OpenAPI e lo usa tipicamente come dipendenza con `Depends` per leggere il token dall’header `Authorization` (`Bearer ...`).  
> Fonte: `docs/en/docs/tutorial/security/first-steps.md#5`, `docs/en/docs/tutorial/security/simple-oauth2.md#3`
> 
> Nel codice, è definito in:
> 
> - `fastapi/security/oauth2.py:433` — `class OAuth2PasswordBearer`
> 
> Se vuoi, posso anche spiegarti **come si usa in un endpoint FastAPI** con un esempio minimo.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 2 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `find_symbol`

**Ha risposto:**

> `OAuth2PasswordBearer` è una classe di FastAPI usata per definire uno schema di sicurezza OAuth2 basato su password flow. In pratica, FastAPI la usa per leggere il token Bearer dall’header `Authorization`, integrarlo con OpenAPI e usarlo come dipendenza (`Depends`) nei path operation o nelle dependency di sicurezza. Vedi la spiegazione nei tutorial di FastAPI su `OAuth2PasswordBearer` e `OAuth2PasswordRequestForm` (`docs/en/docs/tutorial/security/first-steps.md#5`, `docs/en/docs/tutorial/security/simple-oauth2.md#3`).
> 
> È definito nel file:
> - `fastapi/security/oauth2.py:433`
> 
> Se vuoi, posso anche mostrarti un esempio minimo di utilizzo in FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

---

## «Dove è implementato Depends in FastAPI? Indica il file.»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/param_functions.py` o `fastapi/params.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> `Depends` è implementato in:
> 
> - `fastapi/param_functions.py:2283` — funzione `Depends`
> - `fastapi/params.py:746` — classe `Depends`
> 
> Se vuoi, posso anche dirti quale dei due è il punto d’ingresso pubblico e come si collega alla dependency injection di FastAPI.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code` → `find_symbol` → `search_docs`

**Ha risposto:**

> `Depends` è implementato in:
> 
> - `fastapi/param_functions.py:2283` — funzione `Depends`
> - `fastapi/params.py:746` — classe `Depends`
> 
> Quindi, se cerchi l’implementazione pubblica usata dagli utenti, il punto principale è `fastapi/param_functions.py:2283`; la classe di supporto è definita in `fastapi/params.py:746`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_code` → `find_symbol` → `search_code` → `search_code` → `related_docs`

**Ha risposto:**

> `Depends` è implementato principalmente qui:
> 
> - `fastapi/params.py:30` — definizione della dataclass `Depends`
> - `fastapi/param_functions.py:2283` — helper/factory `Depends(...)` esportato da FastAPI
> 
> Se intendi la classe vera e propria, il file giusto è **`fastapi/params.py`**.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 7 passi · 6 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_code` → `find_symbol`

**Ha risposto:**

> `Depends` è implementato in `fastapi/params.py` come classe dataclass:
> 
> - `fastapi/params.py:746` — `class Depends`
> 
> C’è anche una funzione helper/esportata con lo stesso nome in:
> 
> - `fastapi/param_functions.py:2283` — `function Depends`
> 
> Se vuoi, posso anche dirti quale dei due viene usato pubblicamente da `from fastapi import Depends` e come si collega al sistema di dependency injection.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 3 strumenti

---

## «In quale file è definita la classe BackgroundTasks di FastAPI?»

> **Tipo:** localizzazione · **Atteso:** la risposta cita `fastapi/background.py` · **strumenti ideali:** `find_symbol`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `BackgroundTasks` di FastAPI è definita in:
> 
> - `fastapi/background.py#1`
> 
> Se ti serve, posso anche mostrarti dove viene esportata/importata nel package `fastapi`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 2 passi · 1 strumento

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code` → `find_symbol`

**Ha risposto:**

> La classe `BackgroundTasks` di FastAPI è definita in:
> 
> - `fastapi/background.py:11` — `class BackgroundTasks(StarletteBackgroundTasks)`
> 
> Riferimento trovato anche nel file sorgente `fastapi/background.py#1-2`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 2 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_combined`

**Ha risposto:**

> La classe `BackgroundTasks` è definita in **`fastapi/background.py`** (`fastapi/background.py#1`).  
> 
> Nota: nella documentazione è indicato che `BackgroundTasks` proviene direttamente da **Starlette** (`docs/en/docs/tutorial/background-tasks.md#3`).

**Esito:** ✅ ha citato il file atteso · strumento giusto ❌ · 3 passi · 2 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code`

**Ha risposto:**

> La classe `BackgroundTasks` di FastAPI è definita nel file:
> 
> - `fastapi/background.py#1`
> 
> Se vuoi, posso anche indicarti dove viene esportata/importata nel package `fastapi`.

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

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita in:
> 
> - `fastapi/exceptions.py:17` — `class HTTPException`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 1 strumento

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

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

**Ha fatto:** `find_symbol` → `search_code` → `search_docs` → `search_code` → `search_code` → `search_docs`

**Ha risposto:**

> `HTTPException` è definita in:
> 
> - `fastapi/exceptions.py:17` — classe `HTTPException`
> - anche il simbolo appare come estensione di `StarletteHTTPException` in `fastapi/exceptions.py#2`
> 
> Esempi di codice che la usa:
> 
> - `docs_src/handling_errors/tutorial001_py310.py#0` — esempio base di `FastAPI` + `HTTPException`
> - `docs_src/dependencies/tutorial006_py310.py#0` — usa `raise HTTPException(status_code=400, detail="X-Token header invalid")`
> - `fastapi/security/http.py#6` — `make_not_authenticated_error()` ritorna una `HTTPException`
> - `fastapi/exception_handlers.py#1` — handler `http_exception_handler(request: Request, exc: HTTPException)`
> 
> Dal codice trovato, un esempio concreto è:
> 
> ```python
> raise HTTPException(status_code=400, detail="X-Token header invalid")
> ```
> 
> in `docs_src/dependencies/tutorial006_py310.py#1`.
> 
> Se vuoi, posso anche mostrarti **la definizione completa della classe** `HTTPException` oppure **tutti i punti del progetto in cui viene sollevata**.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 6 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `who_calls` → `search_code`

**Ha risposto:**

> `HTTPException` è definita in `fastapi/exceptions.py` come classe `HTTPException(StarletteHTTPException)`: `fastapi/exceptions.py:2` (e la definizione è indicata anche a `fastapi/exceptions.py:17` dal grafo simboli).
> 
> Esempi di uso nel codice:
> 
> - `docs_src/handling_errors/tutorial004_py310.py#0` usa `HTTPException` insieme a `FastAPI` e `RequestValidationError`.
> - `docs_src/handling_errors/tutorial006_py310.py#0` lo importa per gestire errori con handler personalizzati.
> - `docs_src/dependencies/tutorial008c_py310.py#0` lo usa in un’app con `Depends`.
> - `docs_src/dependencies/tutorial012_py310.py#0` lo importa con `Depends`, `FastAPI`, `Header`.
> 
> Se vuoi, posso anche mostrarti i frammenti esatti di uno o più di questi file.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `search_code` → `search_code` → `search_code` → `search_code` → `search_code` → `search_code` → `search_code`

**Ha risposto:**

> `HTTPException` è definita in `fastapi/exceptions.py` alla classe `HTTPException(StarletteHTTPException)` (`fastapi/exceptions.py:17` e anche `fastapi/exceptions.py#2` nei risultati di ricerca).
> 
> Ecco alcuni esempi di utilizzo nel codice:
> 
> - In un endpoint di esempio, viene sollevata per segnalare un token header non valido:
>   - `docs_src/dependencies/tutorial006_py310.py:1`
>   - `docs_src/dependencies/tutorial012_py310.py:1`
>   - esempio: `raise HTTPException(status_code=400, detail="X-Token header invalid")`
> 
> - In un dependency handler, viene usata per propagare un errore custom:
>   - `docs_src/dependencies/tutorial008b_py310.py#2`
>   - esempio: `raise HTTPException(status_code=400, detail=f"Owner error: {e}")`
> 
> - In un test/app di esempio:
>   - `docs_src/app_testing/app_b_py310/main.py:3`
>   - esempio: `raise HTTPException(status_code=400, detail=...)`
> 
> - Nella documentazione sugli errori:
>   - `docs_src/handling_errors/tutorial001_py310.py#0`
>   - `docs_src/handling_errors/tutorial004_py310.py#1`
> 
> Se vuoi, posso anche mostrarti il contenuto esatto della definizione di `HTTPException` in `fastapi/exceptions.py` oppure elencarti tutti i file che la importano.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 9 passi · 8 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `find_symbol` → `search_code` → `search_docs` → `search_code` → `search_code` → `search_code`

**Ha risposto:**

> `HTTPException` è definita in `fastapi/exceptions.py` alla riga 17 circa, come classe `HTTPException(StarletteHTTPException)`; il simbolo è anche indicato in `fastapi/exceptions.py#2-3` nei risultati di ricerca. Fonte: `fastapi/exceptions.py:17` e `fastapi/exceptions.py#2-3`.
> 
> Ecco alcuni esempi di codice che la usa:
> 
> - In una dependency che valida un header:
>   - `docs_src/dependencies/tutorial006_py310.py#1`
>   - esempio: `raise HTTPException(status_code=400, detail="X-Token header invalid")`
> 
> - In un altro tutorial equivalente:
>   - `docs_src/dependencies/tutorial012_py310.py#1`
>   - stesso pattern: `raise HTTPException(status_code=400, detail="X-Token header invalid")`
> 
> - Nel codice di sicurezza HTTP:
>   - `fastapi/security/http.py#6`
>   - `return HTTPException(status_code=HTTP_401_UNAUTHORIZED, ...)`
> 
> - Nel gestore delle eccezioni HTTP:
>   - `fastapi/exception_handlers.py#1`
>   - funzione `http_exception_handler(request: Request, exc: HTTPException)`
> 
> - Nella documentazione sugli errori:
>   - `docs/en/docs/tutorial/handling-errors.md#1`
>   - sezione “Import `HTTPException`” e “Raise an `HTTPException` in your code”
> 
> Se vuoi, posso anche mostrarti il contenuto della definizione di `HTTPException` in `fastapi/exceptions.py` oppure raccogliere 3-5 esempi completi con contesto più ampio.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 6 strumenti

---

## «Qual è la differenza tra una funzione di endpoint definita con def e una con async def in FastAPI?»

> **Tipo:** doc-concept · **Atteso:** la risposta cita `async.md` · **strumenti ideali:** `search_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code` → `find_symbol` → `search_docs` → `search_code` → `search_code`

**Ha risposto:**

> In FastAPI, la differenza principale è questa:
> 
> - **`async def`**: la funzione dell’endpoint viene eseguita come **coroutine asincrona** e può usare `await` per operazioni I/O non bloccanti. È la scelta naturale quando fai chiamate a database/HTTP client/librerie async.  
> - **`def`**: la funzione dell’endpoint viene eseguita in un **threadpool**, così non blocca il loop asincrono principale mentre svolge lavoro sincrono/bloccante. FastAPI lo fa automaticamente per le path operation functions definite con `def`.  
> 
> Fonti:
> - Documentazione FastAPI: le path operation functions con `def` invece di `async def` vengono eseguite in un threadpool (`docs/en/docs/async.md#27`).
> - Implementazione FastAPI: `run_endpoint_function(..., is_coroutine: bool)` gestisce l’esecuzione dell’endpoint in base al fatto che sia coroutine o meno (`fastapi/routing.py:320`).
> 
> In pratica:
> - usa **`async def`** se il codice interno è async e puoi fare `await`;
> - usa **`def`** se il codice è sincrono/bloccante e vuoi che FastAPI lo sposti fuori dal loop principale.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 5 passi · 6 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code` → `search_docs` → `find_symbol` → `find_symbol` → `search_code` → `search_code`

**Ha risposto:**

> to=functions.search_code  天天中彩票和json
> {"query":"run_in_threadpool fastapi/routing.py threadpool", "k":20}
> In FastAPI, la differenza principale è **come viene eseguita la funzione di endpoint**:
> 
> - **`async def`**: l’endpoint è una coroutine e viene eseguito nel loop async. È la scelta giusta quando usi operazioni I/O compatibili con `await` (per esempio client HTTP async, database async, file async, ecc.).
> - **`def`**: l’endpoint viene eseguito in un **threadpool** separato, così non blocca il event loop principale. FastAPI lo fa apposta per permettere di usare codice sincrono senza congelare l’app. La documentazione lo dice esplicitamente: una path operation definita con `def` “is run in a threadpool” (`docs/en/docs/async.md#27`).
> 
> Dal codice di FastAPI si vede che l’esecuzione dell’endpoint viene delegata in base a se la funzione è coroutine o no: `run_endpoint_function(..., is_coroutine: bool)` in `fastapi/routing.py#22` gestisce proprio questa distinzione, e il request handler passa di lì (`fastapi/routing.py#351`).
> 
> ### In pratica
> - Usa **`async def`** se:
>   - stai chiamando librerie async
>   - vuoi fare `await`
>   - vuoi sfruttare la concorrenza non bloccante
> - Usa **`def`** se:
>   - hai codice sincrono esistente
>   - chiami librerie che non supportano async
>   - il lavoro è CPU-bound o comunque non è pensato per `await`
> 
> ### Nota importante
> Se in un endpoint `async def` chiami una libreria bloccante senza `await`/senza delegarla, **blocchi il loop** e perdi i vantaggi dell’async. Per questo la documentazione suggerisce `async def` quando hai librerie terze asincrone, e `def` quando il codice è sincrono (`docs/en/docs/async.md#1`, `docs/en/docs/async.md#22`, `docs/en/docs/async.md#29`).
> 
> Se vuoi, posso anche mostrarti **un esempio pratico FastAPI con `def` vs `async def`** e quando conviene ciascuno.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 6 passi · 7 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code`

**Ha risposto:**

> In FastAPI, la differenza principale è **come viene eseguita la funzione**:
> 
> - **`async def`**: la funzione è una *coroutine* e può usare `await`. È ideale per operazioni **I/O-bound** non bloccanti, come chiamate a database/servizi HTTP con librerie async.
> - **`def`**: la funzione è sincrona. FastAPI la esegue in un **threadpool**, così non blocca il loop asincrono dell’applicazione.
> 
> Fonti:
> - Documentazione FastAPI: “When you declare a path operation function with normal `def` instead of `async def`, it is run in a threadpool” e se usi `async def` puoi usare `await` dentro la funzione. `docs/en/docs/async.md#22`, `docs/en/docs/async.md#27`
> - Nei dettagli tecnici della doc viene anche spiegato che `await` è utilizzabile solo dentro funzioni `async def`. `docs/en/docs/async.md#22`
> 
> In pratica:
> 
> - usa **`async def`** se chiami librerie async e vuoi sfruttare la concorrenza senza bloccare;
> - usa **`def`** se il codice è sincrono o usi librerie che non supportano async.
> 
> Se vuoi, posso anche spiegarti **quando conviene scegliere `def` rispetto a `async def`** con esempi concreti.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 2 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code` → `search_docs` → `search_docs`

**Ha risposto:**

> In FastAPI, la differenza principale è **come viene eseguita la funzione**, non il fatto che l’endpoint “funzioni” o meno.
> 
> - **`async def`**: definisce una coroutine. FastAPI la esegue direttamente nell’event loop, quindi è ideale per operazioni **I/O-bound** che supportano `await` (es. chiamate HTTP async, database async, file async).  
> - **`def`**: FastAPI la esegue in un **threadpool** separato, così non blocca l’event loop. È utile per codice **sincrono/bloccante** o librerie che non supportano `async`/`await`.
> 
> Quindi:
> - usa **`async def`** se stai usando librerie async e vuoi sfruttare la concorrenza;
> - usa **`def`** se il codice è sincrono o se chiami librerie bloccanti.
> 
> FastAPI documenta esplicitamente che una path operation function definita con `def` invece di `async def` viene eseguita in un threadpool, mentre `async def` è la forma naturale per codice asincrono. Vedi **docs/en/docs/async.md#27** e il riepilogo in **docs/en/docs/async.md#2**.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 4 strumenti

---

## «Come si dichiara un parametro di query in FastAPI? Mostra sia dove è implementato Query sia la documentazione che lo spiega.»

> **Tipo:** code+doc · **Atteso:** la risposta cita `fastapi/params.py` o `fastapi/param_functions.py` o `query-param` · **strumenti ideali:** `find_symbol`, `search_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_docs` → `find_symbol` → `search_docs` → `search_code` → `find_symbol` → `search_docs` → `search_docs`

**Ha risposto:**

> In FastAPI, un parametro di query si dichiara normalmente come parametro della funzione con un default `Query(...)`:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: str | None = Query(default=None, max_length=50)):
>     return {"q": q}
> ```
> 
> Oppure, se vuoi renderlo obbligatorio:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: str = Query(...)):
>     return {"q": q}
> ```
> 
> ### Dove è implementato `Query`
> - Funzione factory `Query` in `fastapi/param_functions.py#357`
> - Classe `Query` in `fastapi/params.py#221`
> 
> ### Documentazione che lo spiega
> - Guida principale sui query parameters: `docs/en/docs/tutorial/query-params.md#0`
> - Sezione sui query parameters obbligatori: `docs/en/docs/tutorial/query-params.md#3`
> - Esempi di validazione e default: `docs/en/docs/tutorial/query-params-str-validations.md#4` e `docs/en/docs/tutorial/query-params-str-validations.md#10`
> 
> ### Nota utile
> FastAPI interpreta automaticamente come query parameters gli argomenti della funzione che **non** fanno parte del path; `Query()` serve per aggiungere metadati, validazioni e per dichiarare esplicitamente il parametro come query. Vedi `docs/en/docs/tutorial/query-params.md#0`.
> 
> Se vuoi, posso anche mostrarti la differenza tra `Query(...)`, `Query(None)` e `Annotated[..., Query()]`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 8 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_docs` → `find_symbol` → `search_code` → `search_docs` → `related_docs` → `search_docs` → `search_docs` → `search_code`

**Ha risposto:**

> In FastAPI, un parametro di query si dichiara normalmente come argomento della funzione di path operation, usando `Query()` per aggiungere vincoli/metadati. Esempio tipico:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: str | None = Query(default=None, min_length=3)):
>     return {"q": q}
> ```
> 
> La documentazione dice che i parametri della funzione che **non** fanno parte del path vengono interpretati automaticamente come **query parameters**. Puoi vedere la spiegazione in `docs/en/docs/tutorial/query-params.md#0` e i dettagli sui tipi/validazioni in `docs/en/docs/tutorial/query-params.md#2`.  
> La reference generale sui request parameters è in `docs/en/docs/reference/parameters.md#0`.
> 
> Dove è implementato `Query`:
> - funzione factory: `fastapi/param_functions.py#8`
> - classe sottostante: `fastapi/params.py#10` e `fastapi/params.py#11`
> 
> Quindi:
> - **uso**: parametro di funzione con `Query(...)`
> - **implementazione**: `fastapi/param_functions.py` + `fastapi/params.py`
> - **documentazione**: `docs/en/docs/tutorial/query-params.md#0`, `docs/en/docs/tutorial/query-params.md#2`, `docs/en/docs/reference/parameters.md#0`
> 
> Se vuoi, posso anche mostrarti come dichiarare query params opzionali, con default, liste, oppure con validazioni tipo `min_length`, `max_length`, `regex`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 9 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_combined` → `find_symbol` → `search_docs` → `find_symbol` → `find_symbol` → `who_calls` → `search_code` → `search_docs` → `search_code` → `search_code`

**Ha risposto:**

> In FastAPI, un parametro di query si dichiara mettendo `Query(...)` come valore di default del parametro della funzione, ad esempio:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: str = Query(default=None)):
>     return {"q": q}
> ```
> 
> Oppure con `Annotated`:
> 
> ```python
> from typing import Annotated
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: Annotated[str | None, Query()] = None):
>     return {"q": q}
> ```
> 
> ### Dove è implementato `Query`
> L’implementazione del simbolo `Query` è in:
> 
> - `fastapi/param_functions.py#8` — funzione `Query(...)`
> - `fastapi/params.py#10` — classe `Query(Param)`
> - `fastapi/params.py#11` — costruttore `__init__` della classe `Query`
> 
> Quindi il factory usato nelle firme è `fastapi/param_functions.py#8`, mentre la classe dati/parametro sottostante è `fastapi/params.py#10-11`.
> 
> ### Documentazione che lo spiega
> La guida ufficiale sui parametri di query è:
> 
> - `docs/en/docs/tutorial/query-params.md#0` — spiega che i parametri di funzione non presenti nel path vengono interpretati automaticamente come query parameters
> - `docs/en/docs/tutorial/query-params.md#1` — sezione sui default, cioè query parameters opzionali e valori di default
> 
> La frase chiave della doc è:
> 
> > “When you declare other function parameters that are not part of the path parameters, they are automatically interpreted as query parameters”
> 
> Fonte: `docs/en/docs/tutorial/query-params.md#0`
> 
> Se vuoi, posso anche mostrarti il collegamento interno tra `Query()` e la generazione dell’OpenAPI schema.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 11 passi · 10 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_code` → `search_docs` → `find_symbol` → `search_code` → `search_docs` → `related_docs` → `search_code` → `search_code` → `search_docs`

**Ha risposto:**

> In FastAPI, un parametro di query si dichiara tipicamente nel path operation function come parametro normale, oppure esplicitamente con `Query(...)` per aggiungere validazioni/metadati.
> 
> Esempio base:
> 
> ```python
> from fastapi import FastAPI, Query
> 
> app = FastAPI()
> 
> @app.get("/items/")
> def read_items(q: str | None = Query(default=None, min_length=3)):
>     return {"q": q}
> ```
> 
> Qui `q` è un query parameter perché non fa parte del path, e `Query(...)` serve a specificarne il comportamento. La documentazione dice che i parametri della funzione che non sono path parameters vengono interpretati automaticamente come query parameters. Vedi: `docs/en/docs/tutorial/query-params.md#0`.
> 
> Dove è implementato `Query`:
> - `fastapi/param_functions.py#8` — funzione `Query(...)`
> - `fastapi/params.py#10` — classe `Query(Param)` con `in_ = ParamTypes.query`
> 
> Documentazione utile:
> - `docs/en/docs/tutorial/query-params.md#0` — spiegazione dei query parameters
> - `docs/en/docs/reference/parameters.md#0` — riferimento dei request parameters
> 
> Se vuoi, posso anche mostrarti la differenza tra `Query`, `Path`, `Header` e `Cookie` con esempi.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 4 passi · 9 strumenti

---

## «A cosa servono le BackgroundTasks e dove sono documentate?»

> **Tipo:** code+doc · **Atteso:** la risposta cita `background-tasks.md` o `reference/background` o `background.md` · **strumenti ideali:** `search_docs`, `related_docs`, `search_combined`

### 🤖 vanilla  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_combined` → `find_symbol` → `search_docs` → `search_code`

**Ha risposto:**

> Le `BackgroundTasks` servono per eseguire operazioni **dopo** che la risposta è già stata inviata al client. Sono utili per attività non critiche nel percorso della request, ad esempio inviare una notifica, scrivere un log o aggiornare qualcosa in modo asincrono rispetto alla risposta. La documentazione avverte anche che **non sono pensate per calcoli pesanti** o lavori che devono essere affidati a un processo separato.  
> Fonti: `docs/en/docs/tutorial/background-tasks.md#0`, `docs/en/docs/tutorial/background-tasks.md#4`
> 
> Dove sono documentate:
> - **Tutorial principale**: `docs/en/docs/tutorial/background-tasks.md#0`
> - **Riferimento API**: `docs/en/docs/reference/background.md#0`
> 
> Nel codice, la classe è definita in:
> - `fastapi/background.py#1`
> 
> Se vuoi, posso anche riassumerti **come si usano** con un esempio tratto dalla codebase.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 4 strumenti

### 🤖 autogen  ·  _gpt-5.4-mini_

**Ha fatto:** `search_combined` → `search_code` → `search_docs`

**Ha risposto:**

> Le `BackgroundTasks` servono per eseguire operazioni **dopo** che la risposta HTTP è già stata inviata al client, senza bloccare la request principale. Sono utili per attività leggere come invio email, logging, o scrittura di file, quando non serve una coda esterna. Questo è spiegato nella guida tutorial: `docs/en/docs/tutorial/background-tasks.md#0` e nel dettaglio tecnico in `docs/en/docs/tutorial/background-tasks.md#3`.  
> 
> In più, la documentazione dice che puoi dichiarare `BackgroundTasks` sia in una path operation sia in una dependency, e poi aggiungere task con `add_task(...)`: `docs/en/docs/reference/background.md#0` e `docs/en/docs/tutorial/background-tasks.md#2`.  
> 
> Dal codice, la classe è definita in `fastapi/background.py#1`, dove è descritta come una collezione di task che verranno chiamati dopo l’invio della response.  
> 
> Nota: per calcoli pesanti o lavoro distribuito, la doc sconsiglia di usare `BackgroundTasks` e suggerisce sistemi esterni tipo task queue: `docs/en/docs/tutorial/background-tasks.md#4`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

### 🤖 sk  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_docs` → `search_code`

**Ha risposto:**

> Le `BackgroundTasks` servono a eseguire operazioni **dopo** che la risposta è già stata inviata al client, quindi senza bloccare la request principale. Sono utili per attività come invio email, scrittura di log, notifiche, o altre operazioni non critiche per la risposta immediata. La documentazione segnala anche che, se hai bisogno di calcolo pesante o distribuito, potresti voler usare strumenti esterni invece dei background task del processo corrente.  
> Fonti: `docs/en/docs/tutorial/background-tasks.md#0`, `docs/en/docs/tutorial/background-tasks.md#3`, `docs/en/docs/tutorial/background-tasks.md#4`
> 
> Sono documentate qui:
> - **Tutorial introduttivo**: `docs/en/docs/tutorial/background-tasks.md#0`
> - **Riferimento API**: `docs/en/docs/reference/background.md#0`
> 
> Nel codice, la classe è definita in:
> - `fastapi/background.py#1`

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 3 passi · 2 strumenti

### 🤖 langgraph  ·  _azure:gpt-5.4-mini_

**Ha fatto:** `search_combined` → `search_code` → `search_docs`

**Ha risposto:**

> Le `BackgroundTasks` servono a eseguire operazioni **dopo** che la risposta è già stata inviata al client, quindi sono utili per lavori non critici nel flusso della request, come inviare notifiche o scrivere log. Questo è spiegato nella guida **Background Tasks**: `docs/en/docs/tutorial/background-tasks.md#0` e anche nella reference API `docs/en/docs/reference/background.md#0`.
> 
> Nel codice, la classe è definita in `fastapi/background.py#1`, dove la docstring dice esplicitamente che è “a collection of background tasks that will be called after a response has been sent to the client”. Inoltre, la guida chiarisce che `BackgroundTasks` deriva da `starlette.background` e che si integra con la dependency injection: `docs/en/docs/tutorial/background-tasks.md#3` e `docs/en/docs/tutorial/background-tasks.md#2`.
> 
> In breve:
> - **A cosa servono:** eseguire task dopo la response, senza bloccare il client `docs/en/docs/tutorial/background-tasks.md#0`
> - **Dove sono documentate:** tutorial e reference in `docs/en/docs/tutorial/background-tasks.md#0` e `docs/en/docs/reference/background.md#0`
> - **Dove sono implementate:** `fastapi/background.py#1`
> 
> Se vuoi, posso anche mostrarti un esempio d’uso preso dai file `docs_src/background_tasks/...`.

**Esito:** ✅ ha citato il file atteso · strumento giusto ✅ · 2 passi · 3 strumenti

---
