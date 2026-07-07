---
title: E15-FEAT-001 scope B — Implementazione asset-install (installatori veri contro dogfood)
type: experiment
tags: [fedelta-dogfood, asset-install, installer, process-fidelity, e15, feat-001, feat-010, implemented]
created: 2026-07-06
updated: 2026-07-06
sources: ["requirements/fedelta-dogfood/asset-install/requirements.md", "specs/089-asset-install/", ".specify/memory/constitution.md"]
---

# Implementazione E15-FEAT-001 scope B — Asset-install

> **Cosa:** trasformazione in realtà del modello «dogfood alimentato dai veri installer». I **3
> installer veri** (`sertor install rag/wiki`, `sertor-flow install`) sono stati eseguiti contro il
> dogfood (branch `089-asset-install`) con la direttiva dell'utente **«asset dall'installer, 0
> special-case»**. Esito: **per lo più idempotente** — gli asset sono depositati fedelmente, la
> process-fidelity è convalidata, i tre finding empirici del [[asset-install-installer-dry-run-2026-07-04|dry-run]]
> sono stati risolti. **Per la prima volta, il dogfood produce sé stesso tramite i veri processi di
> installazione che consegnerà agli ospiti.**

## Sintesi esecutiva

I tre installer eseguiti su dogfood in sequenza (`rag` → `wiki` → `flow`) hanno depositato gli asset
con **block:0** (zero blocchi, tutto idempotente) alla riesecuzione. La **process-fidelity** è stata
conseguita risolvendo i tre artefatti critici emersi dal dry-run:

1. **FEAT-010 policy line-ending**: `.gitattributes` aggiunto a root con `* text=auto eol=lf`
   (LF normalizzato repo-wide), asset bundlato `packages/sertor/src/sertor_installer/assets/rag/gitattributes`
   (CREATE_IF_ABSENT, non-distruttivo).
2. **CLAUDE.md riconciliato**: approccio ibrido con 3 blocchi marker EN (SDLC-RITUAL, RAG-USAGE,
   WIKI-RITUAL) posseduti dai marker, prosa IT dogfood-critica preservata, nota di orientamento
   aggiunte per disambiguare ownership.
3. **`wiki/log.md` legacy retrocesso**: il template è aggiornato alla rotazione `wiki/log/`, dogfood
   non ha più il monolitico (FEAT-006 promosso backlog per il template).

## Implementazione eseguita

### Pipeline SpecKit completata
Spec `089-asset-install` con `plan.md` e `tasks.md` completati: 12 task distinti (installer RAG/wiki/flow
+ FEAT-010 + CLAUDE.md + settings.json + .gitignore + validazioni) eseguiti, ciascuno con controllo
idempotenza (re-esecuzione dell'installer).

### Core invariato
`sertor-core` non toccato — la feature è host-facing (installer/asset) e confine Principio XI
osservato.

### Asset specifici realizzati

- **`.gitattributes` dogfood** (root): byte-identico all'asset installer, LF repo-wide tracciato.
- **`packages/sertor/.../assets/rag/gitattributes`**: asset bundlato, depositato su `sertor install rag` con CREATE_IF_ABSENT.
- **`CLAUDE.md` ibrido**: 3 blocchi marker EN + prosa IT dogfood + nota ownership → forma-client riconciliata.
- **`settings.json` wirati**: 2 hook precedentemente script (`wiki-session-start` SessionStart, `sertor-rag-usage-check` PreToolUse) → forma-client.
- **`.gitignore` +8 ignore**: runtime aggiunto `.sertor/.venv/`, `.index*`, `.rag-health.json`, ecc.
- **`.sertor/sertor-cli-reference.md`** (FR-007): creato dall'install, tracciato come asset.

### Guardie e riconciliazione

- **Script retrocessi a guardia-non-fonte**: `sertor_installer/sync.py`, `sertor_flow/sync.py`,
  `sertor_install_kit/sync.py`, `scripts/dev/materialize-speckit.ps1` — header aggiornati, guardia
  byte rimasta attiva.
- **Sync/script**: descritte in CLAUDE.md §Machinery SpecKit come **non-fonte** (rigenerabili), fonte
  unica è l'installer.

### Idempotenza verificata
Doppia esecuzione (secondo giro) dei 3 installer → **block:0 ovunque** (0 duplicati creati, artefatti
curati preservati: `.env`, costituzione v1.4.0, `.mcp.json`, `wiki.config.toml`).

### Documentazione utente
Riga `.gitattributes` aggiunta alla capability-table di `docs/install.md`.

## Risultati e verdetti

- **Constitution Check**: 12/12 ✅ PASS (Principi I–XII, Principio XI vehicle-only osservato).
- **Mission**: ✅ PASS (auto-conoscenza, codice+doc fusi, portabilità).
- **Test**: 1156 root + 492 sertor + 142 sertor-flow + 151 sertor-install-kit + 122 speclift + 59 specaudit = **2122 test verdi** (no cloud).
- **Lint**: `ruff check .` clean.
- **Spec**: `089-asset-install` completata.
- **Direttiva utente**: ✅ **«0 special-case»** rispettato — il dogfood è alimentato dai processi installer reali, nessuna divergenza di forma da un ospite.

## Lezione

Il modello di fedeltà (dogfood = quello che consegniamo) è realizzabile **in toto** eseguendo i veri
installer in sequenza come lo farebbe un ospite. I tre artefatti critici (line-ending, CLAUDE.md,
log schema) erano **noti e contenuti** dal dry-run → la soluzione è stata sistematica e a basso
rischio. La guardia di non-fonte su sync/script previene il ritorno a processi bypass. **La metà
"asset" di E15-FEAT-001 è completa; mergiata su `master` come parte della chiusura di `089-asset-install`.**

---

## Vedi anche

- [[asset-install-installer-dry-run-2026-07-04]] — il dry-run empirico che ha scoperto i tre finding
- [[dogfood-fidelity]] — il concetto di fedeltà (asset-fidelity e process-fidelity)
- [[epiche-sertor-core-e-cli]] — roadmap feature, epica E15 fedelta-dogfood
