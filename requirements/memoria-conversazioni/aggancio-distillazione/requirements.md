# Requisiti — Aggancio della distillazione all'archivio episodico
<!-- Deriva da: FEAT-003 (epica memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'epica «Memoria delle conversazioni» nasce per chiudere un **loop lossy**: oggi la conoscenza
prodotta in conversazione viene **distillata** in pagine wiki (operazione `distill`,
`.claude/skills/wiki-author/ops/distill.md`), ma **il grezzo si butta**. Con l'MVP della memoria
(FEAT-001 cattura + FEAT-002 ricerca) il grezzo finalmente **si conserva** in un archivio locale
(`<index_dir>/memory.sqlite`), ma la distillazione **non sa raggiungerlo**.

Stato reale del codice (ancoraggio):
- **Archivio (FEAT-001):** `MemoryArchive` (`src/sertor_core/adapters/memory/archive.py`) conserva
  sessioni+turni post-scrub, idempotente. Espone già `get(session_key) → ArchivedSession | None`
  (ricompone la sessione **intera**, turni in ordine) ed `exists()`. **Non** espone un elenco delle
  sessioni archiviate.
- **Ricerca (FEAT-002):** `EpisodicSearch` (`src/sertor_core/services/episodic_search.py`)
  restituisce **solo snippet per-turno troncati** via FTS5 — utile per «ne abbiamo già parlato?», ma
  **non** una conversazione intera da distillare.
- **Distill:** è un'operazione di **giudizio del flusso principale** (non un comando, non un hook).
  Ha tre ingressi; il terzo («from conversation») oggi **pretende un brief condensato a mano** e
  vieta esplicitamente il transcript grezzo (*«Never the raw transcript: the caller condenses
  first»*). È una **rete di sicurezza teorica**: priva di fonte, di fatto non operativa.

Il problema da risolvere: dare alla modalità «from conversation» di `distill` una **fonte reale e
recuperabile** — una sessione archiviata, per intero — **senza** alterare il distill quotidiano e
**senza** introdurre costi di token ricorrenti.

## 2. Obiettivi e criteri di successo

- **CS-1 (recupero intero):** data una sessione presente nell'archivio, il sistema ne restituisce il
  **transcript completo** (tutti i turni, in ordine, con ruolo e timestamp) — non snippet.
- **CS-2 (scelta della sessione):** l'utente/agente può **elencare** le sessioni archiviate più
  recenti (con chiave, data, #turni) per scegliere quale recuperare, senza leggere il file SQLite a
  mano.
- **CS-3 (rete di sicurezza operativa):** un'operazione `distill` in modalità «from conversation»
  può **attingere** a una sessione archiviata invece di richiedere un brief riassunto a mano
  (verificabile: `distill.md` documenta il percorso archivio→contesto→condensazione→distill).
- **CS-4 (nessun costo ricorrente):** l'aggancio **non** aggiunge alcuna invocazione automatica di
  distillazione né alcun consumo di token per-turno/per-sessione. Verificabile: il rituale di step e
  l'hook `SessionEnd` restano invariati; nessun nuovo trigger automatico.
- **CS-5 (additivo/non-breaking):** core, CLI e hook esistenti restano invariati nel comportamento;
  con `SERTOR_MEMORY` spento, nulla cambia rispetto a oggi.
- **CS-6 (host-agnostico):** recupero ed elenco operano su qualunque ospite senza modifiche al corpo
  (`session_key`/`project_id` restano dati opachi, Principio X).

## 3. Stakeholder e attori

- **Owner/maintainer (tu):** invoca esplicitamente il recupero quando si accorge che una decisione
  passata non è mai finita nel wiki; sceglie *quale* sessione.
- **Agente LLM (flusso principale):** consumatore — porta in contesto la sessione recuperata, la
  condensa e la distilla (giudizio). È anche l'unico a *decidere* quando serve.
- **Il sistema-wiki (`distill`):** consumatore della fonte grezza recuperata.

## 4. Ambito

### In ambito
- **A — Recupero nel core:** elenco delle sessioni archiviate (recenti) sull'archivio locale; il
  recupero della sessione intera per chiave **esiste già** (`MemoryArchive.get`) e viene **esposto**
  ai consumatori sottili (factory `build_*`).
- **B — Superficie thin-consumer:** comandi `sertor-rag memory show <session>` (transcript intero,
  umano + `--json`) e `sertor-rag memory list` (sessioni recenti), nello stile dei comandi
  `memory search`/`memory archive` (feature 035).
- **C — Wiring lato distillazione (giudizio):** aggiornare `distill.md` (e l'asset installabile
  `packages/sertor/src/sertor_installer/assets/claude-md-block.md`, se contiene la procedura) perché
  la modalità «from conversation» attinga all'archivio via la nuova superficie.

### Fuori ambito
- **Trigger automatico** di distillazione (a fine sessione, a fine turno, su tutto l'archivio):
  esplicitamente escluso (vedi REQ-013, vincolo cardine).
- **Condensazione automatica** del transcript (uno step che riassume al posto del flusso
  principale): la condensazione resta giudizio del flusso principale (vedi DA-1).
- **Ricerca semantica** sull'archivio (è FEAT-004, Should, opt-in).
- **Distillazione cross-progetto / second-brain** (è il [[second-brain-cross-progetto]]).
- **Retention/cancellazione** del contenuto (è FEAT-006).
- **Modifica del distill quotidiano (step-driven)**: resta invariato e non tocca l'archivio.
- **Cattura multi-assistente** (FEAT-008).

## 5. Requisiti funzionali (EARS)

### Gruppo A — Recupero nel core (lettura sull'archivio)

- **REQ-001 (Event-driven):** *When a full archived session is requested by its key, the system shall
  return the complete transcript — all turns in `turn_index` order, each with role, timestamp and
  text — not a truncated snippet.*
- **REQ-002 (Event-driven):** *When a listing of archived sessions is requested, the system shall
  return the most recent sessions with, for each, the session key, capture timestamp and turn count,
  ordered most-recent-first and bounded by a configurable limit.*
- **REQ-003 (Unwanted):** *If the requested session key is not present in the archive, then the system
  shall return an explicit "not found" outcome (not an error and not a silent empty value
  indistinguishable from an empty session).*
- **REQ-004 (Unwanted):** *If the archive file is missing, empty or unreadable, then the system shall
  degrade to an explicit empty result plus a warning, never a crash (consistent with FEAT-001/002
  non-fatal policy).*
- **REQ-005 (Ubiquitous):** *The session retrieval and listing shall be exposed to thin consumers
  through a composition-root factory (`build_*`), without a new domain port (concrete component,
  single-consumer profile — same as `MemoryArchive`/`EpisodicSearch`).*

### Gruppo B — Superficie thin-consumer (CLI)

- **REQ-006 (Event-driven):** *When the operator runs the "show session" command with a session key,
  the system shall print the full transcript in a human-readable form and, with a `--json` flag, as
  structured JSON — mirroring the output style of `memory search`/`memory archive` (feature 035).*
- **REQ-007 (Event-driven):** *When the operator runs the "list sessions" command, the system shall
  print the recent archived sessions (key, date, turn count), honouring a limit flag, in human and
  `--json` forms.*
- **REQ-008 (Unwanted):** *If conversation memory is not enabled (`SERTOR_MEMORY` off), then the
  command shall fail with an actionable error naming the switch and exit non-zero — identical
  gating to `memory search`/`memory archive`.*
- **REQ-009 (Unwanted):** *If the requested session key is not found, then the "show" command shall
  print an actionable message and exit non-zero (distinct from the success-with-empty case).*

### Gruppo C — Wiring lato distillazione (giudizio, documentazione)

- **REQ-010 (Event-driven):** *When `distill` is invoked in "from conversation" mode, its procedure
  (`distill.md`) shall direct the main flow to retrieve the target archived session via the new
  surface, condense it, then distil — replacing the prior requirement of a hand-written brief.*
- **REQ-011 (Optional feature):** *Where the distillation procedure is shipped to hosts as an
  installable asset (`claude-md-block.md` or equivalent), the same "draw from the archive" guidance
  shall be reflected there, keeping the asset and the in-repo procedure consistent (host-agnostic).*

### Vincoli trasversali

- **REQ-012 (Ubiquitous):** *The feature shall be purely additive: existing core, CLI and hook
  behaviour shall remain unchanged, and with `SERTOR_MEMORY` off the system shall behave exactly as
  before.*
- **REQ-013 (Unwanted — VINCOLO CARDINE):** *If distillation from the archive is triggered, then it
  shall only ever happen by an explicit, human/agent-initiated invocation on a targeted session; the
  system shall never automatically distil whole conversations, the whole archive, or distil on a
  per-turn / per-session schedule.*
- **REQ-014 (Ubiquitous):** *The query path (retrieval and listing) shall stay entirely local — no
  network, no embeddings, no LLM — preserving the privacy-by-design property of FEAT-002 (content
  already scrubbed at archive time by FEAT-001).*

## 6. Requisiti non funzionali

- **RNF-1 (costo / disaccoppiamento):** la cattura (economica: I/O + regex, zero LLM) e la
  distillazione (costosa: giudizio LLM) restano **disaccoppiate**. L'aggancio non introduce costi di
  token ricorrenti (corollario di REQ-013). L'archivio è memoria di **backup** (cold storage), non
  RAM (il contesto attivo) né HD (il wiki sempre montato).
- **RNF-2 (privacy):** nessun contenuto lascia la macchina nel percorso di recupero/elenco; il
  contenuto è già scrubbato a monte; eventuali eventi di osservabilità non registrano testo in chiaro
  (coerente con `episodic_search` che hasha la query).
- **RNF-3 (prestazioni):** recupero ed elenco di una sessione sono operazioni locali SQLite a bassa
  latenza (indici già presenti su `sessions`/`turns`); nessun budget stringente oltre «percepibilmente
  immediato» su archivi tipici (migliaia di turni).
- **RNF-4 (host-agnostico, Principio X):** `session_key`/`project_id`/`adapter_kind` trattati come
  dati opachi; nessun branch sull'identità dell'assistente.
- **RNF-5 (degradazione non-fatale):** ogni guasto di lettura → stato vuoto esplicito + warning, mai
  eccezione (coerenza con la policy di FEAT-001/002).
- **RNF-6 (leggibilità/osservabilità):** l'output `show`/`list` deve essere scansionabile dall'umano e
  parseable in `--json`, coerente con `format_*` di `cli/output.py`.

## 7. Vincoli, assunzioni e dipendenze

- **Dipendenza:** FEAT-001 (archivio, `MemoryArchive.get` già presente) e FEAT-002 (precedente per
  pattern, non funzionalmente necessaria) — entrambe su master.
- **Dipendenza:** la superficie CLI `memory` (feature 035) come gruppo di sotto-comandi su cui
  innestare `show`/`list`.
- **Assunzione:** la condensazione del transcript recuperato è giudizio del flusso principale (Opus),
  non un componente di codice (vedi DA-1). Coerente con «distill è giudizio».
- **Assunzione:** un elenco delle sessioni archiviate è sufficiente per «scegliere quale recuperare»;
  per il filtraggio fine resta `memory search` (FEAT-002).
- **Vincolo costituzionale:** thin consumer (I), niente nuova porta senza secondo consumatore (II/
  YAGNI), local-first + host-agnostico (II/X), additivo/non-breaking, non-bloccante/non-fatale.

## 8. Rischi

- **R-1 — Riapertura del costo token:** se mal progettata, la feature potrebbe indurre a distillare
  troppo/automaticamente. Mitigazione: REQ-013 (vincolo cardine) + RNF-1; nessun trigger automatico.
- **R-2 — Deriva archivio↔wiki:** trasformare la modalità «from conversation» in un secondo canale
  di scrittura massiva nel wiki. Mitigazione: resta **rete di sicurezza** mirata; il distill
  step-driven resta la via primaria.
- **R-3 — Volume del transcript in contesto:** una sessione molto lunga recuperata per intero può
  pesare sul contesto. Mitigazione: la scelta è mirata (una sessione), e la condensazione è giudizio;
  `memory search` resta per restringere prima.
- **R-4 — Confine grezzo↔condensato ambiguo:** se non chiarito, l'implementazione potrebbe aggiungere
  uno step di condensazione automatica non voluto (vedi DA-1).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-003, REQ-004, REQ-005 (recupero core esposto, robusto) · REQ-006, REQ-008,
  REQ-009 (comando `show` gated e robusto) · REQ-010 (wiring `distill.md`) · REQ-012, REQ-013, REQ-014
  (additivo, vincolo cardine, privacy/local).
- **Should:** REQ-002, REQ-007 (`list` sessioni — forte aiuto alla scelta, ma `show` da solo è già
  utile se si conosce la chiave) · REQ-011 (asset installabile allineato).
- **Could:** tool MCP `memory_show`/`memory_list` (parità con la superficie MCP) — fuori MVP della
  feature, valutabile dopo.
- **Won't (in questa feature):** condensazione automatica, trigger automatici, ricerca semantica,
  retention, multi-assistente.

## 10. Domande aperte

- **DA-1 — Confine grezzo↔condensato (decisione di design principale):** il recupero porta i **turni
  grezzi** in contesto e il flusso principale (Opus) **condensa e distilla** (opzione **(a)**,
  raccomandata: coerente con «distill è giudizio», nessun nuovo componente di codice), **oppure** si
  introduce uno step di **condensazione** (riassunto) prima della distillazione (opzione (b): più
  codice, rischio di duplicare il giudizio). *Raccomandazione: (a).* Da confermare in fase di
  clarify/plan.
- **DA-2 — `list` nell'MVP o rinviato:** `memory show <key>` da solo richiede di conoscere la chiave;
  `memory list` la rende scopribile. Should: includerlo nell'MVP della feature o rinviarlo? *(propendo
  per includerlo: il costo è minimo e senza elenco la `show` è scomoda.)*
- **DA-3 — Granularità del recupero:** sessione intera (default, allineato alla granularità ibrida di
  FEAT-001) è sufficiente, o serve un recupero a livello di **thread/finestra di turni**? *(propendo
  per sessione intera nell'MVP; il thread è raffinamento successivo.)*
- **DA-4 — Tool MCP (Could):** esporre `show`/`list` anche come tool MCP per parità con la superficie
  agentica, o lasciare solo CLI? *(rinviabile; la CLI copre il caso d'uso del flusso principale.)*
