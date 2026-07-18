# Tasks: installer esito-azione + log ispezionabile

**Branch**: `110-feat-018-installer-esito-azione-log` · **Plan**: `./plan.md`

Ordine dipendenza-consapevole. Cross-package (kit → sertor/flow → distribuzione).

## T001 — Kit: `Outcome.PRESENT_DIVERGENT` (additivo)
`packages/sertor-install-kit/src/sertor_install_kit/artifacts.py`. Aggiungi UN membro
`PRESENT_DIVERGENT = "present_divergent"` (esistenti invariati). **Copre:** FR-001 (parte), REQ-006.

## T002 — Kit: helper confronto contenuto condiviso
Estrai `content_matches(dest, expected) -> bool` (read + normalizza CRLF + compara) dalla logica di
`lifecycle.py:159-164`; fai riusare a `lifecycle` l'helper (comportamento invariato). **Copre:** FR-001, riuso.

## T003 [P] — Kit: log-writer `install.event/1`
`observability.py`: `log_install_event(runtime_dir, *, op, capability, verb, outcome, reason, cmd=None, rev=None)`
→ append riga JSONL a `.sertor/.install-log.jsonl`; scrub segreti; best-effort non-fatale; parametro dry-run
(non scrive). **Copre:** FR-004, FR-007, FR-008.

## T004 — Kit test
`packages/sertor-install-kit/tests`: `Outcome` additivo; `content_matches` (identico/divergente/CRLF);
`log_install_event` (append, scrub, dry-run no-write). **Copre:** SC-001(parte)/004/005(parte).

## T005 — Installer sertor: esiti onesti + wiring log
`packages/sertor/src/sertor_installer/`: nei siti `if dest.exists(): return SKIPPED "already present"`
(`install_rag`, `install_governance`) → `content_matches` → `SKIPPED` (identico) / `PRESENT_DIVERGENT`
(divergente); `_apply_deps` esito che riflette l'esecuzione (FR-002); logga ogni `ArtifactOutcome` come
`install.event/1` (dry-run: no-write, report proiettato coerente). **Copre:** FR-001/002/003/005.

## T006 — Installer sertor-flow: stesso pattern
`packages/sertor-flow/src/sertor_flow/install_governance.py`: `_apply_file` `SKIPPED "already present"` →
confronto → `SKIPPED`/`PRESENT_DIVERGENT`; wiring log. **Copre:** FR-001/003/005 su flow.

## T007 — Installer test (sertor + flow)
Install su path divergente → `PRESENT_DIVERGENT`; identico → `SKIPPED`; deps onesto; upgrade su capability
assente leggibile come creazione (assorbe 036); `.install-log.jsonl` ben formato; **dry-run == reale**.
**Copre:** SC-001/002/003/004/005.

## T008 — Distribuzione host-facing (CS-7)
`uv run python -m sertor_installer.sync` (bundle) + **suite root** `tests/unit/test_assets_sync.py` verde;
doc utente: `docs/…` (install/reference) + tabella capability `packages/sertor/docs/install.md` menzionano il
log e gli esiti onesti. **Copre:** FR-009, SC-007.

## T009 — Verifica finale (gate)
`uv run pytest -m "not cloud"` verde (root + tutte le suite package) + `uv run ruff check .` pulito.
Conferma SC-006 (0 regressioni esiti esistenti). Smoke: install reale sul dogfood → `.install-log.jsonl` popolato.

## Dipendenze
T001,T002,T003 (kit) → T004 · poi T005,T006 (installer) → T007 · poi T008 (distribuzione) → T009 (gate).
