# Implementation Plan: installer esito-azione + log ispezionabile

**Branch**: `110-feat-018-installer-esito-azione-log` · **Spec**: `./spec.md` · **Requisiti**: `../../requirements/sertor-cli/feat-018-installer-esito-azione-log/requirements.md`

**Date**: 2026-07-18

## Summary

Il report dell'installer descrive la **precondizione**, non l'**azione**: `SKIPPED` conflaziona
identico/divergente (`artifacts.py:63`), `_apply_deps` marca `SKIPPED` per «dir c'era» mentre `uv add`
gira (`install_rag.py:708-717`). **Fix (decisioni clarify):** (P1) nuovo membro `Outcome` additivo per il
caso divergente + confronto di contenuto riusato da `lifecycle.py:159-164`; deps oneste; (P2) log-writer
nel kit → `.sertor/.install-log.jsonl` (`install.event/1`); dry-run fedele; + bundle sync + doc utente.
**Assorbe E10-FEAT-036.**

## Technical Context

- **Package toccati (3):**
  - `packages/sertor-install-kit` — `artifacts.Outcome` (+1 membro); `observability.py` (log-writer
    `install.event/1`); il confronto di contenuto reso riusabile (estrarre da `lifecycle.py`).
  - `packages/sertor` (`sertor_installer`) — siti install `dest.exists() → SKIPPED` (`install_rag`,
    `install_governance`, e simili) → confronto contenuto; `_apply_deps` onesto; wiring del log nel flusso.
  - `packages/sertor-flow` — `install_governance._apply_file` (stesso pattern `SKIPPED "already present"`).
- **Riuso (non reinventare):** il confronto `read_text + normalizza CRLF + compara` di `lifecycle.py:159-164`
  → estrarre in un helper del kit condiviso da install e uninstall; `log_event`/`observability.py` come base del log-writer.
- **Nuovo membro `Outcome`:** additivo (es. `PRESENT_DIVERGENT = "present_divergent"`), gli esistenti
  invariati (report byte-compat, REQ-006). Nome esatto da confermare in implement.
- **`install.event/1`:** riga JSONL append in `.sertor/.install-log.jsonl`; campi chiusi
  (`op`,`capability`,`verb`,`outcome`,`reason`,`cmd?`,`rev`); scrub segreti dell'osservabilità esistente.
- **Dry-run fedele:** il verdetto (identico/divergente/creato) è calcolato dallo **stesso** helper sia in
  proiezione sia in esecuzione; il log-writer in dry-run proietta senza scrivere il file.
- **Fail-safe log (REQ-007):** la scrittura è best-effort; un errore → warning/breadcrumb, mai abort (parità E4-011).
- **Host-facing:** sync bundle installer (`sertor_installer.sync` + guardia root `test_assets_sync.py`) +
  doc utente (`docs/…` + tabella capability `packages/sertor/docs/install.md`).

## Constitution Check (gate)

| # | Principio | Esito | Nota |
|---|---|---|---|
| — | **Missione / North Star** | ✅ PASS | Un setup che *racconta la verità* è il presupposto della fiducia dell'agente/utente nel sistema che serve il retrieval; serve la qualità del contesto reso. |
| I | Core a dipendenze verso l'interno | ✅ PASS | Logica nel kit/installer; nessuna dipendenza invertita. |
| II | Provider/backend dietro boundary | ✅ N/A | Nessun provider/store. |
| III | Semplicità (YAGNI) | ✅ PASS | **UN** membro nuovo (non un set); riuso del confronto e di `log_event` esistenti; niente rotazione log ora. |
| IV | Errori espliciti, niente null silenzioso | ✅ PASS | L'esito onesto è *anti*-silenzio; log-write fail → segnalato (REQ-007), non muto. |
| V | Testabilità / qualità provata | ✅ PASS | Casi costruibili (divergente/identico/deps/upgrade-ex-novo/dry-run) su 3 suite; SC misurabili. |
| VI | Idempotenza, determinismo, non-distruttività | ✅ PASS | Non-distruttività **rafforzata** (divergente → non tocco, esplicito); dry-run == reale. |
| VII | Leggibilità, lascia il codice più pulito | ✅ PASS | Rimuove la conflazione `SKIPPED`; un confronto condiviso invece di duplicato install/uninstall. |
| VIII | Config centralizzata | ✅ N/A | Nessun nuovo default di config (il path `.sertor/` è già risolto). |
| IX | Osservabilità | ✅ PASS | Riusa `log_event`/lo strato d'osservabilità del kit; il log è un canale coerente, non slegato. |
| X | Host-agnostico | ✅ PASS | Log/esiti host-agnostici (path relativi `.sertor/`); bundle+doc distribuiti agli ospiti (CS-7). |
| XI | Consumo via vehicle | ✅ PASS | Tutto dentro gli installer (vehicle); nessun accesso diretto alla libreria core. |
| XII | Fail Loud, Fix the Cause | ✅ PASS | **Cuore:** il report smette di *dichiarare una precondizione al posto di un'azione*; la causa (esito basato su presenza) è eliminata. |

**Esito gate: 12/12 + missione PASS** (2 N/A giustificati). Nessuna deviazione.

## Design (schema)

1. **Kit — `artifacts.Outcome`**: aggiungi `PRESENT_DIVERGENT` (additivo). 
2. **Kit — helper confronto**: `content_matches(dest, expected) -> bool` (read+normalizza CRLF+compara),
   estratto dalla logica di `lifecycle.py:159-164`; uninstall lo riusa (nessun cambio di comportamento lì).
3. **Kit — `observability.py`**: `log_install_event(runtime_dir, event: dict)` → append riga
   `install.event/1` a `.sertor/.install-log.jsonl`; best-effort, scrub; dry-run non scrive.
4. **Installer (sertor + flow)**: nei siti `if dest.exists(): return SKIPPED "already present"` →
   `SKIPPED` se `content_matches`, altrimenti `PRESENT_DIVERGENT` (reason «present but modified»). 
5. **`_apply_deps`**: esito che riflette l'esecuzione del comando (REQ-002).
6. **Wiring log**: ogni `ArtifactOutcome` prodotto → evento loggato (op/capability/verb/outcome/reason/cmd/rev),
   dallo stesso punto che alimenta `InstallReport` (dry-run: report proiettato, log non scritto).
7. **Bundle sync + doc utente** (CS-7): `sertor_installer.sync` + `docs/…` + tabella capability.

## Test
- kit: `Outcome` additivo; `content_matches`; `log_install_event` (append, scrub, dry-run no-write).
- sertor/flow: install su path divergente → `PRESENT_DIVERGENT`; identico → `SKIPPED`; deps onesto;
  upgrade-ex-novo leggibile; `.install-log.jsonl` ben formato; dry-run == reale; guardia sync; **suite esistenti verdi (REQ-006)**.

## Out of scope
- P3 (lettore unico/`doctor` aggrega) + E2-FEAT-017 (auto-updater) — item successivi della coda.
- Rotazione/troncamento del log; ridisegno del report a schermo oltre il minimo.

## Phase completion
- [x] requirements · [x] specify · [x] clarify (4 forcelle sciolte) · [x] plan (+ Constitution Check 12/12)
- [ ] tasks · [ ] implement
