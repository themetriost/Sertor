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
- **Tasks `specs/137-provider-openai/tasks.md`:** 25 task in sequenza; 23 completati; T024/T025 aperte (live test con chiave OpenAI reale + epic row post-merge).

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

## Prodotto

Il provider è **installabile su ospiti manuali** (`.sertor/.env`: `SERTOR_EMBED_PROVIDER=openai` + `OPENAI_API_KEY`), **non** ancora tramite wizard installer (`sertor configure`) — il configuratore conosce solo `azure`/`local` (frozen perimeter di Kaelen).

## Finding su installer

Il configuratore installer (`packages/sertor/src/sertor_installer/configure.py:267-275`) ignora silenziosamente `--set OPENAI_API_KEY=…` / `--set SERTOR_EMBED_PROVIDER=openai` perché il provider risiede fuori dal suo catalogo hand-written; la coverage guard `T-110-COV` (`packages/sertor/tests/test_config_fields.py`) iterates una lista provider manuale e resta verde mentre il catalogo non si aggiorna (Principio XIV istanza). **Da segnalare a Kaelen** in bacheca alla consegna (task T025): l'installer è congelato dal 2026-09-18 e non si ripara da Sertor.

## Link correlati

- **Architettura adattatore:** [[ports-adapters]] (porta `EmbeddingProvider`, adapter OpenAI + condiviso)
- **Configurazione Runtime:** [[retrieval-core]] (Settings, composition root per provider)
- **Decision Record:** `specs/137-provider-openai/research.md` (D-1…D-7, percorso progettuale)

