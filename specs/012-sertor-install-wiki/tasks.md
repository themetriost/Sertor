---
description: "Task list — FEAT-012: Installer `sertor` + `sertor install wiki`"
---

# Tasks: Installer `sertor` + `sertor install wiki` (FEAT-012)

**Input**: `specs/012-sertor-install-wiki/` — spec.md · plan.md · research.md · data-model.md · contracts/ · quickstart.md

**Prerequisites**: plan.md (PASS), spec.md (3 US: P1 repo nuovo / P2 non-distruttività+idempotenza / P3 governo), research.md (D1..D8 chiuse), data-model.md (Artifact/HostProfile/InstallPlan/ArtifactOutcome/InstallReport), contracts/cli-commands.md · install-report.md · claude-md-block.md

**Strategia**: MVP = US1 (Phase 1 → Phase 2 → Phase 3). Fase 4 (US2) aggiunge la garanzia di non-distruttività; Fase 5 (US3) completa backbone e opzioni CLI. Ogni fase è indipendentemente testabile.

**Note sui path**:
- Nuovo pacchetto: `packages/sertor/src/sertor_installer/` (modulo Python) + `packages/sertor/` (pyproject, tests)
- Test della feature: `packages/sertor/tests/` (co-locati col pacchetto) + `tests/unit/` della root per il test di guardia sync (pythonpath root include già `src` e `packages/sertor/src` — da garantire in T004)
- Core invariato: `src/sertor_core/`
- Assets (fonte canonica): `packages/sertor/src/sertor_installer/assets/`
- Derivato: `.claude/` del repo Sertor

## Formato: `[ID] [P?] [Story] Descrizione`

- **[P]**: eseguibile in parallelo (file diversi, nessuna dipendenza incompleta)
- **[Story]**: user story di appartenenza (US1/US2/US3); assente in Setup/Foundational/Polish
- Ogni task include il path file esplicito

---

## Phase 1: Setup (Workspace & Packaging)

**Purpose**: Predisporre il monorepo uv workspace a due pacchetti e la struttura di directory del nuovo pacchetto `sertor`. Nessun comportamento implementato; il workspace deve girare senza rompere la suite esistente.

- [x] T001 Aggiungere `[tool.uv.workspace]` con `members = ["packages/sertor"]` al `pyproject.toml` di root e verificare che `uv sync` e `uv run pytest -m "not cloud"` completino ancora senza errori — file: `pyproject.toml`
- [x] T002 Creare la struttura di directory del pacchetto `sertor`: `packages/sertor/`, `packages/sertor/src/sertor_installer/`, `packages/sertor/src/sertor_installer/assets/`, `packages/sertor/tests/` — directory vuote con `.gitkeep` dove necessario
- [x] T003 Creare `packages/sertor/pyproject.toml` con: nome `sertor`, `requires-python = ">=3.11"`, dipendenza `sertor-core`, build-backend `hatchling`, console-script `sertor = "sertor_installer.__main__:main"`, `[tool.hatch.build.targets.wheel] packages = ["src/sertor_installer"]`, `[tool.pytest.ini_options] testpaths = ["tests"] pythonpath = ["src", "../../../src", "../../../."]` — file: `packages/sertor/pyproject.toml`
- [x] T004 Aggiornare `[tool.pytest.ini_options]` nel `pyproject.toml` di root per aggiungere `packages/sertor/src` al `pythonpath` (così `uv run pytest` dalla root trova `sertor_installer`; precondizione comunque consigliata: `uv pip install -e packages/sertor`, vedi checkpoint) e verificare che la baseline esistente continui a passare — baseline reale: **204 passed + 2 xfail + 1 deselected (207 raccolti)** — file: `pyproject.toml`
- [x] T005 Creare `packages/sertor/src/sertor_installer/__init__.py` vuoto e `packages/sertor/tests/__init__.py` vuoto — file: `packages/sertor/src/sertor_installer/__init__.py`, `packages/sertor/tests/__init__.py`

**Checkpoint**: `uv pip install -e packages/sertor` installa senza errori; `uv run pytest -m "not cloud"` passa (baseline invariata: 204 passed + 2 xfail).

---

## Phase 2: Foundational (Modelli di dominio, Assets e Accesso alle Risorse)

**Purpose**: Struttura dati di dominio, popolamento degli assets host-agnostici, accesso `importlib.resources`. Prerequisito bloccante per tutte le user story.

**ATTENZIONE**: Nessuna user story può iniziare fino al completamento di questa fase.

- [x] T006 Creare il modulo `packages/sertor/src/sertor_installer/artifacts.py` con: enum `ArtifactKind` (FILE/SETTINGS_MERGE/MARKER_BLOCK/STRUCTURE/CONFIG), enum `WriteStrategy` (CREATE_IF_ABSENT/MERGE_DEDUP/APPEND_BLOCK/INIT_STRUCTURE/GENERATE_CONFIG), enum `Outcome` (CREATED/SKIPPED/MERGED/BLOCK/ERROR), dataclass `Artifact(kind, source, target_rel, strategy)`, dataclass `ArtifactOutcome(target_rel, outcome, detail)`, validazione `target_rel` non assoluto e non risalente con `..` — file: `packages/sertor/src/sertor_installer/artifacts.py`
- [x] T007 Creare il modulo `packages/sertor/src/sertor_installer/report.py` con: dataclass `InstallReport(target, outcomes, created, skipped, merged, errors, failed_step)`, metodi `exit_code() -> int` (0/1/2), `render_human() -> str` (formato install-report.md §Formato umano), `render_json() -> str` (schema `install.report/1`) — file: `packages/sertor/src/sertor_installer/report.py`
- [x] T008 Popolare gli assets `packages/sertor/src/sertor_installer/assets/claude/` copiando e riscrivendo in versione host-agnostica (D3) i file della skill wiki-author da `.claude/`: `skills/wiki-author/SKILL.md`, `skills/wiki-author/wiki-playbook.md`, `skills/wiki-author/wiki-craft.md`, `skills/wiki-author/page-craft.md`, `skills/wiki-author/log-craft.md`, `skills/wiki-author/ops/record.md`, `skills/wiki-author/ops/distill.md`, `skills/wiki-author/ops/ingest.md`, `skills/wiki-author/ops/query.md`, `skills/wiki-author/ops/lint.md`, `skills/wiki-author/ops/reorg.md`, `skills/wiki-author/ops/generate.md`, `skills/wiki-author/ops/structure.md`, `skills/wiki-author/ops/rag-sync.md` — obiettivo: rimuovere/riformulare TUTTE le note "profilo Sertor" e le occorrenze di `Sertor|prototype|sertor_core` che non siano nome del comando di prodotto; sostituire `uv run sertor-wiki-tools` con `sertor-wiki-tools` (D3); verificare zero occorrenze di "Sertor-il-progetto" con grep — file: `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/{SKILL.md,wiki-playbook.md,wiki-craft.md,page-craft.md,log-craft.md,ops/*.md}`
- [x] T009 [P] Popolare `packages/sertor/src/sertor_installer/assets/claude/commands/wiki.md` (da `.claude/commands/wiki.md`, già pulito; verificare assenza riferimenti Sertor-specifici), `assets/claude/agents/wiki-curator.md` (da `.claude/agents/wiki-curator.md`, già pulito), `assets/claude/hooks/wiki-pending-check.ps1` (da `.claude/hooks/wiki-pending-check.ps1`, già host-agnostico — bundlare invariato, D6) — file: `packages/sertor/src/sertor_installer/assets/claude/commands/wiki.md`, `packages/sertor/src/sertor_installer/assets/claude/agents/wiki-curator.md`, `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
- [x] T010 [P] Creare `packages/sertor/src/sertor_installer/assets/settings.hooks.json` con il frammento delle 3 voci hook (SessionStart/Stop/SessionEnd, struttura `hooks.<evento>: [{hooks:[{type,shell,command,...}]}]` allineata al formato reale di `.claude/settings.json`) e `packages/sertor/src/sertor_installer/assets/claude-md-block.md` con il contenuto host-agnostico della sezione step-ritual (senza marker, punta a `wiki-curator`/`/wiki`/`wiki.config.toml`, zero riferimenti a Sertor) — file: `packages/sertor/src/sertor_installer/assets/settings.hooks.json`, `packages/sertor/src/sertor_installer/assets/claude-md-block.md`
- [x] T011 [P] Creare `packages/sertor/src/sertor_installer/assets/wiki.config.toml.tmpl` con il template del profilo wiki: segnaposti `{language}` e `{source_dirs}`, valori fissi per `root`, `index_file`, `log_file`, `log_dir`, `profile = "code+doc"`, sezione `[[taxonomy]]` con le 5 aree standard, `[roles] curator = "wiki-curator"` (senza `vcs`), `[rag] enabled = false` (D7); il template compilato deve superare `load_profile` — file: `packages/sertor/src/sertor_installer/assets/wiki.config.toml.tmpl`
- [x] T012 Creare `packages/sertor/src/sertor_installer/resources.py` con: funzione `asset_path(relative: str) -> importlib.resources.abc.Traversable` che restituisce `importlib.resources.files("sertor_installer") / "assets" / relative`; funzione `read_asset_text(relative: str) -> str`; funzione `iter_asset_dir(relative: str) -> Iterator[tuple[str, str]]` che percorre ricorsivamente la sottodirectory e restituisce `(rel_path_str, content)` — usa solo `importlib.resources` (niente `__file__`, D2) — file: `packages/sertor/src/sertor_installer/resources.py`
- [x] T013 Dichiarare gli assets come package-data in `packages/sertor/pyproject.toml`: con hatchling usare `[tool.hatch.build.targets.wheel] packages = ["src/sertor_installer"]` (hatchling include TUTTI i file sotto la dir di package, anche non-Python; la chiave `artifacts` ha altro significato — fix F6 analyze) e in caso di esclusioni inattese ricorrere a `force-include`; VERIFICARE con `uv build packages/sertor` + ispezione del wheel che `assets/**` sia incluso, e che `importlib.resources.files("sertor_installer")` risolva in editable — file: `packages/sertor/pyproject.toml`

**Checkpoint**: moduli `artifacts.py`, `report.py`, `resources.py` importabili; assets popolati e verificabili con grep (zero occorrenze Sertor-specifiche tranne nomi-comando).

---

## Phase 3: User Story 1 — Installare il sistema-wiki su un repo nuovo (P1) — MVP

**Goal**: Su un repo vuoto, `sertor install wiki` crea tutti gli artefatti attesi (skill, comando, agente, hook, settings, blocco CLAUDE.md, wiki.config.toml, struttura wiki/), stampa il report con tutti `created`, esce con 0. Nessun LLM/rete/indicizzazione.

**Independent Test**: `cd <tmp_dir_vuota> && sertor install wiki` → exit 0, tutti gli artefatti presenti, report elenca tutti come `created`, `grep -ri "sertor" <artefatti>` restituisce zero risultati (whitelist: nomi-comando), `sertor-wiki-tools scan --config wiki.config.toml` gira senza errori.

### Implementazione User Story 1

- [x] T014 [US1] Creare `packages/sertor/src/sertor_installer/config_gen.py` con: funzione `build_host_profile(target_root, source_dirs_override, language) -> HostProfile`, euristica `_infer_source_dirs(target_root) -> list[str]` (lista canonica: `src,lib,app,pkg,packages,docs,doc,tests,test,requirements,specs`; fallback `["."]`; D7), funzione `generate_wiki_config(profile: HostProfile) -> str` che carica `wiki.config.toml.tmpl` via `resources.read_asset_text` e inietta `language` e `source_dirs` — file: `packages/sertor/src/sertor_installer/config_gen.py`
- [x] T015 [US1] Creare `packages/sertor/src/sertor_installer/claude_md.py` con: costanti `MARKER_START = "<!-- SERTOR:WIKI-RITUAL START -->"` / `MARKER_END = "<!-- SERTOR:WIKI-RITUAL END -->"`, funzione `write_ritual_block(claude_md_path: Path, block_content: str) -> Outcome` che implementa i 3 casi dell'algoritmo D4 (assente→crea, presente senza marker→appendi, presente con marker→skip), invariante byte-per-byte fuori dai marker — file: `packages/sertor/src/sertor_installer/claude_md.py`
- [x] T016 [US1] Creare `packages/sertor/src/sertor_installer/settings_merge.py` con: funzione `merge_settings(settings_path: Path, hooks_fragment: dict) -> tuple[Outcome, str]` che implementa D5 (assente→crea, valido→merge dedup per `command`, malformato→solleva `ConfigError` con path e causa), funzione `_dedup_hooks(existing: dict, fragment: dict) -> tuple[dict, int]` che restituisce il dict merged e il conteggio di voci aggiunte — file: `packages/sertor/src/sertor_installer/settings_merge.py`
- [x] T017 [US1] Creare `packages/sertor/src/sertor_installer/install_wiki.py` con: funzione `build_install_plan() -> list[Artifact]` che restituisce la lista ordinata secondo `InstallPlan` (data-model §3): FILE×N skill+commands+agents+hooks, SETTINGS_MERGE, MARKER_BLOCK, CONFIG, STRUCTURE; funzione `execute_plan(plan: list[Artifact], profile: HostProfile) -> InstallReport` che esegue sequenzialmente e gestisce fail-fast (REQ-125, D8): al primo ERROR si ferma, `failed_step` valorizzato, artefatti già scritti restano — delega a `claude_md.write_ritual_block`, `settings_merge.merge_settings`, `config_gen.generate_wiki_config`, `sertor_core.wiki_tools.structure.init_structure` — file: `packages/sertor/src/sertor_installer/install_wiki.py`
- [x] T018 [US1] Creare il backbone CLI `packages/sertor/src/sertor_installer/__main__.py` con: `_build_parser()` con `argparse` (pattern `src/sertor_core/cli/__main__.py`): subparser `install` con sotto-subparser `wiki` (argomenti: `--target`, `--language`, `--json`), stub `rag` e `governance`; `main()` con UTF-8 forzato su stdout/stderr, dispatch su handler, catch `SertorError→stderr+exit1`, argparse→exit2; handler `_cmd_install_wiki(args)` che chiama `build_host_profile`, valida il target (non-esistente/non-scrivibile→`ConfigError` prima di scrivere), `execute_plan`, stampa report umano (o JSON con `--json`), return exit code — file: `packages/sertor/src/sertor_installer/__main__.py`
- [x] T019 [US1] Scrivere i test di accettazione US1 in `packages/sertor/tests/test_install_wiki.py`: (a) repo vuoto → tutti `created`, exit 0, presenza file system, report completo; (b) wiki.config.toml generato supera `load_profile` del core; (c) `sertor-wiki-tools scan/validate/lint` gira sulla config generata (SC-008 dogfood completo, fix F10 analyze — invocare come subprocess o import diretto, no rete); fixture `tmp_path` solo, no cloud — file: `packages/sertor/tests/test_install_wiki.py`
- [x] T020 [US1] Scrivere i test del backbone CLI in `packages/sertor/tests/test_cli.py`: help (`--help`, `install --help`) → exit 0 e stringhe attese; sottocomando ignoto → exit 2; stub `install rag|governance` → messaggio leggibile + exit non-zero; `--target` inesistente → exit 1 senza artefatti (SC-007 + edge case spec) — file: `packages/sertor/tests/test_cli.py`
- [x] T021 [P] [US1] Scrivere i test di `config_gen.py` in `packages/sertor/tests/test_config_gen.py`: euristica source_dirs (ospite con `src/`, ospite senza nulla → `["."]`, override `--source-dirs`); `--language it` → `language=it` nel toml; config generata supera `load_profile`; `language` default `en` — file: `packages/sertor/tests/test_config_gen.py`

**Checkpoint**: `uv pip install -e packages/sertor && sertor install wiki` su un tmp repo vuoto → exit 0, tutti gli artefatti presenti, report corretto; `uv run pytest packages/sertor/tests/ -m "not cloud"` verde.

---

## Phase 4: User Story 2 — Install sicuro su un repo con contenuti preesistenti (P2)

**Goal**: Su un repo pre-popolato (CLAUDE.md con contenuto utente, settings.json con hook custom, wiki.config.toml esistente, skill parziale), l'installer non sovrascrive nulla; integra in modo additivo; idempotente al re-run; report distingue created/skipped/merged.

**Independent Test**: fixture `tmp_path` pre-popolata con CLAUDE.md utente + settings.json con hook custom + wiki.config.toml + alcuni file skill già presenti → primo run: contenuto utente intatto byte-per-byte fuori dai marker; voci hook utente tutte in settings.json; report coerente → secondo run identico al primo (stesso stato filesystem, report tutto skipped/merged-0, exit 0).

### Implementazione User Story 2

- [x] T022 [US2] Estendere `packages/sertor/src/sertor_installer/claude_md.py` assicurando la garanzia byte-per-byte fuori dai marker: aggiungere test di invarianza con contenuto arbitrario prima/dopo il blocco (vedi T023); verificare che l'algoritmo legga il file con `Path.read_text(encoding="utf-8")` e non normalizzi line endings in modo distruttivo — nessuna modifica al codice se T015 già soddisfa; aggiungere docstring con la garanzia esplicita — file: `packages/sertor/src/sertor_installer/claude_md.py`
- [x] T023 [US2] Scrivere i test di `claude_md.py` in `packages/sertor/tests/test_claude_md.py`: (a) CLAUDE.md assente → crea con solo blocco; (b) presente senza marker → appendi, contenuto precedente byte-identico; (c) presente con marker → skip, file byte-identico; (d) re-run → nessuna duplicazione; (e) contenuto utente prima e dopo il blocco: intoccato — file: `packages/sertor/tests/test_claude_md.py`
- [x] T024 [US2] Scrivere i test di `settings_merge.py` in `packages/sertor/tests/test_settings_merge.py`: (a) settings.json assente → crea con 3 voci; (b) presente con hook utente → merge additivo, voci utente preservate, nessun duplicato; (c) re-run → zero nuove voci (MERGED detail «nessuna nuova voce»); (d) malformato → `ConfigError` con path e causa, file non toccato; (e) presente senza sezione `hooks` → crea la sezione — file: `packages/sertor/tests/test_settings_merge.py`
- [x] T025 [US2] Estendere `packages/sertor/tests/test_install_wiki.py` con i test di non-distruttività e idempotenza US2: (a) repo pre-popolato (CLAUDE.md con contenuto utente, settings.json con hook custom, wiki.config.toml esistente, skill parziale) → primo run: fuori-marker byte-identici, hook utente presenti, wiki.config.toml non toccato, file skill esistenti non sovrascritti, file mancanti creati; (b) doppio run → stesso stato filesystem, report tutto skipped/merged-0, exit 0 (SC-003); (c) settings.json malformato → exit 1, file malformato non toccato, artefatti già scritti restano, report con `failed_step` — file: `packages/sertor/tests/test_install_wiki.py`

**Checkpoint**: `uv run pytest packages/sertor/tests/test_claude_md.py packages/sertor/tests/test_settings_merge.py packages/sertor/tests/test_install_wiki.py -m "not cloud"` verde; nessun byte utente sovrascritto in tutti gli scenari di non-distruttività.

---

## Phase 5: User Story 3 — Scoprire e governare l'installazione (P3)

**Goal**: `sertor --help` e `sertor install --help` descrivono tutto; stub `install rag|governance` danno messaggio leggibile + exit non-zero; `--target`, `--language`, `--source-dirs` producono gli effetti attesi; errori d'uso → exit 2.

**Independent Test**: invocare help → exit 0 + stringhe attese (sottocomandi, argomenti, stub pianificati); sottocomando ignoto → exit 2; stub non implementato → exit 1 + messaggio; `--target <tmp>` → artefatti sotto `<tmp>`; `--language it` → `language = "it"` nel toml; `--source-dirs src,docs` → `source_dirs` corrispondente nel toml.

### Implementazione User Story 3

- [x] T026 [US3] Verificare e completare `packages/sertor/src/sertor_installer/__main__.py`: i sottocomandi stub `rag` e `governance` devono comparire nell'help di `sertor install --help` come «pianificati» (aggiungere metavar/help espliciti al subparser); il messaggio di stub deve includere il nome del sotto-comando; exit code degli stub = 1 via `SertorError` dedicata — file: `packages/sertor/src/sertor_installer/__main__.py`
- [x] T027 [P] [US3] Verificare il comportamento di `--target <path>` in `_cmd_install_wiki`: validare che il path esista ed sia una directory scrivibile prima di costruire `HostProfile` (altrimenti `ConfigError`→exit 1); garantire che tutti gli artefatti risolvano sotto `target_root` e non sotto `cwd` — file: `packages/sertor/src/sertor_installer/__main__.py`, `packages/sertor/src/sertor_installer/install_wiki.py`
- [x] T028 [P] [US3] Verificare che `--language` e `--source-dirs` siano passati correttamente a `build_host_profile` e che il `wiki.config.toml` generato rifletta i valori; `--source-dirs` deve essere parsato come lista CSV e sostituire l'euristica — file: `packages/sertor/src/sertor_installer/__main__.py`, `packages/sertor/src/sertor_installer/config_gen.py`
- [x] T029 [US3] Estendere `packages/sertor/tests/test_cli.py` con i test US3: (a) `sertor install --help` mostra `rag` e `governance` come pianificati; (b) `sertor install rag` → exit 1 + messaggio leggibile; (c) `--target <tmp>` → artefatti sotto `<tmp>`, non sotto cwd; (d) `--language it` → toml con `language = "it"`; (e) `--source-dirs src,docs` → toml con `source_dirs` corrispondente; (f) `--target` inesistente → exit 1, zero artefatti scritti — file: `packages/sertor/tests/test_cli.py`

**Checkpoint**: `uv run pytest packages/sertor/tests/test_cli.py -m "not cloud"` verde; `sertor --help` e `sertor install --help` mostrano tutti i sottocomandi e argomenti (SC-007).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Test di guardia drift assets↔.claude/, scansione host-agnosticità (SC-004), aggiornamento `.claude/` del repo Sertor (D2: propagare gli assets ripuliti), verifica dogfood SC-008, retro-compatibilità workspace.

- [x] T030 Creare `packages/sertor/src/sertor_installer/sync.py` con: funzione `sync_assets_to_claude(repo_root: Path, dry_run: bool = False) -> dict[str, str]` che copia `assets/claude/**` verso `.claude/` del repo (`assets → .claude`, D2); logga file creati/aggiornati/identici; `python -m sertor_installer.sync` come entry-point CLI di sviluppo — file: `packages/sertor/src/sertor_installer/sync.py`
- [x] T031 Scrivere `tests/unit/test_assets_sync.py` (nella root test suite) che confronta byte-per-byte ogni file in `packages/sertor/src/sertor_installer/assets/claude/` con il corrispondente in `.claude/` del repo Sertor (escludendo differenze accettate documentate: `uv run sertor-wiki-tools` vs `sertor-wiki-tools`, note host-specifiche di Sertor ammesse nel `.claude/` derivato); il test **fallisce** se divergono senza una giustificazione nell'allowlist — questo rende il drift un errore CI (D2) — file: `tests/unit/test_assets_sync.py`
- [x] T032 Scrivere `packages/sertor/tests/test_host_agnostic.py`: scansiona ogni file installato in `<tmp_repo>` dopo `sertor install wiki` con regex `r'\bsertor\b'` (case-insensitive) escludendo la whitelist (`sertor-wiki-tools`, `sertor-rag`); il test fallisce se trovano match — SC-004 — file: `packages/sertor/tests/test_host_agnostic.py`
- [x] T033 Eseguire `python -m sertor_installer.sync` per propagare gli assets ripuliti al `.claude/` del repo Sertor (D2: aggiornare il derivato dopo T008/T009), poi eseguire `uv run pytest tests/unit/test_assets_sync.py` e verificare che il test passi — azione di sviluppo, non crea file; aggiorna: `.claude/skills/wiki-author/` e file wiki collegati. **NOTA SEQUENZA (fix F4 analyze): T031 diventa verde SOLO dopo questo task — se T031 viene scritto prima, eseguirlo nello stesso giro di T033 (mai lasciare la suite rossa tra i due); l'ordine corretto è T030→T031+T033 nello stesso step.**
- [x] T034 Verificare la retro-compatibilità workspace: `uv run pytest -m "not cloud"` dalla root deve passare con tutti i test precedenti (baseline 204 passed + 2 xfail, più i nuovi) più i test del pacchetto `sertor`; in caso di conflitti `pythonpath` risolvere in `pyproject.toml` di root — file: `pyproject.toml`, `packages/sertor/pyproject.toml`
- [x] T035 Aggiornare `specs/012-sertor-install-wiki/quickstart.md` con il comando `python -m sertor_installer.sync` e il path del test di guardia (T031), se non già riflessi — file: `specs/012-sertor-install-wiki/quickstart.md`

**Checkpoint finale**: `uv run pytest -m "not cloud"` verde (baseline 204+2xfail + nuovi); `uv run pytest tests/unit/test_assets_sync.py` verde; `uv run pytest packages/sertor/tests/ -m "not cloud"` verde; `sertor install wiki` su tmp repo vuoto → SC-001..SC-008 verificati.

---

## Grafo delle Dipendenze

### Dipendenze tra fasi

```
Phase 1 (Setup workspace)
    └─► Phase 2 (Foundational: modelli, assets, resources)
            └─► Phase 3 (US1: install repo vuoto — MVP)
            │       └─► Phase 4 (US2: non-distruttività)
            │                   └─► Phase 5 (US3: governo CLI)
            │                               └─► Phase 6 (Polish)
            └─► Phase 6 (Polish: test sync, assets → .claude)
```

### Dipendenze tra user story

- **US1 (P1)**: dipende da Phase 2 completata. Nessuna dipendenza da US2/US3.
- **US2 (P2)**: dipende da US1 (condivide artefatti: `install_wiki.py`, `claude_md.py`, `settings_merge.py`). Non dipende da US3.
- **US3 (P3)**: dipende da US1 per il backbone CLI (`__main__.py`). Può iniziare in parallelo a US2 sui task non conflittuali (T026/T027/T028 vs T022/T023/T024).
- **Phase 6 (Polish)**: dipende da US1/US2/US3 completate.

### Dipendenze interne a US1

```
T006 (artifacts.py) ─┐
T007 (report.py)     ├─► T017 (install_wiki.py) ─► T018 (__main__.py) ─► T019/T020
T008/T009/T010/T011  │         ▲
T012 (resources.py)  ─┘        │
T013 (package-data)            │
T014 (config_gen.py) ──────────┘
T015 (claude_md.py) ──────────►┘
T016 (settings_merge.py) ─────►┘
```

`T008..T013` e `T014..T016` sono **parallelizzabili** tra loro (file diversi, no dipendenze incompleti).
`T017` dipende da tutti i precedenti. `T018` dipende da `T017`. Test (`T019..T021`) dopo `T018`.

---

## Parallelismo: esempi per storia

### Phase 2 — Parallel batch (nessuna dipendenza reciproca)

Possono girare contemporaneamente:
- T008 (ripulitura skill wiki-author)
- T009 (comandi/agente/hook)
- T010 (settings.hooks.json + claude-md-block.md)
- T011 (wiki.config.toml.tmpl)

T006, T007, T012, T013 vanno in serie (fondamenta: artifacts → resources → package-data).

### Phase 3 (US1) — Parallel batch dopo T006-T013

Possono girare contemporaneamente:
- T014 (config_gen.py)
- T015 (claude_md.py)
- T016 (settings_merge.py)

Poi in serie: T017 (install_wiki.py, dipende da T014-T016) → T018 (__main__.py) → T019/T020/T021.

### Phase 4 (US2) e Phase 5 (US3) — Sovrapposizione parziale

Dopo T018, possono iniziare in parallelo:
- **Stream US2**: T022 (claude_md esteso) → T023 → T024 → T025
- **Stream US3**: T026 (stub help) → T027/T028 (paralleli) → T029

---

## Criteri di Test Indipendenti per Storia

### US1 — Repo vuoto

- `sertor install wiki` su `tmp_path` vuota → exit code 0
- Tutti gli artefatti attesi presenti nel filesystem: `.claude/skills/wiki-author/` (14 file), `.claude/commands/wiki.md`, `.claude/agents/wiki-curator.md`, `.claude/hooks/wiki-pending-check.ps1`, `.claude/settings.json` (con le 3 voci hook), `CLAUDE.md` (con blocco marker), `wiki.config.toml`, `wiki/` (cartelle tassonomia + index.md + log.md)
- Report stdout: tutti gli esiti `created`, riepilogo corretto
- `wiki.config.toml` supera `sertor_core.wiki_tools.profile.load_profile(Path("wiki.config.toml"))`
- `sertor-wiki-tools scan --config wiki.config.toml` → exit 0 (SC-008)
- `grep -ri "sertor" <artefatti>` con whitelist → zero match (SC-004, anticipato da T032)
- Nessun processo di rete, LLM, indicizzazione avviato (SC-005): verificabile con mock/assert del modulo

### US2 — Repo pre-popolato

- `CLAUDE.md` pre-esistente con contenuto utente arbitrario → fuori dai marker: byte-per-byte identico dopo il run
- `.claude/settings.json` con hook utente preesistente → tutte le voci utente ancora presenti dopo il merge
- `wiki.config.toml` pre-esistente → non toccato (MD5/hash prima = MD5/hash dopo)
- Skill parziale (alcuni file presenti) → file esistenti non sovrascritti (hash identico), file mancanti creati
- Doppio run → stato filesystem identico, report tutto `skipped`/`merged`(0 voci), exit 0 (SC-003)
- `settings.json` malformato → exit 1, file non toccato, `failed_step` valorizzato nel report

### US3 — Governo CLI

- `sertor --help` → exit 0, output contiene `install`
- `sertor install --help` → exit 0, output contiene `wiki`, `rag` (pianificato), `governance` (pianificato)
- `sertor install rag` → exit 1, messaggio leggibile «non disponibile»
- `sertor sottocomando_ignoto` → exit 2
- `sertor install wiki --target <tmp>` → artefatti sotto `<tmp>`, non sotto cwd
- `sertor install wiki --language it` → `wiki.config.toml` ha `language = "it"`
- `sertor install wiki --source-dirs src,docs` → toml ha `source_dirs = ["src", "docs"]`
- `sertor install wiki --target /path/inesistente` → exit 1, zero artefatti scritti

---

## Strategia di Implementazione

### MVP (User Story 1 — Phase 1+2+3)

1. Completare Phase 1: workspace + struttura pacchetto (T001-T005)
2. Completare Phase 2: assets ripuliti, modelli, resources (T006-T013)
3. Completare Phase 3: US1 install repo vuoto (T014-T021)
4. **STOP e VALIDA**: `sertor install wiki` su repo vuoto → SC-001..SC-006 verificati; dogfood SC-008
5. Demo dimostrabile: il sistema-wiki si installa su qualunque repo con un solo comando

### Incrementale

1. Phase 1+2+3 → MVP operativo (sopra)
2. Phase 4 (US2) → garanzia non-distruttività: l'installer diventa sicuro su progetti reali
3. Phase 5 (US3) → governo completo: `--target`, `--language`, `--source-dirs`, stub leggibili
4. Phase 6 (Polish) → test di guardia drift + dogfood definitivo; baseline suite invariata

### Note architetturali

- **Fallback packaging (D1 alt. b)**: se il workspace `uv` risulta problematico al T001, il fallback è `sertor_installer` come modulo aggiuntivo dentro il wheel `sertor-core` (research D1 alt. (b)) — ma richiede deroga esplicita a REQ-100 registrata in Complexity Tracking di `plan.md`. Valutare in T001 prima di procedere con T002+T003.
- **Test di sync T031**: il test confronta assets ↔ `.claude/` e tollera le differenze ammesse (vedi D3: `uv run sertor-wiki-tools` nel derivato è differenza accettata). Documentare l'allowlist nel test.
- **T008 è il task più laborioso** della fase: ~14 file, ~28 occorrenze da riformulare. Parallelizzabile col resto di Phase 2 solo per i file non-skill (T009-T011).

---

## Note

- `[P]` = file diversi, nessuna dipendenza incompleta: eseguibile in parallelo
- `[US1/US2/US3]` mappa il task alla user story per tracciabilità
- Ogni fase è un incremento indipendente e testabile
- Commit suggeriti: dopo ogni fase completata (Checkpoint verde)
- La suite di base (204 passed + 2 xfail + 1 deselected = 207 raccolti) NON deve regredire: verificare a T034
- `packages/sertor/tests/` ospita i test della feature; `tests/unit/test_assets_sync.py` è l'unico test cross-pacchetto che va nella root suite (T031)
