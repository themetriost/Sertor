---
title: Thin consumer
type: concept
tags: [thin-consumer, architettura, sertor-core, cli, mcp, host-agnostico, composition-root]
created: 2026-06-07
updated: 2026-06-07
sources: ["src/sertor_mcp/server.py", "src/sertor_core/__init__.py", "src/sertor_core/composition.py", "CLAUDE.md"]
---

# Thin consumer

Un **thin consumer** (consumatore sottile) è un'**interfaccia** — un CLI, un server MCP, un tool — che
espone le capacità del [[retrieval-core]] **importandolo come libreria** e cablandolo dalle factory
`build_*`, **senza reimplementare logica di retrieval**. Il valore (e tutta la logica) vive nel core;
l'interfaccia è un guscio sottile che traduce input/output verso il suo protocollo.

È il rovescio applicativo del principio del core: se *le dipendenze puntano verso l'interno*, allora ogni
superficie esterna è un **adattatore in uscita** che dipende dal core, mai il contrario.

## Perché

- **Il prodotto è la libreria, non l'interfaccia.** Mettere la logica nel core e tenere sottili le interfacce
  significa che CLI, MCP e qualunque host futuro **condividono lo stesso comportamento** (stessi risultati,
  stessa config, stessi errori) invece di divergere.
- **Host-agnosticità (Principio X, [[mission-vision]]).** Un'interfaccia sottile non
  incatena il core a un host specifico: aggiungere una nuova superficie = scrivere un nuovo guscio, non
  toccare il core.
- **Niente duplicazione di logica** = niente deriva fra interfacce, e una sola superficie da testare in
  profondità (il core); l'interfaccia si limita a un test di integrazione sottile.

## Come si realizza

Il core riesporta dal suo `__init__.py` le **factory di composizione** — `build_facade()`,
`build_indexer()`, `build_baseline_engine()` — che sono l'**unico punto d'ingresso** per un consumatore.
Il consumatore:

1. costruisce/carica la config (`Settings.load()`);
2. ottiene l'oggetto pronto da una `build_*` (che cabla adapter concreti dal [[retrieval-core|composition root]]);
3. chiama i metodi della facade e **mappa** il risultato sul proprio protocollo (argomenti CLI, tool MCP, …).

Non conosce gli adapter concreti né gli SDK: quelli restano dietro le porte, scelti da `Settings.backend`.

## Esempi (profilo Sertor)

- **Server MCP** ([[server-mcp-produzione-feat-mcp]]) — l'esempio canonico già realizzato: `src/sertor_mcp/`
  ottiene la facade con `build_facade(Settings.load())` (memoizzata) ed espone 3 tool
  (`search_code`/`search_docs`/`search_combined`) mappando i `RetrievalResult` sul protocollo MCP. Nessuna
  logica di retrieval propria.
- **CLI `sertor`** — il CLI di distribuzione (in arrivo) è un thin consumer analogo: importa il core, non
  dipende dagli adapter Azure (extra opzionale).
- **`sertor-wiki-tools`** — la CLI del nucleo wiki deterministico ([[nucleo-wiki-deterministico-feat003d]])
  è un entry sottile sopra `sertor_core.wiki_tools`, guidato da `wiki.config.toml`.

## Vedi anche
- Ciò che consumano: [[retrieval-core]]. Vincolo che lo motiva: [[constitution]] (dipendenze verso l'interno).
