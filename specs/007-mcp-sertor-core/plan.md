# Implementation Plan: Server MCP di produzione (`sertor_mcp`)

**Branch**: `spec/007-mcp-sertor-core` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-mcp-sertor-core/spec.md`

## Summary

Costruire `sertor_mcp`: un server **MCP** (trasporto stdio) che espone il retrieval vettoriale di
`sertor_core` come **tre tool** (`search_code`, `search_docs`, `search_combined`) a un client MCP
(es. Claude Code). È un **consumatore sottile** (Principio I): i tool chiamano la facade del core
(`build_facade(Settings.load())`) e formattano i risultati; nessuna logica di retrieval reimplementata.
Sostituisce il server del prototipo come binding attivo del repo (`.mcp.json` → `python -m
sertor_mcp.server`), col corpus di prodotto `sertor`. Esiste un'implementazione di **riferimento** sul
branch `feat/mcp-sertor-core` (commit `53b8e43`), compatibile con master, da cui partire — completandola
con **osservabilità** (log strutturati) e **gestione errori** esplicita non presenti nel riferimento.

## Technical Context

**Language/Version**: Python ≥ 3.11.

**Primary Dependencies**: `sertor_core` (facade di retrieval, interno); **MCP SDK** Python
(`mcp`, `FastMCP`) come **extra opzionale** isolato (`mcp`). Nessuna dipendenza pesante nuova.

**Storage**: nessuna propria. Consuma l'indice/vector store del corpus configurato via il core
(Chroma in locale · Azure AI Search in cloud), costruito **fuori** da questa feature.

**Testing**: `pytest`; unit test con facade/store **mock** (`tests/fixtures/mocks.py`:
`FakeEmbedder`, `InMemoryStore`), senza rete né indici reali.

**Target Platform**: processo locale avviato dal client MCP via stdio (Windows/Linux/macOS).

**Project Type**: pacchetto-superficie sottile sopra una libreria (single project, `src/`).

**Performance Goals**: overhead del layer trascurabile rispetto al retrieval del core (il server
aggiunge solo formattazione del risultato).

**Constraints**: host-agnostico (Principio X); sola lettura; segreti solo via `.env`; anteprima
risultati troncata per limitare il payload del client.

**Scale/Scope**: ~3 tool, un modulo `server.py` + `__init__.py`, un file di test. Estendibile con
tool grafo/ibrido quando arrivano FEAT-005/FEAT-004.

## Constitution Check

*GATE: superato prima di Phase 0 e ri-verificato dopo Phase 1 design.* Costituzione v1.1.0.

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE):** `sertor_mcp` è un **pacchetto a parte**
  che dipende da `sertor_core` (verso l'interno) e dall'SDK MCP; **non** modifica il core né vi
  inietta SDK. Il core resta usabile/testabile senza MCP. I tool chiamano `build_facade` (il main/
  composition del core). **PASS.**
- [x] **II — Boundary & local-first:** provider/backend/corpus arrivano da `Settings`; locale↔cloud
  per sola config; il server non conosce Chroma/Azure (li conosce il core). **PASS.**
- [x] **III — YAGNI & unità piccole:** un modulo, 3 tool, un formattatore; nessuna astrazione
  speculativa. L'SDK MCP è isolato in un extra. **PASS.**
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** errori reali del motore → propagati come errore
  **leggibile** al client, server resta operativo (FR-013). **Indice mancante → `[]` + warning**: è
  la policy *tollerante e voluta* del **nucleo** (facade) per composabilità — vedi CLAUDE.md "policy
  errori non uniforme e voluta" — non un null silenzioso ma uno stato osservato e segnalato. Scelta
  deliberata, coerente col core; nessuno stato parziale/corrotto. **PASS** (vedi nota Complexity).
- [x] **V — Testabilità & misure:** unit test con doppio mock (tool registrati, formato, filtro per
  tipo); nessun cloud. La qualità del retrieval è già misurata a livello core (FEAT-002); il server
  non altera il ranking. **PASS.**
- [x] **VI — Idempotenza & non-distruttività:** sola lettura; nessuna mutazione di indice/file; output
  deterministico dato l'indice; install≠run (il server non costruisce nulla all'avvio). **PASS.**
- [x] **VII — Leggibilità:** naming di dominio (`search_code`/`search_docs`/`search_combined`);
  formattatore esplicito. **PASS.**
- [x] **VIII — Configurabilità centralizzata:** zero default hardcoded nel server; tutto da `Settings`/
  `.env`; il corpus `sertor` è impostato via binding/ambiente, non nel corpo. **PASS.**
- [x] **IX — Osservabilità:** **GAP nel riferimento** → l'implementazione MUST aggiungere log
  strutturati per ogni invocazione (tool, query troncata, k, n. risultati, tempi, errori), senza
  segreti (RNF-004). Catturato come task esplicito. **PASS (con azione).**
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** il corpo del server non incorpora percorsi/nomi
  dell'ospite; ciò che varia (corpus/backend) sta in config. Gira su un altro progetto-ospite solo
  cambiando `.env`/binding. Il dogfood su Sertor non giustifica deroghe. **PASS.**

**Esito gate: PASS (10/10), con un'azione obbligatoria su IX (osservabilità) tracciata in tasks.**

## Project Structure

### Documentation (this feature)

```text
specs/007-mcp-sertor-core/
├── plan.md              # questo file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── mcp-tools.md     # contratto dei 3 tool MCP
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
└── sertor_mcp/                 # NUOVO pacchetto-superficie (consumatore sottile del core)
    ├── __init__.py             # docstring di scopo (layer sottile, Principio I)
    └── server.py               # FastMCP "sertor-rag": 3 tool + formattatore + logging + main()

tests/
└── unit/
    └── test_mcp_server.py      # tool registrati · formato risultati · filtro per tipo (mock)

# File toccati (non nuovi):
pyproject.toml                  # + extra opzionale [mcp]; + src/sertor_mcp ai packages del wheel
.mcp.json                       # → python -m sertor_mcp.server, SERTOR_CORPUS=sertor
.env.example                    # (opz.) nota su SERTOR_CORPUS=sertor per il dogfood
```

**Structure Decision**: pacchetto separato `src/sertor_mcp/` accanto a `src/sertor_core/`, coerente
con la Dependency Rule (Principio I): il core non sa nulla dell'MCP; l'MCP dipende dal core. Allinea
la struttura al riferimento sul branch (stessa collocazione), senza ereditarne lo stack morto (CLI,
modulo wiki vecchio): si porta **solo** `sertor_mcp` + test.

## Complexity Tracking

> Nessuna violazione che richieda giustificazione di complessità. Una **nota** sul Principio IV:

| Punto | Scelta | Perché non è una violazione |
|-------|--------|------------------------------|
| Indice mancante → `[]` + warning (non eccezione) | Coerente con la policy tollerante del **nucleo/facade** (CLAUDE.md), pensata per composabilità; il server è un consumatore del nucleo, non il motore baseline (che invece è strict). | Non è null silenzioso: è uno stato **osservato, loggato e segnalato**; nessuno stato parziale. Per un agente MCP, `[]`+warning è più robusto di un crash di sessione. Allineato a REQ-050/FR-012. |
