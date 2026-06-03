# Implementation Plan: Skill — creare/indicizzare l'LLM Wiki

**Branch**: `spec/003-wiki-creazione` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-wiki-creazione/spec.md` (deriva da FEAT-003, fonte
EARS `requirements/sertor-core/wiki-creazione/requirements.md`). **Dipende da FEAT-001** (nucleo) per
l'indicizzazione (Gruppo E). FEAT-001 e FEAT-002 sono in `master`.

## Summary

FEAT-003 è la **skill LLM Wiki**: crea da zero la struttura standardizzata di un wiki di progetto,
la alimenta in modo programmatico (operazioni `record`/`ingest`/`distill`) e la **indicizza nel RAG**
così che la conoscenza distillata (il "perché") diventi recuperabile insieme ai sorgenti, come corpus
paritario (DA-W1, nessun boost). È una **skill** (insieme di operazioni su file Markdown), non un
motore RAG: i Gruppi A–D operano sul filesystem; il Gruppo E **riusa il nucleo** (ingestione/chunking/
embeddings/store di FEAT-001) per indicizzare.

Tecnicamente è un nuovo sottopacchetto `wiki/` dentro `sertor_core`. L'unica nuova dipendenza
architetturale è una porta **`LLMProvider`** (boundary per la generazione), richiesta **solo** dalla
distillazione (REQ-031); tutte le altre operazioni sono LLM-free. L'indicizzazione del wiki riusa
`IndexingService(rebuild=True)` puntato sulla radice del wiki (DRY, REQ-040/041). Il cardine è
l'**idempotenza strutturale** (REQ-050/051): rieseguire un'operazione su input invariato non crea
file, voci di log o chunk duplicati.

## Technical Context

**Language/Version**: Python ≥ 3.11 (eredita dal nucleo).

**Primary Dependencies**: nucleo `sertor_core` (services/indexing, composition, ports); `httpx` per
l'adapter LLM (riusa il pattern degli embeddings). `PyYAML` per il frontmatter (già transitivo via
chromadb; lo dichiariamo esplicito). Nessuna dipendenza pesante nuova.

**Storage**: file system del repository target (cartelle wiki + `index.md`/`log.md`); l'indice
vettoriale del nucleo per il Gruppo E.

**Testing**: `pytest`. Tutti i test su un **wiki sandbox in temp dir** (RNF-002/R-W5, mai sul wiki di
produzione). Distillazione con `FakeLLM` mock; indicizzazione con `FakeEmbedder`+store del nucleo.

**Target Platform**: Linux + Windows (RNF-001), come il nucleo.

**Project Type**: estensione della libreria `sertor_core` — nuovo sottopacchetto `wiki/` (+ adapter
LLM). Non CLI.

**Performance Goals**: scala linearmente col numero di file Markdown (RNF-007); nessuna soglia
assoluta.

**Constraints**: idempotenza strutturale (REQ-050/051); operazioni strutturali **LLM-free** (LLM solo
per distill, REQ-031); RAG non raggiungibile → abort senza corrompere l'indice (REQ-043); segreti solo
da env (REQ-E5); non sovrascrivere un wiki esistente (REQ-002).

**Scale/Scope**: ≥ 2 repository (SC-005); struttura cartelle **fissa** nell'MVP (DA-W6); full rebuild
in indicizzazione (DA-W4); no spider/lint/superficie wiki-nativa/arricchimento (fuori MVP, FEAT-007/008).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** la skill vive in `sertor_core/wiki/`,
  dipende da servizi/porte del nucleo e da una nuova porta `LLMProvider`; non importa SDK concreti né
  la CLI. Indicizzazione delegata al nucleo. Esercitabile con `FakeLLM`/`FakeEmbedder`. → **PASS.**
- [x] **II — Boundary & local-first:** LLM e RAG dietro astrazioni; scelte da config; operazioni
  strutturali funzionano in locale senza cloud/LLM. → **PASS.**
- [x] **III — YAGNI & unità piccole:** indicizzazione **riusa** il nucleo (no duplicazione, DRY); porta
  LLM minimale (solo `generate`); struttura cartelle fissa (no framework di config strutturale). → **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** RAG irraggiungibile → abort senza corrompere
  (REQ-043); LLM assente in distill → `LLMNotConfiguredError` esplicito (REQ-031); wiki esistente → non
  sovrascrive (REQ-002, non-distruttivo). → **PASS.**
- [x] **V — Testabilità & misure:** ogni operazione testabile su wiki sandbox isolato (RNF-002); mock
  LLM/embedder; retrieval del wiki verificato (SC-004). → **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** re-run su input invariato → output identico (REQ-050,
  hash file invariato SC-002); id chunk = path relativo (REQ-051); full rebuild idempotente. → **PASS.**
- [x] **VII — Leggibilità:** naming di dominio (`create`/`record`/`ingest`/`distill`/`index_wiki`). → **PASS.**
- [x] **VIII — Configurabilità centralizzata:** radice wiki, provider LLM, RAG da `Settings`/parametri;
  nessun path hardcoded (REQ-006/RNF-003). → **PASS.**
- [x] **IX — Osservabilità:** ogni operazione emette log strutturati (operazione, file, esito)
  riusando `observability.logging` (REQ-013/RNF-004). → **PASS.**

**Esito gate (pre-Phase 0):** ✅ PASS su tutti i 9 principi (inclusi I e IV). Complexity Tracking vuoto.

> **Nota di evoluzione del nucleo (additiva):** FEAT-003 aggiunge una porta `LLMProvider` + adapter e
> `LLMNotConfiguredError`. È additivo e non-breaking; serve solo alla distillazione.

## Project Structure

### Documentation (this feature)

```text
specs/003-wiki-creazione/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── wiki-operations.md   # create / record / ingest / distill
│   └── wiki-indexing.md     # index_wiki (riuso nucleo)
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/sertor_core/
├── wiki/                       # NUOVO — skill LLM Wiki
│   ├── __init__.py
│   ├── conventions.py          # struttura cartelle, frontmatter, kebab-case, formato log (REQ-003/004/005)
│   ├── structure.py            # create_wiki(root): init non-distruttivo (REQ-001/002)
│   ├── operations.py           # record(), ingest() — LLM-free (REQ-010..013, 020..023)
│   ├── distill.py              # distill() — richiede LLMProvider (REQ-030..033)
│   └── indexing.py             # index_wiki(): riusa IndexingService(rebuild=True) (REQ-040..045)
├── domain/
│   ├── ports.py                # + LLMProvider (Protocol) [additivo]
│   └── errors.py               # + LLMNotConfiguredError [additivo]
├── adapters/llm/               # NUOVO — adapter LLM (solo per distill)
│   ├── __init__.py
│   ├── ollama.py               # chat locale (/api/chat)
│   └── azure.py                # chat cloud (/chat/completions)
└── composition.py              # + build_llm(settings) [additivo]

tests/
├── unit/
│   ├── test_wiki_structure.py      # create + convenzioni (US1)
│   ├── test_wiki_operations.py     # record + ingest (US2/US5)
│   └── test_wiki_distill.py        # distill con FakeLLM + errore senza LLM (US6)
├── integration/
│   ├── test_wiki_indexing.py       # index_wiki nel RAG + retrieval (US3)
│   └── test_wiki_idempotence.py    # re-run identico (US4, SC-002)
└── fixtures/                       # + FakeLLM
```

**Structure Decision**: sottopacchetto `wiki/` dentro `sertor_core` (le skill wiki fanno parte del
core per costituzione). L'indicizzazione **consuma** il nucleo (DRY, niente reimplementazione del
RAG). La porta `LLMProvider` è il solo nuovo boundary, isolato e usato unicamente dalla distillazione.

## Complexity Tracking

> Nessuna violazione del Constitution Check.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
