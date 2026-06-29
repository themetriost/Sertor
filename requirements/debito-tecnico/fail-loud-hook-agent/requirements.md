# Requisiti — Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent

<!-- Deriva da: FEAT-019 (epica debito-tecnico) — audit asset first-party 2026-06-26, ISSUE-05 -->

## 1. Contesto e problema (perché)

La costituzione impone il **Principio XII «Fail Loud, Fix the Cause»**: una rottura non va silenziata
per schivare un errore. Due classi di asset *first-party* distribuiti agli ospiti lo violano:

1. **Hook di lifecycle che inghiottono gli errori in silenzio.** Diversi hook PowerShell distribuiti
   via `sertor install rag`/`wiki` racchiudono il lavoro in `try/catch` con `catch` vuoti e
   redirezione `2>$null`, ed escono **sempre `exit 0`** senza lasciare alcuna traccia. Una rottura
   dell'archiviazione memoria, del re-index, dello scan wiki o del version-check resta **invisibile
   per settimane**: nessun segnale, nessun artefatto ispezionabile. Esempi ancorati:
   - `…/assets/rag/hooks/memory-capture.ps1:74-90` — tutti i `catch` vuoti, `2>$null`, nessun breadcrumb.
   - `…/assets/rag/hooks/rag-freshness.ps1:172-175` (errore interno del worker), `:209-212` (spawn del
     worker fallito), `:99-102` (`doctor` fallito), `:164-168` (`index` fallito) — path catastrofici
     muti. (Il verdetto `degraded` è già fail-loud su stderr, `:154-159`.)
   - `…/assets/claude/hooks/wiki-pending-check.ps1:70-73` — `catch { exit 0 } # silent hook, no noise`
     sulla CLI `sertor-wiki-tools scan` non risolvibile.
   - `…/assets/rag/hooks/version-check.ps1:166-168` — `catch { } # Catastrophic internal error: silent`.

2. **Agent che leggono un asset esterno «ed eseguono» senza fallback.** Tre subagent dipendono da un
   asset (skill o playbook) che leggono come prima azione, ma **non prevedono il caso in cui quell'asset
   non sia risolvibile/leggibile**: proseguono «a vuoto» invece di fermarsi e segnalare. Ancorati:
   - `…/assets/rag/agents/concierge.md:12,26-27,32-33` — «follow the `guided-setup` skill … you never
     reimplement», nessun «skill assente → STOP».
   - `…/assets/claude/agents/wiki-curator.md:12-18` — «`Read` that file as your first action», nessun
     «playbook assente → STOP».
   - `…/assets/sertor-flow/.../agents/requirements-analyst.md:13` — «La procedura autorevole è nella
     skill `requirements`. **Leggila ed eseguila.**», nessun fallback.

**Valore:** una rottura silenziosa lascia una traccia ispezionabile (l'opposto del dogfooding cieco);
gli agent non procedono a vuoto quando manca l'asset di cui sono guscio. È debito di **affidabilità**
(Principio XII) e di **onestà** del comportamento distribuito agli ospiti.

## 2. Obiettivi e criteri di successo

- **CS-1** Ogni hook distribuito che oggi sopprime in silenzio il fallimento di un'operazione delegata
  o un errore interno catastrofico, quando degrada **lascia una traccia ispezionabile** che identifica
  *quale hook*, *quando* e *cosa* è fallito — verificabile provocando il fallimento e trovando la traccia.
- **CS-2** L'invariante di non-fatalità è **preservato**: gli hook continuano a uscire `exit 0` sempre e
  a non rompere la chiusura/avvio sessione; la scrittura della traccia è essa stessa best-effort e non
  introduce un nuovo percorso fatale.
- **CS-3** I 3 agent (`concierge`, `wiki-curator`, `requirements-analyst`), quando l'asset di cui sono
  guscio non è risolvibile/leggibile, **si fermano e segnalano** invece di procedere — verificabile dal
  testo del body (istruzione di fallback presente e inequivocabile).
- **CS-4** Nessun segreto compare nella traccia (parità con la disciplina di privacy del progetto).
- **CS-5** Parità host-agnostica preservata: i body degli agent restano byte-identici Claude↔Copilot;
  le modifiche agli hook valgono su entrambe le famiglie di distribuzione; le guardie di parità/sync
  restano verdi.
- **CS-6** Una **guardia anti-regressione** fallisce se un hook distribuito reintroduce un `catch`
  silenzioso (senza breadcrumb) o se un dei 3 agent perde l'istruzione di fallback.

## 3. Stakeholder e attori

- **Operatore/utente ospite** — ispeziona la traccia quando «qualcosa non torna» (memoria non
  archiviata, indice stantio).
- **Agente frontier dell'ospite** — all'avvio può rilevare la traccia e indurre la correzione.
- **Manutentore di Sertor** — la guardia anti-regressione protegge l'invariante in CI.

## 4. Ambito

### In ambito
- I **hook distribuiti** che sopprimono in silenzio un fallimento operativo/catastrofico:
  `memory-capture`, `rag-freshness` (path catastrofici), `wiki-pending-check`, `version-check`.
- Il **fallback «asset mancante → STOP e segnala»** nei body dei 3 agent: `concierge`, `wiki-curator`,
  `requirements-analyst` (decisione utente: **regola uniforme** per tutti e 3, senza path di
  auto-recupero differenziato).
- Una **convenzione del breadcrumb** riusabile dagli hook (formato/posizione decisi in fase di design).
- Le **copie dogfood** sotto `.claude/` sincronizzate con gli asset canonici + guardie di sync/parità.
- Cross-pacchetto: asset in **`sertor`** (hook + `concierge` + `wiki-curator`) e **`sertor-flow`**
  (`requirements-analyst`).

### Fuori ambito
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle: la feature è **additiva e host-facing**,
  zero codice di runtime del core (Principio XI). Gli hook continuano a non importare `sertor_core`.
- **Portabilità OS degli hook** (guardia `pwsh`/gemello bash) e **onestà sui surface Copilot inerti**
  → sono **FEAT-018** (audit ISSUE-04), feature separata.
- **Pulizia stile/altitude** dei body e dei blocchi `CLAUDE.md` → FEAT-021/FEAT-022.
- **Lettura/consumo attivo** della traccia da parte dell'agente come comportamento automatico
  enforced: qui si garantisce *che la traccia esista e sia ispezionabile*; l'eventuale induzione
  automatica all'avvio è un follow-up (gli hook `*-start` esistenti già inducono su stato `degraded`).
- Gli hook **read-only/puri** che non delegano lavoro (`wiki-session-start`, `rag-freshness-start`,
  `version-check-start`) e l'hook **già fail-loud** `sertor-rag-usage-check` (scrive su stderr by
  design): non hanno il difetto di silent-swallow operativo; classificati ma non modificati salvo che
  emerga un caso di soppressione silenziosa di stato illeggibile (vedi REQ-006).

## 5. Requisiti funzionali (EARS)

### Hook — fail-loud breadcrumb

- **REQ-001** When a distributed hook suppresses the failure of a delegated operation (a CLI/vehicle
  invocation) or a catastrophic internal error that previously degraded silently, the hook shall record
  an inspectable breadcrumb before exiting.
- **REQ-002** The breadcrumb shall identify, at minimum, *which hook* produced it, *when* (UTC
  timestamp) and *what* failed (a short, human-readable reason).
- **REQ-003** The breadcrumb shall persist beyond the session in which it was produced, so that it can
  be inspected at a later session start or by the user.
- **REQ-004** While memory/feature gates are unset such that a hook is a deliberate no-op (e.g.
  `SERTOR_MEMORY` disabled → `memory-capture` exits 0), the hook shall NOT record a breadcrumb (a
  gated no-op is not a failure).
- **REQ-005** If recording the breadcrumb itself fails, then the hook shall still exit 0 and shall not
  break the session (the breadcrumb write is best-effort and never fatal).
- **REQ-006** Where a distributed hook reads runtime state it owns (e.g. a health/version state file)
  and that read fails in a way that hides a real problem, the hook shall treat that as a degradation
  and record a breadcrumb per REQ-001..003 (covers the read-only start hooks under the general rule).
- **REQ-007** The hook shall continue to exit 0 in all paths (non-fatal invariant preserved), including
  the degraded paths that now emit a breadcrumb.
- **REQ-008** The breadcrumb shall not contain secrets or sensitive `.env` content; any reason text
  derived from external output shall already be scrubbed by the producing vehicle or kept to
  hook-local, secret-free strings.
- **REQ-009** While a hook degrades, the breadcrumb mechanism shall be consistent (shared convention)
  across the in-scope hooks, so a consumer can locate and read it uniformly.

### Agent — fallback «asset mancante → STOP»

- **REQ-010** The `concierge` agent body shall instruct: if the `guided-setup` skill cannot be
  resolved or read, STOP and signal the missing asset to the user, rather than proceeding.
- **REQ-011** The `wiki-curator` agent body shall instruct: if the wiki playbook (`wiki-playbook.md`)
  or a required `ops/` module cannot be resolved or read, STOP and signal the missing asset, rather
  than proceeding.
- **REQ-012** The `requirements-analyst` agent body shall instruct: if the `requirements` skill cannot
  be resolved or read, STOP and signal the missing asset, rather than proceeding (uniform rule, no
  differentiated inline-taxonomy self-recovery path — user decision).
- **REQ-013** The agent fallback instructions shall be expressed in each agent body as host-agnostic
  text (no `.claude/` path, no slash-command, no Claude-only model/product name), so the body stays
  byte-identical across Claude and Copilot.

### Distribuzione, parità, anti-regressione

- **REQ-014** When the canonical assets under `packages/**/assets/` are modified, the dogfood copies
  under `.claude/` shall be re-synced so the two stay byte-identical (existing sync guard stays green).
- **REQ-015** The feature shall provide an anti-regression test that fails if an in-scope distributed
  hook reintroduces a silent suppression (a degraded path with no breadcrumb), or if any of the 3
  agents loses its «asset missing → STOP» fallback instruction.
- **REQ-016** The runtime breadcrumb artifact shall not be committed to the host repository (it is
  runtime state, like `.sertor/.rag-health.json`), and shall be covered by the appropriate
  ignore/uninstall handling so a host does not accumulate or version it.
- **REQ-017** The change shall be additive to the installer: no removal of an existing capability; the
  install/upgrade/uninstall lifecycle of the touched assets shall remain consistent.

## 6. Requisiti non funzionali

- **NFR-1 (Costituzione)** Realizza il Principio XII «Fail Loud, Fix the Cause»; nessuna deroga attesa.
- **NFR-2 (Principio XI)** Gli hook non importano `sertor_core` e non chiamano un LLM; solo wrapper
  sottili attorno ai vehicle/file.
- **NFR-3 (Privacy)** Nessun segreto nella traccia (NFR allineato a REQ-008).
- **NFR-4 (Host-agnostico, Principio X)** Le modifiche valgono su qualunque ospite e su entrambe le
  famiglie d'assistente; nessun path hardcodato a un progetto specifico.
- **NFR-5 (Non-bloccante/non-fatale)** Costo trascurabile alla chiusura/avvio sessione; mai un nuovo
  percorso che blocca o rompe la sessione.
- **NFR-6 (Additività core)** `sertor-core` invariato; la feature è di soli asset host-facing + test.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo:** gli hook restano PowerShell-only nello scope di questa feature (la portabilità OS è
  FEAT-018); ci si limita a rendere fail-loud i path già presenti, senza riscrivere il wiring.
- **Assunzione (design, da confermare in plan):** il breadcrumb è un **artefatto persistente sotto
  `.sertor/`** (candidato `.sertor/.last-hook-error`, gemello di `.rag-health.json`) eventualmente
  affiancato da una nota su stderr; «last error» (sovrascritto) salvo diversa decisione di plan.
- **Assunzione:** `requirements-analyst` mantiene la tassonomia EARS inline che già possiede, ma —
  per decisione utente — il fallback è **STOP+segnala uniforme**, non auto-recupero silenzioso.
- **Dipendenza:** sincronizzazione asset bundlati→`.claude/` (`sertor_installer.sync`) e guardie
  `test_assets_sync.py` / parità Copilot già esistenti.
- **Dipendenza:** se il breadcrumb è un file nuovo sotto `.sertor/`, va coperto dagli ignore di runtime
  (gemello del trattamento di `.rag-health.json`).

## 8. Rischi

- **R-1** Over-scoping: «tutti gli hook che inghiottono errori» potrebbe gonfiare il diff. Mitigazione:
  scope ancorato alla classificazione del §4 (4 hook operativi in scope; read-only/già-loud esclusi
  salvo REQ-006).
- **R-2** Reintrodurre rumore: un breadcrumb troppo verboso/loud potrebbe degradare la UX di chiusura
  sessione. Mitigazione: traccia su file persistente (silenziosa) + eventuale nota stderr minima.
- **R-3** Drift dogfood↔bundle non colto: le copie `.claude/` divergono. Mitigazione: REQ-014 + guardie.
- **R-4** Falsa sensazione di completezza: la traccia esiste ma nessuno la legge. Mitigazione: gli hook
  `*-start` già inducono su `degraded`; il consumo attivo esteso è follow-up dichiarato (§4 fuori ambito).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-007, REQ-008, REQ-010, REQ-011, REQ-012, REQ-013,
  REQ-014, REQ-015.
- **Should:** REQ-004, REQ-006, REQ-009, REQ-016, REQ-017.
- **Could:** consumo attivo automatico della traccia all'avvio (oltre l'induzione `degraded` già
  esistente) — candidato follow-up.
- **Won't (qui):** portabilità OS/gemello bash (FEAT-018); pulizia stile/altitude (FEAT-021/022).

## 10. Domande aperte

- **[RISOLTA — utente]** Scope hook = **tutti** gli hook che inghiottono errori (non solo i 2 segnalati)
  → ancorato alla classificazione del §4.
- **[RISOLTA — utente]** Fallback agent = **STOP+segnala uniforme** per tutti e 3.
- **[DA CHIARIRE in plan/clarify]** Meccanismo del breadcrumb: file persistente `.sertor/.last-hook-error`
  (sovrascritto) vs append-log con storia vs solo stderr — e se affiancare comunque una nota stderr.
- **[DA CHIARIRE in plan]** Granularità: una singola traccia «ultimo errore» condivisa vs una per hook.
- **[DA CHIARIRE in plan]** Forma della guardia anti-regressione (lint statico sui body degli hook per
  `catch` vuoti senza breadcrumb + assert sulla presenza dell'istruzione di fallback negli agent).
