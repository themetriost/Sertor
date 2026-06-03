---
title: Implementazione FEAT-003 skill LLM Wiki
type: synthesis
tags: [feat-003, wiki, skill, production]
created: 2026-06-03
updated: 2026-06-03
sources: ["specs/003-wiki-creazione/plan.md", "specs/003-wiki-creazione/tasks.md", "src/sertor_core/wiki/**", "requirements/sertor-core/wiki-creazione/requirements.md"]
---

# Skill LLM Wiki — FEAT-003 Completamento

## Stato

✅ **COMPLETATO**: 21/21 task (Phase 1–5), 84 test passed + 2 xfail (soglie di pertinenza motori standard, non di questa feature), ruff clean, **Constitution Check 9/9 ✅**.

## Cosa è stata costruita

Una **skill LLM Wiki** — insieme di operazioni sulla struttura wiki di un progetto, risiede in
`src/sertor_core/wiki/`, è un sottopacchetto **LLM-free** per operazioni strutturali e include un'adapter
LLM (Ollama/Azure) **solo per la distillazione** (REQ-031).

### Componenti principali

| Modulo | Responsabilità |
|--------|---|
| `conventions.py` | Enumerazione aree tematiche → cartelle, Brief/SourceBrief, frontmatter YAML, kebab-case, formato log |
| `structure.py` | `create_wiki()` — inizializza cartelle/index.md/log.md non-distruttivo (REQ-001/002) |
| `operations.py` | `record()`/`ingest()`/`distill()`/`query()` — operazioni su file wiki con idempotenza strutturale |
| `indexing.py` | `index_wiki()` — riusa IndexingService del nucleo, full rebuild, idempotente (REQ-040/041) |
| Adapter LLM (`adapters/llm/{ollama,azure}.py`) | Chat completions via httpx; `build_llm()` in composition |

### Estensioni additive al nucleo

- **Porta `LLMProvider`** in `domain/ports.py`: metodo `generate(prompt, system=None) -> str`
- **Eccezione `LLMNotConfiguredError`** in `domain/errors.py`: sollevata da `distill()` se LLM non configurato (REQ-031, Principio IV esplicito)
- **Chiavi chat in Settings:** `llm_model` (Ollama), `llm_deployment` (Azure)

Tutte le estensioni sono **non-breaking** e **testabili** con mock (FakeLLM).

## Decisione di design chiave: Idempotenza strutturale (REQ-050)

Rieseguire un'operazione con lo stesso input — su un'intera sessione a giorni diversi — produce file con **hash identico**:

- **create_wiki**: crea cartelle/index.md/log.md solo se assenti (mai riscritti).
- **record/ingest**: confrontano il contenuto renderizzato ignorando la riga `updated:` prima di scrivere; se invariato, il file non è toccato.
  - `created` preservato (registra il giorno della creazione originale).
  - `updated` cambia solo a modifica reale del corpo.
- **index.md/log.md**: mai riscritti retroattivamente.
- **distill**: idempotente sulla **STRUTTURA** (layout pagina, sezioni); il contenuto generato dall'LLM è deterministico (FakeLLM nei test).
- **Log append-only**: voce aggiunta solo se operazione ha effet reale (REQ-005).

**Conseguenza**: full rebuild su corpus invariato ha SC-002 garantito (hash identico).

## Stack reale e supporto provider

### Dipendenze nuove (esplicite)

- `PyYAML` (già transitivo; dichiarato esplicito): parse/render frontmatter YAML
- `httpx`: adapter LLM (pattern riusato da embeddings)
- `python-dotenv`: segreti LLM da env

### Provider LLM

| Backend | Adapter | Endpoint | Requisito |
|---------|---------|----------|-----------|
| Ollama | `adapters/llm/ollama.py` | `/api/chat` | `OLLAMA_HOST`, modello env |
| Azure OpenAI | `adapters/llm/azure.py` | `/chat/completions` | `AZURE_OPENAI_*`, lazy import (`[azure]` extra) |

**Local-only**: `RAG_BACKEND=local` → Ollama, zero cloud SDK obbligatorio.

## Test e copertura

| Categoria | Count | Note |
|-----------|-------|------|
| Unit (wiki_structure.py) | 18 | create, re-invoke, frontmatter, kebab-case, log format |
| Unit (operations.py) | 24 | record, ingest, distill, query; idempotenza; voci log; backlink |
| Unit (indexing.py) | 16 | index_wiki, rebuild idempotente, radice vuota → warning, RAG irraggiungibile → errore |
| Integration (E2E) | 14 | Creazione wiki → record → query → indexing ciclo completo |
| Error handling | 8 | LLMNotConfiguredError, wiki esistente, collisioni path |
| Config/Logging | 4 | Settings chiavi LLM, logging strutturato |
| **Totale** | **84 passed + 2 xfail** | xfail = threshold pertinenza motori (non rilevante per FEAT-003) |

### Test suite (sandbox)

Tutti i test eseguono su **wiki sandbox in temp dir** (RNF-002, R-W5). Nessun test tocca il wiki di produzione. FakeLLM (generatore deterministico) usato per distillazione.

**Ruff clean**: zero warning, codice conforme pep8.

## Conformità e governance

### Constitution Check ✅ 9/9

| Principio | Status | Note |
|-----------|--------|------|
| I. Core a dipendenze interne | ✅ PASS | `wiki/` in sertor_core, delega al nucleo, esercitabile con mock |
| II. Boundary & local-first | ✅ PASS | LLM/RAG dietro astrazioni, operazioni strutturali local-only |
| III. YAGNI & unità piccole | ✅ PASS | Indicizzazione riusa nucleo (DRY); porta LLM minimale; struttura fissa |
| IV. Errori espliciti (NON-NEGOZIABILE) | ✅ PASS | LLMNotConfiguredError, wiki non-distruttivo, RAG fallisce esplicitamente |
| V. Testabilità | ✅ PASS | 84 test su sandbox isolato, mock per LLM/embedder, SC verificati |
| VI. Idempotenza & non-distruttività | ✅ PASS | Re-run invariato → hash file identico, id chunk = path relativo |
| VII. Leggibilità | ✅ PASS | Naming di dominio (create/record/ingest/distill/index_wiki) |
| VIII. Configurabilità | ✅ PASS | Radice wiki, provider, RAG da Settings; nessun path hardcoded |
| IX. Osservabilità | ✅ PASS | Log strutturati per ogni operazione |

**Principi I e IV NON-NEGOZIABILI**: confermati in design e implementazione.

### Analisi SpecKit Analyze

- Functional Requirements: 13/13 ✅
- Non-functional: 7/7 ✅
- Critical issues: 0
- Constitution Check: 9/9 ✅

## Riuso del nucleo: Indicizzazione DRY (REQ-040/041)

**Non è stata implementata una indicizzazione custom.** La skill **riusa il nucleo**:

```python
# Pseudo-codice
def index_wiki(wiki_root: Path, rag_backend) -> None:
    indexing = IndexingService(rag_backend)
    indexing.index(
        source_root=wiki_root,
        rebuild=True,
        corpus_id="wiki"  # namespace separato
    )
```

- **ID chunk = path relativo**: consente di identificare quale file/sezione è stata recuperata (REQ-051).
- **Full rebuild**: semplice, idempotente (REQ-044).
- **Store irraggiungibile**: errore propagato (REQ-043), nessun tentativo di correzione automatica.
- **Radice wiki vuota**: warning (nessun file .md), indice non modificato (REQ-045).

## Operazioni pubbliche (API pubblica)

| Funzione | Firma | Esito |
|----------|-------|-------|
| `create_wiki` | `(root: Path, today: date \| None) -> None` | Crea struttura; non-distruttivo |
| `record` | `(root: Path, brief: Brief) -> Page` | Crea/aggiorna pagina da Brief; appendere a log |
| `ingest` | `(root: Path, brief: SourceBrief, section: str) -> Page` | Crea pagina da fonte esterna; appendere a log |
| `distill` | `(root: Path, brief: Brief, llm: LLMProvider) -> Page` | Riassumi con LLM; genera sections da prompt |
| `query` | `(root: Path, question: str) -> List[Section]` | Cerca sezioni in wiki (by content) |
| `index_wiki` | `(wiki_root: Path, rag_backend: RAGBackend) -> None` | Indicizza nel RAG; full rebuild |

Tutte esportate in `src/sertor_core/__init__.py` (API pubblica).

## Ciclo di vita e processo git

### Branch e commit

- **Branch**: `spec/003-wiki-creazione`
- **Stato**: allineato a master (merge FEAT-002 in 4564e77)
- **Commit per fase**:
  - Piano SpecKit (40d437e)
  - Task list e design (57a4e50)
  - Implementazione fase 1–5 (incrementale)

### Integrazione dogfooding

Questa skill **automatizza esattamente** la manutenzione del wiki che oggi facciamo a mano (agente `wiki-keeper`). Rende il wiki:

1. **Creabile programmaticamente** (non bootstrapping manuale)
2. **Aggiornabile via brief LLM-free** (record/ingest/query)
3. **Indicizzabile nel RAG** come corpus paritario (DA-W1: wiki = corpus + superficie)
4. **Interrogabile dal RAG** (future: skill surface queries)

## Chiusura del cerchio (MVP)

FEAT-003 **chiude il loop MVP di Sertor Core**:

- **FEAT-001**: Nucleo retrieval (ingestione, chunking, embeddings, store)
- **FEAT-002**: Motore baseline (indexing, query, ranking, evaluation)
- **FEAT-003** ← **qui**: Skill wiki (creazione, operazioni, indicizzazione, query)

Il wiki di produzione stesso è NOW creabile e interrogabile con gli stessi strumenti che distribuiamo.

## Post-MVP (FEAT-004–008, fuori scope)

- FEAT-004: Hybrid search (Azure AI Search / BM25 + dense + reranking)
- FEAT-005: GraphRAG (AST + knowledge graph)
- FEAT-006: Agentic RAG (multi-agente iterativo)
- FEAT-007: Spider & surface wiki (link verification, query surfaces, arricchimento)
- FEAT-008: Bidirezionale (wiki → agente ingestion source)
- **FEAT-009** ← **Nuovo**: Refresh incrementale corpus (necessità emersa da Decomposizione Must)

---

## Backlink

- [[implementazione-nucleo-retrieval]] — FEAT-001 base
- [[motore-baseline-feat002]] — FEAT-002 dipendenza
- [[costituzione-v1]] — governance 9 principi
- [[ruolo-wiki-da-w1]] — identità wiki (corpus × superficie)
- [[decomposizione-must-core]] — contesto Must/Should/Could
