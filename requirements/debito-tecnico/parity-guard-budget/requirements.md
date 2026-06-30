# Requisiti — Parity guard esteso al wiring Copilot + budget di altitude

<!-- Deriva da: FEAT-024 (epica debito-tecnico) — audit ISSUE-10 del 2026-06-26 -->

## 1. Contesto e problema (perché)

### 1.1 Stato attuale delle guardie di parità e sync

Il progetto ha tre strati di guardie offline per la parità tra assistenti e la fedeltà degli
asset installati:

| Guardia | File | Cosa copre | Cosa esclude |
|---|---|---|---|
| Parity guard (body) | `packages/sertor/tests/test_assets_copilot_parity.py` | Invarianti (a)...(d) su ogni body `.md` reso per Copilot: no `.claude/`, no slash-command, no nomi Claude, closure riferimenti | Script `.ps1` e config/manifest generati `.json`/`.tmpl` — esclusi esplicitamente da `_is_llm_body` (linee 52-58): *"Scripts (.ps1) and generated config/manifest templates (.json/.tmpl) are out of scope"* |
| Schema hook (wiring JSON) | `packages/sertor/tests/test_schema_copilot_hooks.py` | Schema R1..R4 del wiring Copilot: `version:1`, lista piatta, nessun campo Claude-only, `timeoutSec` (non `timeout`), payload-key segue il tipo | **Quali eventi sono presenti**: la funzione `assert_valid_copilot_hook_file` (linee 25-43) valida solo lo schema di ciò che c'è, **non** che SessionEnd/SessionStart/PreToolUse esistano |
| Output shape `.ps1` wiki | `packages/sertor/tests/test_hooks_script_copilot.py` | Output per-evento dei hook wiki (`wiki-pending-check.ps1`, `wiki-session-start.ps1`, `sertor-rag-usage-check.ps1`); guard source-level `test_no_dual_field_in_pending_check_source` (offline) | Hook rag (`rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1`): nessuna source-level shape assertion analoga |
| Sync asset bundlato | `tests/unit/test_assets_sync.py` | `assets/claude/**` ↔ `.claude/` drift | `assets/rag/**` e `assets/sertor_flow/**` — non coperti (buco noto: FEAT-025 per rag-skill) |

### 1.2 Lacuna 1 — Il wiring Copilot non ha una shape-assert di presenza

Il wiring Copilot del piano rag è composto da **6 frammenti** distinti generati via
`render_copilot_hooks()` e uniti in `sertor-hooks.json` dal dispatch
`_rag_hook_fragment()` (`install_rag.py:695-715`):

| Frammento | Evento | Tipo | Script/Prompt |
|---|---|---|---|
| `_copilot_rag_hook_specs()` | PreToolUse | command | `sertor-rag-usage-check.ps1` |
| `_copilot_memory_hook_specs()` | SessionEnd | command | `memory-capture.ps1` |
| `_copilot_freshness_end_specs()` | SessionEnd | command | `rag-freshness.ps1` |
| `_copilot_freshness_start_specs()` | SessionStart | **prompt** | (prompt statico nativo) |
| `_copilot_version_check_end_specs()` | SessionEnd | command | `version-check.ps1` |
| `_copilot_version_check_start_specs()` | SessionStart | **prompt** | (prompt statico nativo) |

Il test `test_real_rag_wiring_is_schema_valid` esegue il piano e legge il file prodotto,
ma `assert_valid_copilot_hook_file` valida solo che ogni entry sia strutturata correttamente.
Se si rimuovesse accidentalmente una delle 6 funzioni-frammento da `install_rag.py`, il
`sertor-hooks.json` risultante passerebbe comunque il test schema, ma mancherebbe un intero
evento — il tipo esatto di **drift silenzioso** descritto in ISSUE-10.

Storia: in FEAT-049 i file hook in `assets/copilot/hooks/` erano in formato Claude
(annidata, `shell`, `timeout`) e venivano scartati silenziosamente dal client Copilot. La
lezione è che il wiring ha già ceduto quando nessun test ne asseriva la presenza e la
correttezza per-evento.

### 1.3 Lacuna 2 — Nessun freno alla crescita dei blocchi always-on

I tre blocchi `claude-md-block*.md` sono iniettati **always-on** in ogni host installatosi
(rispettivamente nel blocco istruzione CLAUDE.md/copilot-instructions di wiki, RAG e SDLC).
Lo stato attuale verificato (dopo FEAT-021):

| Blocco | File canonico | Righe attuali |
|---|---|---|
| Wiki | `packages/sertor/src/sertor_installer/assets/claude-md-block.md` | 52 |
| RAG | `packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md` | ~50 |
| SDLC | `packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md` | ~65 |

Nessun test impone una soglia: ogni futuro contribution può far ricrescere i blocchi senza
che la CI segnali il bloat. FEAT-021 ha ridotto significativamente l'altitude (da 208 a ~167
righe totali), ma senza un guard il risparmio può erodersi silenziosamente.

### 1.4 Forche di scope — raccomandazioni analista

#### DA-1 — Soglia budget (quale numero?)

La soglia è una **guardia di non-regressione**, non un target. Deve essere appena sopra
il valore attuale con margine sufficiente per piccole aggiunte legittime senza permettere
bloat.

Il blocco vincolante è SDLC (~65 righe). Una soglia globale unica di **75 righe** copre:
- SDLC 65 + 10 righe di headroom (15%)
- RAG ~50 + 25 righe di headroom
- Wiki 52 + 23 righe di headroom

**Raccomandazione: soglia per-blocco a 75 righe (tutti e tre).** La soglia per-blocco
distingue i tre asset distinti e non impedisce aggiunte al wiki/RAG (più headroom) mentre
è stretta su SDLC (il più lungo). La soglia è una costante nel test e deve essere aggiornata
esplicitamente quando un'aggiunta legittima la supera: questo è il comportamento voluto
(rende il trade-off visibile e deliberato). Un cap globale (somma) è più difficile da
leggere e nasconde quale blocco è cresciuto.

[DA CHIARIRE — DA-1 — a valle] Se l'utente ritiene 75 troppo largo (vuole vincolare
maggiormente il SDLC) o troppo stretto (vuole più headroom), la soglia è aggiustabile a
design-time senza impatto architetturale. La raccomandazione (75) è il default da cui
partire.

#### DA-2 — Ambito shape-guard (cosa asserire?)

Storia del drift: i `.json` Copilot in formato Claude erano scartati silenziosamente. Il
`test_schema_copilot_hooks.py` già chiude lo schema — la lacuna rimanente è la presenza
degli eventi. La lacuna `.ps1` è meno urgente (i hook rag non hanno branching per-assistente
che produca payload stdout; il buco specifico di `wiki-pending-check.ps1` è già coperto).

**Raccomandazione (DA-2):**
- **In ambito (MUST):** per-event presence assertion nel Copilot hook JSON reso dal piano
  rag: SessionEnd, SessionStart, PreToolUse devono essere presenti come chiavi del campo
  `hooks`. Anti-pattern: rimuovere un frammento → il test fallisce nominando l'evento mancante.
- **In ambito (SHOULD):** guard source-level (offline, no `pwsh`) che i tre script rag
  SessionEnd (`rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1`) non
  contengano righe di codice che emettono un payload `decision`/`reason` su stdout — il
  tipo di output che confonderebbe il client Copilot su un evento di fine sessione.
- **Fuori ambito:** superfici `.vscode/` (solo `copilot-cli` è supportato; VS Code rimosso
  in FEAT-012); esecuzione pwsh dei hook rag (duplicativa, non offline-safe); piano governance
  (`sertor-flow`): non genera hook JSON, quindi nessun gap su questo fronte.

[DA CHIARIRE — DA-2 — a valle] Se a design-time si ritiene che la source-level guard sullo
stdout dei rag `.ps1` sia di valore marginale (i hook non hanno branching per-assistente),
può essere declassata a Could senza impatto sul Must. La raccomandazione è SHOULD: vale come
rete preventiva anche se il rischio attuale è basso.

---

## 2. Obiettivi e criteri di successo

- **CS-1 (event-presence guard)** Se si rimuove una qualsiasi delle 6 funzioni-frammento
  Copilot da `install_rag.py` (es. `_copilot_freshness_end_specs()`), almeno un nuovo test
  fallisce e nomina l'evento mancante (`SessionEnd`/`SessionStart`/`PreToolUse`).
  Verificabile: test negativo (anti-pattern) incluso nel documento di test.

- **CS-2 (budget guard)** Se un `claude-md-block*.md` supera la soglia configurata, il
  test di budget fallisce e riporta: nome del file, conteggio corrente, soglia. Non è
  possibile aggiungere un blocco senza che appaia nel test.
  Verificabile: test con fixture sintetica (file fittizio sopra-soglia → assertion fallisce).

- **CS-3 (reintroduzione difetto storico → rosso)** Reintrodurre il difetto di FEAT-049
  (wiring hook JSON in formato Claude annidata, con `shell`/`timeout` invece di `timeoutSec`)
  causa già un fallimento in `test_schema_copilot_hooks.py`; la presenza-assertion (CS-1)
  deve restare indipendente dalla schema-assertion (non sostituirla né duplicarla).

- **CS-4 (non-regressione suite)** Le suite esistenti rimangono verdi: `packages/sertor/tests`,
  `packages/sertor-flow/tests`, root (`uv run pytest`). Le nuove guardie sono additive.

- **CS-5 (offline-safe)** Tutti i nuovi test girano offline (no rete, no `uv` subprocess,
  no `pwsh` richiesto) per gli assertion critici (schema, presence, budget). I test
  pwsh-dipendenti esistenti rimangono skippabili senza impatto.

---

## 3. Stakeholder e attori

- **Manutentore di Sertor** — ottiene una rete CI che cattura la rimozione accidentale di
  un hook Copilot e la crescita non sorvegliata dei blocchi always-on.
- **CI** — nuovi test nei pacchetti `sertor` e root; green su Windows e Linux.
- **Ospite terzo** — riceve wiring Copilot integro e blocchi compatti, senza che la CI
  del progetto host lo riguardi (la guardia è lato sviluppo Sertor).

---

## 4. Ambito

### In ambito

- **Gruppo A — shape-guard di presenza** nel wiring Copilot: nuovi test nel package
  `packages/sertor/tests/` che asseriscono la presenza per-evento (SessionEnd, SessionStart,
  PreToolUse) nel `sertor-hooks.json` reso dal piano rag per `COPILOT_CLI`; include
  un test anti-pattern (rimozione frammento → fallimento).
- **Gruppo B — budget altitude**: nuovi test (root `tests/unit/` o helper condiviso) che
  leggono i tre `claude-md-block*.md` dai package `sertor` e `sertor-flow` e falliscono se
  una qualsiasi righe-count supera la soglia per-blocco; include anti-pattern e coverage
  esaustiva (qualsiasi nuovo blocco non nella tabella causa fallimento).
- **Gruppo C — source-level guard rag `.ps1`** (SHOULD): asserzione offline che gli script
  rag SessionEnd non emettono un payload Copilot-decision su stdout.
- **Verifica di non-regressione** delle suite esistenti prima di dichiarare la feature completa.
- **Zero modifica di comportamento**: nessuna logica di produzione toccata.

### Fuori ambito

- **`sertor_core`**: zero modifiche (Principio XI).
- **Codice runtime** (`install_rag.py`, `surfaces.py`, hook `.ps1`): invariato.
- **Aggiornamento della soglia budget** a valori diversi da 75: decisione al design-time,
  non è un requisito funzionale.
- **Superfici `.vscode/`** e `copilot` (VS Code): rimosso in FEAT-012, non supportato.
- **Piano governance** (`sertor-flow`): non genera hook JSON, zero gap su questo asse.
- **Test pwsh-dipendenti per i rag hook** (esecuzione reale): fuori ambito, duplicativo.
- **Sincronizzazione `assets/rag/**` ↔ `.claude/`** (buco FEAT-025): fuori ambito qui.
- **Riconciliazione fork IT eval-skill** → FEAT-025.

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Shape-guard della presenza nel Copilot hook JSON

- **REQ-001** When the rag install plan is built and executed for `AssistantId.COPILOT_CLI`,
  the parity guard shall assert that the merged `sertor-hooks.json` contains at least one
  entry under the `SessionEnd` event key.

- **REQ-002** When the rag install plan is built and executed for `AssistantId.COPILOT_CLI`,
  the parity guard shall assert that the merged `sertor-hooks.json` contains at least one
  entry under the `SessionStart` event key.

- **REQ-003** When the rag install plan is built and executed for `AssistantId.COPILOT_CLI`,
  the parity guard shall assert that the merged `sertor-hooks.json` contains at least one
  entry under the `PreToolUse` event key with a non-empty `matcher` field.

- **REQ-004** If any of the required event keys is absent from the hook JSON produced by the
  Copilot rag plan, then the presence-guard shall fail and name the missing event type.

- **REQ-005** The presence-guard shall include at least one anti-pattern test that confirms
  the guard is not vacuous: a simulated plan missing one hook-spec fragment shall trigger
  a failing assertion that names the absent event.

- **REQ-006** The presence-guard tests shall run offline (no network, no `uv` subprocess):
  they shall reuse the same `tmp_path`-based plan-execution pattern established in
  `packages/sertor/tests/test_schema_copilot_hooks.py:test_real_rag_wiring_is_schema_valid`.

- **REQ-007** The presence-guard shall complement, not replace, the existing schema
  validation in `assert_valid_copilot_hook_file`: both schema and presence must hold.

### Gruppo B — Budget altitude dei blocchi `claude-md-block*.md`

- **REQ-008** The system shall include a budget test that, for each known
  `claude-md-block*.md` file across all packages (`sertor` and `sertor-flow`), counts the
  lines of the file and fails if the count exceeds the configured per-block threshold.

- **REQ-009** When a `claude-md-block*.md` line count exceeds the threshold, the budget
  test shall fail with a message naming: the file (package + relative path), the current
  line count, and the configured threshold for that file.

- **REQ-010** The budget test shall cover exhaustively all `claude-md-block*.md` files
  currently known: `claude-md-block.md` (wiki, package `sertor`),
  `rag/claude-md-block-rag-usage.md` (RAG, package `sertor`), and
  `claude-md-block-sdlc.md` (SDLC, package `sertor-flow`).

- **REQ-011** If a fourth `claude-md-block*.md` file is added to either package without a
  corresponding threshold entry in the budget test, then the budget test shall fail,
  naming the unregistered file.

- **REQ-012** The threshold values shall be declared as explicit constants in the test
  source (not computed dynamically from the files at test-time), so that a threshold
  increase is a deliberate, visible code change.

- **REQ-013** The budget test shall include at least one anti-pattern test confirming the
  guard is not vacuous: a synthetic body exceeding the threshold shall trigger a failing
  assertion.

- **REQ-014** The budget test shall run offline (no network, no filesystem outside the
  package assets) and shall not require `pwsh`, `uv`, or any external subprocess.

### Gruppo C — Source-level guard degli script rag SessionEnd (SHOULD)

- **REQ-015** *Where the Copilot source-level guard is implemented,* the system shall
  include an offline assertion that the in-scope rag SessionEnd script sources
  (`rag-freshness.ps1`, `memory-capture.ps1`, `version-check.ps1`) do not contain code
  lines emitting a Copilot `decision`/`reason` JSON payload on stdout: the output channel
  that would be consumed (and likely rejected or misinterpreted) by the Copilot CLI hook
  engine on a `sessionEnd` event.

- **REQ-016** *Where the Copilot source-level guard is implemented,* the guard shall strip
  block comments (`<# … #>`) and whole-line `#` comments from the script source before
  scanning, so that prose mentioning the forbidden pattern is not mistaken for code — the
  same pattern used in `test_assets_hook_cli_invocation.py`.

- **REQ-017** *Where the Copilot source-level guard is implemented,* it shall include at
  least one anti-pattern test confirming the guard catches an artificial snippet that emits
  a `decision`/`reason` construct on stdout in the foreground code path.

---

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI)** Zero modifiche a `sertor_core`: la feature tocca esclusivamente
  file di test e nessun codice runtime.

- **NFR-2 (Additività)** Le nuove guardie non modificano, non sostituiscono e non
  richiamano in modo diverso le guardie esistenti (`test_schema_copilot_hooks.py`,
  `test_assets_copilot_parity.py`, `test_hooks_script_copilot.py`, `test_assets_sync.py`).

- **NFR-3 (Offline-safe)** I nuovi test dei Gruppi A e B non richiedono rete, `pwsh`,
  o processi figli (solo lettura di asset via `iter_asset_dir`/`read_asset_text` e
  costruzione del piano in `tmp_path`).

- **NFR-4 (Non-regressione comportamentale)** Il comportamento dell'installer per entrambi
  gli assistenti (`claude`, `copilot-cli`) è byte-identico prima e dopo l'aggiunta delle
  guardie.

- **NFR-5 (Non-regressione suite)** Le suite `packages/sertor/tests`,
  `packages/sertor-flow/tests` e root rimangono verdi (zero nuovi fallimenti).

- **NFR-6 (Impatto minimale)** La feature richiede solo nuovi file di test (o estensione
  di file esistenti); nessuna modifica al codice Python di produzione.

---

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (Principio XI):** nessuna modifica al codice di `sertor_core`.
- **Vincolo (non-regressione schema):** i nuovi test del Gruppo A devono complementare
  `assert_valid_copilot_hook_file` senza duplicarlo o renderlo ridondante.
- **Dipendenza (test_schema_copilot_hooks.py):** il pattern di esecuzione del piano in
  `tmp_path` già collaudato in quel file è il riferimento da riusare per il Gruppo A
  (`packages/sertor/tests/test_schema_copilot_hooks.py`, fixture `make_runner`).
- **Dipendenza (iter_asset_dir / read_asset_text):** i test del Gruppo B accedono agli
  asset via `sertor_installer.resources.read_asset_text` (package `sertor`) e
  `sertor_install_kit.read_asset_text` con namespace `sertor_flow` (package `sertor-flow`),
  già usati nei test di parità esistenti (`test_assets_copilot_parity.py:100-107`).
- **Assunzione (soglia 75):** le righe attuali dei tre blocchi sono verificate ≤ 65
  (SDLC, il più lungo); la soglia 75 fornisce headroom ≥ 10 righe per il blocco più lungo
  e ≥ 23 righe per i più corti. Se i blocchi crescono legittimamente oltre 75, la soglia va
  aggiornata esplicitamente come decisione cosciente (REQ-012).
- **Assunzione (governance senza hook JSON):** `sertor-flow` non genera hook JSON per
  Copilot — verificato esaminando il codice di `install_governance.py` (nessuna chiamata
  a `render_copilot_hooks` o `HookEntrySpec`). Se in futuro governance aggiungesse hook,
  il Gruppo A va esteso.
- **Assunzione (6 frammenti rag):** il numero di funzioni-frammento in `install_rag.py`
  è stabile (6); se ne venissero aggiunte/rimosse, i test del Gruppo A richiedono
  aggiornamento.

---

## 8. Rischi

- **R-1 (test fragile alla crescita dei frammenti)** Se vengono aggiunte nuove
  funzioni-frammento Copilot in `install_rag.py`, i test di presenza del Gruppo A non
  catturano automaticamente il nuovo frammento (solo gli eventi dichiarati). Mitigazione:
  commentare nel test la lista dei frammenti attesi e aggiornarla quando cambia (come
  fa `test_assets_hook_breadcrumb.py:32-33` con `_RAG_HOOKS`).

- **R-2 (soglia obsoleta per futura feature)** Una feature che aggiunge contenuto a un
  blocco supera la soglia 75 e rompe la CI. Mitigazione: il test (REQ-009) nomina il file
  e la soglia → il contributor sa esattamente cosa aggiornare; l'aggiornamento è una
  modifica deliberata, non un workaround.

- **R-3 (cobertura Gruppo C limitata)** La source-level guard sui rag `.ps1` (REQ-015)
  verifica solo l'assenza di `decision`/`reason` su stdout, non l'intero contratto
  di output. Un cambiamento diverso (es. scrittura di testo arbitrario su stdout) potrebbe
  sfuggire. Mitigazione: la guardia è un presidio preventivo — per la verifica completa
  di comportamento restano i test pwsh-dipendenti (`test_hooks_script_copilot.py`).

- **R-4 (falso-positivo nel guard budget se trailing newlines)** I conteggi di righe
  possono differire di ±1 a seconda del tool di lettura (trailing newline). Mitigazione:
  usare `len(text.splitlines())` per un conteggio consistente (esclude la newline finale);
  i test di non-regressione con i file reali lo verificano alla prima esecuzione.

---

## 9. Prioritizzazione (MoSCoW)

**Must:**
- REQ-001, REQ-002, REQ-003 (presence-guard eventi fondamentali)
- REQ-004, REQ-005 (anti-pattern per non-vacuità)
- REQ-006, REQ-007 (offline-safe, non-sostituzione schema)
- REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014 (budget test completo)

**Should:**
- REQ-015, REQ-016, REQ-017 (source-level guard rag `.ps1` stdout)

**Won't (qui):**
- Guard automatico che aggiorna la soglia budget senza intervento del manutentore
  (renderebbe la guardia non-efficace come freno al bloat).
- Esecuzione pwsh reale dei rag hook per la verifica dell'output (fuori ambito).
- Estensione della parity guard (Gruppo a-d) ai file `.ps1`/`.json` con invarianti
  di contenuto (es. nessun percorso `.claude/` nel codice degli script) — fuori ambito,
  il beneficio è marginale e i `.ps1` non sono body LLM-facing.
- Riconciliazione fork IT eval-skill → FEAT-025.

---

## 10. Domande aperte

Le due forche risolvibili al design-time (non bloccanti per i requisiti):

### DA-1 — Soglia budget per blocco

**Raccomandazione analista:** soglia per-blocco di **75 righe** per tutti e tre i blocchi.
Motivazione: SDLC (~65 righe, il blocco più lungo) riceve 10 righe di headroom (~15%),
sufficiente per piccole integrazioni senza permettere l'erosione silenziosa ottenuta da
FEAT-021. La soglia è un segnale di allerta, non un hard cap senza eccezioni: aggiornarla
esplicitamente è il comportamento inteso (REQ-012).

**[DA CHIARIRE — DA-1]** L'utente preferisce una soglia diversa? Opzioni:
  - **(a) 75 per tutti** (raccomandato): semplice da comunicare, SDLC vincolante.
  - **(b) Per-blocco differenziata** (es. wiki 65 · RAG 65 · SDLC 75): più precisa,
    più manutenzione nel test.
  - **(c) 70 per tutti**: più stretto su SDLC (5 righe headroom), più proibitivo su
    wiki/RAG (18/20 righe headroom comunque ampie).

### DA-2 — Ambito della source-level guard `.ps1`

**Raccomandazione analista:** SHOULD (REQ-015..017). I rag hook non hanno branching
per-assistente e non producono payload `decision`/`reason` — il rischio è basso ma la
guardia è economica (lettura sorgente + regex). Se si ritiene il valore marginale, i
REQ-015..017 possono essere declassati a Could senza impatto sul Must.

**[DA CHIARIRE — DA-2]** L'utente desidera includere la source-level guard (SHOULD) o
limitarsi al Must (Gruppi A e B)?

### Domande di design/plan (non bloccanti per i requisiti)

- **[DA CHIARIRE in design/plan]** I nuovi test del Gruppo A vivono in un file dedicato
  (es. `test_copilot_hook_presence.py`) o come estensione di `test_schema_copilot_hooks.py`?
  Raccomandazione: file separato per chiarire la responsabilità (schema ≠ presenza), ma la
  scelta è di design.
- **[DA CHIARIRE in design/plan]** Il budget test del Gruppo B vive nel root `tests/unit/`
  (come `test_assets_sync.py`, accesso cross-package) o nel package `sertor` con import
  lazy di `sertor_flow` (come già fa `test_assets_copilot_parity.py:93-97`)? Entrambe le
  opzioni sono valide; la scelta è di design e non cambia i requisiti.
