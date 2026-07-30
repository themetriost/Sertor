# Tasks: smoke di upgrade — testare la strada che spediamo

**Feature**: `125-smoke-di-upgrade` (E15-FEAT-012) · **Date**: 2026-07-29
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) ·
[contracts/smoke-upgrade.md](./contracts/smoke-upgrade.md) · [quickstart.md](./quickstart.md)

**Nota sull'ordine dei test**: qui il "test" **è** il deliverable. L'equivalente del test-first è
scrivere per **primo** ciò che deve reggere — la non-regressione del comportamento odierno e la
distinzione ambiente↔prodotto — prima di aggiungere le asserzioni nuove.

---

## Phase 1: Setup

- [x] T001 Determinare l'**ultima release** in modo derivato e verificarlo: `git describe --tags --abbrev=0` deve restituire un tag reale e raggiungibile da `uvx`, su Windows **e** su POSIX
- [x] T002 [P] Fissare la **linea di base**: eseguire lo smoke odierno (senza `-FromRef`) e registrare durata ed esito, per poter dire quanto costa in più il percorso d'aggiornamento

---

## Phase 2: Foundational *(blocca tutte le storie)*

- [x] T003 Aggiungere il parametro **`-FromRef`** a `scripts/smoke.ps1` (default vuoto = comportamento odierno **invariato**)
- [x] T004 [P] Aggiungere lo stesso parametro a `scripts/smoke.sh`, in **parità** con la versione PowerShell
- [x] T005 Estrarre in **un solo punto** di ciascuno script la sequenza nominata degli **esiti asseriti** (FR-015), così che aggiungerne uno sia una riga in più
- [x] T006 [P] Estendere la distinzione **impedimento d'ambiente ↔ divergenza di prodotto** ai prerequisiti che l'aggiornamento richiede in più (ref di partenza raggiungibile), riusando `Require-Tool`/`Fail` esistenti
- [x] T007 Guardia di **non-regressione**: senza `-FromRef` lo script deve fare esattamente ciò che faceva — verificata, non assunta

---

## Phase 3: User Story 1 — Chi rilascia sa che l'aggiornamento funziona (P1)

**Goal**: un host usa-e-getta installa la release precedente, aggiorna, e gli esiti sono asseriti.

**Independent Test**: si prende un difetto d'aggiornamento noto, lo si ricrea, e si verifica che il
meccanismo lo **rilevi**.

- [x] T008 [US1] Implementare la **fase di installazione dalla release precedente** in `scripts/smoke.ps1` (host usa-e-getta, ambiente ripulito, come già fa la fase odierna)
- [x] T009 [US1] Implementare la **fase di aggiornamento** al ref in prova in `scripts/smoke.ps1`
- [x] T010 [P] [US1] Asserzione **pin**: dopo l'aggiornamento il riferimento fissato punta alla versione in uscita (difetto reale: pin fermo, 3 nodi)
- [x] T011 [P] [US1] Asserzione **automatismo unico e aggiornato**: ne esiste esattamente uno, ed è quello corrente (difetto reale: hook duplicati, E10-FEAT-032)
- [x] T012 [P] [US1] Asserzione **configurazione dell'ospite preservata** (difetto reale: il fix di E2-FEAT-022 rischiò di azzerare il corpus — colto da una prova manuale, non dai test)
- [x] T013 [P] [US1] Asserzione **forma dell'invocazione registrata** corrente (difetto reale: `--directory` conservato perché «c'era già»)
- [x] T014 [P] [US1] Asserzione **salute verde** dopo l'aggiornamento
- [x] T015 [US1] Portare le stesse fasi e asserzioni in `scripts/smoke.sh`, in parità
- [x] T016 [US1] Estendere `tests/integration/test_host_smoke.py` col caso d'aggiornamento — **wrapper sottile**: nessuna logica in Python, altrimenti diverge da ciò che si lancia a mano

**Checkpoint US1**: su un host reale, l'aggiornamento dalla release precedente è esercitato e i cinque
esiti sono verificati.

---

## Phase 4: User Story 2 — Un fallimento è diagnosticabile (P2)

**Goal**: chi legge il report capisce **quale** esito diverge e **dove**, senza rieseguire.

- [x] T017 [US2] Fare in modo che ogni asserzione fallita **nomini** l'esito e il contesto (assistente, piattaforma, ref di partenza e d'arrivo) in `scripts/smoke.ps1` e `scripts/smoke.sh`
- [x] T018 [P] [US2] Verificare la diagnosticabilità **introducendo deliberatamente una divergenza** e leggendo il messaggio prodotto — non ispezionando il codice
- [x] T019 [P] [US2] Verificare che un **impedimento d'ambiente** (ref di partenza irraggiungibile) produca un esito **distinto** da una divergenza di prodotto

---

## Phase 5: User Story 3 — Vincolante al momento giusto (P3)

**Goal**: il controllo economico gira sempre; quello completo resta disponibile a richiesta.

- [x] T020 [US3] Aggiungere in `.github/workflows/` il percorso **automatico**: una combinazione, dall'ultima release, vincolante prima di pubblicare
- [x] T021 [US3] Aggiungere il percorso **completo avviabile a richiesta**: tutte le combinazioni + il **salto lungo**
- [x] T022 [US3] Verificare che il percorso automatico **non** si aggiunga al ciclo di ogni modifica ordinaria

---

## Phase 6: Polish & completamento

- [x] T023 **Misurare SC-001**: applicare il meccanismo ai **sette** difetti d'aggiornamento noti e contare quanti ne rileva. Bersaglio ≥5
- [x] T024 **Dichiarare il residuo (SC-007)**: quali dei sette **non** sono coperti, e perché — nella documentazione della verifica, non in una conversazione
- [x] T025 [P] Documentare in `docs/` i due percorsi e **dichiarare** che quello completo non è richiesto per pubblicare (FR-013) — regola 3, nello stesso step
- [x] T026 Eseguire il **gate reale**: `ruff` + le sei suite
- [x] T027 🎯 **La verifica che motiva il vincolo di rilascio**: eseguire lo smoke d'aggiornamento sui **tre riscontri del nodo *Acta* del 29/07** (gate del wiki · `wiki-curator` · falso positivo del `lint`) e stabilire se un ospite che **aggiorna** li riceve davvero
- [ ] T028 Chiudere il **rituale di step** e marcare `E15-FEAT-012` ✅ in `requirements/fedelta-dogfood/epic.md` + EXEC

---

## Dependencies

```
Phase 1 → Phase 2 (parametro · elenco esiti · distinzione ambiente/prodotto · non-regressione)
             ├─► Phase 3 (US1) ──┐
             ├─► Phase 4 (US2)   ├─► Phase 6
             └─► Phase 5 (US3) ──┘
```

**US2 e US3 dipendono da US1** in modo sostanziale: non si può rendere diagnosticabile, né collocare
nel ciclo, un controllo che non esiste ancora. È detto qui invece di essere mascherato da
indipendenza — lo **MVP** è **US1**, e da sola ha già valore: esercita il verbo che nessuno esercita.

## Parallel opportunities

- **Fase 2**: T004 (parità `sh`) e T006 (distinzione ambiente) → in parallelo.
- **Fase 3**: T010–T014 sono cinque asserzioni indipendenti → in parallelo, dopo T009.
- **Fase 4**: T018 e T019 → in parallelo.
- **Fase 6**: T025 (doc) parallelo a T023/T024.

## Implementation strategy

1. **Fase 2 per intera**: senza il parametro e senza la non-regressione, ogni aggiunta rischia di
   rompere lo smoke che oggi funziona.
2. **US1** = MVP. Le cinque asserzioni **prima** su una sola combinazione, poi in parità sull'altro
   script.
3. **US2** subito dopo: un controllo che non si sa leggere non viene usato.
4. **US3** per ultimo fra le storie: è collocazione, non capacità.
5. **T027 non è rifinitura, è il punto**: finché non è eseguito, i tre fix di oggi restano provati *da
   noi* e non *sugli ospiti* — che è la ragione per cui il rilascio è fermo.

## Format validation

**28** task: checkbox · ID sequenziale · `[P]` dove parallelizzabili · `[USn]` nelle sole fasi di
storia · percorso file esplicito dove pertinente.

| Fase | Task | Storia |
|---|---|---|
| 1 Setup | T001–T002 | — |
| 2 Foundational | T003–T007 | — |
| 3 | T008–T016 | **US1** (9) |
| 4 | T017–T019 | **US2** (3) |
| 5 | T020–T022 | **US3** (3) |
| 6 Polish | T023–T028 | — |
