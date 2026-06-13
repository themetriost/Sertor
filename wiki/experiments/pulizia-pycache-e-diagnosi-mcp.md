---
title: Pulizia pycache fantasma e diagnosi .mcp.json (2026-06-05)
type: experiment
status: superseded
superseded_by: mcp-server
tags: [cleanup, diagnostica, mcp, architettura, branch, master, diagnosi-storica]
created: 2026-06-05
updated: 2026-06-13
sources: ["master (HEAD a4640b8)", ".mcp.json", "src/sertor_core/**"]
---

# Pulizia pycache fantasma e diagnosi MCP (2026-06-05)

> **⚠️ Superata (2026-06-06; convenzione di supersession applicata 2026-06-10, FR-017/SC-009 — vedi
> playbook §4 *Verità, autorità e obsolescenza*):** la diagnosi è contraddetta dalle **decisioni
> registrate** PR #13 e PR #15 (autorità sul perché) e dallo stato reale di `master` → verità corrente in
> [[mcp-server]] e [[wiki-tools]]. Questa pagina fotografa lo stato a `master @ a4640b8`
> (2026-06-05). **Da allora la realtà è cambiata** — le rettifiche, per evitare che un agente legga claim
> stantii al presente:
> - **`src/sertor_mcp/` è ora su master** (FEAT-MCP, **PR #15 mergiata**) — non più "solo su branch / PR non mergiata".
> - **Il nucleo wiki deterministico è su master** come `src/sertor_core/wiki_tools/` (FEAT-003-D, **PR #13 mergiata**).
> - **`.mcp.json` è stato ri-puntato alla produzione**: ora invoca `sertor_mcp.server` con `SERTOR_CORPUS=sertor`
>   (non più il server prototipo rotto; lo status "inerte, da riprendere post-merge" non vale più).
> - Su branch resta **solo la CLI** (`src/sertor_cli/`); MCP e wiki-core sono mergiati.
>
> Il corpo sottostante è lasciato **invariato** come registro della diagnosi alla sua data.

## Contesto

Durante il lint semantico di allineamento del 2026-06-04, è stata segnalata la presenza di cartelle `__pycache__` fantasma in `src/` che non corrispondevano a file sorgenti effettivi. Inoltre, il server MCP dogfooding (`.mcp.json` → `prototype/04-agentic-rag/mcp_server.py`) è stato identificato come rotto.

## Cleanup eseguito (2026-06-05)

### Rimozione pycache

- **Cartelle rimosse:** 16 directory `__pycache__` da `src/sertor_core/` (bytecode `.pyc` residui).
- **Directory vuote ripulite:** 6 directory rimaste vuote dopo la rimozione:
  - `src/sertor_cli/`
  - `src/sertor_cli/commands/`
  - `src/sertor_core/adapters/git/`
  - `src/sertor_core/adapters/llm/`
  - `src/sertor_core/wiki/`
  - `src/sertor_mcp/`
  
### Causa identificata

I `.pyc` fantasma provenivano dal **checkout di altri branch** (feature/mcp-sertor-core, spec/005-llm-wiki) che compilano durante la loro sessione, e rimangono in disco tornando su `master`. Tutti gitignored e **non tracciati** → niente da committare.

**Conseguenza chiave:** questi file facevano *sembrare* presenti moduli che in realtà **non vivono su master** (CLI, MCP, modulo wiki).

## Diagnosi architetturale: cosa è realmente su master

Su `master` (HEAD a4640b8) esiste **solo** `src/sertor_core/`:
- `domain/` (entità, porte, errori)
- `services/` (ingestion, chunking, indexing, retrieval)
- `adapters/{embeddings, vectorstores}/` (provider implementazioni)
- `engines/` (motore baseline)
- `config/`, `observability/`, `composition.py`

**NON su master (vivono solo sui branch):**
- `src/sertor_cli/` → branch sconosciuto
- `src/sertor_mcp/` → branch `feat/mcp-sertor-core` (PR #12 aperta, non mergiata)
- `src/sertor_core/wiki/` → branch `spec/005-llm-wiki` (contenuto in FEAT-010, PR #11 aperta, non mergiata)

Questo è **coerente** col fatto che FEAT-003 (wiki) e FEAT-010 (wiki skill/agente) sono in PR non mergiate.

## Diagnosi .mcp.json

Il server MCP puntato da `.mcp.json` è **rotto** perché:

### Problema

- `prototype/04-agentic-rag/mcp_server.py` carica **tutti e 4 gli approcci RAG** (01–04).
- Ogni approccio ha dipendenze distinte (es. `01-baseline` → `chromadb`, `rank_bm25`; `04-agentic-rag` → `mcp`, `sentence_transformers`).
- I due venv complementari non coprono l'unione:
  - `.venv/` ha `chromadb` + basics, ma **manca `mcp`, `rank_bm25`, `sentence_transformers`**.
  - `.venv-core/` ha `mcp` + core, ma **manca lo stack retrieval del prototipo** (`chromadb`, `networkx`, `rank_bm25`, ecc.).
- Risultato: `ModuleNotFoundError` alla partenza del server.

### Decisione presa (da utente)

**NON rianimare il vecchio server agentico.** Rimane known-broken, pendente:
- Causa: il server prototipo appartiene alla *exploration phase* (isolata); no priorità su `master`.
- Fix:** `.mcp.json` sarà ri-puntato al nuovo server `sertor_mcp` (branch `feat/mcp-sertor-core`) **quando sarà mergiato su master** (probabilmente in FEAT-010 o successivo).

**Configurazione attuale:**
- `.mcp.json` → `prototype/04-agentic-rag/mcp_server.py` (**rotto, non usato**)
- Flag: **status = inerte, da riprendere post-merge**

## Consequenze operative

1. **`master` è pulito:** no `__pycache__` fantasma, nessun bytecode stale.
2. **Architettura chiara:** `sertor_core` è completo e self-contained; CLI/MCP/wiki vivono su branch.
3. **MCP dogfooding:** per interrogare il prototipo via RAG, usare il server prototipo una volta che `.mcp.json` sarà aggiornato (post-merge `feat/mcp-sertor-core`). Nel frattempo, consultare il prototipo tramite `Read` diretto o RAG indipendente se necessario.

## Linkage

- [[corpus-index-naming]] — schema corpus `sertor` (prodotto) vs `prototype` (dogfooding), indici isolati.
- [[step-ritual]] — il lint semantico che ha rilevato questi problemi.
- `CLAUDE.md` § "Riferirsi al prototipo" — updated per corpus `prototype`.
