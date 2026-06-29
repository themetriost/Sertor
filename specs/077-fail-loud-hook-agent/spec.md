# Feature Specification: Fail-loud breadcrumb negli hook + fallback «asset mancante → STOP» negli agent (E10-FEAT-019)

**Feature Branch**: `077-fail-loud-hook-agent` · **Created**: 2026-06-29 · **Status**: Draft

<!-- Deriva da: FEAT-019 (epica debito-tecnico E10) — requirements/debito-tecnico/fail-loud-hook-agent/requirements.md (audit asset first-party 2026-06-26, ISSUE-05) -->

**Input**: FEAT-019 dell'epica `debito-tecnico` (E10). La costituzione impone il **Principio XII «Fail
Loud, Fix the Cause»**: una rottura non va silenziata per schivare un errore. Due classi di asset
*first-party* distribuiti agli ospiti lo violano. **(1)** Diversi hook PowerShell di lifecycle
(`memory-capture`, `rag-freshness` su path catastrofici, `wiki-pending-check`, `version-check`)
racchiudono il lavoro in `try/catch` con `catch` vuoti e redirezione `2>$null`, ed escono **sempre
`exit 0`** senza lasciare alcuna traccia: una rottura dell'archiviazione memoria, del re-index, dello
scan wiki o del version-check resta **invisibile per settimane** — nessun segnale, nessun artefatto
ispezionabile. **(2)** Tre subagent (`concierge`, `wiki-curator`, `requirements-analyst`) leggono un
asset esterno (una skill o un playbook) come **prima azione**, ma non prevedono il caso in cui
quell'asset non sia risolvibile/leggibile: **proseguono «a vuoto»** invece di fermarsi e segnalare. La
feature rende entrambe le classi *fail-loud*: una rottura silenziosa lascia una **traccia
ispezionabile** e gli agent **si fermano** quando manca l'asset di cui sono guscio. È debito di
**affidabilità** (Principio XII) e di **onestà** del comportamento distribuito agli ospiti.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e
> realtà del contesto reso all'agente**: RAG, wiki e lint esistono per impedire che un agente ragioni
> su contesto non reale. Un hook che inghiotte in silenzio il fallimento del re-index o
> dell'archiviazione memoria è esattamente il **modo in cui quel contesto degrada senza che nessuno se
> ne accorga** — il dogfooding cieco. Rendere fail-loud questi asset *protegge* la stella polare:
> quando l'apparato si rompe, il guasto si **vede** (traccia ispezionabile) invece di marcire. È
> coerente col confine **D↔N**: gli hook restano **meccanici** (scrivono una traccia, non ragionano,
> **non chiamano mai un LLM**); per gli agent l'istruzione di fallback è **giudizio** del body, non
> codice. Complementa l'enforcement della freschezza (FEAT-011): quella *previene* lo staleness, questa
> rende *visibile* ogni rottura residua del macchinario host-facing.

> **Natura del cambiamento: ADDITIVO + host-facing, ZERO codice di core.** La feature **non** modifica
> `sertor_core` né alcun comando/vehicle. Tocca **solo asset distribuiti** (script hook PowerShell +
> body markdown degli agent) e i loro test di guardia. Gli hook continuano a **non importare
> `sertor_core`** e a **non chiamare un LLM** (Principio XI): restano wrapper sottili attorno ai
> vehicle/file. Introduce: una **convenzione di breadcrumb** condivisa dagli hook in scope; un'istruzione
> di **fallback uniforme** nei 3 body degli agent; le **copie dogfood** `.claude/` ri-sincronizzate; una
> **guardia anti-regressione**. A comportamento sano (nessun fallimento) il funzionamento è invariato:
> gli hook continuano a uscire 0 senza scrivere nulla.

> **Decisione del breadcrumb — FISSATA (era la forca aperta del §10 dei requirements).** Il breadcrumb
> è un **file singolo persistente `.sertor/.last-hook-error`** (JSON con campi minimi `hook` /
> `ts` timestamp UTC / `reason` testo breve leggibile), **sovrascritto a ogni nuovo errore** —
> semantica **«ultimo errore»**, NON storia append, NON un file per hook — affiancato da una **nota
> minima su stderr**. È il **gemello esatto** di `.sertor/.rag-health.json`: stesso pattern, stessi
> ignore/uninstall di runtime, stessa collocazione sotto la radice `.sertor/`. La spec fissa questo come
> il design del breadcrumb; restano *come* di plan i punti precisi di scrittura nei singoli hook e la
> forma esatta della guardia.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Gli asset in scope esistono già e
> sono accertati: gli hook `…/assets/rag/hooks/memory-capture.ps1`, `…/assets/rag/hooks/rag-freshness.ps1`
> (path catastrofici), `…/assets/claude/hooks/wiki-pending-check.ps1`, `…/assets/rag/hooks/version-check.ps1`;
> i body `…/assets/rag/agents/concierge.md`, `…/assets/claude/agents/wiki-curator.md`,
> `…/assets/sertor-flow/.../agents/requirements-analyst.md`. Il file di stato runtime `.sertor/.rag-health.json`
> (FEAT-011) dà il **pattern di riferimento** (formato JSON, ignore/uninstall di runtime, collocazione
> `.sertor/`); le guardie `test_assets_sync.py` e di parità Copilot esistono già. I riferimenti
> **ancorano** i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Una rottura silenziosa di un hook lascia una traccia ispezionabile (P1, Must)
Un operatore ospite nota che «qualcosa non torna» (la memoria non è archiviata, l'indice resta stantio).
Oggi non trova nulla da ispezionare: l'hook è uscito 0 e ha inghiottito l'errore. Con la feature, quando
un hook in scope degrada — perché un'operazione delegata (un'invocazione CLI/vehicle) o un errore interno
catastrofico fallisce — lascia un **breadcrumb ispezionabile** che dice *quale hook*, *quando* e *cosa*
è fallito, prima di uscire.

**Independent Test**: si provoca il fallimento dell'operazione delegata da un hook in scope; al termine
esiste il file `.sertor/.last-hook-error` coi campi `hook` (nome dell'hook), `ts` (timestamp UTC) e
`reason` (motivo breve leggibile); una nota minima è comparsa su stderr.

**Acceptance**:
1. **Given** un hook in scope (`memory-capture` / `rag-freshness` su path catastrofico /
   `wiki-pending-check` / `version-check`), **When** l'operazione delegata o un errore interno
   catastrofico fallisce, **Then** l'hook registra un breadcrumb ispezionabile **prima** di uscire.
2. **Given** il breadcrumb scritto, **When** lo si ispeziona, **Then** identifica almeno *quale hook*,
   *quando* (timestamp UTC) e *cosa* è fallito (motivo breve, leggibile da un umano).
3. **Given** più hook in scope, **When** ciascuno degrada, **Then** usa la **stessa convenzione**
   condivisa (`.sertor/.last-hook-error`), così l'operatore la individua e la legge in modo uniforme.

### User Story 2 — La traccia sopravvive alla sessione e l'invariante non-fatale è preservato (P1, Must)
La traccia deve poter essere ispezionata **più tardi** (a un avvio di sessione successivo o dall'utente),
quindi è persistita su file, non solo emessa a schermo. Allo stesso tempo l'invariante storico degli hook
non cambia: escono **sempre `exit 0`** e non rompono la chiusura/avvio di sessione — **anche se la
scrittura del breadcrumb stessa fallisce** (è best-effort, mai un nuovo percorso fatale).

**Independent Test**: dopo un fallimento, il file `.sertor/.last-hook-error` persiste oltre la sessione
in cui è stato prodotto; in uno scenario in cui la scrittura del breadcrumb non è possibile (es. path non
scrivibile), l'hook esce comunque 0 senza interrompere la sessione.

**Acceptance**:
1. **Given** un breadcrumb prodotto in una sessione, **When** la sessione termina, **Then** il file
   persiste ed è leggibile a un avvio successivo o dall'utente.
2. **Given** un hook in scope su qualunque path (sano, degradato, o con scrittura breadcrumb fallita),
   **When** termina, **Then** esce **sempre 0** e non blocca/rompe il ciclo di vita della sessione.
3. **Given** che la scrittura del breadcrumb stessa fallisca, **When** l'hook prosegue, **Then** non
   introduce un nuovo percorso fatale: la traccia è best-effort, l'uscita resta 0.

### User Story 3 — Un no-op gated NON lascia traccia (P2, Should)
Quando un hook è un **no-op deliberato** perché un gate di feature è spento (es. `SERTOR_MEMORY`
disabilitato → `memory-capture` esce 0 senza fare nulla), questo **non è un fallimento**: l'hook non deve
scrivere alcun breadcrumb. Una traccia su un no-op gated sarebbe rumore e falserebbe la semantica «ultimo
errore».

**Independent Test**: con `SERTOR_MEMORY` spento, `memory-capture` esce 0 e **non** crea/sovrascrive
`.sertor/.last-hook-error`.

**Acceptance**:
1. **Given** un gate di feature spento che rende un hook un no-op deliberato, **When** l'hook esegue,
   **Then** esce 0 e **non** registra alcun breadcrumb.
2. **Given** un breadcrumb preesistente di un errore reale, **When** un hook gira come no-op gated,
   **Then** non lo sovrascrive (un no-op non è l'«ultimo errore»).

### User Story 4 — Un hook che legge stato di runtime proprio e fallisce in modo cieco degrada con traccia (P2, Should)
Dove un hook distribuito legge uno **stato di runtime che possiede** (es. un file di salute/versione) e
quella lettura fallisce in un modo che **nasconde un problema reale**, l'hook tratta il fatto come una
**degradazione** e registra un breadcrumb, invece di passare oltre in silenzio. Questo estende la regola
generale agli hook di avvio read-only, senza riclassificarli come hook che «delegano lavoro».

**Independent Test**: si rende illeggibile/corrotto lo stato di runtime che un hook in scope legge; l'hook
registra un breadcrumb per la lettura fallita e resta non-fatale (exit 0).

**Acceptance**:
1. **Given** un hook che legge uno stato di runtime proprio, **When** la lettura fallisce nascondendo un
   problema reale, **Then** l'hook lo tratta come degradazione e registra un breadcrumb (US1).
2. **Given** quel breadcrumb, **When** lo si ispeziona, **Then** rispetta la stessa convenzione e non
   rende l'hook fatale.

### User Story 5 — Nessun segreto compare nella traccia (P1, Must)
La traccia rispetta la disciplina di privacy del progetto: **non contiene segreti né contenuto sensibile
di `.env`**. Qualunque testo di `reason` derivato da output esterno è già scrubbato dal vehicle che lo
produce, oppure è mantenuto a stringhe locali all'hook, prive di segreti.

**Independent Test**: si provocano fallimenti i cui messaggi potrebbero contenere valori sensibili; il
breadcrumb risultante non contiene segreti né valori `.env`.

**Acceptance**:
1. **Given** un fallimento il cui output potrebbe includere materiale sensibile, **When** l'hook scrive il
   breadcrumb, **Then** il `reason` non contiene segreti né contenuto di `.env`.
2. **Given** il `reason` derivi da output di un vehicle, **When** lo si registra, **Then** è già scrubbato
   alla fonte o ridotto a una stringa locale all'hook, priva di segreti.

### User Story 6 — I 3 agent si fermano quando l'asset di cui sono guscio non è risolvibile (P1, Must)
`concierge`, `wiki-curator` e `requirements-analyst` leggono come prima azione un asset esterno (la skill
`guided-setup`; il `wiki-playbook.md` e i suoi moduli `ops/`; la skill `requirements`). Se quell'asset
**non è risolvibile/leggibile**, oggi proseguono a vuoto. Con la feature, ciascun body istruisce una regola
**uniforme**: «asset mancante → **STOP** e segnala all'utente l'asset mancante», senza un path di
auto-recupero differenziato.

**Independent Test**: il body di ciascuno dei 3 agent contiene un'istruzione **inequivocabile** che, se
l'asset richiesto non può essere risolto/letto, l'agente si **ferma e segnala** invece di procedere. (Il
comportamento runtime vero è verificabile solo con test live — vedi nota sotto.)

**Acceptance**:
1. **Given** il body di `concierge`, **When** lo si legge, **Then** istruisce: se la skill `guided-setup`
   non è risolvibile/leggibile, **STOP** e segnala l'asset mancante, anziché procedere.
2. **Given** il body di `wiki-curator`, **When** lo si legge, **Then** istruisce: se il `wiki-playbook.md`
   o un modulo `ops/` richiesto non è risolvibile/leggibile, **STOP** e segnala l'asset mancante.
3. **Given** il body di `requirements-analyst`, **When** lo si legge, **Then** istruisce: se la skill
   `requirements` non è risolvibile/leggibile, **STOP** e segnala l'asset mancante (regola uniforme,
   nessun auto-recupero differenziato).

> **Nota sul confine D↔N (parte agent = giudizio).** La presenza dell'istruzione nel body è verificabile
> **staticamente** (guardia sul testo, vedi US8). Che l'agente *effettivamente* si fermi è comportamento
> di un LLM e si verifica solo con **test live / dogfooding** su un ospite reale: la spec lo dichiara come
> tale e non lo finge come test deterministico.

### User Story 7 — Il fallback agent resta host-agnostico e byte-identico Claude↔Copilot (P1, Must)
L'istruzione di fallback è espressa nei body con **testo host-agnostico**: niente path `.claude/`, niente
slash-command, niente nome-modello/prodotto Claude-only. Così il body resta **byte-identico** tra Claude e
Copilot e le guardie di parità restano verdi.

**Independent Test**: il testo del fallback nei 3 body non contiene path `.claude/`, slash-command o
nomi-modello/prodotto Claude-only; il body è byte-identico nelle due famiglie di distribuzione.

**Acceptance**:
1. **Given** i 3 body con il fallback, **When** li si confronta tra Claude e Copilot, **Then** sono
   byte-identici.
2. **Given** il testo del fallback, **When** lo si ispeziona, **Then** non contiene `.claude/`,
   slash-command, né nome-modello/prodotto Claude-only (host-agnostico).
3. **Given** le guardie di parità esistenti, **When** girano dopo la feature, **Then** restano verdi.

### User Story 8 — Una guardia anti-regressione protegge l'invariante (P1, Must)
Un test di guardia **fallisce** se un hook in scope reintroduce una **soppressione silenziosa** (un path
degradato senza breadcrumb) o se uno dei 3 agent **perde** l'istruzione di fallback «asset mancante →
STOP». Così l'invariante è protetto in CI, non solo introdotto una volta.

**Independent Test**: reintroducendo un `catch` silenzioso senza breadcrumb in un hook in scope, o
rimuovendo il fallback da un agent, almeno un test di guardia fallisce.

**Acceptance**:
1. **Given** un hook in scope, **When** reintroduce un path degradato privo di breadcrumb, **Then** la
   guardia anti-regressione fallisce.
2. **Given** uno dei 3 agent, **When** perde l'istruzione di fallback «asset mancante → STOP», **Then** la
   guardia fallisce.
3. **Given** lo stato corretto (breadcrumb presente nei path degradati + fallback presente nei 3 body),
   **When** la guardia gira, **Then** passa.

### User Story 9 — Asset dogfood in sync e lifecycle installer additivo (P2, Should)
Le **copie dogfood** sotto `.claude/` sono ri-sincronizzate con gli asset canonici sotto `packages/**/assets/`
così restano **byte-identiche**, verificato dalla guardia di sync esistente. La modifica è **additiva**
all'installer: nessuna capacità è rimossa; il lifecycle install/upgrade/uninstall degli asset toccati resta
coerente; il file runtime `.sertor/.last-hook-error` **non è committato** ed è coperto dagli ignore/uninstall
di runtime (gemello di `.rag-health.json`).

**Independent Test**: dopo la modifica degli asset canonici, le copie `.claude/` sono ri-sincronizzate e la
guardia di sync è verde; il file `.sertor/.last-hook-error` è ignorato dal VCS e non versionato.

**Acceptance**:
1. **Given** gli asset canonici modificati, **When** si esegue il sync, **Then** le copie dogfood `.claude/`
   sono byte-identiche e la guardia di sync è verde.
2. **Given** il file runtime `.sertor/.last-hook-error`, **When** un ospite opera, **Then** non è committato
   ed è coperto dagli ignore/uninstall di runtime (come `.rag-health.json`), così l'ospite non lo accumula
   né lo versiona.
3. **Given** il lifecycle degli asset toccati, **When** si esegue install/upgrade/uninstall, **Then** resta
   coerente e nessuna capacità esistente è rimossa (additività).

## Edge Cases
- **Path degradato senza traccia oggi**: ogni `catch` vuoto/`2>$null`/`exit 0` muto di un hook in scope
  diventa un punto in cui si scrive il breadcrumb prima di uscire (US1, REQ-001).
- **Scrittura del breadcrumb fallisce** (path non scrivibile, `.sertor/` assente): l'hook esce comunque 0,
  best-effort, nessun nuovo percorso fatale (US2, REQ-005).
- **No-op gated** (`SERTOR_MEMORY` spento → `memory-capture`): nessun breadcrumb, e un breadcrumb reale
  preesistente non viene sovrascritto (US3, REQ-004).
- **Errori in rapida successione**: «ultimo errore» — il file è sovrascritto, non appeso; vince l'ultimo
  fallimento (decisione breadcrumb fissata).
- **Lettura cieca di stato runtime proprio** (start hook read-only che non riesce a leggere il suo file di
  stato in modo che nasconde un problema): trattata come degradazione → breadcrumb (US4, REQ-006).
- **Output esterno con materiale sensibile**: il `reason` è scrubbato alla fonte o ridotto a stringa locale
  senza segreti (US5, REQ-008).
- **Asset agent non risolvibile/leggibile**: l'agente STOP e segnala invece di procedere a vuoto (US6,
  REQ-010..012); regola uniforme per tutti e 3, nessun auto-recupero differenziato.
- **Hook read-only/già fail-loud fuori scope** (`wiki-session-start`, `rag-freshness-start`,
  `version-check-start`, `sertor-rag-usage-check`): non modificati, salvo il caso REQ-006 di soppressione
  silenziosa di stato illeggibile.
- **Drift dogfood↔bundle**: la guardia di sync impedisce divergenze tra `.claude/` e gli asset canonici
  (US9, REQ-014).
- **Reintroduzione di un catch silenzioso o perdita del fallback**: la guardia anti-regressione fallisce
  (US8, REQ-015).

## Requirements *(mandatory)*

### Requisiti funzionali

**Hook — fail-loud breadcrumb**
- **FR-001 (breadcrumb su fallimento).** Quando un hook distribuito in scope sopprime il fallimento di
  un'operazione delegata (un'invocazione CLI/vehicle) o un errore interno catastrofico che prima degradava
  in silenzio, l'hook registra un breadcrumb ispezionabile prima di uscire. *(REQ-001; CS-1)*
- **FR-002 (contenuto del breadcrumb).** Il breadcrumb identifica almeno *quale hook* l'ha prodotto,
  *quando* (timestamp UTC) e *cosa* è fallito (motivo breve, leggibile da un umano). *(REQ-002; CS-1)*
- **FR-003 (persistenza oltre la sessione).** Il breadcrumb persiste oltre la sessione in cui è prodotto,
  così è ispezionabile a un avvio successivo o dall'utente. *(REQ-003; CS-1)*
- **FR-004 (no-op gated → niente traccia).** Mentre un gate di feature è spento al punto che un hook è un
  no-op deliberato (es. `SERTOR_MEMORY` disabilitato → `memory-capture` esce 0), l'hook **non** registra
  alcun breadcrumb (un no-op gated non è un fallimento). *(REQ-004)*
- **FR-005 (scrittura best-effort, mai fatale).** Se la scrittura del breadcrumb stessa fallisce, l'hook
  esce comunque 0 e non rompe la sessione (la scrittura è best-effort, mai un nuovo percorso fatale).
  *(REQ-005; CS-2)*
- **FR-006 (lettura cieca di stato runtime → breadcrumb).** Dove un hook distribuito legge uno stato di
  runtime che possiede (es. un file di salute/versione) e quella lettura fallisce in un modo che nasconde
  un problema reale, l'hook tratta il fatto come degradazione e registra un breadcrumb per FR-001..003.
  *(REQ-006)*
- **FR-007 (exit 0 in ogni path).** L'hook continua a uscire 0 in tutti i path (invariante non-fatale
  preservato), inclusi i path degradati che ora emettono un breadcrumb. *(REQ-007; CS-2)*
- **FR-008 (nessun segreto nella traccia).** Il breadcrumb non contiene segreti né contenuto sensibile di
  `.env`; qualunque `reason` derivato da output esterno è già scrubbato dal vehicle che lo produce o
  mantenuto a stringhe locali all'hook, prive di segreti. *(REQ-008; CS-4; NFR-3)*
- **FR-009 (convenzione condivisa).** Mentre un hook degrada, il meccanismo del breadcrumb è coerente
  (convenzione condivisa) tra gli hook in scope, così un consumatore lo individua e lo legge in modo
  uniforme. *(REQ-009; CS-1)*

**Agent — fallback «asset mancante → STOP»**
- **FR-010 (`concierge`).** Il body dell'agent `concierge` istruisce: se la skill `guided-setup` non è
  risolvibile/leggibile, **STOP** e segnala l'asset mancante all'utente, anziché procedere. *(REQ-010;
  CS-3)*
- **FR-011 (`wiki-curator`).** Il body dell'agent `wiki-curator` istruisce: se il `wiki-playbook.md` o un
  modulo `ops/` richiesto non è risolvibile/leggibile, **STOP** e segnala l'asset mancante, anziché
  procedere. *(REQ-011; CS-3)*
- **FR-012 (`requirements-analyst`).** Il body dell'agent `requirements-analyst` istruisce: se la skill
  `requirements` non è risolvibile/leggibile, **STOP** e segnala l'asset mancante, anziché procedere
  (regola uniforme, nessun path di auto-recupero differenziato — decisione utente). *(REQ-012; CS-3)*
- **FR-013 (fallback host-agnostico).** Le istruzioni di fallback sono espresse in ciascun body come testo
  host-agnostico (niente path `.claude/`, niente slash-command, niente nome-modello/prodotto Claude-only),
  così il body resta byte-identico tra Claude e Copilot. *(REQ-013; CS-5)*

**Distribuzione, parità, anti-regressione**
- **FR-014 (sync dogfood↔bundle).** Quando gli asset canonici sotto `packages/**/assets/` sono modificati,
  le copie dogfood sotto `.claude/` sono ri-sincronizzate così le due restano byte-identiche (la guardia di
  sync esistente resta verde). *(REQ-014; CS-5)*
- **FR-015 (guardia anti-regressione).** La feature fornisce un test anti-regressione che fallisce se un
  hook distribuito in scope reintroduce una soppressione silenziosa (un path degradato privo di breadcrumb)
  o se uno dei 3 agent perde l'istruzione di fallback «asset mancante → STOP». *(REQ-015; CS-6)*
- **FR-016 (artefatto runtime non versionato).** L'artefatto runtime del breadcrumb non è committato nel
  repository ospite (è stato di runtime, come `.sertor/.rag-health.json`) ed è coperto dall'opportuno
  trattamento ignore/uninstall così un ospite non lo accumula né lo versiona. *(REQ-016)*
- **FR-017 (additività dell'installer).** Il cambiamento è additivo all'installer: nessuna rimozione di una
  capacità esistente; il lifecycle install/upgrade/uninstall degli asset toccati resta coerente.
  *(REQ-017)*

### Requisiti non funzionali
- **RNF-1 (Costituzione, Principio XII):** la feature realizza «Fail Loud, Fix the Cause»; nessuna deroga
  attesa. *(NFR-1)*
- **RNF-2 (Principio XI):** gli hook non importano `sertor_core` e non chiamano un LLM; restano wrapper
  sottili attorno ai vehicle/file. *(NFR-2)*
- **RNF-3 (privacy):** nessun segreto nella traccia; allineato a FR-008. *(NFR-3)*
- **RNF-4 (host-agnostico, Principio X):** le modifiche valgono su qualunque ospite e su entrambe le
  famiglie d'assistente; nessun path hardcodato a un progetto specifico. *(NFR-4)*
- **RNF-5 (non-bloccante/non-fatale):** costo trascurabile alla chiusura/avvio sessione; mai un nuovo
  percorso che blocca o rompe la sessione. *(NFR-5; FR-005/007)*
- **RNF-6 (additività core):** `sertor-core` invariato; la feature è di soli asset host-facing + test.
  *(NFR-6)*

### Key Entities
- **Breadcrumb di errore hook (file persistito)** — `.sertor/.last-hook-error`: un file singolo persistente
  in JSON con campi minimi `hook` / `ts` (timestamp UTC) / `reason` (motivo breve, scrubbato),
  **sovrascritto a ogni nuovo errore** (semantica «ultimo errore», non storia, non un file per hook);
  gemello di `.sertor/.rag-health.json` per pattern, ignore e uninstall di runtime.
- **Hook in scope** — gli hook distribuiti che oggi sopprimono in silenzio un fallimento operativo o
  catastrofico: `memory-capture`, `rag-freshness` (path catastrofici), `wiki-pending-check`,
  `version-check`. Restano wrapper non-LLM, exit 0 sempre; ora scrivono il breadcrumb sui path degradati.
- **Hook fuori scope (classificati, non modificati)** — gli hook read-only/puri o già fail-loud:
  `wiki-session-start`, `rag-freshness-start`, `version-check-start`, `sertor-rag-usage-check`; toccati solo
  se ricadono nel caso REQ-006 (lettura cieca di stato runtime proprio).
- **Body degli agent con fallback** — i 3 body (`concierge`, `wiki-curator`, `requirements-analyst`) che
  ora portano la regola uniforme «asset mancante → STOP e segnala», espressa in testo host-agnostico,
  byte-identico Claude↔Copilot.
- **Guardia anti-regressione** — il test che fallisce se un hook reintroduce un catch silenzioso senza
  breadcrumb o se un agent perde il fallback; affiancata dalla guardia di sync dogfood↔bundle.

## Success Criteria *(mandatory)*
- **CS-1 (rottura silenziosa lascia traccia):** ogni hook in scope che oggi sopprime in silenzio un
  fallimento, quando degrada lascia una traccia ispezionabile che identifica *quale hook*, *quando* e
  *cosa* è fallito — verificabile provocando il fallimento e trovando la traccia. *(FR-001/002/003/009,
  US1/US2)*
- **CS-2 (non-fatalità preservata):** gli hook continuano a uscire **0 sempre** e a non rompere
  chiusura/avvio; la scrittura della traccia è essa stessa best-effort e non introduce alcun percorso
  fatale. *(FR-005/007, US2)*
- **CS-3 (agent si fermano sull'asset mancante):** i 3 agent, quando l'asset di cui sono guscio non è
  risolvibile/leggibile, si fermano e segnalano invece di procedere — verificabile dal testo del body
  (istruzione presente e inequivocabile). *(FR-010/011/012, US6)*
- **CS-4 (nessun segreto nella traccia):** nessun segreto compare nella traccia (parità con la disciplina
  di privacy del progetto). *(FR-008, US5)*
- **CS-5 (parità host-agnostica preservata):** i body restano byte-identici Claude↔Copilot; le modifiche
  agli hook valgono su entrambe le famiglie di distribuzione; guardie di parità/sync verdi. *(FR-013/014,
  US7/US9)*
- **CS-6 (guardia anti-regressione):** una guardia fallisce se un hook in scope reintroduce un catch
  silenzioso (senza breadcrumb) o se un dei 3 agent perde l'istruzione di fallback. *(FR-015, US8)*

## Assumptions
- **A-001 — Pattern `.sertor/.rag-health.json` riusabile (FEAT-011, su `master`):** dà il modello di
  riferimento per il breadcrumb (formato JSON, collocazione `.sertor/`, ignore/uninstall di runtime). Il
  breadcrumb ne è il gemello. *(FR-016)*
- **A-002 — Guardie `test_assets_sync.py` e parità Copilot esistenti:** la feature le **riusa/estende**,
  non le reinventa; restano verdi dopo il ri-sync. *(FR-014, CS-5)*
- **A-003 — Scrub alla fonte garantito dai vehicle:** l'output dei comandi (`sertor-rag` ecc.) è già
  scrubbato; il `reason` derivato da quell'output eredita lo scrub o è ridotto a stringa locale priva di
  segreti. *(FR-008)*
- **A-004 — Gli hook restano PowerShell-only in questa feature:** ci si limita a rendere fail-loud i path
  già presenti, senza riscrivere il wiring; la portabilità OS (gemello bash) è FEAT-018. *(Vincolo §7
  requirements)*
- **A-005 — `requirements-analyst` mantiene la tassonomia EARS inline che già possiede:** per decisione
  utente il fallback è **STOP+segnala uniforme**, non un auto-recupero silenzioso differenziato. *(FR-012)*

### Fuori ambito (dichiarato)
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle — la feature è **additiva e host-facing**,
  zero codice di runtime del core (Principio XI). Gli hook continuano a non importare `sertor_core` e a non
  chiamare un LLM.
- **Portabilità OS degli hook** (guardia `pwsh`/gemello bash) e **onestà sui surface Copilot inerti** →
  **FEAT-018** (audit ISSUE-04), feature separata.
- **Pulizia stile/altitude** dei body degli agent e dei blocchi `CLAUDE.md` → **FEAT-021/FEAT-022**.
- **Consumo attivo automatico della traccia all'avvio** oltre l'induzione su stato `degraded` già esistente
  (hook `*-start` di FEAT-011) — qui si garantisce *che la traccia esista e sia ispezionabile*; il consumo
  attivo esteso è **follow-up Could**.
- **Hook read-only/già fail-loud** (`wiki-session-start`, `rag-freshness-start`, `version-check-start`,
  `sertor-rag-usage-check`): classificati ma **non modificati**, salvo il caso REQ-006 di soppressione
  silenziosa di stato illeggibile.
- **Il *come* di dettaglio** (punti esatti di scrittura del breadcrumb nei singoli hook; forma precisa della
  guardia anti-regressione e dei lint statici sui body; punti dell'installer/ignore): fase di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali sono già **promossi a casa durevole** nel backlog d'epica:
> portabilità OS + onestà surface Copilot = **FEAT-018**; pulizia stile/altitude = **FEAT-021/FEAT-022**;
> consumo attivo automatico della traccia all'avvio = **follow-up Could** (epica debito-tecnico). Nessun
> rinvio reale resta sepolto in `specs/`. La feature è *done* quando gli hook in scope scrivono il
> breadcrumb sui path degradati, i 3 body portano il fallback host-agnostico, le guardie (anti-regressione
> + sync dogfood↔bundle) sono verdi e gli asset sono distribuiti via installer (additivi).

### Forche di design — RISOLTE con l'utente (per `/speckit-plan`)
- **DA-1 — Scope hook: RISOLTA.** Tutti gli hook che inghiottono errori, ancorati alla classificazione del
  §4 dei requirements: in-scope = `memory-capture`, `rag-freshness` (path catastrofici),
  `wiki-pending-check`, `version-check`; esclusi i read-only/già-fail-loud salvo REQ-006. *(decisione
  utente; FR-001/006/009.)*
- **DA-2 — Fallback agent: RISOLTA.** Regola **uniforme** «STOP e segnala» per tutti e 3 i body, senza path
  di auto-recupero differenziato. *(decisione utente; FR-010/011/012.)*
- **DA-3 — Meccanismo del breadcrumb: RISOLTA.** File singolo persistente `.sertor/.last-hook-error` (JSON
  con `hook`/`ts` UTC/`reason`), **sovrascritto a ogni nuovo errore** (semantica «ultimo errore», non
  storia append, non un file per hook), + nota minima su stderr; gemello di `.sertor/.rag-health.json`
  (stesso pattern, ignore/uninstall di runtime). *(decisione utente, era la forca aperta del §10; FR-001..003/009/016.)*
- **DA-D-r1 (residuo, design) — Punti esatti di scrittura del breadcrumb** nei singoli hook e gestione del
  no-op gated per ciascuno: *come* di plan.
- **DA-D-r2 (residuo, design) — Forma della guardia anti-regressione** (lint statico sui body degli hook per
  `catch` vuoti senza breadcrumb + assert sulla presenza dell'istruzione di fallback negli agent): *come*
  di plan.
