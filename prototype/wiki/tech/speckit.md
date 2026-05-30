---
title: SpecKit — Governance e Orchestrazione di Progetto
type: tech
tags: [governance, workflow, phase-gates, multi-agent, configuration-manager]
created: 2026-05-29
updated: 2026-05-29
sources: [".claude/agents/speckit-*.md", ".claude/skills/speckit-*/SKILL.md", "CLAUDE.md"]
---

# SpecKit — Framework di Governance

## Cos'è SpecKit

**SpecKit** è un framework di governanza **generalist** (non specifico RAG) che introduce **phase-gates strutturate**
per il progetto: ogni feature/task passa attraverso fasi canoniche (Constitution → Specify → Clarify → Plan → Tasks →
Analyze → Checklist → Implement → TasksToIssues) con **agenti esecutori** dedicati (subagent in `.claude/agents/`)
**fedeli a skill canonici** in `.claude/skills/speckit-*/SKILL.md`.

## Architettura: Agenti SpecKit nel workspace

Ogni fase ha un **subagent dedicato** (Haiku per ausiliarie, Sonnet per sostanziali):

| Fase | Agente | Modello | Ruolo |
|------|--------|---------|-------|
| **Constitution** | `speckit-constitution` | Sonnet | Analizza il brief, estrae principi, decide scope/arch |
| **Specify** | `speckit-specify` | Sonnet | Converte feature in spec (COSA/PERCHÉ, tech-agnostica) |
| **Clarify** | `speckit-clarify` | Sonnet | Risolve ambiguità, valida spec contro domande critiche |
| **Plan** | `speckit-plan` | Sonnet | Roadmap tappe, sequenziamento, dipendenze; MCP `sertor-rag` per codebase analysis |
| **Tasks** | `speckit-tasks` | Sonnet | Task breakdown, stime, assegnazione; MCP `sertor-rag` per contesto |
| **Analyze** | `speckit-analyze` | Sonnet | SOLA LETTURA — audit design, contraddizioni, copertura; MCP `sertor-rag` read-only |
| **Checklist** | `speckit-checklist` | Haiku | Valida spec/task/impl contro checklist di qualità |
| **Implement** | `speckit-implement` | Sonnet | Gate finale: autorizza esecuzione manuale, segnala gate critici |
| **TasksToIssues** | `speckit-taskstoissues` | Haiku | Converte task in GitHub issues (quando richiesto) |

## Principi di Design

### Fedeltà a Skill Canonici
Ogni agente **non duplica il suo skill canonico**: il system prompt rimanda a `.claude/skills/speckit-<fase>/SKILL.md`
e lo esegue. Le note aggiungono solo **adattamenti al workspace** (es. CLAUDE.md policy, convenzioni git/wiki).
→ **Evita drift** tra skill e implementazione; aggiornamento del skill riflette automaticamente.

### Git: Delegato al configuration-manager
**Mai** eseguire git negli agenti (nemmeno git commit per step piccoli/meccanici). I briefing di commit tornano
nel report e sono gestiti da `configuration-manager` (modello Haiku).
→ Coerente con policy prototipo→produzione: prototipo = push diretti master (autorizzati), produzione = branch/PR.

### Niente Interazione Diretta
Gli agenti **non aspettano** l'utente; usano default ragionevoli documentati in *Assumptions*. Le decisioni
critiche (`[NEEDS CLARIFICATION]`) tornano nel report formattate (tabella opzioni A/B/C) per il flusso principale.
→ Mantiene il flusso non-bloccante, allineato con la delega implicita di CLAUDE.md.

### Dogfooding via MCP sertor-rag
**speckit-plan, speckit-analyze, speckit-implement** hanno i tool MCP `sertor-rag` (search_code, search_docs,
search_combined, find_symbol, who_calls, related_docs) per studiare la codebase Sertor stessa durante il planning.
speckit-analyze è **sola lettura** (no Write/Edit).
→ Applica il RAG che stiamo costruendo ai problemi di questo progetto.

## Flusso Operativo (Prototipo → Produzione)

```
Brief utente
      ↓
  /speckit-constitution (analizza principi)
      ↓
  /speckit-specify (crea spec, checklist)
      ↓
  /speckit-clarify (risolve [NEEDS CLARIFICATION])
      ↓
  /speckit-plan (roadmap tappe + brief di commit per branch)
      ↓
  /speckit-tasks (task breakdown)
      ↓
  /speckit-analyze (audit design — SOLA LETTURA)
      ↓
  /speckit-checklist (valida checklist di qualità)
      ↓
  /speckit-implement (gate finale, segnala criticità)
      ↓
  configuration-manager (crea branch + staggia + commit)
      ↓
  Sviluppo manuale (codice reale)
      ↓
  /speckit-taskstoissues (opzionale: crea issue GitHub)
```

Nel flusso principale del workspace, gli agenti SpecKit girano **in background** durante o dopo l'esecuzione
di step significativi (feature, fix, refactor), producendo spec + plan + task che guidano il lavoro successivo.
Non bloccano il turno (sono delegati).

## Policy Git Associata

Vedi [[architettura-attuale]] § "Backlog di produzione" e CLAUDE.md § "Git & versionamento":

- **Prototipo attuale** (autorizzato): commit diretto su `master`, ma **delegato a configuration-manager**
  (non eseguire git dentro gli agenti).
- **Transizione a produzione** (futura): branch + PR + review via SpecKit (constitution → plan
  suggerisce branch, configure-manager lo crea, feature-branch governa il lavoro, PR merge finale).

## Integrazione col Wiki

Quando una feature passa attraverso SpecKit:
1. Constitution/Specify generano una **spec** in `specs/<NNN-nome>/`.
2. Al completamento, l'agente **wiki-keeper** (background) aggiorna `wiki/` se rilevante
   (es. creando pagina `wiki/experiments/<NNN-nome>.md` per feature RAG, o `wiki/tech/` per infrastruttura).
3. Voce in `wiki/log.md` con tipo operazione `record` e link alla spec.

## Stato di Adozione nel Workspace

- **2026-05-29**: Creati 9 subagent esecutori fedeli alle skill canoniche di SpecKit.
  Primo tassello della **fase di produzione** (assettizzazione Sertor via SpecKit + dogfooding MCP sertor-rag).
- **Aperto:** integrazione `before_specify` hook (creazione branch automatica); collegamento
  spec ↔ wiki (record voce quando feature si chiude); transizione rami/PR (gate di mercurio per CI/CD).

---

## Vedi Anche

- [[architettura-attuale]] — diagramma as-built e backlog di produzione (caching, SpecKit/branch).
- CLAUDE.md — policy dettagliate su delega git/wiki e convenzioni di codice.
- `.specify/` — directory di configurazione SpecKit (templates, scripts, init options).
