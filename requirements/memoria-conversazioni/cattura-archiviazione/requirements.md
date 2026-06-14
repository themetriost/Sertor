# Requisiti — Cattura & archiviazione locale dei transcript
<!-- Deriva da: FEAT-001 -->

> Livello: **feature**. Decomposta da [`requirements/memoria-conversazioni/epic.md`](../epic.md),
> backlog FEAT-001. Fornisce il **tier grezzo episodico** oggi mancante: cattura i transcript delle
> sessioni tramite un adapter host-specifico e li conserva in un archivio locale persistente,
> idempotente e scrubbed. Non include la ricerca (FEAT-002), l'embedding (FEAT-004) né la
> governance avanzata di retention (FEAT-006).

---

## 1. Contesto e problema (perché)

Ogni conversazione con l'agente produce conoscenza procedurale e decisionale che oggi viene persa
o distillata «al volo» nel wiki senza una fonte grezza a cui tornare. Il modello attuale è **lossy**:
se la distillazione non cattura un dettaglio, quel dettaglio è irrecuperabile. Manca il **tier
episodico** — l'archivio delle conversazioni intere da cui la distillazione (FEAT-003/Should) potrà
attingere e su cui la ricerca full-text (FEAT-002/Must) opererà.

**Fatto ancorante sul primo adapter (Claude Code):** Claude Code persiste già ogni sessione come
file JSONL sotto `~/.claude/projects/<progetto-encoded>/<session-id>.jsonl`. Il primo adapter di
cattura legge quei file — non serve un hook che intercetti turni in tempo reale. Questa osservazione
risolve parzialmente la DA-M-a dell'epica per Claude Code, ma la porta di cattura resta astratta:
l'adapter Claude-Code è la prima implementazione, non l'unica.

**Pattern di riferimento:** il _session archive_ del pattern Hermes (Nous Research) — SQLite + FTS,
memoria episodica interrogabile.

**Ancoraggi a pattern già nel repo** (da riusare nel design a valle, non prescrittivi qui):
- Store SQLite locale con degradazione non-fatale: `src/sertor_core/adapters/embeddings/cache.py`
  (pattern `INSERT OR IGNORE`, lazy connect, no-op su guasto) e
  `src/sertor_core/observability/store.py` (stesso pattern, append-only, indici `(operation, ts)`).
- Scrub dei segreti per-campo: `src/sertor_core/observability/logging.py` — funzione `redact()`
  word-level su chiavi con hint `key/token/secret/password/authorization`; per i transcript
  occorre estendere il meccanismo al **contenuto testuale** (non solo ai campi strutturati).
- Manopole `Settings` e `_bool_env`: pattern `SERTOR_*` in
  `src/sertor_core/config/settings.py` — le nuove manopole di questa feature seguiranno lo stesso
  stile (boolean env con default off = privacy-by-default).
- Stile delle porte `Protocol` (structural typing, runtime-checkable, no inheritance):
  `src/sertor_core/domain/ports.py` — la porta `TranscriptCaptureAdapter` di questa feature seguirà
  lo stesso stile delle 6 porte esistenti (`EmbeddingProvider`, `VectorStore`, …,
  `ObservabilityStore`).

---

## 2. Obiettivi e criteri di successo

Criteri derivati da CS-1, CS-4, CS-5 dell'epica, declinati a livello feature:

| ID | Criterio | Misura |
|----|----------|--------|
| SC-F1 | **Archivio conservato** | Con cattura attiva, dopo N sessioni il numero di record nell'archivio locale è esattamente N (una voce per sessione; duplicati = 0). |
| SC-F2 | **Idempotenza** | Archiviare la stessa sessione più volte non crea duplicati (verificabile: #record dopo K archiviazioni della stessa sessione = 1). |
| SC-F3 | **Privacy-by-default** | Con `SERTOR_MEMORY=false` (default) nessun file/record di transcript viene creato né modificato su disco. |
| SC-F4 | **Scrub segreti** | Con cattura attiva, nessun pattern di segreto noto (API key, token, password) appare in chiaro nell'archivio — verificabile su corpus di test con segreti sintetici. |
| SC-F5 | **Host-agnostico** | La logica di archivio e il contratto della porta passano i test su ≥2 host/assistenti simulati (mock adapter); il test dell'adapter Claude-Code reale funziona su macchina con `~/.claude/`. |
| SC-F6 | **Non-distruttività** | Operazioni di re-cattura di sessioni già archiviate non alterano il contenuto già presente (idempotenza conservativa). |

---

## 3. Stakeholder e attori

| Attore | Ruolo in questa feature |
|--------|------------------------|
| **Owner/maintainer** | Abilita la cattura via config; verifica che l'archivio cresca e sia recuperabile. |
| **Agente LLM (Claude Code, primo)** | Sorgente dei transcript (file JSONL in `~/.claude/`). |
| **Sistema-wiki (FEAT-003/Should)** | Consumatore futuro dell'archivio come fonte grezza per `distill`/`record`. |
| **Adapter Claude-Code** | Prima implementazione concreta della porta `TranscriptCaptureAdapter`; host-specifica. |
| **Adapter futuri (FEAT-008/Could)** | Altre implementazioni (Copilot, Codex, …); fuori ambito qui. |

---

## 4. Ambito

### In ambito
- Definizione della **porta astratta** `TranscriptCaptureAdapter` (stile `Protocol` come le 6 porte
  esistenti): contratto di cattura host-agnostico.
- **Prima implementazione**: adapter Claude-Code che legge i file JSONL di sessione da
  `~/.claude/projects/<progetto-encoded>/`.
- **Archivio locale persistente** delle sessioni catturate: conservato (non ruotato), per-progetto,
  gitignored.
- **Idempotenza** sull'archiviazione della stessa sessione (stessa `session_id` non crea duplicati).
- **Scrub dei segreti nel contenuto testuale** dei transcript (estensione del pattern `redact()`
  esistente ai testi liberi, non solo ai campi strutturati).
- **Manopola di abilitazione** `SERTOR_MEMORY` (default `false` = cattura disattivata,
  privacy-by-default) e **retention configurabile** come gancio (la politica di scadenza di
  dettaglio è FEAT-006/Could, ma il campo/parametro deve esistere qui come gancio).
- **Selezione dell'adapter** tramite config (Principio X): il corpo non conosce l'adapter concreto.
- Integrazione nel **composition root** esistente (`src/sertor_core/composition.py`) con una
  `build_memory_store()` / `build_capture_adapter()` analoga ai `build_*` già presenti.
- Archivio **locale** (on-machine), **per-progetto**, sotto `.sertor/` o `<index_dir>/` (coerente
  con il pattern di collocazione degli artefatti runtime esistenti).

### Fuori ambito
- **Ricerca full-text sull'archivio** (FEAT-002/Must): questa feature solo cattura e persistenza.
- **Ricerca semantica / embedding dei transcript** (FEAT-004/Should): nessun embedding qui.
- **Aggancio operativo alla distillazione** (FEAT-003/Should): l'archivio esiste come fonte, ma
  l'integrazione con `distill`/`record` è FEAT-003.
- **Governance avanzata di retention** (scadenza, compattazione, cancellazione selettiva):
  FEAT-006/Could; qui solo il gancio (parametro retention con valore di default «conserva tutto»).
- **Cattura multi-assistente oltre Claude Code** (FEAT-008/Could): altri adapter sono
  implementazioni future della stessa porta.
- **Cattura selettiva "remember this"** (FEAT-005/Could): qui si archivia la sessione intera
  (assunzione: tutto-con-opt-in; la selezione per marcatura è FEAT-005).
- **Roll-up cross-progetto** (FEAT-007/Could): l'archivio resta per-progetto.
- **Telemetria / metriche operative** sull'archiviazione: è l'epica `osservabilita` gemella;
  possono coesistere ma non si mescolano.
- **Definizione del formato di archivio** (schema, struttura interna): materia del design a valle.

---

## 5. Requisiti funzionali (EARS)

### 5.1 Controllo di abilitazione (privacy-by-default)

**REQ-001 (Unwanted, privacy-by-default):**
*If conversation capture is not explicitly enabled (`SERTOR_MEMORY` is false or absent), then the
system shall not create, modify, or read any transcript archive file or record.*

**REQ-002 (Event-driven):**
*When conversation capture is enabled and the system is initialised, the system shall load the
configured capture adapter without importing host-specific dependencies in the core body.*

**REQ-003 (State-driven):**
*While conversation capture is enabled, the system shall use only the adapter selected by
configuration to obtain transcript content, with no host-specific logic in the archive service or
domain.*

### 5.2 Porta di cattura (contratto astratto)

**REQ-004 (Ubiquitous):**
*The system shall expose a `TranscriptCaptureAdapter` abstraction (structural Protocol, no
inheritance required) with at minimum: `list_sessions(project_id) -> list[SessionRef]` and
`read_session(session_ref) -> TranscriptContent`.*

**REQ-005 (Ubiquitous):**
*The system shall select the concrete capture adapter implementation exclusively via configuration,
with no conditional branching on host identity in the archive service or domain layer.*

**REQ-006 (Unwanted, adapter non disponibile):**
*If the configured capture adapter cannot locate the expected transcript source (e.g., the
`~/.claude/projects/` directory is absent for the Claude-Code adapter), then the system shall emit
a warning and leave the archive unchanged, without raising an unhandled error.*

### 5.3 Adapter Claude-Code (prima implementazione)

**REQ-007 (Optional feature — adapter Claude-Code):**
*Where the Claude-Code capture adapter is configured, the system shall discover transcript sessions
by scanning the JSONL files under `~/.claude/projects/<project-encoded>/` for the current project.*

**REQ-008 (Optional feature — adapter Claude-Code):**
*Where the Claude-Code capture adapter is configured, the system shall read each session's content
from the corresponding JSONL file without modifying or deleting it.*

**REQ-009 (Optional feature — adapter Claude-Code):**
*Where the Claude-Code capture adapter is configured, the system shall derive the session identifier
from the JSONL filename (`<session-id>.jsonl`), treating the filename stem as the canonical session
key for idempotence checks.*

### 5.4 Archivio locale

**REQ-010 (Ubiquitous):**
*The system shall persist archived transcripts in a local archive stored under the project's
runtime directory (consistent with `<index_dir>/` placement of existing runtime artifacts), never
in a remotely-accessible location by default.*

**REQ-011 (Ubiquitous):**
*The archive shall be namespaced per project, so that sessions from different projects do not
co-mingle in the same archive.*

**REQ-012 (Ubiquitous):**
*The archive file or directory shall be listed in `.gitignore` (or equivalent), so that transcript
content is never accidentally committed to version control.*

**REQ-013 (Event-driven — archiviazione):**
*When a session is archived, the system shall record at minimum: the session identifier, the
project identifier, the capture timestamp (UTC), the source adapter kind, and the scrubbed
transcript content.*

**REQ-014 (Event-driven — conservazione):**
*When a session is archived, the system shall not delete or overwrite any previously archived
session, regardless of its age, unless an explicit deletion command is issued (archivio conservato,
non ruotato).*

### 5.5 Idempotenza

**REQ-015 (Event-driven — idempotenza):**
*When the same session (identified by its canonical session key) is submitted for archival more
than once, the system shall store it exactly once, leaving the existing record unchanged on
subsequent submissions.*

**REQ-016 (Unwanted — duplicati):**
*If a session with the same canonical key already exists in the archive, then the system shall not
create a duplicate record and shall not raise an error (silent idempotence).*

### 5.6 Scrub dei segreti nel contenuto

**REQ-017 (While — cattura attiva):**
*While archiving a transcript, the system shall apply secret-pattern scrubbing to the free-text
content of the transcript before persisting it, replacing matched patterns with a placeholder.*

**REQ-018 (Ubiquitous — pattern minimi):**
*The secret scrubbing shall cover at minimum: API keys (patterns like `sk-...`, `AKIA...`),
bearer tokens, environment-variable assignments of the form `KEY=VALUE` where the key name
contains known secret hints (`key`, `token`, `secret`, `password`, `authorization`), and
inline `Authorization:` header values.*

**REQ-019 (Unwanted — scrub non blocca):**
*If the secret-scrubbing step encounters an unrecognised pattern or fails on a segment, then the
system shall apply a conservative fallback (redact the full segment rather than passing it through)
and emit a warning, without aborting the archival.*

**REQ-020 (Ubiquitous — estensibilità scrub):**
*The secret-scrubbing rules shall be configurable (addable patterns via config), so that
project-specific secret formats can be covered without changing the core body.*

### 5.7 Retention (gancio)

**REQ-021 (Ubiquitous — gancio retention):**
*The system shall expose a `SERTOR_MEMORY_RETENTION_DAYS` configuration parameter (default: no
expiry, i.e., retain indefinitely) whose value is stored in the archive metadata, so that
FEAT-006 can implement enforcement without schema migration.*

**REQ-022 (Unwanted — retention non applicata qui):**
*If `SERTOR_MEMORY_RETENTION_DAYS` is set, then the system shall record the expiry policy in the
archive metadata but shall not enforce automatic deletion in this feature (enforcement is FEAT-006).*

### 5.8 Osservabilità minima

**REQ-023 (Event-driven — evento di archivio):**
*When a session is successfully archived, the system shall emit a structured log event
(`operation="memory_archive"`) with at minimum: session key, project identifier, adapter kind,
content size in characters (post-scrub), and whether the session was new or already present
(idempotent skip).*

**REQ-024 (Event-driven — evento di skip):**
*When a session is skipped because it already exists in the archive (idempotent path), the system
shall emit a structured log event (`operation="memory_archive_skip"`) so that batch runs are
observable without silent no-ops.*

**REQ-025 (Unwanted — store non disponibile):**
*If the archive store is unavailable or corrupted, then the system shall emit a warning and leave
the in-flight operation as a no-op, without propagating a fatal error to the caller (pattern
non-fatale, coerente con `SqliteObservabilityStore` e `EmbeddingCache`).*

### 5.9 Composition e integrazione

**REQ-026 (Ubiquitous — composition root):**
*The system shall wire the capture adapter and the archive store exclusively in the composition
root, with `build_memory_store()` and `build_capture_adapter()` functions that read `Settings`
and return protocol-compliant instances.*

**REQ-027 (State-driven — cattura disattivata):**
*While conversation capture is disabled (`SERTOR_MEMORY=false`), the system shall not instantiate
the capture adapter nor the archive store (lazy — no dependency imported, no file opened).*

---

## 6. Requisiti non funzionali

| ID | Area | Requisito |
|----|------|-----------|
| NFR-001 | **Privacy** | Il contenuto dei transcript archiviati non lascia mai la macchina locale per default; nessuna trasmissione a servizi remoti in questa feature (il remoto è opt-in aggiuntivo in FEAT-004). |
| NFR-002 | **Isolamento dipendenze** | Le dipendenze host-specifiche (lettura JSONL da `~/.claude/`) devono essere contenute nell'adapter; il core body (archivio, porta, scrub) usa solo stdlib. |
| NFR-003 | **Degradazione non-fatale** | Un guasto dello store di archivio (disco pieno, file corrotto) non deve interrompere l'operazione principale dell'agente; degradazione a warning + no-op (stesso pattern di `SqliteObservabilityStore` in `src/sertor_core/observability/store.py:9`). |
| NFR-004 | **Crescita prevedibile** | L'archivio deve crescere proporzionalmente al numero di sessioni catturate; nessuna duplicazione silente (idempotenza garantita da REQ-015/016). |
| NFR-005 | **Testabilità senza host reale** | La porta `TranscriptCaptureAdapter` e l'archivio devono essere testabili con un mock adapter (in-memory o filesystem temporaneo) senza dipendere dall'installazione reale di Claude Code o di altri assistenti. |
| NFR-006 | **Osservabilità** | Ogni operazione significativa (archivio, skip, guasto) emette un evento strutturato via `log_event` (coerente con `src/sertor_core/observability/logging.py`), mai segreti in chiaro. |
| NFR-007 | **Configurazione centralizzata** | Tutte le manopole di questa feature (`SERTOR_MEMORY`, `SERTOR_MEMORY_ADAPTER`, `SERTOR_MEMORY_RETENTION_DAYS`, pattern scrub aggiuntivi) vivono in `Settings` come unica fonte di default. |
| NFR-008 | **Idempotenza operativa** | `build_memory_store()` e `build_capture_adapter()` sono idempotenti: chiamate multiple con la stessa `Settings` producono istanze equivalenti senza effetti collaterali. |

---

## 7. Vincoli, assunzioni e dipendenze

### Vincoli
- **Principio X (host-agnostico):** nessuna logica host-specifica nel corpo; ogni adapter è
  un'implementazione separata della porta, selezionabile via config.
- **Privacy-by-default (REQ-M-E1 dell'epica):** la cattura è off per default; opt-in esplicito
  richiesto (`SERTOR_MEMORY=true`).
- **Local-first:** nessuna trasmissione remota in questa feature.
- **Non-distruttività:** l'archivio non cancella mai sessioni automaticamente (la cancellazione
  esplicita è FEAT-006).
- **Stdlib-only nel core body** (coerente con embedding cache e observability store): nessuna
  dipendenza esterna non già presente.

### Assunzioni documentate
- **DA-F1 — Granularità (sessione):** l'unità di memoria archiviata è la **sessione intera**
  (non il singolo turno né il thread). Questa è l'assunzione di default (risolve DA-M-b dell'epica);
  una granularità più fine (turno/thread) è rivalutabile in una iterazione successiva se la ricerca
  (FEAT-002) lo richiede. [Documenta come assunzione; conferma utente benvenuta.]
- **DA-F2 — Cattura tutto-con-opt-in:** con la cattura attiva si archiviano tutte le sessioni
  (non solo quelle marcate). La selezione esplicita «remember this» è rinviata a FEAT-005/Could.
  Questa scelta aumenta il rumore ma massimizza la copertura episodica (R-5 dell'epica).
  [Assunzione di default; conferma utente benvenuta.]
- **DA-F3 — Posizione archivio:** l'archivio risiede sotto `<index_dir>/memory/` (o analogo
  percorso coerente con il pattern `<index_dir>/observability.sqlite` e `<index_dir>/embed_cache.sqlite`
  già in uso). La posizione esatta è materia del design a valle.
- **DA-F4 — Formato JSONL Claude Code:** i file sotto `~/.claude/projects/<progetto>/` sono JSONL
  con una voce per turno; il nome file è `<session-id>.jsonl`. Questa struttura è osservata
  empiricamente su questa sessione (`C:\Users\domen\.claude\projects\C--Workspace-Git-Sertor\
  086720cf-...jsonl`) ma non è documentata pubblicamente da Anthropic — potrebbe variare.
  [DA CHIARIRE: vedere domande aperte §10, DA-F4.]
- **DA-F5 — Scrub basato su pattern:** il meccanismo di scrub è pattern-matching (regex/euristiche),
  non LLM-based; nessuna inferenza semantica nel percorso di cattura (coerente con Principio X).
  Lo scrub basato su LLM è a valle (FEAT-006 eventualmente).
- **DA-F6 — Nessuna cattura in tempo reale:** la cattura avviene in batch (lettura dei JSONL dopo
  la sessione), non via hook che intercettano i turni durante la sessione. Questo semplifica
  l'adapter Claude-Code e riduce il rischio di dipendenza da API interne.

### Dipendenze
- **FEAT-003 ✅ (distillazione wiki):** l'archivio diventa la fonte grezza per `distill`/`record`
  (FEAT-003/Should) — ma FEAT-001 non dipende da FEAT-003; la dipendenza è inversa.
- **FEAT-002 (ricerca full-text):** dipende da FEAT-001 (non può cercare senza archivio); FEAT-001
  deve essere completata prima di FEAT-002.
- **`src/sertor_core/composition.py`:** il composition root va esteso con `build_memory_store()` e
  `build_capture_adapter()` (analogia con `build_observability_store()` già presente).
- **`src/sertor_core/config/settings.py`:** va esteso con le nuove manopole `SERTOR_MEMORY*`.
- **`src/sertor_core/domain/ports.py`:** va esteso con la porta `TranscriptCaptureAdapter` (ottava
  porta, stesso stile `Protocol`).
- **Epica `osservabilita` (parallela):** condivide il principio di privacy (REQ-M-E1/E4) ma
  archivi distinti; nessuna dipendenza tecnica diretta.

---

## 8. Rischi

| ID | Rischio | Probabilità | Impatto | Mitigazione |
|----|---------|-------------|---------|-------------|
| R-F1 | **Formato JSONL Claude Code non stabile** — Anthropic non documenta il formato; potrebbe cambiare tra versioni | Media | Alta (adapter smette di funzionare) | Adapter isolato (fallisce gracefully: REQ-006); test su corpus JSONL campione; parsing difensivo |
| R-F2 | **Percorso `~/.claude/` non trovato** — ambienti container, CI, Windows con percorsi diversi | Media | Media (adapter non funziona, ma sistema non crasha) | REQ-006: warning + no-op; path configurabile |
| R-F3 | **Scrub incompleto** — pattern segreti non coperti dal matcher regex | Media | Alta (segreto persiste in chiaro) | REQ-019: fallback conservativo (redact intero segmento); REQ-020: pattern configurabili; test con segreti sintetici (SC-F4) |
| R-F4 | **Crescita illimitata dell'archivio** — sessioni giornaliere su più progetti | Bassa-Media | Media (disco pieno) | REQ-021/022: gancio retention documentato; NFR-003: degrada a warning; FEAT-006 gestirà enforcement |
| R-F5 | **Falso senso di privacy** — utente crede che scrub = sicurezza totale | Media | Media | Documentazione esplicita: lo scrub è best-effort su pattern noti; segreti non convenzionali possono non essere catturati |
| R-F6 | **Collisione di session-id** — due assistenti/progetti generano lo stesso UUID | Molto bassa | Bassa (namespace per progetto mitiga) | REQ-011: namespace per progetto; REQ-009: session key derivata da filename |

---

## 9. Prioritizzazione (MoSCoW) interna alla feature

| ID | Requisito / gruppo | Priorità |
|----|--------------------|----------|
| REQ-001…003 | Controllo abilitazione / privacy-by-default | **Must** |
| REQ-004…005 | Porta astratta `TranscriptCaptureAdapter` | **Must** |
| REQ-006 | Degradazione graceful adapter non disponibile | **Must** |
| REQ-007…009 | Adapter Claude-Code (prima implementazione) | **Must** |
| REQ-010…014 | Archivio locale persistente e conservato | **Must** |
| REQ-015…016 | Idempotenza | **Must** |
| REQ-017…019 | Scrub segreti (core + fallback) | **Must** |
| REQ-023…025 | Osservabilità minima + degradazione non-fatale | **Must** |
| REQ-026…027 | Composition e lazy wiring | **Must** |
| REQ-020 | Pattern scrub configurabili (estensibilità) | **Should** |
| REQ-021…022 | Gancio retention (`SERTOR_MEMORY_RETENTION_DAYS`) | **Should** |
| NFR-001…008 | Non-funzionali trasversali | **Must** (derivati dai Must funzionali) |

---

## 10. Domande aperte

**DA-F4 — Stabilità e struttura del formato JSONL Claude Code [CRITICA]:**
I file `~/.claude/projects/<progetto>/<session-id>.jsonl` sono osservati empiricamente (sessione
`086720cf-...` su questo progetto), ma Anthropic non li documenta pubblicamente come API stabile.
Domande:
- Qual è la struttura di una voce JSONL (campi presenti, annidamento, encoding)?
- Esiste una versione/schema documentato o un changelog noto?
- Il nome file `<session-id>.jsonl` è garantito stabile o potrebbe cambiare?
Senza risposta, l'adapter deve operare in modalità difensiva (parsing best-effort con fallback).

**DA-F7 — Granularità confermata (sessione vs turno) [MEDIA]:**
L'assunzione DA-F1 fissa la granularità alla sessione intera. Se la ricerca full-text (FEAT-002)
o la distillazione (FEAT-003) beneficerebbero di granularità più fine (turno o scambio),
l'archivio andrebbe esteso. Confermare o rivalutare prima del design.

**DA-F8 — Cattura-tutto vs selettiva: conferma del default [MEDIA]:**
L'assunzione DA-F2 archivia ogni sessione (tutto-con-opt-in). L'alternativa — catturare solo
le sessioni esplicitamente marcate (FEAT-005) — riduce il rumore e il rischio privacy, ma
richiederebbe FEAT-005 come prerequisito anche per FEAT-001. Confermare il default prima del design.

**DA-F9 — Posizione e nome dell'archivio locale [BASSA]:**
L'assunzione DA-F3 suggerisce `<index_dir>/memory/` per coerenza con gli artefatti esistenti.
Alternativa: directory separata (es. `~/.sertor/memory/` condivisa tra progetti). La scelta impatta
la portabilità e il backup. Da decidere nel design, ma utile sapere se l'utente ha preferenze.

**DA-F10 — Encoding e dimensione massima di una sessione [BASSA]:**
Non è noto se le sessioni Claude Code abbiano un limite di dimensione pratico. Se una sessione è
molto grande (ore di lavoro intensivo), il costo di scrub e archiviazione potrebbe essere
rilevante. Nessun requisito di limite oggi: da monitorare nell'implementazione.
