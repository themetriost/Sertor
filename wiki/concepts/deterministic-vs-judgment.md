---
title: Deterministic vs judgment
type: concept
tags: [deterministico, giudizio, confine, delega, architettura, host-agnostico, llm]
created: 2026-06-07
updated: 2026-06-07
sources: ["CLAUDE.md", ".claude/skills/wiki-author/wiki-playbook.md", "src/sertor_core/wiki_tools/**"]
---

# Deterministic vs judgment

Il **confine deterministico↔giudizio** è il principio con cui Sertor separa ciò che è **meccanico**
(calcolabile da codice: deterministico, offline, testabile, **zero LLM**) da ciò che richiede **giudizio**
(un LLM: *cosa* scrivere, *è davvero* una contraddizione?, *dove* collocare una pagina). Ogni capacità è
progettata mettendo il più possibile nel deterministico e riservando all'LLM **solo** il giudizio.

## Come si traccia il confine

La domanda discriminante: *posso calcolarlo senza interpretare il significato?*
- **Sì → deterministico (codice).** Parsing, conteggi, link rotti, scansione mtime, re-index: hanno un
  output ripetibile e verificabile, indipendente dal contenuto.
- **No → giudizio (LLM).** Distillare il *perché*, decidere se due claim si contraddicono, scegliere l'area
  di una pagina per natura: dipendono dal *senso*, non dalla forma.

## Dove si manifesta

- **Nel wiki:** il nucleo deterministico [[nucleo-wiki-deterministico-feat003d|`wiki_tools`]] fa il meccanico
  (scan, lint **A**, collect, index); all'LLM restano il contenuto, il [[lint-semantico-host-agnostico|lint
  semantico (B)]] e il [[lint-organizzativo-e-reorg|lint organizzativo (C)]]. La separazione è il cuore di
  [[architettura-wiki-llm]] e del ponte [[ponte-d-n-host-agnostico|D→N]].
- **Nella delega:** il meccanico si **delega** (il bookkeeping del wiki a un agente curatore, le operazioni
  git a un agente VCS); il giudizio **resta al flusso principale**. È la stessa linea del
  [[rituale-step-e-allineamento-wiki|rituale di step]].

## Perché

Il deterministico è **economico, ripetibile e verificabile**; isolarlo dal giudizio riduce costo ed errore,
rende il comportamento testabile senza LLM, e mantiene la capacità **portabile** (il meccanico non dipende
da un host LLM specifico). All'LLM si chiede solo ciò che solo un LLM può fare.

## Vedi anche
- Applicazioni: [[architettura-wiki-llm]] · [[ponte-d-n-host-agnostico]] · [[rituale-step-e-allineamento-wiki]].
