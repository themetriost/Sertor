# Feature Specification: Portabilità POSIX degli hook (hook portabili)

**Feature Branch**: `095-portable-hooks-09`

**Created**: 2026-07-08

**Status**: Draft

**Input**: A-09 (assessment SWOT P1). Requisiti in
`requirements/sertor-cli/portabilita-hook-python/requirements.md` (13 REQ EARS). Promuove la parte
«hook Linux» di E2-FEAT-010. **DA-1 lock (utente):** *sostituzione* (single-impl ovunque) con la
**verifica di parità come gate pre-merge**.

## User Scenarios & Testing *(mandatory)*

Attori: l'**ospite mac/Linux senza `pwsh`** (oggi penalizzato), l'**ospite Windows** (non deve
regredire), il **manutentore** (una sola implementazione).

### User Story 1 — Su mac/Linux senza `pwsh` gli hook funzionano (Priority: P1)

Uno sviluppatore installa Sertor su un progetto su macOS/Linux e **non** ha PowerShell Core. Oggi gli
8 hook host-facing (freschezza RAG, cattura memoria, avviso versione, rituale wiki) sono **inerti** —
installati ma mai eseguiti — e l'unica risposta è una nota «installa `pwsh`». Con questa feature, ogni
hook **scatta al suo evento e completa** l'effetto atteso senza richiedere `pwsh`.

**Why this priority**: è il cuore della feature e la riparazione pratica del **Principio X** — una
capacità installata ma inerte su un intero OS-family non è host-agnostica.

**Independent Test**: su un host macOS/Linux senza `pwsh`, ai rispettivi eventi ciascun hook produce
il suo effetto osservabile (file di stato scritto, re-index avviato, avviso emesso, contesto caricato).

**Acceptance Scenarios**:

1. **Given** un host mac/Linux **senza `pwsh`**, **When** una sessione dell'agente termina (SessionEnd),
   **Then** `rag-freshness` avvia il re-index e scrive `.sertor/.rag-health.json`, e `version-check`
   aggiorna `.sertor/.version-check.json` — **senza** errori né richiesta di `pwsh`.
2. **Given** lo stesso host, **When** una sessione inizia (SessionStart), **Then** gli hook di start
   (`rag-freshness-start`, `version-check-start`, `wiki-session-start`) leggono lo stato ed emettono il
   loro output all'agente.
3. **Given** lo stesso host, **When** l'agente sta per usare un tool (PreToolUse), **Then**
   `sertor-rag-usage-check` emette il promemoria MCP-first **non-bloccante** (fail-open).

### User Story 2 — Parità funzionale, verificata come gate pre-merge (Priority: P1)

Il manutentore deve avere la garanzia che gli hook portabili facciano **esattamente** ciò che facevano
i `.ps1`: stesso contratto di output **per-assistente** (Claude / Copilot), stessi file di stato,
stessa semantica **fail-safe**. La parità è **verificata** e funge da **gate pre-merge**: se i portabili
divergono, non si merge.

**Why this priority**: senza parità provata, la sostituzione dei `.ps1` rischia una regressione
silenziosa del comportamento dell'assistente. È la rete di sicurezza della decisione DA-1.

**Independent Test**: per ciascun hook, con input simulati, l'output verso l'assistente e gli effetti di
stato del portabile **coincidono** con quelli attesi dal `.ps1`; la verifica gira offline (+ smoke CI).

**Acceptance Scenarios**:

1. **Given** un hook portabile, **When** lo si esegue con l'evento e l'input simulati, **Then** l'output
   per-assistente (Claude: `additionalContext`/`decision` sullo stream corretto; Copilot: formato
   nativo) è **quello atteso**, identico al `.ps1`.
2. **Given** un fallimento interno di un hook, **When** l'hook termina, **Then** esce **`0`**, non blocca
   la sessione, e scrive il breadcrumb `.sertor/.last-hook-error` (schema `hook.error/1`) **senza
   segreti**.
3. **Given** lo stdin rediretto/assente, **When** l'hook parte, **Then** **non si blocca** in attesa di
   input.

### User Story 3 — Una sola implementazione, nessuna regressione Windows (Priority: P2)

Il manutentore vuole **un** corpo per hook (non due per shell) e nessun host lasciato scoperto: i
portabili funzionano **anche su Windows**, dove oggi giravano i `.ps1`; a parità provata, i `.ps1`
sono **ritirati** (niente coesistenza/drift).

**Why this priority**: la ragione stessa della scelta B (host-agnostico, zero drift). Il ritiro dei
`.ps1` avviene **solo** dopo la parità (US2), quindi Windows non resta mai scoperto.

**Independent Test**: su Windows, gli hook portabili producono gli stessi effetti dei `.ps1` (parità);
dopo il ritiro, nel bundle non restano `.ps1` per gli 8 hook e il wiring non dipende da una shell
Windows-only.

**Acceptance Scenarios**:

1. **Given** un host Windows, **When** gli eventi scattano, **Then** gli hook portabili producono gli
   effetti attesi (parità con i `.ps1` rimossi).
2. **Given** il bundle post-feature, **When** si ispezionano gli asset hook, **Then** esiste **una**
   implementazione per hook e il wiring (`settings.json` / Copilot) è **OS-indipendente**.

### Edge Cases

- **Runtime assente** (es. install wiki-only che non ha creato il runtime `.sertor/`): l'hook wirato ma
  senza interprete disponibile **degrada fail-safe** (exit 0, breadcrumb ispezionabile, nessun crash di
  sessione) — vedi FR-011/DA-3.
- **Detach del worker re-index cross-OS**: il background di `rag-freshness` non deve lasciare processi
  zombie né bloccare la chiusura sessione su alcun OS.
- **Encoding/locale**: output e file di stato coerenti (UTF-8) su tutti gli OS, come i `.ps1`.
- **Migrazione**: durante l'aggiornamento di un ospite esistente, il ritiro dei `.ps1` non deve lasciare
  wiring orfano (voci `settings.json` che puntano a script rimossi) — l'upgrade riconcilia il wiring.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Gli 8 hook host-facing MUST essere **operativi su Windows, macOS e Linux** senza
  richiedere `pwsh`. *(REQ-001)*
- **FR-002**: Ogni hook portabile MUST produrre gli **stessi effetti osservabili** del `.ps1` che
  sostituisce — stesso evento, stessi file di stato (`.sertor/.rag-health.json`,
  `.sertor/.version-check.json`), stessi side-effect (re-index avviato, transcript catturato, contesto
  caricato, promemoria emesso). *(REQ-002)*
- **FR-003**: Ogni hook MUST emettere il **contratto di output per-assistente** invariato — Claude
  (`additionalContext`/`decision` sullo stream corretto) e Copilot (formato nativo). *(REQ-003)*
- **FR-004**: Ogni hook MUST essere **fail-safe**: exit `0` sempre, mai bloccante; il `PreToolUse` MUST
  restare **fail-open**. *(REQ-004)*
- **FR-005**: Un hook con **stdin rediretto/assente** MUST NOT bloccarsi in attesa di input. *(REQ-005)*
- **FR-006**: `rag-freshness` (SessionEnd) MUST avviare il re-index in modo **detached/background** che
  **non blocca** la chiusura sessione, su **tutti** gli OS. *(REQ-006)*
- **FR-007**: In caso di errore, un hook MUST scrivere `.sertor/.last-hook-error` (schema `hook.error/1`)
  **senza segreti** e uscire `0`. *(REQ-007)*
- **FR-008**: Gli hook MUST NOT introdurre **dipendenze runtime nuove** oltre a quanto il runtime
  installato già fornisce. *(REQ-008)*
- **FR-009**: La modifica MUST lasciare `sertor-core` **invariato**; la logica hook vive negli **asset
  dell'installer**, non nel core. *(REQ-009)*
- **FR-010**: Il wiring degli hook (`settings.json` per Claude, wiring Copilot) MUST essere
  **OS-indipendente** — nessuna dipendenza da una shell Windows-only (`"shell": "powershell"`).
  *(REQ-010)*
- **FR-011**: Se il runtime necessario a un hook è **assente**, l'hook MUST **degradare fail-safe** (no
  errore, no blocco, breadcrumb ispezionabile). *(REQ-011)*
- **FR-012**: A parità provata, i `.ps1` degli 8 hook MUST essere **ritirati** (single-impl,
  sostituzione DA-1) e la nota `pwsh`-unavailability (E10-FEAT-018) aggiornata/rimossa dove non più
  necessaria per l'operatività degli hook. *(REQ-012, DA-1 lock)*
- **FR-013**: MUST esistere una **verifica di parità** (per-assistente + effetti di stato), runnable in
  CI, che funge da **gate pre-merge** (se un portabile diverge, il merge è bloccato). *(REQ-013)*

### Key Entities

- **Hook portabile**: un asset host-facing eseguito a un evento dell'agente; produce output
  per-assistente + effetti di stato; fail-safe. *Invariante:* iso-funzionale al `.ps1` che sostituisce.
- **Contratto di output per-assistente**: la forma che Claude/Copilot leggono (additionalContext/decision
  · formato nativo). *Invariante:* preservato.
- **File di stato**: `.sertor/.rag-health.json`, `.sertor/.version-check.json`, breadcrumb
  `.last-hook-error`. *Invariante:* stessi path/schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su un host macOS/Linux **senza `pwsh`**, **8/8** hook scattano e completano l'effetto
  atteso al loro evento (verificato).
- **SC-002**: Per **ogni** hook, l'output per-assistente coincide con quello atteso dal `.ps1` su
  Windows/macOS/Linux (parità = **100%**), verificata come **gate pre-merge**.
- **SC-003**: **8/8** hook sono fail-safe (exit 0 su fallimento, non bloccanti, breadcrumb secret-free).
- **SC-004**: **0** dipendenze runtime nuove introdotte.
- **SC-005**: Post-feature esiste **una** implementazione per hook (0 `.ps1` residui per gli 8) e il
  wiring è OS-indipendente (0 `"shell":"powershell"` per questi hook).
- **SC-006**: `sertor-core` **byte-invariato**; suite (`-m "not cloud"`) + `ruff` verdi pre-merge; nessuna
  regressione Windows nei test.

## Out of Scope

- **Nuove capacità** degli hook: è una **riscrittura iso-funzionale**, non un ampliamento.
- **`sertor-core`** e gli **asset non-hook** (skill, agenti, blocchi `CLAUDE.md`).
- La **disciplina di versioning `/VERSION`** (E2-FEAT-014, separata).
- Il resto di **E2-FEAT-010** (fallback `pip`, avviso target non-Python, install multi-target) — solo la
  parte «hook Linux» è in ambito.

## Assumptions

- **Runtime disponibile:** il runtime `.sertor/` installato fornisce l'interprete su cui gli hook
  portabili girano su ogni OS (verificato per `sertor install rag`); il caso wiki-only è coperto da
  FR-011 (degrado) — l'interprete effettivo è DA-3, da fissare al plan.
- **DA-1 = sostituzione** (single-impl, no coesistenza) con parità-gate pre-merge — deciso dall'utente.
- **DA-2/3/4** (meccanismo di invocazione portabile dal wiring; interprete per gli hook wiki-only; forma
  esatta della verifica di parità offline+CI) sono **dettagli di design** → plan, non bloccano la spec.
- **Guardie di sync dogfood↔bundle** vanno aggiornate al nuovo insieme di asset hook (byte-copy).
- **Rete** richiesta a runtime solo dall'hook `version-check` (GET `/VERSION`), come oggi.
