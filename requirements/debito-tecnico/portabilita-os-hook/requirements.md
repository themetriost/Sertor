# Requisiti — Portabilità OS degli hook + onestà sui surface Copilot inerti

<!-- Deriva da: FEAT-018 (epica debito-tecnico) — audit ISSUE-04 del 2026-06-26 -->

## 1. Contesto e problema (perché)

Gli hook PowerShell distribuiti da `sertor install` presentano due classi di disonestà nei confronti
dell'ospite.

### 1.1 Fallimento silenzioso su host non-Windows

Gli hook vengono depositati come file `.ps1` e registrati nel wiring del client agente con
un'invocazione PowerShell. Sul client Claude il campo `"shell": "powershell"` nei JSON di settings
(es. `assets/rag/settings.rag-freshness.json:8`, `assets/settings.hooks.json:8`) richiama
`powershell.exe` (Windows PowerShell 5.1): funziona su Windows, ma su macOS/Linux l'eseguibile
`powershell` non esiste e il client agente non è in grado di invocare lo script. Il hook non viene
mai eseguito, nessun messaggio d'errore, exit 0.

Sul client Copilot CLI, i comandi hook usano esplicitamente `pwsh -File <script>` (costante
`_PWSH = "pwsh -File"` in `install_rag.py:123` e `install_wiki.py:104`): se PowerShell Core
(`pwsh`) non è installato su macOS/Linux, il comando fallisce silenziosamente.

L'installer non rileva la situazione né la segnala. L'utente su un host non-Windows crede di
avere gli hook funzionanti mentre nessuno di essi viene mai eseguito.

**Nota (Windows):** `rag-freshness.ps1` usa internamente `Start-Process pwsh` per lanciare il
worker detached. Se `pwsh` non è installato su Windows, il worker non parte, ma quel path
catastrofico è coperto dall'infrastruttura breadcrumb introdotta da FEAT-019; rimane fuori
dall'ambito di questa feature (decisione di scope).

### 1.2 Claim impliciti non veritieri sui surface «inerti» su Copilot CLI

L'install report afferma implicitamente che tutti gli artefatti depositati sono operativi. Su
Copilot CLI, `memory-capture` è wired e il file `.ps1` viene depositato sotto `.github/hooks/`,
ma è **funzionalmente inerte nelle condizioni di default**:

- `SERTOR_MEMORY=false` per default → no-op su qualunque target (comportamento previsto e
  documentato);
- anche se `SERTOR_MEMORY=true`, l'adapter predefinito è `claude-code`, che legge i file di
  sessione di Claude (`~/.claude/projects/…`) anziché quelli di Copilot CLI
  (`~/.copilot/session-state/…`).

Il `CopilotCliCaptureAdapter` esiste (FEAT-008 epica memoria-conversazioni, 2026-06-22), ma il
template `.env` distribuito dall'installer non imposta `SERTOR_MEMORY_ADAPTER=copilot-cli`. La
distribuzione è rinviata a FEAT-009 dell'epica memoria-conversazioni. Il commento a
`install_rag.py:146-148` ("capture is INERT until a Copilot capture adapter exists (FEAT-008)")
è perciò parzialmente stale dopo il 2026-06-22: l'adapter esiste; la lacuna residua è il template
installer. L'aggiornamento del commento è un implementation detail per il plan, non un requisito
comportamentale qui.

Il meccanismo `InstallReport.notes` (introdotto in FEAT-011 compatibilità-copilot, campo
`sertor-install-kit/report.py:44`; metodo `.note()` a riga 74) è già predisposto per
gap-declaration di questo tipo, ma non è ancora usato in codice di produzione. FEAT-018 è la
prima vera emissione di note nel percorso install.

**Valore:** applicare il **Principio XII «Fail Loud, Fix the Cause»** (nessun claim vuoto) e il
**Principio X** (portabilità reale, non solo nominale): gli host non-Windows ricevono un segnale
azionabile quando manca il prerequisito; i claim dell'installer corrispondono allo stato reale
dei surface.

## 2. Obiettivi e criteri di successo

- **CS-1** Su un host non-Windows in cui `pwsh` non è in PATH, un `sertor install` (rag o wiki)
  che deposita hook **non dichiara quei hook operativi**: il report d'install contiene una nota
  esplicita — visibile sia nella resa umana sia in `notes[]` del JSON — che identifica i surface
  affetti e fornisce una rimediazione azionabile con URL. Verificabile simulando l'assenza di
  `pwsh` e ispezionando `report.notes`.

- **CS-2** Su un host non-Windows in cui `pwsh` è disponibile, la nota d'indisponibilità non
  viene emessa. Verificabile simulando la presenza di `pwsh` e confermando `report.notes` privo
  della nota pwsh.

- **CS-3** Su un host Windows con target Claude, `report.notes` resta `[]` (non-regression).
  Verificabile con il test esistente `test_claude_report_has_no_gap_note`.

- **CS-4** Un install Copilot CLI (rag) include nel report una nota che identifica
  `memory-capture` come richiedente configurazione esplicita (il valore adapter Copilot per
  `SERTOR_MEMORY_ADAPTER`) per catturare sessioni Copilot CLI. Verificabile controllando
  `report.notes` su un install Copilot CLI simulato.

- **CS-5** La documentazione utente (`docs/install.md` e `docs/install-copilot.md`) dichiara
  esplicitamente `pwsh` come prerequisito su macOS/Linux, con URL di installazione e indicazione
  dei surface che ne dipendono. Verificabile leggendo i due file.

## 3. Stakeholder e attori

- **Utente ospite su macOS/Linux** — deve ricevere informazione chiara che gli hook richiedono
  `pwsh` prima o durante l'install, non scoprirlo per assenza di effetti settimane dopo.
- **Utente ospite su Copilot CLI** — deve sapere che `memory-capture` richiede configurazione
  aggiuntiva per funzionare sul suo assistente e cosa deve impostare.
- **Agente frontier dell'ospite** — legge il report d'install e può comunicare o agire sui gap
  dichiarati.
- **Manutentore di Sertor** — le guard tests proteggono da regressioni: né claim dishonest
  reimportati né nota pwsh persa.

## 4. Ambito

### In ambito

- Il **rilevamento della disponibilità di `pwsh`** all'install-time su host non-Windows, per le
  capability `rag` e `wiki` (entrambe depositano hook che ne dipendono).
- L'**emissione della nota d'indisponibilità pwsh** in `InstallReport.notes` quando la condizione
  è rilevata.
- La **nota di configurazione esplicita per `memory-capture`** su install Copilot CLI (rag).
- L'**aggiornamento della documentazione utente** (`docs/install.md`, `docs/install-copilot.md`)
  per dichiarare prerequisiti e surface parzialmente funzionali.
- Le **guard tests** per le note emesse e la non-regressione sul percorso Claude+Windows.
- La coerenza del **sync bundled↔dogfood** (`test_assets_sync.py`).

### Fuori ambito

- **Gemello bash degli hook** (`.sh`): escluso per decisione utente. Gli hook restano PS-only,
  una sola copia per hook (convenzione del progetto «solo PowerShell, non bash»). Nessun
  raddoppio di asset, nessuna guardia di parità `.ps1`↔`.sh`.
- **Guardia pwsh su Windows** per l'uso interno di `rag-freshness.ps1` (`Start-Process pwsh`):
  il breadcrumb FEAT-019 copre quel path catastrofico su Windows; escluso per decisione di scope.
- **Rilevamento runtime** (all'avvio dello script): se `pwsh` manca, il processo non parte —
  il rilevamento runtime richiede `pwsh` stesso. Il punto d'intervento corretto è l'install-time.
- **Codice di `sertor_core`**: zero modifiche (Principio XI). Gli hook non importano `sertor_core`
  né chiamano un LLM.
- **Distribuzione di `SERTOR_MEMORY_ADAPTER=copilot-cli`** nel template `.env`: è FEAT-009
  epica memoria-conversazioni (già tracciata). Qui si emette solo la nota che la configurazione
  è necessaria; il completamento appartiene a quella feature.
- **Visibilità del segnale SessionStart su Copilot CLI** (prompt `type:"prompt"` più visibile
  vs. iniezione silenziosa su Claude): non è un surface «inerte» (il prompt funziona e il
  segnale arriva all'agente), ma si comporta diversamente. Tracciato in **FEAT-008 E10**;
  cross-ref ma non assorbito qui.
- **Pulizia stile/altitude** dei body degli hook e dei blocchi `CLAUDE.md` — FEAT-021/022.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Guardia pwsh all'install-time

- **REQ-001** When `sertor install rag` or `sertor install wiki` runs on a non-Windows host, the
  installer shall detect whether `pwsh` (PowerShell Core) is available on the system PATH.

- **REQ-002** If `pwsh` is not found on a non-Windows host during installation and hook surfaces
  are being deposited, then the installer shall add a note to the install report that: (a)
  identifies which hook surfaces are deposited but non-operational without `pwsh`; (b) provides
  an actionable remediation message, including a URL where the user can install PowerShell Core.

- **REQ-003** The pwsh-unavailability note shall appear in both the human rendering and the JSON
  `notes[]` array of the install report, consistent with the existing `InstallReport.notes`
  contract (`sertor-install-kit/report.py:74`).

- **REQ-004** If `pwsh` IS available on a non-Windows host, the installer shall NOT emit the
  pwsh-unavailability note.

- **REQ-005** The pwsh check shall be non-fatal to the install: even when `pwsh` is absent, all
  non-hook surfaces (MCP config, instruction block, env template, skills, agents, gitignore)
  shall be installed without error, and the overall exit code shall be 0 if no other errors occur.

- **REQ-006** On a Windows host, the installer shall NOT emit the pwsh-unavailability note
  (the `"shell": "powershell"` Claude wiring is valid on Windows; the Copilot `pwsh -File` wiring
  is a separate concern covered per-capability by the documentation).

### Gruppo B — Onestà sui surface inerti (Copilot CLI)

- **REQ-007** When `sertor install rag` targets Copilot CLI, the install report shall include a
  note stating that `memory-capture` requires both `SERTOR_MEMORY=true` and an explicit Copilot
  adapter value for `SERTOR_MEMORY_ADAPTER` to capture Copilot CLI sessions; with the default
  configuration the hook fires but captures nothing useful.

- **REQ-008** The note emitted by REQ-007 shall reference the pending capability that would
  complete the out-of-the-box experience (the installer template distribution of the Copilot
  adapter value, tracked separately in epica memoria-conversazioni), so the user understands
  that a fix is planned and can opt in manually in the meantime.

- **REQ-009** When `sertor install rag` targets Claude on Windows (the primary current-target
  path), the installer shall NOT emit the Copilot-adapter inertness note (non-regression:
  `report.notes == []` for that path).

### Gruppo C — Documentazione utente

- **REQ-010** The `docs/install.md` (install reference) shall declare `pwsh` (PowerShell Core)
  as a required prerequisite on macOS/Linux for hook surfaces to function, including a URL for
  installation, a list of the affected surfaces, and the statement that without `pwsh` those
  surfaces are installed but non-operational.

- **REQ-011** The `docs/install-copilot.md` (Copilot quick-start) shall declare, for the
  Copilot CLI target: (a) that hooks require `pwsh` on macOS/Linux; (b) that `memory-capture`
  requires explicit adapter configuration to capture Copilot CLI sessions, with the environment
  variables to set.

- **REQ-012** The `docs/install.md` shall list, for each supported target (Claude on Windows,
  Copilot CLI), which surfaces are fully operational after install and which require additional
  manual configuration, with what those steps are.

### Gruppo D — Guard tests e sync

- **REQ-013** The feature shall provide a guard test that verifies: (a) a simulated non-Windows
  install without `pwsh` produces a note containing pwsh-unavailability information in
  `report.notes`; (b) a simulated non-Windows install with `pwsh` available does NOT emit that
  note; (c) a Claude-on-Windows install has `report.notes == []` (non-regression of the existing
  test).

- **REQ-014** The feature shall provide a guard test that verifies a Copilot CLI rag install
  emits a note about `memory-capture` requiring explicit adapter configuration, present in
  `report.notes`.

- **REQ-015** The canonical asset sync between bundled assets and the dogfood copies under
  `.claude/` shall remain intact; the existing sync guard (`test_assets_sync.py`) shall stay
  green after any asset changes introduced by this feature.

## 6. Requisiti non funzionali

- **NFR-1 (Costituzione)** Realizza il Principio XII («Fail Loud, Fix the Cause»): nessun
  claim implicito non verificato, nessun fallimento silenzioso senza segnale per l'utente.
  Realizza il Principio X: la portabilità dichiarata corrisponde alla portabilità reale.
- **NFR-2 (Principio XI)** Il rilevamento di `pwsh` avviene in codice installer (Python); zero
  import di `sertor_core`; nessun LLM coinvolto nel check.
- **NFR-3 (Non-fatale, non-bloccante)** L'assenza di `pwsh` non provoca exit non-zero
  dell'installer. La nota è un warning informatvo, non un blocco. Il costo del check è
  trascurabile (singola chiamata `which`/`shutil.which`).
- **NFR-4 (Host-agnostico, Principio X)** Il check si applica a qualunque host non-Windows;
  nessun hardcoding a distribuzioni Linux specifiche. La condizione è binaria: pwsh
  trovato/non trovato.
- **NFR-5 (Non-regressione, Principio VI)** Il percorso Claude+Windows — il caso più comune —
  non cambia comportamento: `report.notes == []`, nessun nuovo artefatto, nessun cambio di
  wiring. CS-3 lo verifica con il test esistente.
- **NFR-6 (Additività installer)** Le modifiche sono additive: lifecycle install/upgrade/
  uninstall invariato salvo l'aggiunta delle note; nessuna rimozione di capability.
- **NFR-7 (Additività core)** `sertor-core` invariato; la feature tocca il pacchetto installer
  `sertor`, eventualmente `sertor-install-kit` per un helper condiviso, e `docs/`.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (decisione utente — RISOLTA):** gli hook restano `.ps1` PowerShell-only; nessun
  gemello `.sh`, nessun raddoppio di asset.
- **Vincolo (decisione utente — RISOLTA):** la strategia è «guardia `pwsh` + gap dichiarato»;
  il requisito `pwsh` su non-Windows è un prerequisito dichiarato, non nascosto.
- **Assunzione:** la distinzione Windows/non-Windows si rileva tramite API o variabile
  d'ambiente standard di Python — il *come* è materia del plan.
- **Assunzione:** la disponibilità di `pwsh` si rileva cercando l'eseguibile nel PATH tramite
  API standard — il *come* è materia del plan.
- **Assunzione:** il check pwsh copre entrambe le capability (wiki e rag) che depositano hook;
  se condividono il codice di esecuzione del plan, il check può essere centralizzato.
- **Dipendenza:** `InstallReport.notes` e il metodo `.note()` già esistono in
  `sertor-install-kit/report.py:74-77` e sono testati (test `test_cli_report_has_no_vscode_gap`
  e `test_claude_report_has_no_gap_note`). Si usa l'infrastruttura esistente, nessuna
  modifica al kit necessaria oltre all'uso del meccanismo.
- **Dipendenza:** il test `test_claude_report_has_no_gap_note` in
  `packages/sertor/tests/test_install_wiki_copilot_cli.py:192-196` afferma `report.notes == []`
  per Claude su Windows. Il check pwsh non deve attivarsi su Windows (CS-3).
- **Dipendenza cross-feature:** FEAT-009 epica memoria-conversazioni (distribuzione
  `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env`) completa il percorso; qui si emette
  solo la nota che orienta l'utente verso quella configurazione.
- **Dipendenza cross-feature:** FEAT-008 E10 (visibilità SessionStart Copilot CLI) —
  cross-ref, non assorbita qui.
- **Dipendenza cross-feature:** FEAT-019 (fail-loud breadcrumb negli hook) — complementare:
  FEAT-019 copre «lo script gira ma l'operazione interna fallisce»; FEAT-018 copre «lo script
  non può nemmeno partire perché manca `pwsh`».

## 8. Rischi

- **R-1 Scope drift:** aggiungere OS-detection sofisticata (rilevamento distribuzione Linux,
  verifica versione `pwsh`). Mitigazione: il check è binario (trovato/non trovato via `which`),
  nessun test di versione.
- **R-2 Falso positivo su Windows:** un check mal condizionato emette note anche su Windows.
  Mitigazione: REQ-006 + CS-3 (guard test di non-regressione esplicita).
- **R-3 Nota troppo prolissa su Copilot:** una nota verbosa per ogni install Copilot degrada
  la UX del report. Mitigazione: REQ-007/008 specificano contenuto minimo (condizione + adapter
  + cross-ref); la forma esatta è decisa in plan.
- **R-4 Nota memory-capture diventa stale:** la nota diventa obsoleta quando FEAT-009
  memoria-conversazioni distribuisce il valore adapter. Mitigazione: REQ-008 cross-referenzia
  la feature successiva; al merge di quella feature la nota viene rimossa o condizionata.
- **R-5 Ambiguità sul SessionStart Copilot:** l'audit ISSUE-04 citava anche il segnale
  SessionStart come «inerte». La verifica del codice mostra che il SessionStart Copilot CLI è
  un `type:"prompt"` funzionale (non inerte), diverso dal SessionStart Claude (silenzioso) ma
  non privo di effetto. Mitigazione: la feature non emette nota per SessionStart; il tema di
  visibilità è tracciato in FEAT-008 E10. Se in plan emerge un caso genuino di inertness,
  si aggiunge il requisito.
- **R-6 Mancanza di test su Linux in CI:** i test girano su Windows (FEAT-003 E10, CI Linux
  avviata ma suite non completa); il check non-Windows va testato con OS mocking/patching per
  restare deterministico in CI Windows. Mitigazione: i guard test (REQ-013) devono usare
  fixture che simulano l'OS anziché dipendere dall'OS reale.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-005, REQ-007, REQ-010, REQ-013, REQ-014.
- **Should:** REQ-004, REQ-006, REQ-008, REQ-009, REQ-011, REQ-012, REQ-015.
- **Could:** audit sistematico di altri surface Copilot che potrebbero meritare una nota
  (es. hook che richiedono pwsh specificamente su Windows senza PS Core).
- **Won't (qui):** gemello `.sh`; guardia pwsh runtime; distribuzione `SERTOR_MEMORY_ADAPTER=
  copilot-cli` (FEAT-009 memoria-conversazioni); visibilità SessionStart Copilot (FEAT-008 E10);
  pulizia stile (FEAT-021/022).

## 10. Domande aperte

- **[RISOLTA — decisione utente]** Strategia OS: guardia `pwsh` + gap dichiarato; hook
  PS-only senza gemello bash. Codificata in §4 (fuori ambito) e nei requisiti del Gruppo A.
- **[RISOLTA — decisione utente]** Onestà surface Copilot: marcare esplicitamente nel report
  d'install i surface inerti invece di lasciare claim impliciti di «parità piena».
- **[RISOLTA — verifica codice]** `memory-capture` su Copilot: la capture adapter Copilot
  esiste (FEAT-008 memorie, 2026-06-22) ma l'installer non imposta il valore — la nota di
  REQ-007/008 è quindi la risposta corretta.
- **[RISOLTA — verifica codice]** SessionStart Copilot CLI: è un `type:"prompt"` funzionale
  (non inerte); il tema di visibilità è FEAT-008 E10 e non rientra in FEAT-018.
- **[DA CHIARIRE in plan]** La logica del check pwsh risiede nei singoli install-builder
  (`install_rag.py`, `install_wiki.py`) oppure in un helper condiviso del kit
  (`sertor-install-kit`)? Impatta la riusabilità futura da `sertor-flow`.
- **[DA CHIARIRE in plan]** La nota memory-capture (REQ-007) viene emessa sempre su install
  Copilot CLI rag oppure solo se `SERTOR_MEMORY=true`? La raccomandazione è: emetterla sempre
  su Copilot CLI rag, indipendentemente da `SERTOR_MEMORY`, perché l'utente che abilita la
  memoria in futuro deve già saperlo. Ma il plan può decidere altrimenti con motivazione.
- **[DA CHIARIRE in plan/docs]** Va aggiornata anche la tabella capability in
  `packages/sertor/docs/install.md` per riflettere una colonna «operativo out-of-the-box» vs.
  «richiede config aggiuntiva»? O è sufficiente la sezione testuale?
