# Data model — 137 provider OpenAI

## Settings (estensione)

| Campo | Variabile | Default | Note |
|---|---|---|---|
| `embed_provider` | `SERTOR_EMBED_PROVIDER` | `glove` | nuovo valore ammesso: `openai` |
| `openai_api_key` | `OPENAI_API_KEY` | `""` | segreto; `repr=False`; obbligatorio con `openai` |
| `openai_embed_model` | `OPENAI_EMBED_MODEL` | `text-embedding-3-large` | vuoto ⇒ default |
| `openai_base_url` | `OPENAI_BASE_URL` | `https://api.openai.com/v1` | vuoto ⇒ default; barra finale ignorata |

**Validazione statica** — `missing_provider_keys()`:

| `embed_provider` | chiavi richieste |
|---|---|
| `glove` / `hash` / `ollama` | nessuna |
| `azure` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT` |
| `openai` | `OPENAI_API_KEY` |

`validate_backend()` = `missing_provider_keys()` + chiavi mancanti dello store (`AZURE_SEARCH_*` se
`store_backend=azure`). Modello e URL hanno default, quindi non sono mai «mancanti».

## OpenAIEmbedder (porta `EmbeddingProvider`)

| Attributo | Valore |
|---|---|
| `name` | `openai:<model>` |
| `dim` | `None` fino alla prima risposta, poi la lunghezza del primo vettore |
| `batch_size` | `Settings.embed_batch_size` |

Costruzione con chiave, modello o URL vuoti → `EmbeddingError(provider="openai",
reason="<campi> missing", retriable=False)`.

## Collezione e cache (invariati, verificati)

- Collezione: `<corpus>__<sanitize("openai:<model>")>` → una per modello.
- Cache embedding: chiave `(inner.name, hash del testo)` → nessun riuso fra provider o modelli.
