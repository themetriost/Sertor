# Research — dedup risultati (Phase 0)

Ground truth: pipeline reale (`engines/hybrid.py:retrieve`, `services/retrieval.py:_search`+fused,
`config/settings.py`), `RetrievalResult` (campi `path`, `chunk_id`, `text`, `score`), diagnosi
`wiki/log/2026-07-07.md`.

---

## D1 — Il pool DEVE essere > k perché la dedup sia efficace *(decisione cardine)*

- **Fatto:** nel path ibrido `fused_k = max(k, rerank_pool) if reranker else k`. Con reranker **off**
  (default `SERTOR_RERANK=false`), `fused_k = k` → `candidates` ha **esattamente k** elementi. Deduplicare k
  elementi senza pool più grande li riduce **sotto k**, senza backfill: il doc sepolto **non** rientra.
- **Decisione:** quando `dedup_enabled`, materializzare un pool **`P = max(k, dedup_pool)`** *anche con
  reranker off*, poi `dedup_results(pool)`, poi `[:k]`. Per `dedup_pool` **riuso `rerank_pool`** (default
  15, ~3×k) come dimensione, **senza** introdurre una manopola nuova (YAGNI): rinominare concettualmente il
  suo uso a «pool di post-processing». *(Se in futuro serve disaccoppiare, si aggiunge `SERTOR_DEDUP_POOL`;
  non ora.)*
- **Rationale:** riusa una sizing già tarata (~3×k) e testata; evita una manopola in più. Il costo è
  materializzare qualche decina di candidati in più — trascurabile, nessuna rete.
- **Alternative scartate:** (a) dedup dopo il cut a k → inefficace (il doc sepolto è già escluso);
  (b) nuova manopola `SERTOR_DEDUP_POOL` subito → YAGNI finché `rerank_pool` basta.

## D2 — Normalizzazione della chiave di contenuto

- **Decisione:** chiave = **hash del testo del chunk normalizzato** con **collasso del whitespace**
  (sequenze di spazi/newline/tab → singolo spazio, trim), **case-preserving**. `hashlib.sha1` sul testo
  normalizzato UTF-8 (veloce, no collisioni pratiche; non è un uso crittografico).
- **Rationale:** cattura i **byte-copy** (identici a meno di EOL/indentazione — proprio il caso `assets/**`
  ↔ blocchi `CLAUDE.md`, dove il churn CRLF/LF già visto in E15 fa differire solo il whitespace). Il
  case-preserving evita di fondere testi diversi che differiscono solo per maiuscole (raro ma possibile).
- **Alternative scartate:** case-folding (rischio over-merge); no-normalization (mancherebbe i dup che
  differiscono solo per EOL — proprio il nostro caso).

## D3 — Casa della funzione pura

- **Decisione:** **`src/sertor_core/services/dedup.py`** con `dedup_results(results: list[RetrievalResult])
  -> tuple[list[RetrievalResult], int]` (ritorna i risultati deduplicati **e** il conteggio dei rimossi,
  per l'osservabilità FR-008). Funzione **pura**, nessuna dipendenza da Settings (il *se* deduplicare è al
  call-site: `if settings.dedup_enabled`).
- **Rationale:** è logica di servizio sul dominio `RetrievalResult`, condivisa dai motori e dalla facade
  (DRY, Principio III). Non è un adapter né una porta. `services/` è la casa coerente (accanto a
  `retrieval.py`, `eval/`).
- **Alternative scartate:** metodo su ogni engine (duplicazione, viola DRY); porta/Protocol (over-eng,
  YAGNI — non è un punto di variabilità pluggable).

## D4 — Siti d'inserimento (tutti i cut che l'agente vede)

Applicare `dedup_results` **prima del cut al top-k**, dietro `if settings.dedup_enabled`, in:

| Sito | Dove | Nota |
|------|------|------|
| Ibrido, path principale | `hybrid.py:retrieve` dopo `_materialize` (riga ~134), pool `P` poi rerank/`[:k]` | il path **misurato** (dogfood) |
| Ibrido, fallback dense-only | `hybrid.py:retrieve` ramo «no lexical» (riga ~110): fetch pool `P` (non k) → dedup → `[:k]` | degradato/raro |
| Facade fallback (no retriever) | `retrieval.py:_search` (riga ~149): fetch pool `P` → dedup → `[:k]` | quando nessun engine wired |
| Facade fused multi-collezione | `retrieval.py` (riga ~265-267): dedup `candidates` prima di `[:k]` | host multi-corpus |
| Baseline | `engines/baseline.py` (cut analogo) | motore baseline |

- **Rationale:** FR-004 (coerenza su tutte le superfici/motori). Il **path caldo e misurato** è l'ibrido
  principale; gli altri sono coperti dallo stesso helper (costo marginale).
- **Nota reranker:** deduplicare `candidates` **prima** del rerank è corretto — near-dup a testo identico
  riceverebbero score ~identico dal cross-encoder, quindi rimuoverli prima non altera il ranking, e il
  rerank lavora su contenuto distinto (top-k più informativo).

## D5 — Manopola & wiring

- **Decisione:** `Settings.dedup_enabled: bool = True`, letta con `_bool_env("SERTOR_DEDUP", True)` (stesso
  pattern di `rerank_enabled`/`graph_enabled`). Passata ai motori/facade via `Settings` (già iniettato).
  Nel **template `.env`** dell'installer: riga `SERTOR_DEDUP=true` documentata (host-facing, unico tocco).
- **Rationale:** configurabilità centralizzata (VIII); default-on perché è un miglioramento sicuro
  (no-op sui distinti); bypassabile per debug/confronto (SC-003).

## D6 — Osservabilità

- **Decisione:** il conteggio dei rimossi entra nel `_log_query` esistente (nuovo campo `deduped=<n>`),
  senza segreti (IX). Zero rimossi = nessun rumore.

## D7 — Determinismo & no-op

- **Decisione:** la lista in ingresso è **già ordinata** (RRF/score); `dedup_results` scorre in ordine e
  tiene la **prima** occorrenza di ogni chiave → l'istanza col rank più alto, tie-break stabile ereditato
  dall'ordine esistente (`(-score, chunk_id)`). Su risultati già distinti è **no-op** (stessa lista).

---

## Sintesi

| # | Decisione |
|---|-----------|
| D1 | Pool `P = max(k, rerank_pool)` prima del cut quando dedup on (anche reranker off); no nuova manopola pool |
| D2 | Chiave = sha1 del testo normalizzato (whitespace collassato, case-preserving) |
| D3 | `services/dedup.py::dedup_results() -> (results, removed_count)`, puro |
| D4 | Applicato ai 5 siti di cut (ibrido main+fallback, facade fallback+fused, baseline) |
| D5 | `Settings.dedup_enabled` / `SERTOR_DEDUP` default True; riga nel template `.env` |
| D6 | `deduped=<n>` nel log query |
| D7 | Tiene la prima occorrenza (rank più alto), no-op sui distinti, deterministico |

Nessuna NEEDS CLARIFICATION residua → Phase 1.
