# Requisiti — Rituale post-merge: re-lock del runtime `.sertor/` a HEAD

<!-- Deriva da: E15-FEAT-008 (epica fedelta-dogfood) -->

## 1. Contesto e problema (perché)

**F1** ha reso il runtime `.sertor/` un uv project che installa `sertor-core` da `git=<repo>` **HEAD**. Ma
oggi, dopo un merge su `master`, il runtime **non si aggiorna da solo**: resta sull'ultimo commit lockato
finché non si rifà `uv lock --upgrade` a mano. Per il modello «il dogfood traccia HEAD» questo passo va
**meccanizzato** (confine D↔N: meccanico → deterministico, non a discrezione dell'agente).

**Auto-finding (correzione di F1):** in F1 `.sertor/uv.lock` è stato **committato**. Ma se il runtime traccia
HEAD e si re-locka ad ogni merge, un lock **committato** crea churn (un diff ad ogni merge) e un **loop**
(merge → re-lock → nuovo lock → commit → merge…). Il lock del dogfood va **gitignorato** (locale, sempre
l'HEAD corrente); resta committato **solo** `.sertor/pyproject.toml` (la spec stabile). *(I client, che
pinnano versioni, NON usano questo meccanismo → auto-updater E2-FEAT-013.)*

## 2. Obiettivi e criteri di successo
- **O1.** Dopo un merge su `master`, il runtime `.sertor/` del dogfood si porta all'**ultimo master mergiato**
  in modo **meccanico** (non a memoria dell'agente).
- **O2.** Nessun churn/loop di commit: il lock del runtime è **locale** (gitignorato).

**Criteri di successo (misurabili):**
- **SC-1:** esiste un passo **deterministico** (hook e/o script) che esegue il re-lock del runtime a HEAD;
  il rituale post-merge lo include **prima** di re-index/smoke.
- **SC-2:** `.sertor/uv.lock` è **gitignorato** (git rm dal tracking); `.sertor/pyproject.toml` resta committato.
- **SC-3:** il re-lock avviene **solo se il runtime è indietro** rispetto al remote HEAD (check-then-act; non
  un `uv sync` costoso ad ogni evento).
- **SC-4:** un clone fresco ottiene un runtime a HEAD via `uv sync` in `.sertor/` (nessun lock committato che
  lo pinni a un vecchio commit).
- **SC-5:** `sertor-core` invariato; fail-loud se il re-lock fallisce (Principio XII), non degradare in silenzio.

## 3. Stakeholder e attori
- **Agente/dogfood** — gira sempre sull'ultimo master installato, senza passi manuali.
- **Manutentore** — non deve ricordarsi il re-lock; è cablato.
- **CI/clone fresco** — non serve il lock committato (uv sync risolve HEAD).

## 4. Ambito
### In ambito
- **Gitignore** di `.sertor/uv.lock` + `git rm` dal tracking (correzione F1).
- **Meccanismo** deterministico di re-lock (hook e/o script) + integrazione nel rituale post-merge.
- **Check-then-act:** re-lock solo se il runtime è dietro il remote HEAD.
### Fuori ambito
- L'auto-updater degli **ospiti** (versioni/tag, E2-FEAT-013) — storia separata.
- Re-lock degli asset (F4) o del `.venv` di sviluppo (resta editable, invariato).
- Cambi a `sertor-core`.

## 5. Requisiti funzionali (EARS)
- **REQ-001 (Event-driven).** When `master` has advanced beyond the runtime's locked commit, the mechanism
  shall re-lock the `.sertor/` runtime to the latest remote HEAD (`uv lock --upgrade` + `uv sync`).
- **REQ-002 (State-driven).** While the runtime is already at the latest HEAD, the mechanism shall be a
  **no-op** (no costly re-sync) — check-then-act.
- **REQ-003 (Ubiquitous).** `.sertor/uv.lock` shall be git-ignored and untracked; `.sertor/pyproject.toml`
  shall remain tracked (the stable runtime spec).
- **REQ-004 (Event-driven).** When a fresh clone runs the runtime setup, it shall resolve `sertor-core` to the
  latest HEAD (no committed lock pinning an old commit).
- **REQ-005 (Unwanted behaviour).** If the re-lock fails (network/resolution), then the mechanism shall report
  an actionable error (fail-loud, Principio XII) and not silently leave a stale runtime.
- **REQ-006 (Ubiquitous).** The re-lock shall run only through vehicles (`uv`), never importing `sertor_core`;
  `sertor-core` unmodified.

## 6. Requisiti non funzionali
- **NFR-1 (deterministico):** il passo è meccanico (hook/script), non a discrezione dell'agente (confine D↔N).
- **NFR-2 (costo):** il check è cheap (confronto commit lockato ↔ remote HEAD); il re-sync avviene solo se serve.
- **NFR-3 (rete):** `uv lock --upgrade` richiede rete (risolve da `git=<repo>`); dichiarato; fail-loud se offline.

## 7. Vincoli, assunzioni e dipendenze
- **Dipendenza:** F1 ✅ (il runtime `.sertor/` esiste).
- **Vincolo:** il re-lock pulla da `git=<repo>` = **remote** → i merge di sessione devono essere **pushati**
  (lo sono: push prima del merge). Il dogfood segue il remote HEAD, non il working tree locale (voluto).
- **Assunzione:** non esiste un hook «post-merge» in Claude Code → il trigger sarà SessionStart (check+induci)
  e/o SessionEnd (re-lock dopo il push/merge di sessione), sul modello di `rag-freshness-*`.

## 8. Rischi
- **R-1 (loop di commit):** se il lock restasse committato + re-lockato → diff/loop ad ogni merge.
  *Mitigazione:* REQ-003 (gitignore il lock).
- **R-2 (re-lock costoso ad ogni evento):** *Mitigazione:* REQ-002 (check-then-act).
- **R-3 (rete assente):** re-lock fallisce. *Mitigazione:* fail-loud + retry alla prossima occasione.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-006.
- **Should:** REQ-004, NFR-2.

## 10. Domande aperte
- **VINCOLO (correzione 2026-07-03):** il re-lock-a-HEAD è **DOGFOOD-ONLY** (i client pinnano versioni +
  auto-updater E2-FEAT-013, NON tracciano HEAD). Quindi **NON** va negli asset **distribuiti** (es. il hook
  `rag-freshness.ps1` è sincronizzato/installato sui client → leakkerebbe). Il meccanismo dev'essere
  **dogfood-local** (script in `scripts/dev/` + wiring dogfood-only), **oppure** distribuito **ma guardato**
  (fire solo se il runtime sorgente da `git=<repo>`, no-op per chi pinna una versione).
- **Q1 [design→plan]:** meccanismo dogfood-local — (a) **script** `scripts/dev/relock-runtime.ps1` chiamato
  dal **rituale post-merge** (main-flow); (b) script + **hook dogfood-only** in `settings.json` (SessionEnd,
  non bundlato) — deterministico ma fragile al sync; (c) re-lock **distribuito guardato** «solo se runtime
  git-tracking» (general per client bleeding-edge, ma aggiunge logica al hook client). *Raccomandazione:* (a)
  o (c)-guardato, da decidere in plan col confine dogfood↔distribuito.
- **Q2 [design→plan]:** rilevare cheap che il runtime è dietro HEAD — confronto commit risolto (`uv.lock` /
  `.sertor/.venv` sertor-core `__version__`/dist-info) ↔ `git rev-parse origin/master`.
