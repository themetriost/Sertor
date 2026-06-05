---
title: Architettura del Wiki LLM — stato e roadmap
type: synthesis
tags: [architettura, wiki-llm, host-agnostico, principio-x, roadmap, feat-003, deterministico-vs-giudizio]
created: 2026-06-05
updated: 2026-06-05
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
in **una sola config** (`wiki.config.toml`) — host-agnosticità, **Principio X**. Vedi [[costituzione-v1]].

## Architettura a strati

```
            wiki.config.toml          ← UNICA fonte di specificità dell'ospite (Principio X)
            (root · tassonomia · frontmatter · source_dirs · [roles] · [rag] · strings · language)
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  NUCLEO DETERMINISTICO — sertor_core.wiki_tools (FEAT-003-D) ✅    │   MECCANICO (D)
│  CLI `sertor-wiki-tools`:                                          │   zero LLM · offline ·
│    scan · structure · validate · lint · collect · index           │   idempotente · errori espliciti
│  contratti JSON versionati: wiki.scan/1 · wiki.lint/1 · …          │
└──────────────────────────────────────────────────────────────────┘
                   ▲  chiama per il meccanico (via Bash)
                   │
┌──────────────────────────────────────────────────────────────────┐
│  LAYER AGENTICO — 4 entità host-agnostiche (leggono la config)    │   GIUDIZIO (N)
│   ▸ wiki-playbook.md   fonte unica: regole · tassonomia · 6 op.   │
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

Ogni operazione del playbook separa il meccanico (chiamata CLI) dal giudizio (LLM). Sintesi (tabella
completa in [[ponte-d-n-host-agnostico]]):

```
operazione            D — meccanico (CLI)              N — giudizio (LLM)
─────────────────────────────────────────────────────────────────────────────
record                collect                          perché · corpo · backlink · nuova-vs-aggiorna
ingest                collect · lint                   riassunto · contraddizioni
query                 collect · index (RAG)            risposta · se archiviare
lint  (A strutturale) lint · validate = 100% D         —
lint  (B semantico)   baseline + ground truth          è davvero una deriva?  ← N5
generate-from-diff    scan · git(→VCS)                 pagine impattate · update
rag-sync              index = 100% D                   —
structure             structure init = 100% D          —
```

Nota: i **write-back** (voce di log, riga d'indice) sono **ancora scritti dall'LLM** — la CLI non li
espone e il formato curato non combacia col deterministico. Chiuderlo = evoluzione **1a** (roadmap).

## Il lint a due livelli (N5, metodo formalizzato)

```
A) strutturale  → sertor-wiki-tools lint + validate     (D, autorevole sui link)
B) semantico    → 1. baseline (A)
   (giudizio,      2. estrai claim verificabili dalle pagine
    flusso          3. ground truth:  git→VCS · RAG-ospite o Read/Grep · pytest
    principale,     4. confronta claim ↔ realtà → giudica (deriva?)
    NON Haiku)      5. report con severità (NON auto-fix)
                    6. correggi su conferma  ·  log `lint`
```
Host-agnostico: i probe degradano per profilo (solo-doc → niente probe di codice; il RAG è acceleratore
se c'è, mai prerequisito). Provato il 2026-06-05 → 2 derive reali corrette.

## Stato attuale

| Pezzo | Stato |
|---|---|
| Nucleo deterministico `wiki_tools` (FEAT-003-D) | ✅ mergiato (PR #13) |
| Ponte D→N (layer agentico host-agnostico + rename author/curator) | ✅ mergiato (PR #14) |
| Fix hook Stop (systemMessage schema-valido) | ✅ mergiato (PR #14) |
| N5 lint semantico — metodo documentato (variante b) | ◑ in corso (metodo sì; probe deterministici no) |
| N1-N4, N6-N8 (operazioni di giudizio) | ☐ da fare |
| `sertor_mcp` (RAG dell'ospite) | ☐ da fare (oggi `.mcp.json` punta al prototipo, rotto) |

## Roadmap

Grafo delle dipendenze (cosa sblocca cosa):

```
✅ FEAT-003-D ─► ✅ Ponte D→N ─► ◑ N5 lint (metodo)
                       │
                       ├─► 1a  Scope completo (write-back in CLI + formato index) ─► N1 record (offload pieno)
                       ├─► 2a  FR-004 (trigger: hook/comando/headless) ─────────► N8 orchestrazione
                       ├─► 3   Operazioni di contenuto: N1 · N2 · N3 · N4
                       ├─► 4   N6 verità/autorità/obsolescenza · N7 gate al commit
                       └─► 5a  sertor_mcp (RAG ospite) ─► N5 probe-RAG · dogfood produzione · agente Azure
```

| # | Evoluzione | Natura | Requisiti? | Priorità | Dipende da |
|---|---|---|---|---|---|
| **5a** | `sertor_mcp` — RAG dell'ospite | **codice** (componente) | ✅ **EARS/SpecKit** (massima leva) | Alta | — |
| **1a** | Scope completo: write-back in CLI + riconciliazione formato index | **codice** (D) | ✅ EARS leggero / spec | Media | FEAT-003-D |
| **2a** | FR-004: chiudere il trigger (hook vs comando vs headless) | **decisione** | ❌ (chiude requisito esistente §13) | Media | — |
| **3a** | N1 record-contenuto (autorship) | giudizio (N) | ❌ build, non spec | Media | 1a (migliora) |
| **3b** | N2 distillazione sessione→pagina | giudizio (N) | ❌ build | Media | — |
| **3c** | N3 generazione dal repo (Karpathy) | giudizio (N) | ❌ build | Bassa | — |
| **3d** | N4 ingest compile | giudizio (N) | ❌ build | Bassa | — |
| **4a** | N6 verità/autorità/obsolescenza | misto (D segnali + N decisione) | ◑ solo metà-D | Bassa | — |
| **4b** | N7 gate al commit (human-in-the-loop) | misto | ◑ solo metà-D | Bassa | 2a |
| **1b** | N5 variante (c): probe deterministici in `wiki_tools` | codice (D) | ◑ EARS-abile, valore incerto | Bassa | N5 |

**Principio di processo** (vedi [[costituzione-v1]] e la regola "calibra al valore"): **EARS è il bisturi
sul lato D** (componenti/contratti con "done" testabile, soprattutto `sertor_mcp`); **sul lato N si
costruisce il metodo, non si spec-a** (i requisiti di outcome esistono già in
`requirements/sertor-core/wiki-creazione/requirements.md`).

**Prossimo passo raccomandato:** `requirements` a livello feature su **`sertor_mcp`** (5a) — è l'enabler che
rende "vero" il probe-RAG del lint semantico, abilita il dogfood di produzione e l'entry-point dell'agente.
