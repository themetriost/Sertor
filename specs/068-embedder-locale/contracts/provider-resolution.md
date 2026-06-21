# Contract — Risoluzione del provider di embeddings (DA-1, REQ-001..007)

**Rigenerato (2026-06-21):** `RAG_BACKEND` **rimosso**. Unica superficie del provider:
`SERTOR_EMBED_PROVIDER`. Lo store ha la sua manopola separata. Confine: la porta `EmbeddingProvider`
**non cambia** (REQ-050).

## Manopole

| Manopola | Valori | Default | Selezione |
|----------|--------|---------|-----------|
| `SERTOR_EMBED_PROVIDER` | `glove` · `hash` · `ollama` · `azure` | `glove` | provider di **embeddings** (UNICA superficie) |
| `SERTOR_STORE_BACKEND` | `local` · `azure` | `local` | backend del **vector store** (ortogonale) |
| `SERTOR_GLOVE_PATH` | path a `glove.6B.300d.txt` | _(unset)_ | override file GloVe (airgapped) |

`SERTOR_EMBED_PROVIDER` e `SERTOR_STORE_BACKEND` sono **indipendenti**: ogni combinazione è valida (es.
`glove` + store `azure`, o `azure` + store `local`).

## Contratto di risoluzione (`Settings.load` → `composition.build_embedder`)

1. `Settings.load()` legge `SERTOR_EMBED_PROVIDER` (default `glove`) in `embed_provider`, `SERTOR_STORE_BACKEND`
   (default `local`) in `store_backend`, `SERTOR_GLOVE_PATH` in `glove_path`.
2. **`RAG_BACKEND` residuo** in env → `WARNING config_rag_backend_ignored` che nomina le manopole
   sostitutive; il valore **non** è letto né mappato (REQ-007). Nessun cambio di comportamento silenzioso.
3. `build_embedder` valida `embed_provider`:
   - valore riconosciuto → costruisce l'adapter corrispondente (import lazy);
   - valore NON in `{glove,hash,ollama,azure}` → `ConfigError(key="SERTOR_EMBED_PROVIDER")` che nomina i
     valori ammessi (REQ-003).

## Tabella decisionale

| `SERTOR_EMBED_PROVIDER` | Adapter | Credenziali richieste da `validate_backend` | Note |
|-------------------------|---------|---------------------------------------------|------|
| _(unset)_ | `GloveEmbedder` | nessuna | **default** (REQ-002) |
| `glove` | `GloveEmbedder` | nessuna | acquisizione on-demand / override path |
| `hash` | `HashingEmbedder` | nessuna | + warning «NL limitata» (REQ-014) |
| `ollama` | `OllamaEmbedder` | nessuna | invariato |
| `azure` | `AzureEmbedder` | `AZURE_OPENAI_ENDPOINT/_API_KEY/_EMBED_DEPLOYMENT` | invariato |
| altro | — | — | `ConfigError` (REQ-003) |

| `SERTOR_STORE_BACKEND` | Store | Credenziali |
|------------------------|-------|-------------|
| _(unset)_ / `local` | `ChromaStore` | nessuna |
| `azure` | `AzureSearchStore` | `AZURE_SEARCH_ENDPOINT/_API_KEY` |

## `validate_backend()` (statica, offline)

- `embed_provider == "azure"` → aggiunge i 3 campi Azure OpenAI mancanti.
- `store_backend == "azure"` → aggiunge i 2 campi Azure Search mancanti.
- provider locali (`glove`/`hash`) e `ollama` → **lista vuota** (mai blocco, REQ-005, SC-001).

## Invarianti
- Esistenti (Ollama/Azure) **invariati** quando non selezionati (REQ-052, SC-004).
- Namespacing `(corpus, provider)` via `collection_name` impedisce la mescolanza (REQ-051).
- Selezione **solo via config**, nessun codice da toccare (SC-004).
