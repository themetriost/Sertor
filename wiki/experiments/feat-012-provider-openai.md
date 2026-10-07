---
title: FEAT-012 — Provider di embedding OpenAI diretto
type: experiment
tags: [embedding, provider, openai, feat-012, sertor-core, adapters]
created: 2026-10-07
updated: 2026-10-07
sources: ["specs/137-provider-openai/", "requirements/sertor-core/epic.md", "src/sertor_core/adapters/embeddings/", "src/sertor_core/config/settings.py"]
---

# FEAT-012 — Provider di embedding OpenAI diretto

> **Contesto (2026-10-07):** la chiave Azure del dogfood è stata rifiutata (`http 401`) e il server MCP
> non serviva più ricerche. Il dogfood è passato a `glove` (indice `sertor__glove_300`, 1557 documenti,
> 17574 chunk) come ripiego; questo provider è il rimedio di qualità.

Implementazione del provider di embedding **OpenAI API diretto** (o qualsiasi servizio compatibile) come alternativa ai provider esistenti (Azure, Ollama, GloVe). Abilita il setup distribuito su ospiti che desiderano usare l'API OpenAI senza Azure.

## Sommario del lavoro

Il feature è stato sviluppato con **full SpecKit flow** (requirements → spec → clarify → plan → tasks → implementation):

- **Spec `specs/137-provider-openai/spec.md`:** 4 user story, 18 functional requirement, 5 criteri di successo, out-of-scope (*org/project headers*, *vector dimensions* → backlog).
- **Plan `specs/137-provider-openai/plan.md`:** 7 decisioni architetturali (D-1…D-7), data model, contracts, quickstart.
- **Tasks `specs/137-provider-openai/tasks.md`:** 25 task in sequenza; 25 completati.

## Implementazione

### Architettura

La base condivisa **`OpenAIProtocolEmbedder`** (`src/sertor_core/adapters/embeddings/_openai_protocol.py`) realizza il protocollo OpenAI (batching, error classification, retry per-batch, dimensionality detection, token-counting signal):

- **`OpenAIEmbedder`** — implementazione per API OpenAI diretta (Bearer auth, endpoint, modello `text-embedding-3-large` default).
- **`AzureEmbedder`** (refactored) — ora una **sottoclasse sottile** della base: fissa solo URL, intestazione `api-key`, `api-version` (fuori dalla superficie v1) e nome. I suoi 24 test esistenti passano senza modifiche.

### Configurazione

Tre nuovi campi in `Settings` (la chiave con `repr=False`, così non compare stampando le settings):
- `openai_api_key` — Bearer token per OpenAI o servizio compatibile
- `openai_embed_model` — modello embedding (default `text-embedding-3-large`)
- `openai_base_url` — endpoint base (default OpenAI pubblico)

Il metodo `missing_provider_keys()` centralizza la validazione (elimina la lista manuale hand-copied `_PROVIDER_ENV_KEYS` dal `cli/__main__.py`).

### Testing

- **Unit tests:** 20 nuovi test in `tests/unit/test_openai_embedder.py` (comportamento, errori, retry, dimensionality)
- **Integration tests (cloud marker):** `tests/integration/test_openai_live.py` — esecuzione con vera API OpenAI
- **Existing tests:** 24 test di Azure passano invariati (refactoring non-breaking)
- **Mutation check:** rimozione del ramo `openai` da `missing_provider_keys()` rende 3 test rossi → validazione della copertura

Esito: **1520 test non-cloud verdi** (3 skipped), **suite completa verde** (sertor 595 · sertor-install-kit 207 · sertor-flow 149 · speclift 122 · specaudit 59), **ruff clean**.

## Docfile del provider

**Contratto OpenAI embedding provider** in `specs/137-provider-openai/contracts/openai-embedding-provider.md` — signature, errori, edge case, protocollo di retry.

## Distillazione

L'architettura della **base di protocollo condivisa** (`OpenAIProtocolEmbedder`) è distillata nella pagina [[ports-adapters]] (sezione della porta `EmbeddingProvider`, tabella degli adapter con la nuova riga OpenAI + selettore a 5 valori). Non crea una pagina propria perché ha una sola casa naturale: la porta.

## Verifica reale (T024)

La chiave OpenAI è stata inserita in `.sertor/.env`; il provider del dogfood rimane `glove` (il runtime `.sertor/` segue `master`, che il provider non conosce ancora).

- **Live test:** `tests/integration/test_openai_live.py -m cloud` → 1 PASSED; vettori 3072-dim (`text-embedding-3-large`).
- **E2E via CLI:** `sertor-rag index .` su corpus temporaneo con `.env` dedicato → collezione `e2e__openai_text_embedding_3_large`, 3 doc, 125 chunk, 3.7 s; `sertor-rag search` ritorna il provider doc primo risultato.
- **Doctor:** `--online --area provider` chiave valida → `pass (probe=reachable)`; chiave sbagliata → `warn` http 401 (chiave non stampata); chiave assente → `FAIL` col nome della variabile.
- **Correzione doctor:** rimedio precedente suggeriva «o esegui `sertor configure`» ma il wizard congelato ignora le chiavi `openai`; rimedio ora è «imposta <KEY> in .sertor/.env» (`src/sertor_core/services/doctor.py`).
- **MCP dogfood:** server riconnesso dall'utente; smoke glove (`search_code`, `search_docs`, `find_symbol` attivi); `find_symbol collection_name` → riga 168 posizione master (attesa fino al post-merge re-index); con glove, `search_code` non ritorna `build_embedder` nei top 3 — drop di qualità che il provider è fatto per correggere.

## Consegna e rilascio

**PR #283 merged (2026-10-07):** Feature mergiata su master (commit `c66c231`). Il commit di rilascio `75f07a1` (`/VERSION` 0.5.0, CHANGELOG, pin d'installazione @v0.5.0 in README/docs) è dentro la PR; il tag `v0.5.0` è sul merge `c66c231`, Release pubblicata come latest. Release notes: solo il capability `rag` cambia; non eseguire upgrade per `wiki`/`sertor-flow`.

**Dogfood su v0.5.0 openai:**
- Runtime re-locked sertor-core 0.4.2 → 0.5.0; provider configurazione glove → openai (`.sertor/.env` SERTOR_EMBED_PROVIDER=openai).
- Re-index completato: collezione `sertor__openai_text_embedding_3_large`, 1572 documenti, 17730 chunks, dimensione vettore 3072, tempo ~320 s.
- Doctor: `--online` prima del re-index → provider `pass (reachable)` e indice mancante (atteso); dopo il re-index → PASS.
- MCP richiede reconnect utente per servire con nuovo provider.

**Comunicato Acta:** Due post pubblicati: release announcement (v0.5.0) e segnalazione a Kaelen di tre wizard defects (no openai profile, --set ignora chiavi, coverage guard hand-written provider-list).

**Verifica:** CI master 9/9 verde; upgrade-smoke-full sul salto v0.4.2 → master (`c66c231`, poi taggato): 4 combinazioni, 36/36 esiti OK.

## Prodotto

Il provider è **installabile su ospiti manuali** (`.sertor/.env`: `SERTOR_EMBED_PROVIDER=openai` + `OPENAI_API_KEY`), **non** ancora tramite wizard installer (`sertor configure`) — il configuratore conosce solo `azure`/`local` (frozen perimeter di Kaelen).

## Finding su installer

Il configuratore installer (`packages/sertor/src/sertor_installer/configure.py:267-275`) ignora silenziosamente `--set OPENAI_API_KEY=…` / `--set SERTOR_EMBED_PROVIDER=openai` perché il provider risiede fuori dal suo catalogo hand-written; la coverage guard `T-110-COV` (`packages/sertor/tests/test_config_fields.py`) iterates una lista provider manuale e resta verde mentre il catalogo non si aggiorna (Principio XIV istanza). **Da segnalare a Kaelen** in bacheca alla consegna (task T025): l'installer è congelato dal 2026-09-18 e non si ripara da Sertor.

## Link correlati

- **Architettura adattatore:** [[ports-adapters]] (porta `EmbeddingProvider`, adapter OpenAI + condiviso)
- **Configurazione Runtime:** [[retrieval-core]] (Settings, composition root per provider)
- **Decision Record:** `specs/137-provider-openai/research.md` (D-1…D-7, percorso progettuale)

