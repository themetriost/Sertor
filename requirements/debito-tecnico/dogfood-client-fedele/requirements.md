# Requisiti — Il dogfood di Sertor come client Sertor fedele (machinery SpecKit)

<!-- Deriva da: E10-FEAT-027 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

Il workspace di Sertor fa **dogfooding** del proprio metodo SDLC (SpecKit + governance), ma **non è un
client fedele di sé** sul fronte SpecKit. Un progetto ospite che installa Sertor
(`sertor-flow install --assistant claude` → `specify init`, feature 045) riceve la **machinery SpecKit**
materializzata: `.claude/skills/speckit-*/SKILL.md`, `.specify/scripts/powershell/*`, template completi.
Il dogfood **non ce l'ha**: è tracciato sotto `.specify/` solo `feature.json`, `memory/constitution.md`,
`templates/plan-template.md`; mancano skill, script e gli altri template.

Simmetricamente, il dogfood **porta 9 agenti hand-authored** `.claude/agents/speckit-*.md` che **nessun
client riceve** — la guardia `packages/sertor-flow/tests/unit/test_no_vendored_speckit.py`
(`test_no_vendored_speckit_agents`) vieta questi agenti negli asset distribuiti. Quegli agenti puntano
proprio alle skill+script **assenti** → 9 riferimenti morti. Sono **residuo pre-pivot 045** (quando Sertor
vendorava SpecKit).

Questo è un **doppio special-case** dogfood↔client. Emerso dall'item A-05 dell'audit SWOT (2026-07-02):
un primo fix (de-reference dei 9 agenti + guardia che *tollerava* le skill assenti) è stato **ritirato**
perché *incistava* la divergenza invece di risolverla. Principio di riferimento (2026-07-03): *il workspace
Sertor deve lavorare come un progetto-cliente di Sertor; ogni divergenza dal client è debito tecnico.*

## 2. Obiettivi e criteri di successo

- **O1.** Il dogfood **esercita** lo stesso percorso d'install/layout SpecKit di un ospite reale.
- **O2.** I riferimenti SpecKit degli asset **risolvono** (nessun link morto) senza tollerare la loro assenza.
- **O3.** Nessuno special-case dogfood-only che diverga dal client (asset che nessun ospite ha; machinery
  che ogni ospite riceve ma qui manca).
- **O4.** Zero re-vendoring: la machinery upstream **non** finisce committata (evita drift di pin — lo
  stesso motivo del pivot launch-installer 045).

**Criteri di successo (misurabili, tech-agnostici):**
- SC-1: dopo il setup del dogfood, ogni skill/script SpecKit referenziato dagli asset **esiste** (0
  riferimenti irrisolti).
- SC-2: `git diff` non introduce **alcun** file di machinery SpecKit rigenerabile (0 copie upstream tracciate).
- SC-3: **0** agenti `.claude/agents/speckit-*.md` hand-authored nel repo.
- SC-4: gli artefatti Sertor-authored (`constitution.md` v1.4.0, `plan-template.md` custom, `feature.json`)
  restano **byte-identici** dopo la materializzazione.
- SC-5: `sertor-core` **invariato** (Principio XI); nessun cambio di codice di libreria.
- SC-6: una guardia in CI fallisce se un agente speckit hand-authored o una copia di machinery rientra.

## 3. Stakeholder e attori

- **Flusso principale (agente) del dogfood** — esegue le fasi SpecKit; oggi improvvisa «per convenzione»
  per l'assenza della machinery.
- **Manutentore Sertor** — deve poter clonare + fare un setup che rende il dogfood fedele.
- **CI** — deve cogliere il ritorno dello special-case.
- *(Indiretto)* **ospiti reali** — beneficiano perché il percorso d'install viene davvero esercitato.

## 4. Ambito

### In ambito
- Materializzazione **sicura e isolata** della machinery SpecKit per il **layout Claude** nel dogfood.
- Esclusione da git (gitignore) della machinery rigenerabile + **step di setup documentato**.
- Rimozione dei 9 agenti hand-authored `speckit-*` (End-state fedele = skill native).
- Guardia anti-regressione (no agenti speckit hand-authored; no machinery rigenerabile tracciata).
- Aggiornamento della documentazione di **setup dev** (il dogfood ottiene la machinery via install, come `uv sync`).

### Fuori ambito
- Il layout **Copilot** (`.github/prompts/speckit.*`): il dogfood è su Claude (eventuale estensione futura).
- Modifiche al **prodotto** `sertor-flow`/installer o al comando `specify init` (si **consuma** il percorso
  esistente; se serve un entrypoint di sola-materializzazione, è decisione di design a valle).
- Ridistribuzione agli ospiti degli agenti hand-authored (contraddirebbe il pivot 045).
- Qualunque modifica a `sertor-core`.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous).** The dogfood workspace shall expose the same SpecKit surface that a Sertor
  client obtains from the install path — the native `speckit-*` skills and the `.specify/` scripts/templates
  — so that references to them from workspace assets resolve.
- **REQ-002 (Event-driven).** When the SpecKit machinery is materialized into the dogfood, the system shall
  preserve every Sertor-authored artifact (`.specify/memory/constitution.md`, the customized
  `.specify/templates/plan-template.md`, `.specify/feature.json`) byte-for-byte.
- **REQ-003 (Unwanted behaviour).** If materialization would overwrite a Sertor-authored artifact, then the
  system shall not perform that overwrite (isolate the upstream output and copy only regenerable machinery).
- **REQ-004 (Ubiquitous).** The regenerable SpecKit machinery (native `speckit-*` skills, `.specify/scripts/`,
  upstream-owned templates/workflows/integrations) shall be excluded from version control.
- **REQ-005 (Ubiquitous).** The repository shall contain no hand-authored `.claude/agents/speckit-*.md`.
- **REQ-006 (Event-driven).** When a hand-authored `.claude/agents/speckit-*.md`, or a tracked copy of the
  regenerable SpecKit machinery, is (re)introduced, a guard test shall fail.
- **REQ-007 (Ubiquitous).** The developer setup documentation shall describe the SpecKit-materialization
  step (how the dogfood obtains the machinery), analogous to `uv sync`.
- **REQ-008 (State-driven).** While the SpecKit machinery is absent (e.g. a fresh clone before setup), the
  dogfood shall degrade honestly — the setup step is documented and the absence is not silently tolerated by
  an asset that claims the machinery is present.
- **REQ-009 (Ubiquitous).** The change shall leave `sertor-core` unmodified (Principle XI): no library code touched.

## 6. Requisiti non funzionali

- **NFR-1 (no re-vendoring).** Nessuna copia della machinery upstream pinnata (v0.8.18) committata: evita
  drift di pin e ricalca il pivot 045.
- **NFR-2 (host-agnosticità del principio).** La soluzione dimostra la fedeltà dogfood↔client senza
  introdurre assunzioni Sertor-specifiche negli asset **distribuiti**.
- **NFR-3 (ripetibilità/offline della guardia).** La guardia gira in CI senza rete e senza la machinery
  materializzata (asserisce assenze/tracciamento, non presenze locali).
- **NFR-4 (sicurezza del setup).** La materializzazione non deve mai richiedere né esporre segreti, né
  toccare `.env`/`raw/`.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo.** `specify init` upstream con `--force` sovrascrive `.specify/memory/constitution.md` e i
  template con quelli di spec-kit → **non** eseguibile sul root del dogfood senza protezione (rischio
  costituzione **confermato** dal vivo). `plan-template.md` è **Sertor-customizzato** (mission gate).
- **Vincolo tecnico verificato.** `specify init` richiede l'overlay UTF-8 (`PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`,
  cfr. `_UTF8_ENV` in `speckit_launch.py`): senza, aborta `UnicodeEncodeError` su console cp1252.
- **Assunzione.** Il layout prodotto da `specify init --ai claude` v0.8.18 è quello osservato (9 skill +
  `.specify/scripts/powershell/{check-prerequisites,common,create-new-feature,setup-plan,setup-tasks}.ps1` +
  template + workflows/integrations); pinnato via `SPECKIT_VERSION = "0.8.18"`.
- **Dipendenza.** Rete disponibile per `uvx` (pull di spec-kit dal tag git) al momento del setup.
- **Dipendenza.** Presuppone il ritiro del fix de-reference di A-05 (già fatto, branch `087-a05-dogfood-client-debt`).

## 8. Rischi

- **R-1.** Materializzazione mal-isolata → clobber della costituzione v1.4.0. *Mitigazione:* REQ-003 (isolare
  + copia selettiva); SC-4 come gate.
- **R-2.** Perdita della **delega a subagent** delle fasi SpecKit rimuovendo i 9 agenti (un client usa le
  skill native in-context). *Mitigazione:* decisione dichiarata (vedi Domande aperte Q1); reversibile.
- **R-3.** La machinery gitignorata assente in CI/clone fresco → una fase SpecKit non gira finché non si fa
  il setup. *Mitigazione:* REQ-007 (doc) + REQ-008 (degradazione onesta).
- **R-4.** Drift del pin upstream (0.8.18) nel tempo. *Mitigazione:* la fonte del pin resta unica
  (`SPECKIT_VERSION`); niente copie tracciate (NFR-1).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-009 (fedeltà + sicurezza + guardia + zero core).
- **Should:** REQ-001, REQ-007 (surface risolta + doc di setup).
- **Could:** REQ-008 (degradazione onesta esplicita, se non già coperta dal doc).
- **Won't (qui):** layout Copilot; entrypoint di prodotto per la sola-materializzazione; ridistribuzione agenti.

## 10. Domande aperte

- **Q1 [bivio, default proposto].** Fato dei 9 agenti hand-authored `speckit-*`: **(a, default)** rimuoverli
  → il dogfood usa le skill native come un client (fedele; perde la delega a subagent); **(b)** tenerli come
  **wrapper funzionali** ora che le skill risolvono (aggiunge la delega come *estensione dogfood dichiarata*,
  ma resta client-divergente). L'utente ha indicato (a) («1 2 3» → R-B). *Raccomandazione: (a).*
- **Q2 [bivio, default proposto].** Machinery in git: **(a, default)** gitignore + step di setup (modello
  `.venv`, rigenerabile) vs **(b)** committare le copie upstream. *Raccomandazione: (a)* (NFR-1; stesso
  principio che ha escluso il "create" in A-05).
- **Q3 [design, a valle].** Come materializzare in sicurezza: **(a)** `specify init` in dir isolata + copia
  chirurgica della sola machinery rigenerabile; **(b)** un piccolo script/entrypoint dedicato di
  sola-materializzazione. Da risolvere in `plan` (tocca il "come", non il "cosa").
- **Q4 [scoping].** La materializzazione locale va **eseguita in questa feature** (rendere fedele la sessione
  corrente) o basta gitignore+doc + guardia, lasciando il `run` del setup al manutentore? *Raccomandazione:*
  eseguirla come parte dell'accettazione (dimostra la fedeltà end-to-end).

---

**Commit proposto (al `configuration-manager`):** `docs(requirements): E10-FEAT-027 requisiti feature — dogfood client-fedele`
