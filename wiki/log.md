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
- **Index aggiornato:** sezione Syntheses con `[[wiki-role-da-w1]]`; nuova sezione Tech con `[[sessionstart-hook]]`.
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
- **Index aggiornato:** aggiunto link `[[constitution]]` in testa a Syntheses; source `.specify/memory/constitution.md` aggiunta.
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
- **Index aggiornato:** aggiunto link `[[corpus-index-naming]]` in sezione Tech; `updated` → 2026-06-04.

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
- **Index aggiornato:** aggiunto `[[step-ritual]]` in cima alle Syntheses.
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
- **Index aggiornato:** nessun link nuovo (già presente [[step-ritual]]), solo update timestamp.

## [2026-06-05] record | Fonte unica del rituale = CLAUDE.md (plugin step-ritual cancellato, riesportazione a backlog)

- **Riconoscimento chiave:** il Rituale di step viveva in due posti fino al 2026-06-05: (1) `CLAUDE.md` istanza operativa concreta, (2) `plugins/step-ritual/` principio astratto/portabile. Non erano "copie derivate" ma **due livelli di astrazione**.
- **Vincolo decisivo:** il rituale è standing behavior (azione LLM nel loop). Standing behavior NON può vivere in un plugin/asset non garantito in contesto. La versione operativa (autorità) **deve** stare in `CLAUDE.md` e solo lì, finché il rituale evolve.
- **Decisione (utente):** **fonte unica = `CLAUDE.md`.** Plugin `plugins/step-ritual/` e `.claude-plugin/marketplace.json` **cancellati** (untracked, mai committati → zero seconde copie, zero deriva).
- **Backlog differito (non abbandonato):** quando sezione *"Rituale di step"* in `CLAUDE.md` sarà matura/stabile, riesportarla come plugin portabile repository-agnostico (asset riusabile, coerente col goal toolset enterprise). Ridecidere nome, collocamento, if Sertor consume via dogfooding oppure esporta.
- **Contenuto:** pagina creata `wiki/syntheses/rituale-step-e-allineamento-wiki.md` § 5 *"Fonte unica del rituale: CLAUDE.md come autorità (decisione 2026-06-05)"* — reframe, vincolo, decisione, backlog differito.
- **File toccati:** `wiki/syntheses/rituale-step-e-allineamento-wiki.md` (nuova sezione 5, rinumerate sezioni seguenti a 6+, tag `fonte-unica` aggiunto a frontmatter), `wiki/log.md` (voce corrente).

## [2026-06-05] record | FEAT-003-D nucleo wiki deterministico implementato (SpecKit)

- **Milestone:** Completamento della **metà deterministica** del LLM Wiki (FEAT-003-D, decomposizione di FEAT-003 lungo confine record/LLM). Implementazione via SpecKit completo (specify → clarify → plan → tasks → implement) completata il 2026-06-05.
- **Libreria:** sottopacchetto `src/sertor_core/wiki_tools/` (11 moduli: profile, frontmatter, contracts, scan, structure, lint, collect, registry, indexing, __main__, __init__).
- **Configurazione:** `wiki.config.toml` (profilo host di Sertor, UNICA fonte di specificità dell'ospite — Principio X + VIII).
- **Operazioni meccaniche:** US1–US5 complete (scan mtime-based, structure idempotente, lint meccanico, enumerazione + registri idempotenti, orchestrazione indicizzazione).
- **CLI:** `sertor-wiki-tools` (console-script registrato in `pyproject.toml`); operazioni: scan, lint, structure, validate, collect, index.
- **Contratti:** dataclass puri + serializzazione JSON versionata (`wiki.scan/1`, `wiki.lint/1`, `wiki.structure/1`, `wiki.index/1`, etc.); consumati da hook refactorizzato, skill, FEAT-003-N.
- **Test:** 8 test suite, 44 verdi, ruff clean, Constitution Check 10/10 ✅ (all principi inclusi NON-NEGOZIABILI I/IV/X).
- **Offline garantito:** zero nuove dipendenze esterne (solo stdlib); import lazy del facade di retrieval (US5) → operazioni wiki_tools non dipendono da vector store.
- **Host-agnostico (Principio X):** SC-001 dimostra — **stesso codice immodificato** esegue operazioni su Sertor ("code+doc") e ospite finto `doc_only_host` ("solo-doc"), differendo **solo** per config.
- **Fixture nuova:** `tests/fixtures/doc_only_host/` (ospite finto per prova SC-001).
- **Punti aperti segnalati:** (1) import package-root non lazy (`sertor_core/__init__.py` importa eagerly composition → chromadb); offline-import garantito solo a livello wiki_tools; (2) link rotto reale nel wiki: `[[architettura-attuale]]` in `syntheses/chiusura-prototipo-dogfooding.md` → pagina inesistente (scoperto dal lint).
- **Branch:** `spec/006-nucleo-wiki-deterministico` | Commit: `4ac4eaa` (non su master, nessuna PR ancora).
- **Pagina creata:** `wiki/syntheses/nucleo-wiki-deterministico-feat003d.md` (sintesi completa, Constitution Check 10/10, linkage a [[constitution]], [[mission-vision]]).
- **Link rotto corretto (scoperto dal lint):** `[[architettura-attuale]]` in `syntheses/chiusura-prototipo-dogfooding.md` → pagina inesistente rimossa, testo generalizzato a "concetto di architettura da `prototype/wiki/`".
- **File toccati:** Nuova pagina `wiki/syntheses/nucleo-wiki-deterministico-feat003d.md`, aggiornati `wiki/index.md` (timestamp + link), `wiki/syntheses/chiusura-prototipo-dogfooding.md` (link rotto corretto), `wiki/log.md` (voce corrente).

## [2026-06-05] record | Mission/Vision canonizzate (README) + Costituzione v1.1.0 (Principio X host-agnostico)

- **README.md (nuovo):** formalizzazione di Vision ("la conoscenza viva e interrogabile, ovunque, senza lock-in") e Mission ("Sertor framework installabile su qualsiasi progetto: indicizzazione + RAG + LLM Wiki, disaccoppiati dal dominio ospite"). Tre profili ospite: code+doc, solo-doc, solo-code. Sottolinea che disaccoppiamento è vincolo, non aspirazione.
- **Emendamento Costituzione v1.0.0 → v1.1.0 (MINOR):** aggiunto **Principio X — Capacità host-agnostiche** (la portabilità è un vincolo, non un'aspirazione). Ogni capacità (core, motori RAG, skill wiki, rituali) MUST essere disaccoppiata da dominio/struttura ospite; l'ospite si configura, non si presume. Dogfooding strumentale, non licenza a violare. Test non-negoziabile: capacità operabile su ospiti diversi senza modifiche al corpo. Generalizza Principio I da core-libreria a TUTTE le capacità.
- **Conseguenza/backlog:** Principio X identifica una **tensione contemporanea** — skill wiki, playbook, rituale today sono Sertor-coupled (citate `wiki/`, `log.md`, agenti, `.claude/`). Refactor host-agnostico (parametrizzazione su path/config) è **differito post-MVP** (quando FEAT-003/FEAT-010 merger). Ispirazione: skill di Transcriptio (parametrizzate). Non è difetto, è evoluzione naturale prototipo → framework.
- **Pagina creata:** `wiki/syntheses/missione-visione-host-agnosticita.md` — lega README (pitch), Principio X (vincolo), backlog (azione differita). Backlink a [[constitution]] e [[step-ritual]].
- **Aggiornamenti wiki:** `wiki/syntheses/costituzione-v1.md` (10 principi, v1.1.0, sezione Versioning, link nuova pagina); `wiki/index.md` (voce costituzione aggiornata, link [[mission-vision]] aggiunto).
- **Corretto CLAUDE.md:** "9 principi" → "i principi" (drift-proof).
- **File toccati (wiki):** `wiki/syntheses/missione-visione-host-agnosticita.md` (nuovo), `wiki/syntheses/costituzione-v1.md` (frontmatter+10 principi+versioning+link), `wiki/index.md` (updated=2026-06-05, link aggiunti).

## [2026-06-05] record | PR #11 ritirata; requisiti FEAT-010 consolidati in FEAT-003 (in progress) + FEAT-004 su master

- **PR #11 ritirata:** branch `spec/005-llm-wiki` chiuso con `gh pr close` (non eliminato; congelato come riferimento leggibile). Contenuto: 100+ file, ~10k righe, 4 feature (FEAT-003 wiki, FEAT-004 CLI, FEAT-010 e2e, server MCP + adapter + ~25 test), costruito PRIMA del Principio X (host-agnostico) → **Sertor-coupled, non production-grade**. PR status: CLOSED.
- **FEAT-010 consolidato in FEAT-003:** file `requirements/sertor-core/wiki-creazione/requirements.md` (master) è ora il **documento consolidato** "LLM Wiki (creazione + end-to-end) — FEAT-003 ⊕ FEAT-010", **Stato: in progress**. In conflitto **vince FEAT-010** (D-10). Assorbiti invariati Gruppi A/B/D/F di FEAT-003; superati C (ingest → import in `ingested_sources/`, FR-030/031) e E (indicizzazione → collezioni separate, FR-008..011/023/024); aggiunti 42 FR net-new, 17 decisioni D-1..D-17, criteri, tabella tracciabilità.
- **FEAT-004 (CLI esecuzione) portato su master:** `requirements/sertor-cli/esecuzione/requirements.md` + riga epic CLI.
- **Motivo:** salvare solo i requisiti (non spec/codice) e ritirare il ramo morto; il codice FEAT-010/MCP/CLI verrà RIFATTO host-agnostico (Principio X).
- **Domanda aperta preservata** (§13 doc FEAT-003): FR-004 trigger esatto hook Stop/SessionEnd vs comando `/wiki` vs entrambi — differito a design.
- **Consequenze:** `requirements/sertor-core/epic.md` riga FEAT-003 aggiornata (stato in progress, vince FEAT-010); confine net-new FEAT-010 vs FEAT-003 storico tracciato; backlog di azioni post-MVP chiaro.
- **File toccati (requirements):** `requirements/sertor-core/wiki-creazione/requirements.md` (consolidato), `requirements/sertor-cli/esecuzione/requirements.md` (nuovo), `requirements/sertor-core/epic.md` (FEAT-003 riga aggiornata).

## [2026-06-05] record | Ponte D→N: layer agentico wiki host-agnostico + rename author/curator (FEAT-003-N step 1)

- **Step:** primo passo di FEAT-003-N (metà di giudizio del Wiki LLM). Trasformato il layer agentico perché poggi sul nucleo deterministico `wiki_tools` (FEAT-003-D) per il meccanico e resti solo il giudizio; reso **host-agnostico** (Principio X); **rename coerente** delle 4 entità. Scope deciso con l'utente: **leggero** (zero codice in `sertor_core`).
- **Rename (author/curator):** skill `genera-wiki`→**`wiki-author`** (cartella spostata), playbook `playbook.md`→**`wiki-playbook.md`**, agente `wiki-keeper`→**`wiki-curator`** (+ tool **`Bash`** così può chiamare la CLI), comando `/wiki` invariato.
- **Playbook riscritto** (`.claude/skills/wiki-author/wiki-playbook.md`): §0 host-agnostico (tutto da `wiki.config.toml`), §2 confine deterministico↔giudizio con tabella CLI, ogni operazione delega il meccanico a `sertor-wiki-tools` (scan/lint/validate/collect/index/structure); ruoli da `[roles].curator`/`[roles].vcs` invece dei nomi letterali; nota sui write-back log/indice ancora LLM-authored.
- **Superfici sottili aggiornate:** `wiki-author/SKILL.md`, `commands/wiki.md`, `agents/wiki-curator.md` (frontmatter `tools: …, Bash`).
- **Config/glue:** `wiki.config.toml` `[roles].curator = "wiki-curator"`; `wiki-pending-check.ps1` e `settings.json` (promemoria → `wiki-curator`); `CLAUDE.md` (tutti i riferimenti: `wiki-keeper`→`wiki-curator`, `genera-wiki`→`wiki-author`, path playbook, nota CLI meccanica, rag-sync via CLI).
- **Confine D↔N (clarity richiesta):** `lint`/`validate`/`index`/`structure` = 100% meccanico (CLI); `record`/`ingest`/`query`/`generate-from-diff` = meccanico (collect/scan) + giudizio (corpo, perché, contraddizioni, pagine impattate). Lint **semantico** resta giudizio (Opus), futuro N5.
- **4 scoperte tracciate:** (1) la CLI non espone i write-back (`append_log`/`upsert_index` solo Python); (2) disallineamento identità/formato (rel_path vs slug `[[foo]]`, riga piatta vs sezioni curate); (3) → log/indice restano LLM-authored; (4) hook ancora con stringhe (parametrizzazione = codice, deferita).
- **Verifica:** CLI col config rinominato OK — `scan` 6 pending, `lint`/`validate` 0 broken/0 orphans, `collect` 16 pagine. Nessun nome vecchio nei file tooling (residui solo in `log.md` storico e artefatti SpecKit datati).
- **Pagine wiki:** nuova `syntheses/ponte-d-n-host-agnostico.md`; aggiornate `sistema-wiki-fonte-unica.md` (rename + sezione Evoluzione), `rituale-step-e-allineamento-wiki.md`, `tech/hook-sessionstart-wiki.md`, `index.md`.
- **Tracker:** `requirements/sertor-core/wiki-llm/TODO.md` (step ponte D→N segnato fatto).
- **Fuori scope/prossimi:** scope "completo" (write-back in CLI + riconciliazione formato index), FR-004 (trigger), operazioni di contenuto N1/N2/N5.

## [2026-06-05] lint | Lint semantico del wiki (prova N5) — 2 derive corrette vs realtà del repo

- **Operazione:** primo test del **lint semantico** (la metà di giudizio del lint, N5): lint meccanico CLI (pulito) + confronto claim del wiki ↔ realtà del repo (codice `src/`, `git log`, requisiti). Reader in parallelo per estrazione claim; giudizio e verifica nel flusso principale.
- **Finding #1 [ALTO] corretto:** `syntheses/nucleo-wiki-deterministico-feat003d.md` dichiarava FEAT-003-D *"non ancora su master, no PR"* (riga di stato non aggiornata dopo il merge). Realtà: **mergiata su master via PR #13** (merge `17569da`). Riga aggiornata con commit impl. `4ac4eaa`, PR #13, merge `17569da`, fix post-test.
- **Finding #2 [MEDIO] corretto:** la scomposizione "14 linguaggi" era errata in 4 pagine — il numero 14 è giusto (set MVP REQ-011) ma la ripartizione diceva "10 sintattici + **3** fallback (PowerShell, T-SQL, PL/SQL)" dimenticando **Bash**, e in `implementazione` Bash era addirittura listato tra i sintattici. Verità del codice (`code.py` `_TS_NAME`/`_LANG`): **10 sintattici + 4 fallback (PowerShell, Bash, T-SQL, PL/SQL)**; Bash non è mappato → fallback. Corrette: `index.md`, `tech/tree-sitter-language-pack.md`, `syntheses/piano-nucleo-retrieval.md`, `syntheses/implementazione-nucleo-retrieval.md`. Voci storiche di `log.md` (108/129/141) **non toccate** (registro append-only).
- **Falsi positivi scartati:** 5 wikilink dati per "inesistenti" da un reader erano validi (cercava nella cartella sbagliata); la CLI conferma 0 broken. Conteggi test per-feature (53/67/44) = snapshot storici, non derive (totale corrente 113/114).
- **Nota codice (non toccato, scope leggero):** il docstring di `code.py` giustifica come fallback solo PowerShell+SQL e tace su Bash, che cade in fallback de facto perché non mappato. Eventuale chunking sintattico di Bash = estensione post-MVP.

## [2026-06-05] record | Formalizzato il lint semantico nel playbook (FEAT-003-N / N5, variante b)

- **Step:** trasformata la procedura di lint semantico — finora improvvisata — in **metodo ripetibile e documentato**, scelta utente **variante (b)**: documentazione + cablaggio agli strumenti esistenti, host-agnostico, **zero codice nuovo** nel core.
- **Playbook (`.claude/skills/wiki-author/wiki-playbook.md`):** riscritta l'operazione `lint` su **due livelli**. **A) strutturale** = 100% CLI (`lint`+`validate`, autorevole sui link). **B) semantico** = giudizio LLM nel flusso principale (Opus; **non** delegato al `curator` Haiku), con procedura a 6 passi (baseline → estrai claim → ground truth → giudica → report con severità → correggi su conferma) e **tassonomia** dei controlli (stato git/PR/branch, numeri vs codice, file/simboli assenti, date/versioni, contraddizioni tra pagine, claim più vecchi delle `sources`, coverage).
- **Ground truth via strumenti già disponibili** (non reinventati): **git** delegato al ruolo VCS; **esistenza file/simboli** via RAG dell'ospite (`search_code`/`find_symbol`) **o** fallback `Read`/`Grep`; **conteggi** via tool di test dell'ospite (`pytest --collect-only`). **Degradazione host-agnostica** per profilo (solo-doc → niente probe di codice; il RAG è acceleratore se c'è, mai prerequisito).
- **Confine D↔N coerente col resto:** il meccanico (baseline strutturale + recupero ground truth) si appoggia a D/strumenti; il **giudizio** ("è davvero una deriva?") resta N (Opus).
- **CLAUDE.md:** il lint semantico per-step (rituale, punto 2 della DoD) ora rimanda al **metodo del playbook (livello B)** → stesso metodo per la passata per-step (stretta) e per quella on-demand `/wiki lint` (larga).
- **Tracker:** `requirements/sertor-core/wiki-llm/TODO.md` N5 → **◑ in corso** (metodo documentato variante b; provato sul wiki reale con 2 derive corrette). Deferito **(c)**: probe deterministici in `wiki_tools`.
- **File toccati:** `.claude/skills/wiki-author/wiki-playbook.md`, `CLAUDE.md`, `requirements/sertor-core/wiki-llm/TODO.md`.

## [2026-06-05] record | Pagina d'architettura del Wiki LLM + roadmap; sessione mergiata (PR #14)

- **Mergiato:** ponte D→N + fix hook Stop + lint semantico (4 commit) su `origin/master` via **PR #14** (merge `4be79e7`).
- **Nuova pagina** `syntheses/architettura-wiki-llm.md`: vista d'insieme dell'architettura dopo il ponte D→N, come **pagina d'ingresso** che unifica [[nucleo-wiki-deterministico-feat003d]] + [[ponte-d-n-host-agnostico]] + [[sistema-wiki-fonte-unica]]. Contiene **schemi**: architettura a strati (config → nucleo deterministico CLI → 4 entità agentiche → hook), confine D↔N per operazione, lint a due livelli, e **grafo di dipendenze della roadmap**.
- **Roadmap** (nuovo contenuto): tabella con natura (codice/giudizio/decisione), priorità, dipendenze e — punto chiave di processo — **EARS sul lato D** (soprattutto `sertor_mcp`), **build sul lato N** (i requisiti di outcome esistono già). Prossimo passo raccomandato: `requirements` a livello feature su `sertor_mcp` (5a).
- **Aggiornato** `wiki/index.md` (voce 🗺️ in cima alle sintesi + updated).
- **Lint:** strutturale pulito (0 broken/orphans).

## [2026-06-06] record | FEAT-MCP implementata (SpecKit completo, codice finito)

- **Milestone:** Completamento della feature **FEAT-MCP** (Server MCP di produzione, `sertor_mcp`), flusso SpecKit **completo** con implementazione finita il **2026-06-06**.
- **Ciclo SpecKit:** requirements ✅ (`requirements/sertor-core/mcp/requirements.md`, 57 REQ + 8 RNF) → specify ✅ (`specs/007-mcp-sertor-core/spec.md`, Constitution Check 10/10) → clarify ✅ (research) → plan ✅ (`specs/007-mcp-sertor-core/plan.md`) → analyze ✅ (requirements.md checklist, Constitution riconciliato) → **implement** ✅ (codice).
- **Codice:** `src/sertor_mcp/{__init__,server}.py` — FastMCP("sertor-rag"), 3 tool (`search_code`/`search_docs`/`search_combined`), facade memoizzata, formattatore con troncamento anteprima a 300 car.
- **Test:** `tests/unit/test_mcp_server.py`, **6 test verdi**: tool registrati, formato stabile, filtro per tipo, anteprima troncata, indice mancante→`[]` (degrado pulito), errore propagato+ripresa server.
- **Config & binding:** `pyproject.toml` extra `mcp` isolato (REQ-060); `.mcp.json` rimontato su server produzione (`python -m sertor_mcp.server`, `SERTOR_CORPUS=sertor`), sostituendo il server del prototipo rotto.
- **Scoperte cruciali:**
  - **Osservabilità (Principio IX):** la facade del core logga **già** `retrieve`/`no_index` (provider/k/results/elapsed); RNF-004 coperto dal nucleo. Aggiunto comunque log di superficie per-tool (nominare il tool in contesto MCP). Nessuna duplicazione.
  - **Degrado indice mancante:** `[]` + warning è **policy tollerante e voluta del core** per composabilità; non è null silenzioso, è stato osservato/loggato/segnalato. Ereditato dal server (consumatore sano). Coerente con CLAUDE.md "policy errori non uniforme e voluta".
  - **Naming corpus:** DA-MCP1 risolto. Server non hardcoded; legge da `Settings`/`SERTOR_CORPUS` env. Binding imposta `sertor` (non legacy `production`). REQ-021 ✅.
- **Constitution Check:** 10/10 ✅, Principi I/IV/X NON-NEGOZIABILI superati (Principio I: layer sottile, core non modificato; IV: errori espliciti; X: host-agnostico).
- **Suite test:** 116 passed (non-cloud, include le 6 del server).
- **Ruff:** pulito.
- **Acceptance fuori dal codice della feature (richiedono decisione/setup esterno):**
  - **T023 (validazione live con client MCP reale):** richiede un indice del corpus `sertor`.
  - **T024 (dogfood index):** creazione indice è fuori ambito (feature *consuma*, non crea); inoltre `.env` `RAG_BACKEND=azure` comporterebbe costo (Azure embeddings), dipende da entry-point indicizzazione (CLI non su master).
- **Pagina wiki aggiornata:** `syntheses/server-mcp-produzione-feat-mcp.md` — da "avvio/requisiti" a "implementata/completata", con sezioni Flusso SpecKit, Implementazione (struttura, dettagli, test), Scoperte, Note di processo, Stato, Roadmap successiva.
- **Index aggiornato:** entry `[[server-mcp-produzione-feat-mcp]]` con summary completo; timestamp updated.
- **Commit:** delegato al configuration-manager (feat(mcp): implementazione SpecKit completo, 3 tool, Constitution Check 10/10, .mcp.json rimontato).
- **Roadmap:** item 5a di [[architettura-wiki-llm]] **realizzato**. Prossimi: FEAT-005 (GraphRAG, tool grafo), FEAT-004 (Hybrid), dogfood indice, agente Azure.

## [2026-06-06] record | Avvio feature FEAT-MCP (Server MCP di produzione)

- **Feature avviata:** FEAT-MCP (epica sertor-core §8) con **flusso SpecKit completo** (requirements → specify → plan → tasks → implement).
- **Requisiti decompositi:** `requirements/sertor-core/mcp/requirements.md` (57 REQ funzionali EARS + 8 RNF, 7 rischi, 4 DA aperte con default assunto, 8 CS).
- **Priorità:** **Should** (enabler critico di 3 cose: probe-RAG del lint semantico N5, dogfood di produzione, entry-point agente Azure).
- **Scope MVP onesto:** 3 tool baseline (`search_code`, `search_docs`, `search_combined`) perché il core ha solo FEAT-001+002 (vettoriale). Fuori scope: tool di grafo (FEAT-005) e reranking ibrido vero (FEAT-004), registrabili non-breaking quando arrivano (REQ-061).
- **Scoperta importante:** esiste già un'implementazione di riferimento su branch NON mergiato `feat/mcp-sertor-core` (commit `53b8e43`): `src/sertor_mcp/server.py` + `tests/`, pulita, testata, compatibile con `master` (build_facade/Settings/RetrievalFacade/RetrievalResult con `score` verificati).
- **Decisione di processo:** NON merge dei soli sorgenti (codice orfano senza spec); si usa come **RIFERIMENTO** durante implement. Master rimane pulito da sorgenti MCP/CLI orfani.
- **Riconciliazione naming critico (DA-MCP1/R-02):** il branch usa `SERTOR_CORPUS=production` (legacy); i requisiti e il prodotto usano `sertor`. REQ-021 formalizza: il server **deve** riconciliare a `sertor` senza hard-code.
- **Binding `.mcp.json` pendente (REQ-031/CS-7):** dopo merge implement, `.mcp.json` sarà ri-puntato da `prototype/04-agentic-rag/mcp_server.py` (rotto) a `python -m sertor_mcp.server`.
- **Roadmap successiva:** specify (contratti MCP) → plan (task) → analyze (Constitution Check, atteso ✅) → implement (coding, test, binding).
- **Nuova pagina wiki:** `syntheses/server-mcp-produzione-feat-mcp.md` — visione d'insieme, requisiti sommati, rischi, domande aperte, legami architetturali, checklist.
- **Aggiornamenti:** `wiki/index.md` (timestamp + link a [[server-mcp-produzione-feat-mcp]] in Syntheses), `wiki/log.md` (voce corrente).

## [2026-06-06] record | Lint semantico esteso a audit globale (host-agnostico)

- **Motivazione:** il 2026-06-04 il flusso principale ha lavorato su dati stantii in `requirements/sertor-core/wiki-llm/TODO.md` senza verificarli — nessun controllo di coerenza su artefatti non-wiki. Il lint finora copriva solo il wiki, lasciando fuori il monte (requirements/spec/tracker) da cui gli agenti attingono. Questa è una **buco critico**: la rete anti-deriva deve essere globale.

- **Decisione:** formalizzare l'estensione del lint semantico a una **audit globale host-agnostica**.

- **Implementazione (tre parti):**
  1. **Config (`wiki.config.toml`):** nuova sezione `[[audit]]` con 4 `kind` di artefatti (wiki, requirements, spec, tracker) e `paths` glob ospite-specifici. Regola matching: primo glob che matcha vince → `**/TODO.md` ricade in `tracker` anche sotto `requirements/`.
  2. **Playbook (`.claude/skills/wiki-author/wiki-playbook.md`):** riscritta operazione `lint` livello B (semantico); tabella profilo universale che per ogni `kind` definisce cosa conta come "deriva" (es. per `requirements`: solo claim di STATO, non intento; un «shall X» non-implementato = backlog, NON deriva; per `tracker`: checkbox contraddetti = deriva diretta). Procedura ripetibile a 6 step (baseline → estrai claim → ground truth via VCS/RAG/Grep → giudica → report → correggi su conferma).
  3. **CLAUDE.md e rituale:** il lint semantico è il punto 2 della Definition of Done, eseguito dal flusso principale (Opus, non delegato a Haiku) a ogni step.

- **Host-agnostico (Principio X):** la tassonomia di coerenza (profili di `kind`) è codificata nel playbook; i file specifici dell'ospite (`[[audit]].paths`) in config. Stessa implementazione, due ospiti diversi → due reti di audit, zero replica.

- **Metodo, non auto-fix:** il valore sta nella **rilevazione** (warning NON bloccante), non nella correzione automatica. Un esperimento passato di auto-fix LLM si era rivelato troppo rumoroso. Default: report-only, correggi su conferma esplicita.

- **Stato:** ◑ metodo documentato (2026-06-06); ◑ config estesa (wiki.config.toml); ◑ playbook recritto (§5.4); ☐ automazione al commit (FR-004 trigger differito).

- **File toccati:**
  - Nuova pagina: `wiki/syntheses/lint-semantico-host-agnostico.md` (problema, soluzione, tassonomia, collegamenti).
  - Aggiornati: `wiki/index.md` (timestamp + link a [[lint-semantico-host-agnostico]] in Syntheses), `wiki/log.md` (voce corrente).

- **Collegamento architettura:** [[architettura-wiki-llm]] item "N5 lint semantico — metodo documentato (variante b)"; [[step-ritual]] punto 2 (lint di allineamento); [[ponte-d-n-host-agnostico]] confine D↔N.

## [2026-06-06] lint | Audit globale on-demand su intero repo (4 kind)

- **Trigger:** richiesta utente `/wiki lint deterministico e semantico su intero repo` — primo esercizio del metodo di lint host-agnostico (esteso il 2026-06-06) su **tutti** i target `[[audit]]`, non incrementale sul changeset.

- **Ambito:** 20 pagine wiki + 9 tracker + 7 requirements + 28 spec ≈ 64 documenti. Ground truth: git (delega `configuration-manager`, read-only), `src/` + `pytest --collect-only`, `.mcp.json`.

- **Livello A (strutturale, CLI):** ✅ pulito — 0 link rotti / orfane / frontmatter mancante / naming su tutto il wiki.

- **Livello B (semantico) — findings:**
  - 🔴 **ALTO** — `wiki/tech/pulizia-pycache-e-diagnosi-mcp.md`: diagnosi datata 2026-06-05 con claim architetturali al presente ora contraddetti da master (`sertor_mcp` su master via PR #15; `wiki_tools`/FEAT-003-D su master via PR #13; `.mcp.json` ri-puntato a `sertor_mcp.server`/corpus `sertor`; solo CLI resta su branch). **Corretto** con banner "Superato il 2026-06-06" (corpo storico invariato).
  - 🟡 **MEDIO** — `wiki/index.md` riga 62: il sommario propagava lo stesso claim stantio. **Corretto** (sommario marcato come diagnosi superata).
  - 🟢 **BASSO** — `requirements/sertor-core/wiki-llm/TODO.md` (N5): sottostimava il progresso (mancava l'estensione audit-globale del 2026-06-06). **Corretto** (nota su PR #16).
  - ℹ️ **INFO (no-azione)** — `requirements/sertor-core/epic.md`: colonna "Stato=decomposta" traccia la decomposizione, non l'implementazione → falso positivo, nessuna deriva.

- **Verificato pulito:** spec/requirements (intento/design; «shall» non-implementato = backlog, non deriva; CLI assente da master = backlog corretto); sintesi di implementazione (conteggi datati per-feature, non claim globali); checkbox `tasks.md` delle feature mergiate.

- **Metodo confermato:** report-only + correzione su conferma esplicita dell'utente; nessun auto-fix; storia datata non riscritta (solo banner). Esercita N5 ([[lint-semantico-host-agnostico]], punto 2 del rituale in [[step-ritual]]).

## [2026-06-06] record | Disciplina organizzativa del wiki: lint livello C + reorg + regole di creazione

- **Motivazione:** un'analisi del wiki (best practice LLM Wiki + referto) ha rilevato una **terza categoria di deriva** oltre a igiene (lint A) e claim-vs-realtà (lint B): l'**organizzazione**. Misurata: 16/20 pagine in `syntheses/` (80%), `concepts/`/`experiments/`/`sources/` vuote, `type: synthesis` semanticamente falso (per il RAG non discrimina più), `index.md` auto-contraddittorio, alcune pagine non-atomiche (sezioni duplicate).

- **Meccanismo (verificato in `collect.py`):** l'`area` è derivata dalla cartella ma il `type` è letto dal frontmatter senza validazione di coerenza; e — punto chiave — un check `type==taxonomy[area].type` sarebbe inutile, perché la deriva tiene cartella e `type` coerenti tra loro mentre **entrambi mentono sul contenuto**. Stabilire la natura reale è **inerentemente semantico**: il lint organizzativo è tutto giudizio (N), nessun helper deterministico per la detection.

- **Intervento (3 parti):**
  1. **Preventivo — regole di creazione** in `wiki-playbook.md`: atomicità (una pagina = un focus, criterio di split), auto-contenimento (prima frase = definizione, per i chunk RAG), euristica di collocazione per natura (§3, ruoli delle aree + regola anti-discarica), `type` riflette la natura non solo la cartella, link densi/inline/bidirezionali.
  2. **Correttivo — nuova operazione `/wiki`**: lint **livello C (organizzativo)** (detection: collocazione vs natura, `type` falso, tassonomia collassata, atomicità, disciplina link; backlink calcolati invertendo `collect`) + operazione **`reorg`** (applica su conferma: sposta + corregge `type` + aggiorna wikilink entranti + indice; verifica igiene post-move via CLI). Aggiornati `commands/wiki.md` (enum + livelli) e `agents/wiki-curator.md` (confine: C e `reorg` sono giudizio, non delegati a Haiku).
  3. **Tracking** (non-SpecKit): riga **N9** in `requirements/sertor-core/wiki-llm/TODO.md` (ancorata a FR-035..038/D-14, → FEAT-007); annotato il buco: nessun FR esplicito su organizzazione/refactoring in `wiki-creazione/requirements.md`.

- **Decisioni (con l'utente):** forma = nuova operazione in `/wiki` (non skill standalone, fonte-unica); confine D/N = tutto N ora, helper `move`-deterministico a backlog D; collocazione = euristica nel playbook (non campo config).

- **Host-agnostico (Principio X):** regole espresse sui nomi-area della config; nessun path Sertor hardcoded.

- **File toccati (tooling, non indicizzati):** `.claude/skills/wiki-author/wiki-playbook.md`, `.claude/commands/wiki.md`, `.claude/agents/wiki-curator.md`, `requirements/sertor-core/wiki-llm/TODO.md`.

- **Prossimo:** esercitare `lint` C + `reorg` sul wiki reale (le ~16 pagine mal-collocate) in incrementi su conferma; valutare una pagina-concetto sul "lint a tre livelli / deriva organizzativa".

## [2026-06-06] reorg | Primo refactoring organizzativo del wiki (lint C esercitato)

- **Trigger:** richiesta utente "esercita sul wiki reale" — prima esecuzione end-to-end di `lint` livello C + `reorg` sul wiki di produzione.

- **Report lint C:** tassonomia collassata (16/20 in `syntheses/`, `concepts/`/`experiments/`/`sources/` vuote), 13 pagine con `type: synthesis` semanticamente falso, 12 pagine mal-collocate, `rituale-step` non-atomica, `ruolo-wiki-da-w1` con H1 non descrittivo (`# Contesto`).

- **Increment applicato (alta confidenza, link-safe):**
  - **9 record → `experiments/`** (type→experiment): implementazione-nucleo-retrieval, motore-baseline-feat002, nucleo-wiki-deterministico-feat003d, server-mcp-produzione-feat-mcp, piano-nucleo-retrieval, ponte-d-n-host-agnostico, chiusura-prototipo-dogfooding, decomposizione-must-core, epiche-sertor-core-e-cli.
  - **3 fondamenti → `concepts/`** (type→concept): costituzione-v1, missione-visione-host-agnosticita, ruolo-wiki-da-w1.
  - **Indice ristrutturato** per area (Concepts/Experiments/Syntheses/Tech); rimosso il placeholder auto-contraddittorio ("la produzione inizia ora"); corretto "lint a due livelli" → "tre livelli" nel sommario di architettura-wiki-llm.
  - **Fix auto-contenimento:** H1 di ruolo-wiki-da-w1 da `# Contesto` al titolo descrittivo.

- **Sicurezza del move:** i wikilink sono `[[slug]]` (indipendenti dalla cartella) e i link relativi puntano a `../../requirements|specs` (stessa profondità per tutte le aree) → spostare tra cartelle non rompe nulla. **Verificato:** `lint`/`validate` post-move = 0 link rotti / 0 orfani / 0 frontmatter / 0 naming.

- **Distribuzione:** da 16/0/0/4 (syntheses/concepts/experiments/tech) a **4/3/9/4**; `type` ↔ area coerenti ovunque.

- **Restano in `syntheses/` (viste integrative):** architettura-wiki-llm, sistema-wiki-fonte-unica, lint-semantico-host-agnostico, rituale-step-e-allineamento-wiki.

- **Increment successivi (proposti, non applicati):** (a) split di `rituale-step` (concetto rituale-di-step ↔ retrospettiva-2026-06-04); (b) aggiornare il corpo di `architettura-wiki-llm` (sezione "lint a due livelli" → tre livelli A/B/C); (c) verificare sezioni duplicate in server-mcp-produzione-feat-mcp.

- **Esercita N9** ([[lint-semantico-host-agnostico]] livello C, [[step-ritual]]): prima prova del metodo su contenuti reali, con esito pulito.

## [2026-06-06] record | Documentazione lint C/reorg + sistemati i 3 follow-up

- **Trigger:** richiesta utente — documentare il nuovo step di `reorg` e chiudere i 3 increment lasciati aperti dal reorg precedente.

- **Documentazione del nuovo step:** nuova pagina **[[lint-organizzativo-e-reorg]]** (syntheses): le tre categorie di deriva (A igiene / B claim / C organizzazione), perché C è interamente giudizio (cartella e `type` mentono *insieme* sul contenuto → nessun check deterministico le coglie), principio "grafo non albero", prevenzione (regole di creazione) vs correzione (lint C + `reorg`), esercizio 2026-06-06 (16/20→4/3/9/4, 0 link rotti), host-agnostico, tracking N9.

- **(a) Split di `rituale-step` (era non-atomica):** la pagina mescolava il *design* del rituale e la *retrospettiva* dell'interazione. Separata in due pagine atomiche: **[[step-ritual]]** (concept, ricucito, prima frase = definizione) + **[[retrospettiva-interazione-2026-06-04]]** (experiment). Slug del concetto invariato → i 6 inbound restano intatti.

- **(b) `architettura-wiki-llm` allineata:** "lint a **due** livelli" → **tre** (A/B/C, con `reorg`); tabella confine D↔N estesa a lint C + reorg; "6 op" → 7; **corretta deriva adiacente**: `sertor_mcp` da "☐ da fare, .mcp.json rotto" a "✅ PR #15, .mcp.json su produzione"; roadmap 5a marcata fatta.

- **(c) `server-mcp-produzione-feat-mcp` ricucito:** la pagina era cresciuta per append con sezioni ridondanti. Rimossi: la roadmap pre-implementazione (contraddetta dal completamento) e la sezione "Note di processo" duplicata; sommario/titolo aggiornati a "completata".

- **Dogfooding:** il lint **A** ha pizzicato due `[[slug]]`/`[[link]]` scritti come esempi in prosa (collisione notazionale `[[...]]`, la stessa di `[[audit]]`) → corretti. Il livello strutturale fa da rete al livello organizzativo.

- **Indice:** ristrutturato (rituale→Concepts, +retrospettiva in Experiments, +lint-organizzativo in Syntheses). Distribuzione: concepts 4 / experiments 10 / syntheses 4 / tech 4 (22 pagine).

- **Verifica:** `lint`/`validate` = 0 link rotti / 0 orfani / 0 frontmatter / 0 naming.

## [2026-06-06] record | Prossimi step pianificati (backlog di sessione)

Annotati i prossimi passi concordati, da affrontare in sessioni successive:

1. **Strategia di scrittura dei log** — definire una linea guida esplicita su *come* si scrivono le voci di `log.md`: granularità, lunghezza, cosa va nel log (append-only, datato) vs cosa va nelle pagine (evergreen); evitare la deriva verso voci troppo verbose. Da codificare nel playbook (§6 Voce di log).

2. **Ulteriore refining della scrittura del wiki — orientata ai tipi** — affinare la tassonomia/convenzioni distinguendo meglio le nature delle pagine: **entità**, **concetti**, **procedure**, **configurazioni**, ecc. (oltre l'attuale concept/tech/experiment/source/synthesis). Valutare se servono nuovi `type`/aree o solo linee guida di stile per ciascuna natura, mantenendo l'host-agnosticità (config-driven).

3. **Revisione puntuale di `CLAUDE.md` e `.claude/skills/wiki-author/wiki-playbook.md`** — passata mirata sui due file di governance: coerenza interna, ridondanze, allineamento con lo stato reale (lint a tre livelli, reorg, regole di creazione appena aggiunte), eliminazione di eventuali sezioni stantie o duplicate.

## [2026-06-07] record | Modularizzazione del playbook (opzione C, step #3)

Eseguita l'**opzione C** decisa nell'analisi `playbook-flussi-e-modularizzazione.md` (è la forma concreta dello step #3 — revisione di `wiki-playbook.md`). Trigger considerato scattato: il blocco `lint` B/C pesava ~85 righe su 331.

- **Cosa:** `wiki-playbook.md` non è più monolitico → **indice + substrato condiviso** (host-agnosticità, identità, confine D↔N, tassonomia, convenzioni §4, voce di log §6, limiti §7) + **tabella di dispatch** (§5) verso 8 moduli `ops/<operazione>.md` (stessa cartella): `record · ingest · query · lint · reorg · generate-from-diff · rag-sync · structure`. I wrapper fanno `Read` **solo del modulo** dell'operazione invocata (on-demand).
- **File:** creati `.claude/skills/wiki-author/ops/{record,ingest,query,lint,reorg,generate-from-diff,rag-sync,structure}.md`; aggiornati `wiki-playbook.md` (nota di testa + §5 → indice), `SKILL.md`, `commands/wiki.md`, `agents/wiki-curator.md` (pattern di caricamento on-demand).
- **Perché C e non B (skill):** le skill sono un costrutto dell'host → violano il Principio X e duplicano il substrato; C resta `.md` portabile e DRY. Razionale completo nell'analisi.
- **Guadagno misurato:** `record` carica 168 (indice) + 9 (modulo) = 177 righe vs 331; `lint` 168 + 78 = 246 solo quando serve.
- **Wiki:** nota di evoluzione 2026-06-07 su [[sistema-wiki-fonte-unica]] (corretta deriva: era "file unico / 6 operazioni" → ora "indice + moduli / 8 operazioni"); summary aggiornato in `index.md`; nota "ESEGUITO" nell'analisi di design.
- **Verifica:** `lint --json` = 0 link rotti / 0 orfani / 0 frontmatter / 0 naming.

## [2026-06-07] record | N1 record-contenuto — metodo "livello di significato"

Codificato il metodo di scrittura del *contenuto* di una pagina (la metà di giudizio di `record`, nodo N1), oltre alle convenzioni sintattiche già presenti.

- **Dove (DRY):** nuovo blocco «**Il livello di significato — cosa scrivere, non solo come**» nel substrato condiviso del playbook (§4 Convenzioni), così è riusabile da tutte le operazioni che producono contenuto (`record`, `ingest`, `generate`, `reorg`) invece di duplicarlo in `ops/record.md`.
- **Cosa:** 5 regole — distilla-non-trascrivi · cattura il *perché* + le alternative scartate · astrazione coerente con l'area (evergreen vs stato datato) · verità ancorata (rovescio attivo del lint B) · densità di significato — + un **esempio male→bene** (reranking cross-encoder).
- **Moduli:** `ops/record.md` punto 2 riscritto come "giudizio di contenuto" che richiama §4; `ops/ingest.md` punto 2 idem per i riassunti di fonte.
- **Stato N1:** ☐→◑ (metodo documentato, da esercitare) in `requirements/sertor-core/wiki-llm/TODO.md` e nella tabella di [[architettura-wiki-llm]].
- **Origine:** discusso col proprietario (era "il punto 2 di record.md troppo asciutto sul lato contenuto/LLM/significato").

## [2026-06-07] record | Page-craft estratto in pagina-foglia (rompe la dipendenza circolare)

Risolto uno smell architetturale segnalato dal proprietario: i moduli `ops/` rimandavano al playbook §4 mentre il playbook §5 rimandava ai moduli → dipendenza **bidirezionale/circolare**.

- **Fix:** il page-craft ("come si scrive una pagina": atomicità · auto-contenimento · link · **livello di significato**) è stato **estratto** dal playbook §4 nella pagina-foglia `.claude/skills/wiki-author/pagina-ben-fatta.md`. È una **foglia** (non dipende da nessuno); indice e moduli la linkano *verso il basso* → il grafo torna un DAG.
- **Linkata da:** `ops/record.md`, `ops/ingest.md`, `ops/query.md` (quando archivia), `ops/lint.md` (livello C), `ops/reorg.md`; richiamata anche dal playbook §4/§5.
- **Playbook §4:** resta solo il *formato* (frontmatter, naming, wikilink, nuova-vs-aggiorna, contraddizioni, append-only) + puntatore alla foglia.
- **Disambiguazione collaterale:** negli header dei moduli «indice» → «playbook» (`wiki-playbook.md`), così non collide più con «indice del wiki» (`index.md`); il punto 1 di `record` ora dice esplicitamente "indice del wiki (`index.md`)".
- **N1:** il metodo è ora nella foglia (aggiornato tracker + diagramma in [[architettura-wiki-llm]] e nota in [[sistema-wiki-fonte-unica]]).
- **Verifica:** lint A = 0/0/0/0.

## [2026-06-07] record | page-craft ampliato all'anatomia completa (host-agnostico)

Arricchita la pagina-foglia `.claude/skills/wiki-author/page-craft.md` (metodo N1) sulla base di contenuti forniti dal proprietario, resi **host-agnostici**.

- **Aggiunto:** §1 *Struttura della pagina* (titolo univoco · lead · TOC · sezioni gerarchiche · "vedi anche" · fonti · metadati) · §2 *Tipo di contenuti* (piramide rovesciata, concreto/azionabile, auto-contenuta-non-ridondante, stile diretto, aggiornabilità) · §4 *Tipo di link* (3 categorie: contestuali inline / navigazione strutturale / esterni-riferimenti + regole pratiche) · **checklist** finale. Mantenuto §3 *livello di significato* + esempio male→bene.
- **Host-agnostico (Principio X):** neutralizzati gli assunti d'ospite — TOC automatico, campi stato/owner, gerarchie genitore/figlio, redirect a catena → marcati "se l'host lo prevede / da config"; esempi `[[wikilink]]`/`concepts/`/frontmatter tenuti come *profilo Sertor*.
- **Tensione risolta:** lo schema fornito metteva i link in "Vedi anche", la regola del wiki è link inline → integrati come **categorie distinte** (contestuali inline ≠ navigazione), con nota che "Vedi anche" non sostituisce l'inline (smell del lint C).
- **DAG preservato:** la foglia non rimanda *all'insù* al playbook (solo a `wiki.config.toml`, verso il basso).

## [2026-06-07] reorg | Lint C approfondito alla luce di page-craft — reorg + lead + connettività

Lint a tre livelli su tutto il wiki (22 pagine) alla luce delle nuove convenzioni (`page-craft.md`). Baseline A pulita. Applicati i finding C/B concordati col proprietario:

- **🔴 Collocazione vs natura (reorg):** `pulizia-pycache-e-diagnosi-mcp` spostata `tech/` → `experiments/`, `type: tech` → `experiment`. Era un **record datato di diagnosi** (lo dichiara: "diagnosi storica"), non una tecnologia — caso da manuale di cartella+`type` concordi ma falsi sulla natura. Riga di `index.md` spostata di sezione.
- **🟡 Lead che definiscono (page-craft §1.2):** riscritta la prima frase di `costituzione-v1`, `missione-visione-host-agnosticita`, `lint-semantico-host-agnostico`, `naming-corpora-indici` (aprivano con date/eventi/processo invece di «X è…»); aggiunto lead a `motore-baseline-feat002` (apriva con "Data completamento").
- **🟡 Connettività:** `server-mcp-produzione-feat-mcp` aveva 0 backlink → aggiunto wikilink entrante da [[architettura-wiki-llm]] (tabella stato).
- **Igiene post-move:** lint+validate = 0/0/0/0 (il lint A ha pizzicato una collisione `[[audit]]` introdotta in un lead, corretta — conferma del livello A come rete del C).
- **Finding di COVERAGE rimasto (da affrontare a parte):** il wiki è **record-pesante e concept-leggero** — molti `experiment` orbitano attorno a concetti evergreen senza pagina propria (es. `piano-` + `implementazione-nucleo-retrieval` ma nessun `concepts/nucleo-retrieval`). Proposta separata: mappa record→concetti-mancanti, creazione pagine-concetto per distillazione (una a una).

## [2026-06-07] record | Primo concept di dominio: retrieval-core (coverage gap)

Avviata la chiusura del finding di coverage (wiki record-pesante, concept-leggero): creato il primo **concept di dominio del prodotto**, distillato dai record + codice reale.

- **Nuova pagina:** `concepts/retrieval-core.md` (concept evergreen) — architettura Clean di `sertor-core` (domain/services/adapters/engines + porte `Protocol`, composition root da `Settings`, backend local/azure, policy errori tollerante↔strict, idempotenza, collezioni namespaced). **Ancorata al codice reale** (`src/sertor_core/**` + CLAUDE.md), non al piano: il record `piano-nucleo-retrieval` descrive una struttura di design divergente (`domain/ports/` dir, `*_service.py`) → nel concept la struttura è quella vera (`ports.py`, `services/chunking/`, `services/retrieval.py`).
- **Backlink:** i record `piano-` e `implementazione-nucleo-retrieval` ora linkano [[retrieval-core]] inline; aggiunto all'indice (Concepts). Il record `piano-` segnala la divergenza piano↔codice rimandando al concept per l'architettura corrente.
- **Nuova convenzione codificata** (playbook §4): pagine-**entità/concetto** con slug+titolo **in inglese** (`retrieval-core`), corpo discorsivo in italiano; record restano italiani; pagine esistenti rinominate opportunisticamente.
- **Tensione segnalata:** il playbook dice "forward-link a pagina inesistente = feature", ma il lint A della CLI flagga i wikilink senza target come broken → ho usato "consumatori sottili" in testo piano (non `[[thin-consumer]]`) per non rompere il lint. Da riconciliare (prossimo concept candidato: `thin-consumer`).
- **Verifica:** lint+validate 0/0/0/0.

## [2026-06-07] record | Secondo concept di dominio: thin-consumer (+ chiusa la tensione forward-link)

Secondo concept di dominio del coverage gap: il pattern **thin-consumer** (consumatore sottile).

- **Nuova pagina:** `concepts/thin-consumer.md` (concept evergreen, slug+titolo EN, corpo IT) — le interfacce (CLI, server MCP, tool) espongono il [[retrieval-core]] importandolo e cablandolo dalle factory `build_*`, senza reimplementare logica; il prodotto è la libreria, l'interfaccia un guscio sottile (host-agnostico, Principio X). Ancorata al codice: `sertor_mcp/server.py` usa `build_facade(Settings.load())` (verificato).
- **Chiusa l'istanza della tensione forward-link:** in [[retrieval-core]] il testo piano "consumatori sottili" è ora il wikilink `[[thin-consumer|…]]` (prima evitato per non rompere il lint A). La tensione *di sistema* (playbook dice forward-link=feature, CLI lo flagga broken) resta aperta come decisione.
- **Connettività:** [[retrieval-core]] e il record [[server-mcp-produzione-feat-mcp]] linkano il nuovo concept; aggiunto all'indice. server-mcp non è più a 0 backlink.
- **Verifica:** lint+validate 0/0/0/0.

## [2026-06-07] record | Coverage concepts: vector-retrieval, dogfooding, deterministic-vs-judgment

Completato il giro di **concept di dominio** che chiude il coverage gap (wiki record-pesante → ora i concetti evergreen hanno casa). Tre nuove pagine (slug+titolo EN, corpo IT, ancorate al codice/realtà):

- **`concepts/vector-retrieval.md`** — la 1ª modalità RAG: embed query → similarity top-k via il motore baseline (`engines/baseline.py`); policy *strict* (`IndexNotFoundError`) vs nucleo tollerante; valutazione hit-rate@k/MRR@10 (`engines/evaluation.py`). Backlink da [[motore-baseline-feat002]] e [[retrieval-core]].
- **`concepts/dogfooding.md`** — interrogare il progetto col proprio RAG (server MCP `sertor-rag` su corpus `prototype`/`sertor`); validazione continua + contesto ancorato (versante retrieval della disciplina anti-deriva). Backlink da [[chiusura-prototipo-dogfooding]].
- **`concepts/deterministic-vs-judgment.md`** — il confine meccanico (codice, zero LLM) ↔ giudizio (LLM); principio trasversale (wiki D↔N + delega). Backlink da [[architettura-wiki-llm]] e [[ponte-d-n-host-agnostico]] (che prima ridefinivano il confine, ora lo linkano).
- **Indice:** 3 voci aggiunte nella sezione Concepts. **Verifica:** lint+validate 0/0/0/0.
- **Stato coverage:** i 5 concept candidati (retrieval-core · thin-consumer · vector-retrieval · dogfooding · deterministic-vs-judgment) sono fatti. Concepts ora 9 (4 governance + 5 dominio).

## [2026-06-07] record | Risolta la tensione forward-link: convenzione "stub" (zero codice)

Chiusa la tensione di sistema tra playbook ("forward-link = feature") e lint A della CLI (che flaggava i `[[…]]` senza target come `broken`). Scelta: **opzione (c) stub**, realizzata **per convenzione** senza toccare il codice di produzione.

- **Convenzione:** un forward-link verso un nodo da creare si realizza come **stub** — file reale nell'area giusta, frontmatter completo + `status: stub` + corpo `> 🚧 STUB`. Così il link **risolve** (lint A verde) e il nodo è *voluto*; un `[[…]]` senza pagina né stub resta `broken` = **refuso**. È la separazione voluto↔rotto, ottenuta dall'esistenza-o-meno del file (nessuna euristica, nessun giudizio).
- **Grounding:** verificato con uno stub usa-e-getta che `validate`/`lint` restano verdi (il campo extra `status` non disturba; lo stub non è orphan perché il forward-link che lo motiva è il suo arco entrante).
- **Documentato:** regola in `page-craft.md` (disciplina dei link), nota in `wiki-playbook.md` §4 e in `ops/lint.md` (livello A); `status` aggiunto a `frontmatter_optional` in `wiki.config.toml`.
- **Gravy deferito (richiede codice, → branch+PR):** estendere `wiki_tools` perché il `lint` riporti gli **stub** come categoria a sé (worklist "nodi da riempire"), invece di doverli cercare a mano. Non necessario alla separazione voluto↔rotto, che la convenzione già garantisce.

## [2026-06-07] record | lint riporta gli stub come worklist (codice, FEAT-003-D)

Implementato il "gravy" deferito della convenzione stub: il `lint` deterministico ora **espone gli stub come categoria a sé**, non più solo da cercare a mano. Prima vera task di **codice** della sessione → su **branch + PR** (non master), come da policy di produzione.

- **Codice (`src/sertor_core/wiki_tools/`):** campo **additivo** `stubs: list[str]` in `LintResult` (contratto `wiki.lint/1` invariato — è dichiarato forward-compatible); `lint()` popola gli stub dalle pagine con frontmatter `status: stub`; l'output umano della CLI mostra `stubs=N`.
- **Test:** nuovo `test_stub_is_wanted_not_broken_nor_orphan` — uno stub linkato da un forward-link **non** è broken né orfano e compare in `stubs`. Suite lint 6/6 verde (l'unico rosso della suite, `test_settings`, è ambientale: `RAG_BACKEND=azure` nel `.env`, pre-esistente).
- **Doc allineati** (stesso branch): `ops/lint.md` e `page-craft.md` annotano il campo `stubs`.
- **Constitution Check:** additivo, zero nuove dipendenze, deterministico/offline, test verdi, leggibile → PASS.

## [2026-06-07] record | Creata la guida di livello-grafo: wiki-craft (gemella di page-craft)

Aggiunta la pagina-foglia **`wiki-craft.md`** (governance, in `.claude/`), il gemello a livello-grafo di `page-craft`: *page-craft* = com'è fatta **una** pagina; *wiki-craft* = **cosa merita di essere una pagina** e **come l'insieme tiene insieme**.

- **Contenuto:** quando creare una pagina (test del link/nome, anti-frammentazione) · archetipi (Diátaxis: entità/how-to/reference/spiegazione/hub) · pagine di struttura (home/hub/overview/glossario/categorie) · i due assi (gerarchia + rete) · igiene a livello wiki (SSoT, no orfani/dead-end, naming, coerenza>completezza, crescita per refactoring) · modello mentale "grafo + impalcatura".
- **Host-agnostica (Principio X):** principi universali; mappatura/esempi = profilo Sertor. Mapping esplicitato: aree *per natura* (concepts/tech/experiments/sources/syntheses) che **tagliano** gli archetipi; `index.md` = home+hub globale; `tags` = categorie; albero volutamente piatto, valore nella rete. Sertor non usa tutti gli archetipi (no how-to/hub per-area).
- **Riconciliazione col playbook §3:** "grafo non albero" resta valido; wiki-craft aggiunge la sfumatura che anche un albero *piatto* è un asse-punto-fermo, da tenere basso non abolire.
- **Wiring (foglia, linkata verso il basso):** playbook §3 + `ops/record`, `ops/ingest`, `ops/reorg` (crescita per refactoring), `ops/lint` livello C (criteri di grafo). Peer-link reciproco con `page-craft`.
- **Possibili follow-up (segnalati, non agiti):** `index.md` fa home+hub insieme ed è lungo (tende all'hub); nessun hub/overview per-area.

## [2026-06-07] reorg | Lint approfondito (page-craft + wiki-craft) + rename EN dei 6 slug italiani

Lint a tutte le lenti su 27 pagine. **page-craft** e **wiki-craft** giudicano il wiki **sano**: 0 orfani, 0 dead-end, SSoT ok (D↔N canonico in [[deterministic-vs-judgment]]), due assi coerenti col profilo piatto. L'unico finding sistematico era la **coerenza di naming** (convenzione EN); l'utente ha scelto di rinominare tutte e 6.

- **Rename EN (slug + titolo, corpo IT):** `costituzione-v1`→`constitution` · `missione-visione-host-agnosticita`→`mission-vision` · `ruolo-wiki-da-w1`→`wiki-role-da-w1` · `rituale-step-e-allineamento-wiki`→`step-ritual` · `naming-corpora-indici`→`corpus-index-naming` · `hook-sessionstart-wiki`→`sessionstart-hook`. Tutti i wikilink entranti aggiornati (~34) in wiki + `index.md` + `log.md`.
- **Blast radius esterno:** aggiornati `CLAUDE.md` (`[[step-ritual]]`) e `requirements/sertor-core/epic.md` (menzione `corpus-index-naming`). **Lasciata** la spec mergiata `specs/007-mcp-sertor-core/research.md` (artefatto datato, riferimenti già stale di suo).
- **Minori:** lead-che-definiscono per `tree-sitter-language-pack` ed `epiche-sertor-core-e-cli`; rimosso da tree-sitter un `sources` inesistente (`adapters/chunkers/syntactic_chunker.py`); +1 backlink a [[pulizia-pycache-e-diagnosi-mcp]] da [[server-mcp-produzione-feat-mcp]] (era a 0).
- **Verifica:** lint+validate **0/0/0/0** (zero broken = rename corretto); pycache backlink 1.

## [2026-06-07] record | Priorità prossima sessione: la funzione di log del wiki

Deciso con l'utente che la **priorità della prossima sessione** è migliorare la **funzione di log** del wiki (`log.md`). Scope concordato:

1. **Strategia di scrittura** *(certo, giudizio)* — come si scrivono le voci di `log.md`: granularità, lunghezza, cosa va nel log (datato/append-only) vs nelle pagine (evergreen), evitare la deriva verso voci verbose. → da codificare nel **playbook §6 (Voce di log)**. È il backlog #1 già annotato il 2026-06-06.
3. **Struttura/manutenzione** *(certo)* — il `log.md` cresce indefinitamente (append-only): valutare rotazione / partizionamento per periodo / indicizzazione-sommari; gestire dimensione e navigabilità.
2. **Write-back deterministico `append_log`** *(da discutere — "capiamo bene" prima)* — eventuale cablaggio di `append_log` di `wiki_tools` nella CLI (oggi le voci le scrive l'LLM a mano; formato deterministico diverso). Se si procede → codice, branch+PR (scope completo deferito di FEAT-003-N).

NB: si parla del log del **wiki**, non del logging runtime/osservabilità del codice. Checkpoint di ripresa aggiornato in memoria.

## [2026-06-08] distill | FEAT-001: 4 pagine-entità del nucleo + record assottigliato

Primo esercizio reale dell'operazione `distill` (introdotta in giornata nel rituale). Il record `experiment`
di FEAT-001 (~312 righe) teneva la conoscenza-entità durevole **sepolta e drifted**: estratta in pagine-entità
ancorate al **codice reale** (non al record, già stantio).

- **Estratte** (`concepts/`): [[domain-model]] · [[ports-adapters]] · [[chunking-dispatch]] · [[indexing-and-retrieval]] — da `domain/entities.py`, `domain/ports.py`, `composition.py`, `services/`.
- **Assottigliato:** `implementazione-nucleo-retrieval` da ~312 righe a **evento + esito + puntatori**.
- **Deriva corretta nel record:** citava `domain/ports/` (cartella), `ollama_provider.py`, facade `ingest_repository`/`retrieve`, "14 lingue" → realtà: `ports.py` (file unico), `adapters/embeddings/ollama.py`, facade `search_code/docs/combined`, **10** lingue sintattiche (+ fallback).
- **Cablaggio:** [[retrieval-core]] punta giù alle 4 entità; `index.md` aggiornato.
- **Segnalato (backlog):** `tech/tree-sitter-language-pack` è gonfio e in parte **fabbricato** (`adapters/chunkers/syntactic_chunker.py` inesistente, `FALLBACK_LANGUAGES` inventato) → da ripassare con distill/lint-B.
- **Verifica:** lint A = 0/0/0/0.
