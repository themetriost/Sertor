# Requisiti — Installer preservante su `plan-template.md`

<!-- Deriva da: E15-FEAT-005 (epica fedelta-dogfood) ≡ E10-FEAT-028 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

Perché il dogfood (e qualunque ospite) possa girare il **vero `sertor-flow install`** senza perdere
personalizzazioni curate, l'installer non deve **clobberare** `.specify/templates/plan-template.md`.

Oggi lo clobbera: `sertor-flow install` esegue come **Step 0** `launch_speckit` → `specify init --force`
(`install_governance.py` → `speckit_launch.py:build_specify_command`), che **sovrascrive**
`plan-template.md` con il template upstream vanilla; e `plan-template.md` **non è nel piano Sertor**
(`build_governance_plan`) → **niente lo ripristina**. La versione customizzata (in Sertor: il **mission-gate
/ Constitution Check**) viene persa.

**Circoscritto empiricamente (spike + test isolato 2026-07-03):** `specify init --force` **NON** tocca
`.specify/memory/constitution.md` (create-if-absent → la v1.4.0 sopravvive) né `.specify/feature.json`.
**L'unico** artefatto curato clobberato è `plan-template.md` → questa feature è **un solo file**, non una
revisione dell'installer.

## 2. Obiettivi e criteri di successo

- **O1.** Un ospite con un `plan-template.md` **customizzato** che esegue/ri-esegue `sertor-flow install`
  **conserva** la propria versione (nessuna perdita del mission-gate).
- **O2.** Comportamento **host-agnostico**: si preserva **qualunque** customizzazione dell'ospite, senza
  imporre una versione Sertor-specifica (Principio X).
- **O3.** Nessuna regressione su un ospite **pulito** (plan-template = quello upstream da `specify init`).

**Criteri di successo (misurabili):**
- **SC-1:** dopo `sertor-flow install` su un host con `plan-template.md` customizzato, il file è
  **byte-identico** a prima (verificabile con hash pre/post, come lo fa lo script del dogfood oggi).
- **SC-2:** su un host **pulito**, `plan-template.md` è quello depositato da `specify init` (nessuna
  regressione, nessun file inventato).
- **SC-3:** idempotente — ri-eseguire l'install lascia lo stato stabile.
- **SC-4:** `sertor-core` **invariato**; la modifica vive in `packages/sertor-flow`.

## 3. Stakeholder e attori
- **Dogfood di Sertor** — deve poter fare self-install senza perdere il `plan-template.md` col mission-gate
  (sblocca F1/il modello install-based).
- **Ospite che customizza il plan-template** — beneficia della stessa preservazione.
- **CI** — un test che pinna la preservazione (no regressione).

## 4. Ambito
### In ambito
- Preservazione di `plan-template.md` **esistente** attraverso lo Step 0 (`specify init --force`) di
  `sertor-flow install` (install **e** upgrade).
### Fuori ambito
- Preservare **altri** artefatti (costituzione/`feature.json` non sono clobberati; verificato). Se lo spike
  futuro trovasse **nuovi** clobber, sono feature separate.
- Distribuire una versione Sertor-specifica del plan-template agli ospiti (violerebbe X).
- Cambi a `specify init` upstream o a `sertor-core`.

## 5. Requisiti funzionali (EARS)
- **REQ-001 (Unwanted behaviour).** If a customized `plan-template.md` exists before `sertor-flow install`,
  then the installer shall ensure that after the run the file retains the host's customized content (not the
  vanilla upstream that `specify init --force` deposits).
- **REQ-002 (Ubiquitous).** The preservation shall be host-agnostic — it preserves the host's existing
  `plan-template.md` as-is, without imposing any Sertor-specific template.
- **REQ-003 (State-driven).** While no `plan-template.md` exists before install (fresh host), the installer
  shall leave the upstream template that `specify init` deposits (no regression, no invented file).
- **REQ-004 (Ubiquitous).** The behaviour shall be idempotent: a second `sertor-flow install` leaves
  `plan-template.md` stable.
- **REQ-005 (Event-driven).** When the preservation cannot be completed (e.g. the file could not be
  read/restored), the installer shall **fail loud** (report an actionable error), never leave the clobbered
  vanilla silently in place (Principio XII).
- **REQ-006 (Ubiquitous).** The change shall leave `sertor-core` unmodified (Principle XI) and live in
  `packages/sertor-flow`.

## 6. Requisiti non funzionali
- **NFR-1 (no data loss):** la preservazione non deve mai lasciare l'ospite peggio di prima (né vanilla né
  file corrotto/parziale).
- **NFR-2 (offline/test):** verificabile da un test offline con un runner `specify init` mockato (come già
  esiste `FakeSpecifyRunner`) **più** un pin sul comportamento reale se fattibile.
- **NFR-3 (report onesto):** l'esito (preservato/creato-fresh) compare nel report d'install
  (`InstallReport`), coerente con gli altri passi.

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo/ordine:** `launch_speckit` (Step 0) gira **prima** del piano Sertor (`install_governance.py`).
  La fix opera attorno a questo ordine (backup pre-Step-0 + restore post, **o** un passo di piano
  replace-after).
- **Assunzione verificata:** `specify init --force` clobbera SOLO `plan-template.md` (non costituzione/
  feature.json). Se ciò cambiasse con un pin spec-kit futuro, va ri-verificato.
- **Verificato nel codice:** `FakeSpecifyRunner` (`conftest.py:72-75`) **già** scrive `plan-template.md`
  incondizionatamente nel layout → **clobbera** il plan-template come il `--force` reale (è la **costituzione**
  a essere create-if-absent). Quindi il test della fix è significativo col fake attuale, **senza** modifiche.

## 8. Rischi
- **R-1:** un test che pre-piazza un plan-template **identico** al mock del fake non esercirebbe la
  preservazione. *Mitigazione:* il test usa contenuto customizzato **distinto** dal mock del fake.
- **R-2 (RISOLTO):** scelta meccanismo = **(a) backup/restore** (decisione utente 2026-07-03) — host-agnostico,
  nessuna fonte canonica.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-006.
- **Should:** REQ-004, NFR-3.

## 10. Domande aperte
- **Q1 [bivio → plan]:** meccanismo di preservazione — **(a) backup/restore** (l'installer salva
  `plan-template.md` prima dello Step 0 e lo ripristina dopo; host-agnostico, preserva *qualunque*
  customizzazione) vs **(b) replace-if-upstream** (dopo lo Step 0, l'installer riscrive la versione
  "corretta"; ma quale? servirebbe una fonte canonica → rischia di imporre una versione). *Raccomandazione
  provvisoria: (a)* — più host-agnostica, nessuna fonte canonica da distribuire.

---

**Commit proposto:** `docs(requirements): E15-FEAT-005/E10-FEAT-028 requisiti — installer preservante plan-template`
