---
title: FEAT-004 — Ricerca semantica sull'archivio episodico (implementazione SpecKit)
type: experiment
tags: [feat-004, memoria, ricerca-semantica, embedding, archive, incrementalità, chroma, bugfix]
created: 2026-06-22
updated: 2026-06-22 (bugfix post-merge metadata Chroma generici + test store reale)
sources: ["requirements/memoria-conversazioni/ricerca-semantica/requirements.md", "specs/072-ricerca-semantica-memoria/**", "src/sertor_core/services/memory_semantic.py", "src/sertor_core/adapters/vectorstores/chroma.py", "tests/unit/vectorstores/test_vectorstore.py", "tests/unit/services/test_memory_semantic.py"]
---

# FEAT-004 — Ricerca semantica sull'archivio episodico

**Epica:** [[memoria-conversazioni]] (Should priority).
**Branch:** `072-ricerca-semantica-memoria`.
**Timeline:** decomposizione 2026-06-22; speckit→implementazione 2026-06-22; test e Constitution Check passati.

## Problema

La ricerca episodica di FEAT-002 usa **full-text lessicale** (FTS5): trova per **parola esatta**. Ma una conversazione su «astensione dal consigliare» non contiene la parola «confidence», benché il concetto sia imparentato. La ricerca per **significato** colmerebbe la lacuna.

## Soluzione

Aggiungere un **tier semantico** all'archivio: indicizzazione embedding dei turni (contenuto testuale + metadati), ricercabili per **similarità vettoriale**. Riuso **puro** delle primitive di retrieval del core — nessun nuovo motore (Principio I/III).

### Design (forche risolte)

**(DA-SS-1) Architettura store:** store vettoriale **separato** dedicato alla memoria semantica, non mescolato con il corpus RAG documentale. Riuso delle primitive (`build_embedder`, `build_store`, `collection_name` namespaced), senza dipendenza da `IndexingService` né dal manifest FEAT-009.

**(DA-SS-2) Granularità:** **TURNO** (chunk_id = session_key#turn_index). Ogni turno è un documento vettorializzato; la sessione contiene N turni. Così la ricerca ritorna turni specifici con contesto di sessione, non interi archivi.

**(DA-SS-3) Superficie:** **modo separato opt-in** via flag `--semantic` su `memory search` (il default resta full-text FTS5). Nessun fallback silenzioso né query duale; l'utente sceglie consapevolmente.

**(DA-SS-4) Incrementalità (il punto cardine):** l'archivio è **append-only** (sessioni mai modificate post-archiviazione). L'indicizzazione embedda **SOLO i turni nuovi**, mai l'intero archivio. **Marker:** lo stato del vector store — un turno è «già indicizzato» ⇔ il chunk_id è presente nella collezione (nessun registro separato, nessun manifest nuovo). **Gap chiuso:** aggiunto `ChromaStore.contains_ids(ids: list[str]) → list[str]` (capability opzionale duck-typed, non sulla porta — Principio III): permette il backfill incrementale anche su Chroma locale, non solo nei test su mock.

**(DA-SS-5) Privacy-by-default stratificato:** `SERTOR_MEMORY=true` (opt-in generale) **AND** `SERTOR_MEMORY_SEMANTIC=false` (default, opt-in separato). Con provider locale (FEAT-011 glove), l'intero percorso è on-machine.

## Implementazione

**Nuovo servizio:** `src/sertor_core/services/memory_semantic.py` espone:

- `MemorySemanticIndex` (manager): metodi `search(query, top_k)`, `index_session(session_key, turns)`, `index_all()`.
- Entità nuove: `SemanticMemoryQuery`, `SemanticMemoryHit`, `SemanticResults`, `SemanticIndexReport`.
- Errore di dominio `SemanticMemoryUnavailableError` (azionabile, REQ-013).

**Auto-index non-fatale:** a fine sessione via aggancio in `services/memory_archive.archive_all()` — solo sessioni appena archiviate (idempotente, non tutto l'archivio ogni volta).

**Osservabilità:** due eventi metrics-only:
- `memory_semantic_search`: query HASHATA (privacy), results_count, provider, latency.
- `memory_semantic_index`: session_key, turni_nuovi, turni_totali_collezione, provider, latency.

**Factory:** `build_memory_semantic_index(settings) → MemorySemanticIndex | None` — ritorna `None` se `SERTOR_MEMORY_SEMANTIC` spento, sollevando `SemanticMemoryUnavailableError` se cliente chiama senza opt-in.

## Risultati

- **998 test non-cloud passed:** +48 nuovi (46 della feature + 2 per `contains_ids`).
- **1 xfailed noto:** FEAT-010 pip (pre-esistente).
- **ruff clean:** src + test.
- **Constitution Check:** 12/12 PASS (pre e post-design).
- **sertor-core invariato:** fuori dai punti di seam citati (composition.py, settings, services/memory_semantic, adapters se necessario).

## Gap e debito

**Debito P2 (corollario installabile):** le manopole `SERTOR_MEMORY_SEMANTIC*` non sono ancora nei template `.env` dell'installer `sertor` (env.local.tmpl, env.azure.tmpl). Follow-up di FEAT-009 (distribuzione memoria via installer).

**Documento:** il requisito esatto in `requirements/memoria-conversazioni/ricerca-semantica/requirements.md` (29 REQ, 8 NFR, 6 DA risolte).

## Bugfix post-merge: metadata generici nello store

**Scoperto in dogfooding (2026-06-22, commit 0f51bf7):** il comando `sertor-rag memory index-semantic` sull'archivio episodico reale falliva su **tutti i 5067 turni** con errore di metadati. **Causa-radice:** la funzione `ChromaStore._clean_metadata` indirizzava una **ALLOW-LIST hardcoded** di chiavi metadata — specifiche del **corpus documentale** (path, doc_type, chunker) — scartando completamente il payload della memoria (session_key, turn_index, captured_at, role). Chroma rifiutava `{}` (nessun metadata) → loss di dati silenzioso.

**Rimedio:** `_clean_metadata` ora **DERIVA i metadata dal payload**, non da una lista fissa. Mantiene ogni scalare e unisce le sequenze con "/", escludendo solo `text` (il documento). Il payload del corpus è un **sottinsieme esatto** dei nuovi metadata → comportamento corpus **preservato**; i metadata della memoria ora round-trippano intatti.

**Lezione critica:** i 46 test della feature passavano silenziosamente perché lo store FINTO (`InMemoryStore`) rispecchiava il lato **lettura** (`_to_results`) ma non il lato **scrittura** (`_clean_metadata`). Un mock fedele a **metà del contratto** nasconde i guasti. Rimedio codificato: 2 **test di regressione sullo store REALE** `ChromaStore` — (1) round-trip metadata in `test_vectorstore.py`; (2) flow end-to-end `index_session + search` in `test_memory_semantic.py`. **Principio:** testare il componente reale, non solo un fake che imita un lato del contratto. Memoria semantica ora completamente operativa; 1000 test non-cloud verdi.

## Lezioni codificate

1. **Incrementalità append-only:** per archivi che non si modificano, il marker di indicizzazione è lo stato dello store (collezione), non un registro separato. Permette re-index deterministico senza gestione esterna.
2. **Capability opzionale duck-typed:** `ChromaStore.contains_ids` aggiunta come metodo opzionale (non sulla porta), non richiede refactor della porta `VectorStore` (Principio III).
3. **Privacy stratificato:** ogni nuovo percorso embedding ha il suo gate, non fida la composabilità del precedente.

## Pagine collegate

- [[memoria-conversazioni]] — anchor concettuale (sezione tier semantico aggiunta).
- [[ricerca-episodica-fts5]] — il tier lessicale che precede.
- [[ports-adapters]] — architecture, dove il nuovo store semantico si integra.
- [[hybrid-retrieval]] — il motore ibrido cui la semantica episodica si ispira.
