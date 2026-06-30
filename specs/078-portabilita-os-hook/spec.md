# Feature Specification: Portabilità OS degli hook (guardia pwsh + gap dichiarato) + onestà sui surface inerti (E10-FEAT-018)

**Feature Branch**: `078-portabilita-os-hook` · **Created**: 2026-06-30 · **Status**: Draft

<!-- Deriva da: FEAT-018 (epica debito-tecnico E10) — requirements/debito-tecnico/portabilita-os-hook/requirements.md (audit asset first-party 2026-06-26, ISSUE-04) -->

**Input**: FEAT-018 dell'epica `debito-tecnico` (E10). Gli hook distribuiti da `sertor install` sono
**tutti `.ps1`** e il wiring Claude li invoca con `"shell": "powershell"` — cioè `powershell.exe`
(Windows PowerShell 5.1). Su macOS/Linux l'eseguibile `powershell` **non esiste**: il client agente
non riesce a invocare lo script, l'hook **non viene mai eseguito**, nessun messaggio, **exit 0**.
L'utente non-Windows crede di avere gli hook attivi mentre **nessuno** di essi gira: è una violazione
del **Principio XII «Fail Loud, Fix the Cause»** (un fallimento silenziato per schivare un errore) e
del **Principio X** (la portabilità dichiarata non corrisponde a quella reale). In parallelo, l'install
report afferma **implicitamente** che ogni artefatto depositato è operativo: su Copilot CLI
`memory-capture` viene wired e depositato, ma è **funzionalmente inerte** nelle condizioni di default
(l'adapter predefinito è `claude-code`, non quello Copilot). La feature rende **onesti** entrambi i
claim: su host non-Windows senza `pwsh` l'installer **dichiara** che i surface hook sono installati ma
non-operativi e fornisce una **rimediazione azionabile**; su Copilot CLI **dichiara** che
`memory-capture` richiede configurazione esplicita. È debito di **onestà** e **portabilità reale**.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e
> realtà del contesto reso all'agente**: hook e installer esistono per tenere quel contesto reale
> (freschezza RAG, cattura memoria) su qualunque ospite. Un installer che **dichiara** operativi degli
> hook che su mac/Linux non partono mai è esattamente il **modo in cui l'apparato si scopre rotto solo
> settimane dopo** — il dogfooding cieco esteso all'ospite. Rendere la portabilità **onesta** (segnale
> azionabile quando manca il prerequisito, claim allineati allo stato reale dei surface) *protegge* la
> stella polare: l'ospite non opera credendo di avere protezioni che non ha. È coerente col confine
> **D↔N**: il rilevamento di `pwsh` e l'emissione delle note sono **meccanici** (codice installer
> Python, nessun ragionamento, **nessun LLM**); l'azione sui gap dichiarati resta all'agente/utente.
> Complementa FEAT-019 (fail-loud breadcrumb negli hook): quella copre «lo script gira ma l'operazione
> interna fallisce»; questa copre «lo script **non può nemmeno partire** perché manca `pwsh`».

> **Natura del cambiamento: ADDITIVO + host-facing, ZERO codice di core.** La feature **non** modifica
> `sertor_core` né alcun comando/vehicle (Principio XI). Tocca il **pacchetto installer** (`sertor`,
> eventualmente un helper condiviso in `sertor-install-kit`), i **template di documentazione utente**
> (`docs/install.md`, `docs/install-copilot.md`) e i loro **test di guardia**. Introduce: un
> **rilevamento install-time della disponibilità di `pwsh`** su host non-Windows; l'**emissione di note**
> nel report d'install (`InstallReport.notes`) per i surface inerti; l'**aggiornamento della
> documentazione utente** con il prerequisito `pwsh`; le **guard tests** delle note e la
> non-regressione sul percorso Claude+Windows. A comportamento sano (host Windows + Claude, o
> non-Windows con `pwsh` presente) il funzionamento è **invariato**: `report.notes == []`, nessun nuovo
> artefatto, nessun cambio di wiring.

> **Decisione di strategia — FISSATA con l'utente (non riaprire).** La strategia è **«guardia `pwsh` +
> gap dichiarato»**, **non** un gemello bash. Gli hook restano **PowerShell-only** (`.ps1`, una sola
> copia per hook — convenzione standing «solo PowerShell, non bash»): **nessun** `.sh`, **nessun**
> raddoppio di asset, **nessuna** guardia di parità `.ps1`↔`.sh`. Su host non-Windows `pwsh`
> (PowerShell Core) è un **prerequisito dichiarato**: se manca, l'installer **fa fail loud** con un
> messaggio azionabile (installa PowerShell Core + URL) invece del silent exit 0. L'**onestà sui
> surface inerti** si esprime riusando il meccanismo **`InstallReport.notes`** (già presente nel kit,
> oggi inutilizzato in produzione) per marcare esplicitamente i surface non-operativi sul target/
> assistente corrente, invece di affermare «parità piena».

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Gli asset e i meccanismi in scope
> esistono già e sono accertati: il wiring Claude usa `"shell": "powershell"` (es.
> `assets/rag/settings.rag-freshness.json`, `assets/settings.hooks.json`); il wiring Copilot usa già
> `pwsh -File` (costante `_PWSH = "pwsh -File"` in `install_rag.py` / `install_wiki.py`); il meccanismo
> `InstallReport.notes` + metodo `.note()` esiste in `sertor-install-kit/report.py` ma non è ancora
> emesso in codice di produzione; il test esistente `test_claude_report_has_no_gap_note` asserisce
> `report.notes == []` per Claude su Windows; la convenzione breadcrumb `Write-HookBreadcrumb` /
> `.sertor/.last-hook-error` di FEAT-019 (stessi hook) è riusabile come segnale. I riferimenti
> **ancorano** i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Su mac/Linux senza `pwsh`, l'installer non finge che gli hook funzionino (P1, Must)
Un utente installa Sertor su macOS/Linux dove `pwsh` non è nel PATH. Oggi gli hook vengono depositati e
l'installer dichiara successo, ma nessun hook potrà mai essere eseguito (l'invocazione PowerShell non
risolve) — l'utente lo scopre, se mai, per assenza di effetti. Con la feature, l'installer **rileva**
l'assenza di `pwsh`, **non dichiara operativi** quei surface e produce una **nota azionabile** (quali
surface sono installati ma non-operativi, come installare PowerShell Core, con URL), visibile sia nella
resa umana sia in `notes[]` del JSON.

**Independent Test**: si simula un host non-Windows senza `pwsh`; si esegue un `sertor install rag` (o
`wiki`) che deposita hook; `report.notes` contiene una nota d'indisponibilità `pwsh` che identifica i
surface affetti e fornisce un URL di rimediazione, presente sia nella resa umana sia in `notes[]`.

**Acceptance**:
1. **Given** un host non-Windows senza `pwsh` nel PATH, **When** `sertor install rag`/`wiki` deposita
   hook, **Then** l'installer rileva l'assenza di `pwsh` e aggiunge al report una nota che identifica i
   surface hook depositati ma non-operativi.
2. **Given** quella nota, **When** la si legge, **Then** contiene una rimediazione azionabile, incluso
   un URL dove installare PowerShell Core.
3. **Given** il report d'install, **When** lo si rende, **Then** la nota appare **sia** nella resa umana
   **sia** in `notes[]` del JSON, coerente col contratto `InstallReport.notes` esistente.

### User Story 2 — Su mac/Linux con `pwsh` presente, nessun falso allarme (P2, Should)
Quando `pwsh` **è** disponibile su un host non-Windows, gli hook possono partire: l'installer **non**
emette la nota d'indisponibilità. Una nota in questo caso sarebbe rumore e indebolirebbe il segnale
quando serve davvero.

**Independent Test**: si simula un host non-Windows **con** `pwsh` disponibile; dopo l'install,
`report.notes` non contiene la nota d'indisponibilità `pwsh`.

**Acceptance**:
1. **Given** un host non-Windows con `pwsh` nel PATH, **When** l'install deposita hook, **Then**
   l'installer **non** emette la nota d'indisponibilità `pwsh`.

### User Story 3 — Su Windows + Claude (caso più comune) nulla cambia (P1, Must)
Il percorso primario di oggi — host Windows, target Claude — non deve cambiare comportamento: il wiring
`"shell": "powershell"` è valido su Windows, quindi nessuna nota d'indisponibilità è dovuta. Il report
resta pulito, nessun nuovo artefatto, nessun cambio di wiring.

**Independent Test**: su un host Windows con target Claude, `report.notes == []` dopo l'install
(verificato dal test esistente `test_claude_report_has_no_gap_note`, esteso/preservato).

**Acceptance**:
1. **Given** un host Windows con target Claude, **When** l'install deposita hook, **Then**
   `report.notes == []` (non-regressione: nessuna nota `pwsh`, nessuna nota Copilot).
2. **Given** lo stesso percorso, **When** si confronta col comportamento precedente la feature, **Then**
   nessun nuovo artefatto è prodotto e il wiring degli hook è invariato.

### User Story 4 — L'install non è bloccato dall'assenza di `pwsh` (P1, Must)
La guardia `pwsh` è **informativa, non un blocco**: anche quando `pwsh` manca, tutti i surface non-hook
(config MCP, blocco istruzioni, template `.env`, skill, agent, gitignore) vengono installati senza
errore e l'install esce 0 se non si verificano altri errori. L'utente ottiene un sistema parzialmente
funzionante con un segnale chiaro su cosa completare, non un install fallito.

**Independent Test**: si simula un host non-Windows senza `pwsh`; l'install completa i surface non-hook
senza errore e l'exit code è 0 in assenza di altri errori; la sola differenza osservabile è la nota.

**Acceptance**:
1. **Given** un host non-Windows senza `pwsh`, **When** l'install gira, **Then** tutti i surface
   non-hook sono installati senza errore.
2. **Given** lo stesso scenario, **When** l'install termina, **Then** l'exit code è 0 se nessun altro
   errore si è verificato (la guardia `pwsh` è non-fatale).

### User Story 5 — Su Copilot CLI l'utente sa che `memory-capture` richiede configurazione (P1, Must)
Su un install `sertor install rag` con target Copilot CLI, `memory-capture` è wired e depositato, ma in
configurazione di default l'hook **scatta senza catturare nulla di utile** (default `SERTOR_MEMORY=false`;
e anche con la memoria attiva, l'adapter predefinito `claude-code` legge le sessioni Claude, non quelle
Copilot). Con la feature, il report include una nota che spiega che `memory-capture` richiede sia
`SERTOR_MEMORY=true` **sia** un valore adapter Copilot esplicito per `SERTOR_MEMORY_ADAPTER` per
catturare sessioni Copilot CLI, e che il completamento out-of-the-box è una capacità **pianificata**
(distribuzione del valore adapter nel template `.env`), così l'utente può optare manualmente nel
frattempo.

**Independent Test**: si simula un `sertor install rag` con target Copilot CLI; `report.notes` contiene
una nota su `memory-capture` che indica la condizione (`SERTOR_MEMORY=true` + adapter Copilot esplicito)
e rimanda alla capacità pianificata che completerà l'esperienza.

**Acceptance**:
1. **Given** un install rag con target Copilot CLI, **When** il report è prodotto, **Then** include una
   nota che dichiara che `memory-capture` richiede `SERTOR_MEMORY=true` e un valore adapter Copilot
   esplicito per `SERTOR_MEMORY_ADAPTER`, e che col default l'hook scatta ma non cattura nulla di utile.
2. **Given** quella nota, **When** la si legge, **Then** rimanda alla capacità pendente (distribuzione
   del valore adapter nel template `.env`, tracciata in epica memoria-conversazioni) così l'utente sa
   che un fix è pianificato e può abilitarlo manualmente intanto.
3. **Given** un install rag con target Claude su Windows, **When** il report è prodotto, **Then** la
   nota Copilot-adapter **non** è emessa (`report.notes == []` per quel percorso).

### User Story 6 — La documentazione utente dichiara il prerequisito e i surface parziali (P1, Must)
La documentazione utente smette di nascondere il requisito: `docs/install.md` (riferimento) dichiara
`pwsh` come prerequisito su macOS/Linux per il funzionamento dei surface hook (con URL d'installazione,
elenco dei surface affetti, e la frase esplicita che senza `pwsh` quei surface sono installati ma
non-operativi); `docs/install-copilot.md` (quick-start Copilot) dichiara che gli hook richiedono `pwsh`
su mac/Linux e che `memory-capture` richiede configurazione adapter esplicita per catturare sessioni
Copilot CLI, con le variabili da impostare. `docs/install.md` elenca inoltre, per ogni target supportato
(Claude su Windows, Copilot CLI), quali surface sono pienamente operativi dopo l'install e quali
richiedono configurazione manuale aggiuntiva, con quali passi.

**Independent Test**: si leggono `docs/install.md` e `docs/install-copilot.md`; entrambi dichiarano
`pwsh` come prerequisito su mac/Linux con URL e surface affetti; `docs/install-copilot.md` dichiara la
configurazione adapter richiesta per `memory-capture`; `docs/install.md` distingue surface operativi
vs. da configurare per target.

**Acceptance**:
1. **Given** `docs/install.md`, **When** lo si legge, **Then** dichiara `pwsh` come prerequisito
   richiesto su macOS/Linux per i surface hook, con URL d'installazione, elenco dei surface affetti e la
   frase che senza `pwsh` quei surface sono installati ma non-operativi.
2. **Given** `docs/install-copilot.md`, **When** lo si legge, **Then** dichiara, per il target Copilot
   CLI: (a) che gli hook richiedono `pwsh` su macOS/Linux; (b) che `memory-capture` richiede
   configurazione adapter esplicita per catturare sessioni Copilot CLI, con le variabili da impostare.
3. **Given** `docs/install.md`, **When** lo si legge, **Then** elenca per ogni target supportato quali
   surface sono pienamente operativi dopo l'install e quali richiedono configurazione manuale, con i
   passi.

### User Story 7 — Guard tests e sync dogfood↔bundle proteggono l'onestà in CI (P1, Must)
Le note emesse sono protette da guardie deterministiche: un test verifica che un install non-Windows
senza `pwsh` produca la nota d'indisponibilità, che con `pwsh` presente non la produca, e che
Claude+Windows resti a `report.notes == []` (non-regressione); un altro test verifica che un install
Copilot CLI rag emetta la nota su `memory-capture`. I test usano fixture che **simulano l'OS** anziché
dipendere dall'OS reale (la CI gira su Windows), restando deterministici. La coerenza del sync
bundled↔dogfood (`test_assets_sync.py`) resta verde dopo ogni cambiamento di asset.

**Independent Test**: si esegue la suite di guardia: i test sulle note (pwsh presente/assente,
Claude+Windows pulito, Copilot memory-capture) passano usando OS mocking; la guardia di sync è verde.

**Acceptance**:
1. **Given** la guardia note-pwsh, **When** gira, **Then** verifica (a) install non-Windows senza
   `pwsh` → nota presente; (b) install non-Windows con `pwsh` → nota assente; (c) Claude+Windows →
   `report.notes == []`.
2. **Given** la guardia nota-Copilot, **When** gira, **Then** verifica che un install rag Copilot CLI
   emetta la nota su `memory-capture` in `report.notes`.
3. **Given** le guardie, **When** girano in CI su Windows, **Then** restano deterministiche perché
   simulano l'OS (fixture), non dipendono dall'OS reale.
4. **Given** la guardia di sync bundled↔dogfood, **When** gira dopo i cambiamenti di asset, **Then**
   resta verde (`.claude/` byte-identico agli asset canonici).

## Edge Cases
- **Host non-Windows, `pwsh` assente, hook depositati**: nota d'indisponibilità con surface affetti +
  URL; install non-fatale, exit 0 (US1, US4 — FR-002/005).
- **Host non-Windows, `pwsh` presente**: nessuna nota d'indisponibilità (US2 — FR-004).
- **Host Windows, target Claude**: `report.notes == []`, comportamento invariato (US3 — FR-006/REQ-009).
- **Install Copilot CLI rag**: nota `memory-capture` (condizione adapter + cross-ref capacità
  pianificata); emessa anche con `SERTOR_MEMORY` spento, perché l'utente che la abiliterà deve già
  saperlo — la decisione finale «sempre vs. solo se `SERTOR_MEMORY=true`» è di *plan* (US5 — FR-007/008).
- **Check binario, nessuna OS-detection sofisticata**: condizione binaria `pwsh` trovato/non trovato,
  nessun test di versione, nessun hardcoding di distribuzione Linux (NFR-1/NFR-4 — R-1).
- **Falso positivo su Windows**: il check non deve attivarsi su Windows — protetto da guardia di
  non-regressione esplicita (US3, US7 — R-2).
- **Rilevamento runtime escluso**: se `pwsh` manca a runtime il processo non parte (servirebbe `pwsh`
  per rilevarlo) → il punto d'intervento corretto è l'install-time (fuori ambito §Fuori ambito).
- **Nota memory-capture diventa stale**: quando la capacità pianificata distribuirà il valore adapter,
  la nota va rimossa o condizionata; la nota cross-referenzia quella feature per renderlo tracciabile
  (R-4).
- **CI su Windows**: i guard test del percorso non-Windows usano OS mocking/patching, non dipendono
  dall'OS reale (US7 — R-6).

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Guardia `pwsh` all'install-time**
- **FR-001 (rilevamento `pwsh` su non-Windows).** Quando `sertor install rag` o `sertor install wiki`
  gira su un host non-Windows, l'installer rileva se `pwsh` (PowerShell Core) è disponibile nel PATH di
  sistema. *(REQ-001; CS-1)*
- **FR-002 (nota d'indisponibilità `pwsh`).** Se `pwsh` non è trovato su un host non-Windows mentre si
  depositano surface hook, l'installer aggiunge al report una nota che (a) identifica quali surface hook
  sono depositati ma non-operativi senza `pwsh`; (b) fornisce un messaggio di rimediazione azionabile,
  incluso un URL dove installare PowerShell Core. *(REQ-002; CS-1)*
- **FR-003 (nota in resa umana e JSON).** La nota d'indisponibilità `pwsh` appare sia nella resa umana
  sia in `notes[]` del JSON del report, coerente col contratto `InstallReport.notes` esistente.
  *(REQ-003; CS-1)*
- **FR-004 (nessuna nota se `pwsh` presente).** Se `pwsh` **è** disponibile su un host non-Windows,
  l'installer **non** emette la nota d'indisponibilità `pwsh`. *(REQ-004; CS-2)*
- **FR-005 (check non-fatale).** Il check `pwsh` è non-fatale: anche con `pwsh` assente, tutti i surface
  non-hook (config MCP, blocco istruzioni, template `.env`, skill, agent, gitignore) sono installati
  senza errore e l'exit code complessivo è 0 se nessun altro errore si verifica. *(REQ-005; CS-1)*
- **FR-006 (nessuna nota su Windows).** Su un host Windows l'installer **non** emette la nota
  d'indisponibilità `pwsh` (il wiring Claude `"shell": "powershell"` è valido su Windows; il wiring
  Copilot `pwsh -File` è coperto, per capacità, dalla documentazione). *(REQ-006; CS-3)*

**Gruppo B — Onestà sui surface inerti (Copilot CLI)**
- **FR-007 (nota `memory-capture` su Copilot CLI).** Quando `sertor install rag` ha come target Copilot
  CLI, il report include una nota che dichiara che `memory-capture` richiede sia `SERTOR_MEMORY=true`
  sia un valore adapter Copilot esplicito per `SERTOR_MEMORY_ADAPTER` per catturare sessioni Copilot
  CLI; col default l'hook scatta ma non cattura nulla di utile. *(REQ-007; CS-4)*
- **FR-008 (cross-ref alla capacità pianificata).** La nota di FR-007 rimanda alla capacità pendente che
  completerebbe l'esperienza out-of-the-box (la distribuzione del valore adapter Copilot nel template
  `.env`, tracciata separatamente in epica memoria-conversazioni), così l'utente sa che un fix è
  pianificato e può optare manualmente nel frattempo. *(REQ-008; CS-4)*
- **FR-009 (nessuna nota Copilot su Claude+Windows).** Quando `sertor install rag` ha come target Claude
  su Windows (percorso primario corrente), l'installer **non** emette la nota d'inertness Copilot-adapter
  (non-regressione: `report.notes == []` per quel percorso). *(REQ-009; CS-3)*

**Gruppo C — Documentazione utente**
- **FR-010 (`docs/install.md` — prerequisito `pwsh`).** `docs/install.md` dichiara `pwsh` (PowerShell
  Core) come prerequisito richiesto su macOS/Linux per il funzionamento dei surface hook, incluso un URL
  d'installazione, l'elenco dei surface affetti e la frase che senza `pwsh` quei surface sono installati
  ma non-operativi. *(REQ-010; CS-5)*
- **FR-011 (`docs/install-copilot.md` — Copilot).** `docs/install-copilot.md` dichiara, per il target
  Copilot CLI: (a) che gli hook richiedono `pwsh` su macOS/Linux; (b) che `memory-capture` richiede
  configurazione adapter esplicita per catturare sessioni Copilot CLI, con le variabili da impostare.
  *(REQ-011; CS-5)*
- **FR-012 (`docs/install.md` — surface per target).** `docs/install.md` elenca, per ogni target
  supportato (Claude su Windows, Copilot CLI), quali surface sono pienamente operativi dopo l'install e
  quali richiedono configurazione manuale aggiuntiva, con i passi. *(REQ-012; CS-5)*

**Gruppo D — Guard tests e sync**
- **FR-013 (guardia note `pwsh`).** La feature fornisce un test di guardia che verifica: (a) un install
  non-Windows simulato senza `pwsh` produce una nota d'indisponibilità `pwsh` in `report.notes`; (b) un
  install non-Windows simulato con `pwsh` disponibile **non** emette quella nota; (c) un install
  Claude+Windows ha `report.notes == []` (non-regressione del test esistente). I test simulano l'OS
  (fixture), non dipendono dall'OS reale. *(REQ-013; CS-6; R-6)*
- **FR-014 (guardia nota Copilot).** La feature fornisce un test di guardia che verifica che un install
  rag Copilot CLI emetta una nota su `memory-capture` (richiede configurazione adapter esplicita),
  presente in `report.notes`. *(REQ-014; CS-6)*
- **FR-015 (sync dogfood↔bundle intatto).** Il sync degli asset canonici verso le copie dogfood `.claude/`
  resta intatto; la guardia di sync esistente (`test_assets_sync.py`) resta verde dopo ogni cambiamento
  di asset introdotto dalla feature. *(REQ-015; CS-6)*

### Requisiti non funzionali
- **RNF-1 (Costituzione, Principi XII e X):** la feature realizza «Fail Loud, Fix the Cause» (nessun
  claim implicito non verificato, nessun fallimento silenzioso senza segnale) e la portabilità reale (la
  portabilità dichiarata corrisponde a quella effettiva). *(NFR-1)*
- **RNF-2 (Principio XI):** il rilevamento di `pwsh` avviene in codice installer (Python); zero import di
  `sertor_core`; nessun LLM coinvolto nel check. *(NFR-2)*
- **RNF-3 (non-fatale, non-bloccante):** l'assenza di `pwsh` non provoca exit non-zero; la nota è un
  warning informativo, non un blocco; il costo del check è trascurabile (singola ricerca dell'eseguibile
  nel PATH). *(NFR-3; FR-005)*
- **RNF-4 (host-agnostico, Principio X):** il check si applica a qualunque host non-Windows, senza
  hardcoding di distribuzioni Linux specifiche; la condizione è binaria (pwsh trovato/non trovato).
  *(NFR-4)*
- **RNF-5 (non-regressione, Principio VI):** il percorso Claude+Windows — il più comune — non cambia
  comportamento (`report.notes == []`, nessun nuovo artefatto, nessun cambio di wiring). *(NFR-5; CS-3)*
- **RNF-6 (additività installer):** le modifiche sono additive: lifecycle install/upgrade/uninstall
  invariato salvo l'aggiunta delle note; nessuna rimozione di capacità. *(NFR-6)*
- **RNF-7 (additività core):** `sertor-core` invariato; la feature tocca il pacchetto installer
  `sertor` (eventualmente `sertor-install-kit` per un helper condiviso) e `docs/`. *(NFR-7)*

### Key Entities
- **Nota d'indisponibilità `pwsh` (voce di `InstallReport.notes`)** — un avviso informativo emesso
  all'install-time quando su host non-Windows manca `pwsh`: identifica i surface hook depositati ma
  non-operativi e fornisce una rimediazione azionabile con URL; appare nella resa umana e in `notes[]`
  del JSON.
- **Nota d'inertness `memory-capture` Copilot (voce di `InstallReport.notes`)** — un avviso emesso su
  install rag Copilot CLI: dichiara la condizione di configurazione (`SERTOR_MEMORY=true` + adapter
  Copilot esplicito) e cross-referenzia la capacità pianificata che completerà l'esperienza.
- **Meccanismo `InstallReport.notes`** — il campo/contratto già presente nel kit
  (`sertor-install-kit/report.py`, metodo `.note()`), finora inutilizzato in produzione; questa feature
  ne è la prima vera emissione nel percorso install.
- **Guardia `pwsh` install-time** — il punto del flusso d'installazione, in codice installer Python, che
  rileva la disponibilità di `pwsh` su host non-Windows e decide se emettere la nota (binario: trovato/
  non-trovato; non-fatale).
- **Surface hook depositati ma non-operativi** — gli artefatti `.ps1` distribuiti (hook di lifecycle) che
  su host non-Windows senza `pwsh` non potranno essere eseguiti dal client agente: oggetto della nota,
  non rimossi né tradotti.
- **Documentazione utente toccata** — `docs/install.md` (prerequisito `pwsh` + surface per target) e
  `docs/install-copilot.md` (prerequisito `pwsh` + configurazione adapter `memory-capture`).

## Success Criteria *(mandatory)*
- **CS-1 (gap `pwsh` dichiarato, non nascosto):** su un host non-Windows in cui `pwsh` non è in PATH, un
  `sertor install` (rag o wiki) che deposita hook **non** li dichiara operativi: il report contiene una
  nota esplicita — visibile in resa umana e in `notes[]` — che identifica i surface affetti e fornisce
  rimediazione azionabile con URL; l'install resta non-fatale (exit 0 in assenza di altri errori).
  Verificabile simulando l'assenza di `pwsh` e ispezionando `report.notes`. *(FR-001/002/003/005, US1/US4)*
- **CS-2 (nessun falso allarme con `pwsh`):** su un host non-Windows con `pwsh` disponibile, la nota
  d'indisponibilità non viene emessa. Verificabile simulando la presenza di `pwsh` e confermando
  `report.notes` privo della nota `pwsh`. *(FR-004, US2)*
- **CS-3 (non-regressione Claude+Windows):** su un host Windows con target Claude, `report.notes == []`
  (nessuna nota `pwsh`, nessuna nota Copilot). Verificabile con il test esistente
  `test_claude_report_has_no_gap_note`. *(FR-006/009, US3)*
- **CS-4 (onestà su `memory-capture` Copilot):** un install Copilot CLI (rag) include nel report una
  nota che identifica `memory-capture` come richiedente configurazione esplicita (il valore adapter
  Copilot per `SERTOR_MEMORY_ADAPTER`) per catturare sessioni Copilot CLI, con cross-ref alla capacità
  pianificata. Verificabile controllando `report.notes` su un install Copilot CLI simulato.
  *(FR-007/008, US5)*
- **CS-5 (documentazione utente onesta):** `docs/install.md` e `docs/install-copilot.md` dichiarano
  esplicitamente `pwsh` come prerequisito su macOS/Linux (con URL e surface affetti) e i surface che
  richiedono configurazione aggiuntiva per target. Verificabile leggendo i due file. *(FR-010/011/012, US6)*
- **CS-6 (guardie deterministiche):** le guardie verificano la nota `pwsh` (presente senza pwsh / assente
  con pwsh / `[]` su Claude+Windows) e la nota Copilot `memory-capture`, simulando l'OS in CI Windows; la
  guardia di sync dogfood↔bundle resta verde. Verificabile eseguendo la suite di guardia. *(FR-013/014/015,
  US7)*

## Assumptions
- **A-001 — Distinzione Windows/non-Windows via API/variabile standard di Python:** il *come* di
  rilevamento dell'OS è materia di plan; il requisito è la condizione binaria. *(FR-001)*
- **A-002 — Disponibilità di `pwsh` rilevata cercando l'eseguibile nel PATH** tramite API standard
  (es. ricerca dell'eseguibile): il *come* è di plan. *(FR-001)*
- **A-003 — Il check `pwsh` copre entrambe le capability (wiki e rag)** che depositano hook; se
  condividono il codice di esecuzione del plan, il check può essere centralizzato — collocazione di
  *plan*. *(FR-001)*
- **A-004 — `InstallReport.notes` e `.note()` esistono e sono testati** in `sertor-install-kit/report.py`:
  la feature **usa** l'infrastruttura esistente, nessuna modifica al kit necessaria oltre all'uso del
  meccanismo. *(FR-003)*
- **A-005 — Il test `test_claude_report_has_no_gap_note` asserisce `report.notes == []`** per Claude su
  Windows: il check `pwsh` non deve attivarsi su Windows (CS-3). *(FR-006)*
- **A-006 — La convenzione breadcrumb di FEAT-019** (`Write-HookBreadcrumb` / `.sertor/.last-hook-error`,
  stessi hook, su `master`) è riusabile come segnale d'assenza `pwsh` ove pertinente; il *come* è di plan.
  *(complementarità con FEAT-019)*

### Fuori ambito (dichiarato)
- **Gemello bash degli hook (`.sh`)** — escluso per **decisione utente**. Gli hook restano PS-only, una
  sola copia per hook (convenzione «solo PowerShell, non bash»); nessun raddoppio di asset, nessuna
  guardia di parità `.ps1`↔`.sh`.
- **Guardia `pwsh` su Windows** per l'uso interno di `rag-freshness.ps1` (`Start-Process pwsh`): quel
  path catastrofico su Windows è coperto dal breadcrumb **FEAT-019** (già consegnata); escluso per
  decisione di scope.
- **Rilevamento runtime** (all'avvio dello script): se `pwsh` manca, il processo non parte — il
  rilevamento runtime richiederebbe `pwsh` stesso; il punto d'intervento corretto è l'install-time.
- **Codice di `sertor_core`** o qualunque comando/vehicle — zero modifiche (Principio XI). Gli hook non
  importano `sertor_core` né chiamano un LLM.
- **Distribuzione di `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env`** — è **FEAT-009 epica
  memoria-conversazioni** (già tracciata). Qui si emette solo la nota che la configurazione è necessaria;
  il completamento appartiene a quella feature.
- **Visibilità del segnale SessionStart su Copilot CLI** (`type:"prompt"` più visibile vs. iniezione
  silenziosa su Claude): **non** è un surface inerte (il prompt funziona e il segnale arriva all'agente),
  si comporta solo diversamente → tracciato in **E10-FEAT-008** (cross-ref, non assorbito qui).
- **Pulizia stile/altitude** dei body degli hook e dei blocchi `CLAUDE.md` → **FEAT-021/FEAT-022**.
- **Il *come* di dettaglio** (collocazione del check — singoli install-builder vs. helper condiviso del
  kit; forma esatta delle note; aggiornamento della tabella capability in `packages/sertor/docs/install.md`;
  emissione della nota memory-capture sempre vs. solo con `SERTOR_MEMORY=true`): fase di **design/plan**.

> **Tracciamento dello scope.** I rinvii reali sono già **promossi a casa durevole** nel backlog
> d'epica: distribuzione `SERTOR_MEMORY_ADAPTER=copilot-cli` → **FEAT-009 epica memoria-conversazioni**;
> visibilità SessionStart Copilot → **E10-FEAT-008**; pulizia stile/altitude → **FEAT-021/FEAT-022**;
> gemello bash + guardia `pwsh` runtime → **Won't (qui)** per decisione utente. Nessun rinvio reale
> resta sepolto in `specs/`. La feature è *done* quando l'installer rileva l'assenza di `pwsh` su
> non-Windows ed emette la nota azionabile, emette la nota `memory-capture` su Copilot CLI, la
> documentazione utente dichiara prerequisito e surface parziali, e le guardie (note + sync
> dogfood↔bundle) sono verdi (additive all'installer).

### Forche di design — RISOLTE con l'utente (per `/speckit-plan`)
- **DA-1 — Strategia OS: RISOLTA.** Guardia `pwsh` + gap dichiarato; hook PS-only senza gemello bash.
  Codificata in §Fuori ambito e nei requisiti del Gruppo A. *(decisione utente; FR-001..006.)*
- **DA-2 — Onestà surface inerti: RISOLTA.** Marcare esplicitamente i surface inerti nel report
  d'install via il meccanismo esistente `InstallReport.notes`, invece di affermare «parità piena».
  *(decisione utente; FR-002/007.)*
- **DA-3 — `memory-capture` su Copilot: RISOLTA (verifica codice).** L'adapter Copilot esiste (FEAT-008
  epica memorie, 2026-06-22) ma l'installer non imposta il valore → la nota di FR-007/008 è la risposta
  corretta; la distribuzione del valore è FEAT-009 (memorie), cross-ref. *(verifica codice.)*
- **DA-4 — SessionStart Copilot CLI: RISOLTA (verifica codice).** È un `type:"prompt"` funzionale (non
  inerte); il tema di visibilità è E10-FEAT-008 e non rientra qui. *(verifica codice.)*
- **DA-D-r1 (residuo, design) — Collocazione del check `pwsh`:** nei singoli install-builder
  (`install_rag.py`, `install_wiki.py`) oppure in un helper condiviso del kit (`sertor-install-kit`),
  per riusabilità futura da `sertor-flow`: *come* di plan.
- **DA-D-r2 (residuo, design) — Emissione nota `memory-capture`:** sempre su install rag Copilot CLI
  oppure solo se `SERTOR_MEMORY=true` (raccomandazione: sempre, perché chi abiliterà la memoria deve già
  saperlo); + se aggiornare la tabella capability in `packages/sertor/docs/install.md`: *come* di plan.
