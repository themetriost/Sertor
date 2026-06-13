# Implementation Plan: Manutenzione wiki deterministica (`move` · `reconcile` · `collect`+status)

**Branch**: `017-manutenzione-wiki` | **Date**: 2026-06-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-manutenzione-wiki/spec.md`

## Summary

Tre capacità **deterministiche** (parte D del confine D↔N) in `sertor-wiki-tools`, residuo di
FEAT-007: **`move`** (sposta una pagina e riscrive tutti i wikilink/link relativi entranti,
form-preserving, con `--dry-run`, idempotente/recovery, errore su collisione), **`reconcile`**
(detection read-only delle pagine `status: superseded` con successore dichiarato), e l'estensione di
**`collect`** col campo `status`. Tutto offline, stdlib-only, zero LLM. Nuovi contratti versionati
`wiki.move/1` e `wiki.reconcile/1`. Gruppo D (trigger periodico) = solo documentazione (host
scheduler). Riusa `_link_targets`/`iter_pages`/`frontmatter` esistenti per coerenza con `lint`.

## Technical Context

**Language/Version**: Python ≥ 3.11
**Primary Dependencies**: solo stdlib (`re`, `posixpath`, `pathlib`); nessuna nuova dipendenza.
**Storage**: file system del wiki (pagine `.md`, indice).
**Testing**: pytest su wiki temporaneo (`tmp_path`); nessuna rete, nessun LLM.
**Target Platform**: cross-platform.
**Project Type**: libreria core (`sertor_core.wiki_tools`) + CLI.
**Performance Goals**: lineare nel numero di pagine (RNF-007).
**Constraints**: deterministico/offline; non-distruttività (reconcile read-only; move solo sui file
coinvolti + dry-run); host-agnostico; contratti forward-compatible.
**Scale/Scope**: 2 moduli nuovi (`move.py`, `reconcile.py`) + estensione `collect.py` + 2 contratti +
parsing CLI + test; doc per il gruppo D.

## Constitution Check

*GATE iniziale (pre-Phase 0).* Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno:** moduli `wiki_tools` puri, nessun SDK; il CLI è un guscio
  sottile sopra le funzioni pure (`move`/`reconcile`).
- [x] **II — Boundary & local-first:** N/A provider; tutto locale/offline.
- [x] **III — YAGNI & unità piccole:** `move`/`reconcile` rispondono a REQ presenti; nessuna
  astrazione speculativa; riuso di `_link_targets`/`iter_pages` (DRY), no duplicazione.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** collisione `move` (dest+src), sorgente non
  trovata, path non valido → `SertorError` esplicito + `wiki.error/1`; nessuno stato parziale
  silenzioso (rewrite-then-move + recovery).
- [x] **V — Testabilità & misure:** tutto testabile su `tmp_path` offline; SC misurabili
  (link riscritti 100%, dry-run 0 modifiche, reconcile read-only).
- [x] **VI — Idempotenza & non-distruttività (NON-NEGOZIABILE):** `reconcile` read-only;
  `move` idempotente/recovery (D5), tocca solo i file coinvolti, `--dry-run`; il contenuto delle
  pagine superate resta su disco (REQ-027).
- [x] **VII — Leggibilità:** naming di dominio (`move`, `reconcile`, `rewritten`, `candidates`).
- [x] **VIII — Config centralizzata:** radice wiki/tassonomia/lingua dalla config; nessun default
  cablato nel corpo dei comandi.
- [x] **IX — Osservabilità:** ogni operazione emette `log_event` (operazione, conteggi) come gli
  altri comandi `wiki_tools`.
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** path relativi alla radice del wiki dalla config;
  nessuna assunzione su nomi/cartelle dell'ospite; trigger periodico delegato all'ambiente ospite.

**Esito gate iniziale: PASS (10/10), nessuna deroga.**

## Project Structure

### Documentation (this feature)

```text
specs/017-manutenzione-wiki/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/cli-commands.md
├── checklists/requirements.md
└── tasks.md   (da /speckit-tasks)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── move.py          # NUOVO — move(profile, src, dest, dry_run) -> MoveResult
├── reconcile.py     # NUOVO — reconcile(profile) -> ReconcileResult
├── collect.py       # esteso — _page_meta + campo `status` (D8)
├── contracts.py     # + MoveResult (wiki.move/1), ReconcileResult (wiki.reconcile/1)
└── __main__.py      # + op move/reconcile, 2° positional `dest`, --dry-run, dispatch, _human

tests/unit/
├── test_wiki_tools_move.py        # NUOVO — wikilink/relativi, dry-run, collisione, recovery
├── test_wiki_tools_reconcile.py   # NUOVO — superseded list, clean, read-only
├── test_wiki_tools_collect.py     # status nel meta (o estende l'esistente)
└── test_wiki_tools_cli.py         # estende: parsing/dispatch move/reconcile

docs/install.md (o docs wiki) — nota gruppo D (trigger periodico via scheduler ospite)
```

**Structure Decision**: estendere `wiki_tools` (nessun nuovo pacchetto); il CLI resta un guscio
sottile. `move`/`reconcile` sono funzioni pure testabili senza CLI.

## Complexity Tracking

> Nessuna violazione costituzionale: tabella non necessaria.

## Post-design re-check

Dopo research/data-model/contracts: nessun SDK, nessuna nuova dipendenza, errori espliciti su tutti i
percorsi di fallimento, `reconcile` read-only, `move` idempotente. **PASS (10/10), Complexity vuoto.**
