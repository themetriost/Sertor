# E4-FEAT-014 — BUG: `memory search` fallisce (mascherato) su query con punteggiatura

**Epica:** [`memoria-conversazioni`](../epic.md) · **Tipo:** bug · **Priorità:** Should
**Fonte:** segnalazione del **nodo Acta** (bacheca `Feedback Sertor`, 2026-07-21), verificata sul codice e
sull'archivio reale del dogfood.

## Contesto / difetto

`EpisodicSearch._build_sql` (`services/episodic_search.py`) passa il **testo grezzo** dell'utente al
`MATCH ?` di FTS5. FTS5 interpreta il valore come **espressione di query**: `.` `-` `:` `"` `*` `(` `)`
sono sintassi speciale → un token come **`0.1.1`** produce `sqlite3.OperationalError: fts5: syntax error
near "."`. L'eccezione è catturata in `_run_query` → degradata a tupla vuota → l'utente vede **`(no
results)`**.

**Due problemi (il secondo peggiore):**
1. Una **classe intera** di query normali fallisce: numeri di versione (`0.1.1`), path (`a/b.py`), tag
   `tipo:esito`, orari, sigle con trattino.
2. Il guasto è **mascherato**: un errore di *sintassi query* appare come «nessun risultato» — l'**opposto
   di Fail Loud** (Principio XII). Chi cerca conclude «non ne abbiamo mai parlato» quando la ricerca non è
   nemmeno partita.

Colpisce sia la CLI `sertor-rag memory search` sia il tool MCP `memory_search` (full-text) — entrambi
passano per `EpisodicSearch.search`. **Riprodotto LIVE** sull'archivio reale: RAW `0.1.1` →
`OperationalError`; il fix trova **13 match** prima mascherati.

## Requisiti (EARS)

- **REQ-001** — QUANDO l'utente cerca con testo libero, il sistema DEVE trattare la punteggiatura come
  **contenuto**, non come operatore: nessun `OperationalError` per input ordinario (versioni, path, tag,
  trattini, orari, parentesi).
- **REQ-002** — Il testo libero DEVE essere sanitizzato prima del `MATCH`: ogni token (split su
  whitespace) avvolto in un **string-literal FTS5** (doppi apici; un `"` interno raddoppiato), token
  space-joined = **AND implicito** (comportamento multi-parola preservato).
- **REQ-003** — QUANDO il testo non produce token (solo whitespace/punteggiatura degenere), il sistema
  DEVE ritornare lo **stato vuoto esplicito** (non un errore) — parità con la query vuota.
- **REQ-004** — Il fix DEVE valere per **entrambi** i vehicle (CLI `memory search` e tool MCP
  `memory_search`), per costruzione (unica sede `EpisodicSearch`).

## Fuori scope

- Modalità `--raw` per la sintassi FTS5 esplicita (AND/OR/NEAR/prefix) — la ricerca in memoria è testo
  libero per default; il `--raw` è un follow-up **solo se** emerge il bisogno.
- Riprogettare la policy di degradazione non-fatale di `EpisodicSearch` (resta non-fatale): col sanitizer
  l'`OperationalError` da input utente non si verifica più, quindi il masking è **risolto per
  prevenzione**.

## Verifica

- Unit del puro `_to_fts_match` (quoting, escaping `"`, empty→`''`).
- Regressione: query `0.1.1` trova il turno che la contiene; classe punteggiatura (`a/b.py`,
  `tipo:esito`, `v0.3.1`, `hy-phen`, `10:30`, `C()`) → stato vuoto pulito, mai crash; multi-token = AND.
- LIVE sull'archivio reale (RAW crasha, SANITIZED ok).
