---
title: Memoria episodica — Cattura delle conversazioni (il tier grezzo)
type: concept
tags: [memoria, episodico, conversazioni, hermes, tier-grezzo, archive, host-agnostico, feat-001, feat-008]
created: 2026-06-14
updated: 2026-07-23
sources: ["requirements/memoria-conversazioni/epic.md", "requirements/memoria-conversazioni/cattura-copilot-cli/requirements.md", "src/sertor_core/domain/memory.py", "src/sertor_core/adapters/capture/copilot_cli.py", "https://github.com/nous-research/hermesresearch"]
---

# Memoria episodica — il tier grezzo delle conversazioni

Nel [[diary-vs-graph|modello a due memorie]] del wiki, il wiki stesso è il grafo aggiornabile in place: le pagine-entità si evolvono, le pagine-concetto distillano. Ma il grafo è **lossy**: quello che non entra nel wiki scompare.

Questo concetto descrive il **tier episodico** che cattura il grezzo prima che si distilli: l'archivio **conservato** di tutte le conversazioni dell'agente con il progetto, la fonte da cui la distillazione attinge, e la base su cui una ricerca full-text locale può ragionare **senza** embedding (privacy + robustezza).

## Il problema: perdita di conversazione

Oggi una sessione di lavoro con l'agente è effimera: la conversazione avviene, genera decisioni e codice, ma il transcript scompare quando la finestra si chiude. Ciò che rimane nel wiki è una distillazione manuale o automatica. Il problema:

1. **Conversazioni non archiviate** → impossibile tornare al contesto grezzo se una decisione va ripresa.
2. **Ricerca episodica assente** → non si sa dove una domanda è stata già posta o risolta, si ricomincia da zero.
3. **Fonte grezza persa** → la distillazione è one-way; non si può ottenere più dettagli dal grezzo perché il grezzo è sparito.
4. **Prova/audit** → nessuna traccia immutabile di cosa è stato discusso, deciso, perché.

## La soluzione: archivio episodico conservato

Catturare **tutte** le sessioni in un archivio locale persistente (SQLite, per-progetto, gitignored). L'archivio è:

- **Grezzo**: conserva il transcript così come è stato generato, strutturato in turni ma non distillato.
- **Conservato**: non si cancella automaticamente, no rotazione. Si conserva indefinitamente (o con una retention policy opzionale).
- **Ricercabile**: structured query locale (full-text lessicale, non embedding) senza dover ri-elaborare il grezzo.
- **Privacy-by-default**: disattivato per default; attivazione esplicita via manopola. Segreti ripuliti prima di persistere.
- **Host-agnostico**: la cattura è dietro un adapter (`TranscriptCaptureAdapter`), swappabile per ospiti diversi. Primo: Claude Code che legge i file di sessione locali.
- **Non-bloccante**: se il store fallisce, l'operazione principale dell'agente non si interrompe (degradazione onesta).

## Tre livelli di memoria (+ semantico opzionale)

Il progetto ospite ha adesso **tre tier** di memoria cumulativi (non esclusivi), più un **tier semantico** opzionale:

1. **Episodico (grezzo)** — FEAT-001: archivio conservato di sessioni `<index_dir>/memory.sqlite`, catturatrici a grana di turno per ricerca futura.
2. **Ricerca episodica (full-text)** — FEAT-002: query full-text locale su (1) via FTS5 SQLite, senza embedding, per domande-nel-passato («ne avevamo parlato?»). Default.
3. **Ricerca episodica (semantica)** — FEAT-004: **opt-in separato**, embedding dei turni in store vettoriale dedicato, ricerca per **significato** non per parola esatta. Riuso pure RAG (build_embedder/store), provider locale (FEAT-011). Auto-indexa a fine sessione (idempotente, append-only). Privacy stratificato: `SERTOR_MEMORY_SEMANTIC=true` **and** provider configurato.
4. **Grafo** — wiki + corpus + knowledge-graph: le pagine-entità, il wiki distillato, la base del [[retrieval-core]].

La [[diary-vs-graph|memoria diaria del wiki]] (log + record datati) entra nel grafo quando la conoscenza si cristallizza; il grezzo dell'episodico non entra mai a meno che (a) la distillazione non lo pompi dentro il wiki, o (b) la ricerca episodica lo faccia emergere per il contesto.

## Pattern Hermes

Il design è ispirato a **Hermes (Nous Research)** — una architettura multi-assistente in cui ogni assistente archivia i propri transcript e il sistema conosce come recuperarli. Nel nostro caso: un solo assistente (Claude Code), ma la porta è astratta e consente agenti futuri.

Mappa Hermes ↔ Sertor:
- `session-archive` (Hermes) = `memory.sqlite` (Sertor) + `MemoryArchive` store.
- `.jsonl` di sessione (Hermes) = frammenti letti dall'adapter `TranscriptCaptureAdapter`, che li incolla nel nostro schema.
- `MEMORY.md` (Hermes, skill registry) ≈ `.claude/` (Sertor, governance) — dove registrare metadati di conversazione.

## Granularità ibrida (decisione FEAT-001)

La domanda: a che grana si archivia?

- **Per turno**: granularità fine, idempotenza per turno, ma risbiadendo le sessioni si creano record per ogni turno.
- **Per sessione**: unità naturale di conversazione, idempotenza per sessione (una chiave canonica per ripetibilità), ma la ricerca futura deve sapere dove finiscono i turni.

**Decisione**: **granularità ibrida** — l'unità *archiviata* è la **sessione intera** (per idempotenza), l'archivio conserva però i **confini dei turni** dentro il record (due tabelle: `sessions` + `turns`, con FK), così la ricerca di FEAT-002 può indicizzare a grana di turno senza ri-elaborare il grezzo.

## Privacy per design

Privacy-by-default: cattura disattivata salvo opt-in esplicito.

Quando attiva, il contenuto dei transcript è sottoposto a **scrub**: segreti (chiavi API, token, password) sono sostituiti con segnalatori prima di persistere. La redazione è:

- **Sui pattern noti**: `sk-…` (OpenAI), `AKIA…` (AWS), `bearer …`, `KEY=VALUE` con nome-chiave che contiene hint di segreto.
- **Conservativa su fallimento**: se un pattern non è riconosciuto, l'intero segmento è redatto.
- **Configurabile**: pattern aggiuntivi possono essere registrati per segreti specifici del progetto.

Nessun segreto entra mai in chiaro nell'archivio né negli eventi di osservabilità.

## Host-agnosticità (Principio X)

La **cattura è host-specifica** per definizione: ogni assistente persiste le sessioni diversamente.

Ciò che è **generico** (archiviazione, scrub, idempotenza) è nel core, dietro contratti astratti. La 8ª porta `TranscriptCaptureAdapter` + l'adapter Claude-Code è il meccanismo di disaccoppiamento:

- Il core non conosce Claude Code, non importa i suoi file direttamente.
- La sorgente dei transcript è selezionata **esclusivamente via configurazione** (`SERTOR_MEMORY_ADAPTER`).
- Futuri adattatori (e.g. per Cline, Aider, LangSmith) non toccheranno il core.

Verificato in test: logica di archivio e contratto di cattura passano con ≥2 adapter simulati, senza rami condizionali sull'identità dell'host.

## Stato

- ✅ **FEAT-001 (Cattura & archiviazione)**: implementata (PR #45, 2026-06-14). Store SQLite, adapter Claude-Code, scrub, privacy-by-default, host-agnostico.
- ✅ **FEAT-002 (Ricerca episodica full-text)**: implementata (2026-06-14). Ricerca FTS5 nativa SQLite, turni interrogabili, full-text lessicale, privacy (offline), robustezza. DEFAULT di FEAT-004.
- ✅ **FEAT-035 (Superficie CLI + hook SessionEnd)**: implementata (2026-06-14). MVP COMPLETO: comandi `sertor-rag memory search` / `archive` (thin-consumer) + hook SessionEnd (cattura automatica a fine sessione). Privacy-by-default (disattivato se `SERTOR_MEMORY` non è configurato); hook non-bloccante.
- ✅ **FEAT-003 (Aggancio alla distillazione)**: implementata (PR #51, 2026-06-14). Comandi `sertor-rag memory show <key>` (transcript intero) / `memory list` (sessioni recenti) → la modalità «from conversation» di `distill` ([[diary-vs-graph]]) attinge all'archivio invece di un brief a mano: **loop cattura→distillazione chiuso**. Thin consumer additivo (riuso `MemoryArchive.get` + `list_recent`, nessuna nuova porta). **Vincolo FR-013:** sempre sessione mirata su invocazione esplicita, mai automatica/intero archivio.
- ✅ **FEAT-004 (Ricerca episodica semantica)**: implementata (branch 072, 2026-06-22). Opt-in separato via `memory search --semantic`, store vettoriale dedicato, indicizzazione incrementale append-only (marker = collezione ChromaStore). Gap chiuso: aggiunto `contains_ids` per backfill Chroma. Privacy stratificato: `SERTOR_MEMORY_SEMANTIC=true` + provider locale. 998 test verdi, Constitution 12/12. Vedi [[feat-004-ricerca-semantica-memoria]].
- ✅ **FEAT-008 (Cattura transcript Copilot CLI)**: implementata (branch 073, 2026-06-22). Secondo adapter `CopilotCliTranscriptAdapter` dietro porta `TranscriptCaptureAdapter` — legge `events.jsonl` da `~/.copilot/session-state/`, identico parser Copilot CLI. Associazione progetto via `cwd`/`gitRoot` in session.start. Privacy offline (niente cloud-sync). 1039 test verdi, Constitution 12/12. Gap dichiarato: manopole `SERTOR_MEMORY_ADAPTER=copilot-cli` + `SERTOR_MEMORY_COPILOT_SESSION_DIR` non ancora nei template `.env` installer (FEAT-009 P2). Vedi [[feat-008-cattura-copilot-cli]].
- ✅ **FEAT-010 (Parità MCP per la lettura della memoria)**: consegnata (PR #208, 2026-07-20). 3 tool read-only nel server `sertor-rag`: `memory_search` (full-text FTS5), `memory_list`, `memory_show` — thin sopra gli stessi servizi core della CLI (`MemoryArchive.list_recent`/`get`, `EpisodicSearch.search`), gated da `SERTOR_MEMORY` (spenta → `{"status":"disabled"}` esplicito). Memoria interrogabile nativamente dall'agente, non solo da terminale. `sertor-core` invariato (solo `sertor_mcp`).
- ✅ **FEAT-012 (Fix cattura-auto — gate privacy sull'ambiente sbagliato)**: consegnata (PR #210, 2026-07-21). L'hook `memory-capture` (SessionEnd) gata su `os.environ["SERTOR_MEMORY"]`, ma il valore vive in `.sertor/.env` → gate sempre `None` → cattura mai eseguita. `_hooklib.memory_enabled()` ora legge `./.env`→`.sertor/.env` (ancorato a `CLAUDE_PROJECT_DIR`, `.env` vince su `os.environ`), byte-copiato Claude/Copilot. `sertor-core` invariato (solo asset hook).
- ✅ **FEAT-013 (Ricerca semantica della memoria via MCP)**: consegnata (PR #212, 2026-07-21). Il tool MCP `memory_search` accetta `semantic=true` (ricerca per significato), mirror di `sertor-rag memory search --semantic`, dietro il doppio gate `SERTOR_MEMORY` + `SERTOR_MEMORY_SEMANTIC`. Chiude il residuo «semantico via MCP» rinviato da FEAT-010. `sertor-core` invariato (solo `sertor_mcp`).
- ✅ **FEAT-014 (Fix FTS5 punteggiatura in `memory search`)**: consegnata (2026-07-21). Il testo grezzo andava nel `MATCH` FTS5 senza quoting → un token tipo `0.1.1` causava `fts5: syntax error` mascherato a `(no results)` (anti-Fail-Loud). Funzione pura `_to_fts_match` (quoting per-token, AND preservato) a monte di `_build_sql`; colpiva CLI + tool MCP `memory_search`.
- 📋 **FEAT-005/006/007**: estensioni (remember-this, retention, second-brain).

---

## Pagine collegate

- [[feat-001-memoria-cattura-archiviazione]] — record della feature (cattura & archivio).
- [[feat-002-ricerca-episodica-fulltext]] — record della feature (ricerca episodica full-text).
- [[feat-004-ricerca-semantica-memoria]] — record della feature (ricerca semantica).
- [[feat-008-cattura-copilot-cli]] — record della feature (adapter Copilot CLI, multi-assistente).
- [[feat-035-superficie-cli-memoria-hook-sessionend]] — record del completamento MVP (superficie CLI + hook).
- [[transcript-capture-adapter-e-storage]] — le componenti tecniche (porta + adapter + store).
- [[ricerca-episodica-fts5]] — il motore FTS5 SQLite.
- [[copilot-cli-session-storage]] — ricognizione tecnica storage sessioni Copilot CLI (FEAT-008).
- [[diary-vs-graph]] — come la memoria episodica si relaziona al grafo wiki.
- [[second-brain-cross-progetto]] — visione meta: memoria su più progetti e assistenti.
- [[constitution]] — Principio X (host-agnosticità) alla base della porta.
