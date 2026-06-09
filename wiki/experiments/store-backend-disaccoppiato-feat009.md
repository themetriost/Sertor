---
title: Disaccoppiamento store ↔ embeddings + indice dogfood sertor — FEAT-009
type: experiment
tags: [FEAT-009, sertor-core, composition, store-backend, azure, embeddings, dogfooding, indice, speckit]
created: 2026-06-09
updated: 2026-06-09
sources: ["specs/009-store-backend-disaccoppiato/**", "src/sertor_core/config/settings.py", "src/sertor_core/composition.py", "src/sertor_core/adapters/embeddings/azure.py"]
---

# Disaccoppiamento store ↔ embeddings + indice dogfood `sertor` — FEAT-009

**Evento (2026-06-09).** Per costruire l'**indice di dogfooding del corpus di produzione `sertor`** (assente
finché ora) servivano **embeddings Azure** + **store Chroma locale**, combinazione non esprimibile perché su
`master` lo store era accoppiato a `RAG_BACKEND`. Implementata via flusso SpecKit (lean) la manopola
`store_backend` **distinta** dal provider di embeddings, più la compatibilità dell'`AzureEmbedder` con
l'endpoint **v1**. Poi **costruito** l'indice. Aperta la **PR** `spec/009-store-backend-disaccoppiato` → master.

> Record datato: il *cosa è* (decoupling, naming) è distillato in [[ports-adapters]] e [[corpus-index-naming]];
> gli artefatti di processo vivono in `specs/009-store-backend-disaccoppiato/` (citati, non ricopiati).

## Le decisioni che lo caratterizzano
- **Due manopole, non una**: `backend` (`RAG_BACKEND`) sceglie l'embedder, `store_backend`
  (`SERTOR_STORE_BACKEND`) sceglie lo store. Default `store_backend = backend` → **retro-compatibile** (nessun
  cambio per chi non usa la nuova variabile). Rafforza i Principi II (local-first) e VIII (config centralizzata).
- **Endpoint Azure v1**: l'`AzureEmbedder` rileva la superficie `/openai/v1` e **non** invia `api-version`
  (che la v1 rifiuta con HTTP 400, verificato con probe live: solo la chiamata senza `api-version` torna 200).
- **Branch stale non mergiata**: il design era già abbozzato su `feat/decouple-store-backend`, **divergente**
  (regrediva la rotazione log FEAT-008, rimuoveva `wiki_tools`) → **riusato il design, riscritto pulito**.
- **Fuori scope**: `build_llm`/porta LLM (distillazione wiki) — feature separata.

## Esito (al 2026-06-09)
- **Codice:** `config/settings.py` (campo `store_backend`), `composition.py` (`build_store`/`collection_name`
  su `store_backend`), `adapters/embeddings/azure.py` (flag v1).
- **Test:** suite `not cloud` verde (135) + ruff pulito su `src`/`tests`. Aggiunto un **fix d'isolamento** in
  `test_mcp_server` (`_facade()` caricava il `.env` reale con `override=True`, inquinando `os.environ` e
  rompendo i test sui default — emerso ora che `.env` ha `RAG_BACKEND=azure`).
- **Indice dogfood:** corpus `sertor` indicizzato per la **prima volta** — **191 doc / 1578 chunk**, dim 3072,
  collezione `sertor__azure_text_embedding_3_large` in `.index-sertor/` (~55s). Retrieval verificato via
  facade (`search_docs` molto pertinente su query reali).

## Resta aperto
- **Server MCP live**: il processo `sertor-rag` avviato a inizio sessione gira col **codice pre-modifica**
  (store accoppiato) → erra `azure_search` finché non **riparte** (nuova sessione/reconnect); post-restart
  servirà l'indice. Il path di codice è già provato identico via `build_facade`.
- **Qualità retrieval su codice**: `search_code` su query architetturali è debole (motore baseline vettoriale);
  migliorerà con i motori ibrido/grafo.

---
**Cross-refs:** [[ports-adapters]] · [[corpus-index-naming]] · [[thin-consumer]] · [[dogfooding]] · [[mcp-server]]
