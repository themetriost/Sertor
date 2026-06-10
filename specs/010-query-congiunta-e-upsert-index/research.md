# Research — Query congiunta multi-collezione & `upsert-index` in CLI

**Feature**: `010-query-congiunta-e-upsert-index` · **Date**: 2026-06-10

Scioglie le decisioni rimandate dal clarify (DA-2, DA-3, DA-5, DA-6) e definisce la meccanica di
DA-1 (fail-fast) e DA-4 (Settings) decise dall'utente. Ogni decisione è ancorata al codice reale.

## R1 — Topologia dello store (DA-2): un solo store, stesso `persist_dir`

**Decision**: un solo `VectorStore`; le due collezioni convivono nello stesso `persist_dir`.

**Rationale**: verificato sul setup reale — `index_wiki` (`wiki_tools/indexing.py`) costruisce
l'indexer con `Settings.load()` cambiando **solo** `corpus` (`replace(settings, corpus=...)`):
`index_dir` resta quello di `SERTOR_INDEX_DIR` (`.index-sertor`). Ispezione di `.index-sertor`:
contiene `sertor__azure_text_embedding_3_large`; la collezione wiki, quando costruita via
`sertor-wiki-tools index`, atterra nello stesso client Chroma. Quindi **nessun secondo store**: il
fan-out è su più *nomi di collezione* dentro lo stesso backend.

**Alternatives considered**: fan-out su più istanze di store (per `persist_dir` diversi) — scartato:
nessun caso reale lo richiede (YAGNI, Principio III); se servirà, è un'estensione del composition
root, non delle firme.

## R2 — Dove vive la fusione (DA-3): orchestrata nella `RetrievalFacade`

**Decision**: il fan-out + merge vive in `RetrievalFacade` (`services/retrieval.py`); la porta
`VectorStore.query()` resta **invariata** (una collezione per chiamata).

**Rationale**: minimizza l'impatto sugli adapter e sui mock (rischio R-4 dei requirements): la
facade chiama `store.query()` N volte (una per collezione) e fonde. La query viene embeddata **una
sola volta** (un solo embedder → un solo vettore). La porta resta a singola responsabilità.

**Alternatives considered**: estendere `VectorStore.query()` ad accettare `list[str]` di collezioni
— scartato: ogni adapter dovrebbe reimplementare il merge (duplicazione, viola DRY) e cambia una
firma esistente per tutti gli adapter/mock.

## R3 — Manopola di configurazione (DA-4, decisa in clarify): `extra_corpora`

**Decision**: nuovo campo `Settings.extra_corpora: tuple[str, ...] = ()` letto da
`SERTOR_EXTRA_CORPORA` (lista separata da virgole, riusa l'helper `_split_env` esistente).
`build_facade()` deriva la collezione di ogni corpus extra con la stessa
`collection_name(replace(settings, corpus=c), embedder)` e passa alla facade la mappa
`corpus → collection`. Default vuoto → comportamento odierno identico (FR-006/SC-003).

**Rationale**: «default solo in `Settings`» (Principio VIII), thin-consumer (Principio I): i
consumatori (server MCP incluso) non cambiano di una riga. Il nome è generico (*extra corpora*, non
*wiki*): host-agnostico (Principio X) — sul dogfood varrà `SERTOR_EXTRA_CORPORA=wiki` (il corpus
del wiki da `wiki.config.toml [rag].corpus`), ma su un altro ospite può essere qualsiasi corpus.

**Alternatives considered**: campo dedicato `wiki_corpus` — scartato: incorpora il concetto "wiki"
nel core (violazione X); parametro per-chiamata — scartato in clarify (rompe il thin-consumer).

## R4 — Rilevare il provider eterogeneo (meccanica del fail-fast di DA-1)

**Decision**: nuova capacità di porta `VectorStore.list_collections() -> list[str]` + nuova
eccezione di dominio `ProviderMismatchError(SertorError)`. Nella ricerca combinata multi-collezione,
per ogni corpus bersaglio la collezione attesa è `{corpus}__{provider-corrente}`; se **assente**:
- esistono altre collezioni con prefisso `{corpus}__` → il corpus è indicizzato con un **altro
  provider** → `ProviderMismatchError` (esplicita: corpus, collezione attesa, collezioni trovate);
- non esiste alcuna collezione del corpus → corpus mai indicizzato → **degradazione morbida**
  (warning + contributo vuoto, FR-004).

**Rationale**: il naming per `(corpus, provider)` rende l'eterogeneità *osservabile solo* elencando
le collezioni: senza `list_collections` non si distingue "mai indicizzato" (tollerato) da
"indicizzato con provider diverso" (errore, decisione clarify #1). L'aggiunta alla porta è piccola,
implementabile da tutti i backend (Chroma: `client.list_collections()`; Azure AI Search:
`list_index_names()`; `InMemoryStore`: chiavi del dict) e giustificata da un requisito presente
(FR-009 — Principio III rispettato).

**Alternatives considered**: duck-typing opzionale (`getattr(store, "list_collections", None)`) —
scartato: capacità implicita, non testabile come contratto; metadato di provider dentro la
collezione — scartato: richiede scrittura/migrazione degli indici esistenti.

## R5 — Algoritmo di merge

**Decision**: per ogni collezione disponibile si chiede `k` risultati (`doc_type="both"`); si
concatenano e si ordinano per `(-score, chunk_id)` — score decrescente, pareggi risolti
deterministicamente per id — e si tronca a `k` complessivi. Nessuna deduplicazione cross-collezione
in v1.

**Rationale**: chiedere `k` per collezione garantisce che i top-k globali siano un sottoinsieme dei
candidati raccolti (correttezza del merge). Il tie-break per `chunk_id` rende l'output stabile a
input costante (Principio VI / edge case "parità di punteggio"). La dedup cross-collezione non ha un
caso reale (i corpora hanno path disgiunti per costruzione: il corpus codice esclude `wiki/` solo se
configurato — e in ogni caso due hit identici da due corpora sono informativi, non dannosi): YAGNI.

**Alternatives considered**: k proporzionale per collezione (k/2 ciascuna) — scartato: se la
pertinenza è concentrata in una collezione si perdono risultati migliori (edge case esplicito in
spec); normalizzazione/interleaving — scartati in clarify (territorio FEAT-004).

## R6 — Nomenclatura CLI (DA-5): `upsert-index --page --summary`

**Decision**: operazione `upsert-index`; argomenti `--page` (obbligatorio) e `--summary`
(opzionale: se assente, il sommario è letto da **stdin** riusando `_read_body`, già UTF-8). Output
umano `written=... action=... page=...`; `--json` emette il contratto.

**Rationale**: speculare ad `append-log` (stesso modello mentale, stessa meccanica stdin/UTF-8 già
collaudata contro il mojibake su console Windows). Verificato in `__main__.py`: basta aggiungere
l'op a `_OPS`, due argomenti al parser, un ramo in `_run` e uno in `_human`.

## R7 — Contratto dell'esito (DA-6): `UpsertIndexResult`, e validazione nella funzione pura

**Decision**: nuovo contratto `UpsertIndexResult(written: bool, action: "insert"|"update"|"noop",
page: str, schema="wiki.upsert_index/1")` in `wiki_tools/contracts.py`. La firma di
`registry.upsert_index` cambia da `-> bool` a `-> UpsertIndexResult` (nessun consumatore esistente:
verificato, la funzione non è cablata da nessuna parte; i soli test interni si aggiornano).
La **validazione del sommario** (FR-018: vuoto/whitespace o newline interni → errore) vive nella
funzione pura `upsert_index`, sollevando `ConfigError` (il precedente del modulo: input non valido
della CLI → `ConfigError`, vedi `append-log richiede --entry-op e --title` e `data non valida`),
così la regola vale anche per chi usa la libreria direttamente, non solo per la CLI.

**Rationale**: uniformità con gli altri esiti versionati (`AppendLogResult` ecc.) e con il flusso
`--json`; la distinzione insert/update/noop richiesta da FR-016 non è esprimibile con un `bool`.

**Alternatives considered**: mantenere `bool` e derivare l'azione nella CLI — scartato: la CLI
dovrebbe rileggere l'indice per capire cosa è successo (duplicazione di logica, race banale).

## R8 — Osservabilità del fan-out

**Decision**: la ricerca combinata multi-collezione emette un evento `retrieve` con
`collections=[...]` (lista interrogata), `provider`, `k`, `results` (post-merge), `elapsed_ms`;
le collezioni saltate per degradazione emettono il warning `no_index` già esistente, una volta per
collezione assente.

**Rationale**: Principio IX; coerente con il formato `log_event("retrieve", ...)` già in uso.
