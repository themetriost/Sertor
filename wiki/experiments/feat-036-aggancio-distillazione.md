---
title: FEAT-036 — Aggancio della distillazione all'archivio episodico
type: experiment
tags: [memoria-conversazioni, distillazione, wiki, operazione-distill]
created: 2026-06-14
updated: 2026-06-14
sources: ["specs/036-aggancio-distillazione/**", "src/sertor_core/adapters/memory/archive.py", "src/sertor_core/cli/__main__.py", ".claude/skills/wiki-author/ops/distill.md"]
---

# FEAT-036 — Aggancio della distillazione all'archivio episodico

**Completamento 2026-06-14.** Feature che chiude il loop cattura→distillazione dell'epica Memoria conversazioni: l'archivio episodico (FEAT-001 cattura + FEAT-002 ricerca) diventa una FONTE RECUPERABILE per l'operazione `distill` del wiki — finora teorica, pretendeva un brief scritto a mano su trascrizione grezzo (non era legale).

## Consegna

**PR #51 mergiata su master** (merge commit 88088fe). Due commit: 1cb6f69 (docs), 399e2e2 (feat+test+wiring).

### Pezzi consegnati (thin consumer additivo, zero nuove porte)

**Core (`src/sertor_core/adapters/memory/archive.py`):**
- Metodo nuovo **`list_recent(limit)`** di `MemoryArchive` — elenco sessioni recenti, ordinato per recency-first, metadati di sessione (chiave, captured_at, turn_count con fallback COUNT(*)), degrado non-fatale.
- Entità di dominio `SessionSummary(session_key, captured_at, turn_count)` in `domain/memory.py`.
- Eccezione `SessionNotFoundError` in `domain/errors.py`.
- Factory `build_memory_reader(settings) → MemoryArchive|None` gated su `SERTOR_MEMORY` in `composition.py`.
- Manopola `Settings.memory_list_limit` (env `SERTOR_MEMORY_LIST_LIMIT`, default 20).

**CLI (`src/sertor_core/cli/__main__.py` + `cli/output.py`):**
- Sottocomandi nuovi: 
  - `sertor-rag memory show <session_key> [--json]` — trascrizione intera di una sessione (non troncata); not-found → `SessionNotFoundError` exit 1 DISTINTO da sessione vuota exit 0; gate `None` → `ConfigError` exit 1.
  - `sertor-rag memory list [-k N] [--json]` — elenco sessioni recenti; stessi gate.
- Funzioni pure in `output.py`: `format_session_transcript` e `format_session_list`.
- Evento osservabilità: `memory_show`/`memory_list` registra solo conteggi+chiave opaca (mai contenuto).

**Wiring distill (`.claude/skills/wiki-author/ops/distill.md`):**
- Modalità «from conversation» della procedura `distill` — attinge all'archivio via comandi `memory list`/`memory show`; ribadito vincolo **FR-013: distillazione SEMPRE su singola sessione mirata, su invocazione esplicita; MAI intero archivio, MAI automatica.**

**Asset canonico (packages):**
- `.../assets/claude/skills/wiki-author/ops/distill.md` (anti-drift, specchio della versione viva).

## Vincolo cardine: FR-013 (cattura economica, distillazione costosa)

L'archivio è memoria di **backup (cold storage)**, non RAM né HD da consultazione quotidiana.

- **Cattura (FEAT-001):** economica (I/O + regex JSONL, zero LLM).
- **Distillazione (FEAT-003):** costosa (giudizio LLM). Acceso SOLO su invocazione esplicita, su sessione singola mirata.
- **Archivio:** decoupled da distill; il distill giornaliero (step-driven) resta invariato e **non** tocca l'archivio.

Non automatismo a fine-sessione (no trigger SessionEnd per distill); non per-turno; non su intero archivio (vincolo di confine / responsabilità).

## Qualità

- **Constitution Check:** PASS 10/10 senza deroghe.
- **Test:** 558 test non-cloud verdi (31 nuovi: `test_cli_output_session.py`, `test_memory_archive_list_recent.py`, `test_cli_memory_show_list.py`).
- **Ruff:** clean su file toccati.
- **Additivo puro:** `SERTOR_MEMORY` spento → nulla cambia.
- **Validazione live:** `memory list`/`show` eseguiti su archivio dogfood reale (36 sessioni, 5062 turni).

## SpecKit

Pipeline completa **specify→plan→tasks→analyze→implement** in giornata.

- **Spec:** `specs/036-aggancio-distillazione/spec.md`.
- **Plan:** `specs/036-aggancio-distillazione/plan.md`.
- **Research:** `specs/036-aggancio-distillazione/research.md` — 8 decisioni D1–D8 documentate (non-full-history, edge case archivio assente, idempotenza della query `show`).
- **Artefatti:** tasks, design, contracts, quickstart.

## Legami

Pagine correlate:

- [[memoria-conversazioni]] — il concetto di tier episodico.
- [[transcript-capture-adapter-e-storage]] — i componenti della cattura (FEAT-001).
- [[ricerca-episodica-fts5]] — il motore di query dell'archivio (FEAT-002).
- [[feat-035-superficie-cli-memoria-hook-sessionend]] — la superficie CLI precedente (memoria archive/search).
- [[diary-vs-graph]] — il confine diario (log append-only) ↔ grafo (pagine aggiornate in place); distill è il "travaso" fra i due.
- [[deterministic-vs-judgment]] — distill è **giudizio LLM**, non meccanico; per questo l'operazione impone l'invocazione esplicita.

## Note

**DA-W1 parzialmente risolta da questa feature:** un archivio grezzo di sessioni diventa una **fonte** legale per `distill` — il wiki acquista consapevolezza della memoria episodica.

Residui per FEAT-003:
- **Corpus distillato:** ove vivono le entità estratte da una sessione (oggi: intero wiki); da chiarire confine episodio ↔ corpus.
- **Validazione semantica:** finora il distill è giudizio puro; accertare che la distillazione non contraddica il wiki esisting.
- **Trigger ricerca:** il workflow di ricerca all'interno di un archivio grande (36 sessioni/5062 turni) va testato a carico.

## Prossimo

- Distillazione vera da un transcript reale (FEAT-003 full).
- Should dell'epica memoria (retention, distillazione semantica, multi-assistente).
