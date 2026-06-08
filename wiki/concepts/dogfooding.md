---
title: Dogfooding
type: concept
tags: [dogfooding, rag, mcp, contesto-ancorato, corpus, sertor-core]
created: 2026-06-07
updated: 2026-06-07
sources: ["CLAUDE.md", ".mcp.json", "src/sertor_mcp/server.py"]
---

# Dogfooding

Il **dogfooding** in Sertor è la pratica di **interrogare il progetto stesso col proprio RAG**: Sertor
indicizza il proprio codice e la propria documentazione come **corpus** e li consulta con i suoi stessi tool
di retrieval, invece di leggerli a mano. *Usiamo il nostro stesso strumento* — su di noi.

## Come

Il server MCP `sertor-rag` (un [[thin-consumer|consumatore sottile]] del [[retrieval-core]], dichiarato in
`.mcp.json`) è puntato su un **corpus del progetto**; un agente interroga via `search_code` / `search_docs`
/ `search_combined` invece di Glob/Grep manuali. I corpora sono **isolati** per ambito (vedi
[[corpus-index-naming]]): `prototype` (il prototipo congelato) e `sertor` (la produzione). Richiede che il
corpus sia stato **indicizzato** prima dell'uso.

## Perché

- **Validazione continua del prodotto.** Esercitare il RAG sul caso d'uso reale (un repository vero, il
  nostro) fa emergere difetti e regressioni che un test sintetico non coglie.
- **Contesto ancorato, non assunto.** Dare a un agente le risposte recuperate dal codice reale — invece di
  affidarsi alla memoria o a ipotesi — è la stessa disciplina del [[lint-semantico-host-agnostico|lint
  semantico]]: non ragionare su contesto non verificato. Il dogfooding è il versante *retrieval* di questa
  disciplina.

## Vedi anche
- La superficie che lo abilita: [[server-mcp-produzione-feat-mcp]]. L'isolamento dei corpora:
  [[corpus-index-naming]]. Il record d'avvio (isolamento prototipo + setup): [[chiusura-prototipo-dogfooding]].
