# Tasks: la registrazione copre un changeset, non una data

**Feature**: `124-copertura-changeset-scan` (E10-FEAT-062) · **Date**: 2026-07-29
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**Test-first richiesto**: in ogni fase i test precedono l'implementazione. I test che contano sono
quelli che **falliscono ora** e devono passare dopo — non quelli che confermano ciò che già funziona.

---

## Phase 1: Setup

- [ ] T001 Fissare la **linea di base misurata** eseguendo la matrice comportamentale su host effimeri e salvandone l'esito in `specs/124-copertura-changeset-scan/baseline.md` (8 scenari di non-rilevazione + 3 race + costo end-to-end), così che SC-001/SC-008 si verifichino contro numeri e non contro ricordi
- [ ] T002 [P] Verificare che la guardia esistente sulla stringa di schema (scritta in FEAT-045) sia individuata e leggibile in `tests/`, per estenderla invece di duplicarla

---

## Phase 2: Foundational *(blocca tutte le storie)*

- [ ] T003 [P] Test unitari del formato di copertura in `tests/unit/test_wiki_tools_coverage.py`: serializzazione, parsing, **round-trip**, path contenente `@`, elemento rimosso (`-`), ordine deterministico, blocco assente → insieme vuoto
- [ ] T004 [P] Test unitari dell'**unione** in `tests/unit/test_wiki_tools_coverage.py`: commutativa, idempotente, e `covers(path, id)` falso quando l'identità differisce
- [ ] T005 Implementare `CoveredItem`/`CoverageSet` + parse/serialize del blocco `sertor-covers/1` in `src/sertor_core/wiki_tools/coverage.py` (modulo nuovo, per `contracts/sertor-covers.1.md`)
- [ ] T006 [P] Test dell'identità di contenuto in `tests/unit/test_wiki_tools_vcs.py`: N path in **una sola** invocazione; per un file intatto l'identità coincide con quella consegnata; file assente → sentinella
- [ ] T007 Implementare l'helper di identità di contenuto in `src/sertor_core/wiki_tools/vcs.py` (`git hash-object --stdin-paths`, un solo spawn per N path — vedi research R1)
- [ ] T008 Estendere `ScanResult` in `src/sertor_core/wiki_tools/contracts.py` coi campi **additivi** `determination`, `determination_reason`, `legacy_coverage`, e `AppendLogResult` con `covered`
- [ ] T009 Estendere la guardia di schema in `tests/` per asserire che `wiki.scan/1` **non cambia** **e** che un consumatore che ignora i campi additivi resti funzionante (`contracts/wiki.scan.1.md`)

---

## Phase 3: User Story 1 — Il gate resta vivo per tutta la sessione (P1)

**Goal**: `pending` deriva dalla **copertura**, non dalla presenza di una registrazione.

**Independent Test**: con un giornale-fixture che contiene blocchi di copertura scritti a mano, `scan`
deve nominare il lavoro non coperto e tacere su quello coperto — verificabile **senza** la Storia 3.

- [ ] T010 [P] [US1] Test degli **otto scenari** oggi non rilevati in `tests/unit/test_wiki_tools_scan_git.py` (C · D · F · G · H · I · J · R3): ognuno deve riportare `pending > 0` coi path nominati
- [ ] T011 [P] [US1] Test di **non-regressione** in `tests/unit/test_wiki_tools_scan_git.py`: i casi che chiusero il blocco-di-sessione (`merge poi pull`, `lavoro e giornale nello stesso commit`) restano verdi — è il rischio R-1 del piano
- [ ] T012 [P] [US1] Test della regola di transizione in `tests/unit/test_wiki_tools_scan_git.py`: una voce **non consegnata e priva di blocco** copre il lavoro in perimetro **e** `legacy_coverage` la conta; una voce **consegnata** priva di blocco non produce alcuna deroga (research R4)
- [ ] T013 [P] [US1] Test che l'esito **non dipenda dalla data** in `tests/unit/test_wiki_tools_scan_git.py`: la stessa copertura in una partizione di ieri produce lo stesso verdetto
- [ ] T014 [US1] Sostituire `recorded_today` con il calcolo della copertura in `src/sertor_core/wiki_tools/scan.py`: leggere i blocchi da **tutte** le partizioni, `pending = lavoro_in_perimetro − copertura`
- [ ] T015 [US1] Implementare la regola di transizione ristretta (solo voci **non consegnate** prive di blocco) + popolare `legacy_coverage` in `src/sertor_core/wiki_tools/scan.py`
- [ ] T016 [US1] Rimuovere da `src/sertor_core/wiki_tools/scan.py` ciò che la copertura rende superfluo (`_today_recording`, e `_stale_recording` **solo se** i test di FR-015 restano verdi senza), senza toccare `stale_recording` nell'esito
- [ ] T017 [US1] Verificare il **costo** rispetto alla linea di base di T001 e registrarlo: entro **+15%** (SC-008)

**Checkpoint US1**: gli otto scenari passano, le non-regressioni reggono, il costo è dentro budget.

---

## Phase 4: User Story 2 — Un «pulito» non nasce da un controllo fallito (P2)

**Goal**: un insieme vuoto è un risultato **solo** quando la determinazione è riuscita.

**Independent Test**: si rende non interrogabile la fonte del controllo; l'esito deve dichiarare
`determination: failed` invece di `pending: 0`.

- [ ] T018 [P] [US2] Test in `tests/unit/test_wiki_tools_scan_git.py`: con le invocazioni di lettura che falliscono, l'esito riporta `determination: "failed"` + causa, e **non** `pending: 0` con `determination: "ok"`
- [ ] T019 [P] [US2] Test di **controprova** in `tests/unit/test_wiki_tools_scan_git.py`: stesso albero con la fonte disponibile → il lavoro risulta pendente (cioè il «pulito» del caso precedente **non era** la realtà)
- [ ] T020 [US2] Sostituire in `src/sertor_core/wiki_tools/scan.py` le degradazioni silenziose (`return … if rc == 0 else []`) con la propagazione di un fallimento **tipizzato**: mai fabbricare un insieme vuoto quando non si è potuto guardare
- [ ] T021 [US2] Popolare `determination`/`determination_reason` nell'esito ed estendere l'evento di osservabilità `scan` (metrics-only, nessun contenuto) in `src/sertor_core/wiki_tools/scan.py`
- [ ] T022 [P] [US2] Test degli hook in `packages/sertor/tests/test_wiki_guard.py`: con `determination: "failed"` l'hook **non** tratta l'esito come pulito, **non** blocca, e scrive il breadcrumb
- [ ] T023 [US2] Aggiornare l'asset `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-guard.py` per onorare `determination` (dichiara, non blocca — research R5)
- [ ] T024 [US2] Aggiornare l'asset `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.py` con la stessa semantica, solo segnalazione
- [ ] T025 [US2] Propagare gli asset aggiornati al dogfood (`python -m sertor_installer.sync`) e verificare la **parità Claude/Copilot** con le guardie esistenti

**Checkpoint US2**: un ambiente rotto è distinguibile da un progetto pulito, e non impedisce di chiudere la sessione.

---

## Phase 5: User Story 3 — La registrazione dice cosa copre (P3)

**Goal**: `append-log` deriva e persiste la copertura, senza chiederla a chi scrive.

**Independent Test**: si aggiunge una voce e si legge il giornale: il blocco c'è e corrisponde al lavoro
presente in quel momento.

- [ ] T026 [P] [US3] Test in `tests/unit/test_wiki_tools_log_rotation.py`: la voce appena scritta porta il blocco di copertura, e il blocco corrisponde al lavoro pendente **prima** dell'append
- [ ] T027 [P] [US3] Test della **composizione** in `tests/unit/test_wiki_tools_log_rotation.py`: due voci nello stesso giorno su lavori diversi → coperto è l'**unione**; la seconda copre **solo il delta** (research R6)
- [ ] T028 [P] [US3] Test di **non-regressione** di `append-log` in `tests/unit/test_wiki_tools_log_rotation.py`: corpo curato non riformattato, idempotenza sull'intestazione, rotazione per data — invariati
- [ ] T029 [US3] Implementare la derivazione e la scrittura del blocco in `src/sertor_core/wiki_tools/registry.py` (`append_log`), calcolando la copertura **prima** dell'append; popolare `AppendLogResult.covered`
- [ ] T030 [P] [US3] Test end-to-end del ciclo in `tests/unit/test_wiki_tools_scan_git.py`: registra → lavora ancora → `pending` nomina **solo** il lavoro successivo (è lo scenario G, ora dal vivo e non da fixture)

**Checkpoint US3**: il ciclo completo funziona come nel [quickstart](./quickstart.md).

---

## Phase 6: Polish & superfici host-facing

> Le regole di completamento del progetto vivono qui: una feature **non è done** finché un ospite può
> ottenerla (regola 1) e finché la documentazione utente riflette il cambiamento (regola 3).

- [ ] T031 [P] Aggiornare il **formato della voce** nel playbook distribuito `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md`: il blocco `sertor-covers/1` è parte del contratto della voce, e il playbook è la fonte unica che gli ospiti ricevono
- [ ] T032 [P] Aggiornare la **documentazione utente** in `docs/` per ciò che il changeset rende falso o incompleto, verificando prima **cosa** effettivamente afferma (regola 3, da eseguire come verifica e non come atto di fede)
- [ ] T033 Verificare il **budget righe** dei blocchi `claude-md-block` se toccati, e dichiarare l'eventuale aumento nel registro invece di aggirarlo
- [ ] T034 Eseguire il **gate reale**: `uv run ruff check .` + le **sei** suite (root · `packages/sertor` · `sertor-install-kit` · `sertor-flow` · `speclift` · `specaudit`) — non la sola suite che il comando documentato raccoglie (debito noto: E15-FEAT-012)
- [ ] T035 **Prova LIVE attraverso il runtime installato** seguendo [quickstart.md](./quickstart.md): re-lock del runtime, poi registra → lavora ancora → `scan` nomina il lavoro successivo. La prova che conta è quella che passa dal vehicle, non dai test
- [ ] T036 Verificare il comportamento su un progetto **senza sistema di versionamento**: ripiego dichiarato con causa tipizzata, nessuna regressione host-agnostica (SC-009)
- [ ] T037 Chiudere il **rituale di step**: record + distill + lint semantico, e marcare `E10-FEAT-062` ✅ in `requirements/debito-tecnico/epic.md` + EXEC

---

## Dependencies

```
Phase 1 (Setup)
   └─► Phase 2 (Foundational: coverage.py · identità di contenuto · campi additivi · guardia schema)
          ├─► Phase 3 (US1) ──┐
          ├─► Phase 4 (US2)   ├─► Phase 6 (Polish + host-facing)
          └─► Phase 5 (US3) ──┘
```

**US2 è genuinamente indipendente** da US1 e US3: tocca la propagazione dei fallimenti, non la
copertura. Può essere consegnata da sola.

⚠️ **US1 e US3 sono indipendenti come *test*, non come *valore*.** US1 è verificabile con giornali-fixture
che contengono blocchi scritti a mano, ma in produzione i blocchi li scrive US3: **il valore reale
arriva quando entrambe sono fatte**. È detto qui invece di essere mascherato da una falsa indipendenza —
lo **MVP** è quindi **US1 + US3**, non US1 da sola.

## Parallel opportunities

- **Fase 2**: T003/T004 (formato) e T006 (identità di contenuto) toccano file diversi → in parallelo.
- **Fase 3**: T010–T013 sono quattro test su file diversi/aree diverse → in parallelo, prima di T014.
- **Fase 4**: T018/T019 (core) e T022 (hook) → in parallelo.
- **Fase 5**: T026–T028 e T030 → in parallelo, prima di T029.
- **Fase 6**: T031 (playbook) e T032 (docs) → in parallelo.

## Implementation strategy

1. **Fase 2 per intera** — senza il formato e l'identità di contenuto nessuna storia si regge.
2. **US1 + US3 insieme** = MVP: è il ciclo che chiude il difetto segnalato.
3. **US2** subito dopo, o in parallelo se conviene: è separabile davvero.
4. **Fase 6 non è rifinitura**: contiene le due regole per cui una feature conta come consegnata. Un
   changeset che si ferma alla Fase 5 è codice che funziona **da noi**, e questa giornata ha mostrato
   cosa costa.

## Format validation

Tutti i **37** task hanno: checkbox · ID sequenziale · marcatore `[P]` dove parallelizzabili · etichetta
`[USn]` nelle sole fasi di storia · percorso file esplicito.

| Fase | Task | Storia |
|---|---|---|
| 1 Setup | T001–T002 | — |
| 2 Foundational | T003–T009 | — |
| 3 | T010–T017 | **US1** (8) |
| 4 | T018–T025 | **US2** (8) |
| 5 | T026–T030 | **US3** (5) |
| 6 Polish | T031–T037 | — |
