# Tasks — il perimetro dello step è anche ciò che non hai ancora consegnato (E10-FEAT-060)

**Branch**: `126-ritual-check-perimetro` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Ordine per dipendenza. `[P]` = parallelizzabile con la task precedente.

## Fase 1 — Derivazione condivisa (fondamenta)

- [x] **T001** — `src/sertor_core/wiki_tools/vcs.py`: aggiungere `split_z(out) -> list[str]` (helper per
  l'output `-z` di git) e `worktree_changes(cwd) -> tuple[list[str], list[str]] | None` che ritorna
  `(changed, untracked)` in percorsi relativi alla radice del repo.
  Semantica **identica** a `scan._worktree_changes`: `diff --name-only -z HEAD` per i tracciati
  (confronto sul contenuto → le sole terminazioni di riga non entrano, FR-005), `status --porcelain -z
  -uall` per i non tracciati (`-uall` perché altrimenti git collassa una cartella nuova in un'unica
  voce), rinomine contate una sola volta sulla destinazione. Ritorna `None` — **mai `[]`** — quando git
  non ha saputo rispondere.
  ⛔ **Non toccare `scan.py`.**

- [x] **T002** — `tests/unit/test_vcs_worktree.py` (nuovo): test dell'helper su host effimeri —
  tracciato modificato · non tracciato · cartella nuova con più file (devono comparire i file, non la
  cartella) · rinomina · file ignorato (assente) · differenza di sole terminazioni di riga (assente) ·
  git indisponibile → `None`.

## Fase 2 — Contratto (l'entità che oggi manca)

- [x] **T003** — `src/sertor_core/wiki_tools/contracts.py`: aggiungere il campo `perimeter` a
  `RitualCheckResult` (`{"kind": "derived"|"explicit", "sources": [{"name", "ref", "paths"}]}`) e la
  funzione che **DERIVA** `scope` da `perimeter`.
  ⚠️ `scope` **non** va più assegnata a mano da `ritual_check`: fonte unica (Principio XIV). Verificare
  che per il perimetro solo-committato e per quello esplicito la stringa risultante sia **identica a
  oggi** (retrocompatibilità).

- [x] **T004 [P]** — la derivazione di `scope` produce le tre forme attese; `perimeter` è
  serializzato; `schema` resta `wiki.ritual_check/1`; un consumatore che legge solo i campi odierni
  continua a funzionare (additività).
  ⚠️ **Scarto dal piano, dichiarato:** i test vivono in `tests/unit/test_ritual_check_perimetro.py`
  (sezione *contratto derivato*) invece che in un file proprio — consolidati lì perché condividono la
  stessa fixture. Il piano nominava `test_contracts_ritual_check.py`, che **non esiste**.

## Fase 3 — Perimetro unito + fail-loud (il cuore)

- [x] **T005** — `ritual_check.py`: comporre il perimetro come **unione** committato ∪ albero di lavoro
  usando `vcs.worktree_changes`; costruire `Perimeter` con i conteggi **per sorgente**; passare a
  `scope` derivata (FR-001/002/008).

- [x] **T006** — `ritual_check.py`: le pagine **aggiunte** comprendono anche quelle **non tracciate**
  (FR-003), incluse quelle in cartella-casa della distillazione (FR-004).
  *Perché conta:* senza questo, creare la pagina di distillazione senza averla consegnata fa suggerire
  allo strumento di distillare ciò che è appena stato distillato.

- [x] **T007** — `ritual_check.py`: **fail-loud** su ogni interrogazione del perimetro. In particolare
  sostituire il ramo `if rc == 0:` delle pagine aggiunte (oggi `ritual_check.py:259`) con un
  `ConfigError` esplicito (FR-013/014). `worktree_changes() is None` → errore, non insieme vuoto.

- [x] **T008** — `ritual_check.py`: con `--pages` il perimetro resta **esclusivamente** quello fornito,
  dichiarato `kind: "explicit"` (FR-007/011). Nessuna unione.

- [x] **T009** — `ritual_check.py`: estendere l'evento di osservabilità già emesso con i conteggi **per
  sorgente**, così la divergenza è visibile in telemetria e non solo a schermo (Principio IX).

## Fase 4 — Superficie umana

- [x] **T010** — `__main__.py`: il summary umano dichiara il perimetro (`perimetro: committed=N ·
  worktree=M`), **sempre**, anche a zero candidati (FR-009/010).
  *È la resa che una persona e un agente leggono davvero: dichiararlo solo nel JSON non chiuderebbe il
  difetto.*

## Fase 5 — Verifica che può fallire

- [x] **T011** — `tests/unit/test_ritual_check_perimetro.py` (nuovo): **matrice comportamentale
  versionata**, portata dallo scratchpad ai test. Include il giornale committato nella fixture —
  **senza, `scan` ripiega su mtime e i numeri sono falsi** (buco già pagato una volta).
  - **SC-001**: stesso contenuto consegnato vs non consegnato → **stesso elenco di candidati**.
  - **SC-002**: scenario misto → **zero** segnalazioni false sulla parte non consegnata (oggi 1).

- [x] **T012 [P]** — dichiarazione sempre presente (incluso zero candidati) · perimetro esplicito
  dichiarato come tale · pagina nuova non tracciata riconosciuta come aggiunta · file ignorato fuori
  perimetro.
  ⚠️ **Due scarti dal piano, dichiarati:** (a) i test stanno in `test_ritual_check_perimetro.py`, non
  in `test_ritual_check.py`, che resta invariato (13 test, tutti ancora verdi — è la prova di
  non-regressione); (b) le **terminazioni di riga** sono verificate al livello dell'helper
  (`test_vcs_worktree.py::test_sole_terminazioni_di_riga_non_entrano`), non a livello di
  `ritual-check`: è lì che la proprietà è decisa, ma va detto che l'asserzione non è sul percorso
  end-to-end.

- [x] **T013 [P]** — test **fail-loud** (SC-004): parametrizzato sulle **quattro** interrogazioni del
  perimetro (`diff-committed` · `diff-added` · `diff-worktree` · `status`), nessuna esclusa, più il
  caso di perimetro indeterminabile.
  ✅ **Anti-vacuità applicata:** ogni caso asserisce `chiamato["hit"]`, cioè di aver **raggiunto** il
  ramo d'errore — senza, un `ConfigError` sollevato da tutt'altra causa lo farebbe passare gratis.

- [x] **T014** — `tests/unit/test_perimetro_equivalenza.py` (nuovo): **test di equivalenza** fra la
  derivazione di `scan` e quella di `ritual_check` sullo **stesso** albero effimero. Diventa rosso se
  una delle due viene toccata da sola. È la mitigazione R-3 resa eseguibile, e il presidio finché
  E10-FEAT-066 non unifica.

## Fase 6 — Documentazione e chiusura

- [x] **T015** — Allineare la superficie host-facing che descrive il perimetro come «git diff»:
  `.claude/skills/wiki-author/wiki-playbook.md` **e** la copia bundlata in
  `packages/sertor/src/sertor_installer/assets/`. Poi `uv run python -m sertor_installer.sync` e la
  suite **root** `tests/unit/test_assets_sync.py` (le suite di `packages/sertor` **non** la coprono).

- [x] **T016** — Aggiornare `wiki/concepts/ritual-check.md`: il «⚠️ Limite noto» diventa il
  comportamento corretto; aggiornare la voce corrispondente in `wiki/index.md` e il caveat in
  `wiki/concepts/step-ritual.md`. *(Delegabile al `wiki-curator` per la parte di trascrizione.)*

- [x] **T017** — **Prova sul campo**: eseguire `ritual-check` su questo repo durante uno step reale con
  lavoro non consegnato e verificare un elenco **non vuoto** dove oggi risponde zero (**SC-005**).

- [x] **T018** — Gate pre-merge **completo**: `ruff check .` + le **sei** suite (root · `packages/sertor`
  con `-m hooks_smoke` · install-kit · flow · speclift · specaudit). Il comando del `CLAUDE.md` da solo
  ne raccoglie circa metà.

- [x] **T019** — Chiusura: E10-FEAT-060 marcata nell'EXEC e in `epic.md`, voce di giornale scritta
  (delegata al `wiki-curator`), **distill** eseguito → nuova pagina
  [[il-rimedio-ricade-nel-difetto]], **lint semantico** eseguito con due correzioni reali trovate
  *dallo strumento appena riparato* (`daily-distill-floor.md` · `fail-loud-fix-cause.md`).

## Tracciamento requisiti → task

| Requisito | Task |
|---|---|
| FR-001/002 perimetro unito | T001, T005 |
| FR-003/004 pagine aggiunte non tracciate | T006, T012 |
| FR-005 terminazioni di riga | T001, T002, T012 |
| FR-006 percorsi ignorati | T001, T002, T012 |
| FR-007/011 perimetro esplicito | T008, T012 |
| FR-008/009/010 dichiarazione | T003, T005, T010, T012 |
| FR-012 additività del contratto | T003, T004 |
| FR-013/014/015 fail-loud | T007, T013 |
| FR-016..019 invarianti | T003 (ordinamento), T013, T018 |
| SC-001 / SC-002 | T011 |
| SC-003 | T010, T012 |
| SC-004 | T013 |
| SC-005 | T017 |
| SC-006 (≤2 interrogazioni) | T001, T018 |
| R-3 anti-divergenza | T014 |
