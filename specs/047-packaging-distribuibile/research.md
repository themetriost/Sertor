# Phase 0 — Research: Packaging distribuibile (distribuzione interim `git+url`)

**Feature**: `047-packaging-distribuibile` | **Date**: 2026-06-17

Risolve le **tre incognite di design** lasciate aperte dalla spec (sezione *Assumptions*) e i punti
tecnici necessari a impostare licenza/metadati/verifica. Ground-truth di build già verificata a monte
(spec §Assumptions, sessione 2026-06-16): i 4 pacchetti buildano (sdist+wheel), la wheel di `sertor`
include `assets/**`, ma **manca** il file `LICENSE`, i metadati user-facing (`urls`/`classifiers`/
`keywords`) e l'allineamento delle versioni. Le decisioni DA-P1..P4 (requirements §10) sono **chiuse**
e non vengono riaperte qui.

> Stato verificato in questa fase: `uv 0.11.12` presente; remote `origin =
> https://github.com/themetriost/Sertor.git`; i 4 `pyproject.toml` dichiarano `license = { text =
> "MIT" }`, `requires-python = ">=3.11"`, `authors = [{ name = "Sertor" }]`, `version = "0.1.0"`, build
> `hatchling` (`requires = ["hatchling"]`, non pinnato). Nessun `LICENSE` nel repo né nei package.
> Nessun `urls`/`classifiers`/`keywords` in alcun pyproject. `sertor`/`sertor-flow` non dichiarano
> `readme` (solo `sertor-core` punta a `src/sertor_core/README.md`).

---

## Decision 1 — Fonte di verità della versione e meccanismo di bump (DA-P1, REQ-011, NFR-4)

**Decision.** La versione di prodotto vive in **un unico file di testo `VERSION` nella radice del
repository** (es. `0.1.0\n`); ciascuno dei 4 `pyproject.toml` passa da `version = "0.1.0"` statico a
**versione dinamica letta da quel file** via il plugin di hatchling `hatch.metadata` integrato
(`[tool.hatch.version] source = "regex"` / file di versione). Il bump è un'azione su **un solo file**;
i 4 artefatti ne ereditano la stessa versione per costruzione. La verifica di packaging (Decision 2)
**asserisce l'allineamento** leggendo la versione dei 4 metadati buildati e confrontandola con `VERSION`.

**Meccanismo concreto (hatchling, uv workspace).** Hatchling supporta `version.source` di tipo file
nativamente. Forma adottata (semplice, senza plugin di terze parti):

```toml
# in OGNI pyproject.toml dei 4 pacchetti:
[project]
dynamic = ["version"]            # rimuove "version = ..." statico

[tool.hatch.version]
path = "VERSION"                 # radice repo per la root; "../../VERSION" per i membri
pattern = "^(?P<version>.+?)\\s*$"
```

I membri (`packages/sertor`, `packages/sertor-flow`, `packages/sertor-install-kit`) puntano al
**medesimo** `VERSION` di radice con path relativo. Poiché in `uv build` ogni membro viene buildato
dalla propria directory, il path relativo `../../VERSION` risolve al file di radice in entrambi i
percorsi (build standalone del membro e build del workspace).

**Rationale.**
- **Un solo punto di verità** (NFR-4): editare 4 stringhe a mano è esattamente l'errore che la feature
  deve impedire (R-5, edge "versioni disallineate"). Un file unico + lettura dinamica elimina il
  disallineamento *per costruzione*, non per disciplina.
- **Niente over-engineering** (Principio III, convenzione repo): nessun tool di release (bump2version,
  hatch-vcs/tag-driven), nessuna dipendenza nuova. Il versioning **automatico da git tag** è
  esplicitamente fuori ambito (requirements §4, Won't) — qui serve *coerenza* e una *strategia
  dichiarata*, non un meccanismo di release. `hatch.version` source-file è già parte di hatchling
  (build backend già in uso): zero superficie nuova.
- **Bump = un comando documentato**: cambiare la riga di `VERSION` (a mano o con un one-liner) e
  ricostruire. La guida lo documenta; la verifica lo enforce.

**Alternatives considered.**
- *Versione statica `version = "x"` ×4 + script di sync* — rifiutata: reintroduce 4 sorgenti di
  verità e uno script custom da mantenere; il disallineamento ridiventa possibile tra un bump e il
  run dello script (NFR-4 violato nello spazio tra le due azioni).
- *`hatch-vcs` (versione da git tag)* — rifiutata: è il meccanismo automatico da tag, fuori ambito
  (Won't); aggiunge una dipendenza di build e accoppia la versione alla strategia di tag, decisione
  di *design* rinviata.
- *Campo condiviso in `[tool.uv.workspace]`* — non esiste: uv non propaga una versione di workspace ai
  membri (ogni membro ha la sua `[project].version`). Il file unico letto da hatchling è il
  meccanismo realmente disponibile.

**Open risk.** Se hatchling in una versione futura cambiasse l'API `version.source` file-based, la
build fallirebbe in modo visibile (la verifica di build lo coglie). Pin di hatchling fuori ambito (i
`requires = ["hatchling"]` restano non pinnati come oggi; non li tocchiamo per non allargare lo scope).

---

## Decision 2 — Forma e collocazione della verifica ripetibile (REQ-022, gruppi C/D, NFR-1/2)

**Decision.** La verifica è una **suite pytest dedicata, marcata `@pytest.mark.integration`**, in
`tests/integration/test_packaging.py` (root del workspace), **non** inclusa nella CI unit veloce. Si
articola in tre livelli, dal più economico al più costoso:

1. **Verifica statica dei metadati e della licenza (no build, veloce).** Legge i 4 `pyproject.toml` e
   il file `VERSION`, e asserisce: file `LICENSE` presente in radice e in ogni package (REQ-001);
   `license` MIT coerente (REQ-002, REQ-004); versione allineata ai 4 + a `VERSION` (REQ-011, REQ-014
   per i campi user-facing); `requires-python >= 3.11` ×4 (REQ-012); per i due user-facing
   (`sertor`, `sertor-flow`) presenza di `name/version/description/authors/license/urls` (REQ-010,
   REQ-014). Questo livello **non richiede `uv build`** ed è il gate dei gruppi A/B.
2. **Verifica di build dell'artefatto (`uv build`, offline).** Per ogni package distribuibile esegue
   `uv build --package <name> --out-dir <tmp>` (o `uv build` dal package dir), asserisce sdist+wheel
   prodotti (REQ-020); estrae la wheel (zipfile, stdlib) e verifica: `LICENSE` incluso (REQ-003); per
   `sertor`, `assets/**` presenti (REQ-021); `entry_points.txt` / `METADATA` dichiarano i
   console-script attesi (REQ-023); metadati `License`/`Project-URL`/`Classifier` nei METADATA
   user-facing. Su fallimento di build → identifica package + esce non-zero (REQ-024). **`uv build`
   non contatta PyPI** (NFR-1): build da sorgente locale.
3. **Verifica install pulito a un comando (env effimero, GitHub-only).** Su un **venv effimero**
   (`tmp_path`), installa da `git+url` con i due gestori e verifica gli entry-point invocabili
   (`--help`/`--version`, exit 0): `uv`/`uvx` = percorso primario e **gate** (REQ-030/031/034/035);
   `pip` = percorso secondario verificato best-effort (REQ-033, vedi Decision 3). Questo livello tocca
   GitHub (clona il checkout via `git+url`) ma **non** PyPI per i pacchetti Sertor (le dipendenze
   interne si risolvono dal workspace).

**Helper di verifica = funzioni pure + thin runner, NON import di `sertor_core`.** Le asserzioni su
metadati/wheel sono **stdlib pura** (`tomllib`, `zipfile`, `email.parser` per i METADATA,
`configparser` per `entry_points.txt`); le build/install sono **subprocess** verso `uv`/`pip`/`git`.
Nessun import di `sertor_core` (Principio XI: la verifica esercita gli *artefatti distribuiti*, non la
libreria; e comunque packaging non è runtime RAG). I subprocess girano in `tmp_path` con `cwd`
controllata — non toccano il repo ospite (REQ-052).

**Rationale.**
- **Marker `integration`, non `unit`** (esiste già, `pyproject.toml` markers): `uv build` ×4 + un
  install pulito in venv effimero sono **lenti** e **toccano la rete GitHub** → non appartengono alla
  CI unit veloce (`uv run pytest -m "not cloud"` e `tests/unit` restano veloci e offline-totali). Il
  livello 1 (statico) è veloce ma resta nella stessa suite `integration` per coesione del contratto di
  packaging; chi vuole solo lo statico può selezionarlo per nome.
- **Niente marker nuovo**: `cloud` significa "credenziali/servizi cloud" — qui **non** servono (NFR-1:
  no cloud); `integration` = "end-to-end" calza. Aggiungere un terzo marker sarebbe over-engineering
  (Principio III).
- **Tre livelli a costo crescente**: il livello 1 (statico) coglie il 90% delle regressioni di
  coerenza (licenza/metadati/versione) **senza** pagare la build; i livelli 2/3 chiudono build e
  install. Un fallimento riporta sempre *package + percorso* (REQ-024, REQ-035).
- **stdlib per l'ispezione wheel**: una wheel è uno zip; i METADATA sono RFC822; `entry_points.txt` è
  INI. Nessuna dipendenza nuova (no `pkginfo`/`build`/`twine`).

**Collocazione.** `tests/integration/test_packaging.py` nel testpaths della root (`tests`), accanto
agli altri `test_*_end_to_end`/`test_local_only`. La root vede già tutti i `pyproject.toml` del
workspace e ha `uv` nell'ambiente. La verifica è eseguibile con `uv run pytest -m integration
tests/integration/test_packaging.py`.

**Alternatives considered.**
- *Script PowerShell/bash standalone in CI* — rifiutata come forma primaria: perde l'integrazione con
  pytest (selezione per marker, report uniforme, asserzioni leggibili) e duplica logica di
  inspection. Un thin wrapper script che invoca pytest resta possibile a valle (doc), ma la **verità**
  è la suite pytest.
- *Test nella suite unit con build reale* — rifiutata: viola FAST/Independent (F.I.R.S.T.); `uv build`
  in unit rallenterebbe la CI veloce e introdurrebbe dipendenza di rete.
- *Verifica solo statica (no build/install reali)* — rifiutata: REQ-020/021/030..035 richiedono la
  prova *reale* che l'artefatto si costruisca e l'install pulito funzioni; lo statico da solo non
  attesta la wheel né l'entry-point installato.

---

## Decision 3 — Percorso secondario `pip` e dipendenze interne di workspace (DA-P2, REQ-033/035, R-2)

**Decision.** Il **percorso primario è `uv`/`uvx`** (gate del Must): `uvx --from "git+<url>#subdirectory=packages/sertor" sertor --help` e analogo per `sertor-flow`. È verificato e **deve** rendere disponibili gli entry-point risolvendo `sertor-core`/`sertor-install-kit` dal **workspace scoperto nel checkout git** (comportamento già verificato end-to-end 2026-06-12; vedi nota in `packages/sertor/pyproject.toml`).

Il **percorso secondario è `pip`**, verificato **best-effort e documentato**:
`pip install "git+<url>#subdirectory=packages/sertor"`. Atteso comportamento: `pip` **non** conosce
il concetto di *workspace uv*; quando risolve le dipendenze `sertor-core`/`sertor-install-kit` di
`sertor`, **non** le scopre automaticamente dal checkout come fa `uv`, e — non essendo su PyPI —
fallisce la risoluzione (o richiederebbe `#subdirectory` espliciti per ciascuna dipendenza interna).
**Questo è un limite atteso e accettato** (DA-P2): non blocca il "done".

**Come la verifica lo tratta (REQ-035).**
- Il caso `uv`/`uvx` è un **assert hard**: se l'entry-point non è disponibile → la verifica **fallisce**
  identificando package + gestore.
- Il caso `pip` è un **assert soft / xfail documentato**: la verifica *tenta* l'install `pip` e
  **registra l'esito**. Se `pip` risolve (improbabile per le dipendenze di workspace) → ottimo,
  asserisce gli entry-point. Se `pip` **non** risolve le dipendenze interne → la verifica **non
  fallisce il Must**: marca il caso come *known-limitation* (es. `pytest.xfail("pip non risolve il
  workspace uv — FEAT-010", strict=False)` o un assert condizionale con messaggio) e il limite è
  **documentato** in `docs/install.md`. L'ergonomia piena di `pip` è rinviata a **FEAT-010**.

**Rationale.**
- **Allinea verifica e decisione**: DA-P2 dice esplicitamente che `pip`-workspace non è gate. Tradurlo
  in un `xfail(strict=False)`/soft-assert rende la verifica *onesta*: prova davvero `pip`, ma non
  trasforma un limite noto in un rosso che blocca il merge.
- **Niente null silenzioso** (Principio IV): il limite non è ignorato — è **dichiarato** (xfail con
  motivo + nota in `docs/install.md`), così resta visibile e tracciato verso FEAT-010, non sepolto.
- **Confine pulito**: la feature **non** prova a far funzionare `pip`-workspace (sarebbe scope creep
  verso FEAT-010); si limita a *verificare* e *documentare* lo stato di fatto.

**Forma documentale del limite (REQ-040/041, R-2).** `docs/install.md` riporta, per entrambi i
gestori, il comando esatto della distribuzione interim; per `pip` aggiunge una nota: *«`pip install
git+url#subdirectory=…` installa il pacchetto ma la risoluzione delle dipendenze interne di workspace
(`sertor-core`, `sertor-install-kit`) **non** è garantita come con `uv` — usa `uv`/`uvx` per l'install
a un comando; l'ergonomia piena di `pip` è rinviata a FEAT-010»*.

**Alternatives considered.**
- *`pip` come gate alla pari di `uv`* — rifiutata: contraddice DA-P2; richiederebbe di risolvere il
  `pip`-workspace ora (scope di FEAT-010).
- *Non verificare `pip` affatto* — rifiutata: REQ-033 richiede **≥2 gestori** verificati; `pip` va
  *provato* anche solo per documentarne lo stato (la prova è ciò che rende il limite un fatto, non
  una congettura).
- *Workaround `pip` con `#subdirectory` multipli per ogni dipendenza interna* — rifiutata in questo
  ambito: è ergonomia avanzata dell'installer (FEAT-010), non coerenza di packaging.

---

## Punti tecnici di supporto (non incogniti, fissati qui)

### P1 — File LICENSE: collocazione e inclusione nella wheel (REQ-001/003)
Un solo testo MIT canonico in **radice** (`/LICENSE`); ogni package distribuibile ne ha una **copia**
nella propria sotto-directory (`packages/<pkg>/LICENSE`) o, dove il package è la root (`sertor-core`),
la radice stessa. Hatchling include la licenza nella wheel via `[tool.hatch.build.targets.wheel]`
+ il campo standard `license-files` (PEP 639) oppure `force-include`. Forma adottata: dichiarare nel
`[project]` di ciascun package `license = "MIT"` (espressione SPDX) o mantenere `{ text = "MIT" }` e
aggiungere il file ai dati inclusi. La verifica (Decision 2, liv. 2) **estrae la wheel e asserisce la
presenza di `LICENSE`** — è il controllo che rende vera l'inclusione, indipendentemente dal modo.

> Nota MIT con anno/holder: il testo MIT richiede `Copyright (c) <anno> <holder>`. Holder = "Sertor"
> (coerente con `authors`), anno 2026. Nessun dato personale/segreto nel testo.

### P2 — Metadati user-facing da aggiungere (REQ-010/013)
Per `sertor` e `sertor-flow` (user-facing): aggiungere
`urls = { Repository = "https://github.com/themetriost/Sertor" }`, `description` (già presente),
`authors` (già `[{ name = "Sertor" }]` — adeguato), `readme` (puntare a un README del package, oggi
assente per i due: o si aggiunge un README minimale o si omette `readme` lasciando la sola
`description`; la verifica non richiede `readme`, solo `description`), e (Should, REQ-013)
`classifiers` (`License :: OSI Approved :: MIT License`, `Programming Language :: Python :: 3.11/3.12`,
`Intended Audience :: Developers`) + `keywords` (`rag`, `retrieval`, `installer`, `wiki`, `speckit`).
`sertor-core`/`sertor-install-kit` (interni, DA-P3/P4): **esonerati** dalla checklist user-facing; per
`sertor-core` resta utile (non obbligatorio) un set di `urls`/`classifiers` per chiarezza.

### P3 — `requires-python` (REQ-012)
Già `>=3.11` ×4. Nessuna modifica; la verifica lo asserisce.

### P4 — Invarianti preservati (gruppo F)
`install ≠ run` (REQ-050) è già garantito dall'architettura esistente (install non avvia indicizzazione)
e non viene toccato da questa feature (solo metadati/LICENSE/verifica/doc). Nessun segreto introdotto
(REQ-051, SC-009): `LICENSE`/metadati non contengono chiavi; la verifica usa solo `git+url` pubblico e
venv effimeri. Host-agnostico (REQ-053): la verifica gira in `tmp_path`, non assume layout ospite.

---

## Sintesi delle decisioni

| # | Incognita | Decisione | Driver |
|---|-----------|-----------|--------|
| 1 | Fonte versione + bump | File unico `/VERSION` letto da `[tool.hatch.version]` in tutti e 4 i pyproject (`dynamic`) | NFR-4, Princ. III, no tag-automatico (Won't) |
| 2 | Forma/sede verifica | Suite pytest `@integration` `tests/integration/test_packaging.py`, 3 livelli (statico → build → install), stdlib+subprocess, no `sertor_core` import | REQ-022, NFR-1/2, Princ. XI |
| 3 | Percorso `pip` | `uv`/`uvx` gate hard; `pip` verificato soft (`xfail strict=False`) + limite documentato → FEAT-010 | DA-P2, R-2, Princ. IV (non nascondere il limite) |

Nessun `[NEEDS CLARIFICATION]` residuo: le tre incognite erano di *design* (come), tutte risolte sopra.
