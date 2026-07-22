# Implementation Plan: hook wiki SessionStart host-agnostico (E10-FEAT-029)

**Branch**: `117-feat-029-wiki-hook-host-agnostic` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

## Summary

Bug fix host-facing: `wiki-session-start.py` hardcoda i path della direttiva SessionStart → viola Principio
X. Fix: la direttiva è **config-driven** (legge `root`/`index_file`/`log_dir` + l'opt-in `[ritual].exec_page`
da `wiki.config.toml`) e **degrada** (solo file esistenti). La roadmap/EXEC diventa opt-in via `exec_page`
(il dogfood lo setta → comportamento preservato; un ospite generico non ce l'ha → direttiva generica). Il
prompt Copilot statico reso generico. Riusa il pattern `tomllib` già in `distill-floor.py` (FEAT-039).

## Technical Context
**Language**: Python (hook stdlib-only). **Deps**: nessuna nuova (`tomllib` stdlib). **Target**: ogni host
con la capacità wiki (Claude/Copilot). **Constraints**: host-agnostico, stdlib-only, non-bloccante (exit 0).

## Constitution Check *(GATE — costituzione v1.4.0, tutti PASS)*

- [x] **I — Dipendenze verso l'interno:** PASS — il fix è negli **asset** (`packages/sertor`) + una helper
  in `_hooklib`; nessun SDK. `sertor-core` engine invariato; solo `wiki.config.toml` dogfood (dato, non codice).
- [x] **II — Boundary & local-first:** PASS — nessuna dipendenza esterna; I/O locale.
- [x] **III — YAGNI & unità piccole:** PASS — riuso del pattern `tomllib`/config di `distill-floor.py`; helper
  `_hooklib.wiki_config` condiviso; funzioni piccole, guard-clause.
- [x] **IV — Errori espliciti:** PASS — config illeggibile → `None` esplicito → hook degrada (no stato parziale).
- [x] **V — Testabilità & misure:** PASS — 7 test parità + smoke aggiornato (config-driven, host-agnostico,
  degradazione, exec_page opt-in, no-config). Retrieval hit@k **N/A** (non è retrieval).
- [x] **VI — Idempotenza & non-distruttività:** PASS — sola lettura; nessuna scrittura sul wiki.
- [x] **VII — Leggibilità:** PASS — `_directive`/`_latest_log`/`wiki_config` intention-revealing.
- [x] **VIII — Config centralizzata:** PASS — **è il cuore del fix**: i path vengono dalla config, non
  hardcodati.
- [x] **IX — Osservabilità:** PASS — il fail-safe runner scrive il breadcrumb; exit 0 sempre.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** PASS — **è il requisito**: gira su un host con `root≠"wiki"`
  senza modifiche al corpo (guardia `test_wiki_session_start_host_agnostic_root`). Il dogfooding non
  giustifica più i letterali.
- [x] **XI — Consumo via vehicles:** PASS — l'hook è un asset che legge un file di config (non importa
  `sertor_core`); resta consumatore, non libreria.
- [x] **XII — Fail Loud, Fix the Cause:** PASS — rimuove la **causa** (path hardcoded), non la aggira;
  degradazione che *non* ordina letture fallite (early feedback pulito); breadcrumb su config illeggibile.
- [x] **Allineamento alla missione:** PASS — il SessionStart carica il corpus wiki (metà-doc della fusione
  code+doc) in modo corretto su **qualunque** ospite; senza il fix, un ospite riceve contesto sbagliato
  (path inesistenti) — degrada la qualità del contesto reso all'agente.

*Nessuna violazione → nessun Complexity Tracking.*

## Project Structure

```text
packages/sertor/src/sertor_installer/assets/claude/hooks/
├── _hooklib.py             # + wiki_config(root) (tomllib); byte-copiato anche in assets/rag/hooks/
├── wiki-session-start.py   # RISCRITTO: direttiva config-driven + degradazione
packages/sertor/src/sertor_installer/install_wiki.py   # prompt Copilot SessionStart generico
wiki/wiki.config.toml       # + [ritual].exec_page = "syntheses/roadmap.md" (opt-in dogfood)
packages/sertor/tests/test_portable_hooks_parity.py    # +6 casi (config-driven/host-agnostic/degrada/opt-in)
packages/sertor/tests/test_portable_hooks_smoke.py     # aggiornato (config-driven)
```

**Structure Decision**: fix negli asset host-facing + `_hooklib` (helper condiviso, byte-copiato nelle due
copie bundle rag/wiki — guardia `test_hooklib_is_identical_in_both_bundles`). `sertor-core` engine invariato;
`structure.py` **non** toccato (DA-1 = degradazione, non seed). Gemella di FEAT-031/032/039 (correttezza
host-facing degli hook wiki).

## Note di consegna
- **Prova LIVE** sul dogfood: il nuovo hook legge `exec_page` → emette la direttiva roadmap+EXEC identica al
  vecchio comportamento (config-driven). Host-agnosticità provata dai test (root="docs").
- Gate: sertor 556 · kit 194 · flow 142 · root 1241 (le 2 fail packaging = branch non pushato, non regresso),
  ruff pulito.
