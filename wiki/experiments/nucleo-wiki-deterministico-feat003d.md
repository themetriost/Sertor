---
title: Nucleo Wiki Deterministico Host-Agnostico — FEAT-003-D
type: experiment
tags: [FEAT-003-D, wiki-deterministico, host-agnostico, implementation, completed, python, cli]
created: 2026-06-05
updated: 2026-06-08 (distillato: entità in wiki-tools; record ridotto a evento+esito)
sources: ["specs/006-nucleo-wiki-deterministico/**", "src/sertor_core/wiki_tools/**", "wiki.config.toml", "tests/fixtures/doc_only_host/**"]
---

# FEAT-003-D: Nucleo Wiki Deterministico Host-Agnostico

**Evento (2026-06-05).** Implementata via SpecKit (specify→clarify→plan→tasks→implement) la **metà
deterministica** del wiki LLM: il sottopacchetto **[[wiki-tools|`wiki_tools`]]** (console-script
`sertor-wiki-tools`) che orchestra tutte le operazioni meccaniche del wiki — zero LLM, zero rete, stdlib —
guidato da `wiki.config.toml`. FEAT-003 era decomposta in **D** (questa, deterministica) + **N** (layer LLM).

> Record datato: la conoscenza durevole *su cosa è* `wiki_tools` (operazioni, contratti JSON, WikiProfile,
> host-agnosticità) è distillata in [[wiki-tools]].

## Esito (al 2026-06-05)
- **Codice:** 11 moduli in `src/sertor_core/wiki_tools/`; **mergiata su `master` via PR #13** (merge `17569da`).
- **Test:** 8 suite, 44 verdi (offline F.I.R.S.T.). **Lint:** ruff clean. **Constitution Check:** 10/10 ✅
  (inclusi i NON-NEGOZIABILI I/IV/X).

## La prova del Principio X (host-agnosticità)
**SC-001 dimostrata:** lo **stesso codice immutato** gira su Sertor (`code+doc`, radice `wiki/`) e su un
ospite finto `tests/fixtures/doc_only_host/` (solo-doc, radice/lingua diverse) cambiando **solo** il file di
config. È la realizzazione concreta della [[mission-vision|missione host-agnostica]].

## Note di chiusura (datate 2026-06-05)
- Import package-root: verificato **non**-problema (`import sertor_core.wiki_tools.scan` non carica `chromadb`;
  SDK lazy nelle `build_*`).
- Il lint dello strumento ha scoperto link rotti reali (auto-applicato) e la CLI è stata forzata a UTF-8 (fix
  crash su console Windows cp1252).

## Dove vive ora (conoscenza distillata)
- [[wiki-tools]] — operazioni, contratti versionati, `WikiProfile`, idempotenza, chi lo consuma.

---
**Cross-refs:** [[wiki-tools]] · [[deterministic-vs-judgment]] · [[constitution]] (Principio X) · [[sistema-wiki-fonte-unica]] · [[architettura-wiki-llm]]
