---
title: "Ricognizione SpecLift (repo Sinthari) — comprensione per decisioni di packaging Sertor"
type: source
tags: [speclift, sinthari, recon, packaging, sertor-rag, ears, deterministic-sandwich, vendoring]
created: 2026-07-01
updated: 2026-07-01
sources: ["Sinthari repo (github.com/themetriost/Sinthari, master @ be4da28), clonato in C:/Workspace/Git/ExternalRepos/Sinthari"]
---

# Ricognizione SpecLift

Studio di sola lettura del repo **themetriost/Sinthari** (`master` @ `be4da28`, PR #5 mergiata) per capire
la capacità **SpecLift** e le sue implicazioni per Sertor. Nessuna modifica al repo Sinthari.

**Convenzione FATTO vs INFERENZA:** i **FATTI** citano `file:riga`; le **INFERENZE** sono marcate.

---

## 1. Cosa fa la CLI end-to-end

SpecLift è un **generatore `diff → requisiti EARS ancorati`**. Entry point console `speclift =
speclift.cli:main` (`pyproject.toml:20`). Tre modalità (`cli.py:1-11,63-69`):

- `speclift <ref>` — **monolitico legacy**: autore EARS in-process (stub deterministico, offline/test).
- `speclift bundle <ref>` — **marcia 1** (deterministica): emette il fascicolo di evidenza per l'agente.
- `speclift assemble --bundle … --authored …` — **marcia 2** (deterministica): rilegge le frasi
  dell'agente, **riverifica le àncore** (il moat) e stampa il report.

### La pipeline a 7 stadi (il "sandwich deterministico")

Composition root in `pipeline.py`; sequenza `ingest → parse_diff → locate_evidence → bundle → lift →
verify → render` (`pipeline.py:1-7,58-104`). Sei stadi su sette sono **deterministici e testabili**; uno
solo è giudizio LLM (`lift`).

| Stadio | File | Meccanico? | Cosa fa |
|--------|------|-----------|---------|
| ingest | `stages/ingest.py` + `adapters/git_diff.py` | sì | `git show`/`git diff --staged`/`git diff A..B` via subprocess → `RawDiff`. Decodifica byte UTF-8 `errors="replace"` (`git_diff.py:44`, fix bug Windows cp1252). Exit git non-zero → `InvalidRefError` (exit 2). |
| parse_diff | `stages/parse_diff.py` | sì | Da unified-diff a `Changeset` (file/hunk/identificatori candidati). |
| filter_sources | `stages/filter_sources.py` | sì | Esclude **sempre** `specs/`, `requirements/`, `.specify/` (sono ciò *contro cui* SpecLift si confronta — includerli è circolare); la doc (`.md`, `docs/`, …) esclusa di default, inclusa con `--include-docs` (i "due SpecLift"). File esclusi **dichiarati**, mai silenziati (`config.py:29-38`). |
| locate_evidence | `stages/locate_evidence.py` + `adapters/rag_sertor.py` | sì (usa il RAG) | **UNICO stadio che tocca il RAG.** Per ogni file aggrega l'evidenza **per simbolo** (G4, anti-frammentazione): hunk dello stesso simbolo same-file → un `EvidenceItem`; hunk senza simbolo → un item-hunk; cancellazioni → `unresolved`. Simboli cross-layer restano come *contesto*, senza àncora propria (`locate_evidence.py:1-14`). |
| bundle | `stages/bundle.py` | sì | Compone l'`EvidenceBundle` (contratto JSON versionato, `version="1"`). |
| **lift** | `stages/lift.py` | **NO — giudizio** | L'**unico stadio LLM**. Delega a `EarsAuthor.author(bundle)`. Fa rispettare **REQ-X01**: se l'autore introduce un'àncora non nel bundle → `BundleContractError` fail-loud (`lift.py:32-46`). Segnala quote multi-quota mancanti (`_missing_quota_notes`). |
| verify | `stages/verify.py` + `adapters/anchor_fs.py` | sì | **IL MOAT.** Ogni requisito la cui àncora non verifica sul filesystem è **escluso** e segnalato, mai tenuto in silenzio (`verify.py:23-42`). |
| render | `stages/render.py` | sì | `SpecLiftReport` → JSON canonico + Markdown derivato (equivalenza biunivoca). |

### Il "sandwich deterministico" concretamente (chi fa cosa)

Le due marce **spezzano la pipeline al confine del bundle** (`pipeline.py:111-175`) così che l'autore EARS
sia l'**agente chiamante** invece di uno stub in-process:

- **CLI meccanica (marcia 1, `build_evidence_bundle`)**: ingest → parse → filtro → locate → bundle →
  **stop**. Emette `<out>.bundle.json` con, per ogni item, `index` + àncora + `diff` da descrivere
  (`serialize.py:88-118`, `_authoring_item`).
- **Agente (le frasi EARS)**: legge il bundle, scrive requisiti EARS multi-quota, ognuno agganciato a un
  item **per indice** (mai un'àncora nuova). Output `speclift-authored.json`
  (`{changeset_ref, requirements:[{item, quota, statement}], open_questions}`) — vedi `SKILL.md:80-96`.
- **CLI meccanica (marcia 2, `assemble_report`)**: rilegge bundle + authored, àncora per indice (`lift`
  con `AuthoredRequirementsAuthor`), **riverifica** le àncore sul filesystem (`verify`), calcola i drift,
  stampa (`cli.py:156-203`).

**Il "moat" = riverifica deterministica delle àncore** (`anchor_fs.py:26-62`). RAG *propone*, filesystem
*dispone*. Per ogni àncora controlla, senza eseguire codice: (a) il file esiste e l'intervallo di righe è
nei limiti; (b) se cita un simbolo, il nome compare nel file (presenza statica); (c) se cita un test, il
file-test esiste e **referenzia** il simbolo (uso statico). L'LLM non inventa mai un'àncora: se il testo
EARS è sbagliato ma le àncore reggono, resta citabile e riscrivibile. È l'idea del pattern
[[deterministic-sandwich]]: *giudizio isolato, input pulito, output verificato*.

**Exit codes** (`cli.py:8-10`, `contracts/cli.md:37-41`): `0` ok (anche report vuoto) · `2` ref git
invalido · `3` RAG giù/indice mancante · `4` `EarsAuthor` giù · `5` bundle/contratto invalido. Nessun
output parziale silenzioso: causa + stadio su stderr.

> **Onestà dichiarata (`ears-author-port.md:62-64`):** la CLI **da sola** non emette requisiti veri (solo
> placeholder dallo `StubEarsAuthor`). La capacità piena è **CLI + skill + agente** insieme.

---

## 2. Dipendenza esatta dal RAG di Sertor (CRITICO)

**FATTO — un solo punto d'uso, e più stretto di quanto la documentazione lasci intendere.** Tutto il
consumo RAG è in `adapters/rag_sertor.py`. SpecLift invoca il RAG **solo come subprocess della CLI
`sertor-rag`**, mai via MCP, con un **unico sottocomando**:

```
sertor-rag search <query> --type code --json -k 5
```

(`rag_sertor.py:86`, costante `_SEARCH_K = 5`). Il vehicle completo è
`("uv", "run", "--project", ".sertor", "sertor-rag")` (`config.py:27`), eseguito con `cwd=repo_path`
(`rag_sertor.py:111-124`).

- **Cosa invoca**: due metodi, entrambi sullo stesso sottocomando `search --type code`:
  - `locate_symbols(file, identifiers, snippet)` → query = ogni identificatore candidato (dedup,
    cap `MAX_QUERIES_PER_SYMBOL=4`, `config.py:13`); fallback alla prima riga dello snippet solo se è un
    singolo identificatore valido (`rag_sertor.py:42-83`).
  - `locate_tests(symbol)` → `search <symbol.name>`, filtra gli hit il cui `path` è un test
    (`test_`/`_test.py`/`/tests/`) (`rag_sertor.py:61-73,102-108`).
- **Cosa si aspetta come output**: un **array JSON** dove ogni hit ha almeno `path` e (opzionale)
  `chunk_id` (`rag_sertor.py:50-58,66-72,97-99`). La riga esatta del simbolo **non** è usata (`line=0`),
  perché la CLI `search` non la fornisce → l'àncora usa le righe dell'hunk (`rag_sertor.py:55`).
- **Cosa fa se il RAG è assente/rotto (fail-loud, sì)**: runner con exit non-zero (indice mancante →
  Sertor solleva `IndexNotFoundError`, exit ≠ 0), output non-JSON, o array non-lista → tutti sollevano
  `RagUnavailableError` → **exit 3** (`rag_sertor.py:87-99,120-124`). Nessun fallback silenzioso a
  `Read`/`Grep`. Coerente con REQ-X02 (`epic.md:94-96`).

### Verifica del claim di handoff «localizza via Sertor RAG vehicle, mai importa sertor_core»

- **`mai importa sertor_core`: VERIFICATO.** `grep sertor_core|import sertor` su tutto `src/` → **zero
  import**; le uniche occorrenze sono commenti («mai `import sertor_core`») in `config.py:26` e
  `rag_sertor.py:3`. Il vehicle è puro subprocess (Constitution III).
- **`localizza simboli/test via Sertor RAG`: VERIFICATO ma NARROW.** ⚠️ **Discrepanza doc↔codice
  importante.** L'handoff e le pagine wiki (`speclift-handoff.md:52-54`, `concepts/speclift.md:64`)
  affermano che SpecLift usa `find_symbol`/`who_calls`/`search_docs`/`get_context` (i tool MCP di
  navigazione del code-graph). **Il codice NON li usa.** La docstring dell'adapter lo dichiara
  esplicitamente (`rag_sertor.py:4-7`): «la navigazione `find_symbol`/`who_calls` è solo MCP e non
  disponibile qui → si usa `search` per la localizzazione». **Il legame reale con Sertor è quindi
  un solo comando CLI (`sertor-rag search --type code --json -k`)**, non il code-graph. Per Sertor questo
  è un vincolo di superficie molto sottile e stabile.

### Compatibilità reale con la CLI Sertor odierna (verificato nel repo Sertor)

**FATTO — compatibile.** In Sertor, `sertor-rag search` accetta `query`, `-k`, `--type {code,doc,both}`,
`--json` (`src/sertor_core/cli/__main__.py:124-131`). Con `--json` e `--type code` l'output è un **array
piatto** di dict con `path`, `doc_type`, `chunk_id`, `score`, `preview` (`cli/output.py:95-109`). SpecLift
legge `path` e `chunk_id` → **combacia**. Nota: `--type code` mantiene l'array piatto; solo `--type both`
restituisce la coppia strutturata `{"docs":[…],"code":[…]}` (FEAT-070) — SpecLift usa `--type code`,
quindi **non** è impattato da quel breaking change.

---

## 3. Footprint di packaging

- **Dipendenze runtime**: **solo `jsonschema>=4.0`** (`pyproject.toml:7-11`). **CONFERMATO.** Il core è
  stdlib-only; `git` e `sertor-rag` sono invocati via subprocess. `jsonschema` serve **solo ai test di
  contratto** (`tests/contract/`), non al runtime della pipeline — INFERENZA: potrebbe essere spostato in
  `[dev]` e azzerare le dipendenze runtime.
- **`requires-python = ">=3.12"`**: **CONFERMATO** (`pyproject.toml:6`, `target-version = "py312"`
  `:40`). Rilevante: Sertor è `>=3.11` su tutti e 4 i pacchetti del workspace
  (`pyproject.toml:6` + `packages/*/pyproject.toml:5`). Vedi §7c.
- **Build backend**: `hatchling`, wheel = `packages = ["src/speclift"]` (`pyproject.toml:22-27`).
- **Struttura `src/speclift/`**: `cli.py`, `pipeline.py`, `config.py`, `serialize.py`, `observability.py`,
  `domain/` (`models.py`, `ports.py`, `errors.py` — puri, nessun I/O/SDK), `adapters/`
  (`git_diff.py`, `rag_sertor.py`, `anchor_fs.py`, `ears_requirements.py` stub, `authored.py`),
  `stages/` (8 file). Clean/ports&adapters, dominio puro.
- **Entry point**: `[project.scripts] speclift = "speclift.cli:main"`.
- **Self-contained?** **SÌ.** Tutto il codice del pacchetto vive sotto `src/speclift/`; il wheel impacca
  solo quello. **Nessun** import di codice Sinthari-specifico fuori da `src/speclift/`
  (INFERENZA da struttura + grep: le uniche dipendenze esterne sono subprocess `git` e `sertor-rag`).

---

## 4. I contratti

`specs/001-speclift-mvp/contracts/`:

- **`cli.md`** — sintassi delle 3 modalità, flag (`--staged`/`--range`/`--format`/`--out`/`--include-docs`/
  `--verbose`; per `bundle`/`assemble` anche `--repo`), **filtro sorgenti G3**, exit code 0/2/3/4/5, e la
  nota «RAG via vehicle `uv run --project .sertor sertor-rag`, mai `import sertor_core`» (`cli.md:72-74`).
- **`evidence-bundle.schema.json`** — contratto versionato (`version const "1"`, `additionalProperties:
  false`). `$defs`: `anchor` (file, lines[2], symbol?, test?, granularity∈{symbol,hunk},
  status∈{verified,unverified}), `testRef`, `symbol`, `hunk`, `evidenceItem`. È la fonte di verità
  indipendente dalla vista Markdown.
- **`output.schema.json`** — `SpecLiftReport`: `requirements[]` (id, quota∈{user_capability,behaviour,
  implementation}, statement, anchor $ref al bundle-schema, source_item?), `drifts[]` (status const
  `proposed`), `excluded[]` (statement+reason, trasparenza del moat), `open_questions[]`.
- **`ears-author-port.md`** — il port `EarsAuthor.author(bundle) -> EarsAuthoringResult`. Invarianti
  vincolanti: **nessuna àncora nuova** (REQ-X01), non-interattivo, multi-quota, formato EARS standard,
  **fail-loud** se `requirements` non disponibile. Documenta la disambiguazione 2026-06-29: «lo fa Sertor»
  = «lo fa l'**agente chiamante** che opera la skill dentro Sertor Flow», **niente batch esterno**, niente
  BLOCKED-EXT. Lo `StubEarsAuthor` resta solo per test/offline.

Requisiti canonici `requirements/speclift/`: `epic.md` (visione, ambito, CS1–CS6, REQ-X01..X06, backlog
FEAT-001..009) + 7 cartelle-feature (`ingest-changeset`, `parse-diff`, `localizza-evidenza`,
`evidence-bundle`, `stesura-ears`, `anchor-verifier`, `output-render`). **NB**: `epic.md:98,116` parla
ancora di «delega alla skill `requirements` di Sertor» — testo pre-disambiguazione; la decisione viva
(`ears-author-port.md`) dice **agente chiamante**, non un batch della skill `requirements`.

---

## 5. La skill (`skills/speclift/SKILL.md`)

- **Struttura**: frontmatter (`name`, `description` ricca per il triggering, `argument-hint`,
  `compatibility: "Richiede la CLI speclift installata + git su PATH"`, `metadata.author: sinthari`,
  `user-invocable: true`) + 4 step: (1) `speclift bundle <ref> --out <TMP>/…`; (2) leggi il bundle e
  **scrivi le frasi EARS** multi-quota (le 5 forme EARS: Ubiquitous/Event/State/Unwanted/Optional) in
  `speclift-authored.json`, ancorate per `index`; (3) `speclift assemble --bundle … --authored …`;
  (4) riporta all'utente (confermati/excluded/open_questions/drifts).
- **Host-agnostica? SÌ (verificato).** Nessun path `.claude/`/`.github/`, nessuno slash-command, nessun
  nome-modello. Invoca genericamente `speclift …` («se il progetto la espone via un runner, es.
  `uv run speclift …`», `SKILL.md:31`). Coerente con REQ-X05.
- **Come l'agente la usa**: la skill è il «cervello» del sandwich — la CLI fa il meccanico, l'agente
  scrive le frasi leggendo il bundle e riferendo gli item **per indice** (l'unico modo di agganciare
  la frase all'evidenza; un indice inesistente fa fallire la marcia 2 by design, `SKILL.md:94-96`).

---

## 6. La loro ricognizione del NOSTRO sertor-flow

**FATTO — non esiste** un file `wiki/syntheses/handoff-speclift-to-sertor-flow.md` nel repo (né
`concepts/speclift.md`/`deterministic-sandwich.md` contengono un'analisi di `packages/sertor-flow`). Ho
cercato tutti i `.md` del repo: gli unici documenti pertinenti sono l'handoff **Noetix→Sinthari**
(`wiki/sources/processed/speclift-handoff.md`, che riguarda l'idea, non il nostro sertor-flow) e i
concept `speclift.md`/`deterministic-sandwich.md`.

**Conclusione:** **Sinthari NON ha (ancora) prodotto una ricognizione della struttura di
`packages/sertor-flow` né suggerito opzioni di packaging.** Quello che esiste è il vincolo di consumo
lato-loro: SpecLift assume «il changeset appartiene a un repo **indicizzato** dal RAG del progetto»
(`epic.md:71`) e consuma Sertor **solo via vehicle CLI** attraverso `.sertor/` (`.sertor/pyproject.toml`
installa `sertor-core[azure,graph,mcp,rerank]` da `git+https://github.com/themetriost/Sertor.git`).
INFERENZA: la loro aspettativa d'integrazione è «Sertor è un servizio esterno che espone `sertor-rag`»,
non «SpecLift diventa un pacchetto dentro Sertor».

---

## Implicazioni per Sertor (packaging + prereq RAG + versione 3.12)

### (a) Fattibilità del vendoring come `packages/speclift`

**INFERENZA (alta confidenza): fattibile e a basso attrito.** Il pacchetto è self-contained sotto
`src/speclift/`, hatchling, dominio puro ports&adapters — la stessa forma dei pacchetti Sertor. **Zero
dipendenza da `sertor_core`** (verificato), quindi nessun ciclo con `sertor-core`; come `sertor-flow`,
`speclift` sarebbe un membro del workspace **senza** dipendere dal core. L'unica dipendenza runtime
(`jsonschema`) è probabilmente spostabile in `[dev]` (usata solo dai test di contratto).

Attriti da gestire, non bloccanti:
- **Naming/asset**: la skill è già host-agnostica → distribuibile con il pattern asset di `sertor-flow`
  (`assets/…/skills/speclift/SKILL.md`) + generate/sync + guardia di parità Copilot. Andrebbe deciso se
  SpecLift è una capacità di `sertor-flow` (SDLC) o un nuovo pacchetto installabile a sé.
- **Vehicle**: SpecLift hardcoda `("uv","run","--project",".sertor","sertor-rag")` (`config.py:27`). Su
  un ospite Sertor «vero» il vehicle potrebbe essere semplicemente `sertor-rag` sul PATH → serve rendere
  il vehicle configurabile all'install (è già un campo `Config`, quindi override facile).
- **Lingua**: codice/commenti/skill in italiano; gli asset Sertor host-facing tendono all'inglese (E12).

### (b) Come si materializza il prerequisito RAG a runtime (cosa fallirebbe e dove)

Il prerequisito è **un indice RAG del repo ospite interrogabile via `sertor-rag search`**. Catena reale:

1. `SertorRagLocator._search` lancia `sertor-rag search <q> --type code --json -k 5` con `cwd=repo`
   (`rag_sertor.py:85-124`).
2. **Se `sertor-rag`/`.sertor/` non esiste** → subprocess `FileNotFoundError`/exit≠0 → `RagUnavailableError`
   → **exit 3** (fail-loud). Punto di rottura: `rag_sertor.py:89-90` / `120-124`.
3. **Se l'indice non è costruito** → Sertor `search` solleva `IndexNotFoundError` (strict path,
   `cli/__main__.py:670`), exit≠0 → stesso `RagUnavailableError` → exit 3.
4. **Se l'output non è JSON/array** → `RagUnavailableError` («indice mancante o errore?»)
   (`rag_sertor.py:91-99`).

Quindi il fallimento è **onesto e localizzato** (mai degrado silenzioso). Per un ospite Sertor la
materializzazione del prereq è già coperta dal rituale/hook Sertor (`sertor-rag index .` +
`rag-freshness`): SpecLift **consuma** l'indice, non lo costruisce. INFERENZA: se vendorato, `speclift`
non deve reindicizzare — deve solo assumere (e verificare fail-loud) che l'indice esista, esattamente
com'è oggi. Un miglioramento possibile: mappare l'exit 3 su un messaggio azionabile «esegui
`sertor-rag index .`».

### (c) Il problema `requires-python >=3.12` vs workspace `>=3.11`

**FATTO**: SpecLift pinna `>=3.12` (`pyproject.toml:6`, `target-version = py312`); **tutti** i pacchetti
Sertor pinnano `>=3.11`. Un membro del workspace `uv` con `requires-python` più stretto **alza il
pavimento effettivo** del workspace risolto: convivere richiederebbe che l'intero `.venv` giri su ≥3.12,
oppure che `speclift` sia risolto/distribuito separatamente.

**INFERENZA (media-alta confidenza): il pin `>=3.12` è conservativo, non un requisito reale.** Ho cercato
sintassi 3.12-only (PEP 695 `type X =` / `def f[T]` / `class C[T]`, `itertools.batched`): **zero
occorrenze**. Il costrutto «più recente» usato è `StrEnum` (`domain/models.py:24`), disponibile **da
Python 3.11**. Nulla di ciò che ho letto richiede 3.12. **Raccomandazione**: prima del vendoring,
provare ad abbassare il pin a `>=3.11` (+ `target-version = py311`) e far girare la suite su 3.11; se
passa (probabile), l'attrito di versione **sparisce**. Da verificare sui file che non ho letto per intero
(`stages/parse_diff.py`, `render.py`, `ingest.py`, `bundle.py`, `filter_sources.py`, `observability.py`)
— ma il grep negativo è un forte indicatore.

---

## Sintesi dei rischi / sorprese che cambiano il quadro

1. **Discrepanza doc↔codice sul RAG** (la più importante): l'handoff/wiki dicono che SpecLift usa il
   **code-graph MCP** (`find_symbol`/`who_calls`); il **codice usa solo `sertor-rag search --type code
   --json`** (CLI, subprocess). Il legame reale con Sertor è **un solo comando**, molto più sottile e
   stabile di quanto la narrativa suggerisca — semplifica ogni decisione di packaging.
2. **Il pin `>=3.12` sembra rimovibile** (nessuna sintassi 3.12; `StrEnum` è 3.11) → il conflitto di
   versione col workspace è probabilmente **eliminabile con un edit di una riga + test**, non un
   ostacolo architetturale.
3. **Il file di handoff verso sertor-flow non esiste**: Sinthari non ha ancora analizzato il nostro
   `packages/sertor-flow` — la decisione di packaging è interamente da parte nostra.
