---
title: Lint organizzativo (livello C) e reorg — la terza deriva del wiki
type: synthesis
tags: [lint, organizzazione, reorg, atomicita, collocazione, grafo, anti-deriva, host-agnostico, n9]
created: 2026-06-06
updated: 2026-06-06
sources: [
  ".claude/skills/wiki-author/wiki-playbook.md",
  ".claude/commands/wiki.md",
  "requirements/sertor-core/wiki-llm/TODO.md",
  "wiki.config.toml"
]
---

# Lint organizzativo (livello C) e reorg — la terza deriva del wiki

Il **lint organizzativo** è il terzo livello del lint del wiki: verifica che il wiki sia un **grafo ben
organizzato** (pagine collocate per natura, atomiche, ben linkate), non solo igienicamente sano. Affianca
il lint **A** (strutturale: link rotti/orfani/frontmatter — meccanico) e **B** (semantico: claim ↔ realtà
del repo — [[lint-semantico-host-agnostico]]). L'applicazione delle sue proposte è l'operazione **`reorg`**.

## Le tre categorie di deriva

Un wiki può degradare in tre modi indipendenti; ognuno ha un livello di lint:

| Livello | Cosa controlla | Natura | Esempio di deriva |
|---|---|---|---|
| **A** strutturale | igiene: wikilink rotti, orfani, frontmatter, naming | meccanico (CLI) | un wikilink che punta a una pagina inesistente |
| **B** semantico | i *claim* contraddicono la realtà (codice/test/git) | giudizio (LLM) | "FEAT-X mergiata" mentre è su branch |
| **C** organizzativo | collocazione, atomicità, coerenza `type`↔natura, link | giudizio (LLM) | un record di feature in `syntheses/` |

A e B guardano *correttezza*; C guarda *organizzazione*. I tool meccanici (lint A, hook) controllano
l'igiene ma **non giudicano la collocazione** — per costruzione.

## Perché C è interamente giudizio (non deterministico)

Il nucleo deterministico deriva l'**area** dalla cartella ma legge il **`type`** dal frontmatter senza
validare la coerenza. Si potrebbe pensare a un check meccanico `type == taxonomy[area].type`: **è inutile**.
La deriva organizzativa tiene cartella e `type` **coerenti tra loro mentre entrambi mentono sul contenuto**
(es. un record messo in `syntheses/` con `type: synthesis`: la stringa è coerente, la *natura* no). Stabilire
*cos'è davvero* una pagina è **inerentemente semantico**: nessun confronto di stringhe lo coglie. Per questo
il lint C resta al flusso principale (Opus), **non** si delega all'agente Haiku.

## Un wiki è un grafo, non un albero

Il principio che guida sia la prevenzione sia la correzione: la cartella serve solo a dare a ogni pagina
**una casa**; il valore sta nei **link**. Da qui le regole (codificate nel playbook `wiki-author`):

- **Atomicità** — una pagina = un concetto: si linka meglio, si riusa, si **chunka pulito** per il RAG.
- **Auto-contenimento** — la prima frase definisce il soggetto, perché il RAG recupera la pagina fuori contesto.
- **Collocazione per natura** — l'area si sceglie dalla natura logica (concept/tech/experiment/source/synthesis),
  non dalla fase; `syntheses/` è la categoria più rara, non una discarica.
- **Link densi, inline, bidirezionali** — al punto di menzione, specifici, con backlink.

## Prevenzione e correzione

- **Prevenzione** (al momento della creazione): le regole sopra nell'operazione `record`/`generate` del
  playbook — si crea già nel posto giusto, atomica e linkata.
- **Correzione** (su wiki esistente): `lint` livello C rileva (report con severità, nessun auto-fix); `reorg`
  applica su conferma — sposta, corregge `type`, aggiorna i wikilink entranti, ristruttura l'indice, e
  **verifica l'igiene post-move** con la CLI.

## Esercizio sul wiki reale (2026-06-06)

Prima prova end-to-end. Il lint C ha colto una **tassonomia collassata**: 16/20 pagine in `syntheses/`,
con `concepts/`/`experiments/`/`sources/` vuote e `type: synthesis` semanticamente falso. Il `reorg` ha
spostato 9 record in `experiments/` e 3 fondamenti in `concepts/`, correggendo i `type`. Distribuzione **da
16/0/0/4 a 4/3/9/4** (syntheses/concepts/experiments/tech), `type`↔area coerenti ovunque, **0 link rotti**.

Lezione operativa: il refactoring è **sicuro** perché i wikilink si risolvono per **slug** (il nome-pagina,
non il percorso → indipendenti dalla cartella) e le aree stanno alla stessa profondità (`wiki/<area>/`) —
spostare tra cartelle non tocca né i wikilink né i link relativi verso `requirements/`/`specs/`. Per questo l'helper deterministico di `move`
resta un *nice-to-have*, non un prerequisito.

## Host-agnostico e tracking

Le regole vivono nel playbook (espresse sui nomi-area della config, **Principio X** — vedi [[constitution]]);
nessun path hardcoded. Tracciato come **N9** in `requirements/sertor-core/wiki-llm/TODO.md` (FEAT-003-N,
ancorato a FR-035..038/FEAT-007). È il punto 2 del rituale di step esteso all'organizzazione — vedi
[[step-ritual]] e la mappa in [[architettura-wiki-llm]].
