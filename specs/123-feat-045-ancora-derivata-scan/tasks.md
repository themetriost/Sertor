# Tasks: Ancora derivata per la rilevazione del lavoro non registrato

**Feature**: `123-feat-045-ancora-derivata-scan` (E10-FEAT-045, Must/P0) · **Data**: 2026-07-27
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) · [contracts/wiki.scan.v1.md](./contracts/wiki.scan.v1.md) · [quickstart.md](./quickstart.md)

**Test richiesti: SÌ.** Non è TDD per gusto: il criterio centrale (SC-002, determinismo) è
**meccanicamente verificabile** e oggi fallisce, e la guardia sullo schema è ciò che impedisce alla
feature di **spegnere il gate** sugli ospiti. Qui i test sono il deliverable, non il contorno.

---

## Ordine e blocchi

```
Fase 1  Estrazione (vcs.py)              ─┐
Fase 2  Contratto + GUARDIA schema       ─┼─→ bloccano tutto il resto
Fase 3  US1 ancora derivata (P1)          │   ← MVP: da sola chiude il deadlock
Fase 4  US3 proxy dichiarato (P3)         │   ← fixture non-git (Principio XIII)
Fase 5  US2 nominare + ignorare (P2)      │   ← assorbe E10-FEAT-048
Fase 6  Consegna ospiti + doc utente     ─┘   ← Definition of Done, NON opzionale
```

> **Perché la guardia sullo schema è in fase 2 e non alla fine.** Se lo schema si muovesse, il gate non
> si romperebbe: **sparirebbe** sugli ospiti non aggiornati (fail-open), e l'assenza somiglia al
> successo. Una guardia scritta dopo l'implementazione certifica ciò che è stato fatto; scritta prima,
> **vincola** ciò che si può fare.

> **US3 prima di US2** rispetto alla priorità della spec: la modalità proxy tocca lo stesso punto di
> decisione dell'ancora derivata (fase 3), quindi chiuderla subito evita di riaprire `scan.py` due
> volte. US2 lavora a valle, sull'insieme già calcolato.

---

## Fase 1 — Estrazione degli helper git (base condivisa)

**Obiettivo:** una sola implementazione della macchina git nel pacchetto. **Si verifica da sola:** i
test di `ritual-check` devono passare **senza essere toccati**.

- [ ] T001 Creare `src/sertor_core/wiki_tools/vcs.py` con gli helper estratti da `ritual_check.py`: `run_git(args, cwd) -> (rc, stdout)` (non solleva mai, il chiamante decide), `is_repository(cwd) -> bool` (via `git rev-parse --is-inside-work-tree`), `repo_prefix(cwd) -> str` (via `git rev-parse --show-prefix`, mappa i path di git a quelli del progetto). Docstring che dichiara: stdlib-only, nessuna eccezione propagata, host-agnostico.
- [ ] T002 Modificare `src/sertor_core/wiki_tools/ritual_check.py` per consumare `vcs.run_git` e `vcs.repo_prefix` al posto di `_git` e `_wiki_prefix`. **Comportamento invariato**: `_resolve_base`/`_default_base_candidates` restano in `ritual_check.py` (servono il diff verso il ramo di default, che `scan` non usa — R5).
- [ ] T003 [P] Creare `tests/unit/test_wiki_tools_vcs.py`: `run_git` su comando inesistente → `(rc≠0, "")` senza sollevare · `is_repository` vero in un repo temporaneo, falso in una cartella semplice · `repo_prefix` vuoto alla radice e valorizzato in una sottocartella.
- [ ] T004 Verificare che `tests/unit/test_ritual_check.py` passi **senza modifiche**. Se servisse toccarlo, l'estrazione ha cambiato comportamento: correggere l'estrazione, **non il test**.

---

## Fase 2 — Contratto e guardia (BLOCCANTE: prima dell'implementazione)

**Obiettivo:** rendere impossibile, per costruzione, che la feature spenga il gate sugli ospiti.

- [ ] T005 Estendere `ScanResult` in `src/sertor_core/wiki_tools/contracts.py` con i campi **additivi**: `anchor_kind`, `anchor_ref`, `anchor_fallback_reason`, `pending_paths`, `pending_truncated`, `stale_recording`. Default che riproducono il comportamento odierno. **`schema` resta `"wiki.scan/1"`.**
- [ ] T006 ⚠️ Creare `packages/sertor/tests/test_scan_schema_frozen.py`: la guardia legge **entrambe le fonti** — la costante emessa da `ScanResult` **e** la stringa confrontata nei 4 asset hook — e asserisce che coincidano. **Non ripetere la costante nel test**: sarebbe essa stessa un valore duplicato senza riconciliatore (Principio XIV). Il messaggio di fallimento deve spiegare *perché* (un bump non rompe il gate, lo fa sparire).
- [ ] T007 [P] Creare `tests/unit/test_wiki_tools_scan_contract.py` con gli invarianti C-1..C-8 di `contracts/wiki.scan.v1.md`. **File nuovo, non un'aggiunta a `test_wiki_tools_scan.py`**: quello resta intatto perché è la guardia di non-regressione (T037).
- [ ] T008 [P] Aggiungere al profilo (`src/sertor_core/wiki_tools/profile.py`) la manopola opzionale `[ritual].pending_paths_limit` con default 10, seguendo il pattern già in uso di `hub_threshold` (Principio VIII: nessun default hardcoded nel corpo).

---

## Fase 3 — US1: ancora derivata (P1) 🎯 **MVP**

**Obiettivo:** la sequenza «registro → consegno → allineo → chiudo» si completa, e si completa
**sempre**. **Test indipendente:** eseguire la sequenza reale su un repo di prova e ripeterla dopo aver
alterato tutti gli orologi — stessa risposta (SC-002).

- [ ] T009 [US1] Implementare in `src/sertor_core/wiki_tools/scan.py` la funzione `_derived_anchor(profile) -> Anchor | None`: ultima consegna che ha toccato `profile.log_dir_path` via `git log -1 --format=%H|%cI -- <log_dir>`; `None` se assente (→ `log_never_committed`).
- [ ] T010 [US1] Implementare `_pending_from_git(profile, anchor)`: unione delle due metà (R2) — `git diff --name-only <sha> HEAD` **e** `git status --porcelain` (modificati + non tracciati; per i rinomini prendere la **destinazione**; le cancellazioni contano e si nominano, non si leggono).
- [ ] T011 [US1] Mappare i path di git a quelli del progetto con `vcs.repo_prefix`, filtrare per `profile.source_dirs` e applicare `_is_excluded` con `profile.exclude` — le esclusioni dell'ospite valgono in **entrambe** le modalità (A-4, R9).
- [ ] T012 [US1] Implementare il riconoscimento della **registrazione non consegnata**: la partizione di oggi (`profile.log_partition_path(date.today())`) risulta modificata o non tracciata ⇒ vale come registrazione (FR-004). Usare il metodo del profilo, **non** comporre il nome a mano.
- [ ] T013 [US1] Cablare la scelta di modalità in `scan()`: repo ⇒ derivata, altrimenti proxy. Mantenere la firma e il resto del corpo invariati.
- [ ] T014 [P] [US1] Creare `tests/unit/test_wiki_tools_scan_git.py` — casi: lavoro+voce nella stessa consegna ⇒ `pending 0` · lavoro consegnato senza voce ⇒ `pending > 0` · modifiche non consegnate senza voce ⇒ `pending > 0` · voce di oggi non consegnata ⇒ `pending 0` **senza commit** · file cancellato ⇒ contato.
- [ ] T015 [US1] ⭐ Test di **determinismo** (SC-002): stesso stato, orologi alterati arbitrariamente su tutti i file coinvolti ⇒ risultato **identico**. *È il test che oggi fallisce e che definisce la feature.*
- [ ] T016 [P] [US1] Test di **anti-deadlock**: simulare merge+pull (riscrittura di lavoro e giornale con lo stesso mtime) ⇒ `pending 0`. Riproduce le sette occorrenze del nodo *Acta*.

---

## Fase 4 — US3: il proxy, dichiarato (P3)

**Obiettivo:** l'ospite non-git riceve il gate e **sa** che sta ricevendo una stima.
⚠️ **Su fixture, non su osservazione:** il dogfood è un repo, quindi questo ramo è **irraggiungibile
qui** (Principio XIII, terzo limite di `dogfood-fidelity`). Fase **vincolante**, non «se avanza tempo».

- [ ] T017 [US3] Implementare la tassonomia chiusa di `anchor_fallback_reason` (`not_a_repository` · `git_unavailable` · `log_never_committed`) e cablarla nei tre punti di ricaduta. Invariante C-3: `anchor_kind == "mtime"` ⟹ motivo **mai** nullo.
- [ ] T018 [US3] Popolare `anchor_kind`/`anchor_ref` in modalità derivata (invariante C-2: derivata ⟹ citabile) e mantenere `anchor` come **timestamp ISO in entrambe le modalità** (FR-013).
- [ ] T019 [P] [US3] Test su **fixture non-repo**: cartella temporanea che non è un repo ⇒ funziona come oggi, `anchor_kind: "mtime"`, motivo `not_a_repository`.
- [ ] T020 [P] [US3] Test su **fixture repo-senza-giornale-consegnato** ⇒ motivo `log_never_committed` (ospite nuovo / storia troncata).
- [ ] T021 [P] [US3] Test `git_unavailable`: comando git non risolvibile ⇒ ricaduta dichiarata, **nessuna eccezione propagata** (il consumatore è un gate che non deve intrappolare il turno).
- [ ] T022 [US3] Estendere l'evento `log_event` di `scan` con `anchor_kind` e la causa di ricaduta (Principio IX: rendere osservabile proprio ciò che oggi è invisibile). Nessun contenuto di file nei log, solo path.

---

## Fase 5 — US2: nominare i file, ignorare gli scarti (P2) — assorbe E10-FEAT-048

**Obiettivo:** chi riceve un blocco sa **quali** file, e uno scratch non blocca più.
**Test indipendente:** file in cartella ignorata ⇒ non contato; file reale ⇒ path nell'output.

- [ ] T023 [US2] Popolare `pending_paths` (ordinati, deduplicati) e `pending_truncated` rispettando il limite del profilo. Invariante C-5: `pending == len(pending_paths) + pending_truncated` — **il conteggio resta esatto**, è l'elenco a essere troncato.
- [ ] T024 [US2] Comporre il messaggio compatibile con i template dell'ospite (R7): segnaposto `{files}` presente ⇒ sostituire **lì**; assente ⇒ **accodare**. Un ospite che non sa nulla del cambiamento non deve fare niente (FR-008).
- [ ] T025 [US2] Implementare `stale_recording` (FR-004a): partizione **non consegnata e non di oggi** ⇒ nominarla con la sua data. Senza, il giornale sembra aggiornato mentre il gate blocca lo stesso.
- [ ] T026 [P] [US2] Test: file in cartella ignorata dal VCS ⇒ **non contato** (già verificato a mano in R3, qui diventa guardia permanente).
- [ ] T027 [P] [US2] Test: troncamento dichiarato · template ospite con `{files}` · template ospite **senza** `{files}` (non deve rompersi) · `stale_recording` popolato e `pending > 0` insieme.
- [ ] T028 [US2] Popolare `pending_paths` **anche in modalità proxy** (FR-006 non è condizionato alla modalità): i path si conoscono già dall'attraversamento; ciò che manca lì è solo il filtro «ignorato», ed è dichiarato da `anchor_kind`.

---

## Fase 6 — Consegna agli ospiti e documentazione (Definition of Done)

**Non opzionale.** Una feature non è completa finché un ospite non la **ottiene** attraverso
l'installazione e non la **capisce** dalla documentazione utente.

- [ ] T029 Modificare `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-guard.py`: il motivo del blocco **nomina i path** (da `pending_paths`) e, se presente, la `stale_recording` con la sua data. Restano invariati: `exit 0` sempre, anti-loop, fail-open.
- [ ] T030 [P] Modificare `…/assets/claude/hooks/wiki-pending-check.py` allo stesso modo (non bloccante).
- [ ] T031 [P] Propagare i due hook agli asset **Copilot** mantenendo la **parità byte** (`…/assets/copilot/hooks/`).
- [ ] T032 Eseguire `uv run python -m sertor_installer.sync` e verificare `tests/unit/test_assets_sync.py` (la suite **root**: quella di `packages/sertor` non copre il drift `.claude/`).
- [ ] T033 [P] Aggiornare `packages/sertor/tests/test_wiki_guard.py`: i path compaiono nel motivo; il caso `pending == 0` continua a non bloccare.
- [ ] T034 [P] Aggiornare `docs/troubleshooting.md` — voce «il gate blocca e non capisco perché»: come leggere i path nominati, cosa significa una `stale_recording`, e **perché su un ospite senza controllo di versione il comportamento è diverso** (limite dichiarato, A-6).
- [ ] T035 [P] Aggiornare `docs/reference.md` con i campi nuovi del contratto e la manopola `[ritual].pending_paths_limit`.
- [ ] T036 Aggiornare la riga E10-FEAT-045 in `requirements/debito-tecnico/epic.md` (✅ + rimando all'EXEC) e marcare **E10-FEAT-048 come assorbita** su host git, dichiarando il residuo non-git.

---

## Fase 7 — Verifica finale

- [ ] T037 ⚠️ Verificare che `tests/unit/test_wiki_tools_scan.py` passi **SENZA MODIFICHE**. È la guardia di non-regressione del Principio X: se servisse toccarlo, il comportamento è cambiato dove non doveva.
- [ ] T038 Eseguire il **quickstart dal vivo** (9 prove, `quickstart.md`) sul runtime installato — non solo i test unitari. Le prove 1, 2, 5 e 6 sono quelle che i test da soli non coprono.
- [ ] T039 Gate pre-merge: `uv run pytest -m "not cloud"` **completo** + `uv run ruff check .`. Non ci si fida di run mirati.
- [ ] T040 Rituale di step: record + distill (candidato in sospeso dalla spec: «una registrazione esiste in due medium» — si distilla **ora**, col codice a sostenerla, se il fix l'ha resa una forma riusabile) + lint semantico su [[wiki-guard]] e [[wiki-tools]], che **ora** vanno aggiornate (prima sarebbe stato documentare un comportamento inesistente).

---

## Dipendenze

| Fase | Dipende da | Parallelizzabile con |
|---|---|---|
| 1 Estrazione | — | — |
| 2 Contratto + guardia | 1 | — |
| 3 US1 (MVP) | 1, 2 | — |
| 4 US3 | 3 (stesso punto di decisione) | — |
| 5 US2 | 3 (opera sull'insieme calcolato) | 4 |
| 6 Consegna | 5 | — |
| 7 Verifica | tutte | — |

**Task parallelizzabili `[P]`:** 14 su 40 — quasi tutti test su file distinti.

## Strategia di consegna

**MVP = Fase 1+2+3.** Da solo chiude il deadlock, che è la ragione Must/P0 della feature: la sequenza
«registro → consegno → allineo → chiudo» si completa in modo **deterministico**. US3 e US2 sono
incrementi reali e separatamente verificabili, ma nessuno dei due sblocca chi oggi è bloccato.

**Consegna in una sola PR**, non a fette: la fase 6 è Definition of Done e una feature che vive solo
nel nostro `.claude/` è un prototipo, non una capacità.
