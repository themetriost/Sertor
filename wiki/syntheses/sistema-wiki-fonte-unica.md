---
title: Sistema Wiki — Fonte Unica + Tre Interfacce
type: synthesis
tags: [wiki, governance, tooling, fonte-unica, architecture]
created: 2026-06-04
updated: 2026-07-23
sources: [".claude/skills/wiki-author/wiki-playbook.md", ".claude/skills/wiki-author/SKILL.md", ".claude/commands/wiki.md", ".claude/agents/wiki-curator.md", ".claude/hooks/wiki-pending-check.py", ".claude/settings.json", "wiki.config.toml", "CLAUDE.md"]
---

# Sistema Wiki — Fonte Unica + Tre Interfacce Sottili

Il wiki di produzione (`wiki/`) è un **LLM Wiki** in stile Karpathy governato da una **fonte unica** di
regole, consumata da **interfacce sottili** che la leggono invece di duplicarla. Il principio organizzatore:
le regole del wiki (identità, tassonomia, convenzioni, operazioni) vivono in **un solo posto**; skill,
comando e agente vi rimandano. Così non c'è divergenza tra tre copie e c'è un solo punto di manutenzione.

## La fonte unica: il playbook modulare

La fonte unica è `.claude/skills/wiki-author/wiki-playbook.md`. Non è un monolite: è un **indice** col
substrato condiviso (host-agnosticità, identità, confine D↔N, tassonomia, convenzioni, voce di log) + una
tabella di dispatch verso **moduli `ops/<operazione>.md`** caricati **on-demand**. Invocare un'operazione
carica il solo modulo che serve — *progressive disclosure* senza duplicare il substrato (DRY) e senza
trasformare le operazioni in skill (che violerebbe il [[constitution|Principio X]]: le skill sono un
costrutto dell'host).

La conoscenza riusabile su *come si scrive una pagina* è estratta in due **pagine-foglia** linkate dai
moduli (non viceversa, così il grafo resta un DAG): `page-craft.md` (anatomia della singola pagina:
struttura, contenuto, livello di significato, link) e `wiki-craft.md` (livello grafo: cosa merita una
pagina, igiene dei link).

## Le 9 operazioni

`record` · `distill` · `ingest` · `query` · `lint` (livelli A/B/C) · `reorg` · `generate` (da-zero ·
da-diff; fino al 2026-06-10 `generate-from-diff`) · `rag-sync` · `structure`. Ciascuna applica il **confine D↔N** ([[deterministic-vs-judgment]]): il
*meccanico* (scan, lint strutturale, collect, index, write-back del log) è delegato alla CLI
**`sertor-wiki-tools`** (nucleo deterministico [[nucleo-wiki-deterministico-feat003d|FEAT-003-D]]);
all'LLM resta il **giudizio** (cosa scrivere, è una contraddizione?, cosa estrarre). Elenco autorevole e
procedura di ogni operazione: il playbook e i suoi moduli `ops/`.

## Le tre interfacce sottili

```
            wiki-playbook.md  (fonte unica: substrato + dispatch → ops/)
                   ▲   ▲   ▲   leggono, non duplicano
        ┌──────────┘   │   └──────────┐
   skill wiki-author   /wiki        agente wiki-curator
   (autore: dal repo   (comando:    (subagent Haiku, in
    scrive le pagine)   selettore    background; legge il
                        operazione)  playbook come 1ª azione)
```

- **Skill `wiki-author`** — l'autore: legge il playbook, poi opera dal repo (operazione tipica `record`).
- **Comando `/wiki`** — il selettore d'operazione nel flusso principale (router verso la skill/playbook).
- **Agente `wiki-curator`** (Haiku) — bookkeeping in background; **non esegue git** (quello va al
  `configuration-manager`).

Tutte e tre sono **host-agnostiche** (Principio X): radice del wiki, tassonomia, frontmatter, ruoli e
cartelle-sorgente vengono da `wiki.config.toml`, non sono assunti.

## Lo strato automatico: gli hook

Quattro hook wiki in `.claude/settings.json` — due **non bloccanti** (delega automatica) e due
**bloccanti** (le reti hard del rituale, che non orchestrano un agente ma *esigono* l'azione):
- **SessionStart** *(non bloccante)* — inietta lo stato del wiki a inizio sessione ([[sessionstart-hook]]).
- **SessionEnd** *(non bloccante)* — `.claude/hooks/wiki-pending-check.py --mode SessionEnd`: euristica
  `mtime` (confronta `src/`/`specs/`/`requirements/`/`.claude/` con l'ultima voce di log) → **promemoria**
  cross-sessione a delegare al `wiki-curator` (guardia `stop_hook_active` anti-loop).
- **Stop** *(bloccante, [[wiki-guard]] E10-FEAT-040)* — `wiki-guard.py`: se la sessione ha fatto lavoro
  indicizzato non registrato, **blocca la chiusura del turno** esigendo record + distill + lint semantico.
  Ha rimpiazzato allo Stop il vecchio nudge `wiki-pending-check` (che resta solo su SessionEnd).
- **PreToolUse** *(bloccante, [[daily-distill-floor]] E10-FEAT-039)* — `distill-floor.py`: **blocca il merge
  di consegna** finché la giornata non ha una voce `distill` nel log.

Le due reti bloccanti danno al rituale — prima affidato alla sola diligenza dell'agente — un **pavimento
deterministico**: `distill-floor` al merge, `wiki-guard` a fine turno.

## Convenzioni e vincoli stabili

- **Il playbook è tooling, non wiki:** vive in `.claude/`, non si indicizza nel RAG del wiki.
- **Tassonomia consolidata in `sources/`:** la tassonomia alternativa a cartelle-input (`manual_edited/`,
  `ingested_sources/`) è stata **rimossa per design** (D-18); le fonti esterne sono riassunte in `sources/`.
- **Idempotenza:** le operazioni sono idempotenti (record su pagina esistente = aggiornamento).
- **Niente auto-correzione:** il `lint` produce report, non fix automatici; si corregge su conferma.
- **Log partizionato:** la voce si scrive nel file del giorno `wiki/log/<data>.md` (rotazione FEAT-008),
  non più in un `wiki/log.md` unico.

## Vedi anche
- [[ponte-d-n-host-agnostico]] — il rename delle 4 entità e il confine D↔N operazione per operazione.
- [[architettura-wiki-llm]] — la vista d'insieme a strati + roadmap del Wiki LLM.
- [[step-ritual]] — la disciplina d'uso che innesca le operazioni a ogni step.
- [[deterministic-vs-judgment]] — il confine che decide cosa è CLI e cosa è giudizio.
