# Research — 137 provider OpenAI

Decisioni di design della feature FEAT-012. Ancoraggio al codice al 2026-10-07 (branch
`137-provider-openai`, base `9783ad4`).

## D-1 — Una base di protocollo condivisa, due adapter sottili

**Decisione:** estrarre la logica HTTP del protocollo `/embeddings` (lotti, chiamata, classificazione
degli errori, retry per lotto, dimensione, evento con token) dall'adapter Azure in una base privata
`adapters/embeddings/_openai_protocol.py`. `AzureEmbedder` e il nuovo `OpenAIEmbedder` diventano
sottoclassi che fissano solo **URL, intestazione di autenticazione, parametri di query e nome**.

**Perché:** l'adapter Azure (`adapters/embeddings/azure.py`, ~150 righe) parla già il protocollo
OpenAI. Le due superfici differiscono in tre punti, tutti al costruttore:

| | Azure | OpenAI |
|---|---|---|
| URL | `{endpoint}/embeddings` | `{base_url}/embeddings` |
| Credenziale | `api-key: <key>` | `Authorization: Bearer <key>` |
| Query | `api-version` se non v1 | nessuna |
| Nome | `azure:<deployment>` | `openai:<model>` |

Copiare le ~100 righe di logica condivisa farebbe divergere nel tempo retry e classificazione degli
errori (rischio R-1 dei requisiti) — la logica è la stessa per contratto, quindi deve vivere in un
punto solo (Principio XIV applicato al codice, DRY del Principio III).

**Alternative scartate:**
- *Copia dell'adapter Azure* — più rapida, ma duplica la parte che conta (errori/retry) senza
  riconciliatore.
- *`AzureEmbedder` sottoclasse di `OpenAIEmbedder`* — semanticamente plausibile (Azure OpenAI *è* un
  servizio compatibile), ma lega la validazione Azure (messaggio «incomplete Azure configuration») al
  costruttore OpenAI; una base neutra tiene separati i due messaggi d'errore.
- *SDK `openai` ufficiale* — dipendenza nuova e pesante per una sola chiamata REST già scritta con
  `httpx` (Principio III, NFR-02).

**Vincolo di non-regressione (FR-017):** i test esistenti dell'adapter Azure
(`test_embeddings.py`, `test_embed_retry.py`, `test_embedding_token_log.py`) restano **invariati** e
verdi: usano solo costruttore e comportamento, non attributi interni.

## D-2 — Default nelle `Settings`, derivati nel `load()`

**Decisione:** tre campi nuovi in `Settings`: `openai_api_key` (`field(repr=False)`),
`openai_embed_model = "text-embedding-3-large"`, `openai_base_url = "https://api.openai.com/v1"`. In
`Settings.load()` i default si leggono **dal campo** (`os.getenv(...) or cls.<campo>`), non ripetendo il
letterale.

**Perché:** il pattern esistente ripete il letterale due volte (campo + `getenv`, es.
`ollama_embed_model`): due copie dello stesso default, nessun riconciliatore (Principio XIV). Per i
campi nuovi lo si evita senza toccare quelli vecchi (fuori scope). L'`or` tratta anche la variabile
**presente ma vuota** (`OPENAI_BASE_URL=` lasciata nel `.env`) come assente, che è il comportamento
atteso. `repr=False` evita che la chiave compaia stampando le settings (FR-015).

## D-3 — Chiavi obbligatorie del provider: derivate, non elencate due volte

**Decisione:** `Settings` espone `missing_provider_keys()` (chiavi mancanti del solo provider di
embedding) e `validate_backend()` diventa `missing_provider_keys() + chiavi mancanti dello store`. La
CLI di `doctor` usa `missing_provider_keys()` e **rimuove** l'insieme hardcoded `_PROVIDER_ENV_KEYS`
(`cli/__main__.py:633`).

**Perché:** oggi la CLI ricava le chiavi del provider filtrando `validate_backend()` con un elenco
copiato a mano dei tre nomi `AZURE_OPENAI_*`. Aggiungere `OPENAI_API_KEY` a quell'elenco sarebbe la
seconda copia di un fatto che `Settings` già possiede (il docstring di `validate_backend` lo dichiara
«ONLY source»): esattamente l'istanza che il Principio XIV vieta. Derivandolo, il prossimo provider
non richiede di ricordarsi della CLI.

**Alternativa scartata:** aggiungere `OPENAI_API_KEY` a `_PROVIDER_ENV_KEYS` — una riga, ma la copia
resta e il difetto si ripresenta al provider successivo.

## D-4 — La sonda online di `doctor` non richiede lavoro

`build_provider_probe` (`composition.py:819`) costruisce l'embedder dalla factory ed embedda una
stringa sentinella: qualunque provider registrato in `build_embedder` è sondato senza codice dedicato,
e il motivo dell'errore è già passato da `scrub_text`. Si aggiunge solo un test che lo esercita con
`openai`.

## D-5 — Sicurezza della chiave

Il messaggio d'errore usa provider, stato HTTP e tipo d'eccezione: mai corpo della richiesta né
intestazioni. `scrub_text` già redige `sk-…` e `Bearer …` (`observability/scrub.py`). Test dedicato:
la chiave non compare nel messaggio dell'errore né nei campi dell'evento.

## D-6 — Identità e isolamento

Nome `openai:<model>` → collezione `<corpus>__openai_<model sanitizzato>` via `collection_name()`; la
cache degli embedding è già indicizzata per `inner.name` (`adapters/embeddings/cache.py:120`). Nessun
codice nuovo: solo test che lo confermano (FR-016).

## D-7 — Debito verso Kaelen (installer congelato)

Il wizard `sertor configure --backend` (`packages/sertor/src/sertor_installer/configure_fields.py`) e
il template `.env` installato non conoscono `openai`. Non si toccano (congelamento 2026-09-18).

**Verificato nel codice, tre fatti che la richiesta a Kaelen deve portare:**
1. `_embed_provider_for` (`configure.py:192`) mappa i profili solo su `azure`/`glove`: il wizard non
   può produrre `openai`, quindi **non va in crash** (non chiede mai `OPENAI_API_KEY` al catalogo).
2. `--set` scrive **solo** i campi del catalogo applicabile al profilo (`configure.py:267-275`):
   `--set OPENAI_API_KEY=…` e `--set SERTOR_EMBED_PROVIDER=openai` sono **ignorati senza avviso**. È un
   silenzio del wizard indipendente da questa feature, ma che questa feature rende raggiungibile.
3. Il test di non-deriva catalogo↔`validate_backend` (`packages/sertor/tests/test_config_fields.py`,
   T-110-COV) itera su un elenco di provider **scritto a mano** (`azure, glove, hash, ollama`): non vede
   `openai`, quindi resta verde mentre il catalogo non copre `OPENAI_API_KEY`. È una guardia la cui
   premessa è una copia (Principio XIV): andrebbe derivata dai provider ammessi dal core.

Sull'ospite l'attivazione è quindi **manuale** (`.sertor/.env`), ed è così che la documenta
`docs/install.md`. Alla consegna si **affigge in bacheca** la richiesta di cablaggio a Kaelen con i tre
punti. Lato nostro, per rendere derivabile il punto 3 senza toccare l'installer, il core espone
l'elenco dei provider ammessi come costante pubblica (`EMBED_PROVIDERS` in `config/settings.py`), che
`composition.py` usa al posto del proprio `_VALID_EMBED_PROVIDERS`.

## Estensioni promosse (regola «gli Out of Scope si promuovono»)

- Riduzione delle dimensioni (`dimensions`) e intestazioni organizzazione/progetto OpenAI →
  roadmap, *Nuove funzionalità da discutere*.
- Cablaggio nel wizard dell'installer → richiesta a Kaelen (bacheca) + nota nella riga FEAT-012.
