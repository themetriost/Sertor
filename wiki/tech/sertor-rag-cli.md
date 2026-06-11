---
title: sertor-rag — la CLI di esecuzione RAG
type: tech
tags: [cli, retrieval, thin-consumer, dogfooding, produzione]
created: 2026-06-11
updated: 2026-06-11
sources: ["src/sertor_core/cli/", "specs/011-cli-esecuzione-rag/", "requirements/sertor-cli/esecuzione/requirements.md"]
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
| `sertor-rag` | chiamate RAG: `index` / `search` (questa pagina) |
| `sertor-wiki-tools` | nucleo wiki deterministico ([[wiki-tools]]) |
| `sertor` *(futuro)* | installazione/setup sull'ospite |

## Superficie

- **`sertor-rag index <path> [--corpus X] [--json]`** — indice vettoriale del repository via
  `build_indexer()` (full rebuild atomico); report `documents/chunks/embedding_dim/elapsed_ms`.
- **`sertor-rag search <query> [-k N] [--type code|doc|both] [--json] [--full] [--corpus X]`** —
  top-k con path, tipo, chunk id, score e **anteprima troncata** (`Settings.preview_chars`,
  `SERTOR_PREVIEW_CHARS`, default 240); `--full` per il testo integrale.
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
