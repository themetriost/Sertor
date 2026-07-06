---
title: Dry-run dei veri installer sul dogfood (asset-install, E15)
type: experiment
tags: [fedelta-dogfood, asset-install, installer, process-fidelity, crlf, e15, dry-run]
created: 2026-07-04
updated: 2026-07-04
sources: ["requirements/fedelta-dogfood/asset-install/requirements.md", "requirements/fedelta-dogfood/epic.md", "scripts/smoke.ps1"]
---

# Dry-run: i 3 veri installer contro il dogfood (E15 asset-install)

> ⚠️ **Implementata (2026-07-06).** I tre finding di questo dry-run sono stati risolti:
> FEAT-010 line-ending + CLAUDE.md ibrido + wiki/log schema. Vedi [[asset-install-scope-b-implementation-2026-07-06]]
> (pagina esperimento dell'implementazione).

> **Cosa:** eseguiti i 3 veri installer di Sertor (`sertor install rag`, `sertor install wiki`,
> `sertor-flow install`) da `git+url@master` via `uvx` — *come un host reale* — contro il dogfood
> (repo vivo, branch usa-e-getta `090-asset-install-exec`), per **osservare** cosa depositano prima di
> automatizzare la process-fidelity degli asset. **Output scartato** (riproducibile); qui resta il sapere.
> Vedi [[dogfood-fidelity]], requisiti in `requirements/fedelta-dogfood/asset-install/`.

## Comandi (forma fedele, ancorata a `scripts/smoke.ps1`)

```
uvx --refresh --from "git+…/Sertor.git@master#subdirectory=packages/sertor"      sertor install rag  --assistant claude --backend azure --corpus sertor --no-deps --target <repo>
uvx --refresh --from "git+…/Sertor.git@master#subdirectory=packages/sertor"      sertor install wiki --assistant claude --target <repo>
uvx --refresh --from "git+…/Sertor.git@master#subdirectory=packages/sertor-flow" sertor-flow install --assistant claude --target <repo>
```

## Esito headline: **per lo più idempotente**

La grande scoperta: l'install è **quasi interamente idempotente** contro il dogfood. Runtime + ~tutti gli
asset risultano `skipped (already present)` — **byte-identici** a quelli che l'installer depositerebbe.
Questo **prova empiricamente** che il `sync` (FEAT-002) era già fedele: la *asset-fidelity byte* è reale.
`sertor-flow install` ha persino **skippato `specify init`** (machinery già presente). Preservati intatti:
`.sertor/.env` (chiave Azure), `.mcp.json`, **costituzione v1.4.0**, `wiki.config.toml` (super-set).

Il residuo di process-fidelity è quindi **piccolo**: ciò che l'install aggiunge di nuovo (207 righe reali):

| Artefatto | Cambio reale | Nota |
|---|---|---|
| `CLAUDE.md` | +174 = **3 blocchi marker** | RAG-USAGE · WIKI-RITUAL · SDLC-RITUAL |
| `.claude/settings.json` | +24 (hook entries) | |
| `.gitignore` | +9 | |
| `.sertor/sertor-cli-reference.md` | **creato** | residuo FEAT-003 ora prodotto dall'install |
| `wiki/log.md` | **creato** | ⚠️ legacy: il dogfood usa la rotazione `wiki/log/<data>.md` |

## Finding 1 — CLAUDE.md: 3 blocchi generici vs prosa dogfood ricca (DA-1)

Ogni blocco marker è un **sottoinsieme generico host-agnostico** di una sezione dogfood **molto più
ricca e Sertor-specifica**. Decisione utente: approccio **ibrido** (blocco + prosa), da eseguire come
step deliberato. Verdetto per-blocco:

- **RAG-USAGE** — prosa (`Riferirsi al prototipo` + Principio XI) più ricca; il blocco aggiunge solo il
  pattern `uv run --project .sertor` e la memoria conversazioni → **tieni blocco, prosa quasi intatta**.
- **WIKI-RITUAL** — prosa (Rituale di step, **10 punti** vs 4 del blocco: EXEC roadmap, re-index,
  **re-lock F8**, smoke, mostra-roadmap, archivia-agenti) strettamente più ricca → **prosa-vince**,
  valutare di rimuovere il blocco (il rituale è governance dogfood, non capability installabile).
- **SDLC-RITUAL** — parità: il blocco *aggiunge* le 7 fasi SpecKit + Constitution Check esplicitati →
  **ibrido vero**: tieni blocco, sfronda i duplicati puri dalla prosa, tieni il delta (gate pre-merge
  suite+ruff).

**Trasversale:** prosa in **italiano**, blocchi in **inglese** → l'ibrido lascia CLAUDE.md bilingue (da decidere).
Report dettagliato con tabelle riga-per-riga: `scratchpad/asset-install-claude-md-reconciliation-report.md`
(effimero) — da promuovere qui se serve alla riconciliazione.

## Finding 2 — Churn CRLF (line-ending)

Gli installer scrivono i file con **CRLF** (Windows); i file dogfood erano **LF** → git vede *ogni riga*
cambiata. Prova: `git diff --ignore-cr-at-eol` riduce il diff di `CLAUDE.md` da **1228 a 174 righe reali**.
Non è un bug di contenuto, è artefatto di piattaforma. **Confine host:** colpisce *ogni ospite Windows*
che ri-esegue l'install → candidato a **fix di prodotto** (`.gitattributes` `* text=auto eol=lf` nel
template installer), non solo dogfood. Backlog E15.

## Finding 3 — `wiki/log.md` legacy vs rotazione `wiki/log/`

`sertor install wiki` crea `wiki/log.md` (monolitico); il dogfood usa la **rotazione**
`wiki/log/<data>.md` (FEAT-008 meccanica-log). È **staleness inversa** (E15-FEAT-006): il **template è
indietro** rispetto alla realtà dogfood — non è il dogfood in difetto. Fix: scartare `wiki/log.md` nel
dogfood **e** aggiornare il template alla rotazione (beneficia gli ospiti).

## Lezione

Il modello «dogfood prodotto dai veri installer» è per **la maggior parte già vero** grazie al sync
byte-fedele; la process-fidelity residua è **contenuta e nota**: riconciliazione CLAUDE.md (ibrido) +
`.gitattributes` (CRLF) + template `wiki/log/` (FEAT-006). Nessuna sorpresa distruttiva: `.env`,
costituzione, `.mcp.json`, `wiki.config` tutti preservati. La via all'obiettivo dell'utente («Sertor usa
Sertor installato per tutte le sue dimensioni») è chiara e a basso rischio.
