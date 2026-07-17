---
title: Fedeltà del dogfood (dogfood-fidelity)
type: concept
tags: [dogfooding, fedelta, runtime, installato, head-tracking, re-lock, e15]
created: 2026-07-03
updated: 2026-07-03
sources: ["requirements/fedelta-dogfood/epic.md", "wiki/syntheses/audit-fedelta-dogfood-2026-07-03.md", "specs/088-relock-runtime/plan.md", ".sertor/pyproject.toml", "scripts/dev/relock-runtime.ps1", "CLAUDE.md"]
---

# Fedeltà del dogfood (dogfood-fidelity)

Il [[dogfooding]] risponde a «usiamo il nostro RAG su di noi». La **fedeltà del dogfood** risponde a una
domanda più stretta e più severa: **il dogfood si comporta *davvero* come un progetto-ospite di Sertor, o
solo *quasi*?** È la stella polare applicata a noi stessi — se il workspace di Sertor gira su qualcosa di
diverso da ciò che un ospite otterrebbe, il dogfooding *mente* (misura uno strumento che nessun cliente ha).
Ogni divergenza dal client è **debito**, non design (vedi [[feedback_dogfood_client_fedele]]); la direttiva
standing è: il dogfood gira **solo** sulla versione **installata**, mai sul sorgente-repo
([[feedback_dogfood_solo_via_install_versionbump]]).

## I due livelli di fedeltà

La fedeltà non è monolitica: si rompe su due assi indipendenti.

- **Asset-fidelity** — *gli stessi file*. Gli asset host-facing del dogfood (`.claude/`, hook, skill,
  agenti, blocchi `CLAUDE.md`, `wiki/`) sono byte-identici a quelli che un installer depositerebbe? Oggi
  **parziale**, mantenuta via `sertor_installer.sync` + guardie (E15-FEAT-002).
- **Process-fidelity** — *prodotti dal vero processo*. Quegli asset e quel runtime sono stati prodotti
  **eseguendo i veri installer** (`sertor install rag/wiki`, `sertor-flow install`), o curati a mano /
  sincronizzati? Finché si passa dal sync, la *forma* è fedele ma il *processo* no.

La distinzione conta perché un asset può essere identico (asset-fidelity ✅) pur non essendo mai passato per
l'installer (process-fidelity ✗): il secondo è ciò che verifica davvero il percorso che l'ospite vive.

**Lezione complementare:** vedi anche [[esito-sull-host-vs-forma-dell-asset]] — anche un asset
process-fedele si controlla male se testiamo solo la *forma* e non l'*esito sull'host che aggiorna*.

## Il runtime: `.sertor/` installato, che traccia HEAD

Il cuore del modello (E15-FEAT-001/F1): il **runtime dell'agente** — MCP, hook, skill, la macchina che
serve retrieval — gira sul **runtime installato `.sertor/`**, non sul `.venv` editable del workspace. È un
progetto `uv` a sé (`.sertor/pyproject.toml` + `.sertor/uv.lock` + `.sertor/.venv`) che installa
`sertor-core` da `git=<repo>` a **HEAD**, non da un tag.

- **Il dogfood traccia HEAD; gli ospiti pinnano una versione.** Un cliente esterno pinna un tag e riceve
  l'auto-updater ([[auto-update-version-check|E2-FEAT-013]]); il dogfood insegue `origin/master`. Le due
  storie sono **separate** e non devono mescolarsi.
- **Re-lock post-merge (E15-FEAT-008/F8).** `.sertor/uv.lock` fissa il commit risolto: dopo un merge su
  `master`, HEAD avanza e il runtime resta stantio. Il passo `scripts/dev/relock-runtime.ps1` (check-then-act,
  fail-loud, **dogfood-only**) lo riallinea meccanicamente nel rituale post-merge, *prima* di re-index/smoke.
  Il lock è **gitignorato** (volatile, tracks HEAD); solo `.sertor/pyproject.toml` è versionato (la spec
  stabile). Confine D↔N: lo script è deterministico, l'innesco è giudizio del flusso principale — e resta
  **fuori** dagli asset distribuiti (l'hook `rag-freshness.py` non deve inseguire HEAD).

## Il confine dev↔dogfood (non è uno special-case)

Il workspace **è** Sertor più il suo sviluppo, quindi porta cose che un client non ha (`src/`, `packages/`,
`tests/`, `.venv`). Non è una violazione della fedeltà: è la natura del repo-sorgente. Il confine è netto:

- **dev/test** → sul `.venv` editable del workspace (`uv run pytest`, `ruff`);
- **runtime dell'agente** → sull'installato `.sertor/`.

Sotto questa lente, `.venv` non è un «asset divergente» da eliminare — è l'ambiente di sviluppo del prodotto;
il runtime dell'agente semplicemente non lo usa.

## Stato (E15 `fedelta-dogfood`)

| Fetta | Stato |
|---|---|
| **F1/F7** runtime installato `.sertor/` da git HEAD, `.mcp.json` → `uv run --project .sertor` | ✅ (#150) |
| **F5** installer preservante `plan-template.md` attraverso `specify init --force` | ✅ (#149) |
| **F8** re-lock post-merge del runtime a HEAD (script dogfood-only + gitignore lock + rituale/gate) | ✅ (#152) |
| **F2** asset-fidelity RAG (sync esteso + guardie) — *interim, via sync non install* | ✅ (#146) |
| **F4 / asset-install** gli asset prodotti dai **veri** `sertor install`/`sertor-flow install`, non dal sync | 🔜 (ultima crepa reale) |

**La crepa che resta:** F1 ha chiuso il *runtime* (process-fidelity del motore); gli **asset** viaggiano
ancora via sync (asset-fidelity, non process-fidelity). F4 la chiude facendoli produrre dagli installer reali.

## Vedi anche
- La pratica di base che questo modello rende fedele: [[dogfooding]].
- L'audit che ha nominato i due livelli: [[audit-fedelta-dogfood-2026-07-03]].
- Il dry-run empirico che ha verificato l'idempotenza dei veri installer: [[asset-install-installer-dry-run-2026-07-04]].
- Le direttive standing: [[feedback_dogfood_client_fedele]], [[feedback_dogfood_solo_via_install_versionbump]].
