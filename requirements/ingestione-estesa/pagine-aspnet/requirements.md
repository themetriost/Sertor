# Requisiti — Pagine ASP.NET nel corpus (WebForms + Razor, con il C# inline)
<!-- Deriva da: E7-FEAT-006 (requirements/ingestione-estesa/epic.md) -->

> Livello: **feature** dell'epica [`ingestione-estesa`](../epic.md). Decisioni utente del 2026-10-12:
> **estensioni** = famiglia WebForms + Razor · **profondità** = estrazione del C# inline (non solo
> chunking dimensionale) · **processo** = SpecKit completo.

## 1. Contesto e problema (perché)

Un progetto ASP.NET distribuisce la propria logica fra **due posti**: il code-behind (`Pagina.aspx.cs`)
e il **codice lato server scritto dentro le pagine** — blocchi `<script runat="server">` ed espressioni
`<% %>` in WebForms, blocchi `@code` / `@functions` / `@{ }` in Razor/Blazor. Le pagine portano anche il
markup, cioè la struttura dell'interfaccia: quali controlli, quali binding, quale master page.

Oggi Sertor **non vede nessuna delle due metà**. L'ingestione indicizza solo le estensioni di una
allowlist chiusa (`_EXT_LANG`, `src/sertor_core/services/ingestion.py:21-36`), in cui non compare
nessuna estensione ASP.NET: `.aspx`, `.ascx`, `.master`, `.asmx`, `.ashx`, `.cshtml`, `.razor` vengono
**scartate in silenzio** (`discover_files`, riga 92-93). Il code-behind `.aspx.cs` entra invece come C#,
perché l'ultima estensione è `.cs`. Il risultato è un corpus che mostra all'agente il code-behind
**senza la pagina che lo usa**, e che risponde «non c'è» a domande su metodi che esistono, scritti
inline. È l'istanza ASP.NET di [[omissione-che-diventa-risposta]].

Due fatti del codice attuale vincolano la feature:
- il chunker sintattico (`services/chunking/code.py`, `code_chunks`) fa il parsing tree-sitter dell'**intero
  testo** del documento: su un file misto markup + C# il parser C# non produce simboli affidabili;
- l'estrazione del grafo (`services/graph_extraction.py`) fa lo stesso: per i linguaggi in `_REL` analizza
  `doc.text` per intero, e dichiara la copertura per linguaggio in `COVERAGE`.

**Drift collegato:** `src/sertor_core/README.md:131` afferma che *«any other language falls back without
error»*. È falso: le estensioni fuori allowlist non arrivano al chunker.

## 2. Obiettivi e criteri di successo

- **SC-1 (copertura dei file):** su una fixture con almeno un file per ciascuna delle 7 estensioni,
  **7/7** file entrano nel corpus come documenti di codice, con id = path relativo POSIX.
- **SC-2 (simboli inline):** un metodo definito dentro un blocco di codice lato server di una pagina è
  restituito da `find_symbol` con **path della pagina** e **riga di inizio uguale a quella reale nel file
  originale** (scarto 0), per ciascuna delle due famiglie (WebForms, Razor).
- **SC-3 (navigazione):** `who_calls` su un metodo del code-behind restituisce la pagina che lo invoca da
  un blocco di codice lato server (quando il nome non supera la soglia di ambiguità esistente).
- **SC-4 (markup ricercabile):** una ricerca su un testo presente **solo nel markup** (es. l'ID di un
  controllo) restituisce la pagina fra i primi k risultati di `search_code` su una fixture dedicata.
- **SC-5 (niente silenzi):** una pagina il cui codice inline non è analizzabile (C# malformato o pagina in
  VB.NET) è comunque indicizzata, e produce **un evento osservabile** che nomina il file e il motivo:
  0 casi di degradazione silenziosa sulla fixture di prova.
- **SC-6 (non regressione):** l'indicizzazione dei linguaggi già supportati resta identica (suite
  esistente verde, nessun cambiamento negli id o nei chunk dei file non ASP.NET).

## 3. Stakeholder e attori

- **Ospite con un progetto ASP.NET** (WebForms legacy o MVC/Razor/Blazor): vuole che l'agente veda la
  pagina insieme al suo codice.
- **L'agente consumatore** (via MCP/CLI): usa `search_code`, `find_symbol`, `who_calls`, `get_context`.
- **Il core** (ingestione → chunk → embed → store, code-graph): la pipeline che la feature estende.

## 4. Ambito

### In ambito
- Ingestione delle estensioni **WebForms** `.aspx`, `.ascx`, `.master`, `.asmx`, `.ashx` e **Razor**
  `.cshtml`, `.razor`.
- Estrazione del **codice C# lato server** contenuto nelle pagine:
  - WebForms: blocchi `<script runat="server">…</script>`; blocchi di codice `<% … %>`; espressioni
    `<%= … %>`, `<%: … %>`, `<%# … %>`;
  - Razor: blocchi `@code { … }`, `@functions { … }`, `@{ … }`.
- Simboli (classi, metodi, funzioni) definiti nel C# estratto, con **numeri di riga del file originale**.
- Archi `calls` dal C# estratto verso il resto del corpus, con la stessa regola di ambiguità esistente.
- Markup delle pagine **ricercabile** come testo.
- **Dichiarazione della copertura** delle nuove famiglie nel code-graph, come per gli altri linguaggi.
- Correzione del drift in `src/sertor_core/README.md` e aggiornamento della documentazione utente che
  descrive cosa entra nel corpus.

### Fuori ambito
- **VB.NET**, inline o code-behind (`Language="VB"`, `.aspx.vb`, `.vbhtml`): la pagina entra come markup,
  senza estrazione; l'evento lo dichiara (REQ-011). Un eventuale supporto VB è una voce separata.
- **JavaScript lato client** nei blocchi `<script>` senza `runat="server"`: resta testo del markup.
- **Espressioni Razor inline** (`@Model.Nome`, `@Html.Partial(...)`) fuori dai blocchi elencati: restano
  testo, non producono archi.
- **Relazioni fra pagine** (master ↔ content page, `<%@ Register %>` dei controlli, `@inherits`/`@model`):
  vedi REQ-014 (*Could*), altrimenti backlog.
- **La classe generale** «l'ingestione dichiara ciò che scarta» per qualunque estensione: è
  **E10-FEAT-079**. Questa feature chiude il caso ASP.NET, non la classe.

## 5. Requisiti funzionali (EARS)

**Ingestione**
- **REQ-001 (Ubiquitous):** *The ingestion shall include files with the extensions `.aspx`, `.ascx`,
  `.master`, `.asmx`, `.ashx`, `.cshtml` and `.razor` in the corpus as code documents, with the POSIX
  relative path as stable id.*
- **REQ-002 (Ubiquitous):** *The ingestion shall record, for each such document, a language identity that
  distinguishes the WebForms family from the Razor family.*
- **REQ-003 (Ubiquitous):** *The ingestion shall keep indexing a code-behind file (e.g. `Page.aspx.cs`) as
  C#, unchanged by this feature.*

**Estrazione del codice lato server**
- **REQ-004 (Event-driven):** *When a WebForms document is chunked, the system shall extract the C# contained
  in `<script runat="server">` blocks, `<% %>` code blocks and `<%= %>`, `<%: %>`, `<%# %>` expressions.*
- **REQ-005 (Event-driven):** *When a Razor document is chunked, the system shall extract the C# contained in
  `@code`, `@functions` and `@{ }` blocks.*
- **REQ-006 (Ubiquitous):** *The system shall report, for every symbol and chunk derived from extracted C#,
  line numbers that refer to the original page file.*

**Simboli e grafo**
- **REQ-007 (Ubiquitous):** *The system shall expose classes, methods and functions defined in extracted C#
  as code-graph symbols whose path is the page file.*
- **REQ-008 (Ubiquitous):** *The system shall derive `calls` edges from extracted C# to symbols of the corpus,
  applying the existing name-ambiguity threshold.*
- **REQ-009 (Ubiquitous):** *The system shall declare, in the code-graph coverage declaration, which relations
  are supported for the WebForms and Razor families.*

**Markup e degradazione dichiarata**
- **REQ-010 (Ubiquitous):** *The system shall make the markup of every page searchable, so that text found
  only outside server-side code blocks can be retrieved.*
- **REQ-011 (Unwanted):** *If a page declares a server-side language other than C#, then the system shall
  index the page as markup only and emit an observable event naming the file and the declared language.*
- **REQ-012 (Unwanted):** *If the extracted C# of a page cannot be parsed, then the system shall index the page
  with size-based chunking and emit an observable event naming the file and the reason.*
- **REQ-013 (Unwanted):** *If a page contains no server-side code block, then the system shall index it as
  markup without emitting an error.*

**Relazioni fra file (opzionale)**
- **REQ-014 (Optional):** *Where a page declares its code-behind or base class (WebForms `CodeBehind`/`Inherits`
  attributes, Razor `@inherits`), the system shall relate the page to that class in the code-graph.*

**Proprietà della pipeline**
- **REQ-015 (Ubiquitous):** *The system shall produce identical chunks, ids and graph for the same page content
  across rebuilds, in both the full and the incremental indexing paths.*

## 6. Requisiti non funzionali

- **NFR-1 (dipendenze):** nessuna nuova dipendenza obbligatoria del core oltre a quelle già presenti
  (Principio III); l'analisi del C# riusa il supporto già esistente.
- **NFR-2 (osservabilità):** gli eventi di REQ-011/REQ-012 passano dallo strato di osservabilità esistente
  (`log_event`), così finiscono in telemetria come gli altri eventi d'ingestione.
- **NFR-3 (prestazioni):** su un corpus senza file ASP.NET il tempo d'indicizzazione non cambia in modo
  misurabile; su un corpus con pagine il costo aggiuntivo è proporzionale al numero di pagine.
- **NFR-4 (installabilità):** la capacità viaggia con il pacchetto `sertor-core`; nessun artefatto
  host-facing nuovo da cablare nell'installer (perimetro congelato). Raggiunge gli ospiti con un rilascio.
- **NFR-5 (codifica):** i file con BOM UTF-8 sono letti senza che il BOM alteri il primo simbolo o i numeri
  di riga.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo — Clean Architecture:** la logica resta nei servizi del core (ingestione, chunking, estrazione del
  grafo); nessun SDK nel dominio; i consumatori (CLI/MCP) non cambiano.
- **Vincolo — accesso via vehicles** (Principio XI): la verifica sul dogfood si fa con `sertor-rag index` e
  l'MCP, non importando il core.
- **Assunzione A-1:** la grande maggioranza delle pagine reali è in C#; VB.NET resta fuori (REQ-011).
- **Assunzione A-2:** il C# inline di WebForms contiene tipicamente **metodi senza classe che li racchiuda**
  (sono membri della classe generata dalla pagina); la loro identità nel grafo deve comunque essere stabile.
- **Dipendenza:** la grammatica C# già usata per `.cs`.
- **Relazione con altre voci:** E10-FEAT-079 (la classe dei silenzi d'ingestione), E10-FEAT-080 (il terzo
  stato d'assenza nella navigazione), E7-FEAT-005 (Rust: stesso varco nell'allowlist).

## 8. Rischi

- **R-1 — Frammenti non autonomi:** un'espressione `<%= %>` o un `@{ }` non è un'unità sintattica completa;
  analizzarla isolata può fallire o produrre alberi errati. Mitigazione: REQ-012 (degradazione dichiarata)
  e fixture con i casi reali.
- **R-2 — Numeri di riga sbagliati:** l'estrazione sposta il codice; un errore di mappatura rende false le
  citazioni e `find_symbol`. È il rischio più grave per la qualità resa all'agente → SC-2 con scarto 0.
- **R-3 — Doppio conteggio:** lo stesso codice presente sia nei chunk del markup sia in quelli del C#
  estratto può duplicare i risultati. Da decidere in design; la deduplicazione a query-time esistente
  (E5-FEAT-003) è una rete, non la soluzione.
- **R-4 — Collisione di simboli:** più pagine definiscono `Page_Load`; nomi molto ripetuti superano la soglia
  d'ambiguità e non generano archi. È il comportamento voluto (precisione > richiamo), ma va dichiarato.
- **R-5 — Sintassi Razor ambigua:** `@` è anche testo (email, `@@`); il riconoscimento dei blocchi deve
  evitare falsi positivi.

## 9. Prioritizzazione (MoSCoW)

| Requisito | Priorità |
|---|---|
| REQ-001, 002, 003, 010, 013, 015 | **Must** — la pagina entra nel corpus e resta coerente |
| REQ-004, 005, 006, 007, 011, 012 | **Must** — è la scelta dell'utente: il C# inline, con righe vere e senza silenzi |
| REQ-008, 009 | **Should** — navigazione e copertura dichiarata |
| REQ-014 | **Could** — relazione pagina ↔ code-behind |

## 10. Domande aperte

- **DA-1 — Doppio conteggio (R-3):** il C# estratto va **escluso** dai chunk del markup, o i due flussi
  restano sovrapposti? [DA CHIARIRE in clarify]
- **DA-2 — Espressioni `<%= %>` / `<%# %>`:** contano solo per gli archi `calls`, o diventano anche chunk
  propri? Proposta: solo archi.
- **DA-3 — Identità dei metodi WebForms senza classe (A-2):** qualname = `<NomeFile>.<Metodo>`, oppure la
  classe dichiarata da `Inherits`? [DA CHIARIRE in clarify; legata a REQ-014]
- **DA-4 — JS lato client:** indicizzare i `<script>` client come JavaScript sintattico? Proposta: no in
  questa feature; voce di backlog se serve.
