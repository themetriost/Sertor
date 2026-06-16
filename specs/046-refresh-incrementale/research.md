# Research — Refresh incrementale dell'indice (FEAT-009)

Risolve i punti aperti del Technical Context e le 3 domande di design rinviate dal clarify, più le
decisioni emerse dalla mappatura del codice reale. Prior art: CocoIndex (lineage tracking, change
detection mtime+fingerprint, `behavior_version`), LlamaIndex IngestionPipeline (docstore con hash,
`upserts_and_delete`), record-manager di LangChain (ledger SQLite, `cleanup`).

## D1 — Sede e formato del manifest *(domanda di design Q1)*

- **Decisione:** SQLite locale `<index_dir>/index_manifest.sqlite`, **namespaced per collezione
  `(corpus, provider)`** (una riga-stato per file dentro lo scope della collezione).
- **Razionale:** coerenza con gli altri store locali del progetto (`embed_cache.sqlite`,
  `observability.sqlite`, `memory.sqlite`) — stdlib `sqlite3`, atomico, interrogabile, gitignored;
  regge corpora grandi meglio di un JSON monolitico (update parziale senza riscrivere tutto).
- **Alternative scartate:** JSON unico (riscrittura completa a ogni run, niente atomicità parziale);
  sidecar per-file (esplosione di file). 

## D2 — Cosa persiste il manifest *(abilita F1)*

- **Decisione:** per ogni file → `path, mtime, content_hash, logic_version`; **più le unità derivate**:
  il `Document` (testo, doc_type, lingua) e i suoi `Chunk` (id, testo, metadata, doc_type, path).
- **Razionale:** F1 impone di ricostruire BM25 **e** code-graph **senza** rileggere/ri-chunkare gli
  invariati. BM25 `build()` vuole `LexicalEntry` (chunk_id/text/doc_type/path) → dai chunk del manifest.
  `extract_graph(documents, chunks)` vuole i `Document` (testo, per il walk tree-sitter) e i `Chunk` →
  entrambi dal manifest. Persistere le unità = snapshot del corpus *già parsato*, locale e rigenerabile.
- **Costo:** storage ≈ dimensione del testo del corpus (locale, gitignored) — accettabile, è il prezzo
  per evitare il costo dominante di discover (I/O) + chunk (CPU) sugli invariati.
- **Alternativa scartata:** persistere solo i metadati e **rileggere** gli invariati per BM25/graph →
  eroderebbe il guadagno principale (discover) e contraddirebbe F1.

## D3 — Ricostruzione di BM25 e code-graph *(F1)*

- **Decisione:** a ogni run incrementale, BM25 e code-graph sono **ricostruiti pieni** dall'**unione**
  {unità invariate dal manifest} ∪ {unità fresche dei file cambiati}, via i `build()` esistenti (mirror).
  **Nessuna estensione delle porte.**
- **Razionale:** le porte `LexicalIndex`/`CodeGraph` sono mirror-semantics; nutrirle con l'insieme
  completo le rende corrette **per costruzione** (equivalenza col full, FR-012). Il loro build è
  CPU-leggero rispetto a embed ($) e al reset+HNSW del vector store (che invece evitiamo con upsert/delete
  mirati — il guadagno grosso).
- **Alternativa scartata:** BM25/graph **veramente** incrementali (porta `update()`, invalidazione mirata
  degli archi cross-file) → complessità alta, rinviata a Could futuro.

## D4 — Rilevamento dei cambiamenti

- **Decisione:** **mtime come pre-filtro + content-hash come conferma**. Classi: UNCHANGED / NEW /
  MODIFIED / DELETED. Se `mtime` differisce ma `hash` coincide → UNCHANGED (FR-003), si aggiorna solo mtime.
- **Razionale:** prior art convergente; mtime evita di leggere gli invariati, l'hash garantisce
  correttezza. `discover` va separato: `stat` su tutti (cheap) + `read` solo sui candidati cambiati.

## D5 — Invalidazione su cambio di logica *(FR-013)*

- **Decisione:** una `logic_version` (stringa) composta dai parametri/versione di chunking + estrazione
  grafo è salvata nel manifest; se differisce da quella corrente, **tutti i file interessati sono trattati
  come MODIFIED** (riprocessati).
- **Razionale:** equivalente del `behavior_version` di CocoIndex; impedisce che unità prodotte da logica
  vecchia sopravvivano. Conservativo: in dubbio, riprocessa (NFR-1).

## D6 — Attivazione *(F2)*

- **Decisione:** `index()` è **incrementale di default** quando esiste un manifest valido per la collezione;
  `rebuild=True` (CLI `--full`) forza il full; manifest assente/incompatibile/corrotto → **full automatico**
  (FR-011). Manopola `SERTOR_INDEX_INCREMENTAL` (default **True**) per disabilitare e forzare sempre il full.
- **Razionale:** scelta utente F2; il full resta il reset sicuro e il fallback.

## D7 — Rename-detection *(domanda di design Q2 → plan)*

- **Decisione:** **delete + new** nel primo taglio (nessun riconoscimento dei rinomini).
- **Razionale:** semplice e corretto (vecchi chunk cancellati, nuovi inseriti). Costo basso: se il
  contenuto è identico, l'embed-cache (chiave = `content_hash`) fa **hit** → niente ri-embedding, solo
  ri-chunk + ri-upsert. Rename-detection = ottimizzazione futura (Should).

## D8 — Soglia incrementale-vs-full *(domanda di design Q3 → plan)*

- **Decisione:** **tentare sempre l'incrementale** se il manifest è valido (nessuna soglia).
- **Razionale:** su corpora piccoli l'incrementale non è più lento (il run a vuoto ≈ costo del solo `stat`,
  NFR-4); una soglia aggiunge complessità senza beneficio chiaro.

## D9 — Full di riconciliazione *(FR-019, clarify Q1=C)*

- **Decisione:** manopola `SERTOR_INDEX_RECONCILE_EVERY` (int, default **0 = off**); se > 0, ogni N run
  incrementali si forza un full (contatore nel manifest). Più il `--full` manuale.
- **Razionale:** controllo anti-drift a basso costo per il default-incrementale, **spento di default** come
  deciso in clarify. Il *segnale* su quando alzarlo è demandato a `osservabilita` FEAT-012 (drift-detection).

## D10 — Guardia single-writer *(FR-020, clarify Q2=B)*

- **Decisione:** lockfile `<index_dir>/.index.lock` acquisito all'avvio di `index()` e rilasciato a fine
  run; un secondo run concorrente sullo **stesso indice** solleva `IndexLockedError` (fail-fast).
- **Razionale:** previene la corruzione di manifest/store da scritture simultanee; strategie avanzate
  (store condiviso, multi-processo coordinato) → epica `multiutente`.

## Conferme dalla mappa del codice
- `VectorStore.delete(collection, ids)` **esiste** (`ports.py`, `chroma.py`) ma non è invocato da
  `index()` → serve solo orchestrazione. Nessuna nuova porta.
- `IndexReport` va esteso con i conteggi delta (additivo).
- `EmbeddingCache` (FEAT-019) è già cablato in `build_indexer` → l'incrementale ne beneficia gratis.
- ID stabili `Chunk.id = doc_id#index`, `Document.id = relpath POSIX` → idempotenza preservata.
