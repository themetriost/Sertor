# Contract — hook portabile (Phase 1)

Il contratto esterno non è una nuova API: è l'**equivalenza osservabile** tra ogni hook portabile e il
`.ps1` che sostituisce, più l'invocazione OS-indipendente. Qui i contratti verificabili.

## C1 — Invocazione portabile (FR-001/010)

**Contratto:** ogni hook è invocato via **`uv run --no-project python <root>/.claude/hooks/<name>.py
[--assistant <a>] [args]`**, senza dipendenza da `pwsh`/`bash` né da una shell Windows-only.
- `--no-project` isola dall'eventuale `pyproject.toml` dell'host.
- Il wiring (Claude `settings.json`, Copilot) non contiene `"shell":"powershell"` per questi hook.
- **Test:** il piano d'install per Claude/Copilot produce un comando che invoca `uv run --no-project
  python` (asserzione sul wiring generato); `git grep` non trova `"shell": "powershell"` per gli 8 hook.

## C2 — Parità di output per-assistente (FR-003, SC-002) — GATE pre-merge

**Contratto:** con evento+input simulati, stdout del portabile == contratto atteso, per **Claude** e
**Copilot**:
- SessionStart → `additionalContext` (Claude) / equivalente nativo (Copilot);
- Stop/SessionEnd `agentStop` → `decision: allow` **non-bloccante**;
- PreToolUse → **fail-open** (nessun payload `deny` su stdout; eventuale warn su stderr).
- **Test:** per ogni (hook × assistente), asserzione byte/campo sull'output. **Bloccante per il merge.**

## C3 — Parità di effetti di stato (FR-002, SC-001)

**Contratto:** i file di stato scritti hanno **path e schema invariati**:
- `rag-freshness` → `.sertor/.rag-health.json` (`rag.health/1`);
- `version-check` → `.sertor/.version-check.json`;
- errore → `.sertor/.last-hook-error` (`hook.error/1`).
- **Test:** eseguito l'hook con input simulati (rete mockata per version-check), il file atteso esiste con
  lo schema atteso.

## C4 — Fail-safe (FR-004/005/007, SC-003)

**Contratto:**
- exit `0` **sempre** (anche su eccezione interna); la sessione non è mai bloccata;
- `PreToolUse` **fail-open**;
- stdin rediretto/assente → **nessun blocco** (`sys.stdin` non letto in modo bloccante);
- su errore → breadcrumb `.last-hook-error` **senza segreti**.
- **Test:** inietta un errore → l'hook esce 0 e scrive il breadcrumb (senza contenuti sensibili); stdin
  chiuso → l'hook non si appende.

## C5 — Detach cross-OS (FR-006)

**Contratto:** `rag-freshness` avvia il re-index in un worker **detached** (POSIX `start_new_session`,
Windows `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP`, stdio→DEVNULL) e **ritorna subito**; nessun blocco
della chiusura sessione, nessun zombie.
- **Test:** l'invocazione ritorna in tempo trascurabile; il worker è disaccoppiato dal parent (verifica
  della non-attesa; smoke per-OS in CI).

## C6 — Portabilità reale (SC-001/005) — smoke CI matrice

**Contratto:** su **ubuntu** (senza `pwsh`) e **windows**, ogni hook eseguito via `uv run --no-project
python` **completa exit 0** con gli effetti attesi. 0 `.ps1` residui per gli 8; 0 dip nuove.

## C7 — Core invariato + gate (SC-006)

**Contratto:** `git diff --stat src/sertor_core/` = **vuoto**; suite `-m "not cloud"` + `ruff` verdi
pre-merge; nessuna regressione Windows nei test.

## Mappa contratto → criteri

| Contratto | Copre |
|-----------|-------|
| C1 | FR-001/010, SC-005 |
| C2 | FR-003, SC-002 (parità output, gate) |
| C3 | FR-002, SC-001 (parità stato) |
| C4 | FR-004/005/007, SC-003 (fail-safe) |
| C5 | FR-006 (detach) |
| C6 | SC-001/004/005 (portabilità reale) |
| C7 | FR-009, SC-006 (core invariato) |
