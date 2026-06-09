---
title: Step ritual & wiki anti-drift
type: concept
tags: [wiki, automazione, hook, governance, processo, delega, fonte-unica, rituale-di-step]
created: 2026-06-04
updated: 2026-06-09
sources: ["CLAUDE.md", ".claude/skills/wiki-author/wiki-playbook.md", ".claude/agents/wiki-curator.md", ".claude/agents/configuration-manager.md", ".claude/settings.json", ".claude/hooks/wiki-pending-check.ps1"]
---

# Step ritual & wiki anti-drift

Il **rituale di step** è la *Definition of Done* di ogni step significativo: a fine lavoro il flusso
principale, **di propria iniziativa**, registra nel wiki ciò che ha fatto e verifica che il wiki non sia
andato in **deriva** rispetto al repo. Risolve un problema concreto: il wiki di produzione (`wiki/`) **è**
la documentazione del progetto, ma senza un controllo sistematico diverge silenziosamente dalla realtà del
codice. Il *come* della discussione che lo ha originato vive in [[retrospettiva-interazione-2026-06-04]].

## Le due nature di un controllo, e il vincolo degli hook

Ogni controllo di coerenza ha **due nature**, e separarle è la chiave dell'intero design:

- **Meccanico / deterministico** — wikilink rotti, pagine orfane, frontmatter, riferimenti a path/feature
  inesistenti. È uno *script*: un **hook di Claude Code lo esegue da solo**, è automatico nel senso pieno.
- **Semantico / di ragionamento** — «la pagina afferma un comportamento che nel codice non c'è». Richiede
  un **LLM**.

Il vincolo di piattaforma che vincola tutto il resto: un hook è una *shell command fuori dal loop del
modello*. Esegue script (natura 1) ma **non può invocare una skill/subagent in-loop** (natura 2); al
massimo inietta un promemoria, o lancia un processo `claude -p` headless separato (con costi e latenza).
Per questo l'hook esistente `wiki-pending-check.ps1`, basato su `mtime` e git-blind, non può cogliere la
deriva semantica: non ragiona.

## Standing behavior batte unattended

L'intuizione che scioglie il nodo: il flusso principale (Claude) **è un LLM già nel loop**. Scrivere la
voce di log, distillare le entità, fare il lint semantico sono **tutte azioni da LLM**: se l'LLM è già qui
e scrive il log, **non c'è alcun limite tecnico** a fargli fare anche il resto, nello stesso flusso. La
distinzione da tenere ferma:

| | Cosa significa | Chi lo fa | Limite |
|---|---|---|---|
| **Unattended** | scatta senza nessuno (timer/evento) | script in hook · `claude -p` headless · routine schedulata | l'hook non ragiona, non avvia subagent in-loop |
| **Standing** | lo fai sistematicamente mentre lavori | il flusso principale (LLM) | **nessuno** — è già lavoro da loop |

Il rituale è del secondo tipo: per esso non esiste limite tecnico. L'automazione *unattended* (gate
pre-PR, guard su reset/force-push, distillazione dai transcript) resta un **secondo strato** valido ma
separato, che copre i casi «quando non c'è nessuno».

## Il rituale (Definition of Done)

Codificato in `CLAUDE.md`. A fine di ogni step significativo, di propria iniziativa:

1. **Registra** — `record`: appende la voce nel **file del giorno** `wiki/log/<data>.md` (rotazione,
   FEAT-008, via `append-log`) + pagine impattate e `index.md`.
2. **Distilla le entità** — estrai in pagine proprie (`concepts/`/`tech/`) le entità/concetti durevoli che
   lo step ha fatto emergere (operazione `distill`, N2); il record datato resta magro e vi punta.
3. **Lint semantico di allineamento** — confronta il contenuto del wiki con la realtà del repo (`src/`,
   `specs/`, `requirements/`, stato git) e segnala ogni claim contraddetto.
4. **\<altre azioni\>** — lista estendibile: ciò che l'utente chiede di rendere standing si aggiunge qui.

La voce di log **non è posticipabile**: si scrive **nello stesso momento del commit** dello step.

## Confine di delega: trascrizione vs giudizio

La delega esiste per **non bloccare il flusso**, non per saltare il rituale. Due azioni, due regole:

| Azione | Natura | Delega | Perché |
|--------|--------|--------|--------|
| **record** | trascrizione strutturata (brief → pagine, backlink, index, voce log) | ✅ `wiki-curator` (Haiku) | lavoro di forma, retto dal brief; meno costoso |
| **distill** + **lint semantico** | giudizio sui contenuti (cosa estrarre · wiki ↔ codice/repo) | ❌ flusso principale (Opus) | richiede il contesto dello step; un agente lo rileggerebbe a freddo (più costoso e lossy) |

Quindi: la trascrizione si delega a Haiku; **giudizio e riconciliazione wiki↔repo restano in casa**. Se in
casi pesanti il giudizio va proprio delegato, si usa un override `sonnet` per-invocazione, **mai** il
default Haiku. Git si delega al `configuration-manager`. Gli hook restano promemoria vincolanti.

**Calibra al valore:** lo step innesca il rituale solo quando è *significativo* (produce conoscenza,
decisioni o codice); modifiche puramente meccaniche non lo richiedono.

## Fonte unica = CLAUDE.md

La versione **operativa** del rituale (autorità che l'LLM legge a ogni step) vive in `CLAUDE.md` e **solo
lì**, finché il rituale evolve. Il motivo è la sua natura *standing*: un'azione che deve avvenire a ogni
step non può risiedere in un asset (plugin/skill) che **non è garantito in contesto** — solo `CLAUDE.md` è
iniettato sistematicamente. Mantenere una seconda copia "portabile" in parallelo creerebbe due autorità da
sincronizzare a mano, cioè una nuova fonte di deriva. *Backlog differito:* riesportare il rituale come
plugin repository-agnostico **quando sarà stabile** (coerente col goal toolset enterprise).

## Vedi anche
- `CLAUDE.md` → sezione *Rituale di step / Definition of Done* (la regola operativa).
- [[retrospettiva-interazione-2026-06-04]] — il *come* della conversazione che ha originato il rituale.
- [[lint-organizzativo-e-reorg]] — il lint livello C, anti-deriva sull'organizzazione del wiki.
- [[sistema-wiki-fonte-unica]] — il sistema wiki di cui il rituale è la disciplina d'uso.
- [[sessionstart-hook]] — l'hook che inietta lo stato del wiki a inizio sessione.
- [[deterministic-vs-judgment]] — il confine D↔N che governa cosa si delega.
