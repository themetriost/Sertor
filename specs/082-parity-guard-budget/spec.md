# Feature Specification: Parity guard esteso (.ps1/.json) + budget di altitude dei blocchi CLAUDE.md in CI (E10-FEAT-024)

**Feature Branch**: `082-parity-guard-budget` · **Created**: 2026-06-30 · **Status**: Draft

<!-- Deriva da: FEAT-024 (epica debito-tecnico E10) — requirements/debito-tecnico/parity-guard-budget/requirements.md (audit asset first-party 2026-06-26, ISSUE-10) -->

**Input**: FEAT-024 dell'epica `debito-tecnico` (E10). L'audit ISSUE-10 ha rilevato **due lacune nei
guard-rail offline** del progetto. **(1)** Il parity guard dei body Copilot
(`packages/sertor/tests/test_assets_copilot_parity.py`) **esclude esplicitamente** gli script `.ps1` e i
JSON/`.tmpl` generati (`_is_llm_body`, linee 52-58: *"Scripts (.ps1) and generated config/manifest
templates are out of scope"*); separatamente, `test_schema_copilot_hooks.py` valida lo **schema** del
wiring Copilot reso ma **non** che gli eventi attesi (`SessionEnd`/`SessionStart`/`PreToolUse`) siano
**presenti** — manca quindi un assert sullo *shape/presenza* del wiring Copilot. Questo è proprio il tipo
di **drift silenzioso** già successo: in FEAT-011/049 il wiring hook Copilot era in formato Claude
(annidato, `shell`, `timeout`) e veniva scartato silenziosamente dal client → 0 hook eseguiti, senza che
alcun test lo segnalasse. **(2)** Non esiste **alcun freno** alla ricrescita dei blocchi `claude-md-block*.md`
iniettati **always-on** in ogni host: dopo FEAT-021 lo stato verificato è wiki **52** · RAG **49** · SDLC
**64** righe, ma nessun test impone una soglia → ogni futura contribution può erodere silenziosamente la
riduzione di altitude. Il valore: chiudere entrambe le falle con **guardie offline additive** che rendano
la CI rossa quando un evento del wiring Copilot sparisce o quando un blocco always-on supera la sua soglia.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è la **qualità e realtà
> del contesto reso a chi legge il repo e all'agente frontier ospite**. Un wiring Copilot a cui manca un
> evento (drift silenzioso) e blocchi always-on che ricrescono senza freno **degradano il contesto reso
> all'agente ospite**: il primo lascia l'agente senza la freschezza-RAG/memoria enforced via hook (contesto
> stantio non rilevato); il secondo gonfia l'istruzione always-on, abbassando il segnale-rumore di ciò che
> l'agente legge a ogni sessione. Entrambe le guardie sono **igiene host-facing** sul confine **D↔N**:
> nessun codice del core, nessun LLM, nessun cambiamento di comportamento — solo reti CI che impediscono la
> regressione di capacità host-facing già consegnate (freschezza-RAG FEAT-076, altitude FEAT-021).

> **Natura del cambiamento: ADDITIVA / solo test e guardie, ZERO codice di `sertor_core`.** La feature
> **non** modifica `sertor_core` né alcun comando/vehicle/porta/adapter/engine (Principio XI). **Non**
> modifica il codice di `install_rag.py`, `install_governance.py`, `surfaces.py`, né alcun hook `.ps1` o
> asset distribuito. Aggiunge **esclusivamente** nuovi file di test (ed eventualmente un sottile helper di
> test), idealmente **zero codice runtime**. **Zero cambiamento di comportamento** dell'installer e della
> generazione dei payload per entrambi gli assistenti (`claude`, `copilot-cli`): byte-identico prima e dopo.

> **Decisioni di scope — FISSATE (erano le forche aperte §1.4 / DA-1, DA-2 dei requirements).**
> - **DA-1 (soglia budget): DIFFERENZIATA per-blocco — `wiki = 60`, `RAG = 58`, `SDLC = 70`** (costanti
>   esplicite nel test). **Non** la soglia uniforme 75 della raccomandazione analista: i blocchi
>   pre-FEAT-021 erano wiki **71** / RAG **72**, quindi una soglia ≥ 71 li lascerebbe ricrescere fin oltre
>   la riduzione ottenuta. Le soglie scelte danno ~6-9 righe di headroom sull'attuale (wiki 52→60, RAG
>   49→58, SDLC 64→70) **e** bloccano la ricrescita oltre i valori pre-riduzione. Le costanti si aggiornano
>   solo deliberatamente (REQ-012) — il trade-off resta visibile.
> - **DA-2 (source-level guard `.ps1` stdout, REQ-015..017): IN AMBITO come SHOULD.** È economica (lettura
>   sorgente + regex, offline) e chiude un rischio storico (output `decision`/`reason` su stdout che
>   confonderebbe il client Copilot su `sessionEnd`). Confermata SHOULD, non declassata a Could.

> **Ancoraggio all'esistente (dato di partenza, non da progettare).** Stato su `master` verificato: blocchi
> `claude-md-block.md` (wiki, **52** righe), `rag/claude-md-block-rag-usage.md` (RAG, **49**),
> `claude-md-block-sdlc.md` (SDLC, **64**). Wiring Copilot rag = **6 frammenti** generati via
> `render_copilot_hooks()` e uniti in `sertor-hooks.json` dal dispatch `_rag_hook_fragment()`
> (`install_rag.py`): PreToolUse `sertor-rag-usage-check.ps1` · SessionEnd `memory-capture.ps1` ·
> SessionEnd `rag-freshness.ps1` · SessionStart prompt-statico · SessionEnd `version-check.ps1` ·
> SessionStart prompt-statico. Guardie esistenti da riusare/complementare:
> `packages/sertor/tests/test_schema_copilot_hooks.py` (`assert_valid_copilot_hook_file`,
> `test_real_rag_wiring_is_schema_valid`, pattern d'esecuzione del piano in `tmp_path`),
> `test_assets_copilot_parity.py` (accesso asset via `read_asset_text`),
> `test_assets_hook_breadcrumb.py` (pattern anti-vacuità con lista attesa `_RAG_HOOKS`),
> `test_assets_hook_cli_invocation.py` (strip commenti `<# … #>` e `#` prima della scansione sorgente).
> I riferimenti **ancorano** i requisiti, non prescrivono il *come*.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Rimuovere un frammento del wiring Copilot rende la guardia rossa (P1, Must)
Un manutentore che rimuove (anche accidentalmente) una delle 6 funzioni-frammento del wiring Copilot da
`install_rag.py` ottiene una CI **rossa**: una nuova shape-guard di presenza fallisce e **nomina l'evento
mancante** (`SessionEnd`/`SessionStart`/`PreToolUse`), invece di lasciar passare un `sertor-hooks.json` a
cui manca un intero evento (drift silenzioso di ISSUE-10).

**Independent Test**: eseguendo il piano rag per `COPILOT_CLI` in `tmp_path` e leggendo il
`sertor-hooks.json` reso, la guardia asserisce che ciascuna delle tre chiavi-evento attese contiene almeno
una entry; simulando un piano privo di un frammento, la guardia fallisce nominando l'evento assente.

**Acceptance**:
1. **Given** il piano rag eseguito per `COPILOT_CLI`, **When** la shape-guard legge il `sertor-hooks.json`
   reso, **Then** esiste ≥1 entry sotto `SessionEnd`, ≥1 sotto `SessionStart`, e ≥1 sotto `PreToolUse` con
   `matcher` non vuoto.
2. **Given** un piano simulato a cui manca uno hook-spec fragment, **When** gira la shape-guard, **Then**
   l'assertion fallisce e il messaggio nomina l'evento assente.
3. **Given** la shape-guard, **When** gira insieme a `assert_valid_copilot_hook_file`, **Then** entrambe
   le condizioni (schema *e* presenza) devono valere: la presenza **complementa**, non sostituisce, lo schema.

### User Story 2 — Un blocco always-on oltre soglia rende la CI rossa (P1, Must)
Un contributor che porta un `claude-md-block*.md` sopra la sua soglia per-blocco ottiene una CI **rossa**:
il budget-test fallisce con un messaggio che nomina **file, conteggio corrente e soglia**, costringendo
l'aggiornamento della soglia a essere una decisione deliberata e visibile (non un'erosione silenziosa).

**Independent Test**: il budget-test conta le righe di ciascun blocco noto e fallisce se il conteggio
supera la costante per-blocco; con una fixture sintetica sopra-soglia l'assertion fallisce.

**Acceptance**:
1. **Given** i tre blocchi noti (wiki 52, RAG 49, SDLC 64) e le soglie (wiki 60, RAG 58, SDLC 70),
   **When** gira il budget-test allo stato corrente, **Then** passa (tutti sotto soglia).
2. **Given** un blocco portato sopra la sua soglia, **When** gira il budget-test, **Then** fallisce con un
   messaggio che nomina il file (package + path relativo), il conteggio corrente e la soglia configurata.
3. **Given** un body sintetico sopra-soglia (fixture), **When** gira l'anti-pattern test, **Then**
   l'assertion fallisce (la guardia non è vacua).

### User Story 3 — Un nuovo blocco `claude-md-block*.md` non sfugge al budget (P1, Must)
Un contributor che aggiunge un **quarto** file `claude-md-block*.md` in `sertor` o `sertor-flow` senza
registrarne la soglia nel budget-test ottiene una CI **rossa**: la coverage è esaustiva, nessun blocco
always-on può comparire senza una soglia che lo sorvegli (no buco silenzioso).

**Independent Test**: scoprendo i file `claude-md-block*.md` nei due package e confrontandoli con
l'insieme registrato delle soglie, la presenza di un file non registrato fa fallire il test nominandolo.

**Acceptance**:
1. **Given** i tre blocchi noti, **When** gira il budget-test, **Then** ciascuno è coperto da una soglia
   esplicita (wiki/RAG/SDLC).
2. **Given** un quarto `claude-md-block*.md` aggiunto senza soglia, **When** gira il budget-test, **Then**
   fallisce nominando il file non registrato.
3. **Given** le soglie, **When** si ispeziona il sorgente del test, **Then** sono costanti esplicite (non
   calcolate dai file a runtime): un aumento è una modifica di codice cosciente.

### User Story 4 — Il difetto storico FEAT-049 resta coperto (P1, Must)
Reintrodurre il difetto di FEAT-049 (wiring hook JSON in formato Claude — annidato, `shell`/`timeout`
invece di `timeoutSec`) continua a far fallire `test_schema_copilot_hooks.py`: la nuova shape-guard di
presenza **non** sostituisce né duplica la schema-guard; le due restano indipendenti e complementari.

**Independent Test**: la suite schema esistente resta invariata e verde; reintrodurre il formato Claude la
fa fallire; la shape-guard di presenza (US1) è un test distinto.

**Acceptance**:
1. **Given** lo schema-test esistente, **When** la feature è completa, **Then** è invariato e resta verde.
2. **Given** il difetto FEAT-049 reintrodotto, **When** gira lo schema-test, **Then** fallisce (copertura
   storica preservata).
3. **Given** la shape-guard di presenza, **When** gira, **Then** è indipendente dallo schema-test (non lo
   richiama né lo rende ridondante).

### User Story 5 — Gli script rag SessionEnd non emettono payload Copilot su stdout (P2, Should)
Una guardia source-level offline asserisce che i tre script rag SessionEnd (`rag-freshness.ps1`,
`memory-capture.ps1`, `version-check.ps1`) **non** contengono righe di codice che emettono un payload
`decision`/`reason` su stdout — l'output che confonderebbe (o farebbe scartare) il client Copilot su un
evento `sessionEnd`. Un futuro contributor che introducesse un tale stdout otterrebbe una CI **rossa**.

**Independent Test**: la guardia legge i sorgenti `.ps1`, **strippa** i commenti a blocco (`<# … #>`) e i
commenti `#` di riga (così la prosa non genera falsi positivi), poi scansiona il codice residuo; con uno
snippet artificiale che emette `decision`/`reason` su stdout nel percorso foreground, l'assertion fallisce.

**Acceptance**:
1. **Given** i tre script rag SessionEnd, **When** gira la guardia source-level (offline, no `pwsh`),
   **Then** nessuno emette un payload `decision`/`reason` su stdout nel codice (commenti esclusi).
2. **Given** un commento/prosa che menziona `decision`/`reason`, **When** gira la guardia, **Then** **non**
   è scambiato per codice (strip commenti prima della scansione).
3. **Given** uno snippet artificiale che emette `decision`/`reason` su stdout nel percorso foreground,
   **When** gira l'anti-pattern test, **Then** l'assertion fallisce (la guardia non è vacua).

### User Story 6 — Le suite esistenti restano verdi e tutto è offline-safe (P1, Must)
Tutte le suite esistenti (`packages/sertor/tests`, `packages/sertor-flow/tests`, root `tests/`) restano
verdi dopo l'aggiunta delle guardie; i nuovi test girano **offline** (no rete, no `uv` subprocess, no
`pwsh` per gli assert critici di schema/presenza/budget). Le nuove guardie sono additive e non modificano
le guardie esistenti.

**Independent Test**: `uv run pytest` sull'intero workspace non produce nuovi fallimenti rispetto al
baseline; i nuovi test passano senza rete né subprocess.

**Acceptance**:
1. **Given** le nuove guardie, **When** gira l'intera suite, **Then** zero nuovi fallimenti rispetto al
   baseline.
2. **Given** i nuovi test dei Gruppi A e B, **When** girano, **Then** non richiedono rete, `pwsh`, `uv` o
   processi figli (solo lettura asset + costruzione piano in `tmp_path`).
3. **Given** le guardie esistenti (`test_schema_copilot_hooks.py`, `test_assets_copilot_parity.py`,
   `test_hooks_script_copilot.py`, `test_assets_sync.py`), **When** la feature è completa, **Then** sono
   invariate (additività).

## Edge Cases
- **Conteggio righe e trailing newline** — il numero di righe può differire di ±1 a seconda della lettura
  (newline finale). La guardia conta con un metodo consistente (es. `splitlines()`, esclude la newline
  finale); le soglie scelte (6-9 righe di headroom) assorbono ogni differenza di ±1 (US2, FR-008).
- **Nuovo frammento Copilot aggiunto a `install_rag.py`** — la shape-guard di presenza copre gli **eventi**
  dichiarati, non automaticamente un nuovo frammento sullo stesso evento; la lista degli eventi attesi è
  commentata nel test e aggiornata quando cambia (pattern `_RAG_HOOKS` di `test_assets_hook_breadcrumb.py`)
  (US1, R-1 requirements).
- **Governance (`sertor-flow`) senza hook JSON** — `install_governance.py` non chiama `render_copilot_hooks`
  né `HookEntrySpec` (verificato): nessun gap di shape-guard su quell'asse. Se in futuro governance
  aggiungesse hook, il Gruppo A va esteso (FR-004, A-002).
- **Prosa che menziona `decision`/`reason`** nei commenti degli script rag — non deve generare falsi
  positivi: la guardia source-level strippa i commenti prima della scansione (US5, FR-010).
- **Quarto blocco `claude-md-block*.md` aggiunto** in `sertor` o `sertor-flow` senza soglia — fa fallire il
  budget-test nominando il file non registrato (US3, FR-006).

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Shape-guard della presenza nel Copilot hook JSON (Must)**
- **FR-001 (presenza eventi).** Eseguito il piano rag per `AssistantId.COPILOT_CLI`, la guardia asserisce
  che il `sertor-hooks.json` reso contiene ≥1 entry sotto `SessionEnd`, ≥1 sotto `SessionStart`, e ≥1 sotto
  `PreToolUse` con `matcher` non vuoto. *(REQ-001/002/003; CS-1)*
- **FR-002 (fallimento nominante).** Se una delle chiavi-evento attese è assente dal JSON prodotto dal
  piano Copilot rag, la guardia fallisce e **nomina** l'evento mancante. *(REQ-004; CS-1)*
- **FR-003 (anti-vacuità).** La guardia include almeno un test anti-pattern che conferma la non-vacuità: un
  piano simulato privo di un hook-spec fragment innesca un'assertion fallita che nomina l'evento assente,
  riusando il pattern di lista attesa di `test_assets_hook_breadcrumb.py`. *(REQ-005; CS-1)*
- **FR-004 (complementa lo schema, non lo sostituisce).** La shape-guard di presenza **complementa**
  `assert_valid_copilot_hook_file` senza duplicarlo né renderlo ridondante: schema e presenza devono valere
  entrambi e restano test indipendenti. *(REQ-007; CS-3)*

**Gruppo B — Budget altitude dei blocchi `claude-md-block*.md` (Must)**
- **FR-005 (budget per-blocco).** Per ciascun `claude-md-block*.md` noto nei package `sertor` e
  `sertor-flow`, il budget-test conta le righe del file e **fallisce** se il conteggio supera la soglia
  per-blocco configurata. Le soglie fissate: **wiki = 60** (`claude-md-block.md`, pkg `sertor`), **RAG = 58**
  (`rag/claude-md-block-rag-usage.md`, pkg `sertor`), **SDLC = 70** (`claude-md-block-sdlc.md`, pkg
  `sertor-flow`). *(REQ-008/010; DA-1; CS-2)*
- **FR-006 (coverage esaustiva).** Se un quarto `claude-md-block*.md` è aggiunto a uno dei due package
  senza una soglia corrispondente nel budget-test, il test **fallisce** nominando il file non registrato.
  *(REQ-011; CS-2)*
- **FR-007 (messaggio diagnostico).** Quando un blocco supera la soglia, il messaggio di fallimento nomina:
  il file (package + path relativo), il conteggio corrente e la soglia configurata per quel file. *(REQ-009;
  CS-2)*
- **FR-008 (soglie come costanti esplicite + anti-vacuità).** Le soglie sono dichiarate come costanti
  esplicite nel sorgente del test (non calcolate dai file a runtime), così un aumento è una modifica di
  codice deliberata e visibile; il budget-test include almeno un anti-pattern (body sintetico sopra-soglia →
  assertion fallita). *(REQ-012/013; DA-1; CS-2)*

**Gruppo C — Source-level guard degli script rag SessionEnd (Should)**
- **FR-009 (no payload `decision`/`reason` su stdout).** *Dove la guardia source-level è implementata*, una
  asserzione offline verifica che i sorgenti dei tre script rag SessionEnd (`rag-freshness.ps1`,
  `memory-capture.ps1`, `version-check.ps1`) non contengono righe di codice che emettono un payload
  `decision`/`reason` JSON su stdout. *(REQ-015; CS-3)*
- **FR-010 (strip commenti prima della scansione).** *Dove la guardia source-level è implementata*, essa
  strippa i commenti a blocco (`<# … #>`) e i commenti `#` di riga dal sorgente prima della scansione, così
  la prosa che menziona il pattern vietato non è scambiata per codice (pattern di
  `test_assets_hook_cli_invocation.py`). *(REQ-016; CS-3)*
- **FR-011 (anti-vacuità Gruppo C).** *Dove la guardia source-level è implementata*, include almeno un test
  anti-pattern che conferma che la guardia cattura uno snippet artificiale che emette un costrutto
  `decision`/`reason` su stdout nel percorso foreground. *(REQ-017; CS-3)*

**Trasversali**
- **FR-012 (offline-safe).** Tutti i nuovi test girano offline: nessuna rete, nessun `uv` subprocess,
  nessun `pwsh` richiesto per gli assert critici (schema/presenza/budget); il Gruppo A riusa il pattern di
  esecuzione del piano in `tmp_path` di `test_schema_copilot_hooks.py`; il Gruppo B accede agli asset via
  `read_asset_text`. *(REQ-006/014; NFR-3; CS-5)*
- **FR-013 (non-regressione delle suite e additività).** Le suite esistenti (`packages/sertor/tests`,
  `packages/sertor-flow/tests`, root) restano verdi; le nuove guardie non modificano, non sostituiscono e
  non richiamano in modo diverso le guardie esistenti. *(NFR-2/5; CS-4)*

### Requisiti non funzionali
- **RNF-1 (Principio XI):** zero modifiche a `sertor_core` — la feature tocca esclusivamente file di test
  (più, al più, un sottile helper di test); nessun engine/porta/adapter/comando/servizio del core è
  coinvolto. *(NFR-1)*
- **RNF-2 (non-regressione comportamentale):** il comportamento dell'installer e della generazione dei
  payload per entrambi gli assistenti (`claude`, `copilot-cli`) è byte-identico prima e dopo l'aggiunta
  delle guardie (nessun codice runtime toccato). *(NFR-4/6)*
- **RNF-3 (offline-safe):** i nuovi test dei Gruppi A e B non richiedono rete, `pwsh` o processi figli (solo
  lettura asset e costruzione del piano in `tmp_path`). *(NFR-3)*
- **RNF-4 (non-regressione suite):** le suite `packages/sertor/tests`, `packages/sertor-flow/tests` e root
  restano verdi (zero nuovi fallimenti). *(NFR-5)*
- **RNF-5 (impatto minimale):** la feature richiede solo nuovi file di test (o estensione di file di test
  esistenti); nessuna modifica al codice Python di produzione. *(NFR-6)*

### Key Entities
- **Wiring Copilot rag** — i 6 frammenti hook generati da `render_copilot_hooks()` e uniti in
  `sertor-hooks.json` dal dispatch `_rag_hook_fragment()` (`install_rag.py`): PreToolUse (usage-check),
  SessionEnd ×3 (memory-capture, rag-freshness, version-check), SessionStart ×2 (prompt statici). Oggetto
  della shape-guard di presenza (Gruppo A); non modificato.
- **Shape-guard di presenza (nuova)** — il test che asserisce la presenza per-evento (SessionEnd /
  SessionStart / PreToolUse) nel `sertor-hooks.json` reso dal piano rag Copilot, con anti-pattern.
  Complementa, non sostituisce, `assert_valid_copilot_hook_file`.
- **Blocchi always-on `claude-md-block*.md`** — i tre asset iniettati in ogni host: wiki (52 righe, pkg
  `sertor`), RAG (49, pkg `sertor`), SDLC (64, pkg `sertor-flow`). Oggetto del budget-test (Gruppo B).
- **Budget-test (nuovo)** — il test cross-package che conta le righe dei blocchi noti, applica le soglie
  per-blocco costanti (60/58/70) ed è esaustivo sui file scoperti (no buco silenzioso).
- **Source-level guard rag (nuova, Should)** — il test offline che verifica l'assenza di payload
  `decision`/`reason` su stdout nei tre script rag SessionEnd, strippando i commenti prima della scansione.
- **Guardie esistenti** — `test_schema_copilot_hooks.py`, `test_assets_copilot_parity.py`,
  `test_hooks_script_copilot.py`, `test_assets_sync.py`: restano verdi e invariate (additività).

## Success Criteria *(mandatory)*
- **CS-1 (event-presence guard):** rimuovendo una delle 6 funzioni-frammento Copilot da `install_rag.py`,
  almeno un nuovo test fallisce e **nomina** l'evento mancante (`SessionEnd`/`SessionStart`/`PreToolUse`) —
  verificabile col test anti-pattern incluso. *(FR-001/002/003, US1)*
- **CS-2 (budget guard):** portando un `claude-md-block*.md` sopra la sua soglia, il budget-test fallisce
  riportando file + conteggio + soglia; un quarto blocco non registrato fa fallire il test — verificabile
  con fixture sintetica. *(FR-005/006/007/008, US2/US3)*
- **CS-3 (difetto storico FEAT-049 coperto):** reintrodurre il wiring hook JSON in formato Claude
  (annidato, `shell`/`timeout`) fa già fallire `test_schema_copilot_hooks.py`; la presenza-guard (CS-1)
  resta indipendente dalla schema-guard, non la sostituisce. *(FR-004, US4)*
- **CS-4 (non-regressione suite):** le suite esistenti rimangono verdi (zero nuovi fallimenti) — `uv run
  pytest` su `packages/sertor/tests`, `packages/sertor-flow/tests`, root. *(FR-013, US6)*
- **CS-5 (offline-safe):** tutti i nuovi assert critici (schema/presenza/budget) girano offline — no rete,
  no `uv` subprocess, no `pwsh`. *(FR-012, US6)*

## Assumptions
- **A-001 — Soglie differenziate (DA-1):** le righe attuali verificate sono wiki **52** · RAG **49** · SDLC
  **64**; le soglie fissate (60/58/70) danno 8/9/6 righe di headroom **e** restano sotto i valori
  pre-FEAT-021 (wiki 71, RAG 72) — così la riduzione di FEAT-021 non può erodersi. Un aumento futuro
  richiede una modifica deliberata della costante (FR-008). *(DA-1)*
- **A-002 — Governance senza hook JSON:** `install_governance.py` (`sertor-flow`) non genera hook JSON per
  Copilot (nessuna chiamata a `render_copilot_hooks`/`HookEntrySpec`) → nessun gap di shape-guard su
  quell'asse. Se governance aggiungesse hook in futuro, il Gruppo A va esteso. *(Edge Case)*
- **A-003 — 6 frammenti rag stabili:** il numero di funzioni-frammento Copilot in `install_rag.py` è 6; se
  cambiasse, i test del Gruppo A (lista eventi attesa) richiedono aggiornamento — reso visibile dal commento
  della lista, pattern `_RAG_HOOKS`. *(Edge Case, R-1 requirements)*
- **A-004 — Conteggio righe consistente:** la guardia budget usa un conteggio consistente (es.
  `splitlines()`) per evitare falsi-positivi da trailing newline; l'headroom di 6-9 righe assorbe differenze
  di ±1. *(Edge Case, R-4 requirements)*
- **A-005 — DA-2 confermata SHOULD:** la source-level guard `.ps1` (Gruppo C) è inclusa come SHOULD per
  chiudere un rischio storico a costo basso; non è bloccante per i Must (Gruppi A e B). *(DA-2)*
- **A-006 — Accesso asset offline:** i test del Gruppo B leggono i blocchi via
  `sertor_installer.resources.read_asset_text` (pkg `sertor`) e l'equivalente di `sertor_install_kit` con
  namespace `sertor_flow` (pkg `sertor-flow`), già usati nei test di parità esistenti. *(FR-012)*

### Fuori ambito (dichiarato)
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle/porta/adapter/engine — la feature è additiva e
  host-facing-testing, zero codice di runtime del core (Principio XI).
- **Codice runtime** (`install_rag.py`, `install_governance.py`, `surfaces.py`, hook `.ps1`): invariato —
  nessun cambiamento di comportamento dell'installer/generazione.
- **Estensione della parity guard (a)–(d) ai contenuti dei `.ps1`/`.json`** (es. nessun percorso `.claude/`
  nel codice degli script): fuori ambito — il beneficio è marginale e gli script non sono body LLM-facing;
  qui si asserisce **shape/presenza** del wiring, non invarianti di contenuto sul codice degli script.
- **Esecuzione `pwsh` reale dei rag hook** per verificarne l'output: fuori ambito (duplicativo, non
  offline-safe); restano i test pwsh-dipendenti esistenti (`test_hooks_script_copilot.py`).
- **Superfici `.vscode/` e target `copilot` (VS Code):** rimosse in FEAT-012, non supportate.
- **Sincronizzazione `assets/rag/**` ↔ `.claude/`** (buco noto): fuori ambito qui.
- **Riconciliazione fork IT eval-skill** → **FEAT-025**.
- **Guard automatico che aggiorna la soglia budget** senza intervento del manutentore: escluso (renderebbe
  la guardia inefficace come freno al bloat).
- **Il *come* di dettaglio** (file dedicato vs estensione di un test esistente; collocazione del budget-test
  root vs package): fase di **design/plan**.

> **Tracciamento dello scope.** L'unico rinvio reale — riconciliazione fork IT eval-skill — è già **promosso
> a casa durevole**: **FEAT-025** nel backlog d'epica. Nessun rinvio reale resta sepolto in `specs/`. La
> feature è *done* quando: la shape-guard di presenza Copilot è verde e diventa rossa rimuovendo un
> frammento; il budget-test è verde e diventa rosso sopra-soglia / con un blocco non registrato; lo
> schema-test resta indipendente e verde; (Should) la source-level guard rag è verde; zero nuovi fallimenti
> di suite; tutto offline-safe.

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Collocazione della shape-guard di presenza (Gruppo A):** file dedicato (es.
  `test_copilot_hook_presence.py`) vs estensione di `test_schema_copilot_hooks.py`. Raccomandazione
  requirements: file separato (schema ≠ presenza). La direzione (presenza per-evento, complementare allo
  schema) è fissata; la collocazione è plan. *(FR-001..004)*
- **DA-D-2 — Collocazione del budget-test (Gruppo B):** root `tests/unit/` (come `test_assets_sync.py`,
  accesso cross-package) vs package `sertor` con import lazy di `sertor_flow` (come
  `test_assets_copilot_parity.py`). Entrambe valide; la scelta è di plan e non cambia i requisiti.
  *(FR-005..008)*
- **DA-D-3 — Forma della source-level guard (Gruppo C):** estensione di `test_hooks_script_copilot.py`
  (dove vive già `test_no_dual_field_in_pending_check_source`) vs file nuovo; e regex/strcategia di strip
  commenti riusata da `test_assets_hook_cli_invocation.py`. Plan. *(FR-009..011)*
