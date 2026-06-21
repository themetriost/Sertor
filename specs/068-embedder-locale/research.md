# Research — Embedder locale (FEAT-011, epica `sertor-core`)

**Branch**: `068-embedder-locale` · **Spec**: [`spec.md`](./spec.md) · **Requisiti**:
`requirements/sertor-core/embedder-locale/requirements.md`

> **Nota di rigenerazione (2026-06-21).** Questo artefatto SOVRASCRIVE una run precedente, basata
> sull'ipotesi che `RAG_BACKEND` restasse il master-switch. La decisione utente è cambiata: **`RAG_BACKEND`
> è rimosso**; il provider di embeddings si sceglie SOLO con la manopola dedicata `SERTOR_EMBED_PROVIDER`
> (default `glove`), lo store con `SERTOR_STORE_BACKEND` (default proprio `local`). Tutte le decisioni
> qui sotto riflettono questa config.

Phase 0: risolve le forche di *come* (la spec lascia esplicitamente al plan: dimensione/algoritmo del
lessicale, aggregazione GloVe, struttura cache, forma evento, sorgente download) e ancora il design al
codice esistente verificato via MCP `sertor-rag`/`Read`.

---

## Stato del codice (ground truth, verificato MCP + Read)

| Punto | File:linea | Stato oggi | Impatto della feature |
|-------|-----------|------------|------------------------|
| Porta `EmbeddingProvider` | `src/sertor_core/domain/ports.py:26` | `name`/`dim`/`batch_size` + `embed(texts)->list[list[float]]` | **INVARIATA** (REQ-050) |
| `build_embedder` | `src/sertor_core/composition.py:63` | 2 rami (`azure`/else→ollama), import lazy, retry, cache opt-in | → **4 rami** `glove`/`hash`/`ollama`/`azure` |
| `build_store` | `src/sertor_core/composition.py:108` | sceglie da `store_backend` | **INVARIATO nel corpo**; cambia solo il default a monte |
| `Settings.backend` | `src/sertor_core/config/settings.py:93` | campo `local|azure`, EMBEDDINGS provider | **RIMOSSO** |
| `Settings.embed_provider` | `settings.py:211` (property) | derivata da `backend` (`azure`→azure, else ollama) | → campo/risoluzione da `SERTOR_EMBED_PROVIDER` (default `glove`) |
| `Settings.store_backend` | `settings.py:95` + `load():277` | default = `backend` (deriva da `RAG_BACKEND`) | → default **indipendente** `local` |
| `Settings.validate_backend` | `settings.py:215` | chiavato su `backend`/`store_backend` | → chiavato su `embed_provider`/`store_backend`; provider locali = `[]` |
| `Settings.load` | `settings.py:238` | legge `RAG_BACKEND` (254), warning `config_no_env_found` (255) | → niente `RAG_BACKEND`; legge `SERTOR_EMBED_PROVIDER`; warning fail-loud su `RAG_BACKEND` residuo (REQ-007) |
| `collection_name` | `composition.py:132` | namespaced `(corpus, _sanitize(embedder.name))` | **INVARIATO**: il nome stabile del provider isola le collezioni (REQ-051) |
| `FakeEmbedder` | `tests/fixtures/mocks.py:24` | mock di test (hash sha256 d'identità) | **DISTINTO** dal provider `hash` di prodotto (segnale char-n-gram) |
| Adapter esistenti | `src/sertor_core/adapters/embeddings/{ollama,azure,cache,_retry}.py` | stile: `name`, `dim` lazy, `embed` batch, `log_event` | I due nuovi adapter ne seguono forma e convenzioni |
| numpy | `pyproject.toml:16` | **già transitiva** da `chromadb` (commento esplicito) | GloVe può usarla senza nuovo extra; resta importata lazy |

**Errori di dominio rilevanti** (`src/sertor_core/domain/errors.py`): `ConfigError(message, key=)` (per
manopola non valida / mancanza azionabile) e `EmbeddingError(message, provider, reason, retriable)` (per
guasti del provider). Si **riusano**; serve un solo nuovo errore di dominio per la diagnostica GloVe
fail-loud azionabile (vedi D5).

---

## Decisione DA-1 — Rimozione di `RAG_BACKEND` (config single-surface)

**Decisione.** `embed_provider` diventa un **campo** di `Settings` risolto SOLO da `SERTOR_EMBED_PROVIDER`
(default `glove`); la property derivata da `backend` (`settings.py:211`) e il campo `backend`
(`settings.py:93`) sono **rimossi**. `store_backend` resta campo con default **`local`** (non più derivato).
In `load()`: si elimina la lettura di `RAG_BACKEND` (254) e si legge `SERTOR_EMBED_PROVIDER` e
`SERTOR_STORE_BACKEND` indipendentemente. La validazione del valore-manopola avviene nel **composition root**
(come `_validated_engine`/`build_capture_adapter`): valore non in `{glove,hash,ollama,azure}` →
`ConfigError(key="SERTOR_EMBED_PROVIDER")` che nomina i valori ammessi (REQ-003).

**Avviso fail-loud (REQ-007, Principio XII).** In `load()`, se `os.getenv("RAG_BACKEND")` è ancora presente,
emette un `log_event(WARNING, "config_rag_backend_ignored", …)`: *non è più onorato*; usa
`SERTOR_EMBED_PROVIDER` per l'embedder e `SERTOR_STORE_BACKEND` per lo store. **Non cambia comportamento di
nascosto**: il valore di `RAG_BACKEND` NON viene letto né mappato — è ignorato e segnalato. Il warning
esistente `config_no_env_found` (255-264, oggi condizionato a `RAG_BACKEND` non impostato) va riformulato: la
condizione su `RAG_BACKEND` si rimuove; il segnale «nessuna `.env` trovata, uso i default» resta valido
ancorandolo a `env_path is None and env_file is not None`.

**Razionale.** Una sola superficie per il provider elimina l'ambiguità del master-switch (che selezionava
provider *e*, di default, store). È la "semplificazione della config" del gate missione (meno frizione). Mai
mappatura silenziosa `RAG_BACKEND=azure → azure`: sarebbe esattamente il degrado nascosto vietato dal
Principio XII.

**Alternative scartate.** (a) *Alias retrocompatibile* (`RAG_BACKEND` ancora letto come fallback): scartato —
riapre la doppia superficie che la feature elimina, e «cambia comportamento di nascosto» (REQ-007 lo vieta).
(b) *Default `embed_provider` = `ollama`* (status quo locale): scartato — il nuovo default deciso è `glove`
(CS-1, REQ-002).

## Decisione DA-2 — Provider lessicale `hash` (char-n-gram, stdlib)

**Decisione.** Nuovo adapter `src/sertor_core/adapters/embeddings/hashing.py` (classe `HashingEmbedder`):
- **Tokenizzazione**: lowercase del testo; estrazione di **char-n-gram** con `n ∈ {3,4,5}` su uno stream
  che include i confini di parola (padding con uno spazio così i token corti contribuiscono). Si usano
  n-gram di **caratteri** (non di parole) proprio perché gli identificatori di codice OOV devono contribuire
  segnale (REQ-011): `build_indexer` e `buildIndexer` condividono molti tri-grammi.
- **Hashing STABILE**: `hashlib.blake2b(ngram.encode("utf-8"), digest_size=8)` → intero; **mai** il builtin
  `hash()` (salted per-processo, romperebbe RNF-1/REQ-013). Da quell'intero: indice `h % dim` e **segno**
  dal bit successivo (`(h >> k) & 1`) → *sign-hashing* (riduce la collisione sistematica verso il positivo).
- **Dimensione fissa**: **512**. Vettore `float` di 512 componenti, accumulo dei contributi n-gram, poi
  **L2-norm** (testo vuoto → vettore zero, trattato dal cosine come 0.0).
- **Nome stabile**: `name = "hash:512"` (codifica la dimensione → `collection_name` isola dagli altri,
  REQ-012/051). `dim = 512` noto da subito (non lazy: costante del provider).
- **Solo stdlib** (`hashlib`, `re`/`str`, `math`): nessun extra, importabile sempre (REQ-010/053).

**Razionale dimensione 512.** Compromesso tra capacità (meno collisioni di 256) e footprint trascurabile
(512 float ≈ 4 KB/chunk); vicina alle dimensioni dei modelli reali → cosine ben condizionato.

**Determinismo cross-macchina/cross-Python.** `blake2b` è deterministico e indipendente da `PYTHONHASHSEED`;
nessuna struttura ordinata per insert-order influenza l'output (accumulo su array a indice fisso).
SC-003/RNF-1 soddisfatti.

**Alternative scartate.** (a) `hash()` builtin: salted (R-4). (b) n-gram di **parole**: gli OOV-identificatori
contribuirebbero meno segnale. (c) dim 256: più collisioni per poco risparmio. (d) idf/pesatura: YAGNI per un
pavimento (Principio III); il segnale è grezzo per definizione (REQ-014 avvisa l'utente).

## Decisione DA-3 — Provider `glove` (vettori statici, default)

**Decisione.** Nuovo adapter `src/sertor_core/adapters/embeddings/glove.py` (classe `GloveEmbedder`):
- **Caricamento**: legge `glove.6B.300d.txt` (formato testo: `token v1 v2 … v300` per riga) in una mappa
  `dict[str, numpy.ndarray]` (numpy già transitiva, importata **lazy** dentro l'adapter — REQ-024/053). Il
  caricamento è **pigro alla prima `embed`** (non al costruttore): costruire il provider non carica ~400 MB
  se non si indicizza.
- **Tokenizzazione**: lowercase; split su non-alfanumerici. Per ogni token: lookup in vocabolario; se **OOV**
  → split su confini camelCase/snake_case (`getUserId`→`get`,`user`,`id`; `build_indexer`→`build`,`indexer`)
  poi retry dei sotto-token; token ancora OOV → **scartato** dall'aggregazione.
- **Aggregazione token→vettore**: **media dei vettori dei token in-vocab** poi **L2-norm** (REQ-021).
- **Tutto-OOV / testo vuoto** (REQ-023): vettore **zero** deterministico (300 zeri); non fa fallire la
  chiamata; a valle il cosine lo tratta come 0.0 (nessun match falso). È il «deterministico senza far fallire».
- **Nome stabile**: `name = "glove:300"`; `dim = 300` (costante nota). Distinto da ollama/azure/hash
  (REQ-022/051).

**Razionale aggregazione = media.** Aggregazione deterministica standard, robusta alla lunghezza del chunk e
normalizzabile. La somma-normalizzata è equivalente dopo L2-norm; la pesatura (idf) è out-of-scope (Could).

**Alternative scartate.** (a) somma senza norm: vettori non comparabili tra chunk di lunghezza diversa.
(b) caricamento al costruttore: violerebbe install≠run e il lazy di REQ-024. (c) tenere il `.zip` montato:
il `.txt` 300d estratto è la struttura interrogabile diretta.

## Decisione DA-4 — Cache & download GloVe

**Decisione.** Nuovo modulo `src/sertor_core/adapters/embeddings/glove_cache.py` (resolver + acquisizione):
- **Directory cache utente condivisa per-macchina** (stile XDG, REQ-031), risolta con **stdlib** (no
  `platformdirs` — Principio III):
  - Windows → `%LOCALAPPDATA%\sertor\glove\`;
  - macOS/Linux → `$XDG_CACHE_HOME/sertor/glove/` se impostata, altrimenti `~/.cache/sertor/glove/`.
- **File atteso**: `glove.6B.300d.txt` nella dir cache.
- **Override** `SERTOR_GLOVE_PATH` (REQ-032): se impostato, si usa quel file e **non si scarica mai**
  (airgapped). Punta direttamente al `.txt` 300d.
- **Risoluzione (priorità)**: 1) `SERTOR_GLOVE_PATH` se esiste → usa; 2) file in cache → usa (REQ-035);
  3) altrimenti, **solo durante l'indicizzazione** → scarica.
- **Download** (REQ-030/033): `glove.6B.zip` dalla **sorgente ufficiale** Stanford NLP
  (`https://nlp.stanford.edu/data/glove.6B.zip`, ~822 MB, PDDL); estrae **solo** `glove.6B.300d.txt` con
  `zipfile` (stdlib) nella dir cache; download via `urllib.request` (stdlib, no nuove dipendenze), rispetta
  le env-proxy standard (`HTTP_PROXY`/`HTTPS_PROXY` lette da `urllib`). **Avviso una-tantum** prima del
  download: `log_event(WARNING, "glove_download", …)` con dimensione (~822 MB) e host sorgente.
- **Concorrenza**: download su file temporaneo nella stessa dir + `os.replace` atomico → due indicizzazioni
  parallele non corrompono il file. Lock esplicito = YAGNI (l'atomic replace basta; il single-writer
  dell'indice è già garantito da `IndexLockedError`).
- **Checksum**: **Could** (rinviato; backlog d'epica) — il fail-loud copre «file corrotto» a valle (parse
  fallito → errore esplicito, D5).

**Razionale stdlib.** `urllib`+`zipfile`+`os.replace` evitano una nuova dipendenza (RNF-2) e mantengono il
core importabile senza nulla da scaricare (SC-009).

**Alternative scartate.** (a) `platformdirs`: nuova dipendenza per ~10 righe di risoluzione path. (b)
`requests`: non dipendenza; `urllib` basta. (c) scaricare al primo `search`/`install`: violerebbe REQ-034
(acquisizione legata alla sola indicizzazione).

## Decisione DA-5 — Fail-loud (Principio XII)

**Decisione.** Nuovo errore di dominio `GloveUnavailableError(SertorError)` in `errors.py`, con messaggio
**azionabile** che nomina **entrambe** le vie d'uscita:
- *imposta `SERTOR_GLOVE_PATH` a un file `glove.6B.300d.txt` locale*, **oppure**
- *seleziona il provider lessicale con `SERTOR_EMBED_PROVIDER=hash`*.

Sollevato quando: GloVe richiesto, file assente dalla cache, `SERTOR_GLOVE_PATH` non impostato, e download
non possibile/fallito (rete assente o errore HTTP) — **niente degrado silenzioso** verso `hash` (REQ-040,
SC-005). Un errore di **caricamento/parse** del file (corrotto, formato inatteso) è esposto esplicitamente
con lo stesso errore (REQ-041): mai fallback nascosto. **Mai** ripiego automatico su un altro provider: la
selezione è una decisione esplicita dell'utente.

**Avvisi (non errori):**
- Download in corso (~822 MB): `log_event(WARNING, "glove_download", …)` una-tantum (REQ-033).
- Provider `hash` attivo: `log_event(WARNING, …)` "ricerca NL limitata; configura glove/ollama/azure per
  semantica" (REQ-014). Emesso quando il provider lessicale è quello costruito (in `build_embedder`, ramo
  `hash`), così compare a ogni run con il pavimento attivo senza spammare per-chunk.

**Razionale.** Errore di dominio dedicato (non `ConfigError` generico): la causa non è un valore di config
errato ma un *artefatto dati mancante con due rimedi distinti*. Conforme Principio IV (errore ricco di
contesto) e XII (fail-loud, mai sopprimere).

## Decisione DA-6 — Osservabilità (metrics-only)

**Decisione.** Eventi `log_event` coerenti con gli esistenti (`embeddings`, `embeddings_error`),
**metrics-only** (REQ-042, Principio IX/RNF-3 — nessun segreto, nessun path sensibile, nessun testo di query):
- `embeddings_provider_selected` con `provider` (∈ valori chiusi) — in `build_embedder` quando si costruisce
  un provider locale (campo a cardinalità chiusa, non un path);
- `glove_download` con `size_mb` (~822) e `source_host` (host della sorgente, non l'URL completo) — all'avvio
  del download;
- `glove_cache_hit` con esito booleano — quando si riusa il file (cache o override).

Il path della cache **non** entra nell'evento (può contenere lo username in `~`): si registra solo l'esito.

**Razionale.** Gemelli degli eventi `embeddings`/`embeddings_cache` già emessi; la redazione segreti è già
garantita dal logging strutturato. Niente nuovi handler (riusano lo stream `sertor_core` → persistenza/OTel
via `enable_observability`).

## Decisione DA-7 — `validate_backend` ri-chiavata

**Decisione.** `validate_backend` (il **nome del metodo resta** per non rompere i consumatori —
`configure.py`/`config_fields.py` dell'installer lo chiamano) verifica:
- credenziali **Azure OpenAI** (`AZURE_OPENAI_ENDPOINT/_API_KEY/_EMBED_DEPLOYMENT`) **quando**
  `embed_provider == "azure"` (non più `backend == "azure"`);
- credenziali **Azure Search** (`AZURE_SEARCH_ENDPOINT/_API_KEY`) **quando** `store_backend == "azure"`
  (invariato);
- provider locali (`glove`/`hash`) e `ollama` → **nessun campo richiesto** → lista vuota → **mai blocco**
  (REQ-005, SC-001). Ollama oggi non è validato (default validi) e resta così.

**Razionale.** Sposta la chiave da `backend` a `embed_provider` senza cambiare la *forma* dell'output (lista
di nomi-env mancanti): l'installer consuma solo l'esito, non la logica (Principio VIII).

## Decisione DA-8 — Wiring eval/CI via vehicle

**Decisione.** Nessun nuovo seam: `build_embedder`/`build_engine`/`build_eval_runner` già costruiscono il
provider dalla config; il percorso eval/CI ottiene `glove`/`hash` impostando `SERTOR_EMBED_PROVIDER` e
chiamando le factory esistenti (REQ-062, Principio XI). Gli adapter non si importano fuori dai test. La CI
vera è FEAT-003 (`debito-tecnico`), fuori ambito: qui si consegna il **determinismo offline** che la abilita.

---

## Corollario installabile (REQ-060/061) — superficie installer

**Punto delicato dall'ancoraggio.** L'installer `sertor install rag` ha un **proprio** concetto
`backend = azure|local` (`rag_profile.py:19,57`; `configure.py:205`; `install_rag.py:175`) che:
1. seleziona il template `.env` (`env.{backend}.tmpl`) — entrambi scrivono `RAG_BACKEND=...`;
2. compone gli extra `uv add` (`compose_extras`: `azure` solo su backend azure);
3. il wizard `configure` scrive `RAG_BACKEND`/`SERTOR_STORE_BACKEND` e usa `Settings(backend=…)` per la
   validazione.

Questo concetto installer-side è **legato a `RAG_BACKEND`** ed è la superficie host-facing più ampia.
**Decisione di scope (vincolo «feature completa solo se installabile»):**
- **In ambito (Must per la coerenza della rimozione):** i **template `.env`** (`env.local.tmpl`/
  `env.azure.tmpl`) NON devono più contenere `RAG_BACKEND`. Si introducono la riga `SERTOR_EMBED_PROVIDER=...`
  e il commento `# SERTOR_GLOVE_PATH=...` (REQ-060). Il template del **nuovo default** espone
  `SERTOR_EMBED_PROVIDER=glove`. La **documentazione utente** (`docs/install.md`,
  `packages/sertor/docs/install.md`) descrive i 4 provider, il nuovo default e la **nota di migrazione** che
  copre SIA il cambio di default SIA la rimozione di `RAG_BACKEND` (REQ-061).
- **Refactoring del concetto installer `backend`** (`rag_profile`/`configure`/`__main__` flag `--backend`):
  va **allineato** alla nuova config — il flag installer seleziona il provider di embeddings
  (`glove|hash|ollama|azure`), non più scrive `RAG_BACKEND`. **È il pezzo più grande.** Si traccia come
  **debito di completamento P2** del corollario installabile (gruppo G Should): il **valore minimo**
  (provider locali nel core + determinismo offline) è P1 e non dipende da esso; ma la feature **non è "done"**
  finché l'installer non depone le manopole nuove. Resta dentro questa feature come *Should* (completamento,
  non capacità nuova). Tracciato anche in `requirements/sertor-core/epic.md` (FEAT-011).

**Test installer impattati** (cambiano insieme ai template): `test_install_rag.py:128`, `test_env_merge.py`
(× 2: `packages/sertor` e `packages/sertor-install-kit`), `test_cli_configure.py`, `test_configure_write.py`,
`test_config_fields.py`. Sono parte del cambiamento trasversale, enumerati nel plan.

---

## Estensioni (tracciamento, non in questa feature)

Già nella MoSCoW dei requisiti (§9) e nel backlog d'epica (`requirements/sertor-core/epic.md`):
- dimensione GloVe configurabile oltre 300d (Could);
- verifica d'integrità (checksum) del file scaricato (Could);
- helper CLI esplicito di pre-download (Could);
- la **CI vera** è FEAT-003 dell'epica `debito-tecnico` (Won't qui).

Nessun rinvio reale vive solo dentro `specs/`.
