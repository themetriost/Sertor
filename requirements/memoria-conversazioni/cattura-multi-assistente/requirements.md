# Requisiti — Cattura multi-assistente (GitHub Copilot CLI)
<!-- Deriva da: FEAT-008 (epica: memoria-conversazioni) -->

## 1. Contesto e problema (perché)

L'MVP della memoria conversazioni (FEAT-001/002/035/003) e la sua ricerca semantica (FEAT-004) sono
**host-agnostici** — tranne **un** punto: la **cattura** dei transcript, che è host-specifica e oggi
ha un solo adapter, **`claude-code`** (`src/sertor_core/adapters/capture/claude_code.py`), che legge i
JSONL di sessione di Claude Code.

La distribuzione multi-assistente (FEAT-009, consegnata) ha già **depositato l'hook `SessionEnd` su
ospiti Copilot** tramite l'installer — ma quell'hook è **inerte**: scatta a fine sessione e invoca
`sertor-rag memory archive`, che però seleziona l'unico adapter `claude-code`, incapace di leggere i
transcript di Copilot. Risultato: **su Copilot la memoria non cattura nulla** (il tubo è posato, manca
la sorgente).

Questa feature aggiunge l'**adapter di cattura per GitHub Copilot CLI**, dietro la porta esistente
`TranscriptCaptureAdapter` (8ª porta). Una volta presente, l'intero tier — archivio, ricerca full-text
(FEAT-002), ricerca semantica (FEAT-004), distillazione (FEAT-003) — diventa operativo anche su
Copilot **senza modifiche** (è già host-agnostico nel corpo). È il rischio **R-1 dell'epica** (cattura
host-specifica) risolto per il secondo assistente.

**Ricognizione (verificata su doc ufficiale GitHub + filesystem locale, 2026-06-22):** Copilot CLI
conserva ogni sessione in `~/.copilot/session-state/<session-uuid>/`, con un **`events.jsonl`** (stream
di eventi JSONL: prompt, risposte, tool, file) come transcript, più un `session.db` (SQLite
per-sessione), `workspace.yaml`, `vscode.metadata.json` (`origin`/`created`/`modified`); l'indice
globale è `~/.copilot/session-store.db`. *(Sorgenti: docs.github.com/en/copilot/.../copilot-cli/chronicle.)*
Due differenze rilevanti da Claude: **(a)** le cartelle di sessione sono **UUID**, non path-encoded →
l'associazione al progetto va ricavata da *dentro* la sessione; **(b)** Copilot **sincronizza di
default le sessioni sul cloud GitHub** (comportamento suo, a monte, fuori dal controllo di Sertor, che
legge il file **locale**).

## 2. Obiettivi e criteri di successo

- **CM-CS-1 (cattura su Copilot):** con la memoria attiva e l'adapter Copilot selezionato, dopo **N**
  sessioni Copilot le relative conversazioni sono **recuperabili** dall'archivio locale (verificabile:
  #sessioni Copilot archiviate = #sessioni catturate), come già accade per Claude Code.
- **CM-CS-2 (parità di tier):** una conversazione catturata da Copilot è interrogabile via ricerca
  full-text **e** semantica e disponibile alla distillazione **alla pari** di una catturata da Claude,
  **senza** modifiche ad archivio/ricerca/distillazione.
- **CM-CS-3 (host-specificità confinata):** l'unico componente che conosce Copilot (percorsi, formato
  eventi) è il nuovo adapter dietro la porta; il resto del nucleo resta invariato (Principio X).
- **CM-CS-4 (privacy & local-first):** con la cattura disattivata non viene catturato nulla; attiva,
  l'adapter legge **solo** i file locali di Copilot e il contenuto passa per lo scrub esistente; Sertor
  non contatta il cloud-sync di Copilot.
- **CM-CS-5 (idempotenza):** archiviare due volte la stessa sessione Copilot non crea duplicati.
- **CM-CS-6 (robustezza non-fatale):** sorgente assente / evento malformato / formato inatteso non
  generano un errore fatale; la cattura degrada con warning e prosegue.
- **CM-CS-7 (hook reso vivo):** su un ospite Copilot con la memoria configurata, l'hook `SessionEnd`
  già depositato (FEAT-009) cattura effettivamente le sessioni (smette di essere inerte).

## 3. Stakeholder e attori

- **Agente LLM su Copilot CLI (attore primario):** sorgente delle conversazioni e consumatore della
  memoria episodica/semantica.
- **Owner/maintainer (utente):** usa Sertor su un progetto guidato da Copilot e vuole la stessa
  memoria che ha con Claude.
- **Il sistema-wiki:** la distillazione attinge anche alle sessioni Copilot.
- **GitHub Copilot CLI (host):** produce e conserva i transcript di sessione (formato proprio).

## 4. Ambito

### In ambito
- **Nuovo adapter di cattura per Copilot CLI** dietro la porta `TranscriptCaptureAdapter`, selezionabile
  via `SERTOR_MEMORY_ADAPTER` (accanto a `claude-code`).
- **Discovery** delle sessioni Copilot dal session-store locale (`~/.copilot/session-state/<uuid>/`),
  con **percorso sorgente sovrascrivibile** via configurazione (host-agnostico/testabile, come
  l'override del projects-dir di Claude).
- **Estrazione dei turni** (prompt utente / risposte assistente) dallo stream di eventi della sessione,
  **best-effort e non-fatale** (righe/eventi non validi → skip + warning).
- **Associazione sessione↔progetto** ricavata dalla metadata interna della sessione (le cartelle sono
  UUID, non path-encoded).
- **Riuso integrale del tier**: archivio, full-text, semantica, distillazione operano sui transcript
  Copilot **senza modifiche** (l'host-specificità sta solo nell'adapter).
- **Attivazione dell'hook** `SessionEnd` già depositato su Copilot (la cattura diventa effettiva).
- Idempotenza, scrub dei segreti (a monte), privacy-by-default, local-first — **ereditati** dal tier.

### Fuori ambito
- **Modifiche ad archivio / ricerca full-text / ricerca semantica / distillazione** (host-agnostici per
  costruzione; questa feature li *alimenta*, non li tocca).
- **Distribuzione dell'adapter via installer**: l'hook e le manopole memoria su Copilot sono **già**
  distribuiti (FEAT-009); resta da cablare nel template `.env` il valore `SERTOR_MEMORY_ADAPTER=copilot-cli`
  → **debito di completamento** (vedi §10), non risolto qui.
- **Altri assistenti** (Codex, ecc.): fuori da questa feature (estendibile in futuro con lo stesso
  pattern; qui il focus è Copilot CLI).
- **Interazione col cloud-sync di Copilot** (lettura/scrittura della copia su GitHub): Sertor legge
  **solo** il locale; il sync è di Copilot.
- **Definizione del *come*** (schema eventi → turni, fonte `events.jsonl` vs `session.db`, criterio di
  associazione al progetto, gestione sede legacy, nome esatto del valore adapter): fase di **design**
  (§10).

## 5. Requisiti funzionali (EARS)

### 5.1 Selezione dell'adapter
**REQ-001 (Optional feature):** *Where `SERTOR_MEMORY_ADAPTER` selects the Copilot CLI adapter, the
system shall use it as the transcript capture source, on equal footing with the existing `claude-code`
selection.*

**REQ-002 (Unwanted behaviour):** *If the configured capture adapter value is not recognised, then the
system shall raise an actionable configuration error naming the allowed values (today's behaviour,
preserved).*

### 5.2 Discovery delle sessioni Copilot
**REQ-003 (Ubiquitous):** *The Copilot adapter shall discover the captured sessions from Copilot CLI's
local per-session store (the per-session directories under the user's Copilot session-state location).*

**REQ-004 (Optional feature):** *Where the user overrides the Copilot session-state location via
configuration, the adapter shall read from the overridden path (host-agnostic and testable, mirroring
the Claude projects-dir override).*

**REQ-005 (Ubiquitous):** *The adapter shall identify each Copilot session by a stable session
identifier (its session id) so that archival is idempotent.*

### 5.3 Estrazione dei turni (best-effort, non-fatale)
**REQ-006 (Ubiquitous):** *The adapter shall read a session's event stream and produce ordered
conversation turns (user prompts and assistant responses) with their roles, suitable for the archive.*

**REQ-007 (Unwanted behaviour):** *If an event or line in a session is unreadable or structurally
invalid, then the adapter shall skip it, log a warning, and continue parsing the rest, never failing
the capture run (best-effort, parity with the Claude adapter).*

**REQ-008 (Ubiquitous):** *The adapter shall include in the captured turns the user/assistant dialogue
and shall not treat non-dialogue event payloads (tool calls/results, file diffs) as conversation
turns.*

### 5.4 Associazione sessione↔progetto
**REQ-009 (Ubiquitous):** *The adapter shall associate each captured session with a project, derived
from the session's own recorded metadata (the Copilot session directory name is an opaque id, not a
project path).*

**REQ-010 (Unwanted behaviour):** *If a session's project association cannot be determined, then the
adapter shall not silently misattribute it; it shall either skip the session or archive it under an
explicit unknown-project marker (decision deferred to design).*

### 5.5 Idempotenza e scrub (ereditati)
**REQ-011 (Event-driven):** *When the same Copilot session is captured more than once, the system shall
not duplicate it in the archive (idempotent archival, REQ-M-E4).*

**REQ-012 (Ubiquitous):** *The content captured from Copilot shall pass through the existing
secret-scrubbing before archival; the Copilot adapter shall not bypass or weaken it.*

### 5.6 Privacy e local-first
**REQ-013 (Unwanted behaviour):** *If conversation capture is not enabled, then the Copilot adapter
shall capture and persist nothing (privacy-by-default, REQ-M-E1).*

**REQ-014 (Ubiquitous):** *The adapter shall read only the local Copilot session files; it shall not
contact GitHub's cloud session-sync nor require network access.*

**REQ-015 (Ubiquitous):** *The system shall make explicit (in user-facing documentation) that Copilot
CLI may itself synchronise session data to the GitHub cloud by default — a behaviour upstream of and
independent from Sertor's local archive, outside Sertor's control.*

### 5.7 Host-specificità confinata
**REQ-016 (Ubiquitous):** *All host-specific knowledge of Copilot (paths, event format, project
association) shall live only in the Copilot adapter behind the existing capture port; the archive,
full-text search, semantic search and distillation shall require no modification (Principio X /
REQ-M-E3).*

### 5.8 Riuso del tier
**REQ-017 (Ubiquitous):** *Sessions captured from Copilot shall be archived, full-text searchable
(FEAT-002), semantically searchable when opted in (FEAT-004) and available to distillation (FEAT-003)
on equal footing with Claude-captured sessions, with no changes to those components.*

### 5.9 Degradazione non-fatale della sorgente
**REQ-018 (Unwanted behaviour):** *If the Copilot session store is absent (Copilot CLI not installed,
or no sessions), then capture shall yield an empty result with a warning, not an error.*

**REQ-019 (Unwanted behaviour):** *If a session's event format is not the one the adapter expects
(e.g. after a Copilot CLI update changes it), then the adapter shall degrade to a best-effort/empty
capture with a warning, never a crash, and the limitation shall be documented.*

### 5.10 Attivazione dell'hook già distribuito
**REQ-020 (State-driven):** *While the memory capture is enabled and the Copilot adapter is selected on
a Copilot host, the already-deposited `SessionEnd` hook (FEAT-009) shall capture Copilot sessions —
i.e. the hook stops being inert.*

## 6. Requisiti non funzionali

**NFR-001 (Resilienza al formato):** il parsing è **best-effort**: nessuna eccezione non gestita su
formato inatteso/parziale; il guasto è warning, mai crash (parità con l'adapter Claude).

**NFR-002 (Local-first / offline):** la cattura non produce traffico di rete; le sue dipendenze sono
soddisfatte interamente in locale.

**NFR-003 (Additività a leva spenta):** con la memoria off (default) il comportamento e il costo sono
identici a oggi; nessun file letto, nessun adapter Copilot costruito (gate `memory_enabled`).

**NFR-004 (Testabilità offline):** l'adapter è testabile con una directory di sessione Copilot di
**fixture** (events.jsonl + metadata di esempio), senza Copilot CLI installato né rete — pattern dei
test dell'adapter Claude.

**NFR-005 (Tier invariato):** nessuna modifica ad archivio/ricerca/distillazione; verificabile (le loro
suite restano verdi senza tocchi).

**NFR-006 (Accoppiamento a formato non contrattuale):** il formato `events.jsonl` è un dettaglio
**interno** di Copilot CLI (non un contratto stabile pubblico); la documentazione della feature deve
dichiarare la versione/e di Copilot CLI verificata/e e che aggiornamenti possono richiedere adeguamenti
(mitigato da NFR-001).

## 7. Vincoli, assunzioni e dipendenze

### Vincoli (ereditati dall'epica)
- **Privacy-by-default (REQ-M-E1/E2):** cattura off senza opt-in; scrub a monte; local-first.
- **Host-agnostico nel corpo (REQ-M-E3, Principio X):** l'host-specificità sta SOLO nell'adapter.
- **Idempotenza (REQ-M-E4).**
- **Accesso solo via vehicles (Principio XI):** la cattura è esercitata via CLI/hook, non importando il
  core (eccezione: i test).

### Assunzioni documentate (dalla ricognizione 2026-06-22)
- **A-001 — Sorgente locale Copilot:** sessioni in `~/.copilot/session-state/<uuid>/` con `events.jsonl`
  (transcript), `session.db`, `workspace.yaml`, `vscode.metadata.json`; indice globale
  `~/.copilot/session-store.db`; sede legacy `~/.copilot/history-session-state/`.
- **A-002 — Transcript = `events.jsonl`:** lo stream di eventi JSONL è la fonte naturale dei turni
  (prompt/risposte), come il JSONL di Claude; conferma del mapping esatto = design (DA-CM-1).
- **A-003 — Associazione al progetto da metadata interna:** non dal nome cartella (UUID); candidati
  `workspace.yaml` / `vscode.metadata.json.origin` (DA-CM-2).
- **A-004 — Cloud-sync di Copilot fuori controllo:** Copilot può sincronizzare le sessioni sul cloud
  GitHub di default; Sertor legge il **locale** e non interagisce col sync (REQ-014/015).
- **A-005 — Porta e tier esistenti:** si riusa `TranscriptCaptureAdapter` (8ª porta) e tutto il tier a
  valle senza modifiche; l'entità prodotta è la stessa (`TranscriptContent`/`TranscriptTurn`/`SessionRef`).

### Dipendenze
- **FEAT-001 (a monte):** porta di cattura, archivio, servizio, scrub — l'adapter vi si innesta.
- **FEAT-009 (✅ consegnata):** hook + manopole memoria già distribuiti su Copilot — questa feature li
  rende effettivi.
- **FEAT-002/003/004 (✅):** beneficiano automaticamente delle sessioni Copilot (nessuna modifica).
- **Installer / template `.env`:** cablaggio del valore `SERTOR_MEMORY_ADAPTER=copilot-cli` →
  **debito di completamento** (§10), cross-ref FEAT-009.

## 8. Rischi
- **R-CM-1 — Formato non contrattuale (il nodo):** `events.jsonl` è interno a Copilot CLI; un loro
  aggiornamento può romperne il parsing. Mitigazione: best-effort/non-fatale (NFR-001), versione
  verificata dichiarata (NFR-006), copertura test su fixture (NFR-004).
- **R-CM-2 — Privacy del cloud-sync:** il grezzo Copilot è già potenzialmente sul cloud GitHub (scelta
  di Copilot). Mitigazione: dichiararlo esplicitamente (REQ-015); Sertor resta local-first sul suo lato.
- **R-CM-3 — Associazione al progetto errata:** con cartelle UUID, attribuire una sessione al progetto
  sbagliato sporcherebbe l'archivio per-progetto. Mitigazione: REQ-009/010 (deriva dalla metadata, mai
  misattribuire in silenzio).
- **R-CM-4 — Rumore degli eventi:** `events.jsonl` contiene tool/diff oltre al dialogo; includerli
  gonfierebbe e sporcherebbe la ricerca. Mitigazione: REQ-008 (solo dialogo nei turni).
- **R-CM-5 — Sede legacy e doppia fonte:** `history-session-state/` legacy e `session.db` come fonte
  alternativa potrebbero causare doppioni o lacune. Mitigazione: scelta della fonte in design (DA-CM-3/4)
  + idempotenza (REQ-011).

## 9. Prioritizzazione (MoSCoW) interna

| ID | Requisito / gruppo | Priorità |
|----|-------------------|----------|
| REQ-001..002 | Selezione adapter (+ errore azionabile) | **Must** |
| REQ-003, REQ-005..007 | Discovery + estrazione turni best-effort | **Must** |
| REQ-008 | Solo dialogo nei turni (no tool/diff) | **Must** |
| REQ-011..014 | Idempotenza · scrub · privacy-by-default · local-only | **Must** |
| REQ-016..017 | Host-specificità confinata · riuso tier | **Must** |
| REQ-018 | Degradazione su sorgente assente | **Must** |
| REQ-009 | Associazione al progetto | **Must** |
| NFR-001..005 | Resilienza · offline · additività · testabilità · tier invariato | **Must** |
| REQ-004 | Override del percorso sorgente | **Should** |
| REQ-010 | Politica su progetto indeterminato | **Should** |
| REQ-015, REQ-019, REQ-020 | Trasparenza cloud-sync · resilienza al cambio formato · hook reso vivo | **Should** |
| NFR-006 | Dichiarazione versione/accoppiamento formato | **Should** |
| Debito installer (`SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env`) | §10 | **Should** (completamento) |
| Gestione sede legacy `history-session-state/` | DA-CM-4 | **Could** |

## 10. Domande aperte
**DA-CM-1 — Schema eventi `events.jsonl` → turni [ALTA]:** quali tipi di evento mappano a turni
user/assistant, come ricomporre il testo (streaming/delta?), cosa scartare (tool/diff). Richiede di
leggere eventi reali in design. *(Niente «come» qui: il principio è in REQ-006/008.)*

**DA-CM-2 — Fonte dell'associazione al progetto [ALTA]:** `workspace.yaml` vs `vscode.metadata.json.origin`
vs filtro per `cwd`. Decide REQ-009/010.

**DA-CM-3 — Fonte di verità: `events.jsonl` vs `session.db` [MEDIA]:** quale leggere (o entrambe). Lo
stream JSONL è il candidato naturale (A-002); la `session.db` potrebbe dare metadata/turni più puliti.

**DA-CM-4 — Sede legacy `history-session-state/` [BASSA]:** ignorarla o includerla? (Could.)

**DA-CM-5 — Nome del valore adapter [BASSA]:** proposta `copilot-cli` (coerente col naming
`--assistant copilot-cli` dell'installer); confermare in design.

**DA-CM-6 — Trasparenza del cloud-sync [BASSA]:** sola documentazione (REQ-015) o anche un avviso a
runtime quando si cattura da Copilot? Proposta: documentazione.

**DA-CM-7 — Distribuzione del valore adapter via installer [MEDIA, tracciamento]:** il template `.env`
dell'installer su host Copilot deve suggerire `SERTOR_MEMORY_ADAPTER=copilot-cli` (oggi default
`claude-code`). Da promuovere come debito di completamento (cross-ref FEAT-009), **non** risolto qui.
