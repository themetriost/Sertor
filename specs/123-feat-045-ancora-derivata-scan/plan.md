# Implementation Plan: Ancora derivata per la rilevazione del lavoro non registrato

**Branch**: `123-feat-045-ancora-derivata-scan` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/123-feat-045-ancora-derivata-scan/spec.md`

## Summary

`scan` risponde a «c'è lavoro non registrato nel wiki?» **stimando** con gli orologi dei file invece di
**derivare** il fatto. Dopo un merge git riscrive lavoro e giornale insieme, l'ordine diventa arbitrario
e il gate bloccante `wiki-guard` può diventare **insoddisfacibile**. La feature sostituisce la stima con
il fatto **dove è derivabile** (l'ultima consegna che ha toccato la cartella di giornale + il diff da
lì, unito alle modifiche non consegnate dell'albero di lavoro) e **dichiara la stima come tale** dove
non lo è, perché `scan` è host-agnostico per progetto. È il Principio XIV applicato a un meccanismo
nostro. Assorbe E10-FEAT-048: l'esclusione dei file ignorati dal VCS e i nomi dei file **cadono fuori
gratis** dalla derivazione (verificato empiricamente, vedi `research.md` R3).

**Approccio tecnico:** estrarre in un modulo condiviso gli helper git che `ritual_check.py` **ha già**
(stesso pacchetto) e farli usare a entrambi; aggiungere a `ScanResult` campi **additivi** mantenendo
**invariata** la stringa di schema `wiki.scan/1` — vincolo critico, perché i due hook consumatori si
disattivano su mismatch (fail-open) e un bump farebbe **sparire** il gate invece di romperlo.

## Technical Context

**Language/Version**: Python ≥ 3.11 (`sertor-core`); il runtime `.sertor/` gira su ≥ 3.12

**Primary Dependencies**: **nessuna nuova**. Solo stdlib (`subprocess`, `pathlib`, `datetime`,
`fnmatch`) + il binario `git` invocato per subprocess, com'è già in `ritual_check.py`

**Storage**: N/A — operazione di sola lettura, nessuno stato persistito

**Testing**: `pytest`. Unit test con repo git temporanei (il pattern `_git_repo` esiste già in
`tests/unit/test_ritual_check.py`) + i test `scan` esistenti che devono passare **senza modifiche**

**Target Platform**: Windows · macOS · Linux; ospiti **con e senza** controllo di versione

**Project Type**: libreria (`sertor-core`) consumata via vehicle CLI, + asset hook distribuiti

**Performance Goals**: `scan` gira a **ogni** `Stop`, quindi la latenza è percepita. La derivazione fa
2–3 chiamate a `git` al posto di un `rglob` completo di `source_dirs`: su repo grandi è **più veloce**,
non più lenta. Obiettivo: non peggiorare il caso odierno

**Constraints**: offline · zero LLM · zero nuove dipendenze · **stringa di schema congelata** ·
comportamento non-git invariato · determinismo (SC-002: stesso stato ⇒ stessa risposta, comunque siano
gli orologi)

**Scale/Scope**: 3 file di libreria toccati, 1 nuovo; 2 asset hook × 2 assistenti; doc utente

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Costituzione v1.6.0 (14 principi + gate di missione). **Esito: 14/14 + missione — PASS.**

- [x] **I — Dipendenze verso l'interno (NON-NEGOZIABILE): PASS.** `wiki_tools` è già interno a
  `sertor_core` e non importa SDK di provider. La feature non introduce dipendenze verso l'esterno del
  core; `git` è invocato per subprocess, non importato, e il modulo nuovo (`vcs.py`) è stdlib puro.
- [x] **II — Boundary & local-first: PASS.** Nessun provider né backend coinvolto. Il VCS non è un
  provider intercambiabile ma un **fatto dell'ambiente ospite**, rilevato a runtime: la sua assenza è
  un percorso previsto (R8), non una configurazione da scegliere.
- [x] **III — YAGNI & unità piccole: PASS.** La feature **rimuove** duplicazione invece di aggiungere
  astrazione: gli helper git esistono già in `ritual_check.py` e vengono **estratti**, non reinventati.
  Nessun layer nuovo, nessuna manopola oltre al limite di elenco (che segue il pattern già in uso di
  `[ritual].hub_threshold`).
- [x] **IV — Errori espliciti (NON-NEGOZIABILE): PASS.** La ricaduta sul proxy non è un `None`
  silenzioso: è **tipizzata** con tre cause distinte (`not_a_repository` · `git_unavailable` ·
  `log_never_committed`, R8). Un vuoto non tipizzato farebbe fabbricare a chi legge un'affermazione
  falsa — stessa ragione dell'assenza tipizzata in `specs/118`.
- [x] **V — Testabilità & misure: PASS.** Il criterio centrale (SC-002, determinismo) è **verificabile
  meccanicamente**: si alterano gli orologi e si riesegue. I test girano offline su repo temporanei.
  *N/A la parte «qualità retrieval»: la feature non tocca il motore.*
- [x] **VI — Idempotenza & determinismo: PASS, ed è il punto della feature.** `scan` è di sola lettura
  e oggi **non è deterministico** (dipende dall'ordine di scrittura del filesystem dopo un merge). Dopo
  il fix lo diventa: SC-002 è un criterio di accettazione, non un effetto collaterale.
- [x] **VII — Leggibilità: PASS.** Naming di dominio dalla spec — *ancora*, *registrazione*, *insieme
  in sospeso* — non termini di implementazione (`mtime`, `sha`).
- [x] **VIII — Configurabilità centralizzata: PASS.** Nessun default hardcoded nel corpo: il limite
  dell'elenco è una manopola opzionale del profilo con default nel profilo stesso, come già
  `[ritual].hub_threshold`. Le cartelle sorgente e le esclusioni restano quelle di `wiki.config.toml`.
- [x] **IX — Osservabilità: PASS.** `scan` emette già `log_event`; l'evento si estende con la **natura
  dell'ancora** e la causa dell'eventuale ricaduta — cioè si rende osservabile proprio la cosa che oggi
  è invisibile. Nessun segreto nei log (path di progetto, non contenuti).
- [x] **X — Host-agnostico (NON-NEGOZIABILE): PASS, ed è il vincolo che ha determinato il design.**
  `scan.py:4` dichiara «works on non-git hosts too»: passare al solo git romperebbe gli ospiti non-repo.
  Da qui la forma a **due modalità con dichiarazione**, invece della sostituzione. Il comportamento
  non-git resta invariato (FR-014) e i test esistenti devono passare **senza modifiche** — se servisse
  toccarli, sarebbe il segnale di una regressione.
- [x] **XI — Consumo via vehicles: PASS.** I due hook consumano `scan` per **subprocess sulla CLI**
  (`sertor-wiki-tools scan --json`), non importando `sertor_core`. La feature non cambia questo confine;
  i campi nuovi viaggiano nel contratto JSON del vehicle.
- [x] **XII — Fail Loud, Fix the Cause: PASS.** Nessuna capacità disattivata per schivare un errore. La
  degradazione al proxy è **ammessa perché segnalata** (il principio la consente esplicitamente a questa
  condizione). Interrompere invece sarebbe sbagliato: `not_a_repository` è il **funzionamento previsto**
  su un ospite non-git, non un guasto — e il consumatore è un gate che per progetto non deve mai
  intrappolare un turno.
- [x] **XIII — Product Plane vs. Fixture Plane: PASS, con dichiarazione.** Il dogfood **è** un repo git:
  la modalità non-git — cioè il ramo che il Principio X protegge — **è irraggiungibile sul nostro nodo**.
  È il terzo limite di [[dogfood-fidelity]] («il dogfood è una configurazione, e la più favorevole»), la
  stessa posizione che ha lasciato passare il comando d'upgrade rotto per gli host pinnati. **Contromisura
  esplicita nel piano:** la modalità non-git si esercita con **fixture** (cartelle temporanee non-repo),
  non con l'osservazione sul dogfood, e la parte di piano che lo prevede è vincolante — non un
  «se avanza tempo».
- [x] **XIV — Derived State, Not Declared (NON-NEGOZIABILE): PASS — è il principio che governa la
  feature.** Il valore duplicato è l'**ancora**: un fatto (quale consegna ha registrato) tenuto come
  copia approssimata (un orologio). Si **deriva** dove derivabile. Dove non lo è, il riconciliatore è
  **nominato nel contratto stesso**: `anchor_kind` dichiara la natura del valore e
  `anchor_fallback_reason` il motivo — l'output **dice se ha derivato o se sta stimando**, invece di
  presentare i due casi con la stessa faccia. *Nota di coerenza:* il fix stesso avrebbe potuto ripetere
  il difetto (sostituire un proxy silenzioso con un altro), ed è la ragione per cui FR-009 esiste.
- [x] **Allineamento alla missione: PASS, con la tensione dichiarata.** Il differenziatore è la
  **fusione code+doc** in un unico corpus: il wiki **è** la metà doc, ed è indicizzato nello stesso
  corpus del codice. Un gate che non si può soddisfare non è un fastidio di processo — **insegna a
  smettere di registrare**, e ciò che non viene registrato non entra nel corpus: degrada direttamente
  la metà doc della fusione. *Tensione dichiarata onestamente:* è comunque lavoro di **governance**, non
  di retrieval, e l'audit del 2026-07-02 aveva segnalato una deriva «processo > prodotto». Giustificato
  qui perché è **Must/P0 su un difetto che blocca l'uso quotidiano**, riportato da un nodo esterno, non
  un affinamento di processo scelto da noi.

## Project Structure

### Documentation (this feature)

```text
specs/123-feat-045-ancora-derivata-scan/
├── plan.md              # questo file
├── spec.md              # requisiti (con Clarifications)
├── research.md          # Fase 0 — R1..R9, decisioni verificate sul repo reale
├── data-model.md        # Fase 1 — entità e contratto
├── contracts/
│   └── wiki.scan.v1.md  # Fase 1 — il contratto JSON, con il vincolo di compatibilità
├── quickstart.md        # Fase 1 — come si verifica dal vivo
└── checklists/
    └── requirements.md  # qualità della spec (16/16)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── vcs.py               # NUOVO — helper git condivisi (estratti da ritual_check)
├── scan.py              # MODIFICATO — ancora derivata + proxy dichiarato + path nominati
├── ritual_check.py      # MODIFICATO — consuma vcs.py (comportamento INVARIATO)
├── contracts.py         # MODIFICATO — ScanResult: campi additivi, schema invariato
└── profile.py           # MODIFICATO — manopola opzionale per il limite dell'elenco

packages/sertor/src/sertor_installer/assets/
├── claude/hooks/wiki-guard.py            # MODIFICATO — mostra i path nel motivo del blocco
├── claude/hooks/wiki-pending-check.py    # MODIFICATO — idem (non bloccante)
├── copilot/hooks/wiki-guard.py           # parità byte
└── copilot/hooks/wiki-pending-check.py   # parità byte

tests/unit/
├── test_wiki_tools_scan.py       # ESISTENTE — deve passare SENZA MODIFICHE (guardia di non-regressione)
├── test_wiki_tools_scan_git.py   # NUOVO — modalità derivata, su repo temporanei
└── test_wiki_tools_vcs.py        # NUOVO — helper estratti

packages/sertor/tests/
├── test_wiki_guard.py            # MODIFICATO — i path compaiono nel motivo
└── test_scan_schema_frozen.py    # NUOVO — guardia: la stringa di schema non si muove

docs/
├── troubleshooting.md            # MODIFICATO — «il gate blocca e non capisco perché»
└── reference.md                  # MODIFICATO — i campi nuovi del contratto
```

**Structure Decision**: struttura esistente, nessuna nuova area. Il solo modulo nuovo (`vcs.py`) nasce
da un'**estrazione** di codice già presente nello stesso pacchetto, non da una nuova responsabilità:
è la contromisura al fatto che oggi due strumenti gemelli, a due file di distanza, misurano realtà
diverse. Gli asset hook seguono la parità per-assistente già in vigore.

## Fasi di implementazione (ordine di dipendenza)

| # | Fase | Consegna | Perché in questo punto |
|---|---|---|---|
| 1 | **Estrazione** | `vcs.py` + `ritual_check.py` che lo consuma, comportamento invariato | Base condivisa. Si verifica da sola: i test di `ritual-check` devono passare **senza toccarli** |
| 2 | **Contratto** | `ScanResult` con i campi additivi + **guardia sulla stringa di schema** | La guardia va scritta **prima** del resto: è ciò che impedisce alla feature di spegnere il gate |
| 3 | **Ancora derivata** | `scan.py` modalità git (le due metà, R2) | Il cuore. Sblocca US1 |
| 4 | **Proxy dichiarato** | modalità mtime + `anchor_kind`/`anchor_fallback_reason` tipizzato | US3. Include le **fixture non-git** (vedi Principio XIII) |
| 5 | **Nominare** | `pending_paths` + messaggio compatibile coi template ospite | US2, assorbe FEAT-048 |
| 6 | **Consegna agli ospiti** | i 4 asset hook + parità + doc utente | Definition of Done: una feature non è completa finché un ospite non la ottiene e non la capisce |

## Complexity Tracking

> Nessuna violazione costituzionale da giustificare: il Constitution Check è 14/14 + missione PASS.

Un solo punto merita di essere registrato, perché è un **rischio**, non una violazione:

| Rischio | Perché esiste | Contromisura nel piano |
|---|---|---|
| La modalità **non-git** non è esercitabile sul dogfood (siamo un repo) | Terzo limite di [[dogfood-fidelity]]: occupiamo **una** configurazione, la più favorevole. È la posizione che ha già lasciato passare il comando d'upgrade rotto per gli host pinnati | Fase 4 vincolante: fixture non-repo nei test, **non** osservazione sul dogfood. La prova che il ramo funziona non può venire da noi |
