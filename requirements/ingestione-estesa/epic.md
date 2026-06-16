# Epica — Ingestione estesa (fonti e linguaggi oltre il testo locale)

> Livello: **epica** — **estensione dell'epica primaria** [`../sertor-core/epic.md`](../sertor-core/epic.md).
> Allarga **cosa** Sertor sa ingerire oltre il filesystem testuale locale dell'MVP (FEAT-001 core):
> repository **remoti**, formati **non-testo**, **linguaggi** oggi a fallback, progetti **senza codice**.
> Promuove e dà casa durevole alla **FEAT-010 del core** (era «da decomporre») e alle esclusioni note del
> chunking. Si decompone in `requirements/ingestione-estesa/<feature>/requirements.md` (EARS).

## 1. Visione e problema (perché)

L'MVP ingerisce **codice + Markdown da un filesystem locale**. Ma il corpus reale di un ospite va oltre:
sorgenti in un **repo remoto** (URL da clonare), documentazione in **PDF/DOCX/notebook**, linguaggi come
**PowerShell/T-SQL/PL-SQL/Bash** che oggi cadono nel **fallback dimensionale** (esclusi dal chunking
sintattico per decisione R-N2, [[chunking-dispatch]]), e progetti **no-code** (solo doc, niente sorgenti)
dove il wiki/RAG deve comunque funzionare.

Il valore: rendere il corpus **rappresentativo del progetto vero**, non solo della sua fetta testuale
locale, riusando la pipeline di ingestione/chunking del core invece di duplicarla.

> Il *come* (loader, parser, conversione formati) è materia della **fase di design**.

## 2. Ambito

### In ambito
- **Repository remoti via URL**: clone/fetch di un repo come sorgente del corpus (oltre al path locale).
- **Formati non-testo**: estrazione testo da **PDF/DOCX/notebook** (e simili) per l'ingestione documentale.
- **Chunking sintattico esteso**: promozione di **PowerShell, T-SQL, PL-SQL, Bash** da fallback dimensionale
  a chunking sintattico (tree-sitter), dove il node-type è validabile.
- **No-code-first**: wiki e RAG funzionanti su un progetto **senza codice** (solo documentazione/doc-repo).

### Fuori ambito
- **Conoscenza-schema SQL** (DDL/SP/lineage come corpus interrogabile): epica dedicata
  [`../conoscenza-schema-sql/epic.md`](../conoscenza-schema-sql/epic.md) — questa epica le fornisce il
  **prerequisito** (parsing T-SQL/PL-SQL), non il dominio schema.
- **Nuovi backend di store / scala**: epica `backend-store-scala`.
- **Qualità** del retrieval risultante: epica `retrieval-qualita`.
- Definizione del *come* (loader, librerie di conversione): fase di **design**.

## 3. Criteri di successo
- **CS-1 (remoto):** dato un URL di repo, il sistema costruisce un corpus interrogabile **senza** che
  l'utente cloni a mano, con gli stessi id stabili del path locale (idempotenza del rebuild preservata).
- **CS-2 (non-testo):** un PDF/DOCX/notebook nel progetto entra nel corpus come documentazione
  interrogabile (`doc_type=doc`), con citazione tracciabile alla fonte.
- **CS-3 (linguaggi):** almeno **uno** tra PowerShell/T-SQL/PL-SQL/Bash passa da fallback a chunking
  sintattico, con copertura **dichiarata e verificata** (come per i 10 linguaggi attuali).
- **CS-4 (no-code):** su un progetto senza sorgenti il wiki si crea/indicizza e il RAG risponde sulla
  sola documentazione, **senza** assumere l'esistenza di codice.
- **CS-5 (riuso pipeline):** ogni nuova fonte riusa ingestione→chunk→embed→store del core; **0** motori nuovi.

## 4. Stakeholder e attori
- **Owner/maintainer:** vuole indicizzare progetti reali (remoti, con doc binari, multi-linguaggio).
- **Ospite no-code / doc-repo:** progetto fatto di sola documentazione.
- **Il core (FEAT-001 ingestione/chunking):** la pipeline che queste fonti estendono.
- **Epica `conoscenza-schema-sql`:** consumatore del parsing T-SQL/PL-SQL prodotto qui.

## 5. Vincoli, assunzioni e dipendenze
- **Riuso della pipeline FEAT-001:** nuove fonti = nuovi loader/chunker dietro le astrazioni esistenti.
- **Id stabili & idempotenza:** anche da remoto/binario, gli id restano deterministici (path POSIX / `doc_id#index`).
- **Isolamento dipendenze:** parser PDF/DOCX/notebook = extra opzionali (Principio III); il core resta leggero.
- **Tree-sitter:** i nuovi linguaggi sintattici dipendono dal language-pack ([[tree-sitter-language-pack]]);
  promuovere solo dove il node-type è validato (no chunking errato silenzioso).
- **Segreti:** un repo remoto può richiedere auth → credenziali mai versionate.

## 6. Rischi
- **R-1 — Estrazione testo lossy/sporca** da PDF/DOCX (layout, tabelle, OCR): degrada il retrieval;
  mitigare con estrazione conservativa e marcatura della provenienza.
- **R-2 — Chunking sintattico errato** sui nuovi linguaggi se il node-type non è quello atteso: validare
  prima di promuovere, fallback dimensionale come rete.
- **R-3 — Costo/sicurezza del clone remoto** (repo grandi, auth, codice non fidato): limiti e opt-in.
- **R-4 — Assunzioni «c'è del codice»** sparse nel sistema-wiki/graph → rompono il no-code; vanno rese esplicite.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Optional):** *Where a remote repository URL is given as a source, the system shall build the
  corpus from it without manual cloning, preserving stable ids and rebuild idempotence.*
- **REQ-E2 (Optional):** *Where a non-text document (PDF/DOCX/notebook) is present, the system shall ingest
  its extracted text as documentation with traceable provenance.*
- **REQ-E3 (Optional):** *Where a language is promoted to syntactic chunking, the system shall declare and
  verify its coverage, falling back to size-based chunking when the node-type is not validated.*
- **REQ-E4 (Ubiquitous):** *The system shall create and index a wiki/RAG on a project that contains no
  source code (documentation only), without assuming code exists.*
- **REQ-E5 (Unwanted):** *If a source requires authentication, then its credentials shall not be persisted
  in a version-controlled file.*

## 8. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Repository remoti via URL** — clone/fetch come sorgente del corpus | Corpus oltre il filesystem locale | **Could** | da decomporre — promozione di `sertor-core` FEAT-010 |
| FEAT-002 | **Formati non-testo** (PDF/DOCX/notebook → testo) nell'ingestione documentale | Documentazione binaria interrogabile | **Could** | da decomporre — promozione di `sertor-core` FEAT-010 |
| FEAT-003 | **Chunking sintattico esteso** — PowerShell / T-SQL / PL-SQL / Bash da fallback a tree-sitter | Qualità di chunking sui linguaggi esclusi (R-N2); **prerequisito** dell'epica schema-SQL | **Could** | da decomporre |
| FEAT-004 | **No-code-first** — wiki/RAG su progetti senza codice (solo doc) | Portabilità su doc-repo / progetti non-software | **Could** | da decomporre |

> **Nota sull'MVP:** nessuna di queste è Must per il prodotto attuale; l'epica esiste per **dare casa
> durevole** a capacità reali finora orfane (FEAT-010 del core, esclusioni R-N2, no-code). Il primo
> candidato a valore concreto è **FEAT-003** (chunking T-SQL/PL-SQL), perché **sblocca** l'epica
> conoscenza-schema-SQL.

## 9. Domande aperte
- **DA-I-a — Confine introspezione vs file:** per i sorgenti SQL, l'ingestione è file-based (DDL/SP come
  testo) — l'introspezione live di un DB è materia dell'epica schema-SQL, non di qui.
- **DA-I-b — Estensione formati:** [DA CHIARIRE: quali formati non-testo nel primo taglio? Default proposto:
  PDF + notebook (i più comuni in doc tecnica), DOCX a seguire.]
