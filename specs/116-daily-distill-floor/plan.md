# Implementation Plan: Daily distill floor (≥1 distill/giorno)

**Branch**: `116-daily-distill-floor` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: `specs/116-daily-distill-floor/spec.md` · requisiti EARS
`requirements/debito-tecnico/daily-distill-floor/requirements.md` (E10-FEAT-039).

## Summary

Dare al passo `distill` del rituale wiki una **rete di sicurezza** pari a quella di `record`, così che
ogni giornata attiva chiuda con ≥1 distillazione *dichiarata*. Tre meccanismi coesi + una regola:
1. **`distill-audit`** — nuovo sotto-comando deterministico di `sertor-wiki-tools` che scandisce **tutto
   il corpus** (content pages + partizioni di log, cross-sessione — NON git-diff) e riporta le **entità
   referenziate da ≥k punti senza pagina propria** via due segnali strutturali: **wikilink penzolanti**
   (`[[x]]` senza pagina) + **prosa in backtick** (identificatori `` `x` `` frequenti senza pagina),
   producendo un **debito N** + lista candidati. Contratto `wiki.distill_audit/1`.
2. **Hook `distill-floor`** — nuovo asset host-facing, persistente su `SessionStart` + `Stop`/`SessionEnd`
   (come `wiki-pending-check`): se la giornata non ha una voce `distill` nel log **e** N>0, sollecita
   (non-bloccante) nominando debito e top candidati; si auto-silenzia appena la giornata ha una voce
   `distill`; N=0 → mai. Once-per-day: l'audit costoso è cachato in `.sertor/.distill-floor.json`.
3. **Il «no» costa** — contratto host-facing (blocco `SERTOR:WIKI-RITUAL` + playbook): un «distill: non
   necessario» va **registrato come voce di log `distill`** che nomina i candidati considerati; così il
   pavimento è soddisfatto da una distillazione reale **o** da un «no» costato (l'hook vede la stessa
   voce), e un «no» a costo zero non esiste più.
4. **Regola standing** «≥1 distill per giornata attiva» + debito N come metrica leggera.

Confine D↔N: il tool **trova** (deterministico, zero-LLM, sola lettura), l'agente **giudica** (distilla o
scrive un «no» motivato), l'hook **annuncia+esige** (non giudica, non blocca — limite onesto).

## Technical Context

**Language/Version**: Python ≥3.11 (core `sertor-core`); hook stdlib-only (interprete ambiente via `uv run`).

**Primary Dependencies**: nessuna nuova. Riuso di `wiki_tools` (`iter_pages`, `extract_wikilinks`,
`_link_aliases`, `parse_frontmatter`, `WikiProfile`, `contracts`, `log_event`). Hook: `_hooklib` +
subprocess sulla CLI vehicle (Principio XI).

**Storage**: file wiki (sola lettura per l'audit); cache once-per-day `.sertor/.distill-floor.json`
(scritta solo dall'hook, best-effort). Nessun DB.

**Testing**: pytest (unit F.I.R.S.T., offline). Nuovi test: `tests/unit/test_distill_audit.py` (tool),
`packages/sertor/tests/…` per l'hook (parità Claude/Copilot, come `test_portable_hooks_parity.py`), guardie
sync/asset.

**Target Platform**: qualunque host con la capacità wiki (Windows/macOS/Linux); hook portabile stdlib.

**Project Type**: libreria + CLI (`sertor-core`) + asset host-facing (installer `packages/sertor`).

**Performance Goals**: audit dell'intero corpus veloce (scan lineare dei `.md`); once-per-day cache evita
il riscan a ogni turno (NFR-5).

**Constraints**: zero-LLM, offline, deterministico, sola lettura (tool); hook non-bloccante (exit 0 sempre),
host-agnostico (config da `wiki.config.toml`).

**Scale/Scope**: corpus wiki tipico (10²–10³ pagine); il dogfood ha ~1400 doc indicizzati.

## Constitution Check

*GATE — costituzione v1.4.0. Tutti marcati PASS.*

- [x] **I — Dipendenze verso l'interno:** PASS — il tool vive in `sertor_core.wiki_tools`, nessun SDK
  provider, nessun import della CLI; l'hook è un **asset** (non core) e consuma la CLI. Core esercitabile
  senza cloud/CLI (unit test diretti sul tool, Principio V).
- [x] **II — Boundary & local-first:** PASS — nessuna dipendenza esterna; il tool è puro I/O su file locali.
- [x] **III — YAGNI & unità piccole:** PASS — riuso dei primitivi esistenti (`iter_pages`,
  `extract_wikilinks`, alias); nessuna nuova dipendenza; il segnale-prosa è una **regola fissa** (backtick +
  stopword), **non** NLP/embedding (YAGNI). Funzioni piccole, guard-clause.
- [x] **IV — Errori espliciti:** PASS — scope indeterminabile/corpus illeggibile → errore esplicito, **mai**
  `debt=0` silenzioso (Principio XII gemello); nessuno stato parziale (sola lettura).
- [x] **V — Testabilità & misure:** PASS — unit F.I.R.S.T. deterministici; SC-001/002 misurabili (nessun
  falso negativo sui wikilink penzolanti; determinismo + no-write). Retrieval hit@k/MRR **N/A** (non è una
  feature di retrieval).
- [x] **VI — Idempotenza & non-distruttività:** PASS — audit **sola lettura** (SC-002: due run identici,
  0 file toccati); l'hook non muta contenuto (solo la cache `.sertor/`); nessuna sovrascrittura silenziosa.
- [x] **VII — Leggibilità:** PASS — vocabolario di dominio (`audit`/`candidate`/`debt`/`floor`).
- [x] **VIII — Config centralizzata:** PASS — soglia k, stopword, scope da `[ritual]`/config; nessun default
  host hardcoded nel corpo (i default di *campo* generici sono ammessi, come per `ritual-check`).
- [x] **IX — Osservabilità:** PASS — il tool emette `log_event` (`distill_audit`, debito, candidati);
  l'hook scrive il breadcrumb fail-loud su errore CLI. Nessun segreto nei log.
- [x] **X — Host-agnostico:** PASS — config da `wiki.config.toml`, nessun path fisso; l'hook risolve la root
  da `CLAUDE_PROJECT_DIR`; distribuito agli ospiti. Test: gira su un host diverso senza modifiche al corpo.
- [x] **XI — Consumo via vehicles:** PASS — l'hook consuma `sertor-wiki-tools distill-audit` (CLI), **mai**
  importa `sertor_core`; l'agente usa l'output della CLI/hook. Test = eccezione (esercita il tool diretto).
- [x] **XII — Fail Loud, Fix the Cause:** PASS — la feature **È** un meccanismo Fail-Loud: rende visibile lo
  skip silenzioso di `distill` (il buco di 5 settimane). Il tool fallisce esplicito su scope indeterminabile;
  l'hook segnala via breadcrumb + exit 0 (degradazione che *segnala*, non silenzio). Nessuna capacità
  disattivata per schivare l'errore.
- [x] **Allineamento alla missione:** PASS — il wiki è la **metà-doc** della fusione code+doc; uno strato
  distillato più ricco migliora **direttamente** la qualità del retrieval-doc reso all'agente (concetti
  navigabili invece che conoscenza sepolta nel diario) e la sua freschezza. Non è un concern periferico:
  è la salute del corpus che l'agente interroga.

*Re-check post-design (Phase 1): invariato — nessuna violazione introdotta dal data-model/contratti.*

## Project Structure

### Documentation (this feature)

```text
specs/116-daily-distill-floor/
├── plan.md              # questo file
├── research.md          # decisioni (DA-1..5 sciolte)
├── spec.md              # user scenarios + requisiti
├── checklists/requirements.md
└── tasks.md             # (fase /speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── distill_audit.py         # NUOVO — audit cross-sessione deterministico (debt N + candidati)
├── contracts.py             # + DistillAuditResult (wiki.distill_audit/1)
└── __main__.py              # + op "distill-audit" (dispatch + human summary + --threshold)

packages/sertor/src/sertor_installer/assets/
├── claude/hooks/distill-floor.py     # NUOVO — hook pavimento (SessionStart/Stop/SessionEnd)
├── claude/settings*.json             # + wiring distill-floor sui 3 eventi
└── ... (copilot hooks spec + claude-md-block wiki + playbook)

tests/unit/test_distill_audit.py                      # NUOVO — tool
packages/sertor/tests/…                               # hook parità + wiring + sync guards
```

**Structure Decision**: estensione della capacità wiki esistente (`sertor_core.wiki_tools` + asset
installer), stesso pattern di `ritual-check` (FEAT-026, tool) e `wiki-pending-check`/`rag-freshness` (hook).
Il tool è complementare a `ritual-check` (git-diff per lo step) — **non lo sostituisce** (scope diverso:
corpus vs step).

## Complexity Tracking

*Nessuna violazione da giustificare — Constitution Check 12/12 + missione PASS.*
