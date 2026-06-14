# Phase 0 — Research: Cattura & archiviazione locale dei transcript (031)

**Feature**: `031-cattura-archiviazione` · **Spec**: [spec.md](./spec.md) · **Data**: 2026-06-14

Questo documento risolve gli ignoti tecnici della spec prima del design. Ogni decisione è ancorata al
codice reale del core (citato come `path:lineno`) e ai pattern già su master. Le decisioni segnano
**FUORI AMBITO** dove appartengono a feature successive (FEAT-002 ricerca, FEAT-003 distillazione,
FEAT-005 remember-this, FEAT-006 retention, FEAT-008 multi-assistente).

---

## D1 — Schema dell'archivio SQLite (granularità ibrida: sessione + confini dei turni)

**Decisione.** Archivio SQLite a **due tabelle** sotto `<index_dir>/memory.sqlite`:

```sql
-- una riga per sessione (unità idempotente, FR-013/015)
CREATE TABLE IF NOT EXISTS sessions (
    session_key   TEXT PRIMARY KEY,   -- chiave canonica = stem del filename (FR-008)
    project_id    TEXT NOT NULL,      -- namespace progetto (FR-010)
    captured_at   REAL NOT NULL,      -- timestamp di cattura, epoch UTC (FR-012)
    adapter_kind  TEXT NOT NULL,      -- tipo di adapter sorgente (FR-012)
    metadata      TEXT NOT NULL       -- JSON: { retention_days: int|null, source_path, turn_count, ... }
);
-- i confini dei turni, leggibili senza ri-parsare il JSONL grezzo (FR-013, granularità ibrida)
CREATE TABLE IF NOT EXISTS turns (
    session_key  TEXT NOT NULL,       -- FK logica → sessions.session_key
    turn_index   INTEGER NOT NULL,    -- ordinale stabile nell'ordine di emissione (idempotenza)
    role         TEXT NOT NULL,       -- 'user' | 'assistant'
    ts           REAL,                -- timestamp del turno (epoch UTC), null se assente nella sorgente
    content      TEXT NOT NULL,       -- testo del turno GIÀ SCRUBBED (FR-017)
    PRIMARY KEY (session_key, turn_index)
);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions (project_id);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns (session_key, turn_index);
```

**Razionale.** La decisione utente (DA-M-b, Assumptions della spec) è **granularità ibrida**: unità
*archiviata* = sessione intera (record idempotente), ma con i **confini dei turni preservati** così
che FEAT-002 possa indicizzare per turno **senza ri-elaborare la sorgente grezza**. Una tabella `turns`
separata, anziché incapsulare i turni come JSON nel `content` di `sessions`, rende i confini turno
**direttamente interrogabili in SQL** (`SELECT content FROM turns WHERE session_key=?`): FEAT-002 itererà
le righe `turns` come unità di indicizzazione, ogni turno con identità stabile `(session_key, turn_index)`
e `role`/`ts` per la citazione. Niente JSON da riparsare a query-time.

**Come FEAT-002 leggerà i turni (seam documentato, fuori ambito qui).** La ricerca episodica non legge
il `.jsonl` di Claude Code: legge la tabella `turns`. Per ogni turno costruisce un documento indicizzabile
(`chunk_id` derivabile da `session_key#turn_index`, `doc_type` episodico, `path` = riferimento di sessione,
metadata `role`/`ts`). Lo scrub è **già applicato** a monte (in archiviazione): la ricerca non rivede mai
testo non ripulito. Questo è il **contratto fra le due feature** e giustifica la tabella separata.

**Alternative scartate.**
- *Turni come JSON nel `content` di `sessions`* (granularità sola-sessione): più semplice da scrivere,
  ma FEAT-002 dovrebbe ri-parsare il JSON a ogni indicizzazione e non avrebbe identità di turno stabile
  in SQL. Contraddice esplicitamente FR-013 («senza ri-elaborare la sorgente»).
- *Una riga per turno, niente tabella `sessions`* (granularità sola-turno): perde l'unità idempotente di
  sessione richiesta da FR-015/SC-002 (idempotenza «per chiave canonica di sessione») e i metadati
  per-sessione (retention, adapter). La decisione utente è **ibrida**, non per-turno.
- *Contenuto integrale della sessione anche in `sessions.content`* (ridondanza grezzo+turni): duplica i
  dati, costo di scrub e storage raddoppiato, nessun consumatore lo richiede (YAGNI, Principio III). La
  sessione si ricompone concatenando i suoi `turns` se mai servisse.

**Pattern di storage riusato.** Identico a `SqliteObservabilityStore`
(`src/sertor_core/observability/store.py:23-83`) ed `EmbeddingCache`
(`src/sertor_core/adapters/embeddings/cache.py:34-95`): `__init__` salva solo il path; `_connect()` è
**lazy** e idempotente (`CREATE TABLE IF NOT EXISTS`, `self._conn` assegnato solo dopo schema OK → file
corrotto resta `None`); ogni metodo avvolge `sqlite3.Error` in un **warning non-fatale** + no-op/`[]`
(FR-025, SC-007). `stdlib-only` (`sqlite3`/`json`).

---

## D2 — Porta dedicata per lo store vs adapter concreto

**Decisione.** **Una sola porta nuova: `TranscriptCaptureAdapter`** (la *cattura*, host-specifica). Lo
**store di archivio NON ha una porta**: è un componente concreto stdlib (`MemoryArchive`) cablato in
composition, come `SqliteObservabilityStore`/`EmbeddingCache`.

**Razionale.**
- La **cattura** varia per ospite (Claude Code oggi, altri assistenti domani — FEAT-008) ed è il punto
  in cui entra codice host-specifico: **deve** stare dietro un'astrazione (Principio X, FR-004/005).
  Segue lo stile delle 7 porte esistenti in `src/sertor_core/domain/ports.py`: `Protocol`,
  `@runtime_checkable`, structural typing, nessuna ereditarietà, mockabile senza subclassing.
- Lo **store** non varia per ospite né per backend in questa feature: è SQLite locale, sempre. Aggiungere
  una porta `Protocol` per un'unica implementazione concreta è astrazione senza evidenza presente
  (Principio III/YAGNI). Il precedente nel repo è netto: `EmbeddingCache` e `SqliteObservabilityStore`
  sono store SQLite **senza** porta — `ObservabilityStore` ha una porta solo perché è il *seam* fra
  scrittura (handler) e lettura (FEAT-002 report), un confine reale fra due feature. Qui scrittura e
  lettura-futura (FEAT-002) condividono lo schema, non c'è un secondo produttore.

**Porta `TranscriptCaptureAdapter` (forma proposta, dettaglio in [data-model.md](./data-model.md)):**

```python
@runtime_checkable
class TranscriptCaptureAdapter(Protocol):
    kind: str  # tipo di adapter (es. "claude-code") — finisce in sessions.adapter_kind

    def list_sessions(self) -> list[SessionRef]:
        """Riferimenti leggeri alle sessioni del progetto corrente presso la sorgente.
        Sorgente assente → [] (l'adapter logga il warning; FR-006). Non modifica la sorgente."""
        ...

    def read_session(self, ref: SessionRef) -> TranscriptContent:
        """Legge e struttura in turni il contenuto di una sessione (best-effort difensivo)."""
        ...
```

**Alternative scartate.** *Porta anche per lo store*: simmetria estetica con `ObservabilityStore`, ma
nessun secondo consumatore/implementazione oggi → over-engineering. Rivalutabile in FEAT-002 se la
ricerca volesse un boundary di lettura proprio (decisione di quella feature, non di questa).

---

## D3 — Parsing difensivo del JSONL di Claude Code (formato non documentato)

**Decisione.** L'adapter Claude-Code legge
`~/.claude/projects/<encoded-project-path>/<session-id>.jsonl`, **una riga JSON per evento**, ed estrae i
turni **best-effort**: righe non parsabili → skip + warning (mai fatale, FR-006/Edge Cases).

**Ancoraggio alla struttura reale** (ispezione di file veri sotto
`~/.claude/projects/C--Workspace-Git-Sertor/*.jsonl`, 2026-06-14):

- **Encoding del path progetto**: i separatori del path assoluto (`:`, `\`, `/`) diventano `-`. Verificato:
  `C:\Workspace\Git\Sertor` → cartella `C--Workspace-Git-Sertor`. L'adapter deriva l'encoded path dal `cwd`
  del progetto ospite (passato in costruzione dalla config/composition, **non** hardcodato — Principio X).
- **Ogni riga è un evento** con un campo `type` ∈ {`user`, `assistant`, `system`, `summary`,
  `attachment`, `mode`, `permission-mode`, `last-prompt`, `file-history-snapshot`, `ai-title`, …}.
- **I turni veri** sono gli eventi con `message` (dict) che ha `role` ∈ {`user`, `assistant`}. Portano
  anche `timestamp` (ISO 8601), `uuid`, `parentUuid`, `cwd`, `gitBranch`, `sessionId`.
- **`message.content`** è:
  - **stringa** (prompt utente semplice), oppure
  - **lista di block** con `type` ∈ {`text`, `thinking`, `tool_use`, `tool_result`}.
- **Testo da conservare**: solo i block `text` (e `thinking` per l'assistant); `tool_use`/`tool_result`
  sono voluminosi e poco utili come memoria conversazionale → **scartati** dall'estrazione del turno
  (riducono rumore e superficie di scrub). Gli eventi `system`/`summary`/`attachment`/`mode`/… **non**
  sono turni → ignorati.
- **`session-id` = stem del filename** (es. `864c7578-…ce45cc746824`): è la chiave canonica (D4).
- **Le cartelle omonime** accanto ai `.jsonl` (es. `085b6407-…/`) non sono sessioni: si scandiscono solo
  i file `*.jsonl`.

**Regole di robustezza (parser difensivo).**
1. File/cartella sorgente assente → `[]` + warning (`memory_capture_source_absent`), archivio invariato
   (FR-006, US3 scenario 3).
2. Riga vuota → skip silenzioso; riga non-JSON → skip + warning (`memory_capture_unparsable_line` con
   numero di riga), **mai** eccezione propagata (Edge Case «transcript enorme/righe non parsabili»).
3. Evento senza `message.role` valido o senza testo estraibile → non genera un turno (skip).
4. `timestamp` ISO non parsabile → `ts=None` nel turno (campo nullable), non un errore.
5. Sessione con **zero turni** estraibili (solo system/tool) → l'archiviazione la salta con un warning
   (non crea un record vuoto).

**Razionale.** Il formato non è documentato pubblicamente (Assumptions): assumere uno schema rigido lo
renderebbe fragile a ogni release di Claude Code. Best-effort + skip osservabile mantiene la cattura
robusta e non-fatale (Principio IV: un'assenza/riga illeggibile è un esito legittimo loggato, non
un'eccezione). Tutta la conoscenza host-specifica (encoding path, nomi dei campi, tipi di block) vive
**solo** in questo adapter (Principio X): il servizio e il dominio non la conoscono.

**Alternative scartate.** *Parser strict che valida l'intero schema*: fragile, viola la tolleranza
richiesta. *Conservare anche tool_use/tool_result*: gonfia l'archivio e la superficie di scrub senza
valore di memoria conversazionale (rivalutabile in futuro se un consumatore lo chiede — YAGNI).

---

## D4 — Idempotenza (chiave canonica = stem del filename)

**Decisione.** Chiave canonica `session_key` = **stem del filename** della sessione (`<session-id>`,
FR-008). L'archiviazione usa `INSERT OR IGNORE` su `sessions.session_key` (PK): sessione già presente →
**skip osservabile** (evento `memory_session_skipped`, FR-024), record esistente **invariato**, nessun
errore (FR-015/016, SC-002). I `turns` si scrivono **solo** quando la sessione è nuova (stessa
transazione), così la ri-archiviazione non li tocca.

**Razionale.** Identico pattern a `EmbeddingCache.put` (`INSERT OR IGNORE`,
`adapters/embeddings/cache.py:82-95`) e agli ID stabili del dominio (Principio VI): lo stem del filename è
stabile e derivato dalla sorgente, come `Document.id` = path relativo. La distinzione **skip osservabile**
(FR-024) vs no-op silenzioso è esplicita nei requisiti (Edge Case «riprocesso massivo»): l'evento di skip
è emesso, non soppresso.

**Alternative scartate.** *Hash del contenuto come chiave*: il contenuto di una sessione cresce mentre la
sessione è in corso (file append-only di Claude Code) → l'hash cambierebbe e ri-archivierebbe come nuova.
Lo stem-filename è invariante per sessione. *`INSERT OR REPLACE`*: sovrascriverebbe il record esistente,
violando FR-014/015 («record esistente invariato»).

---

## D5 — Collocazione dell'archivio (sotto `<index_dir>/`, gitignored)

**Decisione.** L'archivio risiede in **`<index_dir>/memory.sqlite`** (es. `.sertor/.index/memory.sqlite`),
simmetrico a `observability.sqlite` ed `embed_cache.sqlite` — **già gitignored**.

**Conferma `.gitignore`.** Il file `.gitignore` (radice) ignora `**/.index/` e `**/.index-*/` (righe
21-25): qualsiasi `*.sqlite` sotto `index_dir` è **già escluso dal versionamento** senza nuove regole
(FR-011, SC-003 lato VCS). Verificato leggendo `.gitignore`. Nessuna modifica al `.gitignore` necessaria;
il plan lo annota come verifica esplicita.

**Namespacing per progetto (FR-010).** `index_dir` è già **per-progetto** (ancorato alla home runtime,
`config/settings.py:30-47` e `:198-204`): ospiti diversi hanno `index_dir` diversi → archivi separati. In
più, ogni record porta `project_id` (= `cwd`/identità del progetto fornita dall'adapter) come ulteriore
discriminante in tabella, così anche un eventuale `index_dir` condiviso non mescola progetti (FR-010,
US1 scenario 4). `project_id` è host-agnostico: lo fornisce l'adapter, non lo presume il servizio.

**Razionale.** Coerenza totale con gli artefatti runtime esistenti (cache embeddings, store
osservabilità): stesso `index_dir`, stesso pattern gitignore, stessa semantica «artefatto rigenerabile
locale». Il contenuto dei transcript (il dato più sensibile) non finisce **mai** sotto git per default
(Principio Sicurezza/segreti della costituzione).

**Alternative scartate.** *`.sertor/memory/` separato*: introdurrebbe una nuova convenzione di percorso e
una nuova regola gitignore senza beneficio; rompe la simmetria con gli altri due store. *Archivio fuori da
`index_dir`*: perderebbe il namespacing per-progetto già garantito da `index_dir`.

---

## D6 — Scrub del contenuto testuale libero (estensione della redazione esistente)

**Decisione.** Nuova **funzione pura** `scrub_text(text, extra_patterns) -> str` in
`src/sertor_core/observability/scrub.py`, separata e riusabile, che sostituisce con un segnaposto
(`«[REDACTED]»` / `***`) i pattern di segreto nel **contenuto testuale libero**. La redazione
**per-chiave** esistente (`redact()` in `observability/logging.py:33-35`) resta com'è: opera sui *campi*
strutturati degli eventi; la nuova `scrub_text` opera sul *testo*. Due responsabilità distinte, entrambe
applicate (FR-027: né nel contenuto né negli eventi compaiono segreti).

**Pattern coperti (FR-018), come regex pre-compilate:**
- **API key note**: `sk-…` (OpenAI), `AKIA[0-9A-Z]{16}` (AWS), e simili token con prefisso.
- **Bearer / Authorization**: `Authorization: Bearer <token>`, `Bearer <token>` inline.
- **`CHIAVE=VALORE`** dove il nome chiave contiene un hint di segreto
  (`key|token|secret|password|authorization`, riusando l'insieme `_SECRET_HINTS` di
  `observability/logging.py:18` per coerenza): es. `API_KEY=...`, `PASSWORD=...`.
- **Header di autorizzazione** inline.

**Pattern aggiuntivi configurabili (FR-020).** `Settings.memory_scrub_patterns: tuple[str, ...]` (default
vuoto), via `SERTOR_MEMORY_SCRUB_PATTERNS` (CSV come `SERTOR_EXCLUDE_PATTERNS`,
`config/settings.py:50-54`): regex extra per formati di segreto specifici del progetto, **senza** toccare
il corpo del core (Principio VIII/X).

**Ripiego conservativo (FR-019, US2 scenario 3).** Se l'applicazione di un pattern fallisce (regex error)
o un segmento è ambiguo (segreto a cavallo di un confine), `scrub_text` **redige l'intero segmento** ed
emette un warning (`memory_scrub_fallback`), senza interrompere l'archiviazione. La regola aurea: «mai
lasciar passare il dubbio» (Edge Case).

**Scrub mai bypassabile.** Lo scrub è applicato nel servizio di archiviazione **prima** della scrittura
nello store, su **ogni** turno; non c'è percorso che persista testo non-scrubbed. Gli eventi di
osservabilità della feature non includono `content` grezzo, solo la **dimensione post-scrub** (FR-023):
nessun segreto negli eventi (FR-027).

**Razionale.** Funzione **pura** → testabile offline con segreti sintetici (SC-004) senza store né
adapter. Separarla da `redact()` mantiene le due policy (per-campo vs per-testo) a singola responsabilità
(Principio III/VII). Riusare `_SECRET_HINTS` evita la duplicazione del vocabolario di segreto (DRY).

**Alternative scartate.** *Estendere `redact()` a fare anche lo scrub testuale*: mescola due
responsabilità (campi vs testo libero) e complica una funzione oggi piccola e chiara. *Scrub nello store*:
lo store deve restare un sink meccanico; la policy di redazione è del servizio (Humble Object, Principio
IX). *Scrub nell'adapter*: l'adapter è host-specifico; lo scrub è policy host-agnostica → deve stare nel
corpo (servizio), non nell'adapter.

---

## D7 — Manopole di configurazione (default solo in Settings)

**Decisione.** Quattro manopole nuove, default **solo** in `Settings` (`config/settings.py`), parsate in
`Settings.load()` come le esistenti:

| Campo Settings | Env | Default | Note |
|---|---|---|---|
| `memory_enabled` | `SERTOR_MEMORY` | `False` | privacy-by-default (FR-001/002); `_bool_env` |
| `memory_adapter` | `SERTOR_MEMORY_ADAPTER` | `"claude-code"` | selettore adapter (FR-005) |
| `memory_retention_days` | `SERTOR_MEMORY_RETENTION_DAYS` | `None` (nessuna scadenza) | solo gancio, registrato nei metadati (FR-021/022); `_int_or_none_env` (nuovo helper, gemello di `_float_or_none_env` a `settings.py:65-73`) |
| `memory_scrub_patterns` | `SERTOR_MEMORY_SCRUB_PATTERNS` | `()` | regex extra (FR-020); `_split_env` esistente |

**Razionale.** Principio VIII: default centralizzati, zero hardcoded nei componenti; le manopole seguono i
pattern già nel file (`_bool_env`, `_split_env`, `_float_or_none_env`). `memory_retention_days=None`
distingue «nessuna scadenza» da un `0` esplicito, come `retrieval_min_score` (`settings.py:65-73`).

---

## D8 — Wiring in composition (lazy, zero overhead a flag off)

**Decisione.** Tre `build_*` nuove in `composition.py`, tutte con **import lazy**:
- `build_capture_adapter(settings)` → costruisce l'adapter da `settings.memory_adapter`
  (`"claude-code"` → `ClaudeCodeCaptureAdapter`; valore ignoto → `ConfigError` con valori ammessi, come
  `_validated_engine` a `composition.py:16-23`).
- `build_memory_archive(settings)` → `MemoryArchive(settings.index_dir)`.
- `build_memory_archiver(settings)` → il **servizio** `MemoryArchiveService(adapter, archive, settings)`,
  costruito **solo se `settings.memory_enabled`** è vero; a flag off ritorna `None` (o non viene invocato
  dal consumatore), **nessun import dell'adapter, nessun file aperto** (FR-002, SC-003).

**Razionale.** Identico al gating di `enable_observability` (`composition.py:203-229`): se la manopola è
off, **nessun** handler/store è creato. Import lazy dentro le `build_*` (come tutte le altre): il modulo
`composition` non importa l'adapter Claude-Code al top-level → default-off = zero overhead, zero
dipendenze host-specifiche caricate (FR-002/003, Principio I/III).

---

## D9 — Osservabilità degli eventi (riuso `log_event`)

**Decisione.** Il servizio emette eventi strutturati via `log_event` (`observability/logging.py:38-45`):
- `memory_session_archived` (FR-023): `session_key`, `project_id`, `adapter_kind`, `content_size`
  (post-scrub), `is_new=True`, `turn_count`.
- `memory_session_skipped` (FR-024): `session_key`, `project_id`, `is_new=False`.
- `memory_capture_source_absent` (FR-006), `memory_capture_unparsable_line` (D3),
  `memory_scrub_fallback` (FR-019), `memory_archive_unavailable` (FR-025).

**Nessun segreto negli eventi (FR-027).** Gli eventi non portano `content`, solo `content_size` e
identificatori non sensibili; `redact()` per-campo è comunque applicato da `log_event` come ultima rete.

**Persistenza degli eventi (FUORI AMBITO, ma compatibile).** Se `SERTOR_OBSERVABILITY=true`, gli eventi di
questa feature finiscono **gratis** in `observability.sqlite` tramite l'`EventPersistenceHandler` già
attaccato (`composition.py:203-229`): nessun lavoro aggiuntivo qui. Indipendente da `SERTOR_MEMORY`.

---

## Sintesi delle decisioni

| # | Decisione | Pattern/codice riusato |
|---|---|---|
| D1 | Schema SQLite 2 tabelle (`sessions`+`turns`), ibrido | `observability/store.py`, `embeddings/cache.py` |
| D2 | 1 porta nuova (`TranscriptCaptureAdapter`); store concreto senza porta | `domain/ports.py` stile Protocol |
| D3 | Parser JSONL best-effort difensivo, host-specifico nell'adapter | ispezione file reali `~/.claude/projects/` |
| D4 | Idempotenza via stem-filename + `INSERT OR IGNORE` | `embeddings/cache.py:82` |
| D5 | `<index_dir>/memory.sqlite`, già gitignored, namespaced per progetto | `.gitignore:21-25`, `settings.py:198-204` |
| D6 | `scrub_text` pura separata da `redact()` per-chiave | `observability/logging.py:18,33` |
| D7 | 4 manopole, default solo in Settings | `config/settings.py` helper |
| D8 | 3 `build_*` lazy, gated su `memory_enabled` | `composition.py:203-229` |
| D9 | Eventi via `log_event`, no `content` negli eventi | `observability/logging.py:38` |

Nessun **NEEDS CLARIFICATION** residuo: le due decisioni utente (granularità ibrida DA-M-b, cattura
tutto-con-opt-in DA-M-c) sono già risolte nella spec; le restanti erano decisioni di design, qui chiuse.
