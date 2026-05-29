# ESEMPI — Agentic RAG (documentazione parlante, auto-generata)

> **File generato** da `04-agentic-rag/evaluate.py` (non modificare a mano). Mostra, per ogni
> domanda e per ogni motore, *cosa ho chiesto → cosa ha fatto l'agente → cosa mi ha risposto*.
> È la controparte divulgativa di [`ESEMPI.md`](../ESEMPI.md) per la Tappa 04.

## Riepilogo (a parità di tool e prompt)

| Motore | task | cita atteso | passi medi | tool medi |
|---|---|---|---|---|
| `vanilla` | 5 | 5/5 | 2.0 | 1.0 |
| `autogen` | 5 | 5/5 | 1.4 | 1.4 |

- **cita atteso**: la risposta finale nomina il file giusto (successo end-to-end).
- I motori condividono `tools.py` e il system prompt: le differenze sono di **orchestrazione**.

---

## «In quale file è definita la classe APIRouter di FastAPI?»

> **Atteso:** che la risposta citi `fastapi/routing.py`.

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `APIRouter` di FastAPI è definita nel file `fastapi/routing.py` alla riga 1005.  
> Riferimento: `fastapi/routing.py#1005`

**Esito:** ✅ ha citato il file atteso · 2 passi · 1 chiamate a strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `APIRouter` di FastAPI è definita nel file `fastapi/routing.py` alla riga 1005.
> 
> Path: fastapi/routing.py#1005

**Esito:** ✅ ha citato il file atteso · 1 passi · 1 chiamate a strumenti

---

## «Cos'è OAuth2PasswordBearer in FastAPI e in quale file è definito?»

> **Atteso:** che la risposta citi `fastapi/security/oauth2.py`.

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> OAuth2PasswordBearer è una classe di FastAPI utilizzata per implementare il flusso di autenticazione OAuth2 "password" (RFC 6749), che permette ai client di ottenere un token di accesso inviando credenziali utente (username e password) direttamente al server. Questa classe definisce il formato del token e gestisce la validazione delle richieste di autenticazione.
> 
> È definita nel file `fastapi/security/oauth2.py` alla riga 433:  
> `fastapi/security/oauth2.py#433`

**Esito:** ✅ ha citato il file atteso · 2 passi · 1 chiamate a strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> OAuth2PasswordBearer è una classe in FastAPI utilizzata per implementare il flusso OAuth2 di tipo "password grant" (autenticazione tramite username e password), consentendo di generare un token di accesso tramite la richiesta POST a un endpoint di autenticazione. È definita nel file **fastapi/security/oauth2.py#433**.

**Esito:** ✅ ha citato il file atteso · 1 passi · 1 chiamate a strumenti

---

## «Dove è implementato Depends in FastAPI? Indica il file.»

> **Atteso:** che la risposta citi `fastapi/param_functions.py` o `fastapi/params.py`.

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> Il simbolo `Depends` è implementato come classe nel file `fastapi/params.py` alla riga 746.  
> Riferimento: `fastapi/params.py:746`

**Esito:** ✅ ha citato il file atteso · 2 passi · 1 chiamate a strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> Il simbolo `Depends` è implementato come classe in **fastapi/params.py:746**. 
> 
> Il risultato della ricerca mostra anche una definizione funzionale in `fastapi/param_functions.py:2283`, ma la definizione principale e utilizzata in FastAPI è la classe presente in `params.py` (linea 746). 
> 
> Per riferimento:  
> - `fastapi/params.py:746` è la definizione della classe `Depends` che gestisce le dipendenze nell'applicazione.  
> - `fastapi/param_functions.py:2283` è un'utilizzo funzionale (non la definizione principale).

**Esito:** ✅ ha citato il file atteso · 1 passi · 1 chiamate a strumenti

---

## «Cosa sono le BackgroundTasks in FastAPI e in quale file sono definite?»

> **Atteso:** che la risposta citi `fastapi/background.py`.

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> Le `BackgroundTasks` in FastAPI sono una classe utilizzata per eseguire operazioni in background dopo la risposta HTTP inviata al client (ad esempio, invio email, elaborazione dati). Sono definite nel file `fastapi/background.py` alla riga 11.  
> **Riferimento**: fastapi/background.py:11

**Esito:** ✅ ha citato il file atteso · 2 passi · 1 chiamate a strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol` → `search_docs` → `related_docs`

**Ha risposto:**

> Le `BackgroundTasks` in FastAPI sono un sistema per eseguire operazioni in background dopo aver inviato la risposta HTTP al client. Questo è utile per task non critici, come l'invio di email o la registrazione, senza bloccare la risposta HTTP.
> 
> **Definizione nel codice:**  
> Sono definite nella classe `BackgroundTasks` nel file seguente:
> - `fastapi/background.py#11`
> 
> **Documentazione rilevante:**  
> Per ulteriori dettagli ed esempi, consultare:
> - `docs/en/docs/reference/background.md` (riferimento API)
> - `docs/en/docs/tutorial/background-tasks.md` (tutorial dettagliato)

**Esito:** ✅ ha citato il file atteso · 3 passi · 3 chiamate a strumenti

---

## «In quale file del codice sorgente è definita la classe HTTPException?»

> **Atteso:** che la risposta citi `fastapi/exceptions.py`.

### 🤖 vanilla  ·  _ollama:qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita nel file `fastapi/exceptions.py` alla riga 17.

**Esito:** ✅ ha citato il file atteso · 2 passi · 1 chiamate a strumenti

### 🤖 autogen  ·  _qwen3:30b-a3b_

**Ha fatto:** `find_symbol`

**Ha risposto:**

> La classe `HTTPException` è definita nel file `fastapi/exceptions.py` alla riga 17.  
> Riferimento: `fastapi/exceptions.py:17`

**Esito:** ✅ ha citato il file atteso · 1 passi · 1 chiamate a strumenti

---
