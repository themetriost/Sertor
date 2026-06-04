---
title: Log del Wiki — Produzione Sertor
type: log
created: 2026-05-30
updated: 2026-06-04
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

## [2026-06-03] record | Implementazione FEAT-003 skill LLM Wiki

- **Pagina creata:** `syntheses/skill-wiki-feat003.md` documenta il completamento phase 2–5 di FEAT-003:
  - **Stato:** ✅ 21 task completati (US1–US5), 84 test passed + 2 xfail (soglie pertinenza motori standard, non rilevante per wiki), ruff clean, Constitution Check 9/9 ✅.
  - **Libreria skill:** `src/sertor_core/wiki/` con operazioni `create_wiki()` (struttura non-distruttivo), `record()`/`ingest()`/`distill()`/`query()` (LLM-free eccetto distill), `index_wiki()` (riusa IndexingService del nucleo).
  - **Convenzioni:** `conventions.py` con enumerazione aree tematiche → cartelle, Brief/SourceBrief, frontmatter YAML, kebab-case, formato log append-only.
  - **Estensioni additive al nucleo:** porta `LLMProvider` (Protocol metodo generate), adapter LLM Ollama/Azure, eccezione `LLMNotConfiguredError`, chiavi chat in Settings. Non-breaking, testabili con FakeLLM.
  - **Decisione architetturale chiave:** **idempotenza strutturale (REQ-050/051)** — rieseguire operazione su input invariato → hash file identico (compare content ignorando `updated:`, write only se cambia). `created` preservato, `updated` muta solo a modifica reale; log append-only; index.md/log.md mai riscritti retroattivamente. Conseguenza: SC-002 garantito.
  - **Indicizzazione DRY (REQ-040/041):** `index_wiki()` riusa `IndexingService(rebuild=True)` del nucleo, zero reimplementazione; id chunk = path relativo (REQ-051); radice vuota → warning, RAG irraggiungibile → errore (REQ-043/045).
  - **Test suite:** unit (structure, operations, indexing, LLM adapters), integration (ciclo E2E create→record→query→index), error handling (LLMNotConfiguredError, wiki esistente, collisioni path), config/logging; tutti su wiki sandbox in temp (RNF-002/R-W5).
  - **xfail 2:** threshold pertinenza motori standard (non questa feature).
  - **Artefatti:** `src/sertor_core/wiki/**`, `src/sertor_core/adapters/llm/**`, `specs/003-wiki-creazione/{plan,tasks,design}/*.md`, `tests/**`.
  - **Linkage:** CONSUMA FEAT-001 (nucleo), FEAT-002 (baseline), base per future skill surface wiki (FEAT-007/008).
- **Analisi Speckit Analyze:** FR 13/13, 0 critical, Constitution Check 9/9 ✅.
- **Processo git:** branch `spec/003-wiki-creazione` allineato a master (merge FEAT-002 in 4564e77); commit per fase (piano 40d437e, tasks 57a4e50, implementazione).
- **Chiusura MVP:** questa skill chiude il loop FEAT-001/002/003 di Sertor Core — nucleo (ingestione/embedding) + motore baseline (ranking/eval) + skill wiki (creazione/indicizzazione). Wiki stesso diventa creabile e interrogabile con i tool distribuiti.
- **Index aggiornato:** aggiunto link `[[skill-wiki-feat003]]` in Syntheses; frontmatter sources aggiornato con `specs/003-wiki-creazione/**`.
- **File toccati:** `wiki/syntheses/skill-wiki-feat003.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-03] record | Implementazione CLI esecuzione (FEAT-CLI-004)

- **Pagina creata:** `syntheses/cli-esecuzione-feat004.md` documenta il completamento phase 2 di FEAT-CLI-004:
  - **Stato:** ✅ 17/17 task completati (sottocomandi index/search/wiki), 100 test passed + 2 xfail (soglie baseline, non critiche), ruff clean, Constitution Check 9/9 ✅.
  - **Pacchetto CLI:** `src/sertor_cli/` con `cli.py` (dispatcher argparse), `commands/` (index, search, wiki), `observability.py` (logging config, exit codes, mapping eccezioni), `output.py` (formatter testo/JSON, anteprime troncate).
  - **Sottocomandi:** `sertor index <path>` (riusa build_indexer), `sertor search <query>` (riusa build_facade), `sertor wiki index <wiki>` (riusa build_wiki). Flag `--corpus` per collezioni namespaced (prototipo/produzione), `--rebuild`, `-v/--verbose`, `--log-config <file>` per dictConfig YAML/JSON esterno, `--json` per output strutturato, `--full` per risultati non troncati.
  - **Osservabilità:** logging configurabile via file dictConfig (appender Splunk/ELK/file/syslog senza toccare codice); mapping eccezioni dominio → exit code (IndexNotFoundError=2, LLMNotConfiguredError=3, ValidationError=4); log strutturato core con `log_error()` pre-raise (estensione additiva Principio IX). Formatter JSON interno, zero dipendenze aggiuntive.
  - **Design Clean Architecture (Principio I):** CLI = adapter sottile su composizione root del core; no import dominio; argparse → build_* → output (zero mutazione core).
  - **Dipendenze:** solo `sertor-core` (argparse, logging, config sono stdlib); imports lazy per `[azure]` opzionali.
  - **Processo requisiti:** EARS 26 REQ su esecuzione → spec SpecKit → plan 17 task → implementation incrementale per sottocomando. Decisioni DA-C1..C5 applicate (entry point pubblico, collezioni namespaced, config esterno, output flessibile, zero cloud obbligatorie).
  - **Significato strategico:** primo entry point eseguibile; prova di design Clean Architecture; abilita dogfooding produzione (indicizzare src/specs/wiki in collezione `production` con `sertor index` + `sertor wiki index`); estendibilità per FEAT-CLI-005/006/007.
  - **Artefatti:** `src/sertor_cli/**`, `specs/004-cli-esecuzione/{plan,tasks}/*.md`, `tests/test_cli_*.py` (4 file, 100% test).
  - **Processo git:** branch `spec/004-cli-esecuzione` da master (FEAT-001/002/003 mergiati); commit per fase (requisiti, spec, plan, implementation).
- **Index aggiornato:** aggiunto link `[[cli-esecuzione-feat004]]` in Syntheses con descrizione.
- **File toccati:** `wiki/syntheses/cli-esecuzione-feat004.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-03] record | Dogfooding di produzione + 2 fix CLI

- **Pagina creata:** `experiments/dogfooding-produzione-cli.md` documenta il primo dogfooding reale di produzione:
  - **Setup:** corpus produzione (src/, specs/, requirements/, wiki/, tests/, root Markdown) indicizzato con `sertor index .` su Ollama locale (`nomic-embed-text`, dim 768, RAG_BACKEND=local).
  - **Esito:** 146 documenti, 1.192 chunk indicizzati in `.index-production/`; query di verifica ("chunking code-aware", "idempotenza re-index", "errore isolato policy") restituiscono risultati pertinenti (score > 0.75). RAG produzione è funzionale.
  - **2 bug di produzione trovati e corretti (PR #4 + #5, merge 505eac9):**
    1. **UnicodeEncodeError su Windows console:** caratteri UTF-8 (→, accenti) causavano crash su console cp1252. **Fix:** funzione `_force_utf8()` in `cli.py` forza stdout/stderr a UTF-8. **Test:** `test_cli_search_with_utf8_output()`. **Lezione:** test mock con `capsys` (UTF-8 default pytest) non riproduce console Windows reale; dogfooding reale necessario.
    2. **Opzioni globali non accettate dopo sottocomando:** `sertor -v search "q"` funzionava, `sertor search -v "q"` dava errore (argparse). **Fix:** parent parser condiviso tra main e subparser, `argparse.SUPPRESS` per celare help duplicato. **Test:** `test_cli_global_flags_order()`. **Lezione:** test unitari passavano lista (skip parsing globale); CLI reale richiede shlex.split() o subprocess.
  - **Valore:** MVP core + CLI completati e dogfoodati; primo entry point eseguibile provato; 2 lezioni di process (test mock insufficiente per bug platform-specific e argparse).
  - **Conformità:** Constitution Check 9/9 (Principi I, IV, VII), Costituzione [[costituzione-v1]] rispettata.
- **Index aggiornato:** nuova sezione "Experiments" con link a `[[dogfooding-produzione-cli]]`.
- **File toccati:** `wiki/experiments/dogfooding-produzione-cli.md` (nuovo), `wiki/index.md`, `wiki/log.md`.

## [2026-06-04] record | FEAT-007 lint semantico del wiki

- **Pagina creata:** `syntheses/lint-semantico-feat007.md` documenta l'estensione semantica di FEAT-007:
  - **Modulo principale:** `semantic_lint(root, llm, facade, *, threshold, k_code, max_pages, pages)` confronta claim wiki col codice reale (via LLM + facade di retrieval) e coerenza interna tra pagine; rileva obsolescenza, contraddizioni, lacune di copertura, sommari stantii.
  - **Provenienza pagine:** frontmatter `provenance: generated|curated` (default curated, sicuro). Funzioni `read_provenance()`, `mark_provenance()` non-distruttive. `distill_artifact()` marca automaticamente pagine generate.
  - **Proposte fix:** `propose_fixes()` genera proposte YAML SOLO per pagine `generated` (riscritture chirurgiche, cancellazioni); non scrive file (phase pre-commit dichiarata). Pagine curate: report only.
  - **Entità:** `Severity` (ordinale) · `SemanticIssueKind` (4 tipi: obsolete-vs-code, internal-contradiction, coverage-gap, stale-summary) · `SemanticIssue` + reasoning LLM · `SemanticReport` (ok su threshold + copertura + pages_without_code_context).
  - **Robustezza:** parsing JSON difensivo, gate pass/fail su threshold severità con override dichiarato, degradazione gradevole senza LLM (report skipped, severity NONE).
  - **Requisiti EARS:** Gruppo H, REQ-070..098; P1 (US1 rilevazione + US2 provenienza) implementate; US4 forma "proposta"; US3 watermark + US5 hook pre-commit rinviati (T100-T103).
  - **Test:** 13 nuovi (test_wiki_semantic_*); mock `ScriptedLLM` per test deterministici. Suite totale 137 verdi, ruff pulito, Constitution Check 9/9 ✅.
  - **Dogfooding (2026-06-04):** Ollama qwen3:30b-a3b su 6/17 pagine wiki produzione (~85 s/pagina). Risultati: (1) run end-to-end OK; (2) corpus sorgenti locale non indicizzato in nomic (`.index-production` Azure 3072-dim) → controllo obsolescenza degradato a coerenza interna; aggiunta segnalazione esplicita `pages_without_code_context` per trasparenza; (3) modello 30B rumoroso (false positive lievi) → conferma perché auto-fix gated. **Lezione:** FEAT-009 (refresh incrementale) prioritaria per supportare lint semantico completo.
  - **Conformità:** Constitution Check 9/9; Principi I (core autonomo), VI (non-distruttività), IX (osservabilità) cardine. Phase pre-commit dichiarata, override possibile.
- **Index aggiornato:** aggiunto link `[[lint-semantico-feat007]]` in Syntheses con descrizione P1+post-MVP.
- **Roadmap aggiornata:** riga FEAT-007 ora specifica "lint semantico: rilevazione+provenienza implementate (P1); incrementale/auto-fix-write/hook pre-commit da fare".
- **File toccati:** `wiki/syntheses/lint-semantico-feat007.md` (nuovo), `wiki/index.md`, `wiki/syntheses/roadmap.md`, `wiki/log.md`.

## [2026-06-04] record | FEAT-007 lint semantico — US3/US4/US5 implementati (scope ampliato)

- **Estensione scope:** le user story 3 (incrementale git-driven), 4-scrittura (applicazione fix su generate) e 5 (gate pre-commit) completate nel flusso SpecKit durante questa sessione (fase specify→plan→tasks→analyze→implement).
- **US3 — Incrementale git-driven:**
  - Nuova `GitPort` (domain/ports.py) con `SubprocessGitAdapter` (adapters/git/) seguendo Principio I (core isolato)
  - Watermark persistito: SHA ultimo commit in `wiki/.sertor/semantic-watermark` (read/write in conventions.py)
  - Mappa entità↔pagine derivata da frontmatter `sources:` (no indice persistito)
  - `semantic_lint_incremental()` riusa facade con fallback working tree (stale-index segnalato, FEAT-009 dichiarata)
- **US4 — Applicazione fix (pagine generate):**
  - Funzione `apply_fixes(report, fixes, *, dry_run=True) -> FixApplication`
  - Applicazione chirurgica su pagine `generated` (rifiuta `curated`)
  - Preserva marcatore `generated` in frontmatter; `delete_page` per obsolete; skipped_no_match per claim non trovato
  - Dry-run default per sicurezza; idempotente (rieseguire = stessa versione)
  - Entità `FixApplication` struttura proposte + stato
- **US5 — Gate pre-commit:**
  - Nuovo servizio `src/sertor_core/services/semantic_gate.py` (fuori dominio wiki, orchestrazione Clean Architecture)
  - `run_semantic_gate()` orchestra: incrementale→apply→soglia→status (pass|warning|blocked)
  - Override tracciato: `override_record` con timestamp + reason
  - CLI `sertor wiki semantic-gate` (flag `--threshold`, `--override`, `--reason`; exit code mapping)
  - Gate eseguito dal configuration-manager PRIMA di commit (correzioni generate entrano stesso commit)
- **Qualità raggiunta:** 155 test verdi + 2 xfail (baseline precision), ruff clean, Constitution Check 9/9 ✅ (Principi I, IV, VI, IX cardine)
- **Spec/plan/tasks:** 21 nuovi test (test_wiki_incremental_*, test_wiki_apply_fixes_*, test_semantic_gate_*, test_cli_semantic_gate_*); SC-006/007/008 verificati
- **Dipendenze:** FEAT-009 (refresh incrementale) dichiarata (MVP fallback working tree); wiring hook git rinviato (configuration-manager)
- **File toccati:** `wiki/syntheses/lint-semantico-feat007.md` (esteso con sezione "Scope ampliato"), `wiki/syntheses/roadmap.md`, `wiki/index.md`, `wiki/log.md`.

## [2026-06-03] record | FEAT-007 manutenzione del wiki

- **Pagina creata:** `syntheses/manutenzione-wiki-feat007.md` documenta il completamento phase 2 di FEAT-007:
  - **Stato:** ✅ 16/16 task completati (US1–US5), 124 test passed + 2 xfail (soglie baseline, non critiche), ruff clean, Constitution Check 9/9 ✅.
  - **Libreria skill:** `src/sertor_core/wiki/maintenance.py` con `lint(root, *, expected=None, fix=False) -> LintReport`, `regenerate_index(root) -> bool`, entità `IssueKind`/`Issue`/`LintReport`.
  - **Estensioni additive:** marcatori catalogo `<!-- sertor:catalog -->` + helper `replace_managed_block()` in `conventions.py`; `distill_artifact()` in `distill.py` per convertire artefatti in documentazione wiki.
  - **Funzionalità lint:** rileva link rotti, pagine orfane, pagine fuori indice, coperture mancanti, contraddizioni marcate. Report-only (fix=True rigenera solo index.md, mai auto-fix link). LintReport.ok = gate di passaggio.
  - **Non-distruttivo & idempotente (Principi IV+VI):** rieseguire linting invariato → stessa report; managed block preserva sezioni a mano.
  - **Distillazione artifact:** converte spec/plan/requisito/discussione in pagine wiki ufficiali con backlink alla sorgente; senza LLM → LLMNotConfiguredError (configurabilità esplicita).
  - **Dogfooding su produzione:** primo `lint('wiki/')` ha scoperto **2 link rotti reali** in `syntheses/chiusura-prototipo-dogfooding.md` (wikilink rotte a epica sertor-cli e architettura-attuale). **Fix applicati**: corretti i nomi dei link / riformulato il testo. Dopo fix: gate verde (16 pagine, 0 problemi). **Lezione**: lo strumento ha rilevato errori di curatela che navigazione manuale non catturava.
  - **Conformità:** R1–R8 implementate; Constitution Check 9/9; Principi I–IX confermati; Principi IV+VI (non-distruttività/idempotenza) cardine della feature.
  - **Artefatti:** `src/sertor_core/wiki/maintenance.py`, `src/sertor_core/wiki/conventions.py` (esteso), `src/sertor_core/wiki/distill.py` (esteso), `specs/005-wiki-manutenzione/{plan,spec,tasks}/*.md`, `tests/**`.
  - **Linkage:** CONSUMA FEAT-003 (operazioni wiki), CONSUMA FEAT-001/002 (nucleo/baseline per distill/index), gate di qualità per feature future.
- **Analisi SpecKit Analyze:** FR 15/15, 0 critical, Constitution Check 9/9 ✅.
- **Processo git:** branch `spec/005-wiki-manutenzione` allineato a master (FEAT-001/002/003/004 mergiati); commit per fase.
- **Index aggiornato:** aggiunto link `[[manutenzione-wiki-feat007]]` in Syntheses con descrizione; sources frontmatter aggiornate con `specs/004-cli-esecuzione/**` + `specs/005-wiki-manutenzione/**`.
- **File toccati:** `wiki/syntheses/manutenzione-wiki-feat007.md` (nuovo), `wiki/index.md`, `wiki/log.md`.
