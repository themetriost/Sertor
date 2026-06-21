# Data Model — Embedder locale (FEAT-011)

**Branch**: `068-embedder-locale` · Phase 1.

> **Rigenerato (2026-06-21)** sulla config decisa: **`RAG_BACKEND` rimosso**; `SERTOR_EMBED_PROVIDER`
> (default `glove`) unica superficie del provider; `SERTOR_STORE_BACKEND` (default `local`) per lo store.

La feature è **additiva** e **non introduce entità di dominio nuove** (nessun nuovo `dataclass` in
`domain/entities.py`): aggiunge **due adapter** dietro la porta `EmbeddingProvider` esistente, **una eccezione
di dominio**, una **ristrutturazione di campi** in `Settings`, ed **eventi di osservabilità**. La porta, i
servizi e gli engine **non cambiano** (REQ-050).

---

## 1. Configurazione — `Settings` (`src/sertor_core/config/settings.py`)

### Campi RIMOSSI
| Campo / membro | Oggi | Azione |
|----------------|------|--------|
| `backend: str = "local"` (riga 93) | provider embeddings `local|azure` | **RIMOSSO** |
| `embed_provider` (property, riga 211) | derivata da `backend` | **RIMOSSA** come property → diventa campo |
| lettura `RAG_BACKEND` in `load()` (riga 254) | master-switch | **RIMOSSA** |

### Campi NUOVI / MODIFICATI
| Campo | Tipo / default | Env | Note |
|-------|----------------|-----|------|
| `embed_provider` | `str = "glove"` | `SERTOR_EMBED_PROVIDER` | **campo** (non più property). Valori: `glove`/`hash`/`ollama`/`azure`. Validato nel composition root (REQ-001/002) |
| `store_backend` | `str = "local"` | `SERTOR_STORE_BACKEND` | default **indipendente** (non più derivato da `backend`) (REQ-006) |
| `glove_path` | `Path | None = None` | `SERTOR_GLOVE_PATH` | override del file `glove.6B.300d.txt` (airgapped, REQ-032). `None` = usa cache/scarica |

I campi Ollama/Azure (`ollama_host`, `ollama_embed_model`, `azure_openai_*`, `azure_search_*`) **restano
invariati**.

### `validate_backend()` — ri-chiavata (DA-7, REQ-005)
```text
missing = []
if embed_provider == "azure":
    richiede AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBED_DEPLOYMENT
if store_backend == "azure":
    richiede AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY
# embed_provider ∈ {glove, hash, ollama} → nessun campo (mai blocco)
return missing
```

### `load()` — diff comportamentale
- legge `SERTOR_EMBED_PROVIDER` (default `glove`) e `SERTOR_STORE_BACKEND` (default `local`) **in modo
  indipendente**;
- legge `SERTOR_GLOVE_PATH` → `glove_path`;
- **se `RAG_BACKEND` è presente** in env → `log_event(WARNING, "config_rag_backend_ignored", …)` che nomina
  `SERTOR_EMBED_PROVIDER`/`SERTOR_STORE_BACKEND` (REQ-007); il valore **non** è letto né mappato;
- il warning `config_no_env_found` perde la condizione `RAG_BACKEND is None` (resta su `env_path is None`).

---

## 2. Adapter `HashingEmbedder` (`adapters/embeddings/hashing.py`) — NUOVO

| Membro | Valore | Note |
|--------|--------|------|
| `name` | `"hash:512"` | codifica la dimensione (REQ-012) → isola la collezione |
| `dim` | `512` | costante nota da subito |
| `batch_size` | `int` (da `Settings.embed_batch_size`) | coerente con gli altri adapter |
| `embed(texts)` | `list[list[float]]` | char-n-gram (n=3..5) → sign-hashing `blake2b` → accumulo → L2-norm |

- Solo **stdlib** (`hashlib`, `math`, `re`/`str`). Deterministico cross-macchina/cross-Python (REQ-013/010/011).
- Testo vuoto → vettore zero (L2-norm di zero = zero). Nessun fallimento.

## 3. Adapter `GloveEmbedder` (`adapters/embeddings/glove.py`) — NUOVO

| Membro | Valore | Note |
|--------|--------|------|
| `name` | `"glove:300"` | distinto, codifica la dimensione (REQ-022) |
| `dim` | `300` | costante nota |
| `batch_size` | `int` | da Settings |
| `embed(texts)` | `list[list[float]]` | lookup token → media in-vocab → L2-norm; OOV via split camel/snake; tutto-OOV → zero (REQ-021/023) |

- Vocabolario `dict[str, ndarray]` caricato **lazy alla prima `embed`** dal path risolto (vedi §4).
- `numpy` importato **lazy dentro l'adapter** (REQ-024/053): selezionare un altro provider non lo importa.

## 4. Resolver/acquisizione GloVe (`adapters/embeddings/glove_cache.py`) — NUOVO

Funzioni pure + acquisizione (nessuna entità persistita oltre il file dati):
| Funzione | Firma | Comportamento |
|----------|-------|---------------|
| `glove_cache_dir()` | `() -> Path` | XDG-style per OS (stdlib): `%LOCALAPPDATA%\sertor\glove` / `$XDG_CACHE_HOME` / `~/.cache/sertor/glove` (REQ-031) |
| `resolve_glove_file(settings)` | `(Settings) -> Path` | priorità: `glove_path` esistente → cache → (in index) download; assente+no-rete → `GloveUnavailableError` (REQ-032/035/040) |
| `ensure_glove(settings)` | `(Settings) -> Path` | scarica `glove.6B.zip` (avviso una-tantum), estrae `glove.6B.300d.txt` atomico; legato all'indicizzazione (REQ-030/033/034) |

## 5. Eccezione di dominio `GloveUnavailableError` (`domain/errors.py`) — NUOVA

```text
class GloveUnavailableError(SertorError):
    # messaggio azionabile che nomina ENTRAMBE le vie d'uscita:
    #   "imposta SERTOR_GLOVE_PATH a un file glove.6B.300d.txt locale,
    #    oppure seleziona il provider lessicale con SERTOR_EMBED_PROVIDER=hash"
    def __init__(self, message: str, *, reason: str): ...
```
Sollevata da `resolve_glove_file`/`GloveEmbedder` su file assente+no-rete (REQ-040) e su errore di
download/caricamento/parse (REQ-041). Mai degrado silenzioso.

## 6. Composition root (`composition.py`)

`build_embedder` passa da 2 a **4 rami** (import lazy per ciascuno):
```text
provider = settings.embed_provider   # validato: unknown → ConfigError(key="SERTOR_EMBED_PROVIDER")
match provider:
    "glove" -> GloveEmbedder(resolve_glove_file(settings), batch_size=…)   # lazy numpy
    "hash"  -> HashingEmbedder(batch_size=…)   # + warning REQ-014
    "ollama"-> OllamaEmbedder(... retry ...)   # INVARIATO
    "azure" -> AzureEmbedder(... retry ...)    # INVARIATO
# cache opt-in (CachingEmbedder) invariato; emette embeddings_provider_selected (locali)
```
`build_store` **invariato nel corpo** (sceglie da `store_backend`); cambia solo il default a monte.
`collection_name` **invariato**: il `name` stabile di ogni provider (`glove:300`/`hash:512`/`ollama:…`/
`azure`) garantisce il namespacing `(corpus, provider)` (REQ-051).

## 7. Eventi di osservabilità (metrics-only, REQ-042)

| Evento | Campi | Quando |
|--------|-------|--------|
| `embeddings_provider_selected` | `provider` (chiuso) | costruzione di un provider locale |
| `glove_download` | `size_mb`, `source_host` | avvio download (una-tantum) |
| `glove_cache_hit` | `hit` (bool) | riuso di cache/override |

Nessun segreto, nessun path con `~`/username, nessun testo di query (Principio IX/RNF-3).

## 8. Pacchetto / dipendenze (`pyproject.toml`)

Nessun nuovo extra: `hash` = stdlib; `glove` usa `numpy` **già transitiva** da `chromadb` (riga 16) e
`urllib`/`zipfile` stdlib. Il core resta importabile senza scaricare nulla (SC-009/RNF-2).

## 9. Superficie installer (corollario, §research)

- Template `.env`: rimuovere `RAG_BACKEND`; aggiungere `SERTOR_EMBED_PROVIDER=...` + commento
  `# SERTOR_GLOVE_PATH=...`; profilo default `glove`.
- `rag_profile`/`configure`/`__main__` `--backend`: allineare a `SERTOR_EMBED_PROVIDER` (debito di
  completamento P2, gruppo G Should).
- Doc utente: 4 provider, nuovo default, override airgapped, nota di migrazione (rimozione `RAG_BACKEND` +
  cambio default) (REQ-061).
