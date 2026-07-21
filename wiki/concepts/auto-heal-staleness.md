---
title: Auto-heal della staleness (client di lunga durata)
type: concept
tags: [staleness, auto-heal, mcp-server, re-index, chroma, code-graph, bm25, index-lock, dogfooding]
created: 2026-07-21
updated: 2026-07-21
sources: ["src/sertor_core/adapters/vectorstores/chroma.py", "src/sertor_core/adapters/graph/networkx_graph.py", "src/sertor_core/adapters/lexical/bm25.py", "src/sertor_core/services/indexing.py", "wiki/log/2026-06-19.md", "wiki/log/2026-07-02.md", "wiki/log/2026-07-20.md"]
---

# Auto-heal della staleness (client di lunga durata)

Un requisito nasce dalla topologia stessa del prodotto: il [[mcp-server]] è un **processo di lunga
durata** che tiene in memoria gli indici (Chroma, code-graph, BM25) e serve retrieval per un'intera
sessione, mentre il **re-index gira in un processo separato** (`sertor-rag index`, o l'hook
`rag-freshness` a fine sessione) e **riscrive gli artefatti su disco sotto ai suoi piedi**. Senza una
difesa, il server continua a leggere da handle aperti su uno store che non esiste più: risponde con dati
**stantii** — o peggio, esplode con errori opachi. È la negazione della missione stessa
([[mission-vision]]): un agente che ragiona su un indice fantasma riceve *contesto non reale* senza
saperlo.

L'**auto-heal della staleness** è l'invariante che chiude questo buco: *un client di lunga durata non
deve MAI servire dati stantii dopo un re-index cross-process*. È il **complemento a runtime** dell'hook
di freschezza ([[step-ritual]], punto 5/8) — l'hook *ricostruisce* l'indice, l'auto-heal fa sì che il
server già avviato *se ne accorga da solo* invece di richiedere un riavvio. Entrambi servono lo stesso
fine da lati opposti: uno rende l'indice fresco, l'altro rende il lettore capace di vederlo fresco.

## Le quattro gambe

L'invariante si regge su quattro meccanismi, uno per ogni artefatto che un processo esterno può
riscrivere sotto un handle vivo. Tre sono **auto-guarigioni di lettura** (il server legge stantio → si
riallinea), la quarta è un'**auto-guarigione di scrittura** (il re-index stesso trova un lucchetto
morto → lo reclama).

- **(a) Chroma — refresh-on-error.** `ChromaStore.query` (PR #89) esegue la query; se questa fallisce
  su una collezione appena recuperata, il sintomo è la firma dello store riscritto sotto il client
  aperto: il filtro metadata `where` tocca I/O reale e lancia `InternalError`, mentre la query
  puramente vettoriale regge. Il fix ricrea un client **posseduto** (`clear_system_cache()` + nuova
  connessione SQLite che *vede* lo store nuovo) e **ritenta una volta**; se persiste, `VectorStoreError`
  come prima. Un client *iniettato* (test) non è rinfrescabile. Evento osservabile
  `store_client_refreshed`.
- **(b) Code-graph — reload su firma-file.** `NetworkxCodeGraph._load` (PR #90) cachea il grafo per
  corpus con chiave `(st_mtime_ns, st_size)` dell'artefatto JSON. La prossima query confronta il token
  su disco: se l'artefatto è stato riscritto da un re-index parallelo, ricarica; se combacia, serve la
  cache. Un artefatto **sparito** invalida la cache stantia. È il sintomo gemello di (a): `find_symbol`
  che restituiva righe obsolete perché il grafo era caricato una-tantum all'avvio.
- **(c) BM25 — reload dei token.** `Bm25LexicalIndex._load` cachea `(entries, bm25, token_sets)` con lo
  stesso token `(mtime_ns, size)` del sidecar lessicale. Era «**l'unica delle tre gambe a mancare**»
  (audit A-03, 2026-07-02): Chroma e code-graph già si auto-guarivano, ma il motore di default è
  [[hybrid-retrieval|ibrido]] — il server fondeva contro un corpus lessicale lasciato stantio dal
  re-index. Colmata con lo stesso schema dei gemelli.
- **(d) Index-lock — reclamo del PID morto.** `_IndexLock` (FEAT-035, `services/indexing.py`) è il lato
  *scrittura*: un worker di re-index crashato a metà lascia `.index.lock` con un **PID morto** che
  bloccherebbe ogni re-index futuro (caso reale: PID 33516, 2026-07-17). Al conflitto, il lock legge il
  PID e — se **confermato morto** (`_pid_alive`, stdlib cross-OS: `os.kill(pid,0)` su POSIX,
  `OpenProcess`/`GetExitCodeProcess` via ctypes su Windows, **mai** `os.kill` che lì terminerebbe il
  processo) — lo reclama e procede; altrimenti `IndexLockedError`. Il record lo inquadra esplicitamente
  «come l'auto-heal Chroma/code-graph, PR #89/#90».

## Il pattern condiviso

Le quattro gambe non sono quattro patch scollegate: sono la **stessa idea** applicata a quattro
artefatti. Il pattern ha tre invarianti.

1. **Rileva la staleness a basso costo.** Nessuno *polla*. Le letture confrontano un token economico
   (la firma `(mtime_ns, size)` del file per (b)/(c), o l'*errore stesso della query* come segnale per
   (a)); la scrittura ispeziona il PID scritto nel lockfile per (d). Il caso comune — niente è cambiato
   — non paga nulla.
2. **Re-inizializza in modo trasparente.** Quando la staleness è rilevata, il componente si riallinea da
   solo (ricrea il client, ricarica l'artefatto, reclama il lock) **senza riavvio del processo** e senza
   che il chiamante debba saperlo: la prossima chiamata semplicemente vede dati freschi.
3. **Resta conservativo nell'ambiguità.** Ci si auto-guarisce solo quando la staleness è *certa*, mai
   «nel dubbio». (a) ritenta **una sola volta** e poi propaga l'errore; (d) reclama solo un PID
   **decimale e confermato morto** — un lockfile vuoto o illeggibile (magari un run vivo tra `create` e
   `write` del PID) **non** si ruba, per non svellere un lock a metà acquisizione. È il [[constitution|
   Principio XII]] applicato: l'auto-heal non è silenzioso (ogni riallineamento emette un evento —
   `store_client_refreshed`, `index.lock.reclaimed`) e non è avventato.

## Perché una pagina propria

Questo concetto viene citato ripetutamente nei record come «l'auto-heal» — il fix Chroma è «gemello» di
quello del code-graph, il BM25 è «la gamba mancante», il lock è «come l'auto-heal Chroma/code-graph» —
ma non aveva **una casa**: la conoscenza durevole era sepolta in tre voci di log datate. Questa pagina è
quella casa. Non è un changelog delle PR, è il **principio unificante** di cui ogni gamba è
un'istanza: *chi legge a lungo un artefatto scritto da altri deve saperlo rileggere quando cambia.*

## Vedi anche
- Il processo di lunga durata che questo protegge: [[mcp-server]].
- Il motore che rende (c) non-negoziabile: [[hybrid-retrieval]] · l'artefatto di (b): [[code-graph]].
- Il complemento a monte (ricostruisce l'indice): il rituale di freschezza in [[step-ritual]].
- La pratica che ha fatto emergere ogni guasto: [[dogfooding]] (tutti trovati usando l'MCP, non leggendo
  a mano).
