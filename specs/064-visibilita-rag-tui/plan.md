# Implementation Plan: Visibilità del RAG nella TUI (dimostrabilità) — FEAT-015

**Branch**: `064-visibilita-rag-tui` · **Requirements**:
`requirements/osservabilita/visibilita-rag-tui/requirements.md` (FEAT-015, epica `osservabilita`;
realizza l'opt-in raw-text REQ-E9).

## Summary

Nuovo **opt-in di contenuto** (default off) che, quando attivo, fa portare agli eventi di retrieval il
**testo della query**, una **preview dei risultati** (top-k path+score) e uno **snippet del 1°**
(tutti **scrubbati**), e fa includere agli eventi MCP l'**argomento query**. Una nuova **scheda TUI
"RAG"** legge questi eventi e mostra, per ricerca recente: query · risultato · verdetto **hit / miss /
astenuto**, più le operazioni MCP. Scopo = **dimostrare** come funziona il RAG. Additivo: default
privacy-safe **invariato**; lo store/eventi/F2/TUI esistenti non cambiano comportamento da spenti;
l'export OTel resta **metrics-only** (l'handler già scarta il testo libero). Thin consumer; host-agnostico.

## Forche di design risolte
- **D1 — correlazione query↔risultato↔verdetto:** l'evento di retrieval diventa **self-contained**
  quando il content è on (porta `query`+`results_preview`+`snippet`+`abstained`) → **nessuna
  correlazione cross-evento** per la terna query/risultato/verdetto. *(Risolve REQ-007 per il nucleo.)*
- **D2 — correlazione con l'operazione MCP:** in v1 **non** un id di correlazione: l'evento
  `mcp.<tool>` porta il proprio argomento query (sotto opt-in) ed è mostrato come riga propria; il
  legame MCP↔retrieval è per **adiacenza/tempo**, non hard-linkato (id di correlazione = follow-up).
- **D3 — manopola:** `Settings.observability_content_enabled` ← **`SERTOR_OBSERVABILITY_CONTENT`**
  (default False); **efficace solo se** `observability_enabled` (lo store) è on. Il contenuto vive negli
  **eventi esistenti** (campi JSON), nessuna nuova tabella; retention by-count = Should (gancio DA-O-b).
- **D4 — verdetto 3 stati:** derivato da campi dell'evento: `hit` se `results>0`; altrimenti `astenuto`
  se `abstained` (la soglia `min_score` ha svuotato), `miss` se 0 senza astensione. `abstained` (bool,
  **non** contenuto) si aggiunge **sempre** all'evento retrieve (cheap, safe).

## Constitution Check (pre-design) — **PASS 11/11, nessuna deroga**
- **I (core libreria):** modifiche nel core (retrieval/observability/composition); la TUI resta consumer. ✅
- **II (boundary/local-first):** nessun provider nuovo; contenuto locale, zero rete. ✅
- **III (YAGNI):** riuso `scrub_text` (già esistente) + eventi/store esistenti; nessuna nuova entità/porta. ✅
- **IV (errori espliciti):** nessun null silenzioso; lo scrub degrada conservativo (già). ✅
- **V (testabilità da misure):** render puri (verdetto/preview) testabili offline; SC misurabili. ✅
- **VI (idempotenza/non-distruttività):** additivo; default off = comportamento identico a oggi. ✅
- **VII (leggibilità):** la feature *aumenta* la leggibilità del pannello; codice piccolo, puro. ✅
- **VIII (config centralizzata):** unica manopola in `Settings` (+ retention opzionale). ✅
- **IX (osservabilità):** è osservabilità; segreti **scrubbati** dal contenuto (no segreti mai). ✅
- **X (host-agnostico):** opt-in via config; **default privacy-safe ovunque**, relax solo locale esplicito. ✅
- **XI (vehicles):** il content flag è cablato nel composition root; consumo via TUI/CLI/MCP. ✅

## Phase 1 — Design

**Settings (`config/settings.py`):** `observability_content_enabled: bool = False` ←
`SERTOR_OBSERVABILITY_CONTENT`. Semantica: contenuto catturato **solo** se
`observability_enabled and observability_content_enabled`.

**Cattura del contenuto (retrieval):**
- `services/retrieval.py` e l'engine ibrido (`engines/hybrid`, evento `hybrid_query`): l'evento di
  retrieval aggiunge **sempre** `abstained: bool`; e, **solo se content on**, `query` (via
  `scrub_text`), `results_preview` (lista compatta dei top-k `path|score`, **path non è segreto**),
  `snippet` (testo del 1° risultato, `scrub_text` + troncato a una soglia breve).
- Il flag arriva al servizio/engine **dal composition root** (`build_facade`/`build_engine` leggono
  `Settings`), non hardcodato (Principio VIII/XI).
- I path dei risultati non sono contenuto sensibile (sono già visibili a chi ha il repo); lo `snippet`
  è l'unico testo di contenuto → scrub + troncamento.

**Cattura MCP (`sertor_mcp`):** se content on, gli eventi `mcp.<tool>` includono l'**argomento query**
(scrubbato). Default off: nessun argomento (come oggi).

**Modello + resa TUI (puri, in `observability/live.py`):**
- estendere il modello con i **content events** recenti (query, verdetto, preview, snippet) +
  le **mcp ops** recenti (tool, query) — letti dallo store via F2 (`recent_events`/query_events).
- `verdict(event) -> "hit"|"miss"|"abstained"` (puro, da `results`/`abstained`).
- `render_rag_report(...)` → testo della **scheda "RAG"** (tabella: TIME · VERDICT · QUERY · TOP RESULT;
  + sezione operazioni MCP). Empty-state onesto quando il content è off / nessun evento.

**Guscio Textual (`observability/tui.py`):** nuova `TabPane("RAG", id="tab-rag")` con uno `Static`
aggiornato da `render_rag_report`; la scheda "Live" resta metriche-only.

**Export OTel:** **nessuna modifica** — l'`OtelExportHandler` esporta solo numerici/bool + whitelist
categorica; `query`/`snippet`/`results_preview` (stringhe non-whitelist/liste) sono **scartati**
automaticamente → l'export resta metrics-only (NFR-03). Aggiungere un test che lo **pinna**.

**Privacy/gate:** default off ovunque (REQ-012); `scrub_text` sul contenuto (REQ-003); il content
richiede lo store (D3). Su ospite terzo nulla cambia di default.

**Contratti:** nessuna API runtime nuova; le "guardie" sono i test (verdetto, gate off→no content,
scrub, OTel resta metrics-only).

## Phase 2 — Fasi di implementazione (mappate alle US/REQ)
1. **Gate + abstained:** `Settings.observability_content_enabled`; aggiungere `abstained` agli eventi
   retrieve (sempre). Test: flag off → nessun `query`/`snippet`; `abstained` presente.
2. **Cattura contenuto (REQ-001/003/005-009):** retrieval/engine includono query+preview+snippet
   (scrubbati) sotto flag; threading dal composition. Test: flag on → campi presenti & scrubbati.
3. **MCP query arg (REQ-006):** evento `mcp.<tool>` con query sotto flag. Test off/on.
4. **TUI "RAG" (REQ-005/010):** `verdict` + `render_rag_report` (puri) + `TabPane`. Test render
   (3 stati, preview, empty-state) — offline, senza terminale.
5. **Guardie privacy:** test gate-off→no content (REQ-002); OTel resta metrics-only (no query/snippet
   negli span); scrub segreti (REQ-003). Manopola nei template `.env` dell'installer (installabile).
6. **Non-regressione + bookkeeping:** suite osservabilità/retrieval verdi; ruff; record/roadmap; PR.

## Constitution Check (post-design) — **PASS 11/11**
Additivo, default off (privacy-by-default preservata), riuso di `scrub_text`/eventi/store, nessuna nuova
porta/entità, export OTel intatto (metrics-only). Nessuna complessità da tracciare.

## Complexity Tracking
Nessuna deviazione. Rischi non costituzionali: (R-2) segreti nel testo → `scrub_text` + troncamento;
(R-3) crescita store col contenuto → retention by-count (Should) / contenuto bounded; correlazione
MCP↔retrieval hard = follow-up dichiarato.
