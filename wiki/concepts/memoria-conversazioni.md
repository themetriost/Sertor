---
title: Memoria episodica — Cattura delle conversazioni (il tier grezzo)
type: concept
tags: [memoria, episodico, conversazioni, hermes, tier-grezzo, archive, host-agnostico, feat-001]
created: 2026-06-14
updated: 2026-06-14 (+ FEAT-035 superficie CLI + hook SessionEnd, MVP completo)
sources: ["requirements/memoria-conversazioni/epic.md", "src/sertor_core/domain/memory.py", "https://github.com/nous-research/hermesresearch"]
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

## Tre livelli di memoria

Il progetto ospite ha adesso **tre tier** di memoria cumulativi (non esclusivi):

1. **Episodico (grezzo)** — FEAT-001: archivio conservato di sessioni `<index_dir>/memory.sqlite`, catturatrici a grana di turno per ricerca futura.
2. **Ricerca episodica** — FEAT-002: query full-text locale su (1), senza embedding, per domande-nel-passato.
3. **Grafo** — wiki + corpus + knowledge-graph: le pagine-entità, il wiki distillato, la base del [[retrieval-core]].

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
- ✅ **FEAT-002 (Ricerca episodica)**: implementata (PR [oggi], 2026-06-14). Ricerca FTS5 nativa SQLite, turni interrogabili, full-text lessicale, privacy (offline), robustezza.
- ✅ **FEAT-035 (Superficie CLI + hook SessionEnd)**: implementata (2026-06-14). MVP COMPLETO: comandi `sertor-rag memory search` / `archive` (thin-consumer) + hook SessionEnd (cattura automatica a fine sessione). Privacy-by-default (disattivato se `SERTOR_MEMORY` non è configurato); hook non-bloccante.
- ✅ **FEAT-003 (Aggancio alla distillazione)**: implementata (PR #51, 2026-06-14). Comandi `sertor-rag memory show <key>` (transcript intero) / `memory list` (sessioni recenti) → la modalità «from conversation» di `distill` ([[diary-vs-graph]]) attinge all'archivio invece di un brief a mano: **loop cattura→distillazione chiuso**. Thin consumer additivo (riuso `MemoryArchive.get` + `list_recent`, nessuna nuova porta). **Vincolo FR-013:** sempre sessione mirata su invocazione esplicita, mai automatica/intero archivio.
- 📋 **FEAT-004/005/006/008**: estensioni (ricerca semantica, remember-this, retention, multi-assistente).

---

## Pagine collegate

- [[feat-001-memoria-cattura-archiviazione]] — record della feature (cattura & archivio).
- [[feat-002-ricerca-episodica-fulltext]] — record della feature (ricerca episodica).
- [[feat-035-superficie-cli-memoria-hook-sessionend]] — record del completamento MVP (superficie CLI + hook).
- [[transcript-capture-adapter-e-storage]] — le componenti tecniche (porta + adapter + store).
- [[ricerca-episodica-fts5]] — il motore FTS5 SQLite.
- [[diary-vs-graph]] — come la memoria episodica si relaziona al grafo wiki.
- [[second-brain-cross-progetto]] — visione meta: memoria su più progetti e assistenti.
- [[constitution]] — Principio X (host-agnosticità) alla base della porta.
