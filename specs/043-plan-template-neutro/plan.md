# Implementation Plan: Plan-template neutro nel bundle (Gruppo D)

**Branch**: `043-plan-template-neutro` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

## Summary

Sostituire nel bundle `sertor-flow` il `plan-template.md` *gated* di Sertor con quello **generico**
upstream (gate derivati dalla costituzione dell'ospite), ed **escluderlo** dal sync/anti-drift
bundle↔dogfood (intenzionalmente divergente). Il dogfood di Sertor mantiene il suo template gated.
Coerenza: stessa logica di provenienza degli script (F3, vendored da upstream).

## Design

- **D1 — Asset.** `packages/sertor-flow/src/sertor_flow/assets/specify/templates/plan-template.md` ←
  copia byte-esatta dell'upstream `ExternalRepos/spec-kit/templates/plan-template.md` (placeholder
  `[Gates determined based on constitution file]`).
- **D2 — Esclusione dal sync (kit).** Aggiungere a `sync_subtree` un parametro opzionale
  `exclude: tuple[str, ...] = ()` (backward-compatible): i `rel_path` in `exclude` sono saltati.
- **D3 — Sertor-flow sync.** In `sertor_flow/sync.py`, il subtree `templates` passa
  `exclude=("plan-template.md",)` → il plan-template non viene propagato né confrontato; gli altri
  template restano sincronizzati.
- **D4 — Guard test.** `test_assets_sync.py`: escludere `plan-template.md` dal confronto
  `test_bundle_asset_matches_dogfood`; aggiungere un test che asserisce che il `plan-template.md` del
  bundle è generico (placeholder presente, nessun gate Sertor) e che il sync dry-run non lo elenca.

## Constitution Check (v1.2.0)
- [x] **III/VI/X**: cambio minimo, non-distruttivo; host-agnostico (l'ospite riceve un template neutro,
  non i principi di Sertor). **PASS.**
- [x] **XI**: coerente — i gate Sertor restano interni a Sertor, non vanno all'ospite. **PASS.**
- Altri principi invariati. **Esito: PASS 11/11**, nessuna deroga.

## Project Structure
```text
packages/sertor-install-kit/src/sertor_install_kit/sync.py   # + param exclude in sync_subtree
packages/sertor-flow/src/sertor_flow/sync.py                 # templates: exclude plan-template.md
packages/sertor-flow/src/sertor_flow/assets/specify/templates/plan-template.md   # → generico upstream
packages/sertor-flow/tests/unit/test_assets_sync.py          # esclusione + test "neutro"
```

## Complexity Tracking
> Nessuna violazione. Tabella vuota.
