---
title: Architettura attuale (as-built) — Sertor RAG toolset
type: synthesis
tags: [architettura, as-built, retrieval, agentic, mcp, produzione]
created: 2026-05-29
updated: 2026-05-29
sources: []
---

# Architettura attuale (as-built)

Stato del workspace al 2026-05-29: tappe **01–04 complete**. Questo è il disegno **realizzato**
(complementare al disegno *target* in [[architettura-target]]). Principio portante: gli **stessi
tool** di `shared/retrieval.py` alimentano sia 4 orchestratori LLM sia il server MCP, senza
duplicazione.

## Diagramma

```mermaid
flowchart TB
  subgraph SRC["Corpus — raw/fastapi/ (immutabile)"]
    PY["codice .py<br/>fastapi/ + docs_src/"]
    MD["doc .md<br/>docs/en/"]
  end

  subgraph ING["Ingestion — shared/"]
    LD["loaders.py<br/>Doc{id,text,metadata: source=code|doc}"]
    CK["chunking<br/>tree-sitter code-aware | markdown"]
    EMB["embeddings.py — 3 provider<br/>ollama nomic · azure small · azure large"]
  end

  subgraph IDX["Indici"]
    VEC["Chroma<br/>1 collection / provider · dense"]
    BM["BM25 in-memory<br/>sparse · lessicale"]
    GR["AST code graph<br/>networkx/GraphML · struttura"]
    GRAG["GraphRAG community graph<br/>(03C, separato)"]
  end

  FAC["shared/retrieval.py — FACADE unica<br/>search_code/docs/combined (RRF+rerank, filtro source)<br/>find_symbol · who_calls · related_docs"]

  subgraph CONS["Tappa 04 — consumatori (stessi tool)"]
    direction LR
    ORCH["Orchestratori LLM (loop nostro)<br/>vanilla · AutoGen · Semantic Kernel · LangGraph"]
    MCP["mcp_server.py<br/>(server MCP, stdio)"]
  end

  LLM["shared/llm.py — chat client<br/>Azure gpt-5.4-mini | Ollama"]
  CLAUDE["Claude Code / client MCP<br/>(orchestra lato client)"]
  EVAL["evaluate.py<br/>metriche + ESEMPI-agentic.md<br/>cache: eval_results.json"]

  CFG["shared/config.py + .env<br/>RAG_BACKEND = local|azure"]

  PY --> LD; MD --> LD
  LD --> CK --> EMB --> VEC
  CK --> BM
  LD --> GR
  PY -.-> GRAG
  VEC --> FAC; BM --> FAC; GR --> FAC
  FAC --> ORCH
  FAC --> MCP
  ORCH <--> LLM
  MCP --> CLAUDE
  EVAL --> ORCH
  CFG -. governa .-> EMB
  CFG -. governa .-> LLM
  CFG -. governa .-> FAC
```

## Strati

1. **Ingestion → Indici.** `loaders.py` produce `Doc` con `source=code|doc`; il chunking è
   code-aware (tree-sitter) per il codice, markdown per i doc; `embeddings.py` offre 3 provider.
   Tre indici complementari: denso (**Chroma**), lessicale (**BM25**), strutturale (**grafo AST**).
   **GraphRAG** (03C) è un indice a community separato.
2. **Facade.** `shared/retrieval.py` è l'**unico** punto d'accesso ai motori, con 6 tool
   (`search_code/docs/combined` con RRF + rerank FlashRank e filtro `source`; `find_symbol`,
   `who_calls`, `related_docs` sul grafo). Nasconde i dettagli delle tappe 01–03.
3. **Consumatori (Tappa 04).** Gli stessi 6 tool alimentano: (a) 4 **orchestratori LLM** con loop
   proprio (`vanilla`, AutoGen, Semantic Kernel, LangGraph) via `shared/llm.py`; (b) il **server
   MCP** (`mcp_server.py`), dove l'orchestrazione la fa il client (**Claude Code**). `evaluate.py`
   pilota gli orchestratori e genera metriche + `ESEMPI-agentic.md`.
4. **Trasversale.** `config.py`/`.env` (`RAG_BACKEND`) governa provider di embedding e LLM:
   switch local↔azure. Entry point operativo attuale: **Azure gpt-5.4-mini** + text-embedding-3-large
   (vedi [[agent-llm-azure-non-locale]]).

## Caching — stato e backlog di produzione

**In cache oggi:** risultati eval (`eval_results.json` + `--render-from` + merge per-motore);
indici in-process (`@lru_cache` su HybridIndex/CodeGraph in `shared/retrieval.py`, caldi nel
processo long-lived del server MCP); modello FlashRank su disco; cache estrazione GraphRAG (~210 MB).

**Backlog di produzione** (non in prototipo — vedi policy SpecKit/branch in [[git-policy-prototipo-vs-produzione]]):
1. **Cache embedding query** (lru/disk in `shared/embeddings.py`) — evita di ri-embeddare (e ri-pagare in azure) query identiche.
2. **Cache risposte LLM su disco** (es. SQLite) — run agent/eval riproducibili e gratuiti sui task già visti.
3. **Tracciare/ottimizzare il prompt-caching di Azure** (`cached_tokens` in `shared/llm.py`) — misurare l'hit-rate e ordinare i prompt (system + schemi tool in testa) per massimizzarlo.

Altri punti di produzione: igiene corpus (blob base64 in `docs_src/`), eval con task multi-hop
più discriminanti + media multi-run, transizione a **SpecKit + branch/PR**.
