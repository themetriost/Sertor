# Phase 0 — Research: Nucleo di retrieval condiviso

Consolidamento delle decisioni tecniche per FEAT-001. Ogni voce: **Decisione**, **Razionale**,
**Alternative considerate**. Fonte di ancoraggio primaria: il motore `prototype/shared/` (dogfooding).
Le domande aperte di ambito sono già chiuse nella spec/requirements (DA-001..005); qui si risolvono i
*NEEDS CLARIFICATION* tecnici emersi dal Technical Context.

---

## R1 — Chunking sintattico multilinguaggio (REQ-006/007/009/011, rischio R-N2)

**Decisione.** Usare `tree-sitter` + **`tree-sitter-language-pack`** (wheel precompilati, 305+
grammatiche, Python 3.9–3.13, licenze permissive) come fornitore unico delle grammatiche. Un
dispatcher mappa `language -> grammatica`; per i linguaggi privi di grammatica matura il sistema
**ricade sul chunking dimensionale** (REQ-009) senza errore. Il set MVP dichiarato (Python, JS/TS,
Java, C#, Go, C/C++, PHP, Ruby, PowerShell, Bash, T-SQL, PL/SQL) è coperto **sintatticamente** dove la
grammatica è matura e **per fallback** dove non lo è.

**Stato grammatiche del set MVP (1° rilascio):**
- *Mature / sintattiche da subito*: Python, JavaScript/TypeScript, Java, C#, Go, C, C++, PHP, Ruby,
  Bash. (Coperte dal language-pack.)
- *Fallback dimensionale al 1° rilascio* (grammatica assente/immatura): **PowerShell**, **T-SQL**,
  **PL/SQL**. SQL generico esiste (DerekStride) ma i dialetti T-SQL/PL/SQL sono parziali; PowerShell non
  ha grammatica affidabile nel pack. REQ-009 garantisce la copertura senza errore; il passaggio a
  sintattico è un **incremento** (REQ-011), non una riprogettazione.

**Razionale.** I wheel precompilati eliminano la compilazione C per-grammatica → portabilità
Linux+Windows (NFR-03) senza toolchain. Un solo pacchetto vs N pacchetti `tree-sitter-<lang>` riduce la
superficie di manutenzione. Il prototipo già usa l'API tree-sitter (Parser/Language) ma con un solo
`tree_sitter_python` registrato a mano: il pack generalizza quel pattern.

**Alternative considerate.** (a) Un pacchetto `tree-sitter-<lang>` per linguaggio: più controllo sulle
versioni ma 14 dipendenze + rischio di build su Windows → respinta per costo/portabilità. (b)
`tree-sitter-languages` (grantjenks): più vecchio, copertura inferiore, manutenzione minore → respinta.
(c) Solo chunking dimensionale per tutti: semplice ma viola REQ-006 (confini sintattici) → respinta.

**Conseguenza di design.** La logica code-aware del prototipo (`chunking_code.py`: emit per
classe/metodo/funzione, contesto classe in testa ai metodi, raggruppamento module-level, split
oversize) è **riusabile**, ma il riconoscimento dei tipi di nodo va parametrizzato per linguaggio (i
nomi dei nodi differiscono: `function_definition` in Python vs `function_declaration` in Go/JS). Mappa
`language -> {def_types, class_types, name_field}` nel dispatcher.

---

## R2 — Astrazione del vector store (REQ-017/018/019/021)

**Decisione.** Porta `VectorStore` minimale e backend-agnostica con operazioni: `upsert(chunks,
vectors)`, `query(vector, k, filter)`, `delete(ids)`, `count()`/esistenza-collezione. Namespacing per
corpus tramite **nome di collezione** (`{corpus}` o `{corpus}-{provider}-{dim}`), non tramite directory
separate. Backend locale = **Chroma embedded** (default); cloud = **Azure AI Search** dietro extra
opzionale. Cosmos DB resta opzione futura (stessa porta).

**Razionale.** Nel prototipo Chroma è sepolto dentro `HybridIndex` (accoppiato a BM25/rerank, fuori
ambito qui): va **estratto** in una porta pulita di sola persistenza+similarità. La query per
similarità con filtro su `source` (code/doc) è già il pattern usato (`idx.search(..., source=...)`):
la porta lo formalizza come `filter` sui metadati, evitando indici separati (REQ-027). Il namespacing
per collezione è il meccanismo nativo sia di Chroma sia di Azure AI Search, più portabile del
namespacing per directory del prototipo (`.index-<corpus>`).

**Vincolo di idempotenza/coerenza.** Una collezione è valida per una **tripletta (corpus, provider,
dimensione embedding)**: vettori di dimensioni diverse non sono confrontabili. Il nome di collezione
incorpora provider+dim per impedire query cross-dimensione silenziose (collegato a R3).

**Alternative considerate.** (a) Esporre direttamente l'API Chroma: viola Principio I/II → respinta.
(b) Porta con operazioni ricche (filtri arbitrari, aggregazioni): YAGNI, i requisiti chiedono solo
similarità+filtro tipo → respinta. (c) Namespacing per directory come il prototipo: meno portabile sul
cloud → respinta a favore delle collezioni.

---

## R3 — Provider di embeddings intercambiabili (REQ-012/013/014/015/016)

**Decisione.** Porta `EmbeddingProvider` con `embed(texts) -> list[vector]` (batch) e proprietà
`name`/`dim`/`batch_size`. Adapter: **Ollama** (locale, `/api/embed`) e **Azure OpenAI** (cloud,
`/embeddings`), entrambi via `httpx` come nel prototipo. Batch size da config (REQ-014). Errore →
`EmbeddingError(provider, reason, retriable)` (REQ-015). Local-only: l'adapter Ollama non apre
connessioni cloud (REQ-016); la selezione local-only è garantita dalla config (nessun adapter cloud
istanziato).

**Razionale.** La classe `Embedder` del prototipo (base + batching in `embed`, `_embed_batch`
per-adapter, `get_embedder` factory) è già **quasi una porta**: la si promuove a `Protocol`/ABC nel
domain e la factory diventa parte del composition root. La dimensione `dim` è scoperta al primo batch
(come nel prototipo) e usata per nominare la collezione (R2).

**Alternative considerate.** (a) Usare LangChain `Embeddings`: introduce una dipendenza pesante nel
core e accoppia a un framework → viola Principio I/III → respinta (LangChain resta libero per i motori a
valle). (b) SDK ufficiali Azure/OpenAI invece di `httpx` REST: più superficie, il prototipo dimostra che
REST basta → respinta per semplicità (YAGNI).

---

## R4 — Stabilità degli identificatori (REQ-004/010, idempotenza NFR-02, rischio R-N3)

**Decisione.** `doc_id` = **path relativo POSIX** rispetto alla radice del repo (come `Doc.id` del
prototipo). `chunk_id` = `f"{doc_id}#{index}"` dove `index` è l'**ordinale posizionale** del chunk
nell'ordine deterministico di emissione del chunker. La scoperta dei file è **ordinata** (sort sul path
relativo) per rendere deterministico l'ordine globale; il timestamp non entra mai nell'ID.

**Razionale.** Path relativo + posizione sono stabili tra esecuzioni a contenuto invariato → stessi ID,
nessun duplicato (SC-005). Mitiga R-N3 (ordine di scoperta variabile) imponendo il sort. Evita ID basati
su hash del contenuto: un hash cambierebbe a ogni minima modifica e complicherebbe il debug; l'ordinale
posizionale è leggibile e sufficiente per il full re-index (A-4/DA-004).

**Nota.** L'idempotenza dei **vettori** (NFR-02) vale "a parità di provider": embeddings deterministici
dipendono dal modello; il test di idempotenza confronta l'insieme di `chunk_id` e il contenuto dei
chunk, e (dove il provider è deterministico) i vettori.

**Alternative considerate.** (a) `chunk_id` = hash(testo): instabile a modifiche, meno leggibile →
respinta. (b) ID con offset di riga invece dell'ordinale: l'offset cambia se cambiano righe sopra →
meno stabile dell'ordinale all'interno del documento → l'ordinale è la scelta; le righe restano come
*metadato* (REQ-007), non come ID.

---

## R5 — Osservabilità: logging strutturato (REQ-031, Principio IX)

**Decisione.** Modulo `observability/logging.py` che configura un logger con **record strutturati**
sulla `logging` stdlib (campi via `extra=`/filtro che serializza a chiave-valore o JSON). Campi minimi:
`operation`, `provider`/`backend`, `doc_count`, `chunk_count`, `embedding_dim`, `elapsed_ms`, `error`.
**Redazione** dei segreti: una funzione di sanitizzazione rimuove chiavi note (`*_key`, `*_api_key`,
`authorization`) prima dell'emissione (REQ-032).

**Razionale.** REQ-031 chiede log strutturati "senza imporre un framework al chiamante": la stdlib
`logging` è già disponibile ovunque e il chiamante può ridirigere/handler a piacere. Evita una
dipendenza (`structlog`) non necessaria (YAGNI/Principio III).

**Alternative considerate.** (a) `structlog`: ergonomia migliore ma dipendenza extra non richiesta →
respinta per l'MVP (riconsiderabile come incremento). (b) `print`/stringhe libere: non strutturato,
viola REQ-031 → respinta.

---

## R6 — Configurazione centralizzata e segreti (REQ-030/032, Principio VIII)

**Decisione.** Un unico `Settings` (in `config/settings.py`) che legge **env + file** via
`python-dotenv`, **senza default hardcoded nei componenti** (i default vivono solo in `Settings`).
Espone: backend, corpus, provider embeddings + parametri, percorsi, parametri di chunking
(size/overlap/set linguaggi), `k` di default, batch size, **lista di esclusione** per l'ingestione.
I segreti (API key, endpoint) sono letti solo da env/file non versionato; `.env` resta in `.gitignore`;
mai scritti su path versionati (REQ-032/V-2).

**Razionale.** Generalizza il `Settings` del prototipo (che già usa `RAG_BACKEND`/`SERTOR_CORPUS` +
dotenv con `override=True`) rendendo repo-agnostiche le parti hardcoded: la `_EXCLUDE` di
`loaders.py` (set fisso) diventa **lista configurabile** (REQ-002), e i code-root/corpus hardcoded
(`_SERTOR_CODE_ROOTS`) spariscono a favore della scoperta repo-agnostica (REQ-001).

**Alternative considerate.** (a) Config sparsa per modulo: viola Principio VIII → respinta. (b) Solo env
(no file): meno ergonomico per liste lunghe (esclusioni) → file+env entrambi. (c) `pydantic-settings`:
valida e tipizza bene; opzione accettabile — il piano lascia la scelta dataclass↔pydantic ai task,
purché il punto di configurazione resti unico.

---

## R7 — Isolamento delle dipendenze pesanti / extra opzionali (NFR-04, rischio R-N4)

**Decisione.** Il core + backend locale (Chroma) + provider locale (Ollama) sono l'installazione base.
I backend cloud (Azure AI Search, Cosmos) e — se necessario — grammatiche aggiuntive sono **extra
opzionali** del pacchetto (es. `pip install sertor-core[azure]`). Gli adapter cloud importano i propri
SDK **lazy** (dentro `__init__`/metodo), così l'assenza dell'extra non rompe l'import del core.

**Razionale.** NFR-04 + R-N4 (conflitti di dipendenze tra backend): isolare evita che installare un
backend blocchi gli altri; l'import lazy mantiene il core importabile anche senza gli extra (utile per i
test con mock, NFR-01). La definizione concreta degli extra/packaging è rinviata all'epica `sertor-cli`
(DA-005), ma il **confine** (import lazy, adapter isolati) è deciso qui.

**Alternative considerate.** (a) Tutte le dipendenze obbligatorie: rischio conflitti + installazione
pesante → respinta. (b) Plugin discovery via entry points: over-engineering per 2 backend → respinta
(YAGNI), riconsiderabile se i backend crescono.

---

## R8 — Misura di qualità e baseline di performance (SC-004, NFR-05/06, DA-003)

**Decisione.** Le soglie numeriche **non** si fissano in questo piano: si misurano in fase di
implementazione/test su un **corpus campione con ground-truth** (set di query note → chunk attesi),
usando il **prototipo come baseline** (dogfooding). Metrica primaria: `precision@k` (k=5); il prototipo
locale Ollama ha hit@5 ≈ 0.67 come riferimento minimo accettabile, cloud ≈ 0.80 (da decomposizione Must).
La soglia di accettazione di SC-004 viene fissata quando la misura è disponibile e registrata nei test.

**Razionale.** Decisione "misurare prima" (DA-003): fissare numeri assoluti senza misura sarebbe
arbitrario. Il corpus di dogfooding è già indicizzato e dà un baseline riproducibile.

**Alternative considerate.** (a) Fissare soglie ora: arbitrario, contro DA-003 → respinta. (b) Nessuna
misura (solo test funzionali): viola Principio V (qualità *misurata*) e SC-004 → respinta.

---

## Sintesi NEEDS CLARIFICATION risolti

| Tema (dal Technical Context) | Risolto in | Esito |
|------------------------------|-----------|-------|
| Grammatiche tree-sitter per 14 linguaggi su Win+Linux | R1 | language-pack + fallback per PS/T-SQL/PL-SQL |
| Forma minima della porta vector store | R2 | upsert/query/delete/count + namespace per collezione |
| Promozione dell'`Embedder` del prototipo a porta | R3 | Protocol + factory nel composition root |
| Strategia ID stabili / idempotenza | R4 | path relativo + ordinale posizionale, scoperta ordinata |
| Logging strutturato senza framework imposto | R5 | stdlib logging + redazione segreti |
| Punto di config unico + segreti | R6 | Settings env+file, esclusioni configurabili |
| Extra opzionali / conflitti backend | R7 | base locale + extra cloud, import lazy |
| Soglie performance/qualità | R8 | misurate, baseline prototipo (DA-003) |

**Tutti i NEEDS CLARIFICATION tecnici sono risolti.** Si procede alla Phase 1 (data-model, contratti,
quickstart).
