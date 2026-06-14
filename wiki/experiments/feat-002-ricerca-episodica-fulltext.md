---
title: FEAT-002 Ricerca episodica — Query full-text locale sui transcript
type: experiment
tags: [FEAT-002, memoria-conversazioni, ricerca, full-text, fts5, episodico, speckit]
created: 2026-06-14
updated: 2026-06-14
sources: ["specs/033-ricerca-episodica/spec.md", "src/sertor_core/services/episodic_search.py", "src/sertor_core/domain/errors.py", "requirements/memoria-conversazioni/epic.md"]
---

# FEAT-002 — Ricerca episodica full-text locale

**Merger**: PR [merging today], commit [commit hash da aggiungere post-merge], 2026-06-14  
**Stato**: ✅ In produzione su master

## Cosa è stato costruito

**Il secondo tier della memoria conversazioni**: rende interrogabile l'archivio dei transcript di FEAT-001 mediante una ricerca **full-text lessicale locale**, senza embedding né rete. Domande come "ne avevamo già parlato di X?" e "com'è finita quella cosa tre settimane fa?" trovano risposta cercando in turni archiviati.

### Architettura — ricerca FTS5 nativa sulla granularità di turno

- **Servizio `EpisodicSearch`** (`services/episodic_search.py`, ~180 righe): ricerca della memoria episodica sull'archivio conservato da FEAT-001. Input: query testuale + vincoli opzionali (finestra temporale, ordinamento, limite, lunghezza snippet). Output: lista ordinata di turni corrispondenti citati con sessione padre, timestamp, ruolo, indice, snippet di contesto e score di pertinenza.

- **Indice FTS5 nativo SQLite**: tabella virtuale esterna `turns_fts` su `turns.content` (del database di FEAT-001), ranking `bm25()`, snippet `snippet()` per il contesto. Mantenuta automatica da **trigger di sync** su `INSERT` nella tabella `turns` e da `rebuild()` di recovery (idempotenza). Freschezza per costruzione: nuove sessioni di FEAT-001 sono ricercabili alla ricerca successiva.

- **Entità risultato**: 
  - `SearchQuery` (query testuale, since/until opzionali, limit, snippet_tokens, order_by)
  - `EpisodicHit` (session_key, captured_at, role, turn_index, snippet, score)
  - `EpisodicResults` (hits + latency_ms)
  - `InvalidTimeWindowError` (since > until)
  
  Tutte in `services/episodic_search.py`.

- **Privacy by design**: nessun embedding, nessun LLM, nessuna rete nel percorso di query → il contenuto non lascia mai la macchina. Evento osservabilità `episodic_search` registra la **query hashata** (sha256[:16]), mai il testo in chiaro.

- **Robustezza**: archivio assente/vuoto/non-indicizzabile → stato vuoto + warning (mai errore). Riga malformata → skip + warning. Since > until → `InvalidTimeWindowError` esplicito. Fallimento di osservabilità non-fatale.

### Configurazione e wiring

- **3 manopole in `Settings`**: 
  - `SERTOR_EPISODIC_LIMIT` (default 20) — massimo numero di risultati.
  - `SERTOR_EPISODIC_SNIPPET_TOKENS` (default 12) — lunghezza dello snippet di contesto.
  - (implicito) `SERTOR_MEMORY` deve essere attivo per che l'archivio esista; ricerca assente se archivio non esiste.

- **Wiring in `composition.py`**: `build_episodic_search(settings)` riceve solo `index_dir` (host-agnostico), costruisce lo store e il servizio. Riesportato da `__init__.py`.

### Testabilità e qualità

- **Test**: 27 nuovi test, tutti verdi (`test_episodic_search.py` + fixture `episodic_memory_fixture` con archivio sintetico in tmp_path).
- **Offline**: tutta la logica è testabile senza rete, senza assistente attivo, senza corpus reale.
- **Constitution Check**: ✅ PASS 10/10 senza deroghe (host-agnostico verificato, no embedding, no rete, Principio X + I).

## Prova live

Eseguita su dogfood di produzione (36 sessioni arrivate / 5062 turni archiviati da FEAT-001):

- Query «Langfuse» → trovato il turno reale della domanda di 6 ore fa nella sessione attuale, score 9.57, ~78ms.
- Query «GraphRAG» → trovati 4 turni in sessioni diverse, ordinati per pertinenza (decrescente) e recency.
- Query «Textual/rank» → trovati turni storici e di oggi corrispondenti al pattern (regex FTS5 non supportata, ma substring match funziona come atteso).
- Finestra temporale: query «hardening» limitata agli ultimi 2 giorni → 8 turni su 35 globali, nel range corretto.

**MVP funziona end-to-end**: cattura (FEAT-001) → archivio persistente → ricerca locale → risultati citabili nel contesto dell'agente.

## Specifiche conseguite

Tutti i 21 FR + 8 SC implementati e testati:

- **FR-001/002/008**: Query testuale con risultati ordinati per pertinenza (BM25 FTS5) + citazione completa per ogni turno.
- **FR-003**: Query offline, nessuna rete prodotta.
- **FR-004/014**: Archivio assente/vuoto → stato vuoto + warning, mai errore.
- **FR-005/006/007**: Finestra temporale opzionale (since/until), `since > until` → errore esplicito.
- **FR-009/010/011**: Ordinamento recency-first opzionale, limite configurabile, snippet di lunghezza configurabile.
- **FR-012/013**: Risultati leggibili dalla macchina (session_key, captured_at, turn_index strutturati); voce malformata → skip + warning, continuare.
- **FR-015/016**: Zero assunzioni sull'host; testato con >1 archivio mock.
- **FR-017/018**: Evento `episodic_search` (query hashata, filtri, risultati, latenza); fallimento osservabilità non-fatale.
- **FR-019/020**: Indice FTS5 non-distruttivo (derivato, ricostruibile); nuove sessioni ricercabili alla ricerca successiva via trigger.
- **FR-021**: Ricerca/restituzione a granularità di turno con riferimento a sessione padre.

## Nodo centrale: MVP memoria interrogabile

La memoria episodica era un archivio inerte senza questa feature. Con FEAT-002:

- **Ritrovare il contesto**: «ne avevamo già parlato?» → ricerca → turni + sessioni → link al contesto grezzo.
- **Finestra temporale**: memoria vaga («tre settimane fa») → vincolo temporale → risultati ristretti.
- **Base per distillazione**: FEAT-003 attingerà da questo archivio ricercabile per migliorare il wiki.

## Prossimo

- **FEAT-003** (distillazione): userà l'archivio ricercabile come fonte grezza per pompare conoscenza nel wiki.
- **FEAT-004** (ricerca semantica): estensione opt-in con embedding per query semantiche (fuori ambito MVP).
- **FEAT-005** (remember-this): marcatura esplicita di turni importanti per prioritizzare nella ricerca.
- **FEAT-006** (retention): governance e scadenza controllata dell'archivio.

---

## Pagine collegate

- [[memoria-conversazioni]] — concetto (il tier episodico come parte della memoria, perché, pattern Hermes)
- [[feat-001-memoria-cattura-archiviazione]] — la sorgente dati (FEAT-001, prerequisito).
- [[ricerca-episodica-fts5]] — tech (il motore FTS5, indice trigger-synced, semantica della ricerca).
- [[memoria-negli-agenti]] — explainer (aggiornato: cattura + ricerca).
- [[diary-vs-graph]] — come la memoria episodica si relaziona al wiki.
