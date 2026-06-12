---
title: FEAT-007 — Elicitazione e gap analysis (manutenzione wiki)
type: experiment
tags: [feat-007, manutenzione, wiki, gap-analysis, requirements]
created: 2026-06-12
updated: 2026-06-12
sources: ["requirements/sertor-core/manutenzione-wiki/requirements.md"]
---

# FEAT-007 — Elicitazione e gap analysis (manutenzione wiki)

**Data:** 2026-06-12  
**Operazione:** record (elicitazione + gap analysis + decisioni)  
**Stato:** Completato — 4 domande aperte risolte; requirements finalizzati (22 REQ residui); prossimo passo `/speckit-specify` (branch 015)

## Contesto

FEAT-007 appartiene all'epica `sertor-core`: è la **manutenzione del wiki** come capacità. L'epica aveva elicitato una **dote dichiarata** nel backlog; questo record cattura l'**analisi del gap** (cosa esiste già vs. cosa manca) e le **decisioni risolte** con l'utente sulla base dell'analisi.

## Gap analysis — Cosa esiste già

Quattro aree della dote dichiarata sono **già coperte al 100%** (metodo documentato, giudizio esercitato):

- **Lint semantico (N5):** metodo ripetibile documentato in `wiki-playbook.md` §5 e esercitato quotidianamente nel rituale di step (punto 3 di `CLAUDE.md`). Validazione: le 3 derive trovate il 2026-06-12 in PR #24/25 (docstring MCP, README core, blocco architettura CLAUDE.md) sono state corrette via lint B manuale.
- **Lint organizzativo/reorg (N9):** metodo documentato in `wiki-playbook.md`, `lint-organizzativo-e-reorg.md` e `page-craft.md`. Validazione: 2026-06-06 reorg su `syntheses/` (16→4 pagine in `experiments/`, 9 in `concepts/`, 4 in `tech/`), 0 link rotti post-reorg.
- **Campo `status` in frontmatter:** già tra i campi opzionali di `frontmatter_optional` nel template `wiki.config.toml.tmpl`.
- **Contratti JSON versionati:** sistema `wiki.<op>/<ver>` già in atto per `lint`, `collect`, `structure`, `append-log`, `migrate`.

## Decisioni risolte (D1..D4)

### D1 — Probe di freschezza: ELIMINATO (Won't)

**Decisione:** Eliminare il gruppo A (REQ-001..006) della dote.

**Motivazione (confermata dall'analisi):**
- **Falsi positivi strutturali:** i `sources` larghi (`src/**`, `specs/**`) verrebbero toccati a ogni feature; il probe li segnalerebbe come "stale" sebbene le pagine che li linkano restino accurate.
- **Il lint B del rituale è migliore:** il flusso principale, nel contesto dello step, sa esattamente cosa è cambiato e quali pagine dipendono da quel cambio. Un diff di timestamp a freddo non batte questa informazione.
- **Non copre i doc di repo:** il probe non avrebbe rilevato le 3 derive effettive trovate il 2026-06-12 (docstring, README, CLAUDE.md), che vivono fuori dal frontmatter del wiki.

**Conseguenza:** la **detection del `reconcile`** si regge su solo `status: superseded` (esplicito, zero falsi positivi).

### D2 — Trigger periodico `reconcile`: Rimandato (Could)

**Decisione:** REQ-028 resta **Could**; la forma preferita è **documentazione d'uso + delega all'ambiente ospite** (cron, hook CI, task scheduler).

**Motivazione:** `reconcile` è già un comando deterministico e sicuro; la **schedulazione** è compito dell'ambiente ospite, non di `wiki_tools` (Principio X: host-agnosticità). Non si deve assumere un ambiente di esecuzione.

### D3 — Fonte dei seed localizzati: Tabella di localizzazione in modulo

**Decisione:** I seed di `structure init` (~4 frasi) vivono in una **tabella di localizzazione in modulo dedicato** (`locales`), non in file-risorsa per-lingua.

**Motivazione (dall'analisi):** il volume reale è piccolo (~4 frasi per lingua); un modulo con dizionario `it → strings` e `en → strings` è **YAGNI** rispetto a file-risorsa. Evoluzione futura (override via `[strings]` in config): Could, non richiesta ora.

### D4 — Tema lingua degli asset installer: INGLESE canonico unico

**Decisione:** Gli asset distribuiti (`blocco-rituale.md`, skill, playbook, agente, comando) migrano a **INGLESE canonico unico**. La **manopola `language`** della config governa la lingua del **CONTENUTO** che il sistema produce sull'ospite (seed, pagine, log), **non** la lingua degli asset.

**Motivazione (decisione utente):**
- Nessuna variante per-lingua da mantenere → zero drift ×2 sulla metodologia viva.
- Trasparente: l'asset in inglese **istruisce** l'agente a scrivere nella lingua configurata.

**Implicazione dichiarata:**
- Il `.claude/` di Sertor (derivato dagli asset, test di sync anti-drift) diventerà inglese.
- Il wiki interno di Sertor resta italiano (`language=it` nel `wiki.config.toml`).
- Coordinamento verso FEAT-012 (installer): la traduzione one-time degli asset è compito dell'epica CLI.

## Perimetro finale

**22 REQ residui (21 Should + 1 Could):** *(B=6 + C=7 con REQ-021 incluso + D=1 + E=5 + F=3)*

| Gruppo | ID | Cosa | Classificazione |
|--------|-----|------|---|
| A | REQ-001..006 | Probe di freschezza | ❌ Won't (eliminato) |
| B | REQ-010..015 | Comando `move`-con-link | Should |
| C | REQ-020..027 (no 024) | `reconcile` detection read-only | Should |
| D | REQ-028 | Trigger periodico | Could |
| E | REQ-030..034 | Seed localizzati it/en | Should |
| F | REQ-035..037 | Asset installer in EN canonico | Should (coordinamento FEAT-012) |
| Ext. | REQ-021 | Campo `status` in `collect` | Should (prerequisito `reconcile`) |

**Capacità deterministiche (D):**
- `sertor-wiki-tools move` (dry-run, idempotente)
- `sertor-wiki-tools reconcile` (detection, read-only)
- `collect` con campo `status`
- `structure init` con seed localizzati (tabella modulo)

## Prossimi passi

1. **`/speckit-specify`** (branch 015): creazione spec FEAT-007.
2. **Coordinamento FEAT-012 (installer):** traduzione asset, test di sync anti-drift.
3. **Re-index corpus `sertor`** una volta mergiata la feature (come da rituale standing).

---

**Ultimo aggiornamento:** 2026-06-12 (voce di log appesa, requirements doc finalizzato).
