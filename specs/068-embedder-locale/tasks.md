# Tasks — Embedder locale (local-first per indicizzazione, eval e CI) (FEAT-011)

**Branch**: `068-embedder-locale` | **Generato**: 2026-06-21
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/provider-resolution.md`](contracts/provider-resolution.md) ·
[`contracts/local-providers.md`](contracts/local-providers.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti in ordine di
> esecuzione. Git **mai** qui: brief di commit al fondo per il `configuration-manager`.
> Il core non chiama mai un LLM (confine D↔N vincolante).
>
> **Cambiamento trasversale — `RAG_BACKEND`.** La rimozione di `RAG_BACKEND` è il cambiamento più
> ampio della feature (~40 punti enumerati nel plan). Il plan identifica con precisione file e righe
> da toccare; ogni task di migrazione include un controllo "nessun riferimento residuo" nella
> categoria di propria competenza. Il task TASK-P02 chiude con una verifica cross-repo finale.
>
> **Strategia MVP/incrementale.**
> - **Fase 0 — Setup** (TASK-G01–G03): errori di dominio, Settings e migration di `RAG_BACKEND`
>   in settings/composition — zero dipendenze, bloccanti per tutto il resto.
> - **Fase 1 — Fondazionale** (TASK-F01–F03): tre nuovi adapter + resolver — tutti
>   parallelizzabili tra loro dopo il Setup; testabili in isolamento.
> - **Fase 2 — US1+US2** (TASK-A01–A06): composition factory estesa a 4 rami, test unitari
>   adapter, migrazione test core — realizza il profilo local-first + airgapped (P1 Must).
> - **Fase 3 — US3** (TASK-B01–B04): acquisizione GloVe on-demand, test unitari resolver/cache,
>   test integrazione GloVe su fixture — default semantico (P1 Must, ma dipende da Fase 2).
> - **Fase 4 — US4** (TASK-C01–C03): fail-loud e osservabilità, test unitari fail-loud — P1 Must.
> - **Fase 5 — US5** (TASK-D01–D04): corollario installabile — template `.env`, doc, nota di
>   migrazione, test installer (P1/Should per REQ-060/061; la feature non è "done" senza questo).
> - **Fase 6 — Polish** (TASK-P01–P03): migrazione test trasversale `RAG_BACKEND`, verifica
>   residui, lint e suite verde.
>
> La feature è **additiva**: a provider non selezionato, comportamento e costo di Ollama/Azure
> restano identici (RNF-4). Il breaking change dichiarato (rimozione `RAG_BACKEND`) è mitigato
> dall'avviso fail-loud REQ-007 e dalla nota di migrazione REQ-061.

---

## Fase 0 — Setup: errori, Settings e migrazione `RAG_BACKEND` (3 task)

> Prerequisiti zero. I tre task sono eseguibili in parallelo tra loro; tutti e tre sono bloccanti
> per le fasi successive.

### TASK-G01 — Aggiungi `GloveUnavailableError` in `domain/errors.py` [P]
**File**: `src/sertor_core/domain/errors.py`
→ dipende da: nessuno
- [ ] Aggiungi `GloveUnavailableError(SertorError)` con costruttore
      `__init__(self, message: str, *, reason: str)`.
      Il messaggio deve nominare **entrambe** le vie d'uscita:
      `"imposta SERTOR_GLOVE_PATH a un file glove.6B.300d.txt locale,
      oppure seleziona il provider lessicale con SERTOR_EMBED_PROVIDER=hash"` (REQ-040/041, DA-5).
- [ ] Verifica: `GloveUnavailableError` è sottoclasse di `SertorError`; `domain/errors.py`
      non importa nessun SDK esterno né adapter (Principio I).
- [ ] Verifica: i test esistenti su `errors.py` continuano a passare invariati (RNF-4).

### TASK-G02 — Ristruttura `Settings` (rimuovi `RAG_BACKEND`/`backend`, aggiungi nuovi campi) [P]
**File**: `src/sertor_core/config/settings.py`
→ dipende da: nessuno

Piano di modifica (righe del plan §"Punti del repo che referenziano `RAG_BACKEND`", punti 1–5):
- [ ] **Punto 1** — Rimuovi campo `backend: str = "local"` (riga 93).
- [ ] **Punto 2** — Rimuovi la property `embed_provider` (riga 211) derivata da `backend`;
      aggiungi al suo posto un **campo** `embed_provider: str = "glove"`.
      Valori ammessi: `glove` / `hash` / `ollama` / `azure`; la validazione del valore avviene
      nel composition root (non in Settings). (REQ-001/002)
- [ ] **Punto 3** — Ri-chiava `validate_backend()` (riga 224): usa `embed_provider == "azure"`
      al posto di `backend == "azure"`; provider locali (`glove`/`hash`) e `ollama` → lista vuota
      → mai blocco (REQ-005/007, DA-7). Il nome del metodo **resta** invariato (consumatori:
      `configure.py`/`config_fields.py` dell'installer).
- [ ] **Punto 4** — In `load()` (riga 254): elimina lettura di `RAG_BACKEND`; aggiungi warning
      fail-loud `log_event(WARNING, "config_rag_backend_ignored", …)` se
      `os.getenv("RAG_BACKEND")` è presente nell'ambiente, nominando le manopole sostitutive
      `SERTOR_EMBED_PROVIDER` e `SERTOR_STORE_BACKEND` (REQ-007, Principio XII). Il valore di
      `RAG_BACKEND` NON viene letto né mappato — segnalato e ignorato.
      Il warning `config_no_env_found` perde la condizione su `RAG_BACKEND`; la condizione resta
      su `env_path is None and env_file is not None`.
- [ ] **Punto 5** — In `load()` (righe 273–277): sostituisci
      `backend=…, store_backend=os.getenv(…, backend)` con
      `embed_provider=os.getenv("SERTOR_EMBED_PROVIDER", "glove")`,
      `store_backend=os.getenv("SERTOR_STORE_BACKEND", "local")`,
      `glove_path=Path(os.getenv("SERTOR_GLOVE_PATH")) if os.getenv("SERTOR_GLOVE_PATH") else None`.
      (REQ-002/006, DA-1)
- [ ] Aggiungi campo `glove_path: Path | None = None` letto da `SERTOR_GLOVE_PATH` (REQ-032).
- [ ] Verifica: `Settings` è importabile senza dipendenze esterne; i default sono definiti **solo**
      qui (Principio VIII); `validate_backend()` per provider locali restituisce lista vuota.

### TASK-G03 — Aggiorna `build_embedder` in `composition.py` a 4 rami [P]
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-G01, TASK-G02

Piano di modifica (piano §"Punti", punto 6):
- [ ] Sostituisci la logica attuale di `build_embedder` (riga 82, 2 rami `azure`/else) con un
      match a **4 rami** (`glove` / `hash` / `ollama` / `azure`) con import lazy per ciascun ramo
      (Principio I — nessun import in testa al modulo per i nuovi adapter):
      ```
      provider = settings.embed_provider
      match provider:
          "glove"  -> GloveEmbedder(resolve_glove_file(settings), batch_size=…)
          "hash"   -> HashingEmbedder(batch_size=…)  # + warning REQ-014
          "ollama" -> OllamaEmbedder(...)             # INVARIATO
          "azure"  -> AzureEmbedder(...)              # INVARIATO
          _        -> raise ConfigError(key="SERTOR_EMBED_PROVIDER", …)  # REQ-003
      ```
- [ ] Aggiungi `log_event("embeddings_provider_selected", {"provider": provider})` per i
      provider locali (`glove` e `hash`), dopo la costruzione dell'adapter (DA-6/REQ-042).
      Aggiungilo come evento informativo: `provider` è a cardinalità chiusa (mai testo libero).
- [ ] Per il ramo `hash`: aggiungi `log_event(WARNING, …)` «ricerca NL limitata; configura
      glove/ollama/azure per semantica» (REQ-014, DA-5).
- [ ] Verifica: i rami `ollama` e `azure` restano **invariati** nel corpo (RNF-4/REQ-052);
      `build_store` **non viene toccato** (il default cambia solo nel Settings, non qui).
- [ ] Verifica: `composition.py` non importa direttamente adapter GloVe/Hashing in testa al
      file; gli import lazy avvengono dentro il ramo (Principio I/RNF-2/REQ-053).

---

## Fase 1 — Fondazionale: nuovi adapter (3 task)

> Tutti e tre i task sono **parallelizzabili** `[P]`.
> Prerequisiti comuni: TASK-G01 (errore di dominio), TASK-G02 (Settings con `glove_path`).

### TASK-F01 — Implementa `HashingEmbedder` (`adapters/embeddings/hashing.py`) [P]
**File nuovo**: `src/sertor_core/adapters/embeddings/hashing.py`
→ dipende da: TASK-G02
- [ ] Implementa `HashingEmbedder` che soddisfa la porta `EmbeddingProvider` (structural typing):
      - `name = "hash:512"` (stabile, codifica la dimensione — REQ-012/051)
      - `dim = 512` (costante nota da subito, non lazy)
      - `batch_size: int` da `Settings.embed_batch_size`
      - `embed(texts: list[str]) -> list[list[float]]`
- [ ] Algoritmo char-n-gram (DA-2, contratto `local-providers.md`):
      - Per ogni testo: lowercase; estrai char-n-gram con `n ∈ {3, 4, 5}` con padding di
        confine (padding con spazio ai confini di parola così token corti contribuiscono).
      - Per ogni n-gram: `hashlib.blake2b(ngram.encode("utf-8"), digest_size=8)` → intero
        a 64 bit; **mai** il builtin `hash()` (salted per-processo) — REQ-013/RNF-1.
      - Indice: `h % 512`; segno dal bit successivo `(h >> 8) & 1` (*sign-hashing*,
        riduce collisione sistematica verso il positivo).
      - Accumulo su array di 512 float, poi **L2-norm**. Testo vuoto → 512 zeri. (REQ-011)
- [ ] Solo **stdlib** (`hashlib`, `math`): nessun extra, nessuna rete, nessuna credenziale
      (REQ-010/053).
- [ ] Verifica: `HashingEmbedder` non importa SDK esterni; è importabile senza nessun
      extra opzionale; la dimensione è fissa a 512 sempre.

### TASK-F02 — Implementa `GloveEmbedder` (`adapters/embeddings/glove.py`) [P]
**File nuovo**: `src/sertor_core/adapters/embeddings/glove.py`
→ dipende da: TASK-G01, TASK-G02
- [ ] Implementa `GloveEmbedder` che soddisfa la porta `EmbeddingProvider`:
      - `name = "glove:300"` (stabile, codifica la dimensione, distinto dagli altri — REQ-022)
      - `dim = 300` (costante nota)
      - `batch_size: int` da Settings
      - `embed(texts: list[str]) -> list[list[float]]`
      - Costruttore riceve il path risolto al file `glove.6B.300d.txt`; **non carica il file
        al costruttore** ma **lazy alla prima `embed`** (install≠run — REQ-024, DA-3).
- [ ] Caricamento vocabolario (lazy, `numpy` importato lazy dentro il metodo, non in testa
      al modulo — REQ-024/053): legge `glove.6B.300d.txt` linea per linea, costruisce
      `dict[str, numpy.ndarray]`; failure di parse → `GloveUnavailableError` (REQ-041).
- [ ] Tokenizzazione e aggregazione (DA-3, contratto `local-providers.md`):
      - Lowercase + split su non-alfanumerici.
      - Per ogni token: lookup nel vocabolario; se OOV → split camelCase/snake_case
        (`getUserId`→`get`,`user`,`id`) poi retry dei sotto-token; sotto-token ancora OOV
        → scartati dall'aggregazione (REQ-023).
      - Aggregazione: **media dei vettori in-vocab** poi **L2-norm** (REQ-021).
      - Tutto-OOV / testo vuoto → vettore **zero** (300 zeri) deterministico;
        non fa fallire la chiamata (REQ-023).
- [ ] Emetti `log_event("glove_cache_hit", {"hit": True})` quando il vocabolario è già
      caricato (riuso da run precedente — DA-6).
- [ ] Verifica: `GloveEmbedder` non importa `numpy` in testa al modulo; selezionare
      `SERTOR_EMBED_PROVIDER=hash` non importa `numpy` (RNF-2/REQ-053).

### TASK-F03 — Implementa resolver/acquisizione GloVe (`adapters/embeddings/glove_cache.py`) [P]
**File nuovo**: `src/sertor_core/adapters/embeddings/glove_cache.py`
→ dipende da: TASK-G01, TASK-G02
- [ ] Implementa `glove_cache_dir() -> Path`: directory cache utente condivisa per-macchina,
      **stdlib** (no `platformdirs`) — DA-4/REQ-031:
      - Windows: `%LOCALAPPDATA%\sertor\glove\`
      - macOS/Linux: `$XDG_CACHE_HOME/sertor/glove/` se impostata, altrimenti
        `~/.cache/sertor/glove/`
- [ ] Implementa `resolve_glove_file(settings: Settings) -> Path` — priorità di risoluzione
      (REQ-032/035/040):
      1. `settings.glove_path` se impostato ed esistente → usa quel file, nessun download.
      2. File `glove.6B.300d.txt` in `glove_cache_dir()` esistente → usa la cache.
      3. Durante l'indicizzazione: chiama `ensure_glove(settings)` (download).
      4. File assente, no path, no rete → solleva `GloveUnavailableError` (REQ-040).
      Emette `log_event("glove_cache_hit", {"hit": True/False})` in base alla risoluzione (DA-6).
- [ ] Implementa `ensure_glove(settings: Settings) -> Path` — acquisizione on-demand (REQ-030):
      - Emette `log_event(WARNING, "glove_download", {"size_mb": 822, "source_host": "nlp.stanford.edu"})`
        una-tantum prima del download (REQ-033, DA-5).
      - Scarica `https://nlp.stanford.edu/data/glove.6B.zip` via `urllib.request` (stdlib,
        rispetta `HTTP_PROXY`/`HTTPS_PROXY`) su file temporaneo nella dir cache.
      - Estrae **solo** `glove.6B.300d.txt` con `zipfile` (stdlib) nella dir cache.
      - Replace atomico con `os.replace` (concorrenza sicura senza lock esplicito — DA-4).
      - Errore di rete o HTTP → solleva `GloveUnavailableError` con il motivo (REQ-041).
      - Errore di parse/formato inatteso → `GloveUnavailableError` (REQ-041).
- [ ] Verifica: solo **stdlib** (`urllib`, `zipfile`, `os`, `pathlib`) — RNF-2.
- [ ] Verifica: `ensure_glove` non viene mai chiamato da `search`/`install` (solo da `index`) —
      REQ-034; questa distinzione è garantita dal fatto che `resolve_glove_file` viene chiamata
      solo dentro `build_embedder` che è invocato dal percorso di indicizzazione.

---

## Fase 2 — US1+US2: composition a 4 rami, test adapter, migrazione test core (6 task)

> US1 = indicizzo e cerco senza alcun provider configurato (default GloVe).
> US2 = indicizzo e cerco airgapped/offline senza download (provider `hash`).
> Prerequisiti: Fase 0 e Fase 1 complete.

### TASK-A01 — Test unitari `HashingEmbedder` (determinismo, OOV, testo vuoto) [P]
**File nuovo**: `tests/unit/test_hashing_embedder.py`
→ dipende da: TASK-F01
- [ ] Test di base: `embed(["x"])` produce lista di 1 vettore di lunghezza 512; tutti float.
- [ ] Test determinismo stesso-run: `embed(["hello world"]) == embed(["hello world"])`.
- [ ] Test **determinismo cross-`PYTHONHASHSEED`** (subprocess): lancia due subprocess Python
      con `PYTHONHASHSEED=0` e `PYTHONHASHSEED=42` che stampano `embed(["test text"])` come JSON;
      verifica che i due output siano identici (REQ-013, SC-003).
      > Usare `subprocess.run([sys.executable, "-c", "..."], env={…})` senza download reali.
- [ ] Test OOV / identificatori di codice: `embed(["build_indexer"])` produce vettore **non nullo**
      (i char-n-gram garantiscono segnale anche per token fuori vocabolario — REQ-011, US2-AC2).
- [ ] Test testo vuoto: `embed([""])` → vettore di 512 zeri; nessuna eccezione (REQ-011 edge).
- [ ] Test batch: `embed(["a", "b"])` → 2 vettori; ordine preservato.
- [ ] Tutti i test: no rete, no cloud (`not cloud`), solo stdlib.

### TASK-A02 — Test unitari `GloveEmbedder` (fixture mini-vocabolario, OOV, caricamento lazy) [P]
**File nuovo**: `tests/unit/test_glove_embedder.py`
**File fixture**: `tests/fixtures/glove_mini.txt` (mini-file GloVe con 2–3 token e 300 dim)
→ dipende da: TASK-F01, TASK-F02
- [ ] Crea fixture `tests/fixtures/glove_mini.txt`: mini-file GloVe con 3 token
      (es. `hello`, `world`, `code`) e 300 float casuali ma fissi (hardcodati nel file),
      formato `token v1 v2 … v300` per riga. Usato da TUTTI i test GloVe offline —
      **NON scaricare mai il file reale (~822 MB) nei test**.
- [ ] Test base: `GloveEmbedder(path_mini).embed(["hello world"])` → vettore di 300 float;
      media dei due vettori in-vocab, L2-normalizzato.
- [ ] Test **determinismo**: `embed(["hello world"]) == embed(["hello world"])` con stessa fixture
      (REQ-021/RNF-1/SC-003).
- [ ] Test **OOV camelCase**: `embed(["getUserId"])` → split in `get`, `user`, `id`; sotto-token
      in-vocab (se presenti nella fixture) contribuiscono; non solleva eccezione (REQ-023).
- [ ] Test **tutto-OOV**: `embed(["xqzjvbk"])` → vettore zero (300 zeri); nessuna eccezione
      (REQ-023, US3-AC4).
- [ ] Test testo vuoto: `embed([""])` → vettore zero; nessuna eccezione.
- [ ] Test **caricamento lazy**: costruire `GloveEmbedder(path_mini)` non carica il file;
      il caricamento avviene solo alla prima `embed` (verifica con monkeypatch del metodo
      `_load_vocab` che conta le chiamate).
- [ ] Test batch: `embed(["hello", "world"])` → 2 vettori; ordine preservato.
- [ ] Tutti i test: no rete, no cloud; nessun download reale.

### TASK-A03 — Test unitari resolver GloVe (cache, override path, fail-loud) [P]
**File nuovo**: `tests/unit/test_glove_cache.py`
→ dipende da: TASK-F02, TASK-F03
- [ ] Test **override path presente**: `resolve_glove_file` con `Settings(glove_path=path_mini)`
      → restituisce `path_mini` senza chiamare il downloader (monkeypatch `ensure_glove` e
      verifica che non sia chiamato — US3-AC3, REQ-032).
- [ ] Test **cache presente**: con `glove_cache_dir()`/`glove.6B.300d.txt` esistente (tmpdir),
      `resolve_glove_file` restituisce il path dalla cache; downloader non chiamato; emette
      `glove_cache_hit` con `hit=True` (REQ-035, DA-6).
- [ ] Test **file assente, downloader che solleva** (simula no-rete): monkeypatch `ensure_glove`
      per sollevare `GloveUnavailableError`; `resolve_glove_file` propaga l'errore con il
      messaggio azionabile che nomina entrambe le vie d'uscita (REQ-040, SC-005, US4-AC1).
- [ ] Test **download riuscito** (mock `urllib` e `zipfile`): `ensure_glove` con mock del download
      che crea il file nella tmpdir; verifica che il path restituito sia corretto e che
      `os.replace` atomico sia avvenuto (DA-4).
- [ ] Test **emissione evento glove_download**: prima del download, l'evento `glove_download`
      con `size_mb=822` e `source_host` non vuoto è emesso (REQ-033/042, DA-6);
      usa `caplog` o mock di `log_event`.
- [ ] Test **glove_cache_dir() cross-OS**: su Windows stub `os.environ["LOCALAPPDATA"]` e
      verifica path; su posix stub `XDG_CACHE_HOME` e verifica.
- [ ] Tutti i test: no rete reale; `urllib.request.urlretrieve` mockato; no cloud.

### TASK-A04 — Test unitari Settings e composition: default provider, `validate_backend` ri-chiavata [P]
**File**: `tests/unit/test_settings.py`
**File**: `tests/unit/test_settings_runtime.py`
**File**: `tests/unit/test_settings_validate_backend.py`
**File**: `tests/unit/test_composition.py`
→ dipende da: TASK-G02, TASK-G03

Migrazione test core (piano punti 7–11):
- [ ] **`test_settings.py`** (punti 7): sostituisci tutti i riferimenti a `s.backend` e
      `RAG_BACKEND` con `embed_provider`/`SERTOR_EMBED_PROVIDER` e `store_backend` default `local`.
      Rimuovi `test_embed_provider_follows_backend` e `test_store_backend_defaults_to_rag_backend`;
      aggiungi:
      - `Settings()` → `embed_provider == "glove"` (default, REQ-002).
      - `Settings()` → `store_backend == "local"` (default indipendente, REQ-006).
      - `Settings(embed_provider="hash")` → `validate_backend()` → lista vuota (REQ-005).
      - `Settings(embed_provider="glove")` → `validate_backend()` → lista vuota.
      - `Settings(embed_provider="azure")` → `validate_backend()` → 3 campi Azure OpenAI.
      - `Settings(embed_provider="bogus")` → valore non riconosciuto (il composition root
        solleverà `ConfigError`; settings è solo il campo grezzo).
- [ ] **`test_settings_runtime.py`** (punto 8): sostituisci `.env` con `RAG_BACKEND` →
      `SERTOR_EMBED_PROVIDER`; verifica che `RAG_BACKEND` residuo nell'env produca il warning
      `config_rag_backend_ignored` (REQ-007) senza cambiare comportamento.
- [ ] **`test_settings_validate_backend.py`** (punto 9): `Settings(backend=…)` →
      `Settings(embed_provider=…)`.
- [ ] **`test_composition.py`** (punto 10): `RAG_BACKEND` e `backend=azure` → `embed_provider`;
      aggiorna il commento «local store despite backend=azure» → «despite embed_provider=azure».
      Aggiungi test per i due nuovi rami `glove` e `hash` in `build_embedder`.
- [ ] Verifica: tutti i test modificati continuano a passare; nessun test nuovo dipende da rete
      o cloud (usa `FakeEmbedder` per mock dove serve).

### TASK-A05 — Migrazione test CLI/integration che referenziano `RAG_BACKEND`/`backend` [P]
**File**: `tests/unit/test_cli_index.py`
**File**: `tests/unit/test_cli_graph_eval.py`
**File**: `tests/unit/test_cli_eval_compare.py`
**File**: `tests/unit/test_cli_eval.py`
**File**: `tests/integration/test_graph_eval_gate.py`
**File**: `tests/integration/test_eval_gate.py`
**File**: `tests/integration/test_local_only.py`
**File**: `tests/unit/test_baseline_engine.py`
**File**: `tests/unit/test_mcp_server.py`
→ dipende da: TASK-G02, TASK-G03

Migrazione test core (piano punti 11–16):
- [ ] **`test_cli_index.py`** (punto 11, riga 23 e 108): `Settings(backend="azure",…)` →
      `Settings(embed_provider="azure",…)`.
- [ ] **`test_cli_graph_eval.py`** (punto 12, riga 67): rimuovi kwarg `backend="local"` o
      sostituisci con `embed_provider="hash"` se il test richiede un provider deterministico.
- [ ] **`test_cli_eval_compare.py`** (punto 12, riga 43): stessa migrazione.
- [ ] **`test_cli_eval.py`** (punto 12, riga 59): stessa migrazione.
- [ ] **`test_graph_eval_gate.py`** (punto 12, riga 84): stessa migrazione.
- [ ] **`test_eval_gate.py`** (punto 12, riga 47): stessa migrazione.
- [ ] **`test_local_only.py`** (punto 13, righe 3/16/28): `RAG_BACKEND=local` →
      `SERTOR_EMBED_PROVIDER=ollama` (il test verifica che la composizione locale instanzi
      Ollama+Chroma).
- [ ] **`test_baseline_engine.py`** (punto 14, riga 110): `RAG_BACKEND=local` →
      `SERTOR_EMBED_PROVIDER=ollama`.
- [ ] **`test_mcp_server.py`** (punto 15, riga 44): aggiorna il commento che cita `RAG_BACKEND`.
- [ ] **`test_logging.py`** (punto 16): **NON toccare** — usa `backend="local"` come campo di
      `log_event`, non come `Settings.backend`; non è correlato.
- [ ] Verifica: `uv run pytest -m "not cloud" tests/unit/test_cli_index.py tests/unit/test_cli_graph_eval.py tests/unit/test_cli_eval.py tests/integration/test_local_only.py` → tutti verdi.

### TASK-A06 — Test unitari: Settings default, warning `RAG_BACKEND`, composizione a 4 rami [P]
**File nuovo**: `tests/unit/test_embedder_local_composition.py`
→ dipende da: TASK-G02, TASK-G03, TASK-F01, TASK-F02
- [ ] Test **default provider**: con `Settings()` (nessuna env impostata), `build_embedder`
      costruisce un `GloveEmbedder` (ramo `glove` — REQ-002/SC-001).
      Usa monkeypatch per evitare il caricamento del file vocabolario (non indicizzare davvero).
- [ ] Test **provider `hash`**: `Settings(embed_provider="hash")` → `build_embedder` costruisce
      un `HashingEmbedder`; emette warning «NL limitata» (verifica con `caplog` — REQ-014).
- [ ] Test **provider `ollama`** (invarianza): `Settings(embed_provider="ollama")` →
      `build_embedder` costruisce un `OllamaEmbedder`; nessun import di `GloveEmbedder`
      né di `numpy` (RNF-4/REQ-052).
- [ ] Test **provider `azure`** (invarianza): `Settings(embed_provider="azure")` →
      `build_embedder` costruisce un `AzureEmbedder` (RNF-4/REQ-052).
- [ ] Test **valore non riconosciuto**: `Settings(embed_provider="bogus")` →
      `build_embedder` solleva `ConfigError(key="SERTOR_EMBED_PROVIDER")` che nomina i valori
      ammessi (REQ-003, SC-005).
- [ ] Test **evento `embeddings_provider_selected`**: rami `glove` e `hash` emettono l'evento
      con campo `provider` a valore chiuso (verifica con `caplog`/mock `log_event` — REQ-042).
      I rami `ollama` e `azure` **non** emettono questo evento (invarianza).
- [ ] Test **warning `RAG_BACKEND` residuo**: con `RAG_BACKEND=azure` in env e
      `SERTOR_EMBED_PROVIDER=glove` → `Settings.load()` emette `config_rag_backend_ignored`
      e instanzia comunque `GloveEmbedder` (comportamento non cambiato — REQ-007, DA-1).
- [ ] Test **store ortogonale**: `SERTOR_EMBED_PROVIDER=glove` + `SERTOR_STORE_BACKEND=azure` →
      `Settings` ha `embed_provider="glove"` e `store_backend="azure"` (REQ-006).
- [ ] Tutti i test: no rete, no cloud; mock di `ensure_glove` dove serve.

---

## Fase 3 — US3: acquisizione GloVe on-demand e semantica locale (4 task)

> US3 = semantica NL locale di default con acquisizione on-demand.
> Prerequisiti: Fase 0, Fase 1 e Fase 2 complete.

### TASK-B01 — Test unitari GloVe: avviso download, cache hit, override airgapped [P]
**File nuovo**: `tests/unit/test_glove_acquisition.py`
→ dipende da: TASK-F02, TASK-F03, TASK-A02, TASK-A03
- [ ] Test **prima indicizzazione — cache assente**: `resolve_glove_file` chiama `ensure_glove`
      quando né il path esplicito né la cache esistono; verifica con monkeypatch di `ensure_glove`
      che sia chiamato esattamente una volta (REQ-030, US3-AC1).
- [ ] Test **seconda indicizzazione — cache presente**: dopo il primo download (simulato creando
      il file in tmpdir), `resolve_glove_file` restituisce il file dalla cache senza chiamare
      `ensure_glove` (REQ-035, US3-AC2); evento `glove_cache_hit(hit=True)` emesso.
- [ ] Test **override airgapped**: `SERTOR_GLOVE_PATH=path_mini` →
      `resolve_glove_file` restituisce `path_mini` senza chiamare `ensure_glove` (REQ-032,
      US3-AC3).
- [ ] Test **avviso dimensione prima del download**: prima che `ensure_glove` inizi a scaricare,
      l'evento `glove_download` con `size_mb≈822` è emesso (REQ-033/042).
- [ ] Test **nessun download a `search`/`install`**: `resolve_glove_file` chiamata con
      `in_index_path=False` (o equivalente flag che blocca il download) solleva
      `GloveUnavailableError` invece di scaricare (REQ-034, US3-AC5).
      > Nota implementativa: il confine "solo durante l'indicizzazione" può essere implementato
      > passando un flag booleano `allow_download: bool = False` a `resolve_glove_file`;
      > `build_embedder` per i percorsi di indicizzazione lo passa `True`.
- [ ] Test **errore rete → `GloveUnavailableError` azionabile**: `ensure_glove` con mock che
      solleva `urllib.error.URLError`; l'errore propagato nomina entrambe le vie d'uscita
      (REQ-040/041, US4-AC2).
- [ ] Test **file corrotto → `GloveUnavailableError`**: mock che produce un file GloVe con
      formato inatteso; `GloveEmbedder._load_vocab` solleva `GloveUnavailableError` (REQ-041).
- [ ] Tutti i test: no rete reale; mock completo di `urllib.request` e `zipfile`.

### TASK-B02 — Test di fumo GloVe con fixture locale (offline, non cloud) [P]
**File nuovo**: `tests/unit/test_glove_embedding_offline.py`
→ dipende da: TASK-A02, TASK-B01
- [ ] Test **media+norm deterministica**: con vocabolario fixture mini (TASK-A02), calcola
      manualmente la media attesa dei vettori di `hello world` e verifica che
      `GloveEmbedder(path_mini).embed(["hello world"])` coincida (entro fp-epsilon).
- [ ] Test **OOV split camelCase con fixture**: con token `worldCode` (split: `world` in-vocab,
      `code` in-vocab) → vettore non nullo, media dei due sotto-token.
- [ ] Test **tutto-OOV**: token non presente nella fixture e non splittabile →
      vettore di 300 zeri (REQ-023/SC-010).
- [ ] Test **batch deterministico**: `embed(["hello", "world"])` due volte → risultati identici
      (RNF-1/SC-003).
- [ ] Test **`numpy` non importato se non si usa GloVe**: importa il modulo `hashing` in un
      processo separato (subprocess) e verifica che `numpy` non sia in `sys.modules`
      (RNF-2/REQ-053).
- [ ] Tutti i test: no rete, no cloud; usa solo la fixture mini.

### TASK-B03 — Aggiunta flag `allow_download` a `resolve_glove_file` e wiring composition [P]
**File**: `src/sertor_core/adapters/embeddings/glove_cache.py`
**File**: `src/sertor_core/composition.py`
→ dipende da: TASK-F03, TASK-G03
- [ ] Aggiungi parametro `allow_download: bool = False` a `resolve_glove_file(settings, …)`:
      se `False` e il file non è in cache/path esplicito → solleva `GloveUnavailableError`
      invece di chiamare `ensure_glove` (REQ-034, US3-AC5 — acquisizione solo in index).
- [ ] In `composition.py`, ramo `glove` di `build_embedder`: passa `allow_download=True`
      solo quando il contesto è quello di indicizzazione (l'unico che chiama `build_indexer`).
      Per i percorsi di query/search: `allow_download=False` (cache deve essere già presente).
      > Il modo più semplice: `build_indexer` chiama `resolve_glove_file(settings, allow_download=True)`;
      > `build_facade`/`build_engine` passano `allow_download=False`.
- [ ] Verifica: `uv run pytest -m "not cloud" tests/unit/test_glove_acquisition.py` → verde.

### TASK-B04 — Test integrazione composizione con provider `glove` su fixture (not cloud) [P]
**File nuovo**: `tests/integration/test_local_glove.py`
→ dipende da: TASK-A01, TASK-A02, TASK-A03, TASK-B01, TASK-B02, TASK-B03
- [ ] Test `@integration` `not cloud`: costruisce `build_embedder` con
      `Settings(embed_provider="glove", glove_path=path_mini)` (override path, no download)
      → restituisce un `GloveEmbedder`; chiama `embed(["hello world"])` → vettore valido
      (verifica dimensione 300 e L2-norm ≈ 1.0 entro epsilon).
- [ ] Test `@integration` `not cloud`: costruisce `build_embedder` con
      `Settings(embed_provider="hash")` → restituisce `HashingEmbedder`; chiama
      `embed(["hello"])` → vettore di dim 512, norma ≈ 1.0.
- [ ] Test **namespacing collezione**: `collection_name(corpus="test", embedder=glove_adapter)`
      contiene `"glove"` nel nome; `collection_name(corpus="test", embedder=hash_adapter)`
      contiene `"hash"` — provider diversi producono nomi distinti (REQ-051, RNF-6 di R-6).
- [ ] Tutti i test: no rete reale; `path_mini` dalla fixture TASK-A02.

---

## Fase 4 — US4: fail-loud e osservabilità (3 task)

> US4 = fallimento rumoroso e azionabile, mai degrado silenzioso.
> Prerequisiti: Fase 0, Fase 1, Fase 2 complete (Fase 3 consigliata ma non strettamente bloccante).

### TASK-C01 — Test unitari fail-loud: `GloveUnavailableError`, `ConfigError` valore non valido [P]
**File nuovo**: `tests/unit/test_fail_loud.py`
→ dipende da: TASK-G01, TASK-G03, TASK-F03
- [ ] Test **`GloveUnavailableError` azionabile**: cattura l'eccezione e verifica che il messaggio
      contenga `SERTOR_GLOVE_PATH` **e** `SERTOR_EMBED_PROVIDER=hash` (entrambe le vie — REQ-040,
      US4-AC1).
- [ ] Test **nessun fallback silenzioso**: `resolve_glove_file` con file assente + `ensure_glove`
      che simula no-rete → `GloveUnavailableError` propagato; il composition root non cattura e
      non ripiega su un altro provider (US4-AC2).
- [ ] Test **`ConfigError` su valore non valido**: `build_embedder` con
      `Settings(embed_provider="typo")` → `ConfigError` con `key="SERTOR_EMBED_PROVIDER"` e
      messaggio che nomina i valori ammessi (`glove`, `hash`, `ollama`, `azure`) — REQ-003,
      US4-AC3.
- [ ] Test **evento osservabilità strutturato**: per i provider locali, `build_embedder` emette
      `embeddings_provider_selected` con campo `provider` a valore chiuso; verifica con mock
      `log_event` che nessun segreto, path con `~`/username, né testo di query sia incluso
      (REQ-042, Principio IX, RNF-3/DA-6).
- [ ] Test **osservabilità `glove_download`**: i campi emessi sono `size_mb` e `source_host`
      (non l'URL completo, non il path locale — RNF-3).
- [ ] Tutti i test: no rete; no cloud.

### TASK-C02 — Test unitari: avviso NL limitata per provider `hash` [P]
**File**: `tests/unit/test_embedder_local_composition.py` (aggiungi, o nuovo file)
→ dipende da: TASK-G03, TASK-F01
- [ ] Verifica che, quando `build_embedder` costruisce un `HashingEmbedder`, venga emesso
      il warning `log_event(WARNING, …)` con il messaggio che invita a configurare
      `glove`/`ollama`/`azure` per semantica NL (REQ-014, US2-AC4).
- [ ] Verifica che il warning sia emesso **una volta** per costruzione, non per ogni chunk
      (non spam per batch — comportamento from `build_embedder`).
- [ ] Verifica che i provider `glove`, `ollama`, `azure` **non** emettano questo warning.
- [ ] No rete, no cloud.

### TASK-C03 — Verifica isolamento dipendenze e importabilità senza extra [P]
**File nuovo**: `tests/unit/test_dependency_isolation.py`
→ dipende da: TASK-F01, TASK-F02
- [ ] Test **lessicale importabile senza `numpy`**: subprocess con env che non ha `numpy` nel
      path (o con monkeypatch che rende `numpy` non importabile) + import di
      `sertor_core.adapters.embeddings.hashing` → nessuna eccezione (REQ-010/053).
- [ ] Test **provider non-GloVe non importa `numpy`**: subprocess con
      `SERTOR_EMBED_PROVIDER=hash`, import di `sertor_core` e verifica che `numpy` non sia
      in `sys.modules` dopo `Settings.load()` e `build_embedder` (RNF-2/REQ-053).
- [ ] Test **provider non-GloVe non scarica file**: con `SERTOR_EMBED_PROVIDER=hash`,
      `build_embedder` non chiama mai `ensure_glove` né `resolve_glove_file`
      (verifica con monkeypatch — REQ-024).
- [ ] No rete, no cloud.

---

## Fase 5 — US5: corollario installabile (4 task)

> US5 = la capacità è installabile su un ospite (template `.env`, doc, nota di migrazione).
> Prerequisiti: Fase 0 completata (le manopole devono esistere in Settings prima di documentarle).
> Attenzione: il **debito di completamento P2** (allineamento wizard/profilo installer
> `rag_profile.py`/`configure.py`/`__main__.py`, punti 19–23 del plan) è tracciato qui come
> TASK-D04 (Should). La feature non è "done" finché i template (TASK-D01) e la doc (TASK-D02)
> non sono completati.

### TASK-D01 — Aggiorna template `.env` installer (rimuovi `RAG_BACKEND`, aggiungi nuove manopole) [P]
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.local.tmpl`
**File**: `packages/sertor/src/sertor_installer/assets/rag/env.azure.tmpl`
→ dipende da: TASK-G02 (le manopole devono essere definite in Settings)

Migrazione installer (piano punti 17–18):
- [ ] **`env.local.tmpl`** (punto 17, riga 3): rimuovi `RAG_BACKEND=local`; aggiungi:
      ```
      # Embedding provider: glove (default), hash (airgapped/CI), ollama, azure
      SERTOR_EMBED_PROVIDER=glove
      # Optional: path to a local glove.6B.300d.txt file (airgapped/offline).
      # SERTOR_GLOVE_PATH=
      # Vector-store backend: local (default), azure
      # SERTOR_STORE_BACKEND=local
      ```
      (REQ-060, US5-AC1)
- [ ] **`env.azure.tmpl`** (punto 18, riga 3): rimuovi `RAG_BACKEND=azure`; aggiungi:
      ```
      SERTOR_EMBED_PROVIDER=azure
      # SERTOR_GLOVE_PATH=
      ```
      e mantieni `SERTOR_STORE_BACKEND=local` (il default locale è ok anche con embed azure).
- [ ] Verifica: nessun segreto nei template; nessuna riga `RAG_BACKEND` residua in nessuno
      dei due file.

### TASK-D02 — Aggiorna documentazione utente (4 provider, nuovo default, nota di migrazione) [P]
**File**: `docs/install.md`
**File**: `packages/sertor/docs/install.md`
**File**: `README.md` (sezione che cita `RAG_BACKEND`)
**File**: `.env.example` (root, se esiste e cita `RAG_BACKEND`)
→ dipende da: TASK-D01

Migrazione documentazione (piano punto 25, REQ-061):
- [ ] In ogni file di documentazione utente:
      - Descrivi i **4 provider** di embeddings: `glove` (default, semantica NL locale, download
        822 MB una-tantum per-macchina), `hash` (airgapped/CI, zero-download, lessicale), `ollama`
        (modello locale), `azure` (cloud, credenziali richieste).
      - Descrivi il **nuovo default** (`SERTOR_EMBED_PROVIDER=glove`) e l'**override airgapped**
        (`SERTOR_GLOVE_PATH=/path/to/glove.6B.300d.txt`).
      - Includi la **nota di migrazione** che copre entrambi i cambi (REQ-061, US5-AC2):
        1. `RAG_BACKEND` è **rimosso** — il provider embeddings si seleziona con
           `SERTOR_EMBED_PROVIDER`, lo store con `SERTOR_STORE_BACKEND`.
        2. Il **default è cambiato**: prima il local-first implicava Ollama; ora è il provider
           a vettori statici (GloVe); Ollama/Azure vanno selezionati esplicitamente.
      - Cita la licenza GloVe (PDDL/pubblico dominio) per l'approvazione enterprise (R-5).
- [ ] Verifica: nessun riferimento a `RAG_BACKEND` nelle sezioni di documentazione aggiornate
      (eccetto nella nota di migrazione, dove si nomina come manopola rimossa).

### TASK-D03 — Migrazione test installer (RAG_BACKEND → SERTOR_EMBED_PROVIDER) [P]
**File**: `packages/sertor/tests/test_install_rag.py`
**File**: `packages/sertor/tests/test_env_merge.py`
**File**: `packages/sertor-install-kit/tests/unit/test_env_merge.py`
**File**: `packages/sertor/tests/test_cli_configure.py`
**File**: `packages/sertor/tests/test_configure_write.py`
**File**: `packages/sertor/tests/test_config_fields.py`
**File**: `packages/sertor/tests/test_configure_check.py`
**File**: `packages/sertor/tests/test_configure_report.py`
→ dipende da: TASK-D01, TASK-G02

Migrazione test installer (piano punto 24):
- [ ] **`test_install_rag.py`** (riga 126–128): aggiorna asserzione su `RAG_BACKEND=local` →
      `SERTOR_EMBED_PROVIDER=glove` nel template installato.
- [ ] **`test_env_merge.py`** (pacchetto `sertor`, righe 10/21/49): aggiorna riferimenti a
      `RAG_BACKEND` → `SERTOR_EMBED_PROVIDER`.
- [ ] **`test_env_merge.py`** (pacchetto `sertor-install-kit`, righe 10/21/49): stessa migrazione.
- [ ] **`test_cli_configure.py`** (righe multiple): `RAG_BACKEND` → `SERTOR_EMBED_PROVIDER`/
      `SERTOR_STORE_BACKEND`; aggiorna la validazione attesa a includere i provider locali.
- [ ] **`test_configure_write.py`** (righe multiple): aggiorna scrittura `RAG_BACKEND` →
      `SERTOR_EMBED_PROVIDER`.
- [ ] **`test_config_fields.py`** (righe 90–107): aggiorna i campi del catalogo `ConfigField` per
      il nuovo schema; i provider locali non generano campi obbligatori mancanti (REQ-005).
- [ ] **`test_configure_check.py`** (riga 33): aggiorna riferimento a `RAG_BACKEND`.
- [ ] **`test_configure_report.py`** (riga 114): aggiorna il campo `backend` del report →
      `provider`/`embed_provider`.
- [ ] Verifica: `uv run pytest -m "not cloud" packages/` → tutti i test installer verdi.

### TASK-D04 — Allineamento wizard installer `rag_profile`/`configure`/`__main__` (P2 Should)
**File**: `packages/sertor/src/sertor_installer/rag_profile.py`
**File**: `packages/sertor/src/sertor_installer/configure.py`
**File**: `packages/sertor/src/sertor_installer/configure_report.py`
**File**: `packages/sertor/src/sertor_installer/install_rag.py`
**File**: `packages/sertor/src/sertor_installer/__main__.py`
→ dipende da: TASK-D01, TASK-D02, TASK-D03

Debito di completamento P2 — allineamento concetto installer `backend` → `provider` (piano punti 19–23):
- [ ] **`rag_profile.py`** (punto 19, righe 19/30–40/57–58/87): allinea il concetto
      `backend=azure|local` a `provider=glove|hash|ollama|azure`; aggiorna `compose_extras`
      (extra `azure` solo per provider `azure`).
- [ ] **`configure.py`** (punto 20, righe 205/222/258/307–311/343): scrive `SERTOR_EMBED_PROVIDER`
      invece di `RAG_BACKEND`; usa `Settings(embed_provider=…)` invece di `Settings(backend=…)`.
- [ ] **`configure_report.py`** (punto 21, righe 27–28/94/127): rinomina/allinea campo `backend`
      del report a `embed_provider` o `provider`.
- [ ] **`install_rag.py`** (punto 22, righe 175/265): seleziona il template da `provider`
      (es. `env.local.tmpl` per provider locali, `env.azure.tmpl` per azure) invece che da
      `backend`.
- [ ] **`__main__.py`** (punto 23, righe 138/244/291/316): rinomina flag `--backend` →
      `--provider`; aggiorna help text e passaggio di `args.backend` → `args.provider`;
      allinea i valori al nuovo schema `glove|hash|ollama|azure`.
- [ ] Verifica: `sertor install rag --provider glove` deposita `SERTOR_EMBED_PROVIDER=glove`
      nel template; `sertor install rag --provider hash` deposita `SERTOR_EMBED_PROVIDER=hash`.
- [ ] Verifica: `uv run pytest -m "not cloud" packages/sertor/tests/` → verde dopo
      aggiornamento TASK-D03.

---

## Fase 6 — Polish e cross-cutting (3 task)

> Dipendono dal completamento di tutte le fasi precedenti.

### TASK-P01 — Verifica finale "nessun riferimento residuo a `RAG_BACKEND`"
→ dipende da: tutti i task delle Fasi 0–5
- [ ] Esegui una ricerca grepping cross-repo per `RAG_BACKEND` in tutto il codice sorgente
      di produzione (escludi `prototype/`, `wiki/`, `specs/` vecchie, `CLAUDE.md`,
      `wiki/log/`, `.sertor/.env`):
      ```
      # file da controllare: src/, packages/, tests/, docs/, .env.example, README.md
      ```
      Verifica che NESSUN riferimento a `RAG_BACKEND` esista fuori dai seguenti contesti ammessi:
      - la nota di migrazione in `docs/install.md` e `packages/sertor/docs/install.md`
        (dove si nomina come manopola rimossa — è intenzionale)
      - eventuali commenti di test che spiegano la migrazione
- [ ] Per ogni riferimento residuo trovato, correggi nel task appropriato delle fasi precedenti
      (o aggiungi un nuovo task di fix se sfuggito).
- [ ] Esegui la stessa verifica per `Settings.backend` (il campo rimosso) nei file di produzione
      `src/` e `packages/`: nessuna occorrenza fuori da `adapters/vectorstores/` e `domain/errors.py`
      (gli omonimi non correlati — `VectorStoreError.backend` — che il plan esclude esplicitamente).

### TASK-P02 — Lint ruff e verifica suite completa non-cloud
→ dipende da: TASK-P01
- [ ] Esegui `uv run ruff check .` su tutti i file nuovi e modificati; correggi ogni errore
      (regole E,F,I,UP,B; line-length 100). Zero errori come pre-condizione al merge.
- [ ] Esegui `uv run pytest -m "not cloud" tests/unit/` → suite unit **completamente verde**
      (inclusi i test IR esistenti, i nuovi adapter, la migrazione `RAG_BACKEND`).
- [ ] Esegui `uv run pytest -m "not cloud" packages/` → suite installer **verde**.
- [ ] Esegui `uv run pytest -m "not cloud" tests/integration/test_local_glove.py` → verde.
- [ ] Verifica **additività** (RNF-4/SC-004): con `SERTOR_EMBED_PROVIDER=ollama` e store local,
      `sertor-rag index .` e `sertor-rag search "test"` hanno comportamento e costo identici
      a prima (nessun warning aggiuntivo, nessun overhead — REQ-052).
- [ ] Verifica **additività** con `SERTOR_EMBED_PROVIDER=azure`: stessa verifica.
- [ ] Verifica: `EvalSuite` e `GraphEvalReport` (feature 066) invariati con le nuove Settings
      (i test IR/graph-eval esistenti continuano a passare senza modifiche).

### TASK-P03 — Aggiornamento dogfood `.sertor/.env` (manuale, documentato)
→ dipende da: TASK-P02
- [ ] Aggiungi una nota in `.claude/CLAUDE.md` o nel log (`wiki/log/2026-06-21.md`) che segnala:
      il file `.sertor/.env` del dogfood (e di ogni ospite esistente che usa `RAG_BACKEND=azure`)
      va migrato **manualmente** sostituendo `RAG_BACKEND=azure` →
      `SERTOR_EMBED_PROVIDER=azure` (il runtime lo segnala via REQ-007 ma non lo corregge).
- [ ] Verifica che `.sertor/.env` **non sia incluso nel commit** (è gitignored e contiene segreti
      — regola workspace).
- [ ] Esegui una verifica finale dell'intero set di test non-cloud:
      `uv run pytest -m "not cloud"` → verde senza regressioni.
- [ ] Verifica manuale smoke del RAG dogfood (se l'ambiente è disponibile):
      - `uv run sertor-rag search "embedding provider"` → risultati non vuoti.
      - `uv run sertor-rag search "GloveEmbedder"` → risulta un chunk relativo ai nuovi adapter.
      - Nessun warning `config_rag_backend_ignored` se il `.sertor/.env` è già migrato.

---

## Grafo delle dipendenze (sintesi)

```
TASK-G01 (GloveUnavailableError) ──┐
TASK-G02 (Settings ristrutturato)  ─┤
TASK-G03 (composition 4 rami)      ─┤
                                    │
                ┌───────────────────┤
                ↓                   │
    [Fase 1 — Fondazionale, parallela]
                │
    TASK-F01 (HashingEmbedder) [P] ─────────────────────────────────┐
    TASK-F02 (GloveEmbedder)   [P] ─────────────────────────────────┤
    TASK-F03 (glove_cache.py)  [P] ─────────────────────────────────┤
                                                                     ↓
               [Fase 2 — US1+US2, parallela dopo Fase 0+1]
                                                                     │
    TASK-A01 (test HashingEmbedder)  [P] ← TASK-F01                 │
    TASK-A02 (test GloveEmbedder)    [P] ← TASK-F02                 │
    TASK-A03 (test glove_cache)      [P] ← TASK-F02, TASK-F03       │
    TASK-A04 (test settings migr.)   [P] ← TASK-G02, TASK-G03       │
    TASK-A05 (test CLI/int migr.)    [P] ← TASK-G02, TASK-G03       │
    TASK-A06 (test composizione)     [P] ← TASK-G02, TASK-G03, F01/F02
                                                                     ↓
               [Fase 3 — US3, dopo Fase 2]
                                                                     │
    TASK-B01 (test acquisizione)   [P] ← TASK-F02, TASK-F03, A02/A03│
    TASK-B02 (test smoke offline)  [P] ← TASK-A02, TASK-B01         │
    TASK-B03 (flag allow_download) [P] ← TASK-F03, TASK-G03         │
    TASK-B04 (test integr. glove)  [P] ← TASK-A01-A03, B01-B03      │
                                                                     ↓
               [Fase 4 — US4, dopo Fase 2 (3 consigliata)]
                                                                     │
    TASK-C01 (test fail-loud)      [P] ← TASK-G01, TASK-G03, F03    │
    TASK-C02 (test avviso hash)    [P] ← TASK-G03, TASK-F01         │
    TASK-C03 (test isol. dipend.)  [P] ← TASK-F01, TASK-F02         │
                                                                     ↓
               [Fase 5 — US5, dopo Fase 0 per D01/D02]
                                                                     │
    TASK-D01 (template .env)       [P] ← TASK-G02                   │
    TASK-D02 (doc + migrazione)    [P] ← TASK-D01                   │
    TASK-D03 (test installer)      [P] ← TASK-D01, TASK-G02         │
    TASK-D04 (wizard installer P2) ─── ← TASK-D01, D02, D03         │
                                                                     ↓
               [Fase 6 — Polish, dopo tutto]

    TASK-P01 (verifica residui)    ← tutte le fasi
    TASK-P02 (lint + suite verde)  ← TASK-P01
    TASK-P03 (dogfood + smoke)     ← TASK-P02
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali |
|----|-------------------------------|-----------------|
| **US1** (indicizzo senza provider configurato — default GloVe) | `Settings()` → `embed_provider=="glove"`; `build_embedder` costruisce `GloveEmbedder`; `validate_backend()` per `glove` → lista vuota; `sertor-rag index .` con `SERTOR_EMBED_PROVIDER=glove` e file in override path → exit 0. | TASK-G02, TASK-G03, TASK-A04, TASK-A06, TASK-B04 |
| **US2** (airgapped/offline, zero download) | `HashingEmbedder` deterministico cross-`PYTHONHASHSEED`; OOV → segnale non nullo; `Settings(embed_provider="hash")` + no rete → index e search ok; no download reale in nessun test. | TASK-A01, TASK-A06, TASK-C02, TASK-C03 |
| **US3** (GloVe on-demand + cache) | Prima indicizzazione: downloader chiamato con mock; avviso `size_mb` emesso; seconda: cache riusata senza download; override path: downloader non chiamato; fixture offline: embed deterministico. | TASK-A02, TASK-A03, TASK-B01, TASK-B02, TASK-B04 |
| **US4** (fail-loud, mai degrado silenzioso) | File assente + no rete → `GloveUnavailableError` con entrambe le vie d'uscita; nessun fallback silenzioso; valore non valido → `ConfigError` con manopola e valori ammessi; eventi osservabilità senza segreti. | TASK-G01, TASK-C01, TASK-A06 |
| **US5** (installabile su ospite) | Template `.env` contiene `SERTOR_EMBED_PROVIDER` e `SERTOR_GLOVE_PATH` commentata; `RAG_BACKEND` assente; doc descrive 4 provider + nota di migrazione; test installer verdi. | TASK-D01, TASK-D02, TASK-D03 |

---

## Parallelizzazione consigliata (MVP P1)

**Sprint 1 (parallelo — zero prerequisiti):**
- Sviluppatore A: TASK-G01 (errore di dominio)
- Sviluppatore B: TASK-G02 (Settings)
- Sviluppatore C: TASK-G03 (composition skeleton a 4 rami — placeholder per i nuovi adapter)

**Sprint 2 (parallelo — dopo Sprint 1):**
- Sviluppatore A: TASK-F01 (HashingEmbedder) + TASK-A01 (relativi test)
- Sviluppatore B: TASK-F02 (GloveEmbedder) + TASK-A02 (relativi test con fixture)
- Sviluppatore C: TASK-F03 (glove_cache.py) + TASK-A03 (relativi test)
- Sviluppatore D: TASK-A04 + TASK-A05 (migrazione test core — si può fare subito dopo G02/G03)

**Sprint 3 (dopo Sprint 2 — US3+US4+D01):**
- Sviluppatore A: TASK-B01 + TASK-B02 + TASK-B03 (acquisizione GloVe, flag allow_download)
- Sviluppatore B: TASK-C01 + TASK-C02 + TASK-C03 (fail-loud + isolamento)
- Sviluppatore C: TASK-A06 (test composizione completa) + TASK-D01 (template .env)
- Sviluppatore D: TASK-D02 (doc) + TASK-D03 (test installer)

**Sprint 4 (dopo Sprint 3 — integrazione e P2):**
- TASK-B04 (test integrazione GloVe con fixture)
- TASK-D04 (debito completamento wizard installer — P2 Should)

**Sprint finale:**
- TASK-P01 → TASK-P02 → TASK-P03 (polish, lint, smoke)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per FEAT-011 epica sertor-core (embedder locale)

Fase SpecKit "tasks" completata per specs/068-embedder-locale.
28 task in 6 fasi operative + polish (Fase0: 3 / Fase1: 3 / Fase2: 6 / Fase3: 4
/ Fase4: 3 / Fase5: 4 / Fase6-Polish: 3). Copertura trasversale RAG_BACKEND:
~40 punti enumerati nel plan distribuiti su TASK-G02, A04, A05, D01-D03, P01.
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/068-embedder-locale/tasks.md` (questo file, nuovo)
