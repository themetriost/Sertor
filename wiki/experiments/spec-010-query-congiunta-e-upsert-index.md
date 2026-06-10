---
title: Feature 010 — Query congiunta multi-collezione & upsert-index in CLI (pezzi D residui di FEAT-003)
type: experiment
tags: [feat-003, spec-010, wiki, speckit, query-multi-collezione, upsert-index-cli]
created: 2026-06-10
updated: 2026-06-10 (implement completata + PR #20; corretto il naming FEAT-010 → feature/spec 010)
sources: [
  "specs/010-query-congiunta-e-upsert-index/",
  "requirements/sertor-core/query-congiunta-e-indice/requirements.md",
  "CLAUDE.md (Domande all'utente)"
]
---

# Feature 010 — Query congiunta multi-collezione & `upsert-index` in CLI

Record datato (2026-06-10) della feature **`specs/010`**: i due **pezzi deterministici (D) residui
della feature Wiki (FEAT-003** dell'epica — *non* confondere col numero di spec, vedi il banner "due
numerazioni" in [[roadmap]]), portati da requirements a implementazione in un **unico flusso SpecKit
completo** nella stessa giornata. Branch `010-query-congiunta-e-upsert-index`, **PR #20 mergiata su
`master`** lo stesso giorno (merge `74783db`).

## Contesto

Restavano due lacune deterministiche per la visione «una sola verità interrogabile»: (A) wiki e codice
in collezioni RAG separate ma `search_combined` interrogava **una sola** collezione; (B) `upsert_index()`
esisteva nel nucleo ma non era esposto in CLI. Il terzo pezzo (`sertor wiki init`) è rimandato all'epica
CLI. Requisiti a monte: [`requirements/sertor-core/query-congiunta-e-indice/requirements.md`](../../requirements/sertor-core/query-congiunta-e-indice/requirements.md)
(gruppi EARS A/B: REQ-A1..A9, REQ-B1..B8).

## Le 4 decisioni del clarify (Session 2026-06-10)

1. **Provider di embeddings eterogenei** tra le collezioni → **errore esplicito** (`ProviderMismatchError`,
   fail-fast): deroga deliberata alla policy tollerante della facade — meglio nessuna risposta che una
   fusione di score incomparabili.
2. **Individuazione della seconda collezione** → da **configurazione centrale** (`Settings.extra_corpora`,
   env `SERTOR_EXTRA_CORPORA`); consumatori invariati ([[thin-consumer]], «default solo in Settings»).
3. **Sommario multilinea a `upsert-index`** → errore esplicito, nessuna normalizzazione silenziosa
   ([[deterministic-vs-judgment|confine D↔N]]: la CLI piazza fedelmente, non ripara).
4. **Fan-out solo per `search_combined`** — `search_code`/`search_docs` invariati (zero cambi di
   semantica per i consumatori esistenti).

## Esito dell'implementazione (stesso giorno)

- **US1 (query congiunta):** fan-out + merge nella `RetrievalFacade` (porta `query` invariata); merge per
  `(-score, chunk_id)` deterministico; degradazione su corpus mai indicizzato; nuova capacità di porta
  `VectorStore.list_collections()` (Chroma, Azure Search, mock) per distinguere "mai indicizzato" da
  "indicizzato con altro provider". Dettagli evergreen in [[indexing-and-retrieval]] e [[ports-adapters]].
- **US2 (`upsert-index` in CLI):** sottocomando idempotente (`--page` + `--summary` o stdin UTF-8),
  contratto `wiki.upsert_index/1` (insert/update/noop), validazione del sommario. Dettagli in [[wiki-tools]].
- **Qualità:** suite `not cloud` **159 verdi** (+24 nuovi test) + 2 xfail noti di misura; ruff pulito;
  Constitution Check v1.1.0 **10/10** pre e post design.
- **Validazione live sul dogfood:** costruita la collezione `wiki__azure_text_embedding_3_large` (49 doc)
  in `.index-sertor/`; con `SERTOR_EXTRA_CORPORA=wiki` la combinata fonde davvero hit dal wiki e dal codice.

## Governance emersa

Nuova regola in `CLAUDE.md` (sezione *Domande all'utente*, nata durante il clarify): ogni domanda va
preceduta dal **contesto** (origine del problema, implicazioni concrete delle opzioni, raccomandazione
motivata) — mai opzioni "secche".

## Post-merge (2026-06-10)

- ✅ `SERTOR_EXTRA_CORPORA=wiki` nel `.env`: la combinata fonde codice+wiki **dalla sola config**
  (verificato live post-merge); entrambi i corpora ri-costruiti (regola di re-index, momento obbligato).
- ☐ Riavvio del **server MCP** per servire il nuovo codice (alla prossima sessione).
- ☐ Decidere l'**esclusione di `wiki/` dal corpus primario** (`SERTOR_EXCLUDE_PATTERNS`) — il corpus
  `sertor` indicizza anche `wiki/` → quasi-duplicati nella combinata (deliberato: niente dedup, R5 YAGNI).

## Artefatti

`specs/010-query-congiunta-e-upsert-index/` — spec (con Clarifications), plan (research R1–R8, data-model,
contratti `combined-search`/`cli-upsert-index`, quickstart), tasks 22/22. Commit principali: `00e9a34`
(spec+clarify), `ee89a39` (plan), `b2c0a74` (tasks), `42bd6ac` (implement).

## Link correlati

- [[indexing-and-retrieval]] · [[ports-adapters]] · [[wiki-tools]] — le pagine evergreen che ospitano le entità.
- [[deterministic-vs-judgment]] — il confine che governa upsert-index e la policy fail-fast.
- [[roadmap]] — stato di prodotto e banner sulle due numerazioni (`FEAT-NNN` ≠ `specs/NNN`).
