---
title: Log del Wiki — Produzione Sertor
type: log
created: 2026-05-30
---

# Registro di Produzione (append-only)

Voci in ordine cronologico. Formato: `## [YYYY-MM-DD] <operazione> | <titolo>`
(operazione ∈ setup/ingest/record/query/lint).

## [2026-05-30] setup | Apertura del wiki di produzione (chiusura del prototipo)

- **Isolamento prototipo:** codice `01–04`, `shared/`, `tests/`, corpus FastAPI (`raw/`),
  documentazione (`README/DEMOS/ESEMPI`) e il wiki storico spostati in **`prototype/`**
  (stesso repo). Il wiki del prototipo è ora **congelato** (sola lettura) in `prototype/wiki/`.
- **RAG di dogfooding:** motore reso *corpus-aware* (env `SERTOR_CORPUS`); nuovo indice separato
  `prototype/01-baseline/.index-sertor` il cui corpus è il **prototipo stesso** (codice + doc + wiki).
  L'indice FastAPI esistente **non è stato toccato**.
- **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py` con
  `PYTHONPATH=prototype`, `SERTOR_CORPUS=sertor`. Ogni riferimento al prototipo passa ora dal RAG.
- **Questo `wiki/` di root** è il nuovo wiki di **produzione**; hook `SessionStart`, agente
  `wiki-keeper` e skill `.claude/` restano invariati (continuano a puntare a `wiki/`).

## [2026-05-30] record | Chiusura prototipo + RAG dogfooding + MCP ri-puntato

- **Pagina creata:** `syntheses/chiusura-prototipo-dogfooding.md` documenta in dettaglio:
  - **Motivazione:** confine netto prototipo (exploration) ↔ produzione (CLI `sertor-rag`).
  - **Isolamento fisico:** prototipo sotto `prototype/` (snapshot congelato), produzione
    a livello alto (requirements, wiki, nuovi moduli).
  - **Motore corpus-aware:** `SERTOR_CORPUS` (`fastapi` | `sertor`) in `config.py` e `loaders.py`;
    fix critico del filtro `mentions` in `build_graph.py` (era hardcoded, ora dinamico).
  - **Indici namespaced:** `.index` (FastAPI) vs `.index-sertor` (dogfooding).
  - **RAG di dogfooding:** indice Chroma `.index-sertor` su prototipo stesso.
    Corpus = 57 doc, 670 chunk (dim 3072); grafo = 240 nodi, 835 archi (415 mentions, 26 doc).
  - **MCP ri-puntato:** `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py`
    (`SERTOR_CORPUS=sertor`). Tutti i tool (`find_symbol`, `search_code`, etc.) testati e funzionanti.
  - **Conseguenze operative:** sviluppo isolato da prototipo; accesso via MCP; wiki prototipo
    congelato; corpus dogfooding come acceptance test.
- **Index aggiornato:** sezione "Syntheses" con link a `[[chiusura-prototipo-dogfooding]]`.
- **Branch/commit:** `chore/isolamento-prototipo` (commit `104e666`), pagina aggiunta in questo record.

## [2026-05-30] record | Ristrutturazione epiche: sertor-core (primaria/MVP) + sertor-cli (secondaria)

- **Nuova pagina:** `syntheses/epiche-sertor-core-e-cli.md` documenta la ristrutturazione di visione:
  - **Razionale:** il valore core non è la CLI ma le capacità (creare RAG production-grade + skill
    LLM Wiki). CLI è il veicolo di distribuzione/uso.
  - **Epica primaria (sertor-core, `requirements/sertor-core/epic.md`):** 8 feature, sequenza logica.
    FEAT-001/002/003 Must (nucleo retrieval, baseline, wiki skill); FEAT-004/005/006/007 Should
    (ibrido, grafo, agentico, spider/lint); FEAT-008 Could (arricchimento bidirezionale). 7 success
    criteria, 6 requisiti EARS.
  - **Epica secondaria (sertor-cli, `requirements/sertor-cli/epic.md`):** 6 feature, CLI instalabile
    + selezione capacità + config + RAG/wiki command. Decisioni DA-1…DA-6 (naming, git, vector DB,
    provider) rimangono valide.
  - **Questione aperta DA-W1:** ruolo profondo del wiki non ancora definito (fonte di contesto per
    agenti? luogo di query precise? fonte di ingestion per RAG?). Blocca decomposizione FEAT-003
    wiki. Richiede decisione di prodotto PRIMA di user story.
- **Index aggiornato:** sezione Syntheses con link a nuova pagina.
- **Pagina storica superata:** `prototype/wiki/epica-sertor-cli.md` (congelata, consultabile via RAG).

## [2026-05-31] record | DA-W1 risolta (ruolo wiki: corpus×superficie) + hook SessionStart documentato

- **Pagina creata:** `syntheses/ruolo-wiki-da-w1.md` documenta il modello concettuale risolutivo:
  - **Due assi ortogonali:** corpus (wiki vs codice) × superficie (RAG semantica vs wiki-nativa).
  - **Identità:** wiki = CORPUS + SUPERFICIE entrambi; già ingerito nel RAG, navigabile per struttura.
  - **Tre ruoli:** (1) contesto iniettato (push, host); (2) query precisa (pull strutturato); (3) ingestion nel RAG (già attivo).
  - **Decisioni chiave:** MVP Must = creare+indicizzare (ruolo 3); post-MVP = superficie nativa (ruoli 1–2) + spider/lint/arricchimento.
  - **Confine MVP risolto:** chiude DA-W1 e DA-2 (wiki = solo creazione/indicizzazione, niente spider automatico).
  - **Sblocca FEAT-003 decomposizione** e inquadra FEAT-007/008 (post-MVP).
- **Pagina creata:** `tech/hook-sessionstart-wiki.md` documenta il meccanismo concreto di ruolo 1:
  - **Hook `SessionStart`:** PowerShell inline in `.claude/settings.json`, attiva a inizio sessione/resume/compact.
  - **Payload:** indice wiki intero + ultime 20 righe di log, iniettate in contesto (sola lettura).
  - **Rilevanza DA-W1:** prova empirica di ruolo 1 (contesto iniettato); competenza dell'host, non MVP Sertor.
- **Index aggiornato:** sezione Syntheses con `[[ruolo-wiki-da-w1]]`; nuova sezione Tech con `[[hook-sessionstart-wiki]]`.
- **Epica sertor-core `epic.md`:** §9 (DA-W1, DA-2 risolte) e §6 (R-5 mitigato).

## [2026-05-31] record | Decomposizione Must sertor-core + decisioni di ambito MVP

- **Pagina creata:** `syntheses/decomposizione-must-core.md` documenta:
  - **FEAT-001 (Nucleo retrieval):** ingestione repo-agnostica, chunking code-aware 14 linguaggi MVP, embeddings multi-provider, astrazione vector store, facade di retrieval. 32 REQ + 8 NFR.
  - **FEAT-002 (RAG baseline):** indicizzazione, query vettoriale, ranking, valutazione pertinenza. 16 REQ + 8 NFR. Dipende da FEAT-001.
  - **FEAT-003 (Wiki creazione):** invocazione via brief, distillazione (record/ingest/query/lint), indicizzazione nel RAG, struttura fissa. 26 REQ + 7 NFR. Perimetro MVP da DA-W1: creazione + indicizzazione, no spider.
- **Sei decisioni MVP:**
  1. Chunking 14 linguaggi + fallback testuale da subito (non Python-solo).
  2. Full re-index idempotente nell'MVP; incrementale post-MVP → **FEAT-009 nuova** (refresh incrementale sorgenti, Could backlog).
  3. No file non-testo (PDF/DOCX) nell'MVP.
  4. Soglie di performance misurate in design su corpus con ground-truth; local Ollama hit@5≈0.67 accettabile (vs cloud ≈0.80).
  5–6. Agente LLM primario per wiki; brief condensato → no chunking input MVP; struttura directory fissa.
- **Conseguenza:** FEAT-009 nel backlog (§8 epic.md) come pendant per sorgenti di FEAT-007 wiki (post-MVP).
- **Domande aperte (§10):** rinviate a design (estensione linguaggi, formati, ground-truth, test Linux, packaging extras → sertor-cli).
- **Index aggiornato:** link `[[decomposizione-must-core]]` in Syntheses.

## [2026-05-31] record | Ratifica Costituzione di Sertor v1.0.0

- **Pagina creata:** `syntheses/costituzione-v1.md` documenta:
  - **Origine:** derivata da zero da wiki Clean Code + Clean Architecture (ExternalRepos) allineata ai requisiti Sertor (REQ-E*, epiche, FEAT-001/002/003).
  - **9 principi vincolanti:** (I) core a dipendenze interne; (II) provider intercambiabili; (III) semplicità YAGNI; (IV) gestione errori esplicita; (V) testabilità misurata; (VI) idempotenza/non-distruttività; (VII) leggibilità; (VIII) config centralizzata; (IX) osservabilità via log strutturati.
  - **Principle I e IV NON-NEGOZIABILI:** gate Constitution Check del planning.
  - **Governance attivata:** branch + PR (niente più push diretti); Constitution Check in Phase 0–1; semantic versioning per emendamenti.
- **Index aggiornato:** aggiunto link `[[costituzione-v1]]` in testa a Syntheses; source `.specify/memory/constitution.md` aggiunta.
- **File toccati:** `wiki/syntheses/costituzione-v1.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-03] record | Piano SpecKit FEAT-001 nucleo-retrieval

- **Pagina creata:** `syntheses/piano-nucleo-retrieval.md` documenta:
  - **Architettura Clean:** layout `src/sertor_core/` con domain (entità + porte + errori), services, adapters, config, observability, composition root. Nessun import SDK nel domain (Principio I).
  - **Decisioni tecniche R1–R8:**
    - R1: Chunking sintattico `tree-sitter-language-pack` (305+ linguaggi wheel precompilati, Win/Linux nativi); MVP 10 sintattici + 3 fallback (PowerShell, T-SQL, PL/SQL) al 1° rilascio.
    - R2: Astrazione minimale `VectorStore` (upsert/query/delete/count), namespacing per collezione; Chroma embedded default, Azure Search extra opzionale.
    - R3: Porta `EmbeddingProvider` (embed batch, dim, name, batch_size); Ollama locale (default), Azure OpenAI REST (extra); local-only via config.
    - R4: ID stabili (doc_id = path relativo, chunk_id = {doc_id}#{ordinale}) → idempotenza garantita.
    - R5: Logging strutturato stdlib, redazione segreti, nessun framework imposto.
    - R6: `Settings` dataclass unica (env+file), nessun segreto versionato.
    - R7: Extra opzionali (`[azure]`) + import lazy → evita conflitti dipendenze con CLI.
    - R8: Soglie performance/qualità misurate (baseline prototipo: precision@5 ≈0.67 locale).
  - **Constitution Check:** ✅ PASS su tutti e 9 i principi, Principi I+IV NON-NEGOZIABILI confermati. Complexity Tracking vuoto.
  - **Modello dati:** Document, Chunk, ChunkMetadata (codice vs Markdown), EmbeddedChunk, RetrievalResult, SertorError gerarchia.
  - **Scope MVP:** ingestione, chunking 14 linguaggi, embeddings Ollama, vector store Chroma, full re-index idempotente, facade+test.
  - **Linkage:** FEAT-002 aggiunge ranking; FEAT-003 usa il RAG; sertor-cli importa libreria (no dipendenze cloud obbligatorie).
- **Index aggiornato:** aggiunto link `[[piano-nucleo-retrieval]]` in Syntheses con descrizione.
- **File toccati:** `wiki/syntheses/piano-nucleo-retrieval.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-03] record | Implementazione FEAT-001 nucleo-retrieval

- **Pagina creata:** `syntheses/implementazione-nucleo-retrieval.md` documenta il completamento phase 2 (implementation) di FEAT-001:
  - **Stato:** ✅ 42 task completati (US1–US6), 53 test passed + 1 xfail (DA-003 precision@k baseline), ruff clean, Constitution Check 9/9 ✅.
  - **Libreria:** `src/sertor_core/` installabile (sertor-core package), Python 3.12 + venv uv `.venv-core`.
  - **Stack reale:** tree-sitter-language-pack 1.8.1 (binding Rust, wrapper `_Node` per API metodi), chromadb, httpx, python-dotenv, pytest 9.
  - **Chunking sintattico:** 10 lingue validati (Python, JS/TS, Java, C#, Go, C/C++, PHP, Ruby, Bash); 3 fallback dimensionali (PowerShell, T-SQL, PL/SQL, validazione AST in sospeso).
  - **Decisione tecnica notevole:** binding tree-sitter espone API come metodi (non attributi); wrapper `_Node` risolve leggibilità codice, chiama `kind()`, `byte_range()`, `start_position()`, slicia sorgente in byte.
  - **Conformità:** R1–R8 implementate; Constitution Check 9/9; Principi I+IV NON-NEGOZIABILI confermati.
  - **Idempotenza (SC-005):** doc_id = path POSIX, chunk_id = `{doc_id}#{ordinale}`, tested; re-ingest → stessi ID.
  - **Local-only (SC-006):** `RAG_BACKEND=local` → Chroma + Ollama, zero cloud SDK required.
  - **Test suite:** unit (ingestion, chunking, embeddings, vector store), integration (E2E ingest→retrieve), error handling, config/logging.
  - **xfail 1:** `test_precision_at_k_baseline` — DA-003 (baseline prototipo vs ground-truth corpus, rinviato a definizione soglia).
  - **Artefatti:** `src/sertor_core/**`, `specs/001-nucleo-retrieval/{plan,tasks,research,data-model,contracts}/*.md`, `tests/**`.
  - **Linkage:** FEAT-002 (ranking su retrieval_facade), FEAT-003 (ingestion wiki), sertor-cli (import libreria).
- **Pagina creata:** `tech/tree-sitter-language-pack.md` approfondimento su binding Rust, quirk API, 14 lingue MVP, wrapper `_Node`, performance/robustness, extension strategy (post-MVP).
  - **Binding PyO3:** metodo-based API, no attributi (design choice ufficiale).
  - **10 lingue sintattico:** Python, JS/TS, Java, C#, Go, C/C++, PHP, Ruby, Bash (node-type mappato, qualname support).
  - **3 fallback:** PowerShell, T-SQL, PL/SQL (grammatica presente, AST non ancora stabile upstream).
  - **Wrapper `_Node`:** proprietà clean per `kind`, `byte_range`, `start_position`, `start_line` (1-indexed), iterazione figli.
  - **Quirk:** byte offsets (non character), 0-indexed row/col, slicing UTF-8, no `.text` diretto, wheel precompilato.
  - **Performance:** parsing ~50 ms/file, bottleneck reale = embedding, memory = 1 MB/10KB file.
  - **Extension strategy:** controllare upstream tree-sitter, identificare node-type, test corpus, fallback dimensionale se no AST.
- **Index aggiornato:** aggiunto link `[[implementazione-nucleo-retrieval]]` in Syntheses; link `[[tree-sitter-language-pack]]` in Tech.
- **File toccati:** `wiki/syntheses/implementazione-nucleo-retrieval.md` (nuovo), `wiki/tech/tree-sitter-language-pack.md` (nuovo), `wiki/index.md`.

## [2026-06-03] record | Implementazione FEAT-002 motore baseline

- **Pagina creata:** `syntheses/motore-baseline-feat002.md` documenta il completamento phase 2 (implementation) di FEAT-002:
  - **Stato:** ✅ 21 task completati (4 US), 67 test passed + 2 xfail (DA-1/DA-3 hit-rate baseline, rinviati a decision gate), ruff clean, Constitution Check 9/9 ✅.
  - **Libreria motore:** `src/sertor_core/engines/` con `BaselineEngine` (indexing + query top-k similarity), `evaluation.py` (hit_rate@k, MRR@10).
  - **Decisione chiave 1:** policy di errore ISOLATA dal nucleo — il motore solleva `IndexNotFoundError` su indice mancante (REQ-009 FEAT-002, usabilità CLI), mentre il nucleo resta tollerante `[]`+warning (REQ-028 FEAT-001, composabilità). Motivo: Principio I (core isolation) + struttura consumatore del nucleo.
  - **Decisione chiave 2:** atomicità rebuild via ordine operazionale — `rebuild=True` esegue embed, poi reset collezione DOPO, poi upsert; se upsert fallisce, indice rimane coerente (vecchia versione intatta).
  - **Estensioni non-breaking al nucleo:** nuovo metodo `reset(collection)` sulla porta `VectorStore`, flag `rebuild` su `IndexingService.index()`, nuova eccezione `IndexNotFoundError` (tutte validate con Constitution Check 9/9).
  - **API pubblica:** esportati 6 symbol (`build_baseline_engine`, `BaselineEngine`, `evaluate`, `EvalReport`, `IndexNotFoundError`, `EvaluationConfig`).
  - **Test suite:** unit (engine init, query, error), integration (E2E ingest→query→ranking), evaluation metrics.
  - **xfail 2:** `test_precision_at_k_baseline` (DA-1), `test_hit_rate_evaluation_baseline` (DA-3) — metriche rinviate a definizione soglia corpus ground-truth.
  - **Artefatti:** `src/sertor_core/engines/**`, `specs/002-rag-baseline/{plan,tasks,research}/*.md`, `tests/**`.
  - **Linkage:** CONSUMA FEAT-001 (nucleo [[implementazione-nucleo-retrieval]]), dipendenza di FEAT-003 (wiki), sertor-cli (import libreria).
- **Analisi Speckit Analyze:** FR 15/15, 0 critical, Constitution Check 9/9 ✅, SC-005 (isolamento modalità) LOW (banale finché non esistono altre modalità).
- **Processo git:** branch `spec/002-rag-baseline` allineato a master (merge 5502700) per avere FEAT-001; commit piano (4f159d0), tasks (23641b3), implementazione incrementale.
- **Index aggiornato:** aggiunto link `[[motore-baseline-feat002]]` in Syntheses; frontmatter sources aggiornato con `specs/002-rag-baseline/**`.
- **File toccati:** `wiki/syntheses/motore-baseline-feat002.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-04] record | Consolidamento sistema wiki (fonte unica + tre interfacce + hook)

- **Pagina creata:** `syntheses/sistema-wiki-fonte-unica.md` documenta il consolidamento architetturale del wiki:
  - **Visione:** wiki è LLM Wiki Karpathy; fino a oggi regole erano duplicate (skill, comando, agente) → oggi fonte unica con tre interfacce sottili.
  - **Fonte unica:** nuovo file `.claude/skills/genera-wiki/playbook.md` (identità + tassonomia UNICA + convenzioni frontmatter + 6 operazioni: record, ingest, query, lint, generate-from-diff, rag-sync). È tooling (in `.claude/`), non contenuto wiki.
  - **Tre interfacce sottili:**
    1. **Skill** (istruzioni autore da-repo): hyperlink a playbook, no duplicazione regole.
    2. **Comando** (selector flusso principale `/wiki`): brief + parametri, router verso skill.
    3. **Agente** (wiki-keeper, subagent Haiku background): legge playbook come prima azione, esegue operazioni senza duplicazione.
  - **Incoerenze corrette:**
    - Tassonomia divergente (manual_edited/, ingested_sources/) rimossa; consolidata in sources/.
    - Residuo prototipo (riferimento 03-graphrag.md in wiki-keeper) rimosso.
    - `updated` rimosso da frontmatter log.md (file append-only).
  - **4 nuove operazioni aggiunte al playbook:**
    - `lint`: coerenza (frontmatter, wikilink rotti, pagine orfane, claim superati) → report, no auto-fix.
    - `ingest`: file/URL/PDF → sources/ con frontmatter integrato.
    - `generate-from-diff`: git log/diff delegato al configuration-manager → aggiorna solo pagine impattate.
    - `rag-sync`: re-indexizza wiki con SERTOR_CORPUS='wiki', backend azure, indice isolato.
  - **Strato automatico (hook):**
    - **Script:** `.claude/hooks/wiki-pending-check.ps1` (euristica mtime).
    - **Modo:** SessionEnd (riepilogo) + Stop (promemoria, non bloccante, guardia anti-loop).
    - **Registrazione:** `.claude/settings.json` (hook key `wiki-pending-check-stop`, `wiki-pending-check-sessionend`).
  - **CLAUDE.md aggiornato:** frase "non c'è più uno Stop hook bloccante" corretta (esplicito: non bloccante, promemoria).
- **File toccati:**
  - Nuovi: `.claude/skills/genera-wiki/playbook.md`, `.claude/hooks/wiki-pending-check.ps1`.
  - Aggiornati: `.claude/skills/genera-wiki/SKILL.md`, `.claude/commands/wiki.md`, `.claude/agents/wiki-keeper.md`, `.claude/settings.json`, `CLAUDE.md`.
  - Wiki: `wiki/syntheses/sistema-wiki-fonte-unica.md` (nuovo), `wiki/index.md`, `wiki/log.md`.
- **Benefici:** Regole consolidate, tassonomia univoca, meno duplicazione, manutenzione centralizzata, operazioni ben definite, automazione non-bloccante. Pronto per scalare.

## [2026-06-04] record | Rinomina corpora/indici RAG per chiarezza naming

- **Rinomina effettuata:**
  - Corpus **prodotto (radice):** `production` → `sertor` (etichetta primaria del prodotto).
  - Corpus **prototipo (congelato):** `sertor` → `prototype` (risolve fuorvianza).
  - Indice **prodotto (radice):** `.index-production` (eliminato, stale) → `.index-sertor`.
  - Indice **prototipo (congelato):** `prototype/01-baseline/.index-sertor` + `prototype/03-graphrag/.index-sertor` → `.index-prototype/`.
- **Motivazione:** chiarire il naming schema; `sertor` ora etichetta unicamente il corpus del prodotto (radice).
- **Non distruttivo:** i rename sono nel naming delle cartelle; le collezioni Chroma/grafo risiedono già nei percorsi rinominati (nessuna ri-indicizzazione necessaria). Smoke test del prototipo conferma che `.index-prototype/` è risolto correttamente.
- **Consequenze operative:**
  - `.env` (gitignored): `SERTOR_CORPUS=sertor`, `SERTOR_INDEX_DIR=.index-sertor`.
  - `.mcp.json` (root): `SERTOR_CORPUS=prototype` (update 2026-06-04); MCP per ri-connettersi/reload.
  - `.gitignore` (root): generalizzato a `**/.index-*/` per coprire entrambi gli indici.
  - `CLAUDE.md` § "Riferirsi al prototipo": sezione aggiornata (corpus→`prototype`, spiegazione corpus-aware).
- **Pagina creata:** `wiki/tech/naming-corpora-indici.md` documenta schema, convenzioni, storico.
- **Index aggiornato:** aggiunto link `[[naming-corpora-indici]]` in sezione Tech; `updated` → 2026-06-04.

## [2026-06-04] record | Rituale di step (Definition of Done) + retrospettiva interazione

- **Problema:** il wiki = documentazione del progetto era in **deriva** rispetto alla realtà di `master`
  (memoria dava per mergiate FEAT-003/004/MCP/CLI; in realtà solo FEAT-001+002 dopo il reset del 2026-06-04).
  Nessun meccanismo verificava *contenuto wiki ↔ realtà progetto*.
- **Decisione (svolta dell'utente):** le azioni semantiche (record + lint di allineamento) sono **lavoro da
  LLM nel loop**, quindi il flusso principale può/deve farle **come comportamento standing**, senza dipendere
  da hook/automazione *unattended*. Distinzione codificata: *unattended* (script/headless/cron, "quando non
  c'è nessuno") vs *standing* ("lo faccio mentre lavoro", nessun limite tecnico).
- **`CLAUDE.md`:** nuova sezione **"Rituale di step / Definition of Done" (regola SEMPRE attiva)** prima di
  *Git & versionamento*. Checklist a fine step: (1) record su `log.md`/pagine/`index.md`; (2) **lint semantico
  di allineamento** wiki↔progetto (oltre al lint meccanico); (3) lista azioni standing **estendibile**. Delega
  (`wiki-keeper`/`configuration-manager`) = non-bloccare, **non** un modo per saltare il rituale.
- **Pagina creata:** `syntheses/rituale-step-e-allineamento-wiki.md` — design anti-deriva (due nature dei
  controlli, vincolo hook, standing vs unattended) + **retrospettiva onesta** sull'interazione (richiesta
  dall'utente per un blog post): nessun rifiuto esplicito, ma un pattern di deferral/ratifica/caveat che ha
  *funzionato* come ostruzione; effetto > intento; correttivo = default "fai" invece di "chiedi-poi-forse-fai".
- **Index aggiornato:** aggiunto `[[rituale-step-e-allineamento-wiki]]` in cima alle Syntheses.
- **Nota di allineamento (eseguito il rituale stesso):** rilevati ma NON ancora corretti — wikilink rotto
  storico `[[epica-sertor-cli]]`→`[[epiche-sertor-core-e-cli]]` in `chiusura-prototipo-dogfooding.md`;
  `__pycache__` fantasma in `src/sertor_cli|sertor_mcp|sertor_core/wiki|adapters/git|adapters/llm` (zero
  sorgenti); `.mcp.json` punta a server prototipo rotto (manca modulo `mcp` in `.venv`). Da sistemare su richiesta.

## [2026-06-04] lint | Allineamento wiki↔progetto (primo lint semantico del rituale)

- **Eseguito** il punto 2 del nuovo *Rituale di step*: confronto *contenuto wiki ↔ realtà di `master`* (b0703ec).
- **Esito:** wiki **sostanzialmente allineato** — le pagine versionate descrivono FEAT-001/002 come fatti (vero)
  e **non** millantano FEAT-003/004/010 come mergiate. Il disallineamento grave era nella **memoria** (dava per
  mergiate cose rimosse dal `reset` del 2026-06-04), non nelle pagine del wiki.
- **Corretto:** wikilink rotto `[[epica-sertor-cli]]` → `[[epiche-sertor-core-e-cli]]` in
  `syntheses/chiusura-prototipo-dogfooding.md` (la pagina target del prototipo è congelata/superata).
- **Segnalato (fuori scope del lint wiki, da decidere):** `__pycache__` fantasma in
  `src/{sertor_cli,sertor_mcp,sertor_core/wiki,adapters/git,adapters/llm}` (zero sorgenti, fa *sembrare*
  presente codice assente); `.mcp.json` punta al server prototipo rotto (`ModuleNotFoundError: mcp` in `.venv`).
- **RISOLTO il 2026-06-05** → voce successiva.

## [2026-06-05] record | Pulizia pycache fantasma + diagnosi .mcp.json

- **Cleanup eseguito:**
  - Rimozione di 16 dir `__pycache__` da `src/sertor_core/` (bytecode `.pyc` residui da checkout di altri branch).
  - Pulizia di 6 directory vuote rimaste: `src/sertor_cli/`, `src/sertor_cli/commands/`, `src/sertor_core/adapters/{git,llm}/`, `src/sertor_core/wiki/`, `src/sertor_mcp/`.
  - Tutti i `.pyc` sono gitignored → niente da committare, nessun file sorgente toccato.

- **Diagnosi architetturale (critico per wiki allineamento):**
  - Su `master` (HEAD a4640b8) **esiste SOLO** `src/sertor_core/` (domain, services, adapters, engines, config, observability, composition).
  - **NON su master** (vivono su branch):
    - `src/sertor_cli/` → branch sconosciuto.
    - `src/sertor_mcp/` → branch `feat/mcp-sertor-core` (PR #12 aperta).
    - `src/sertor_core/wiki/` → branch `spec/005-llm-wiki` (PR #11 aperta, parte di FEAT-010).
  - I `.pyc` fantasma facevano *sembrare* presente codice che esiste solo su branch — spiega la confusione precedente.

- **Diagnosi .mcp.json:**
  - Server `prototype/04-agentic-rag/mcp_server.py` è **rotto**: carica tutti e 4 gli approcci RAG (01–04) con dipendenze inconciliabili.
  - Due venv complementari: `.venv/` ha `chromadb` ma manca `mcp`; `.venv-core/` ha `mcp` ma manca stack retrieval.
  - Risultato: `ModuleNotFoundError` all'avvio.

- **Decisione (presa da utente):** NON rianimare il vecchio server agentico. Rimane **known-broken, pendente**:
  - Causa: server prototipo = exploration phase, bassa priorità su `master`.
  - Soluzione: `.mcp.json` sarà ri-puntato a nuovo `sertor_mcp` (branch `feat/mcp-sertor-core`) **quando sarà mergiato su master** (post-FEAT-010 presumibilmente).

- **Pagina creata:** `tech/pulizia-pycache-e-diagnosi-mcp.md` documenta il cleanup, diagnosi, decisione e conseguenze operative.

- **Aggiornamenti:**
  - `wiki/index.md` (updated → 2026-06-05, aggiunto link a nuova pagina tech in sezione Tech).
  - `wiki/log.md` (voce corrente).

- **Stato finale:** flag segnalazioni 2026-06-04 CHIUSI (pycache risolto, .mcp.json con decisione documentata).

## [2026-06-05] record | Confine di delega del rituale: lint semantico resta in casa

- **Precisazione documentata:** `syntheses/rituale-step-e-allineamento-wiki.md` — nuova sezione 4a *Confine di delega*.
- **Contenuto:** chiarimento netto su quale azione delegare a `wiki-keeper` (Haiku) vs mantenere nel flusso principale (Opus):
  - ✅ **record** → delegabile: trascrizione strutturata (brief → pagine/backlink/log), lavoro di forma retto dal playbook.
  - ❌ **lint semantico di allineamento** → NON delegabile: richiede giudizio e contesto dello step appena completato. Re-leggere a freddo per delegare = token costosi + rischio di giudizi lossy. Flusso principale ha già la visione.
- **Motivo tecnico:** distinzione tra "lavoro di forma" (token-efficiente da delegare) e "giudizio" (loss di contesto se delegato). Se casi pesanti richiedono override, usare `sonnet` per-invocazione, non il default Haiku.
- **Conseguenza operativa:** rituale rimane **integralmente responsabilità del flusso principale**; delega = non-bloccare, non scappare. **Qualità del brief** (input a wiki-keeper) è la leva cruciale: brief povero → wiki disallineato silenziosamente.
- **File toccati:** `wiki/syntheses/rituale-step-e-allineamento-wiki.md` (frontmatter updated 2026-06-05, sezione 4a aggiunta, tag `delega` aggiunto).
- **Index aggiornato:** nessun link nuovo (già presente [[rituale-step-e-allineamento-wiki]]), solo update timestamp.

## [2026-06-05] record | Fonte unica del rituale = CLAUDE.md (plugin step-ritual cancellato, riesportazione a backlog)

- **Riconoscimento chiave:** il Rituale di step viveva in due posti fino al 2026-06-05: (1) `CLAUDE.md` istanza operativa concreta, (2) `plugins/step-ritual/` principio astratto/portabile. Non erano "copie derivate" ma **due livelli di astrazione**.
- **Vincolo decisivo:** il rituale è standing behavior (azione LLM nel loop). Standing behavior NON può vivere in un plugin/asset non garantito in contesto. La versione operativa (autorità) **deve** stare in `CLAUDE.md` e solo lì, finché il rituale evolve.
- **Decisione (utente):** **fonte unica = `CLAUDE.md`.** Plugin `plugins/step-ritual/` e `.claude-plugin/marketplace.json` **cancellati** (untracked, mai committati → zero seconde copie, zero deriva).
- **Backlog differito (non abbandonato):** quando sezione *"Rituale di step"* in `CLAUDE.md` sarà matura/stabile, riesportarla come plugin portabile repository-agnostico (asset riusabile, coerente col goal toolset enterprise). Ridecidere nome, collocamento, if Sertor consume via dogfooding oppure esporta.
- **Contenuto:** pagina creata `wiki/syntheses/rituale-step-e-allineamento-wiki.md` § 5 *"Fonte unica del rituale: CLAUDE.md come autorità (decisione 2026-06-05)"* — reframe, vincolo, decisione, backlog differito.
- **File toccati:** `wiki/syntheses/rituale-step-e-allineamento-wiki.md` (nuova sezione 5, rinumerate sezioni seguenti a 6+, tag `fonte-unica` aggiunto a frontmatter), `wiki/log.md` (voce corrente).

## [2026-06-05] record | Mission/Vision canonizzate (README) + Costituzione v1.1.0 (Principio X host-agnostico)

- **README.md (nuovo):** formalizzazione di Vision ("la conoscenza viva e interrogabile, ovunque, senza lock-in") e Mission ("Sertor framework installabile su qualsiasi progetto: indicizzazione + RAG + LLM Wiki, disaccoppiati dal dominio ospite"). Tre profili ospite: code+doc, solo-doc, solo-code. Sottolinea che disaccoppiamento è vincolo, non aspirazione.
- **Emendamento Costituzione v1.0.0 → v1.1.0 (MINOR):** aggiunto **Principio X — Capacità host-agnostiche** (la portabilità è un vincolo, non un'aspirazione). Ogni capacità (core, motori RAG, skill wiki, rituali) MUST essere disaccoppiata da dominio/struttura ospite; l'ospite si configura, non si presume. Dogfooding strumentale, non licenza a violare. Test non-negoziabile: capacità operabile su ospiti diversi senza modifiche al corpo. Generalizza Principio I da core-libreria a TUTTE le capacità.
- **Conseguenza/backlog:** Principio X identifica una **tensione contemporanea** — skill wiki, playbook, rituale today sono Sertor-coupled (citate `wiki/`, `log.md`, agenti, `.claude/`). Refactor host-agnostico (parametrizzazione su path/config) è **differito post-MVP** (quando FEAT-003/FEAT-010 merger). Ispirazione: skill di Transcriptio (parametrizzate). Non è difetto, è evoluzione naturale prototipo → framework.
- **Pagina creata:** `wiki/syntheses/missione-visione-host-agnosticita.md` — lega README (pitch), Principio X (vincolo), backlog (azione differita). Backlink a [[costituzione-v1]] e [[rituale-step-e-allineamento-wiki]].
- **Aggiornamenti wiki:** `wiki/syntheses/costituzione-v1.md` (10 principi, v1.1.0, sezione Versioning, link nuova pagina); `wiki/index.md` (voce costituzione aggiornata, link [[missione-visione-host-agnosticita]] aggiunto).
- **Corretto CLAUDE.md:** "9 principi" → "i principi" (drift-proof).
- **File toccati (wiki):** `wiki/syntheses/missione-visione-host-agnosticita.md` (nuovo), `wiki/syntheses/costituzione-v1.md` (frontmatter+10 principi+versioning+link), `wiki/index.md` (updated=2026-06-05, link aggiunti).
