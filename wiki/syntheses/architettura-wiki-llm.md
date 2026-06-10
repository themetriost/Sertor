---
title: Architettura del Wiki LLM — stato e roadmap
type: synthesis
tags: [architettura, wiki-llm, host-agnostico, principio-x, roadmap, feat-003, deterministico-vs-giudizio]
created: 2026-06-05
updated: 2026-06-10 (feature 010: query congiunta multi-collezione + upsert-index in CLI → write-back entrambi cablati, evoluzione 1a chiusa; restano N3/N4/N6)
sources: [
  "src/sertor_core/wiki_tools/**",
  "wiki.config.toml",
  ".claude/skills/wiki-author/wiki-playbook.md",
  ".claude/agents/wiki-curator.md",
  ".claude/commands/wiki.md",
  ".claude/settings.json",
  "requirements/sertor-core/wiki-llm/TODO.md",
  "requirements/sertor-core/wiki-creazione/requirements.md"
]
---

# Architettura del Wiki LLM — stato e roadmap

Vista d'insieme dell'**LLM Wiki** di Sertor dopo il ponte D→N. Per i dettagli dei singoli pezzi:
[[nucleo-wiki-deterministico-feat003d]] (il nucleo), [[ponte-d-n-host-agnostico]] (il confine + rename),
[[sistema-wiki-fonte-unica]] (la fonte unica + le interfacce). Questa pagina **unifica** e aggiunge la
**roadmap**.

## Principio organizzatore: deterministico (D) vs giudizio (N)

Il wiki LLM è diviso da una linea sola: **ciò che è meccanico** (dove/come scrivere, parsing, scan, link)
sta nel **nucleo deterministico** (codice, zero LLM); **ciò che è giudizio** (cosa scrivere, il perché, è
una contraddizione?, è obsoleto?) sta nel **layer agentico** (LLM). Tutto ciò che varia tra progetti vive
in **una sola config** (`wiki.config.toml`) — host-agnosticità, **Principio X**. Vedi [[constitution]].

## Architettura a strati

```
            wiki.config.toml          ← UNICA fonte di specificità dell'ospite (Principio X)
            (root · tassonomia · frontmatter · source_dirs · [roles] · [rag] · strings · language)
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  NUCLEO DETERMINISTICO — sertor_core.wiki_tools (FEAT-003-D) ✅    │   MECCANICO (D)
│  CLI `sertor-wiki-tools`:  scan · structure · validate · lint ·    │   zero LLM · offline ·
│    collect · index · append-log · migrate · upsert-index          │   idempotente · errori espliciti
│  contratti JSON versionati: wiki.scan/1 · wiki.lint/1 · …          │
└──────────────────────────────────────────────────────────────────┘
                   ▲  chiama per il meccanico (via Bash)
                   │
┌──────────────────────────────────────────────────────────────────┐
│  LAYER AGENTICO — 4 entità host-agnostiche (leggono la config)    │   GIUDIZIO (N)
│   ▸ wiki-playbook.md   indice + moduli ops/ + page-craft          │
│   ▸ wiki-author (skill)     autore: genera/aggiorna dal repo       │
│   ▸ /wiki (comando)         dispatcher manuale, flusso principale  │
│   ▸ wiki-curator (agente Haiku, +Bash)   bookkeeping in background │
└──────────────────────────────────────────────────────────────────┘
                   ▲  promemoria (NON orchestrano: un hook non avvia un agente)
                   │
┌──────────────────────────────────────────────────────────────────┐
│  HOOK   SessionStart → carica indice+log   ·   Stop/SessionEnd →   │
│         systemMessage "lavoro non registrato" (non bloccante)      │
└──────────────────────────────────────────────────────────────────┘
```

## Il confine D↔N, per operazione

Ogni operazione del playbook applica il [[deterministic-vs-judgment|confine deterministico↔giudizio]]:
separa il meccanico (chiamata CLI) dal giudizio (LLM). Sintesi (tabella completa in [[ponte-d-n-host-agnostico]]):

```
operazione            D — meccanico (CLI)              N — giudizio (LLM)
─────────────────────────────────────────────────────────────────────────────
record                collect                          perché · corpo · backlink · nuova-vs-aggiorna
distill               collect                          quali entità estrarre · cosa assottigliare  ← N2
ingest                collect · lint                   riassunto · contraddizioni
query                 collect · index (RAG)            risposta · se archiviare
lint  (A strutturale) lint · validate = 100% D         —
lint  (B semantico)   baseline + ground truth          è davvero una deriva?  ← N5
lint  (C organizzativo) collect (+ backlink invertiti) natura·collocazione·atomicità?  ← N9
reorg                 move via Edit · lint post-move   cosa spostare/dove/splittare  ← N9
generate-from-diff    scan · git(→VCS)                 pagine impattate · update
rag-sync              index = 100% D                   —
structure             structure init = 100% D          —
```

Nota: i **write-back** sono **entrambi cablati in CLI** — il log con `append-log` (FEAT-008, rotazione
giornaliera) e la riga d'indice con `upsert-index` (feature 010, `specs/010`): l'LLM **autora** il corpo
curato / il sommario, il codice fa il **piazzamento idempotente**. Sfumatura onesta sull'indice: la CLI
scrive la riga **piatta** (wikilink della pagina + lineetta + sommario), mentre l'`index.md` di Sertor è
*curato* (grassetti, sezioni per area) — sull'indice curato il giudizio resta quindi all'LLM, che può
usare la CLI come write-back accettandone il formato o continuare ad autorare la riga.

## Il lint a tre livelli (N5 + N9)

```
A) strutturale   → sertor-wiki-tools lint + validate    (D, autorevole sui link)
B) semantico     → claim ↔ realtà del repo (codice/test/git)             (N · N5)
   (giudizio,       baseline → estrai claim → ground truth (git→VCS · RAG/Read/Grep · pytest)
    flusso          → confronta → report con severità → correggi su conferma
    principale,     esteso il 2026-06-06 ad audit globale su 4 kind (wiki/requirements/spec/tracker)
    NON Haiku)
C) organizzativo → collocazione · atomicità · type↔natura · disciplina link  (N · N9)
                    detection via collect + backlink invertiti; applica con `reorg` su conferma
```
Host-agnostico: i probe degradano per profilo (solo-doc → niente probe di codice; il RAG è acceleratore
se c'è, mai prerequisito). Esercitati su contenuti reali: B → derive corrette (2026-06-05/06); C → reorg
del 2026-06-06 (`syntheses/` da 16/20 a una distribuzione 4/3/9/4). Dettagli:
[[lint-semantico-host-agnostico]] · [[lint-organizzativo-e-reorg]].

## Stato attuale

| Pezzo | Stato |
|---|---|
| Nucleo deterministico `wiki_tools` (FEAT-003-D) | ✅ mergiato (PR #13) |
| Ponte D→N (layer agentico host-agnostico + rename author/curator) | ✅ mergiato (PR #14) |
| Fix hook Stop (systemMessage schema-valido) | ✅ mergiato (PR #14) |
| [[server-mcp-produzione-feat-mcp|`sertor_mcp`]] (RAG dell'ospite, FEAT-MCP) | ✅ mergiato (PR #15); `.mcp.json` ri-puntato alla produzione (corpus `sertor`) |
| N5 lint semantico — metodo + audit globale 4 `kind` (PR #16) | ◑ in corso (metodo sì, esercitato; probe deterministici no) |
| N9 lint organizzativo + `reorg` — metodo + esercitato (reorg 2026-06-06) | ◑ in corso |
| N1 record-contenuto — metodo «livello di significato» (page-craft) | ◑ in corso (metodo sì, da esercitare) |
| N2 distillazione — operazione `distill` + standing nel rituale (esercitata su FEAT-001, 2026-06-08) | ✅ fatto |
| N8 orchestrazione/trigger (`generate-from-diff` + `/wiki`) | ✅ completa come procedura (2026-06-09, D-19) |
| N7 gate al commit | ⛔ deleted by design (2026-06-09, D-20) |
| Pezzi codice D residui: **query congiunta multi-collezione** + **`upsert-index` in CLI** (feature 010) | ✅ implementati (2026-06-10, PR #20 — record: [[spec-010-query-congiunta-e-upsert-index]]) |
| N3, N4 (ingest→`sources/`), N6 (operazioni di giudizio) | ☐ da fare |

## Roadmap

Grafo delle dipendenze (cosa sblocca cosa):

```
✅ FEAT-003-D ─► ✅ Ponte D→N ─► ◑ N5 lint (metodo)
                       │
                       ├─► ✅ 1a  Scope completo (write-back index in CLI, feature 010) ─► N1 record (offload pieno)
                       ├─► ✅ 2a  FR-004 trigger RISOLTO (D-19: comando manuale /wiki) ─► ✅ N8 generate-from-diff (procedura)
                       ├─► 3   Operazioni di contenuto: N1 · N2(✅) · N3 · N4(ingest→sources/, D-18)
                       ├─► 4   N6 verità/autorità/obsolescenza · ⛔ N7 gate ELIMINATO (D-20)
                       └─► ✅ 5a sertor_mcp (PR #15) + indice corpus `sertor` COSTRUITO (FEAT-009) → dogfood vivo
```

| # | Evoluzione | Natura | Requisiti? | Priorità | Dipende da |
|---|---|---|---|---|---|
| **5a** | `sertor_mcp` — RAG dell'ospite | **codice** (componente) | ✅ **FATTO** (PR #15, SpecKit completo) | — | — |
| **1a** | Scope completo: write-back in CLI (+ formato index, vedi nota sui write-back) | **codice** (D) | ✅ **FATTO** (feature 010, 2026-06-10: `upsert-index` cablata; sommario resta LLM-authored) | — | — |
| **2a** | FR-004: trigger | **decisione** | ✅ **RISOLTA (2026-06-09, D-19)**: comando manuale `/wiki`, ambito = ultimo commit | — | — |
| **3a** | N1 record-contenuto (autorship) | giudizio (N) | ❌ build, non spec | Media | 1a (migliora) |
| **3b** | N2 distillazione sessione→pagina — operazione `distill` + rituale | giudizio (N) | ✅ **FATTO** (2026-06-08, pilota FEAT-001) | — | — |
| **3c** | N3 generazione dal repo (Karpathy) | giudizio (N) | ❌ build | Bassa | — |
| **3d** | N4 ingest (fonte→riassunto in `sources/`, D-18) | giudizio (N) | ❌ build | Bassa | — |
| **4a** | N6 verità/autorità/obsolescenza | misto (D segnali + N decisione) | ◑ solo metà-D | Bassa | — |
| ~~**4b**~~ | ~~N7 gate al commit~~ | — | ⛔ **DELETED BY DESIGN (2026-06-09, D-20)**: incoerente col trigger manuale post-commit; lint/freschezza restano non bloccanti | — | — |
| **1b** | N5 variante (c): probe deterministici in `wiki_tools` | codice (D) | ◑ EARS-abile, valore incerto | Bassa | N5 |

**Principio di processo** (vedi [[constitution]] e la regola "calibra al valore"): **EARS è il bisturi
sul lato D** (componenti/contratti con "done" testabile, soprattutto `sertor_mcp`); **sul lato N si
costruisce il metodo, non si spec-a** (i requisiti di outcome esistono già in
`requirements/sertor-core/wiki-creazione/requirements.md`).

**Aggiornamento 2026-06-09:** chiuse le decisioni di trigger/scope del wiki — **D-18** (rimossi
`manual_edited/`/`ingested_sources/`; ingest→`sources/`), **D-19** (trigger = comando manuale `/wiki`,
ambito = ultimo commit), **D-20** (gate al commit eliminato). L'indice dogfood `sertor` è **costruito**
(FEAT-009).

**Aggiornamento 2026-06-10:** implementati i **pezzi codice D residui** con la feature 010 (SpecKit
completo, PR #20 — record: [[spec-010-query-congiunta-e-upsert-index]]): la **query congiunta
multi-collezione** (il wiki diventa interrogabile *insieme* al codice via `search_combined`, corpora extra
da `Settings`) e il write-back **`upsert-index` in CLI** (evoluzione 1a). `sertor wiki init` resta
nell'epica CLI. **Prossimo passo raccomandato:** esercitare le operazioni di contenuto N (N3 generazione ·
N4 ingest→`sources/` · N6 verità/obsolescenza).
