# Research — Server MCP di produzione (`sertor_mcp`)

**Phase 0** del piano. Decisioni tecniche con razionale e alternative scartate. Ancorato al codice
reale di `master` e al riferimento sul branch `feat/mcp-sertor-core` (commit `53b8e43`).

## R1 — SDK MCP e tipo di server

**Decisione**: usare l'SDK MCP Python ufficiale con `FastMCP` (`mcp.server.fastmcp.FastMCP`),
registrando i tool con il decoratore `@mcp.tool()` e avviando con `mcp.run()` (default stdio).

**Razionale**: è l'API ergonomica e standard del protocollo; il riferimento la usa già; minimizza il
codice di boilerplate (un decoratore per tool). La descrizione/instructions del server guidano il
client nella scelta del tool (FR-014).

**Alternative scartate**: server MCP low-level (più verboso, nessun vantaggio qui); orchestratore LLM
proprietario (era la via del prototipo `04-agentic-rag`, ma l'obiettivo è far orchestrare al client).

## R2 — Trasporto

**Decisione**: **stdio**; il server è avviato dal client MCP (`.mcp.json`), non è un servizio di rete.

**Razionale**: è il modello d'uso di Claude Code e il più semplice/sicuro (nessuna porta, nessuna
auth di rete). Coerente con l'MVP.

**Alternative scartate**: HTTP/SSE/remoto → fuori ambito (richiederebbe auth/hardening); rinviabile.

## R3 — Aggancio al core (consumatore sottile)

**Decisione**: i tool delegano a `RetrievalFacade` ottenuta da `build_facade(Settings.load())`; la
facade è costruita **una volta** e memoizzata (es. `functools.lru_cache(maxsize=1)`).

**Razionale**: Principio I/III — nessuna logica duplicata; la facade incapsula embedder+store+
collection. Verificato su `master`: `composition.build_facade(settings)` esiste; `RetrievalFacade`
espone `search_code/search_docs/search_combined`; `Settings.load()` legge `.env`. La memoizzazione
evita di ricostruire embedder/store a ogni chiamata (latenza), restando deterministica.

**Alternative scartate**: costruire la facade per-chiamata (spreco); che il server conosca
store/embeddings (viola Principio I).

## R4 — Formato dei risultati

**Decisione**: ogni hit `RetrievalResult` → `dict` con campi stabili `path`, `source`
(= `doc_type.value`), `chunk` (= `chunk_id`), `score` (arrotondato), `preview` (testo normalizzato e
**troncato** a una soglia, con marcatore di troncamento). Set di campi **identico** tra i 3 tool.

**Razionale**: payload prevedibile e citabile dall'agente; troncamento per non gonfiare il contesto
(RNF-007/FR-011). Verificato su `master`: `RetrievalResult` ha `text`, `path`, `chunk_id`,
`doc_type` (`DocType`), `score: float`, `metadata`.

**Soglia anteprima**: costante locale (es. `_PREVIEW = 300`); è un parametro di presentazione del
server, non una scelta di dominio del core → ammesso come costante del modulo (non config del core).
*(Coerente con DA-MCP3: nessun cap su `k`, ma anteprima limitata.)*

## R5 — Riconciliazione del naming del corpus

**Decisione**: il server **non** impone un corpus nel codice; lo legge da `Settings.corpus`
(env `SERTOR_CORPUS`). Il binding del repo (`.mcp.json`) imposta `SERTOR_CORPUS=sertor` (corpus di
prodotto). Si abbandona il valore legacy del riferimento (`production`).

**Razionale**: convenzione attuale (wiki `naming-corpora-indici`): `sertor` = prodotto/radice,
`prototype` = prototipo congelato. Host-agnostico (Principio VIII/X): il valore vive in config.
*(DA-MCP1: non si tocca il default interno di `Settings` — oggi `"default"` — in questa feature.)*

**Alternative scartate**: cambiare il default di `Settings.corpus` a `sertor` (impatta altri
consumatori del core; fuori scope feature); tenere `production` (disallineato dalla convenzione).

## R6 — Policy di errore e degrado

**Decisione**: due comportamenti distinti.
1. **Indice mancante / corpus vuoto** → la facade (nucleo, tollerante) restituisce `[]`; il server
   restituisce lista vuota e **logga un warning** (FR-012/REQ-050). Nessun crash.
2. **Errore interno reale** durante la ricerca → propagato come errore **leggibile** al client
   (l'SDK MCP lo trasforma in errore del tool); il server resta vivo per le chiamate successive,
   senza stato parziale (FR-013/REQ-051).

**Razionale**: allineato alla "policy errori non uniforme e voluta" del progetto (nucleo tollerante,
motore baseline strict). Per un agente, `[]`+warning su indice assente è più robusto di un'eccezione.
Coerente con Principio IV (nessun null silenzioso: lo stato è osservato e segnalato/loggato).

## R7 — Isolamento della dipendenza MCP

**Decisione**: l'SDK MCP è un **extra opzionale** in `pyproject.toml` (`[project.optional-
dependencies] mcp = ["mcp>=1.2"]`); `src/sertor_mcp` è aggiunto ai `packages` del wheel. Installare la
libreria core senza l'extra `mcp` non installa l'SDK.

**Razionale**: Principio III / RNF-003 / NFR isolamento del core: l'MCP non deve pesare su chi usa
solo la libreria. Allineato al riferimento (che introduce l'extra `mcp`). **Attenzione (porting):**
NON copiare il `pyproject.toml` del branch (sostituiva `sertor-wiki-tools` con `sertor`=CLI e
aggiungeva pacchetti inesistenti su master): applicare **solo** le due aggiunte (extra `mcp` + package
`sertor_mcp`), preservando lo script `sertor-wiki-tools` esistente.

## R8 — Osservabilità (gap del riferimento)

**Decisione**: aggiungere log strutturati a ogni invocazione di tool: nome tool, query (eventualmente
troncata nel log), `k` effettivo, numero di risultati, tempo, backend/provider e corpus; warning su
indice assente; nessun segreto.

**Razionale**: Principio IX + RNF-004. Il `server.py` di riferimento **non** logga: è un gap da
colmare. Usare l'osservabilità del core (`sertor_core.observability.logging`) se idonea, altrimenti
un logger standard configurato in modo coerente.

## R9 — Scope dei tool (onestà sul presente)

**Decisione**: esporre **solo** i 3 tool che la facade di `master` può servire (`search_code`,
`search_docs`, `search_combined`). I tool di grafo (`find_symbol`/`who_calls`/`related_docs`/
`get_context`) e il reranking ibrido restano **fuori**: la facade attuale non li espone.

**Razionale**: ancorare al codice reale; evitare tool "vuoti". Estendibilità non-breaking (FR-017):
quando arrivano FEAT-005 (grafo) e FEAT-004 (ibrido) si registrano nuovi tool senza toccare i 3.

## Riferimenti di codice verificati su `master`

- `src/sertor_core/composition.py` → `build_facade(settings)`, `Settings.load()`.
- `src/sertor_core/services/retrieval.py` → `RetrievalFacade.search_code/search_docs/search_combined`.
- `src/sertor_core/domain/entities.py` → `RetrievalResult(text, path, chunk_id, doc_type, score, metadata)`.
- `src/sertor_core/config/settings.py` → `Settings.corpus` (env `SERTOR_CORPUS`, default `"default"`), `backend`.
- `tests/fixtures/mocks.py` → `FakeEmbedder`, `InMemoryStore` (presenti).
- Riferimento: `feat/mcp-sertor-core:src/sertor_mcp/server.py` + `tests/unit/test_mcp_server.py`.
