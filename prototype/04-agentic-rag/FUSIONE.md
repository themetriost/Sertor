# FUSIONE — dual-RAG vs LLM (documentazione parlante, auto-generata)

> Generato da `04-agentic-rag/compare_fusion.py`. Confronta due modi di **unire codice e documentazione** per un simbolo: la **fusione dual-RAG** (`get_context`, deterministica, 0 token LLM) e la **fusione fatta dall'LLM** (assembla dai tool primitivi).

## Riepilogo: l'LLM ricostruisce ciò che il dual-RAG dà per costruzione?

Il bundle dual-RAG è il **riferimento**: `✅`=l'LLM l'ha coperto, `❌`=mancato, `—`=non applicabile.

| Simbolo | def (LLM) | chiamanti (LLM) | doc (LLM) | costo LLM (tool/turni) | costo dual-RAG |
|---|---|---|---|---|---|
| `OAuth2PasswordBearer` | ✅ | — | ✅ | 3 tool / 2 turni | 1 chiamata · **0 token LLM** |
| `HTTPException` | ✅ | ✅ | ✅ | 3 tool / 2 turni | 1 chiamata · **0 token LLM** |
| `APIRouter` | ✅ | ✅ | ✅ | 6 tool / 4 turni | 1 chiamata · **0 token LLM** |
| `BackgroundTasks` | ✅ | ✅ | ✅ | 3 tool / 2 turni | 1 chiamata · **0 token LLM** |

Il dual-RAG copre per costruzione definizione+chiamanti+doc collegati (dove esistono), in modo deterministico e gratuito. L'LLM può ricostruirli ma dipende dai tool che sceglie e paga ogni volta; può anche omettere una parte (es. i doc) o fermarsi prima.

---

## `OAuth2PasswordBearer`

### 🧩 dual-RAG — `get_context` (deterministico, 0 LLM)

- **Definizione:** fastapi/security/oauth2.py:433  class OAuth2PasswordBearer
- **Codice:** fastapi/security/oauth2.py:433-441
- **Chiamanti:** —
- **Doc collegati:** docs/en/docs/reference/security/index.md (grafo:mentions), docs/en/docs/release-notes.md (grafo:mentions), docs/en/docs/tutorial/security/first-steps.md (grafo:mentions), docs/en/docs/tutorial/security/simple-oauth2.md (grafo:mentions)

### 🤖 LLM — `vanilla` (azure:gpt-5.4-mini) assembla dai tool primitivi

**Ha usato:** `find_symbol` → `who_calls` → `related_docs`

**Ha risposto:**

> Ecco il contesto completo di `OAuth2PasswordBearer` nella codebase.
> 
> ## 1) Dove è definito
> Il simbolo è definito in:
> 
> - `fastapi/security/oauth2.py:433` — `class OAuth2PasswordBearer`
> 
> ## 2) Chi lo usa / chi lo chiama nel codice
> La ricerca dei chiamanti non ha restituito risultati:
> 
> - **nessun risultato trovato** per `who_calls(OAuth2PasswordBearer)`
> 
> Quindi, nel grafo dei simboli disponibile, non risultano chiamate dirette a `OAuth2PasswordBearer` da altri simboli del codice indicizzato.
> 
> ## 3) Quali documenti lo spiegano
> I documenti Markdown che lo menzionano sono:
> 
> - `docs/en/docs/reference/security/index.md`
> - `docs/en/docs/release-notes.md`
> - `docs/en/docs/tutorial/security/first-steps.md`
> - `docs/en/docs/tutorial/security/simple-oauth2.md`
> 
> Se vuoi, posso anche ricostruirti il contesto d’uso pratico di `OAuth2PasswordBearer` nel codice FastAPI, ad esempio mostrando la sua implementazione e i simboli correlati.

---

## `HTTPException`

### 🧩 dual-RAG — `get_context` (deterministico, 0 LLM)

- **Definizione:** fastapi/exceptions.py:17  class HTTPException
- **Codice:** fastapi/exceptions.py:17-44
- **Chiamanti:** docs_src/app_testing/app_b_an_py310/main.py:32  function create_item, docs_src/app_testing/app_b_an_py310/main.py:23  function read_main, docs_src/app_testing/app_b_py310/main.py:30  function create_item, docs_src/app_testing/app_b_py310/main.py:21  function read_main, docs_src/authentication_error_status_code/tutorial001_an_py310.py:10  method HTTPBearer403.make_not_authenticated_error, docs_src/bigger_applications/app_an_py310/dependencies.py:11  function get_query_token, docs_src/bigger_applications/app_an_py310/dependencies.py:6  function get_token_header, docs_src/bigger_applications/app_an_py310/routers/items.py:22  function read_item
- **Doc collegati:** docs/en/docs/advanced/advanced-dependencies.md (grafo:mentions), docs/en/docs/advanced/security/http-basic-auth.md (grafo:mentions), docs/en/docs/advanced/security/oauth2-scopes.md (grafo:mentions), docs/en/docs/advanced/websockets.md (grafo:mentions), docs/en/docs/reference/exceptions.md (grafo:mentions), docs/en/docs/release-notes.md (grafo:mentions)

### 🤖 LLM — `vanilla` (azure:gpt-5.4-mini) assembla dai tool primitivi

**Ha usato:** `find_symbol` → `who_calls` → `related_docs`

**Ha risposto:**

> Ecco il contesto completo di `HTTPException` nella codebase, con riferimenti ai file.
> 
> ## 1) Dove è definito
> 
> Il simbolo `HTTPException` è definito in:
> 
> - `fastapi/exceptions.py:17` — `class HTTPException`
> 
> Questa è la definizione principale del simbolo nella codebase.
> 
> ## 2) Chi lo usa / chi lo chiama nel codice
> 
> Dalla call graph risultano questi usi/chiamate di `HTTPException`:
> 
> ### Codice applicativo / esempi in `docs_src`
> - `docs_src/app_testing/app_b_an_py310/main.py:23` — `function read_main`
> - `docs_src/app_testing/app_b_an_py310/main.py:32` — `function create_item`
> - `docs_src/app_testing/app_b_py310/main.py:21` — `function read_main`
> - `docs_src/app_testing/app_b_py310/main.py:30` — `function create_item`
> - `docs_src/authentication_error_status_code/tutorial001_an_py310.py:10` — `method HTTPBearer403.make_not_authenticated_error`
> - `docs_src/bigger_applications/app_an_py310/dependencies.py:6` — `function get_token_header`
> - `docs_src/bigger_applications/app_an_py310/dependencies.py:11` — `function get_query_token`
> - `docs_src/bigger_applications/app_an_py310/routers/items.py:22` — `function read_item`
> - `docs_src/bigger_applications/app_an_py310/routers/items.py:33` — `function update_item`
> - `docs_src/custom_request_and_route/tutorial002_an_py310.py:13` — `method ValidationErrorLoggingRoute.get_route_handler.custom_route_handler`
> - `docs_src/custom_request_and_route/tutorial002_py310.py:12` — `method ValidationErrorLoggingRoute.get_route_handler.custom_route_handler`
> - `docs_src/dependencies/tutorial006_an_py310.py:8` — `function verify_token`
> - `docs_src/dependencies/tutorial006_an_py310.py:13` — `function verify_key`
> - `docs_src/dependencies/tutorial006_py310.py:6` — `function verify_token`
> - `docs_src/dependencies/tutorial006_py310.py:11` — `function verify_key`
> - `docs_src/dependencies/tutorial008b_an_py310.py:18` — `function get_username`
> - `docs_src/dependencies/tutorial008b_an_py310.py:26` — `function get_item`
> - `docs_src/dependencies/tutorial008b_py310.py:16` — `function get_username`
> - `docs_src/dependencies/tutorial008b_py310.py:24` — `function get_item`
> - `docs_src/dependencies/tutorial008c_an_py310.py:20` — `function get_item`
> - `docs_src/dependencies/tutorial008c_py310.py:18` — `function get_item`
> - `docs_src/dependencies/tutorial008d_an_py310.py:21` — `function get_item`
> - `docs_src/dependencies/tutorial008d_py310.py:19` — `function get_item`
> - `docs_src/dependencies/tutorial012_an_py310.py:6` — `function verify_token`
> - `docs_src/dependencies/tutorial012_an_py310.py:11` — `function verify_key`
> - `docs_src/dependencies/tutorial012_py310.py:4` — `function verify_token`
> - `docs_src/dependencies/tutorial012_py310.py:9` — `function verify_key`
> - `docs_src/dependencies/tutorial013_an_py310.py:24` — `function get_user`
> - `docs_src/dependencies/tutorial014_an_py310.py:24` — `function get_user`
> - `docs_src/handling_errors/tutorial001_py310.py:9` — `function read_item`
> - `docs_src/handling_errors/tutorial002_py310.py:9` — `function read_item_header`
> - `docs_src/handling_errors/tutorial004_py310.py:23` — `function read_item`
> - `docs_src/handling_errors/tutorial006_py310.py:25` — `function read_item`
> - `docs_src/path_operation_advanced_configuration/tutorial007_py310.py:22` — `function create_item`
> - `docs_src/security/tutorial003_an_py310.py:58` — `function get_current_user`
> - `docs_src/security/tutorial003_an_py310.py:69` — `function get_current_active_user`
> - `docs_src/security/tutorial003_an_py310.py:78` — `function login`
> - `docs_src/security/tutorial003_py310.py:56` — `function get_current_user`
> - `docs_src/security/tutorial003_py310.py:67` — `function get_current_active_user`
> - `docs_src/security/tutorial003_py310.py:74` — `function login`
> - `docs_src/security/tutorial004_an_py310.py:93` — `function get_current_user`
> - `docs_src/security/tutorial004_an_py310.py:113` — `function get_current_active_user`
> - `docs_src/security/tutorial004_an_py310.py:122` — `function login_for_access_token`
> - `docs_src/security/tutorial004_py310.py:92` — `function get_current_user`
> - `docs_src/security/tutorial004_py310.py:112` — `function get_current_active_user`
> - `docs_src/security/tutorial004_py310.py:119` — `function login_for_access_token`
> - `docs_src/security/tutorial005_an_py310.py:108` — `function get_current_user`
> - `docs_src/security/tutorial005_an_py310.py:143` — `function get_current_active_user`
> - `docs_src/security/tutorial005_an_py310.py:152` — `function login_for_access_token`
> - `docs_src/security/tutorial005_py310.py:107` — `function get_current_user`
> - `docs_src/security/tutorial005_py310.py:142` — `function get_current_active_user`
> - `docs_src/security/tutorial005_py310.py:151` — `function login_for_access_token`
> - `docs_src/security/tutorial007_an_py310.py:12` — `function get_current_username`
> - `docs_src/security/tutorial007_py310.py:11` — `function get_current_username`
> - `docs_src/sql_databases/tutorial001_an_py310.py:59` — `function read_hero`
> - `docs_src/sql_databases/tutorial001_an_py310.py:67` — `function delete_hero`
> - `docs_src/sql_databases/tutorial001_py310.py:55` — `function read_hero`
> - `docs_src/sql_databases/tutorial001_py310.py:63` — `function delete_hero`
> - `docs_src/sql_databases/tutorial002_an_py310.py:76` — `function read_hero`
> - `docs_src/sql_databases/tutorial002_an_py310.py:84` — `function update_hero`
> - `docs_src/sql_databases/tutorial002_an_py310.py:97` — `function delete_hero`
> - `docs_src/sql_databases/tutorial002_py310.py:73` — `function read_hero`
> - `docs_src/sql_databases/tutorial002_py310.py:81` — `function update_hero`
> - `docs_src/sql_databases/tutorial002_py310.py:96` — `function delete_hero`
> 
> ### Uso interno della libreria FastAPI
> - `fastapi/routing.py:382` — `method get_request_handler.app`
> - `fastapi/security/api_key.py:31` — `method APIKeyBase.make_not_authenticated_error`
> - `fastapi/security/http.py:87` — `method HTTPBase.make_not_authenticated_error`
> - `fastapi/security/oauth2.py:401` — `method OAuth2.make_not_authenticated_error`
> - `fastapi/security/open_id_connect_url.py:80` — `method OpenIdConnect.make_not_authenticated_error`
> 
> ## 3) Quali documenti lo spiegano
> 
> I documenti Markdown che lo menzionano/spiegano sono:
> 
> - `docs/en/docs/reference/exceptions.md`
> - `docs/en/docs/tutorial/handling-errors.md`
> - `docs/en/docs/tutorial/dependencies/dependencies-with-yield.md`
> - `docs/en/docs/tutorial/security/simple-oauth2.md`
> - `docs/en/docs/advanced/advanced-dependencies.md`
> - `docs/en/docs/advanced/security/http-basic-auth.md`
> - `docs/en/docs/advanced/security/oauth2-scopes.md`
> - `docs/en/docs/advanced/websockets.md`
> - `docs/en/docs/release-notes.md`
> 
> ## Sintesi rapida
> 
> - **Definizione:** `fastapi/exceptions.py:17`
> - **Usi nel codice:** soprattutto in `fastapi/routing.py`, nei moduli `fastapi/security/*`, e in molti esempi sotto `docs_src/*`
> - **Documentazione:** soprattutto `docs/en/docs/reference/exceptions.md` e `docs/en/docs/tutorial/handling-errors.md`, più varie guide su dependency/security
> 
> Se vuoi, posso anche fare un secondo passaggio e raggruppare gli usi di `HTTPException` per categoria, ad esempio:
> 1. errori di validazione/route,
> 2. security/auth,
> 3. esempi tutorial,
> 4. gestione errori generica.

---

## `APIRouter`

### 🧩 dual-RAG — `get_context` (deterministico, 0 LLM)

- **Definizione:** fastapi/routing.py:1005  class APIRouter
- **Codice:** fastapi/routing.py:1005-1031
- **Chiamanti:** fastapi/applications.py:57  method FastAPI.__init__
- **Doc collegati:** docs/en/docs/_llm-test.md (grafo:mentions), docs/en/docs/advanced/custom-response.md (grafo:mentions), docs/en/docs/advanced/openapi-callbacks.md (grafo:mentions), docs/en/docs/advanced/openapi-webhooks.md (grafo:mentions), docs/en/docs/how-to/custom-request-and-route.md (grafo:mentions), docs/en/docs/reference/apirouter.md (grafo:mentions)

### 🤖 LLM — `vanilla` (azure:gpt-5.4-mini) assembla dai tool primitivi

**Ha usato:** `find_symbol` → `who_calls` → `related_docs` → `search_code` → `search_docs` → `search_code`

**Ha risposto:**

> Ecco il contesto completo di `APIRouter` nella codebase, con i limiti di ciò che sono riuscito a recuperare.
> 
> ## 1) Dove è definito
> Il simbolo `APIRouter` è definito in:
> 
> - `fastapi/routing.py:1005` — `class APIRouter`
> 
> ## 2) Chi lo usa / chi lo chiama nel codice
> Dal grafo dei simboli risulta che `APIRouter` è chiamato/usato da:
> 
> - `fastapi/applications.py:57` — metodo `FastAPI.__init__`
> 
> Non sono riuscito a ottenere un elenco più completo dei chiamanti perché i tool di ricerca sul codice hanno restituito un errore interno durante l’analisi.
> 
> ## 3) Quali documenti lo spiegano
> I documenti che lo menzionano/spiegano sono:
> 
> - `docs/en/docs/_llm-test.md`
> - `docs/en/docs/advanced/custom-response.md`
> - `docs/en/docs/advanced/openapi-callbacks.md`
> - `docs/en/docs/advanced/openapi-webhooks.md`
> - `docs/en/docs/how-to/custom-request-and-route.md`
> - `docs/en/docs/reference/apirouter.md`
> - `docs/en/docs/release-notes.md`
> - `docs/en/docs/tutorial/bigger-applications.md`
> - `docs/en/docs/tutorial/metadata.md`
> - `docs/en/docs/tutorial/static-files.md`
> 
> ## Nota
> Ho usato il grafo dei simboli per la definizione e i riferimenti, ma le ricerche testuali su codice e docs hanno avuto un errore 500 del backend di embedding, quindi non posso garantire che l’elenco dei chiamanti sia esaustivo oltre a quanto emerso dal grafo.
> 
> Se vuoi, posso fare un secondo passaggio mirato per ricostruire:
> - tutti gli import/usi di `APIRouter` nel codice,
> - e un riassunto dei contenuti di `docs/en/docs/reference/apirouter.md` e degli altri documenti citati.

---

## `BackgroundTasks`

### 🧩 dual-RAG — `get_context` (deterministico, 0 LLM)

- **Definizione:** fastapi/background.py:11  class BackgroundTasks
- **Codice:** fastapi/background.py:11-39
- **Chiamanti:** fastapi/dependencies/utils.py:598  function solve_dependencies
- **Doc collegati:** docs/en/docs/reference/background.md (grafo:mentions), docs/en/docs/release-notes.md (grafo:mentions), docs/en/docs/tutorial/background-tasks.md (grafo:mentions)

### 🤖 LLM — `vanilla` (azure:gpt-5.4-mini) assembla dai tool primitivi

**Ha usato:** `find_symbol` → `who_calls` → `related_docs`

**Ha risposto:**

> Ecco il contesto completo di `BackgroundTasks` nella codebase.
> 
> ## 1) Dove è definito
> Il simbolo `BackgroundTasks` è definito in:
> 
> - `fastapi/background.py:11` — `class BackgroundTasks`
> 
> ## 2) Chi lo usa / chi lo chiama nel codice
> Dalla call graph risulta usato da:
> 
> - `fastapi/dependencies/utils.py:598` — funzione `solve_dependencies`
> 
> ## 3) Quali documenti lo spiegano
> I documenti Markdown che lo menzionano/spiegano sono:
> 
> - `docs/en/docs/reference/background.md` — documentazione di riferimento
> - `docs/en/docs/release-notes.md` — note di rilascio
> - `docs/en/docs/tutorial/background-tasks.md` — tutorial dedicato ai background tasks
> 
> Se vuoi, posso anche ricostruirti il flusso completo di utilizzo di `BackgroundTasks` nella FastAPI codebase, partendo dalla definizione fino all’iniezione nelle dependency.

---
