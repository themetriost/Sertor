# Research — dogfood client-fedele (Phase 0)

Risolve gli unknown della spec, in primis **Q3** (come materializzare in sicurezza). Ogni decisione:
Decision / Rationale / Alternatives.

## D-1 — Come materializzare la machinery SpecKit in sicurezza (Q3)

**Decision.** Materializzazione **isolata + copia selettiva**: eseguire `specify init --ai claude` (pin
`SPECKIT_VERSION`, con overlay UTF-8) in una **dir temporanea**, poi copiare nel repo **solo** la machinery
**rigenerabile** (skill `speckit-*`, `.specify/scripts/`, template non-custom, workflows/integrations). Gli
artefatti Sertor-authored (`.specify/memory/constitution.md`, `.specify/templates/plan-template.md`,
`.specify/feature.json`) **non** vengono mai sovrascritti. Il tutto incapsulato in un **piccolo script di
setup dogfood** (PowerShell), idempotente.

**Rationale.** Verificato dal vivo che funziona (layout completo prodotto) e che l'isolamento è
**necessario**: `specify init --force` sul root sovrascriverebbe la nostra costituzione v1.4.0 e il
`plan-template.md` custom (rischio confermato). L'overlay UTF-8 (`PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`) è
necessario: senza, aborta `UnicodeEncodeError` su console cp1252 — lo script lo incapsula (come il vehicle
di produzione `_UTF8_ENV`). Uno script rende il passo **ripetibile e testabile**; codifica la sicurezza
(isolamento, preservazione, UTF-8) che passi manuali sbagliano (l'abbiamo già colpito).

**Alternatives rejected.**
- **`sertor-flow install` / `specify init --force` sul root:** clobber della costituzione + plan-template
  custom (l'ordine che li ripristina esiste solo sul percorso ospite completo, non nel dogfood). Rifiutato.
- **Committare la machinery (vendoring):** viola NFR-1 (drift di pin 0.8.18, mix authored+upstream) — è lo
  stesso motivo per cui il pivot 045 ha **un-vendorato** SpecKit e per cui l'opzione "create" di A-05 è stata
  scartata. Rifiutato.
- **Solo documentazione (passi manuali, nessuno script):** footgun UTF-8/isolamento; non testabile; l'errore
  reale già osservato. Rifiutato.

## D-2 — Forma dell'artefatto di setup

**Decision.** Uno script versionato `scripts/dev/materialize-speckit.ps1` (nome indicativo, → plan/tasks),
che: (1) risolve una temp dir; (2) lancia `uvx --from git+…spec-kit@v<SPECKIT_VERSION> specify init . --here
--ai claude --script ps --no-git --force --ignore-agent-tools` con l'overlay UTF-8; (3) copia **solo** la
machinery rigenerabile nel repo; (4) **verifica** che gli artefatti Sertor-authored siano invariati (fail
loud se cambierebbero). Idempotente (re-run = no-op sugli invarianti).

**Rationale.** Ripetibile (setup come `uv sync`), testabile, fail-loud (Principio XII), pin da fonte unica.

**Alternatives.** Riuso diretto di `launch_speckit` (prodotto) — rifiutato: mira al root con `--force`
(clobber) e importerebbe logica di prodotto in uno script dev (accoppiamento); il valore dell'isolamento è
proprio non passare dal percorso ospite completo.

## D-3 — Fato dei 9 agenti hand-authored (Q1, decisione utente)

**Decision.** **Rimuovere** i 9 `.claude/agents/speckit-*.md`. Il dogfood usa le **skill native** `speckit-*`
(materializzate) come un client — invocate in-context via il tool Skill.

**Rationale.** End-state fedele: un client non ha quegli agenti. Elimina la divergenza alla radice.

**Alternatives.** Tenerli come wrapper funzionali (ora che le skill risolvono) — resta client-divergente
(estensione dogfood-only); l'utente ha scelto la rimozione. Reversibile via git se la delega a subagent
servisse (allora sarebbe una decisione di *prodotto*: distribuirli, contro il pivot 045).

## D-4 — Insieme esatto dei path da gitignorare (dal layout verificato)

**Decision.** Gitignorare (rigenerabili, non tracciati oggi):
`.claude/skills/speckit-*/`, `.specify/scripts/`, `.specify/workflows/`, `.specify/integrations/`,
`.specify/init-options.json`, `.specify/integration.json`, e i template **non-custom**
`.specify/templates/{checklist-template,constitution-template,spec-template,tasks-template}.md`.
**Restano tracciati** (Sertor-authored): `.specify/templates/plan-template.md`,
`.specify/memory/constitution.md`, `.specify/feature.json`.

**Rationale.** Ricalca esattamente la separazione authored↔rigenerabile verificata via `git ls-files`.
Nessun file oggi tracciato viene untrackato → gitignore pulito, senza sorprese.

**Alternatives.** Ignorare `.specify/` in blocco con negazioni — più fragile (rischio di ignorare
`constitution.md`/`plan-template.md`). Rifiutato per chiarezza.

## D-5 — Guardia anti-regressione

**Decision.** Test di root (offline) che asserisce: (1) **0** file `.claude/agents/speckit-*.md`; (2)
nessuna copia di machinery rigenerabile **tracciata** in git (es. `git ls-files` non elenca
`.claude/skills/speckit-*` né `.specify/scripts/**`). Gira senza rete e **senza** la machinery materializzata
localmente (asserisce assenze/tracciamento, non presenze).

**Rationale.** Coglie il ritorno di **entrambe** le facce dello special-case (agente orfano; re-vendoring).
Complementa `test_no_vendored_speckit.py` (che guarda il bundle **distribuito**); questa guarda il **repo dogfood**.

**Alternatives.** Guardia che pretende la **presenza** delle skill — rifiutata: fallirebbe in CI/clone fresco
(machinery gitignorata) e ri-legittimerebbe l'accoppiamento presenza-in-git.

## D-6 — Documentazione di setup

**Decision.** Aggiornare la sezione **Sviluppo** di `CLAUDE.md` (accanto a `uv sync`): il dogfood ottiene la
machinery SpecKit eseguendo lo script di materializzazione (rigenerabile, come il `.venv`; non in git).

**Rationale.** REQ-007: il setup è comprensibile; la fedeltà è "by design" (install come step). Nota: è
documentazione **interna/dev** (`CLAUDE.md`), non doc utente `docs/` — la feature è dogfood-only, non
host-facing (confine doc interna↔utente).

## Unknown residui
Nessuno bloccante. Il nome esatto dello script e la sua collocazione (`scripts/dev/`) sono dettagli di `tasks`.
