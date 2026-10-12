---
description: "Task list — Pagine ASP.NET nel corpus (140)"
---

# Tasks: Pagine ASP.NET nel corpus, con il codice lato server che contengono

**Input**: Design documents from `specs/140-pagine-aspnet/`

**Prerequisites**: [`plan.md`](plan.md), [`spec.md`](spec.md), [`research.md`](research.md), [`data-model.md`](data-model.md), [`contracts/page-projection.md`](contracts/page-projection.md), [`quickstart.md`](quickstart.md)

**Tests**: richiesti. La spec fissa criteri numerici (SC-001..SC-006) e la costituzione (Principio V) non
considera «done» una capacità senza misura. I test si scrivono **prima** dell'implementazione di ogni storia
e devono **fallire** prima di passare.

**Organization**: per user story; la Fase 2 (proiezione) è il fondamento di tutte.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizzabile (file diversi, nessuna dipendenza da task incompleti)
- **[Story]**: US1..US5 della spec

---

## Phase 1: Setup

**Purpose**: fixture condivise da tutte le storie (piano-fixture dichiarato, Principio XIII).

- [ ] T001 Creare le fixture in `tests/fixtures/aspnet/`: `Default.aspx` (direttiva C#, controllo `OrdiniGrid`, `<script runat="server">` con `Page_Load` alla riga 5 e `Helper` alla riga 9, un secondo blocco script più in basso con `Secondo`, `<% foreach %>` su più blocchi, `<%= FormatTitolo() %>`, `<%# Eval("Nome") %>`, `<%-- commento --%>`), `Default.aspx.cs` (classe `Demo.Default` con `BindGrid`, `FormatTitolo`, `Secondo` assente), `Menu.ascx` (solo markup), `Site.master` (solo markup + un `<% %>`), `Api.asmx` e `Handler.ashx` (direttiva `WebService`/`WebHandler` + classe C#), `Index.cshtml` (`@{ }` con una riga di markup interna, `@functions`, email `info@esempio.it`, `@@`), `Counter.razor` (`@code` con `IncrementCount` e `count++`), `Vecchia.aspx` (`<%@ Page Language="VB" %>`), `Rotta.aspx` (script C# malformato), `Bom.aspx` (con BOM UTF-8 e un metodo a riga nota). Annotare in un `README.md` della cartella le righe attese di ogni simbolo.

---

## Phase 2: Foundational — la proiezione (blocca tutte le storie)

**Purpose**: `project_page` e `PageProjection` ([contratto](contracts/page-projection.md)), puri e deterministici.

- [ ] T002 [P] Test dell'invariante delle righe in `tests/unit/test_aspnet_projection.py`: per ogni fixture di T001, `chunk_view`, `graph_view` e `markup_view` hanno lo stesso numero di `\n` del testo; `project_page` con un linguaggio non di pagina solleva `ValueError`.
- [ ] T003 [P] Test dei costrutti WebForms in `tests/unit/test_aspnet_projection.py`, una riga per ciascuna voce della tabella WebForms del contratto (direttiva, commento server, script, `<% %>`, `<%= %>`/`<%: %>`/`<%# %>`/`<%#: %>`, `<%$ %>`, markup, handler `WebHandler`/`WebService`), più `server_language` letto dalla direttiva `Page`/`Control`/`Master` e dall'attributo `language` del tag script; `has_code=False` su `Menu.ascx`.
- [ ] T004 [P] Test dei costrutti Razor in `tests/unit/test_aspnet_projection.py`: `@code`/`@functions` avvolti, `@{ }` con la riga di markup interna sbiancata in `chunk_view` e conservata in `markup_view`, `@* *@`, `@@`, email, graffe dentro stringhe (`"}"`, `@"}"`, `'}'`) e commenti (`// }`, `/* } */`) che non chiudono il blocco.
- [ ] T005 Creare `src/sertor_core/services/chunking/aspnet.py` con le costanti `WEBFORMS = "webforms"`, `RAZOR = "razor"`, `PAGE_LANGUAGES`, `PAGE_SENTINEL = "__page__"`, il dataclass frozen `PageProjection` (campi del [data-model](data-model.md)) e `project_page(text, language)` che delega a uno scanner per famiglia (research D-1, D-2, D-3, D-5).
- [ ] T006 Implementare lo scanner WebForms in `src/sertor_core/services/chunking/aspnet.py`: una passata sui token `<%…%>` e sui tag `<script … runat="server">…</script>` (case-insensitive), con una funzione di sbiancamento che sostituisce ogni carattere non `\n` con uno spazio; direttiva `WebHandler`/`WebService` → tutto dopo la direttiva è codice (research D-3); estrazione di `server_language` (default `C#`).
- [ ] T007 Implementare lo scanner Razor in `src/sertor_core/services/chunking/aspnet.py`: riconoscimento della transizione `@` (non dopo un alfanumerico, non `@@`), blocchi `@code`/`@functions`/`@{` chiusi alla graffa bilanciata ignorando stringhe e commenti C#, commenti `@* *@`, righe di markup interne ai `@{ }` (primo carattere non spazio `<` + lettera o `/`, oppure `@:`) sbiancate in `chunk_view`/`graph_view` e lasciate in `markup_view` (research D-4).
- [ ] T008 Verificare che T002–T004 passino (`uv run pytest tests/unit/test_aspnet_projection.py`) e che `uv run ruff check src/sertor_core/services/chunking/aspnet.py` sia pulito.

**Checkpoint**: la proiezione è corretta e verificata in isolamento.

---

## Phase 3: User Story 1 — Le pagine entrano nel corpus e il loro testo si trova (P1) 🎯 MVP

**Goal**: le 7 estensioni sono ingerite come codice; il markup è ricercabile; le pagine senza codice non danno errori; il code-behind resta invariato.

**Independent Test**: indicizzare `tests/fixtures/aspnet/` e cercare `OrdiniGrid`.

- [ ] T009 [P] [US1] Test d'ingestione in `tests/unit/test_ingestion.py` (o nuovo `tests/unit/test_ingestion_aspnet.py`): le 7 estensioni producono `Document` con `doc_type=CODE` e `language` `webforms`/`razor`; `Default.aspx.cs` resta `c_sharp` (FR-001..FR-003).
- [ ] T010 [P] [US1] Test del dispatch in `tests/unit/test_chunking_aspnet.py`: per `Menu.ascx` (senza codice) solo chunk `SIZE_FALLBACK` della `markup_view`, nessun evento (FR-013); per `Default.aspx` i chunk del markup contengono `OrdiniGrid` e **non** contengono il corpo di `Page_Load` (FR-010, clarify Q1); `language` dei chunk = quello della pagina.
- [ ] T011 [US1] Aggiungere le 7 estensioni a `_EXT_LANG` in `src/sertor_core/services/ingestion.py`, importando `WEBFORMS`/`RAZOR` da `services/chunking/aspnet.py` (research D-8, Principio XIV).
- [ ] T012 [US1] Ristrutturare `chunk_document` in `src/sertor_core/services/chunking/dispatch.py` perché ogni raw porti la propria funzione di metadati (coppie `(raw, meta_of)`), senza cambiare l'output per i linguaggi esistenti; aggiungere il ramo `doc.language in PAGE_LANGUAGES` che, per ora, emette i chunk dimensionali della `markup_view`.
- [ ] T013 [US1] Verificare T009–T010 e la non-regressione del chunking esistente (`uv run pytest tests/unit -k "chunk or ingest"`).

**Checkpoint**: le pagine sono nel corpus e il markup si trova. MVP consegnabile.

---

## Phase 4: User Story 2 — I metodi scritti nelle pagine si trovano, alla riga giusta (P1)

**Goal**: simboli del codice inline con righe del file originale (scarto 0) e qualname `Stem.Metodo`.

**Independent Test**: chunk sintattici di `Default.aspx`, `Counter.razor`, `Bom.aspx` con righe uguali a quelle annotate in T001.

- [ ] T014 [P] [US2] Test in `tests/unit/test_chunking_aspnet.py`: `Default.aspx` produce chunk `SYNTACTIC` con `qualname` `Default.Page_Load`, `Default.Helper`, `Default.Secondo` e `start_line` uguali alle righe reali (incluso il secondo blocco); `Counter.razor` → `Counter.IncrementCount`; `Handler.ashx` → qualname della classe dichiarata **senza** prefisso (FR-007a); `Bom.aspx` → riga invariata dal BOM; nessun chunk ha `symbol == "__page__"` e nessun testo di chunk contiene `__page__`; i chunk sintattici precedono quelli del markup (research D-9).
- [ ] T015 [P] [US2] Test in `tests/unit/test_chunking_code.py`: `code_chunks(..., reject_on_error=True)` restituisce `None` su C# con errori e i chunk su C# valido; senza l'opzione il comportamento esistente è invariato.
- [ ] T016 [US2] Aggiungere il parametro keyword `reject_on_error: bool = False` a `code_chunks` in `src/sertor_core/services/chunking/code.py` (`root.has_error()` → `None`).
- [ ] T017 [US2] Implementare in `src/sertor_core/services/chunking/aspnet.py` la funzione che dai raw sintattici della `chunk_view` rimuove il chunk della classe sentinella, riscrive il prefisso `__page__.` in `<Stem>.` (nome del file senza **tutte** le estensioni) e cancella il testo della sentinella dai chunk.
- [ ] T018 [US2] Collegare nel ramo pagine di `src/sertor_core/services/chunking/dispatch.py`: chunk sintattici della `chunk_view` (grammatica `c_sharp`, `reject_on_error=True`, metadati `SYNTACTIC` con `language` della pagina) **seguiti** dai chunk della `markup_view`.
- [ ] T019 [US2] Verificare T014–T015.

**Checkpoint**: definizioni inline trovabili alla riga giusta.

---

## Phase 5: User Story 4 — Ciò che non si può analizzare si dichiara (P1)

**Goal**: VB.NET e C# malformato → indicizzati come testo, con evento `aspnet_page_degraded`.

**Independent Test**: `Vecchia.aspx` e `Rotta.aspx` producono chunk e un evento ciascuna.

- [ ] T020 [P] [US4] Test in `tests/unit/test_chunking_aspnet.py` (con `caplog`): `Vecchia.aspx` → chunk `SIZE_FALLBACK` sull'**intero** testo + un evento `aspnet_page_degraded` con `reason=server_language`, `path`, `detail="VB"`; `Rotta.aspx` → idem con `reason=parse_error` e `detail` = riga del primo errore; nessun evento per `Default.aspx` e `Menu.ascx`; nessun simbolo per le pagine degradate.
- [ ] T021 [US4] Implementare la decisione di degradazione e l'evento (WARNING, via `log_event`) nel ramo pagine di `src/sertor_core/services/chunking/dispatch.py` o in una funzione di `aspnet.py` da esso chiamata (research D-6); la decisione deve essere riusabile dal grafo senza emettere un secondo evento.
- [ ] T022 [US4] Verificare T020.

**Checkpoint**: nessuna degradazione silenziosa.

---

## Phase 6: User Story 3 — Chi chiama cosa, fra pagine e code-behind (P2)

**Goal**: archi `calls` dal codice della pagina (blocchi ed espressioni); chiamante = simbolo racchiudente o modulo della pagina.

**Independent Test**: grafo di `tests/fixtures/aspnet/`: `who_calls("BindGrid")` contiene `Default.Page_Load`, `who_calls("FormatTitolo")` contiene il modulo `Default.aspx`.

- [ ] T023 [P] [US3] Test in `tests/unit/test_graph_aspnet.py` su `extract_graph` con documenti e chunk delle fixture: nodi simbolo `Default.aspx::Default.Page_Load` con riga reale, nessun nodo `__page__`; arco `calls` `Page_Load → BindGrid`; arco `calls` dal nodo modulo `Default.aspx` verso `FormatTitolo` (espressione `<%= %>`) e verso un metodo invocato in `<% %>`; nessun arco dalle pagine degradate; un'espressione breve malformata non elimina gli altri archi della pagina (research D-6); i linguaggi esistenti non producono archi dal modulo (FR-015).
- [ ] T024 [US3] In `src/sertor_core/services/graph_extraction.py`: per i documenti `webforms`/`razor`, ricalcolare la proiezione e la decisione di degradazione (T021), analizzare la `graph_view` con la grammatica C#, e visitare con una funzione dedicata che rende trasparente la classe sentinella (prefisso `Stem`, nessun nodo) e parte con `enclosing_id = doc.path`; `_walk_relations` resta invariato per gli altri linguaggi.
- [ ] T025 [US3] Test d'integrazione dell'adapter in `tests/unit/test_graph_aspnet.py`: costruire il grafo `networkx` dalle fixture e verificare che `who_calls("FormatTitolo")` restituisca un hit con `path="Default.aspx"` e `kind="module"`; annotare il `ref` effettivo e correggere di conseguenza la riga corrispondente di [`quickstart.md`](quickstart.md).
- [ ] T026 [US3] Verificare T023, T025 e la non-regressione del grafo (`uv run pytest tests -k graph`).

**Checkpoint**: navigazione fra pagina e code-behind.

---

## Phase 7: User Story 5 — La copertura è dichiarata (P2)

**Goal**: `COVERAGE` dichiara `webforms` e `razor`, derivati da `c_sharp`.

- [ ] T027 [P] [US5] Test in `tests/unit/test_graph_aspnet.py`: `COVERAGE["webforms"] == COVERAGE["razor"] == COVERAGE["c_sharp"]` e il `GraphData.coverage` di un estratto contiene le due voci.
- [ ] T028 [US5] In `src/sertor_core/services/graph_extraction.py` derivare `_REL[WEBFORMS]` e `_REL[RAZOR]` da `_REL["c_sharp"]` (nessuna copia letterale, research D-8).
- [ ] T029 [US5] Verificare T027.

---

## Phase 8: Polish & cross-cutting

- [ ] T030 [P] Test d'integrazione `tests/integration/test_aspnet_corpus.py`: indicizzare `tests/fixtures/aspnet/` con embedder `hash` e motore di default in una cartella temporanea; asserire SC-001 (7/7 estensioni nel corpus), SC-002 (righe con scarto 0 via grafo), SC-003 (`who_calls` restituisce la pagina), SC-004 (`OrdiniGrid` nei primi 5 di `search_code`), SC-005 (2/2 pagine degradate nel corpus, 2/2 eventi), FR-014 (seconda indicizzazione incrementale senza modifiche: 0 aggiunti/aggiornati; dopo una modifica a una sola pagina: 1 aggiornato).
- [ ] T031 [P] Riconciliatore README in `tests/unit/test_readme_languages.py`: fallisce se un'estensione di `_EXT_LANG` non compare in `src/sertor_core/README.md` (research D-11, Principio XIV).
- [ ] T032 Correggere la sezione *Languages supported* di `src/sertor_core/README.md`: elencare le famiglie WebForms (`.aspx .ascx .master .asmx .ashx`) e Razor (`.cshtml .razor`) con il comportamento (C# lato server estratto, markup ricercabile, VB dichiarato come testo); sostituire «any other language falls back without error» con la verità (le estensioni fuori elenco non entrano nel corpus, E10-FEAT-079) e verificare T031 (FR-016).
- [ ] T033 Aggiornare i docstring di modulo toccati (`ingestion.py`: «files with unrecognised extensions are silently ignored» resta vero ma va citato E10-FEAT-079; `code.py`, `dispatch.py`, `graph_extraction.py`: menzione delle pagine).
- [ ] T034 Eseguire [`quickstart.md`](quickstart.md) alla lettera via vehicles (`sertor-rag index`/`search`/`graph-eval validate-ref`) e correggere il file dove l'esecuzione reale differisce.
- [ ] T035 Gate pre-merge: `uv run pytest -m "not cloud"`, le suite di `packages/*` lanciate a parte, `uv run ruff check .` — tutto verde.
- [ ] T036 Verifica sul dogfood (non-regressione, SC-006): `uv run --project .sertor sertor-rag index .` dopo il re-lock, e smoke MCP (`search_code`, `search_docs`, `find_symbol` su un simbolo a riga nota).

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T008)** → tutte le storie.
- **US1 (T009–T013)** dopo la Fase 2. È l'MVP.
- **US2 (T014–T019)** dopo US1 (usa il ramo pagine del dispatch, T012).
- **US4 (T020–T022)** dopo US2 (la degradazione per `parse_error` usa `reject_on_error`, T016).
- **US3 (T023–T026)** dopo US4 (riusa la decisione di degradazione, T021).
- **US5 (T027–T029)** indipendente dalle altre storie; può procedere dopo la Fase 2, in parallelo a US1.
- **Polish (T030–T036)** dopo tutte le storie; T031 e T032 possono procedere appena T011 è fatto.

## Parallel Opportunities

- Fase 2: T002, T003, T004 (stesso file di test, sezioni distinte: scrivibili in parallelo da chi lavora a mano, in sequenza da un solo agente).
- US1: T009 ∥ T010. US2: T014 ∥ T015. US5 ∥ US1.
- Polish: T030 ∥ T031.

## Implementation Strategy

1. **MVP = Fase 1 + Fase 2 + US1**: le pagine sono nel corpus e il loro testo si trova. Già chiude il silenzio
   dell'allowlist per ASP.NET.
2. **+ US2 + US4**: la scelta dell'utente (C# inline, righe esatte) e la regola *fail loud*. Insieme sono il
   cuore P1: vanno consegnate insieme, perché US2 senza US4 degraderebbe in silenzio le pagine malformate.
3. **+ US3 + US5**: navigazione e copertura dichiarata.
4. **Polish**: integrazione end-to-end, README e riconciliatore, quickstart eseguito, gate pre-merge.
