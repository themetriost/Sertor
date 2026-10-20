# Implementation Plan: Memoria semantica che regge i turni grandi e i rifiuti del provider

**Branch**: `145-memoria-semantica-turni-grandi` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/145-memoria-semantica-turni-grandi/spec.md` (E4-FEAT-016,
REQ-033..036)

## Summary

`MemorySemanticIndex.index_session` manda ogni turno intero al provider e, al primo rifiuto, conta in
errore tutti i turni nuovi della sessione con un motivo sbagliato. La correzione resta tutta nel servizio
`services/memory_semantic.py` e nel formatter CLI:

1. i turni oltre `SERTOR_MAX_CHUNK_TOKENS` sono spezzati con `cap_to_tokens`, lo stesso tetto del
   corpus; i turni entro il budget conservano identità e payload (nessun rebuild);
2. su un rifiuto del testo (`http 400/413/422`) un ripiego per pezzo confina l'errore ai turni rifiutati;
3. l'esito porta l'elenco dei turni rifiutati (sessione, turno, motivo) e gli eventi distinguono
   `input_rejected` da `provider_unavailable`, restando metrics-only;
4. la ricerca restituisce un risultato per turno.

Decisioni e alternative: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11+ (come il resto di `sertor-core`)

**Primary Dependencies**: nessuna nuova. `tiktoken` resta opzionale (extra `tokenizer`), con il ripiego
prudente già esistente.

**Storage**: collezione vettoriale della memoria (Chroma in locale) — stessa collezione, id compatibili.

**Testing**: pytest, offline, embedder e store finti (`tests/fixtures/mocks.py` + `IncrementalStore`);
round-trip su Chroma reale già presente nella suite della 072.

**Target Platform**: Windows/Linux/macOS, ogni ospite con la memoria semantica accesa.

**Project Type**: libreria + CLI (`sertor-core`).

**Performance Goals**: costo invariato sul percorso normale (una chiamata `embed()` per sessione); il
ripiego per pezzo esiste solo sulle sessioni con un rifiuto.

**Constraints**: incrementalità invariata (zero chiamate su indice completo); esito CLI invariato in
assenza di rifiuti; nessun testo né id di sessione negli eventi.

**Scale/Scope**: ~150 righe di produzione in 2 file, test in 3 file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.6.0).

- [x] **I — Dipendenze verso l'interno:** PASS. Il servizio usa solo le porte `EmbeddingProvider`/
  `VectorStore` e una funzione pura di `services/chunking`; nessun SDK.
- [x] **II — Boundary & local-first:** PASS. Nessuna dipendenza esterna nuova; il criterio di rifiuto
  usa il `reason` già normalizzato dagli adapter.
- [x] **III — YAGNI & unità piccole:** PASS. Riuso di `cap_to_tokens` e di `SERTOR_MAX_CHUNK_TOKENS`
  invece di una manopola nuova; ripiego lineare invece di bisezione.
- [x] **IV — Errori espliciti:** PASS. L'errore resta un `EmbeddingError` di dominio; il report rende
  esplicito chi è stato rifiutato invece di un conteggio cieco. Tutto o niente per turno: nessuno stato
  parziale nello store.
- [x] **V — Testabilità & misure:** PASS. Il caso di Kaelen diventa un test con embedder che applica il
  limite; SC-001..006 hanno ciascuno un test.
- [x] **VI — Idempotenza:** PASS. Id deterministici (turno o turno/pezzo), `upsert` idempotente; turni
  entro il budget con id invariato.
- [x] **VII — Leggibilità:** PASS.
- [x] **VIII — Configurabilità centralizzata:** PASS. Budget e overlap da `Settings`
  (`max_chunk_tokens`, `chunk_overlap`); l'insieme dei motivi di rifiuto è una costante del servizio
  perché descrive la semantica HTTP, non una scelta dell'ospite.
- [x] **IX — Osservabilità:** PASS. Nuovo motivo `input_rejected` e conteggio `rejected` negli eventi.
- [x] **X — Host-agnostico:** PASS. Nessun ramo per assistente; opera su `memory.sqlite`.
- [x] **XI — Consumo via vehicles:** PASS. Esposto tramite `sertor-rag memory index-semantic` e
  l'indicizzazione automatica; nessun consumatore importa il core.
- [x] **XII — Fail Loud, Fix the Cause:** PASS. È esattamente la correzione: la causa (turno troppo
  grande) viene rimossa spezzando, e il rifiuto residuo è nominato invece di sparire in un conteggio.
- [x] **XIII — Product vs Fixture Plane:** PASS. Il caso è reale-utente (nodo Kaelen); nessun
  workaround sul dogfood.
- [x] **XIV — Derived State, Not Declared:** PASS. Il budget non è duplicato (stessa manopola del
  corpus); «già indicizzato» resta derivato dallo store.
- [x] **Allineamento alla missione:** PASS. Una sessione mancante dall'indice è una risposta falsa
  all'agente («non ne abbiamo parlato»); la correzione riguarda la recall resa all'agente.

**Re-check post-design:** invariato, tutti PASS. Nessuna voce in Complexity Tracking.

**Feature completa = installabile (regola 1 di `CLAUDE.md`):** soddisfatta per costruzione — la
correzione viaggia nel pacchetto `sertor-core`; nessun asset host-facing, nessuna manopola nuova.
**Documentazione utente (regola 3):** `docs/retrieval.md` nomina il backfill; si aggiunge che i turni
grandi sono spezzati con `SERTOR_MAX_CHUNK_TOKENS` e che l'esito elenca i turni rifiutati; voce in
`CHANGELOG.md` §Unreleased.

## Project Structure

### Documentation (this feature)

```text
specs/145-memoria-semantica-turni-grandi/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/memory-semantic-index.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
src/sertor_core/
├── services/memory_semantic.py   # unità per turno, ripiego, RejectedTurn, dedup in ricerca
└── cli/output.py                 # format_semantic_index_report: righe/campo `rejected`

tests/unit/
├── test_memory_semantic.py       # caso Kaelen, rifiuto mirato, incrementalità, dedup, eventi
├── test_cli_memory_semantic.py   # esito umano/JSON con e senza rifiuti
└── test_memory_archive_semantic.py  # invariato (regressione)

docs/retrieval.md · CHANGELOG.md  # documentazione utente
```

**Structure Decision**: modifica localizzata nel servizio esistente della 072 e nel suo formatter; nessun
file nuovo di produzione.

## Complexity Tracking

Nessuna violazione.
