# Implementation Plan: Il server MCP funziona su entrambe le linee dell'SDK

**Branch**: `128-porting-mcp-sdk-v2` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/128-porting-mcp-sdk-v2/spec.md` · Requisiti:
[`requirements/debito-tecnico/feat-070-porting-mcp-sdk-v2/requirements.md`](../../requirements/debito-tecnico/feat-070-porting-mcp-sdk-v2/requirements.md)
· Ricerca: [research.md](./research.md)

## Summary

Il server MCP — uno dei due vehicles che la capability `rag` promette all'ospite — non parte sugli host
il cui ambiente ha risolto la major 2.x dell'SDK MCP, uscita il 2026-07-28: l'import di
`mcp.server.fastmcp` in cima al modulo uccide il processo, e **nessun** tool raggiunge l'agente. Tre nodi
della federazione l'hanno misurato; due sono degradati a CLI da oltre un mese.

**Approccio:** un modulo di compatibilità (`sertor_mcp/_sdk.py`, ~15 righe) diventa l'**unico** punto che
sa dell'esistenza di due linee, ed esporta i due nomi che servono — la classe del server e la classe
d'errore `ToolError`, che la misura ha trovato **su entrambe** con semantica identica al client. `_guard`
mappa i guasti previsti del dominio (`SertorError`) su `ToolError`, così la diagnosi arriva all'agente su
ogni linea; le eccezioni inattese restano ri-sollevate come oggi. Il vincolo passa a `>=1.2,<2.3`. Due
verifiche nuove chiudono i buchi di misura: un test **end-to-end sul protocollo** e un **settimo esito**
nell'upgrade smoke che pianta la condizione di un host già colpito.

## Technical Context

**Language/Version**: Python 3.11 e 3.12 (entrambe in CI)

**Primary Dependencies**: `mcp` (le due linee: 1.29.0 e 2.2.0 — l'extra opzionale `mcp`), `sertor-core`
(facade, dominio degli errori, osservabilità). Nessuna dipendenza nuova.

**Storage**: N/A — il server è stateless; indice e store sono del core.

**Testing**: `pytest`. Tre livelli coinvolti: unit (i 29 test del server), **contract/end-to-end nuovo**
(client MCP reale sul transport stdio), integration (upgrade smoke su host usa-e-getta).

**Target Platform**: Windows e Linux (matrice CI), avvio via stdio da un client MCP.

**Project Type**: libreria + vehicle (server MCP consumatore sottile del core).

**Performance Goals**: nessuna regressione sull'avvio (~1s di warm-up, entro il timeout di 30s del
client). La selezione della linea è un import: costo trascurabile e nessuna chiamata di rete.

**Constraints**: l'SDK resta confinato nell'extra `mcp` (il core senza extra non deve importarlo); il
contratto verso l'agente non cambia, tranne il miglioramento sugli errori previsti.

**Scale/Scope**: 10 tool, 1 file da modificare + 1 nuovo, 2 punti di vincolo, 11 test esistenti come
presidio, 2 verifiche nuove.

## Constitution Check

*GATE: passato prima della Phase 0; **ri-valutato dopo il design** (esito in fondo alla sezione).*

Gate derivati dalla costituzione (`.specify/memory/constitution.md`, v1.6.0).

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** Il nuovo modulo vive in `sertor_mcp/`,
  cioè in un **vehicle**, non nel core: `sertor_core` continua a non conoscere l'SDK MCP. La direzione
  delle dipendenze non cambia (server → core, mai il contrario).
- [x] **II — Boundary & local-first: PASS.** L'SDK resta dietro l'extra opzionale `mcp`; il modulo di
  compatibilità è esso stesso un boundary esplicito dove prima c'era un import nudo.
- [x] **III — YAGNI & unità piccole: PASS.** Un modulo di ~15 righe con due nomi, giustificato da
  un'evidenza **presente** (due linee vive, tre host rotti). Le alternative più strutturate (un adapter
  per linea) sono state scartate in R-1 come sproporzionate.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS, rafforzato.** La feature **aumenta** l'esplicitezza:
  oggi la diagnosi di un guasto previsto arriva al client per accidente (v1 inoltra ogni messaggio) e su
  v2 non arriverebbe; dopo, arriva **per costruzione** perché lo dichiariamo. Nessun `None` silenzioso,
  nessuno stato parziale. REQ-003 rende esplicito anche il fallimento d'import.
- [x] **V — Testabilità & misure: PASS.** 11 test esistenti nominati come presidio (R-3), un test
  end-to-end nuovo, esecuzione su entrambe le linee (R-5), un esito d'integrazione non-vacuo (R-4).
  *La parte «qualità retrieval (hit@k/MRR)» è **N/A**: la feature non tocca il retrieval, tocca il
  transport che lo consegna.*
- [x] **VI — Idempotenza & non-distruttività: N/A con motivo.** Nessuna scrittura, nessun artefatto
  generato, nessun file dell'ospite toccato. L'import è deterministico per costruzione.
- [x] **VII — Leggibilità: PASS.** I nomi restano di dominio (`ServerClass`, `ToolError`, `SDK_LINE`); il
  modulo porta un commento sull'**intenzione** (perché due linee esistono e cosa succede quando la
  prossima major arriva), non sulla meccanica.
- [x] **VIII — Configurabilità centralizzata: N/A con motivo.** Nessuna manopola nuova: quale linea usare
  **non è una scelta dell'utente**, è un fatto del suo ambiente. Renderla configurabile darebbe all'ospite
  una leva su cui può solo sbagliare.
- [x] **IX — Osservabilità: PASS.** FR-009 impone nomi e campi invariati degli eventi (`mcp.<tool>`,
  `mcp.<tool>.error`, `mcp.self_test`), presidiati da 6 test. Lo scrub dei segreti nell'evento resta, e la
  mappatura **non** introduce nuovi canali verso il client per le eccezioni inattese.
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS.** Nessun percorso, nome o struttura d'ospite: il
  modulo è puro Python e la selezione dipende solo da ciò che è installato. Il test end-to-end lancia il
  server come processo, quindi vale su qualunque host.
- [x] **XI — Consumo via vehicles: PASS, ed è il punto della feature.** Il server MCP **è** un vehicle, e
  questa feature lo rimette in funzione dove è morto. Il test end-to-end nuovo lo esercita **come lo
  esercita un client** — lanciandolo come processo e parlando il protocollo — invece di importarne le
  funzioni: è il principio applicato alla verifica di se stesso (→ [[misura-al-confine-pubblico]]).
- [x] **XII — Fail Loud, Fix the Cause: PASS, ed è la ragione d'essere.** Il tetto `<2` di agosto era il
  contenimento; questa feature **rimuove la causa** (codice fermo su una linea sola) invece di continuare
  ad aggirarla. Nessuna capacità viene disattivata per schivare l'errore; REQ-003 trasforma un
  `ModuleNotFoundError` su un sottomodulo interno in un messaggio che nomina versione e intervallo.
- [x] **XIII — Product Plane vs. Fixture Plane (NON-NEGOZIABILE): PASS con dichiarazione.** L'esito di
  R-4 **pianta una condizione nella fixture** (forza il runtime dell'host a risolvere la major 2.x). È
  piano-fixture, e va tenuto distinto: la decisione di prodotto — portare il server — è giustificata dal
  **caso reale-utente** (tre nodi nominati, con misure proprie), non dalla comodità della fixture. La
  piantagione **non** tappa un buco di prodotto: serve a evitare che l'esito passi gratis, ed è
  accompagnata dall'asserzione che *prima* dell'upgrade l'import **fallisca** — senza la quale la fixture
  misurerebbe se stessa. Nessuna OPEN PRODUCT QUESTION aperta da questa feature.
- [x] **XIV — Derived State, Not Declared (NON-NEGOZIABILE): PASS con riconciliatore nominato.** Due
  valori da esaminare: **(a)** `SDK_LINE` — **derivato** dall'import che è riuscito, non dichiarato da
  nessuna parte, quindi non può divergere. **(b)** Il commento che accompagna il vincolo e nomina la
  versione misurata (`2.2.0`, 2026-09-13): è **prosa che descrive un fatto a monte**, quindi invecchia per
  costruzione e non è derivabile dal nostro repo. Il riconciliatore è **nominato**, non promesso alla
  disciplina: **E10-FEAT-071**, estesa il 2026-09-13 a coprire la domanda *«è uscita a monte una versione
  sopra il nostro tetto?»* — che è il report che rende visibile la divergenza. Finché quella guardia non
  esiste, il pin è sorvegliato dalla memoria umana, e la spec lo dichiara come **R-6** invece di presumerlo
  risolto.
- [x] **Allineamento alla missione: PASS.** La mission misura la **qualità del retrieval reso all'agente**.
  Se il vehicle che lo consegna non parte, quella qualità è **zero** — indipendentemente da quanto sia buono
  l'indice. Per due nodi noti per nome la fusione code+doc esiste nell'indice e **non arriva all'agente** da
  oltre un mese. Questa feature non è un concern periferico: ripristina il canale su cui la mission si
  misura, e la parte sugli errori ne migliora la **leggibilità** per l'agente.

**Esito del gate: nessuna violazione.** *Complexity Tracking* resta vuoto.

**Ri-valutazione post-design (Phase 1):** i tre artefatti di design (`data-model.md`, `contracts/`,
`quickstart.md`) non hanno introdotto astrazioni, manopole o dipendenze ulteriori rispetto a quanto
valutato sopra: il contratto del layer resta due nomi + un valore derivato, e il contratto d'errore verso
il client è una **restrizione** di ciò che esce, non un canale nuovo. **Gate confermato PASS su tutti i
punti**, con le stesse motivazioni.

## Project Structure

### Documentation (this feature)

```text
specs/128-porting-mcp-sdk-v2/
├── spec.md                    # cosa e perché (fatto)
├── checklists/requirements.md # validazione della spec, 15/16 con 3 riserve (fatto)
├── research.md                # Phase 0: R-1..R-6, tutte misurate (fatto)
├── plan.md                    # questo file
├── data-model.md              # Phase 1: entità e stati
├── contracts/
│   ├── sdk-compat.md          # il contratto del layer di compatibilità
│   └── tool-error-surface.md  # cosa arriva al client, per classe d'errore
├── quickstart.md              # Phase 1: come verificarlo a mano
└── tasks.md                   # Phase 2 (/speckit-tasks — non creato qui)
```

### Source Code (repository root)

```text
src/sertor_mcp/
├── _sdk.py          # NUOVO — unico punto che conosce le due linee: ServerClass, ToolError, SDK_LINE
├── server.py        # MODIFICATO — :25 import dal layer · :112 istanziazione · _guard: mappa SertorError
└── __init__.py      # invariato

tests/
├── unit/
│   ├── test_sdk_compat.py          # NUOVO — il layer: entrambi i rami, SDK_LINE derivato
│   ├── test_mcp_server.py          # MODIFICATO — + mappatura SertorError→ToolError (i 4 test di
│   │                               #   re-raise restano invariati: vedi R-2)
│   ├── test_mcp_graph_tools.py     # invariato (gira anche sull'altra linea)
│   ├── test_mcp_combined_graph.py  # invariato (idem)
│   ├── test_score_contract.py      # invariato (idem)
│   ├── test_doctor.py              # invariato (idem)
│   └── test_single_venv_guard.py   # invariato (idem)
└── contract/
    └── test_mcp_protocol_e2e.py    # NUOVO — client MCP reale su stdio: handshake, 10 tool,
                                    #   payload, contenuto diagnostico di un guasto previsto

tests/integration/test_host_smoke.py   # MODIFICATO — settimo esito `mcp-server-imports`
scripts/smoke.ps1 · scripts/smoke.sh   # MODIFICATI — pianta la condizione + asserisce i due stati
pyproject.toml                          # MODIFICATO — :52 e :91 → `mcp>=1.2,<2.3` + commento
.github/workflows/ci.yml                # MODIFICATO — passo «test MCP sull'altra linea SDK»
docs/troubleshooting.md                 # MODIFICATO — versioni supportate + azione per chi è colpito
```

**Structure Decision.** Struttura esistente, nessuna riorganizzazione: la feature aggiunge **un** modulo
al vehicle `sertor_mcp` e **due** verifiche nuove (una unit sul layer, una contract sul protocollo).

⚠️ **`tests/contract/` è una cartella NUOVA** — verificato in fase `analyze`: `tests/` contiene oggi
`unit/`, `integration/` e `fixtures/`, nessuna `contract/`. *(La prima stesura di questo paragrafo la dava
«prevista dalla convenzione del repo»: era un claim non verificato.)* Va creata col proprio `__init__.py`,
come le sorelle. La raccolta non è un problema: `testpaths = ["tests"]` prende l'albero intero. Si crea
invece di mettere il test fra gli unit perché la distinzione è reale — gli unit **chiamano le funzioni**
del server, questo **parla il protocollo** lanciando un processo.

## Ordine di lavoro e dipendenze

1. **`_sdk.py` + il suo unit test.** Va per primo: tutto il resto importa da lì.
2. **`server.py`**: import dal layer, istanziazione, mappatura in `_guard`.
3. **Test end-to-end sul protocollo.** Prima del vincolo, perché è la verifica che dice se il porting
   funziona davvero; deve girare su entrambe le linee.
4. **Vincolo + commento** in `pyproject.toml` (2 punti) e rigenerazione del lock.
5. **Passo CI sull'altra linea** (con l'asserzione su `SDK_LINE`, altrimenti il passo è verde e vuoto).
6. **Settimo esito dell'upgrade smoke** (piantare la condizione + asserire i due stati).
7. **Documentazione utente** (`docs/troubleshooting.md`): la feature non è completa senza.
8. **Gate pre-merge**: sette suite + `ruff`, più gli smoke, che girano perché il diff tocca le dipendenze.

## Rischi di esecuzione noti

- **Il passo CI sull'altra linea può risultare verde e vuoto** se l'ambiente non ha davvero cambiato
  linea: mitigato dall'asserzione su `SDK_LINE` come **primo** test del passo.
- **Il settimo esito può passare gratis** se la condizione non viene piantata: mitigato asserendo che
  *prima* dell'upgrade l'import fallisca (R-4).
- **Il lock del workspace non deve spostarsi** per via del passo CI: si usa l'isolamento `uv --with`, che
  non tocca `uv.lock`.
- **`docs/troubleshooting.md` contiene oggi un rimedio che diventa obsoleto** (descrive il guasto e dice
  come conviverci): va riscritto, non solo integrato.
