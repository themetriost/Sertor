# Implementation Plan: smoke di upgrade — testare la strada che spediamo

**Branch**: `125-smoke-di-upgrade` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/125-smoke-di-upgrade/spec.md`

## Summary

Lo smoke end-to-end esiste, gira in CI su quattro matrici e installa da `git+url@<ref>` — ma **su un
host pulito**. Nessuna verifica tocca il verbo che gli ospiti eseguono davvero: **`upgrade`**. Su ~14
difetti reali dal campo, **13 stanno nella superficie di consegna** e **7 richiedono un'installazione
preesistente più vecchia** per manifestarsi.

**Approccio:** *estendere la macchina, non costruirne una seconda.* `scripts/smoke.{ps1,sh}` accetta un
nuovo parametro **`-FromRef`**: quando è valorizzato, lo script **installa la release precedente**,
**aggiorna** al ref in prova, e asserisce gli **esiti sullo stato dell'host** — il pin si è mosso,
l'automatismo è uno e aggiornato, la configurazione dell'ospite è preservata, la salute è verde. Due
percorsi d'esecuzione: uno **automatico e leggero** vincolante al rilascio, uno **completo a richiesta**.

## Technical Context

**Language/Version**: PowerShell 5.1+/Core e Bash (gli script di piattaforma esistenti); Python 3.11+
per il wrapper `pytest`.

**Primary Dependencies**: nessuna nuova. `uvx` (già richiesto dallo smoke), `git`, la CLI installata.

**Storage**: nessuna. Host usa-e-getta creati e buttati.

**Testing**: `pytest -m integration` come wrapper, GitHub Actions come esecutore.

**Target Platform**: `ubuntu-latest` e `windows-latest` × `claude` e `copilot-cli`.

**Project Type**: infrastruttura di verifica. **Nessuna modifica al prodotto**: questa feature
*misura*, non cambia l'aggiornamento.

**Performance Goals**: il percorso **automatico** deve restare economico abbastanza da girare a ogni
rilascio senza che nessuno voglia spegnerlo (è il rischio R-1). Il percorso **completo** non ha budget:
si lancia a richiesta.

**Constraints**:
- **Rete obbligatoria** (`uvx` scarica da git). Un'assenza di rete è un **impedimento d'ambiente** e
  deve essere distinguibile da un difetto di prodotto (FR-011).
- **Nessuna modifica al comportamento di `upgrade`**: i difetti che questa verifica rileverà si
  chiudono altrove.
- **Parità fra i due script di piattaforma**: `smoke.ps1` e `smoke.sh` devono restare equivalenti, come
  già impone la guardia esistente.

**Scale/Scope**: 4 combinazioni assistente × piattaforma già esistenti; l'aggiornamento le raddoppia
come tempo — da cui la separazione automatico/completo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I — Dipendenze verso l'interno:** **N/A.** Nessun codice di prodotto toccato; è verifica.
- [x] **II — Boundary & local-first:** **PASS.** L'unica dipendenza esterna è la rete per `uvx`, già
  richiesta dallo smoke esistente e dichiarata.
- [x] **III — YAGNI & unità piccole:** **PASS.** Un **parametro** aggiunto a uno script esistente, non
  un secondo harness. Le asserzioni nuove sono quelle derivate dai difetti **realmente occorsi**, non
  un elenco esaustivo di ciò che si potrebbe verificare.
- [x] **IV — Errori espliciti:** **PASS.** Lo script fallisce a voce alta (`Fail`) e distingue
  l'impedimento d'ambiente dal difetto di prodotto (FR-011): due esiti diversi, non un unico rosso.
- [x] **V — Testabilità & misure:** **PASS, ed è il cuore.** La feature **è** una misura, e ha un
  criterio d'accettazione falsificabile (SC-001: ≥5 dei 7 difetti noti rilevati).
- [x] **VI — Idempotenza & non-distruttività:** **PASS.** Ogni esecuzione crea un host nuovo e lo
  butta; nulla tocca il repo o la macchina dello sviluppatore.
- [x] **VII — Leggibilità:** **PASS.** `-FromRef` dice cosa fa; le asserzioni portano il nome
  dell'esito che verificano, non un numero.
- [x] **VIII — Configurabilità centralizzata:** **PASS.** Ref e perimetro sono parametri, non costanti
  sparse; l'elenco degli esiti asseriti vive in un punto solo (FR-015).
- [x] **IX — Osservabilità:** **PASS.** Il fallimento **nomina** l'esito divergente e il contesto
  (FR-008) — è la Storia 2, non un extra.
- [x] **X — Host-agnostico:** **PASS.** Lo script crea un host **sintetico e neutro**, come già fa; non
  presume nulla del progetto che lo ospita.
- [x] **XI — Consumo via vehicles:** **PASS.** La verifica esercita `sertor install` / `sertor upgrade`
  / `sertor-rag doctor` — cioè **solo** i vehicles, che è precisamente il punto: prova ciò che l'ospite
  esegue.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS.** La feature nasce per **rendere visibile** una
  classe di guasti che oggi si scopre presso gli ospiti. La distinzione ambiente↔prodotto evita il
  rosso indistinto che porterebbe a ignorare il gate.
- [x] **XIII — Product Plane vs. Fixture Plane:** **PASS**, cerimonia **bassa**: il prodotto non muta
  l'asset in place, la fixture è un host usa-e-getta creato e distrutto. La distinzione resta netta —
  ciò che si asserisce è lo **stato dell'host** (piano-prodotto), mai la forma del sorgente.
- [x] **XIV — Derived State, Not Declared:** **PASS.** La versione da cui si parte è **derivata** dal
  riferimento pubblico (l'ultimo tag), non scritta a mano in un file che invecchierebbe. È il principio
  applicato al meccanismo stesso.
- [x] **Allineamento alla missione:** **PASS.** La missione è **auto-conoscenza portabile e senza
  lock-in**: una capacità che non arriva integra all'ospite non è portabile. Questa verifica presidia
  il solo tratto di strada che nessuno percorre prima di lui.

**Esito gate: 13 PASS + 1 N/A + missione PASS.** Nessuna voce in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/125-smoke-di-upgrade/
├── plan.md              # questo file
├── spec.md              # /speckit-specify + clarify
├── research.md          # Fase 0
├── quickstart.md        # Fase 1
├── contracts/
│   └── smoke-upgrade.md # superficie dello script + esiti asseriti
├── checklists/
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
scripts/
├── smoke.ps1            # + parametro -FromRef, fase upgrade, asserzioni d'esito
└── smoke.sh             # idem, in parità

tests/integration/
└── test_host_smoke.py   # + caso d'upgrade (wrapper sottile, la logica resta nello script)

.github/workflows/
└── ci.yml               # + job automatico leggero al rilascio; + workflow manuale completo
```

**Structure Decision**: nessun file nuovo di sostanza. La macchina esiste, il test è già un **wrapper
sottile** per una ragione dichiarata nel suo docstring — *«lo script che un dev lancia a mano è quello
che gira in CI, così non possono divergere»* — e quella ragione vale identica per l'aggiornamento.
Costruire un secondo harness introdurrebbe proprio la divergenza che il primo è stato scritto per
evitare.

## Complexity Tracking

> Nessuna violazione del Constitution Check: tabella non compilata.
