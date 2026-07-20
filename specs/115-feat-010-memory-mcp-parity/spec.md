# Feature Spec: parità MCP per la lettura della memoria

**Branch**: `115-feat-010-memory-mcp-parity` · **Requisiti**: `../../requirements/memoria-conversazioni/feat-010-parita-mcp-lettura/requirements.md` · **Epica**: `memoria-conversazioni` (E4-FEAT-010)

**Date**: 2026-07-20

## Cosa & perché

L'archivio della memoria conversazioni è **leggibile solo dalla CLI** (`memory list`/`show`/`search`). Il
server MCP `sertor-rag` — la superficie **nativa** con cui l'agente (e i consumatori esterni) consuma
Sertor — espone 7 tool sul corpus/grafo ma **nessuno sulla memoria**. Questa feature aggiunge la **parità
di lettura**: tre tool MCP che elencano, aprono e cercano nell'archivio, con lo **stesso gate di privacy**
(`SERTOR_MEMORY`) e la **stessa semantica** della CLI. Serve il valore dell'epica («memoria interrogabile
**nativamente** dall'agente») e il contratto pubblico (i consumatori usano l'MCP, non la CLI — Principio XI).

Scope deciso (utente 2026-07-20): **list + show + search full-text**; il semantico resta CLI-only (follow-up).

## Comportamento (l'esito osservabile)

Tre nuovi tool MCP, accanto ai 7 esistenti, **thin** sopra il core:
- **`memory_list(limit?)`** → sessioni recenti: `{status, sessions:[{session_key, captured_at, turn_count}]}`.
- **`memory_show(session_key)`** → una sessione: `{status, session:{session_key, project_id, captured_at,
  adapter_kind, turns:[{index, role, ts, text}]}}` (o `session:null` se assente).
- **`memory_search(query, k?)`** → hit full-text: `{status, hits:[{session_key, captured_at, role,
  turn_index, snippet, score}]}`.

**Gate di privacy (identico alla CLI):** con `SERTOR_MEMORY` spento (default), ogni tool ritorna
`{status:"disabled", hint:"set SERTOR_MEMORY=true to enable conversation memory"}` — **né** lista vuota
(mentirebbe), **né** errore opaco (rumore su `mcp.*.error`). Con memoria accesa, `status:"ok"`.

**Degradazione non-fatale:** archivio assente/vuoto/illeggibile → `status:"ok"` con collezione vuota
(stato esplicito), come già fa il core; un guasto reale → tool error via `_guard` (`mcp.<tool>.error`).

## Criteri di accettazione
Vedi CS-1..CS-6 in requirements §2. In sintesi:
- **AC-1:** i tre tool ritornano gli **stessi dati** dei read CLI a parità di archivio (stessa sorgente,
  stesso ordinamento, stessi default di `Settings`).
- **AC-2:** memoria spenta → `status:"disabled"` esplicito su tutti e tre (non `[]`, non errore).
- **AC-3:** solo contenuto già archiviato (scrubbed); `memory_search` logga la query **hashata**.
- **AC-4:** ogni risultato è citabile (`session_key`; hit = sessione+turno).
- **AC-5:** delega ai servizi core (`MemoryArchive.list_recent`/`get`, `EpisodicSearch.search`), nessuna
  logica riscritta; i 7 tool esistenti e lo startup **invariati**.

## Out of scope
- Ricerca **semantica** via MCP (doppio gate `SERTOR_MEMORY_SEMANTIC`) → follow-up (nuova FEAT).
- **Scrittura** via MCP (`archive`/`index-semantic`).
- Cambi allo schema `memory.sqlite` o ai 7 tool esistenti.

## Note di design (forcelle sciolte nel plan)
- **Envelope con `status`** (`ok`/`disabled`) per tutti e tre → il disabled è first-class e non maschera
  (R-3/R-5). Diverge di proposito dai search-corpus (liste nude) perché la memoria ha lo **stato di gate**.
- **`show` = testo pieno** del turno (è «mostra la sessione»); **`search` = snippet** (come `EpisodicSearch`,
  `snippet_tokens` da `Settings`).
- **Naming `memory_*`** (prefisso, coerente col gruppo CLI e distinto da `search_code`/`search_docs`).
