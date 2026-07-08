# Research — portabilità hook (Phase 0)

Ground truth: wiring attuale (`assets/rag/settings.*.json`), gli 8 `.ps1` (comportamento), `install_wiki.py`
(no runtime `.sertor/`), meccanismo `uv run`. Risolve DA-2/3/4 (DA-1 è lock: sostituzione + parità-gate).

## D1 — Interprete & invocazione portabile (DA-2)

- **Decisione:** wire ogni hook come **`uv run --no-project python <hookpath>`**.
- **Rationale:**
  - **`uv` è garantito**: è il percorso d'installazione di Sertor (uv/uvx) → presente su ogni OS; fornisce
    (o auto-provisiona) Python cross-platform → **nessuna dipendenza da `pwsh`/`bash`**.
  - **`--no-project` è essenziale:** senza, `uv run python` in un host che ha un **proprio `pyproject.toml`**
    attiverebbe l'env del progetto ospite (sbagliato, potenzialmente lento/fallace). `--no-project` esegue
    un Python **isolato**, ignorando il progetto dell'host.
  - **Non dipende da `.sertor/.venv`** per lo *script* dell'hook → funziona anche per l'install **wiki-only**
    (che non crea il runtime — vedi D2). Gli hook che usano il RAG chiamano `uv run --project .sertor
    sertor-rag …` **internamente** (Principio XI), raggiunto solo sugli install RAG.
- **Wiring:** il comando **non** usa più `"shell":"powershell"`. Il path dell'hook si risolve via
  `CLAUDE_PROJECT_DIR` (Claude lo esporta) o cwd=project-dir; l'hook Python può anche **auto-localizzarsi**
  (`os.environ["CLAUDE_PROJECT_DIR"]` con fallback `.`). Forma comando (da fissare in implement, verificata
  cross-shell): `uv run --no-project python <root>/.claude/hooks/<name>.py [args]`.
- **Alternative scartate:** (a) `.sertor/.venv/{bin,Scripts}/python` — OS-path-dependent e assente su
  wiki-only; (b) system `python3` — non garantito; (c) `uv run python` senza `--no-project` — cattura il
  progetto ospite; (d) varianti `.sh`+`.ps1` — è proprio il doppio-binario che eliminiamo (NFR-1).

## D2 — Interprete per gli hook wiki su install wiki-only (DA-3)

- **Fatto:** `install_wiki.py` **non** crea il runtime `.sertor/` (verificato: nessun `uv add`/venv). I 2
  hook wiki (`wiki-pending-check`, `wiki-session-start`) fanno solo I/O di file (mtime, lettura contesto) →
  **non** servono `sertor-rag` né `.sertor/.venv`.
- **Decisione:** `uv run --no-project python` (D1) risolve il caso: fornisce Python **senza** `.sertor/`.
  Gli hook wiki girano con esso su qualunque install.
- **Degrado (FR-011):** un hook che **richiede** il RAG runtime (es. `rag-freshness`) ma lo trova assente
  (config anomala) → **fail-safe**: breadcrumb + exit 0, nessun crash. Il check «runtime presente» è
  esplicito nel corpo dell'hook.

## D3 — Contratto di output per-assistente preservato (FR-003)

- **Fatto:** i `.ps1` emettono per-assistente via `-Assistant` (Claude: JSON su stdout con
  `additionalContext`/`decision`; Copilot: formato nativo `additionalContext`/`decision:allow`/preToolUse
  fail-open). SessionStart Claude = `additionalContext`; agentStop = `decision:allow` non-bloccante;
  PreToolUse = fail-open (warn su stderr, niente payload deny su stdout).
- **Decisione:** ogni hook Python replica **esattamente** questi output, parametrico sull'assistente (arg/env
  `--assistant` come oggi). La **verifica di parità** (D5) asserisce byte-per-byte questi output.

## D4 — Detach cross-OS del worker re-index (FR-006)

- **Fatto:** `rag-freshness.ps1` usa `Start-Process` per lanciare un worker detached che re-indicizza,
  così SessionEnd non si blocca.
- **Decisione:** in Python, **`subprocess.Popen`** del worker con **detach cross-OS**: su POSIX
  `start_new_session=True` (nuovo process group, sopravvive al parent); su Windows `creationflags`
  `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`. stdin/stdout/stderr rediretti a `DEVNULL`. Il parent
  ritorna subito (non-bloccante). Il worker esegue `uv run --project .sertor sertor-rag index .` + `doctor`
  e scrive `.rag-health.json` (come oggi).
- **Rationale:** stdlib, portabile; nessun processo zombie (session detach) né blocco.

## D5 — Verifica di parità = gate pre-merge (DA-4)

- **Decisione:** **test offline per-hook** (pytest, no rete salvo il caso version-check che si mocka):
  per ciascun hook si simula l'**evento** (input su stdin nel formato che l'assistente passa) e si
  asserisce (a) l'**output** per-assistente (stdout, per Claude e Copilot) e (b) gli **effetti di stato**
  (file `.sertor/*` scritti nello schema atteso) **coincidono** col contratto (il comportamento dei `.ps1`
  come riferimento documentato). + **smoke CI su matrice** (ubuntu + windows) che esegue ogni hook e
  verifica exit 0 + assenza di crash (i Python-hook **non** richiedono `pwsh` → girano su ubuntu, a
  differenza dei `.ps1`).
- **Gate:** la suite di parità è **bloccante** per il merge (SC-002). I `.ps1` **non** girano in CI (ubuntu
  può non avere `pwsh`): il loro comportamento è il **riferimento** codificato nei test, non un run.
- **Rationale:** offline+deterministico per il grosso (V, F.I.R.S.T.); lo smoke matrice prova la
  portabilità reale dell'esecuzione.

## D6 — Ritiro dei `.ps1` e nota `pwsh` (FR-012, DA-1 lock)

- **Decisione:** a parità verde, **rimuovere** gli 8 `.ps1` dal bundle e dal dogfood (`.claude/hooks`),
  aggiornare il wiring a `uv run --no-project python …`, e **aggiornare la nota `pwsh`-unavailability**
  (E10-FEAT-018 `host_env.py`): non è più precondizione per l'operatività degli hook (rimuovere/riformulare;
  la logica detect-only può restare per altri usi ma non gate degli hook). Le **guardie di sync**
  dogfood↔bundle si aggiornano al nuovo insieme (`.py` invece di `.ps1`).
- **Migrazione (edge):** `sertor upgrade` deve **riconciliare il wiring** (rimuovere le voci `settings.json`
  che puntano ai `.ps1` rimossi e mettere quelle nuove) — nessun wiring orfano.

## Sintesi

| # | Tema | Decisione |
|---|------|-----------|
| D1 | Invocazione (DA-2) | `uv run --no-project python <hook>` — isolato dall'host, no `.sertor/` per lo script, no pwsh |
| D2 | Wiki-only (DA-3) | risolto da D1; hook che richiedono runtime → degrado fail-safe (FR-011) |
| D3 | Output per-assistente | replicato esatto (Claude/Copilot), asserito dalla parità |
| D4 | Detach (FR-006) | `subprocess.Popen` + `start_new_session`(POSIX)/`DETACHED_PROCESS`(Win), stdio→DEVNULL |
| D5 | Parità (DA-4) | test offline per-hook (output+stato) + smoke CI matrice; **gate pre-merge** |
| D6 | Ritiro `.ps1` + nota pwsh | rimuovi `.ps1`, aggiorna wiring + nota E10-FEAT-018 + guardie sync + upgrade riconcilia wiring |

Nessuna NEEDS CLARIFICATION residua → Phase 1.
