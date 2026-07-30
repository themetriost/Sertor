# Implementation Plan: il perimetro dello step è anche ciò che non hai ancora consegnato

**Branch**: `126-ritual-check-perimetro` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: [spec.md](./spec.md) · requisiti EARS
[`requirements/debito-tecnico/feat-060-perimetro-ritual-check/requirements.md`](../../requirements/debito-tecnico/feat-060-perimetro-ritual-check/requirements.md)

## Summary

`ritual_check` deriva il perimetro dello step da `git diff <base>...HEAD` — **solo il committato** —
mentre `scan` (che regge l'hook bloccante `wiki-guard`) somma committato **e** albero di lavoro. Poiché
il rituale prescrive di registrare *nello stesso momento del commit*, `ritual-check` è invocato quando
il suo perimetro è ancora vuoto e risponde «0 candidati» mentre il gate blocca.

**Approccio:** (1) il perimetro diventa l'**unione** committato ∪ albero di lavoro; (2) il risultato
**dichiara** le sorgenti e i loro conteggi, sempre; (3) ogni interrogazione git necessaria al perimetro
**fallisce forte** invece di degradare verso l'insieme vuoto.

**Scelta strutturale: una sola derivazione.** La derivazione dell'albero di lavoro vive in **`vcs.py`**,
il modulo di primitive VCS che *entrambi* già importano, ed **entrambi la consumano**: la copia privata
`scan._worktree_changes` è stata rimossa, insieme al gemello `_split_z`. La divergenza non è «corretta
una volta» ma **impossibile per costruzione**.

*Come ci si è arrivati, perché è la parte istruttiva.* La prima stesura si fermava un passo prima —
helper condiviso consumato dal solo `ritual_check`, copia di `scan` intatta «perché regge un gate
bloccante» — con un **test di equivalenza** a sorvegliare le due. Una domanda dell'utente (*«ma quindi
cosa abbiamo fatto?»*) ha reso evidente il conto: si passava da **una** implementazione a **due**. E il
rischio invocato per rinviare si era già estinto grazie al lavoro stesso — l'helper esisteva, era
testato, e l'equivalenza era dimostrata. Il test di equivalenza **esisteva solo perché avevamo
declinato una modifica da due righe**: non una mitigazione, un promemoria. Rimosso perché diventato
vacuo (confrontava una funzione con sé stessa), sostituito da una guardia strutturale che verifica che
la derivazione resti **una**.

## Technical Context

**Language/Version**: Python 3.11+ (stdlib only per questo modulo)

**Primary Dependencies**: nessuna nuova. `subprocess` verso `git`, già incapsulato in
`sertor_core/wiki_tools/vcs.py`

**Storage**: N/A — la capacità è di sola lettura, non persiste nulla

**Testing**: pytest; host git **effimeri** (`tmp_path` + `git init`), zero rete

**Target Platform**: Windows · macOS · Linux (la capacità viaggia con `sertor-core` su ogni ospite)

**Project Type**: libreria + vehicle CLI (`sertor-wiki-tools ritual-check`)

**Performance Goals**: al più **due** interrogazioni git aggiuntive per esecuzione — le stesse che
`scan` già paga (NFR-001/SC-006)

**Constraints**: sola lettura · zero LLM · offline · host-agnostico · contratto esteso in modo
**additivo** (`wiki.ritual_check/1` invariato)

**Scale/Scope**: due moduli consumatori (`ritual_check.py`, `scan.py`), la derivazione condivisa in
`vcs.py`, un campo di contratto, una riga di summary. In `scan.py` il changeset **toglie** 56 righe.

## Constitution Check

*GATE: prima della Phase 0 e dopo il design.* Costituzione **v1.6.0**.

- [x] **I — Dipendenze verso l'interno:** **PASS** — `ritual_check` e `vcs` vivono in
  `sertor_core.wiki_tools`; **nessun SDK di provider**, solo stdlib. Il core resta importabile e
  testabile senza cloud né CLI.
- [x] **II — Boundary & local-first:** **PASS** — l'unica dipendenza esterna è `git`, già dietro
  l'astrazione `vcs.run_git`. Nessun vector store, nessuna scelta locale↔cloud coinvolta.
- [x] **III — YAGNI & unità piccole:** **PASS** — **nessuna** opzione `--committed-only` (nessuno l'ha
  chiesta). L'unificazione con `scan` è **inclusa**, non rinviata: **rimuove** codice (56 righe) invece
  di aggiungerne, e toglie il test che esisteva solo per sorvegliare la duplicazione.
- [x] **IV — Errori espliciti (NON-NEGOZIABILE):** **PASS** — è il cuore della feature: ogni
  interrogazione git necessaria al perimetro solleva `ConfigError`; sparisce il ramo `if rc == 0:` che
  produceva un insieme vuoto silenzioso.
- [x] **V — Testabilità & misure:** **PASS** — test F.I.R.S.T. su host git effimeri, offline. La
  matrice comportamentale diventa un **test versionato**, non uno script di scratchpad: SC-001 è
  falsificabile (righe «consegnato» e «non consegnato» devono coincidere).
- [x] **VI — Idempotenza & non-distruttività:** **PASS** — capacità di sola lettura; ordinamento
  esplicito dei percorsi → due esecuzioni sullo stesso albero danno lo stesso output (FR-019).
- [x] **VII — Leggibilità:** **PASS** — naming di dominio (`perimeter`, `source`, `committed`,
  `worktree`); i commenti spiegano *perché* il perimetro ha due sorgenti, non *cosa* fa il codice.
- [x] **VIII — Configurabilità centralizzata:** **PASS** — tassonomia, soglie e cartelle-casa
  continuano a venire da `wiki.config.toml`. Nessun default nuovo hardcodato.
- [x] **IX — Osservabilità:** **PASS** — l'evento `ritual_check` già emesso viene esteso con i
  conteggi **per sorgente**, così la divergenza è visibile anche in telemetria e non solo a schermo.
  Nessun segreto (solo percorsi relativi).
- [x] **X — Host-agnostico (NON-NEGOZIABILE):** **PASS** — nessun percorso fisso; il ramo di default
  resta **rilevato a runtime** (E10-FEAT-033). La nuova derivazione usa gli stessi comandi git su ogni
  OS. Il dogfooding non introduce deroghe.
- [x] **XI — Consumo via vehicles:** **PASS** — il consumo resta via CLI `sertor-wiki-tools
  ritual-check`; l'import diretto avviene **solo nei test**, che è l'eccezione dichiarata.
- [x] **XII — Fail Loud, Fix the Cause:** **PASS** — nessuna capacità viene spenta per schivare un
  errore; al contrario, si **rimuove** una degradazione silenziosa preesistente. L'unica tolleranza
  residua è dichiarata e circoscritta (vedi *Complexity Tracking*).
- [x] **XIII — Product Plane vs. Fixture Plane:** **PASS** — cerimonia **bassa** per costruzione: la
  capacità è **stateless e di sola lettura**, non scrive nulla nell'asset, quindi il caso
  «workaround-fixture che tappa un buco-prodotto» non si presenta. Il difetto è stato riprodotto sul
  **piano-prodotto** (host effimeri *e* questo repo durante uno step reale), non dedotto da una
  fixture. Nota di disciplina già pagata in questa feature: la prima fixture della matrice dava numeri
  falsi (mancava un giornale committato) ed è stata **riparata**, non assecondata.
- [x] **XIV — Derived State, Not Declared:** **PASS — e il gate ha cambiato il design.** La prima
  stesura prevedeva di *aggiungere* la struttura `perimeter` **accanto** alla stringa `scope`
  esistente: due descrizioni dello stesso fatto, libere di divergere — cioè la malattia che questa
  feature cura, reintrodotta nel suo stesso rimedio. Corretto: **`scope` viene DERIVATA da
  `perimeter`** da un'unica funzione, non mantenuta in parallelo. Nessun riconciliatore serve, perché
  non c'è nulla da riconciliare.
- [x] **Allineamento alla missione:** **PASS** — la wiki è **metà del corpus** che l'agente interroga
  (fusione code+doc). Uno strumento che tace sul lavoro non registrato lascia entrare nel corpus
  documentazione mancante o stantia: qui si difende la **freschezza** di ciò che viene reso all'agente,
  che è il fronte di valore dichiarato dalla stella polare.

**Esito: 14 PASS + missione PASS.** Nessun FAIL da giustificare; la tolleranza residua di `_links_at`
è registrata sotto come limite dichiarato, non come deroga.

## Project Structure

### Documentation (this feature)

```text
specs/126-ritual-check-perimetro/
├── spec.md                     # ✅ fase specify
├── plan.md                     # questo file
├── research.md                 # decisioni di design + alternative scartate
├── data-model.md               # entità Perimeter / PerimeterSource, contratto esteso
├── contracts/
│   └── ritual-check.md         # contratto CLI + JSON aggiornato
├── checklists/
│   └── requirements.md         # ✅ fase specify
└── tasks.md                    # fase tasks (non creato qui)
```

### Source Code (repository root)

```text
src/sertor_core/wiki_tools/
├── vcs.py              # + worktree_changes() e split_z(): derivazione condivisa, UNA sola
├── ritual_check.py     # perimetro unito + dichiarazione + fail-loud
├── contracts.py        # RitualCheckResult: + perimeter (scope DERIVATA da esso)
├── __main__.py         # summary umano: dichiara il perimetro
└── scan.py             # consuma l'helper condiviso; rimosse le copie private (−56 righe)

tests/unit/
├── test_vcs_worktree.py                # l'helper condiviso
├── test_ritual_check_perimetro.py      # matrice comportamentale versionata (SC-001/002)
└── test_perimetro_derivazione_unica.py # guardia: la derivazione resta UNA
```

**Structure Decision**: modifica **in place** di moduli esistenti, con la derivazione promossa nel
modulo VCS già condiviso e consumata da entrambe le capacità. Nessun pacchetto nuovo, nessuna porta
nuova, nessun adapter: la capacità è deterministica e vive interamente in `wiki_tools`. Nel modulo
`scan` il changeset **rimuove** più codice di quanto ne aggiunga.

## Complexity Tracking

Nessuna violazione costituzionale da giustificare. Si registra **un limite dichiarato**, perché tacerlo
sarebbe la stessa classe di difetto che la feature chiude:

| Limite | Perché resta | Alternativa scartata perché |
|--------|--------------|------------------------------|
| `_links_at` (`git show <base>:<path>`) continua a restituire l'insieme vuoto su rc≠0 | Per una pagina **mai consegnata** il fallimento è la risposta *corretta* (non esiste una versione precedente): tutti i suoi collegamenti sono nuovi. `git show` però usa lo stesso codice d'uscita per «percorso assente» e «repository rotto», quindi i due casi non sono distinguibili lì. | Trattare rc≠0 come errore renderebbe **impossibile** il caso legittimo — pagina nuova — che è proprio quello che la feature deve far funzionare. Mitigazione reale: le interrogazioni del **perimetro** falliscono forte *prima*, quindi se git è rotto lo si scopre lì, non qui. Dichiarato nella spec (*Assumptions*) e nel contratto, non lasciato implicito. |
