# Implementation Plan: Pagine ASP.NET nel corpus, con il codice lato server che contengono

**Branch**: `140-pagine-aspnet` | **Date**: 2026-10-12 | **Spec**: [`spec.md`](spec.md)

**Input**: Feature specification from `specs/140-pagine-aspnet/spec.md` · Deriva da **E7-FEAT-006**

## Summary

Le pagine ASP.NET (WebForms `.aspx .ascx .master .asmx .ashx`, Razor `.cshtml .razor`) entrano nel corpus
come codice. Per ciascuna si costruisce una **vista C# proiettata con le stesse righe del file** (il markup
diventa spazi, i blocchi di script e `@code` sono avvolti in una classe sentinella): il chunker e il grafo
esistenti la analizzano con la grammatica C# già in uso e producono simboli e righe del file originale **per
costruzione**, senza tabelle di rimappatura. Il markup, senza il codice, diventa chunk dimensionali
ricercabili. Le pagine non analizzabili (VB.NET, C# malformato) sono indicizzate come testo con un evento
`aspnet_page_degraded`. Tutte le scelte sono misurate su probe del parser reale ([`research.md`](research.md)).

## Technical Context

**Language/Version**: Python 3.11+ (come il core)

**Primary Dependencies**: `tree-sitter-language-pack` (già dipendenza del core, grammatica `csharp` già usata per i `.cs`); nessuna dipendenza nuova

**Storage**: N/A (corpus, store vettoriale e grafo invariati nel formato)

**Testing**: `pytest` — unit sulla proiezione e sul dispatch, integration su fixture con indicizzazione e grafo; embedder `hash` (nessuna rete)

**Target Platform**: la libreria `sertor-core` (Windows/macOS/Linux), consumata via CLI/MCP

**Project Type**: library (servizio del core) + nessuna modifica ai vehicles

**Performance Goals**: costo nullo sui corpora senza pagine; lineare nel numero di pagine (una proiezione e due parse per pagina)

**Constraints**: righe con scarto 0 (SC-002); nessuna degradazione silenziosa (SC-005); identità stabili (FR-014)

**Scale/Scope**: 1 modulo nuovo (`services/chunking/aspnet.py`, ~200 righe), ritocchi a `ingestion.py`, `dispatch.py`, `code.py`, `graph_extraction.py`, README; ~40 test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.6.0). Valutati **prima** e **dopo** il
design: l'esito non cambia.

- [x] **I — Dipendenze verso l'interno:** PASS. La proiezione è un servizio puro in `services/chunking/`; nessun
  SDK di provider, nessun import della CLI. Il parser tree-sitter è già usato nello stesso strato, con import
  lazy. Esercitabile con mock, senza rete.
- [x] **II — Boundary & local-first:** N/A. Nessuna dipendenza esterna nuova; tutto locale.
- [x] **III — YAGNI & unità piccole:** PASS. Un modulo nuovo; riuso di `code_chunks`, `size_chunks`,
  `_walk_relations`; nessuna astrazione nuova, nessuna porta nuova. Scartato un parser ASP.NET dedicato.
- [x] **IV — Errori espliciti:** PASS. `project_page` non solleva sui dati ma restituisce viste valide; la
  degradazione è una decisione esplicita con evento; nessun `None` silenzioso introdotto. L'unico `ValueError`
  è per un linguaggio non di pagina (errore di programmazione).
- [x] **V — Testabilità & misure:** PASS. Unit F.I.R.S.T. sulla proiezione (invariante delle righe su ogni
  costrutto), integration che asseriscono SC-001..SC-006 su fixture. Misura di qualità: SC-004 (top-5) e SC-002
  (scarto 0) come asserzioni numeriche; la suite di non-regressione esistente resta verde (SC-006).
- [x] **VI — Idempotenza & non-distruttività:** PASS. Proiezione deterministica, ordine di emissione fisso,
  id posizionali invariati nel meccanismo (research D-9); percorso incrementale identico.
- [x] **VII — Leggibilità:** PASS. Nomi di dominio (`project_page`, `PageProjection`, `chunk_view`,
  `markup_view`); scanner in funzioni piccole con guard clause.
- [x] **VIII — Configurazione centralizzata:** PASS. Nessuna manopola nuova: si riusano `chunk_size`,
  `chunk_overlap`, `max_chunk_tokens`, `graph_ambiguity` da `Settings`.
- [x] **IX — Osservabilità:** PASS. Evento `aspnet_page_degraded` (WARNING) via `log_event`; i conteggi
  dell'evento `ingest`/`index` includono le pagine senza modifiche.
- [x] **X — Host-agnostico:** PASS. Nessuna assunzione sull'ospite: il comportamento dipende dall'estensione e
  dal contenuto del file; nessun percorso, nessun nome di progetto.
- [x] **XI — Consumo via vehicles:** PASS. La verifica end-to-end ([`quickstart.md`](quickstart.md)) usa
  `sertor-rag index`/`search`/`graph-eval` e l'MCP; il core si importa solo nei test.
- [x] **XII — Fail Loud:** PASS. VB.NET e C# malformato → indicizzati come testo **con evento**. Unico punto
  best-effort dichiarato: un'espressione breve malformata non degrada la pagina ma può perdere un arco, come già
  avviene per gli archi di tutti i linguaggi (research D-6), ed è fissato da un test.
- [x] **XIII — Product vs Fixture Plane:** PASS. Il corpus del progetto non contiene pagine ASP.NET: la capacità
  si verifica su fixture **dichiarate come tali** (`tests/fixtures/aspnet/`), il dogfood verifica solo la
  non-regressione. Nessun workaround di fixture che copra un buco di prodotto.
- [x] **XIV — Derived State, Not Declared:** PASS. Tre fatti potevano duplicarsi e sono derivati: le costanti
  `webforms`/`razor` vivono nel modulo della proiezione e sono importate da ingestione e grafo; `_REL` delle due
  famiglie è **derivato** da `c_sharp`; handler e web service si riconoscono dalla **direttiva**, non da una
  seconda lista di estensioni. Il README è prosa che descrive `_EXT_LANG`: **riconciliatore** = test unitario
  che fallisce se un'estensione di `_EXT_LANG` manca dal README (research D-11).
- [x] **Allineamento alla missione:** PASS. Chiude un'omissione silenziosa che toglieva all'agente metà di un
  progetto ASP.NET: la pagina entra nello stesso corpus del code-behind e della documentazione, e la navigazione
  collega le due metà. È qualità del retrieval reso all'agente (recall, citazioni corrette).

## Project Structure

### Documentation (this feature)

```text
specs/140-pagine-aspnet/
├── spec.md              # specifica (con Clarifications 2026-10-12)
├── plan.md              # questo file
├── research.md          # D-1..D-11, misurate sul parser reale
├── data-model.md        # PageProjection, valori di linguaggio, chunk e grafo
├── quickstart.md        # verifica end-to-end via vehicles
├── contracts/
│   └── page-projection.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/sertor_core/
├── services/
│   ├── ingestion.py              # _EXT_LANG: +7 estensioni → webforms / razor
│   ├── chunking/
│   │   ├── aspnet.py             # NUOVO: project_page, PageProjection, page_raws, costanti
│   │   ├── code.py               # code_chunks: opzione reject_on_error (has_error)
│   │   └── dispatch.py           # chunk_document: ramo pagine (metadati per-raw)
│   └── graph_extraction.py       # _REL derivato; visita delle pagine (sentinella trasparente, chiamante = modulo)
└── README.md                     # sezione Languages corretta

tests/
├── fixtures/aspnet/              # NUOVO: pagine WebForms, Razor, handler, VB, malformata, BOM
├── unit/
│   ├── test_aspnet_projection.py # NUOVO: invariante righe, costrutti, Razor, direttive
│   ├── test_chunking_aspnet.py   # NUOVO: dispatch, qualname, degradazione + evento
│   ├── test_graph_aspnet.py      # NUOVO: simboli, calls, chiamante-modulo, coverage
│   └── test_readme_languages.py  # NUOVO: riconciliatore README ↔ _EXT_LANG
└── integration/
    └── test_aspnet_corpus.py     # NUOVO: SC-001..SC-006 su fixture via index reale
```

**Structure Decision**: progetto singolo (il core). La logica nuova sta in **un** modulo di servizio accanto ai
chunker esistenti; ingestione, dispatch e grafo ricevono ritocchi localizzati. Nessuna modifica a porte,
adapter, vehicles o installer (perimetro congelato non toccato).

## Tracciamento dello scope (regola 2 di CLAUDE.md)

| Rinvio | Casa durevole |
|---|---|
| REQ-014 — relazioni pagina ↔ code-behind / master / controlli | **E7-FEAT-007** promossa nel backlog di `ingestione-estesa` |
| VB.NET; JavaScript lato client | riga in roadmap → *Nuove funzionalità da discutere* |
| Dichiarare le estensioni scartate (la classe) | già **E10-FEAT-079** |
| Navigazione del grafo dalla CLI (oggi solo MCP / `graph-eval validate-ref`) | osservazione, non un rinvio di questa feature: annotata nel record |

## Installabilità (regola 1 di CLAUDE.md)

Capacità di sola libreria: viaggia con `sertor-core` e raggiunge gli ospiti con un rilascio. Nessun artefatto
host-facing nuovo (nessun hook, manopola `.env`, skill o blocco). La documentazione utente toccata è il README
del core (FR-016); `docs/` non elenca i linguaggi indicizzati, quindi non c'è altro da allineare.

## Complexity Tracking

Nessuna violazione da giustificare.
