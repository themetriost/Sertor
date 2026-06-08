---
title: Server MCP di Produzione (FEAT-MCP) — record di feature (completata)
type: experiment
tags: [feature, mcp, server, produzione, retrieval, superficie-finale, enabler, feat-mcp]
created: 2026-06-06
updated: 2026-06-08 (distillato: entità in mcp-server; record ridotto a evento+esito)
sources: ["requirements/sertor-core/mcp/requirements.md", "specs/007-mcp-sertor-core/**", "src/sertor_mcp/**"]
---

# Server MCP di Produzione (FEAT-MCP) — record di feature

**Evento (2026-06-06).** Implementato — flusso **SpecKit completo** (requirements→specify→clarify→plan→
analyze→implement) — il **[[mcp-server|server MCP `sertor-rag`]]** (`src/sertor_mcp/`), un
[[thin-consumer|consumatore sottile]] del [[retrieval-core]] che espone la ricerca del nucleo come tool MCP.
**Mergiata su `master` (PR #15)**; `.mcp.json` ri-puntato dal server del prototipo (rotto) alla produzione.

> Record datato: la conoscenza durevole *su cosa è* il server (3 tool, formato, facade memoizzata, tolleranza
> ereditata, isolamento dipendenze) è distillata in [[mcp-server]].

## Esito (al 2026-06-06)
- **Codice:** `src/sertor_mcp/{__init__,server}.py` + `tests/unit/test_mcp_server.py` (**6 test verdi**;
  suite non-cloud **116 passed**). **Lint:** ruff clean. **Constitution Check:** 10/10 ✅ (I/IV/X superati).
- **Binding:** `pyproject.toml` extra `mcp`; `.mcp.json` → `python -m sertor_mcp.server`, `SERTOR_CORPUS=sertor`.

## Perché è l'enabler critico
FEAT-MCP è la **superficie finale** che sblocca tre capacità: (1) il **probe-RAG del lint semantico** del
wiki (N5, oggi fallback `Read`/`Grep`); (2) il **[[dogfooding|dogfood di produzione]]** (interrogare Sertor su
sé stesso); (3) l'**entry-point dell'agente Azure**.

## Resta aperto (non bloccante)
**Acceptance T023/T024 non eseguiti:** richiedono l'**indice del corpus `sertor`** (fuori dal codice della
feature; manca un entry-point CLP di indicizzazione su master). Finché manca, i tool danno `[]` e il probe N5
resta in fallback.

## Dove vive ora (conoscenza distillata)
- [[mcp-server]] — i 3 tool, il formato citabile, la facade memoizzata, la tolleranza, l'isolamento `mcp`.

---
**Cross-refs:** [[mcp-server]] · [[thin-consumer]] · [[retrieval-core]] · [[architettura-wiki-llm]] (item 5a) · [[corpus-index-naming]]
