# Corollario di costo — motivazione di FEAT-009 (refresh incrementale)

> **Stato:** nota di motivazione/corollario per **FEAT-009** dell'epica `sertor-core`
> (*Manutenzione/refresh incrementale dell'indice RAG sui sorgenti*), oggi **Could / da decomporre**.
> Raccolta il **2026-06-15** analizzando il costo del re-index del dogfood dopo il merge di
> `sertor-flow`. Non è una decomposizione EARS: è la **base di evidenza** che alza la rilevanza della
> feature su ospiti grandi.

## Tesi

Oggi **`engine.index(rebuild=True)` ri-processa e ri-scrive l'intero corpus a ogni invocazione**.
L'unico stadio realmente *incrementale* è il **costo degli embedding**, grazie alla cache per
content-hash (FEAT-019, `SERTOR_EMBED_CACHE`). Tutto il resto — scoperta file, chunking, scrittura
sul vector store, indice lessicale BM25, code-graph — è **full ogni volta**. Su repository grandi
questo non scala: è esattamente il vuoto che FEAT-009 deve colmare.

## I cinque stadi di `index(rebuild=True)` (fonte: `src/sertor_core/services/indexing.py`)

| Stadio | Comportamento | Incrementale oggi? |
|---|---|---|
| **discover** (ingestione, `:71`) | cammina e legge **tutto** il corpus | ❌ full |
| **chunk** (`:74-75`) | ri-chunka **ogni** documento (tree-sitter per il codice), **sequenziale/single-thread** | ❌ full |
| **embed** (`:78`) | chiama `embed()` su **tutti** i chunk | ✅ **solo i delta pagano** (cache 019 per content-hash) |
| **reset + upsert** (`:84-85`) | `reset` della collezione + riscrittura di **tutti** i record in Chroma (+ rebuild HNSW) | ❌ full |
| **BM25 + code-graph** (`:86-94`) | sidecar lessicale come **snapshot completo**; code-graph **ricostruito** (seconda passata di analisi del codice, AST per simboli/chiamate) | ❌ full |

**La cache aiuta solo lo stadio 3** (il costo $ degli embedding, es. Azure). Non tocca discover,
chunk, scrittura store, BM25, grafo — che restano wall-clock pieno e CPU/I-O piena.

## Misura reale (2026-06-15, questa macchina, Windows)

`discover` + `chunk` **da soli** (senza embed/store/grafo/BM25), su un albero di **337 MB /
21.585 documenti / 449.728 chunk** (scope non filtrato, includeva i virtualenv):

- **discover ≈ 88 s · chunk ≈ 37 s · totale ≈ 126 s**
- rate end-to-end **≈ 2,7 MB/s (~171 doc/s)**; **discover (I/O) domina** su chunk.

> Caveat: quel run usava `Settings()` di default **senza i pattern di esclusione** del `.env`, quindi
> ha indicizzato anche `.venv`/`prototype`/store — 21.585 doc invece dei **652** del dogfood reale (la
> differenza è **tutta** negli exclude patterns). Il numero assoluto va letto come **rate**, non come
> il costo del dogfood (che, ben filtrato, chunka in pochi secondi). Lezione a margine: su un ospite gli
> **exclude patterns** incidono enormemente sul costo.

## Estrapolazione (a ~2,7 MB/s, solo discover+chunk)

| Sorgente (ben filtrata) | discover+chunk stimato |
|---|---|
| ~10 MB | ~4 s |
| ~100 MB | ~40 s |
| ~300–500 MB | **~2–3 min** |

Il re-index **completo** è **più pesante** di così: somma a discover+chunk anche la **seconda passata
del code-graph**, la build BM25 e il `reset`+`upsert`+HNSW di Chroma — tutti full, nessuno aiutato
dalla cache.

## Implicazione per la prioritizzazione

- Su corpora piccoli (es. il dogfood, 652 doc) il full re-index è di pochi secondi → la **regola
  standing di re-index a fine step/merge** (CLAUDE.md p.5) è un mitigante sufficiente.
- Su **ospiti grandi** (centinaia di MB / decine di migliaia di file) il full re-index a ogni modifica
  è **minuti**, dominato da I/O (discover) e CPU (chunk + grafo) — stadi che la cache **non** copre.
  Qui FEAT-009 smette di essere un *Could* mitigato e diventa **rilevante davvero**.
- Direzione di design per FEAT-009 (quando si decompone): indicizzare **solo i file cambiati**
  (rilevamento per mtime/hash), gestire le **cancellazioni** (rimuovere i chunk dei file spariti),
  e rendere **incrementali** anche store/BM25/grafo (non solo gli embedding) — altrimenti il collo di
  bottiglia si sposta ma non sparisce.

## Possibili leve complementari (da valutare in decomposizione)

- **Parallelizzare il chunking** (oggi loop sequenziale single-thread) — taglia lo stadio CPU.
- **discover incrementale** (walk + stat, salta file invariati prima di leggerli) — taglia lo stadio
  I/O dominante.
- **Upsert/delete mirati** sul vector store invece di `reset`+full-upsert.
