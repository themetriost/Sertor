# Implementation Plan: Contratto di retrieval verso l'agente

**Branch**: `118-contratto-retrieval-agente` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/118-contratto-retrieval-agente/spec.md`

## Summary

Portare il segnale **strutturale** del code-graph dentro la ricerca combinata come **terzo flusso
etichettato** (dietro interruttore, spento di default), e **prima** costruire l'**harness di
valutazione agent-facing** che ne è il gate.

L'ordine è invertito rispetto al valore, deliberatamente: la macchina di valutazione esistente misura
il *retrieval* (hit@k/MRR su ciò che viene recuperato), non il *comportamento dell'agente* che quel
materiale lo legge. Senza colmare quel divario il fan-out si consegnerebbe sulla fiducia — e il costo
che introduce (materiale aggiuntivo su **ogni** ricerca) è esattamente il danno che non si vede senza
misurarlo.

**Approccio tecnico:** tre entità di dominio nuove che *compongono* quelle esistenti; due funzioni pure
che risolvono i punti d'ingresso dalla query senza LLM; un servizio orchestrante che mappa le
indisponibilità del grafo in **tre** cause distinte; una superficie MCP che aggiunge la chiave `graph`
solo a interruttore acceso; un harness fuori dal prodotto che confronta due varianti di payload sul
comportamento dell'agente.

## Technical Context

**Language/Version**: Python ≥ 3.11

**Primary Dependencies**: nessuna nuova nel core. `networkx` resta l'extra opzionale `graph` già
esistente (serve alla navigazione, non alla costruzione). L'harness usa la CLI dell'assistente già
presente sulla macchina, in modalità headless.

**Storage**: nessuno nuovo. Il grafo è l'artefatto JSON già prodotto a ogni indicizzazione; gli esiti
dell'harness sono JSONL sotto `eval_ab/results/` (git-ignored).

**Testing**: `pytest` (unit + integration, offline, senza rete). L'harness **non** entra nella suite:
richiede un agente e non è riproducibile a costo zero.

**Target Platform**: Windows · macOS · Linux (moduli nuovi del core: stdlib-only).

**Project Type**: libreria Python (`sertor-core`) con superfici sottili (CLI, server MCP).

**Performance Goals**: il ramo strutturale è fatto di lookup su un grafo **già caricato in memoria**.
Obiettivo: costo marginale **nullo** su una domanda che non attiva alcun punto d'ingresso (nessun
accesso al grafo). Il costo sulle domande che lo attivano è **misurato**, non assunto (SC-008).

**Constraints**: nessun LLM nel percorso di retrieval (RNF-1) · additività totale a interruttore spento
(SC-007) · determinismo della risoluzione degli ingressi (RNF-2) · nessuna dipendenza nuova nel core.

**Scale/Scope**: ~6 file nuovi nel core + estensioni puntuali a 6 esistenti; harness ~5 file fuori dal
prodotto; misure su 20–30 domande × 2 arm × 3 ripetizioni.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** Le entità nuove vivono in `domain/`
  senza importare SDK. Le funzioni di risoluzione degli ingressi sono pure. Il servizio orchestrante
  dipende dalle **porte**, non dagli adapter. L'unico punto che conosce le implementazioni concrete
  resta `composition.py` (nuova factory `build_agent_context`).
- [x] **II — Boundary & local-first: PASS.** L'accesso al grafo passa dalla porta `CodeGraph` già
  esistente; nessuna dipendenza esterna nuova; la capacità funziona interamente in locale.
- [x] **III — YAGNI & unità piccole: PASS.** Le entità nuove esistono perché la spec richiede stati
  per-relazione e provenienza per-ingresso, che le strutture attuali non portano. La via d'ingresso
  semantica è **rinviata** (R15) anziché costruita «perché un giorno servirà».
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS.** Le indisponibilità del grafo diventano
  **stati tipizzati** (`graph_not_built` / `navigation_library_missing` / `graph_artifact_unusable`),
  mai una lista vuota. Un risultato vuoto *afferma un'assenza*: è il `None` silenzioso che il principio
  vieta, tradotto nel dominio del retrieval.
- [x] **V — Testabilità & misure: PASS.** Risoluzione degli ingressi e property di stato sono pure →
  test F.I.R.S.T. senza I/O; il grafo si mocka via `Protocol`. E la feature **aggiunge una misura** che
  il progetto non aveva: il gate duplice è un requisito funzionale (FR-034..038), non una raccomandazione.
- [x] **VI — Idempotenza & non-distruttività: PASS.** A interruttore spento la risposta è identica a
  oggi (SC-007, asserito da test). Il campo `totals` su `ContextBundle` è additivo con default vuoto.
  Nessuna migrazione di artefatti.
- [x] **VII — Leggibilità: PASS.** Naming di dominio: `EntryPoint`, `RelationBlock`, `SymbolContext`,
  `resolve_entry_points`, `mark_corroboration`.
- [x] **VIII — Configurabilità centralizzata: PASS.** Le tre manopole nuove hanno il default **solo**
  in `Settings` (R12); nessun valore murato nei componenti.
- [x] **IX — Osservabilità: PASS.** Il ramo strutturale emette un evento con i punti d'ingresso
  risolti, la loro provenienza e l'esito. Una risoluzione a vuoto e un'indisponibilità sono
  **osservabili**, non silenziose.
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS.** Nessun percorso né nome di dominio nel corpo; la
  risoluzione opera su qualunque corpus indicizzato; tetto e soglia sono configurabili. *Limite
  dichiarato:* la via lessicale è debole quando la lingua della domanda differisce da quella degli
  identificatori — riconosciuto negli Edge Cases della spec, non un'assunzione nascosta sull'ospite.
- [x] **XI — Consumo via vehicles: PASS.** L'harness cattura i payload eseguendo **CLI/MCP**, non
  importando `sertor_core` (R3). Gli import diretti restano confinati agli unit test, che è l'eccezione
  prevista dal principio.
- [x] **XII — Fail Loud, Fix the Cause: PASS.** È il cuore della feature: nessuna indisponibilità
  silenziata in una lista vuota. In più la feature **rimuove un silenzio esistente** — le due invarianti
  della valutazione strutturale, oggi vere ma non protette, ricevono test che falliscono se violate
  (R14); e il discriminante fragile di R6 viene **pinnato da un test** invece che lasciato degradare.
- [x] **XIII — Product Plane vs. Fixture Plane: PASS.** La feature è stateless rispetto al corpus (non
  scrive nell'asset indicizzato) → cerimonia minima. L'harness gira sul dogfood ma la sua utilità è
  dichiarata per **qualunque ospite**: domande e fonti attese vengono dalla suite di valutazione
  dell'ospite, non da fixture interne. Nessun workaround-fixture tappa un buco-prodotto.
- [x] **Allineamento alla missione: PASS.** È esattamente la stella polare — la fusione code+doc **resa
  all'agente**. Oggi il grafo, la descrizione più precisa che abbiamo di *cosa fa* il codice, è
  costruito a ogni indicizzazione e caricato a ogni avvio, ma raggiunge l'agente **solo se lui lo
  chiede**. Questa feature lo porta nel materiale reso, e ne misura la qualità con un metro che prima
  non esisteva.

**Esito: 13/13 PASS + missione PASS, senza deroghe.** Nessuna voce in Complexity Tracking.

*Ri-verifica post-design (dopo data-model e contracts): invariata, 13/13 PASS.* Il design non ha
introdotto nuove dipendenze, non ha spostato scelte concrete fuori da `composition.py`, e non ha
aggiunto stati impostabili a mano (lo stato complessivo è derivato — R5).

## Project Structure

### Documentation (this feature)

```text
specs/118-contratto-retrieval-agente/
├── plan.md              # questo file
├── spec.md              # cosa e perché (3 user story · 40 FR · 10 SC)
├── research.md          # 15 decisioni di progetto (R1..R15)
├── data-model.md        # entità nuove e invarianti
├── quickstart.md        # come esercitare capacità e misure
├── checklists/
│   └── requirements.md  # validazione della spec (16/16)
├── contracts/
│   ├── agent-context.md # forma del terzo flusso (payload)
│   └── graph-entry.md   # contratto delle vie d'ingresso deterministiche
└── tasks.md             # output di /speckit-tasks
```

### Source Code (repository root)

```text
src/sertor_core/
├── domain/
│   ├── agent_context.py         # NUOVO — EntryPoint · RelationBlock · SymbolContext ·
│   │                            #         GraphBranch (status derivato) · AgentContext
│   ├── entities.py              # ESTESO — ContextBundle: campo additivo `totals`
│   └── ports.py                 # ESTESO — CodeGraph: `list_symbols()`
├── services/
│   ├── graph_entry.py           # NUOVO — funzioni pure: extract_identifiers ·
│   │                            #         match_symbol_table · resolve_entry_points
│   ├── agent_context.py         # NUOVO — AgentContextService: orchestra facade + grafo,
│   │                            #         mappa le 3 indisponibilità, marca la corroborazione
│   └── eval/runner.py           # ESTESO — segnaposto promosso a costante nominata
├── adapters/graph/
│   └── networkx_graph.py        # ESTESO — list_symbols() + conteggio totali pre-taglio
├── config/settings.py           # ESTESO — 3 manopole nuove, default conservativi
└── composition.py               # ESTESO — build_agent_context()

src/sertor_mcp/
└── server.py                    # ESTESO — descrizioni dei tool derivate da Settings;
                                 #          chiave `graph` in search_combined a flag acceso

tests/unit/
├── test_agent_context_entities.py    # NUOVO — invarianti dello stato derivato
├── test_graph_entry.py               # NUOVO — vie d'ingresso (funzioni pure)
├── test_agent_context_service.py     # NUOVO — 3 indisponibilità · corroborazione · troncamento
├── test_eval_routing_invariants.py   # NUOVO — instradamento esclusivo · indipendenza dal segnaposto
├── test_score_contract.py            # NUOVO — descrizione derivata dalla configurazione
└── test_mcp_combined_graph.py        # NUOVO — additività a flag spento · forma a flag acceso

eval_ab/                          # NUOVO — FUORI dal prodotto e dalla suite
├── README.md                     # regole di decisione REGISTRATE PRIMA delle esecuzioni
├── cases.toml                    # domande + fonti attese (dalla suite esistente)
├── capture.py                    # cattura i payload via vehicle
├── variants.py                   # trasformazioni pure: strip_scores · strip_graph
├── drive.py                      # esegue gli arm, calcola i verdetti deterministici
└── results/                      # JSONL per (misura, arm, esecuzione) — git-ignored
```

**Structure Decision**: layout a progetto singolo, coerente con la Clean Architecture esistente. Il
**solo elemento fuori schema** è `eval_ab/`, deliberatamente esterno sia a `src/` (non è prodotto: non
viaggia col pacchetto) sia a `tests/` (non è deterministico: richiede un agente, costa denaro, non gira
offline). Motivazione completa in R1.

## Fasi di consegna

L'ordine segue le priorità della spec e rende ogni fase **indipendentemente verificabile**.

| Fase | Contenuto | User story | Verificabile con |
|---|---|---|---|
| **F1** | Blindatura delle invarianti della valutazione + costante nominata | US2 | test che falliscono se le invarianti si rompono |
| **F2** | Descrizione dei tool derivata dalla configurazione (contratto di comparabilità + asimmetria delle scale) | US2 | test su due configurazioni |
| **F3** | Entità di dominio + porta estesa + totali pre-taglio | US3 | test puri sulle invarianti dello stato |
| **F4** | Vie d'ingresso deterministiche (funzioni pure) | US3 | test puri, inclusi i casi che NON devono agganciare |
| **F5** | Servizio orchestrante + factory + manopole | US3 | test sulle 3 indisponibilità e sulla corroborazione |
| **F6** | Superficie MCP dietro interruttore | US3 | test di additività a flag spento |
| **F7** | Harness A/B fuori dal prodotto | US1 | esecuzione su un caso di prova |
| **F8** | Esecuzione delle misure e applicazione del gate | US1+US3 | esiti registrati, gate applicato |

**F1–F6 sono implementabili e verificabili offline.** F7 richiede l'agente; F8 richiede F7 e produce
la decisione finale sull'attivazione (FR-034..038).

## Complexity Tracking

> Nessuna violazione da giustificare: Constitution Check 13/13 PASS + missione PASS.
