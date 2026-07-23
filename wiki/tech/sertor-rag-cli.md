---
title: sertor-rag — la CLI di esecuzione RAG
type: tech
tags: [cli, retrieval, thin-consumer, dogfooding, produzione]
created: 2026-06-11
updated: 2026-07-23
sources: ["src/sertor_core/cli/__main__.py", "specs/011-cli-esecuzione-rag/", "requirements/sertor-cli/esecuzione/requirements.md"]
---

# `sertor-rag` — la CLI di esecuzione RAG

La **terza superficie** del [[retrieval-core]] dopo la libreria e il [[mcp-server]]: un
console-script del pacchetto `sertor-core` (accanto a `sertor-wiki-tools`, vedi [[wiki-tools]]) che
rende eseguibili dal terminale le capacità di retrieval senza scrivere codice. Consegnata con la
feature 011 (`specs/011-cli-esecuzione-rag`, PR #21, 2026-06-11); secondo esempio realizzato del
pattern [[thin-consumer]].

## Il posto nella mappa dei comandi (DA-8)

Per la decisione **DA-8** (epica `sertor-cli`, 2026-06-11) il comando `sertor` è riservato
all'**installer** (`sertor install <capacità>`, da elicitare); l'**esecuzione** vive nei
console-script del core:

| Comando | Ruolo |
|---|---|
| `sertor-rag` | chiamate RAG: `index` / `search` / `doctor` / `observe` / `memory` / `eval` / `graph-eval` (questa pagina) |
| `sertor-wiki-tools` | nucleo wiki deterministico ([[wiki-tools]]) |
| `sertor` *(futuro)* | installazione/setup sull'ospite |

## Superficie

I comandi del `sertor-rag` (subparser in `src/sertor_core/cli/__main__.py`):

### Retrieval — `index` / `search`

- **`sertor-rag index <path> [--full] [--corpus X] [--json]`** — indice vettoriale del repository via
  `build_indexer()`; **incrementale di default** (solo i file cambiati sono ri-processati),
  `--full` forza un **rebuild atomico** da zero; report `documents/chunks/embedding_dim/elapsed_ms`.
- **`sertor-rag search <query> [-k N] [--type code|doc|both] [--json] [--full] [--corpus X]`** —
  top-k con path, tipo, chunk id, score e **anteprima troncata** (`Settings.preview_chars`,
  `SERTOR_PREVIEW_CHARS`, default 240); `--full` per il testo integrale.

### `doctor` — health check deterministico (FEAT-074)

- **`sertor-rag doctor [--online] [--area config|provider|index|mcp|all] [--json]`** — verifica di
  salute **sola lettura, senza LLM** delle quattro aree (config/env, provider di embedding, indice,
  registrazione MCP): per ciascuna `pass`/`warn`/`fail` con causa + rimedio, **exit non-zero su un
  problema critico**. `--online` opta per il probe di raggiungibilità del provider (rete); senza, solo
  statico. `--json` emette il contratto stabile `doctor.report/1`. È il comando «ha funzionato?»
  citato in `CLAUDE.md`.

### `observe` — pannello di osservabilità (TUI)

- **`sertor-rag observe [--corpus X]`** — apre il **pannello live** (ultimo index, cache, costo,
  eventi recenti), auto-refresh. Richiede l'extra `tui` e `SERTOR_OBSERVABILITY=true`.

### `memory` — memoria episodica delle conversazioni (E4, gate `SERTOR_MEMORY`)

Gruppo di sotto-comandi, **opt-in** (silente finché `SERTOR_MEMORY=true`), locale, sola lettura tranne
`archive`/`index-semantic`:

- **`memory archive`** — archivia ogni sessione scopribile (idempotente); report archived/skipped/errors.
- **`memory search <query> [--semantic] [--since/--until] [--order relevance|recency] [-k N]`** —
  ricerca full-text FTS5 (default, no rete/no LLM); `--semantic` cerca per **significato** (FEAT-013,
  richiede `SERTOR_MEMORY_SEMANTIC=true`, **mai** fallback silenzioso al full-text).
- **`memory index-semantic`** — backfill incrementale dell'indice semantico sulle sessioni archiviate.
- **`memory show <session_key>`** — trascrizione integrale di una sessione (not-found → exit 1).
- **`memory list [-k N]`** — sessioni recenti (recency-first). `memory`/`doctor` sono i due gruppi
  user-facing citati in `CLAUDE.md`.

### `eval` / `graph-eval` — valutazione della qualità (ground-truth)

- **`sertor-rag eval run [--compare a,b] [--fused] [--by-kind] [--record-baseline] [-k 1,3,5,10]`** —
  misura hit-rate@k/MRR contro la suite versionata `eval/suite.toml` e **gate di non-regressione** su
  `eval/baseline.toml` (exit 1 sulla regressione oltre tolleranza). Sotto-comandi di authoring:
  `add-case` / `amend-case` (persistono un caso *query → path attesi*, validato contro l'indice) e
  `validate-path` (primitiva per le skill di authoring, exit 0 sempre).
- **`sertor-rag graph-eval run [--exact] [--record-baseline]`** — valutazione **set-based** della
  navigazione del [[code-graph]] (precision/recall/F1 di `who_calls`/`defines`) con baseline distinta
  `eval/graph_baseline.toml`. Authoring: `add-case` / `amend-case` / `validate-ref`. Il run è un
  **vehicle deterministico** (Principio XI): mai un LLM.

### Osservabilità ed exit code (comuni)

- **Osservabilità**: `-v` (eventi INFO strutturati), `--log-json` (un record JSON per evento),
  `--log-config` (dictConfig JSON/YAML per appender esterni; YAML solo se `pyyaml` presente).
- **Exit code**: 0 successo · 1 errore di dominio (`SertorError` → messaggio leggibile su stderr) ·
  2 uso errato (argparse). Contratti in `specs/011-cli-esecuzione-rag/contracts/`.

## Scelte di design che contano

- **CLI sottile** (Principio I): parse → composition root → formatta output; nessuna logica di core.
- **Via strict per l'indice mancante**: `BaselineEngine.ensure_index()` (estratto da `query()`, che
  ora vi *delega*) precede ogni ricerca — la deroga alla facade tollerante è la stessa policy del
  motore baseline ([[indexing-and-retrieval]]); il check sta *prima* dell'embed → indice assente non
  costa una chiamata al provider.
- **Validazione statica della config**: `Settings.validate_backend()` ritorna le env mancanti per il
  backend scelto (es. `azure` senza endpoint/key/deployment) e la CLI blocca **prima** di contattare
  servizi; la *raggiungibilità* resta errore a runtime. I default restano solo in `Settings`
  (Principio VIII).
- **Eventi ai boundary** (Principio IX, estensione additiva del core): `embeddings_error` /
  `store_error` emessi **solo** dove si solleva l'errore vero — mai sui `return []` leciti della
  collezione assente. Schema campi in `contracts/log-events.md` (+ `src/sertor_core/observability/README.md`).
- **`--type both` = `facade.search_combined`** → eredita il fan-out multi-collezione da
  `Settings.extra_corpora` (feature 010) senza codice dedicato.

## Validazione (smoke 2026-06-11)

Suite `not cloud` **204 passed + 2 xfail** (45 test nuovi, mock senza rete); dogfood
`sertor-rag index .` → 230 doc / 2051 chunk dim 3072; **SC-008**: top-3 della CLI **identici** a
`search_combined` del server MCP (stessi chunk e score); **SC-005**: secondo repository indicizzato e
interrogato senza toccare i file target. Vedi il record nella voce di log del 2026-06-11.
