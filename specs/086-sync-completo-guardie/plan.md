# Implementation Plan — Sync completo + guardie (E15-FEAT-002)

**Branch:** `087-a05-dogfood-client-debt` | **Date:** 2026-07-03 | **Spec:** [spec.md](./spec.md)

## Summary
Estendere il sync (`sertor_installer.sync`) ai file-asset byte-copiati di `assets/rag/{hooks,skills,agents}`
(oltre a `claude`) + una **guardia esaustiva auto-derivante** dogfood↔bundle. Rieseguire il sync **crea** gli
asset RAG oggi assenti (`sertor-rag-usage-check.ps1`, `guided-setup`, `concierge`) → assorbe F3-file.

## Technical Context
Python 3.11, stdlib + `sertor_install_kit.sync` (`sync_subtree`/`iter_asset_dir` esistenti, parametrici su
`(subtree→dest)` + `exclude`). Test `pytest` offline. Nessun `sertor-core`. Tocca `packages/sertor` (tool di
sync dev) + `tests/unit`.

## Constitution Check
- **I/II** PASS (N/A core). **III** PASS — riusa `sync_subtree`/`iter_asset_dir` (no nuovo meccanismo, DRY).
- **IV** PASS — guardia fail-loud che nomina asset+fix. **V** PASS — guardia F.I.R.S.T. offline, esaustiva.
- **VI** PASS — sync idempotente (created/updated/identical). **VII/VIII** PASS.
- **IX** PASS (N/A). **X** PASS — il sync è tool **dev**, host-agnostico (assets→.claude); nessun asset
  distribuito reso Sertor-specifico. **XI** PASS (usa file/asset API, non `sertor_core`).
- **XII** PASS (rafforzato) — la guardia esaustiva **fa emergere** il drift silenzioso (oggi 3 hook soli),
  non lo tollera. **Missione** PASS (periferico: fedeltà del dogfooding).

**12/12 + missione PASS. Complexity Tracking vuoto.**

## Design (Phase 0/1)
- **D-1 (sync):** `sync_assets_to_claude` passa da `sync_subtree("claude", .claude)` a `sync_assets` con
  mapping `[("claude",".claude"), ("rag/hooks",".claude/hooks"), ("rag/skills",".claude/skills"),
  ("rag/agents",".claude/agents")]`. I non-byte (`rag/env*`, `rag/mcp*`, `rag/settings*`, `claude-md-block*`,
  `rag/sertor-cli-reference.md`) vivono in `assets/rag/` **root** → **non** nei 3 subtree byte → esclusi per
  costruzione. `main()` invariato (stampa il report merge).
- **D-2 (guardia esaustiva):** riscrivere `test_assets_rag_dogfood_sync.py` da lista-fissa-3-hook a
  **enumerazione** via `iter_asset_dir(anchor, subtree)` sui 3 subtree byte RAG, `parametrize` su ogni file,
  assert byte-identità al dest (`.claude/hooks|skills|agents/<rel>`). `test_assets_sync.py` continua a coprire
  `claude`. Insieme = copertura esaustiva dei file-asset byte-copiati.
- **D-3 (F3-file assorbita):** eseguire il sync esteso popola gli asset mancanti nel dogfood. Post-sync la
  guardia è verde. Se un asset RAG **divergeva** (non solo mancava), il sync lo riallinea → drift chiuso.
- **Confine (spec [NEEDS CLARIFICATION] risolto):** l'insieme byte è definito dai **subtree** enumerati
  (`claude`, `rag/hooks`, `rag/skills`, `rag/agents`), non da un filtro fragile — verificabile e stabile.

## Project Structure (paths reali)
```text
packages/sertor/src/sertor_installer/sync.py          # + mapping rag byte
tests/unit/test_assets_rag_dogfood_sync.py            # → guardia esaustiva (da 3-hook a auto-derivante)
.claude/hooks/sertor-rag-usage-check.ps1              # CREATO dal sync (era assente)
.claude/skills/guided-setup/SKILL.md                  # CREATO dal sync
.claude/agents/concierge.md                           # CREATO dal sync
# (+ eventuali riallineamenti di asset RAG già presenti ma divergenti)
```
**Structure Decision:** nessun `src/sertor_core`. Tocca il tool di sync dev + la guardia + gli asset dogfood
popolati dal sync.

## Complexity Tracking
*(vuoto)*

## Note
- **F2 assorbe F3-file:** il wiring `settings.json` della rag-usage (non-byte) resta **F1**. Aggiornare lo
  stato F3 nell'epica a «file assorbiti da F2; wiring→F1».
- **Rischio R-2 (atteso):** l'estensione può far emergere divergenze già esistenti → si riallineano nel sync.
