---
title: E10-FEAT-023 — Rimozione stub copilot assets fuorviante
type: experiment
tags: [debito-tecnico, igiene, host-facing, copilot]
created: 2026-06-30
updated: 2026-06-30
sources: ["requirements/debito-tecnico/stub-copilot/requirements.md", "requirements/debito-tecnico/epic.md"]
---

# E10-FEAT-023 — Rimozione stub copilot assets

**Feature completata:** 2026-06-30, branch `081-stub-copilot`

## Il problema

La cartella `packages/sertor/src/sertor_installer/assets/copilot/` contiene **solo 4 `.gitkeep`** (sottocartelle `agents/`/`hooks/`/`instructions/`/`prompts/`).

**Fuorviante:** suggerisce l'esistenza di asset Copilot statici depositati, quando la realtà è che **tutti i payload Copilot sono generati a runtime** da:
- `assets/claude/**` (asset sorgente, canonici)
- `assets/rag/**` (asset RAG, canonici)
- `surfaces.py` (rendering per-assistente: `render_copilot_hooks`, `render_custom_agent`, `render_prompt_file`)

La directory stub era un artefatto residuo della fase di design, rimasto dimenticato.

## Decisione e soluzione

**Rimozione totale** (scelta tra due opzioni: rimuovere il tree → non aggiungere README):
- Beneficio: chiarezza immediata, niente ambiguità sull'origine dei payload
- Costo: cambio meccanico nel repo (visibile storicamente, non visibile agli ospiti)

**Implementazione:**
1. `git rm packages/sertor/src/sertor_installer/assets/copilot/.gitkeep` × 4 cartelle
2. Le directory vuote spariscono automaticamente dal repo git
3. **Zero README aggiunto** (un file «questi asset sono generati a runtime» contraddirebbe il senso della guardia)

**Guardia anti-regressione:**
- Nuova riga in `test_assets_copilot_guard.py`: `assert not (asset_path("copilot").is_dir())`
- Fallisce se qualcuno tenta di riaggiungere la directory (protezione contra future derive da malintesi)

## Verifica

**grep esaustivo:** zero consumatori Python della directory:
- Nessun import
- Nessun path-reference in codice
- Nessun glob pattern che la includa

La directory è davvero inerte. Rimozione sicura.

## Esiti

- **SpecKit:** completo (spec → plan → tasks → impl)
- **Constitution Check:** 12/12 pass + missione soddisfatta
- **Test suite:** sertor **474** · root **1131 passed** (3 skip, non-regressione)
- **Ruff:** clean
- **`sertor-core`:** invariato (Principio XI)

## Backlink

- [[constitution]] — Principio X host-agnostico, richiesta di chiarezza (Principio XII)
- [[assistant-targeting]] — la parità Copilot è nel rendering, non in asset statici
- [[sertor-installer]] — topologia asset, ciclo di vita
- [[feat-022-pulizia-stile-skill]] — serie di igiene parallela (stile, ALL-CAPS)
- [[feat-021-altitude-claude-md]] — riduzione carico sempre-on
- [[feat-019-fail-loud-hook-agent]] — fallback agent su asset mancante
- [[feat-018-portabilita-os-hook]] — onestà sui surface (serie fail-loud)
