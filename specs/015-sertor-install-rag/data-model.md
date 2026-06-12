# Data Model — `sertor install rag`

Entità di dominio dell'installer per il taglio `rag`. Value object puri (nessun import SDK,
Principio I), riuso massimo del data-model di `install wiki`. Riferimenti: `artifacts.py`,
`report.py`, `config_gen.py`.

## §1. Entità riusate INVARIATE (da `install wiki`)

- **`Artifact(kind, source, target_rel, strategy)`** — `target_rel` validato relativo
  (no path-traversal). Riusato; si aggiungono valori a `kind`/`strategy` (§2).
- **`ArtifactOutcome(target_rel, outcome, detail)`** — esito per artefatto. Invariato.
- **`Outcome`** = `CREATED | SKIPPED | MERGED | BLOCK | ERROR`. Invariato (per il RAG si usano
  `CREATED`/`SKIPPED`/`MERGED`/`ERROR`; `BLOCK` resta specifico del marker wiki).
- **`InstallReport(target, outcomes, created, skipped, merged, block, errors, failed_step)`** —
  conteggi + `exit_code()` (0 se nessun errore, 1 altrimenti) + `render_human()`/`render_json()`
  (schema `install.report/1`). Invariato. L'exit `2` (uso) resta gestito da argparse in `__main__`.

## §2. Estensioni agli enum (`artifacts.py`)

`ArtifactKind` aggiunge:

| Valore | Significato |
|---|---|
| `DEPENDENCIES` | bootstrap del progetto Python in `<target>/.sertor/` (uv init + uv add) |
| `ENV_MERGE` | scrittura/merge additivo di `<target>/.sertor/.env` |
| `MCP_MERGE` | scrittura/merge additivo di `<target>/.mcp.json` (radice host) |
| `GITIGNORE_APPEND` | append dedup di righe nel `<target>/.gitignore` (radice host) |

`WriteStrategy` aggiunge: `BOOTSTRAP_DEPS`, `MERGE_ENV`, `MERGE_JSON`, `APPEND_LINES`.

> Coerenza: ogni `Artifact` continua a "conoscere la propria regola di non-distruttività" (la
> `WriteStrategy`). I nuovi `kind` sono additivi: il dispatch in `execute_plan` cresce di 4 rami.

## §3. Nuove entità della feature

### `RagInstallOptions` (input normalizzato del comando)
Frozen dataclass costruita dal parsing argparse:
- `target_root: Path` — radice host (da `--target`, default cwd; validata esistente/dir).
- `backend: str` — `"azure" | "local"` (da `--backend`, default `azure`).
- `corpus: str` — da `--corpus`; default = nome sanitizzato di `target_root.name`.
- `include_graph: bool` / `include_rerank: bool` — da `--no-graph`/`--no-rerank` (default True).
- `with_deps: bool` — `not --no-deps` (default True).
- `json_report: bool` — da `--json`.
- *Derivato:* `extras() -> list[str]` = `compose_extras(backend, include_graph, include_rerank)`
  (R5): sempre `mcp`; `azure` solo se backend azure; `graph`/`rerank` salvo opt-out.

### `RagHostProfile` (specificità dell'ospite per il RAG)
Analogo di `HostProfile` del wiki, ma per il RAG:
- `target_root: Path`, `sertor_dir: Path` (= `target_root/".sertor"`), `backend: str`, `corpus: str`,
  `extras: list[str]`, `dist_url: str` (la `git+url` di distribuzione).
Alimenta la generazione dei template (`.env`, frammento `.mcp.json`) e la spec di `uv add`.

### `CommandRunner` (porta per i comandi esterni — R3)
Protocol iniettabile:
- `is_available(tool: str) -> bool` (es. `uv`).
- `run(cmd: list[str], cwd: Path) -> CommandResult` con `CommandResult(returncode, stdout, stderr)`.
Impl reale `SubprocessRunner` (usa `subprocess.run`); test `FakeCommandRunner` (scriptato).
**Non** è una porta del *core* — vive nell'installer (è orchestrazione, non retrieval).

## §4. Piano RAG (analogo di `build_install_plan`)

`build_rag_plan(profile: RagHostProfile, with_deps: bool) -> list[Artifact]` produce l'ordine
canonico:
1. `DEPENDENCIES` (`.sertor/`) — saltato se `with_deps=False`.
2. `ENV_MERGE` → `.sertor/.env`.
3. `MCP_MERGE` → `.mcp.json` (radice).
4. `GITIGNORE_APPEND` → `.gitignore` (radice).

`execute_rag_plan(plan, profile, runner) -> InstallReport` — stesso schema fail-fast no-rollback di
`execute_plan`; ogni ramo ritorna un `ArtifactOutcome`. Il passo `DEPENDENCIES` riflette nel
`detail` il comando `uv` eseguito (NFR-2 osservabilità).

## §5. Regole di validità / invarianti
- `target_rel` di `.mcp.json`/`.gitignore` = `".mcp.json"` / `".gitignore"` (radice, relativi, ok);
  di `.env` = `".sertor/.env"`; il bootstrap opera in `.sertor/` (mai risalente).
- **Idempotenza:** ENV/MCP/GITIGNORE merge additivi (mai sovrascrivono valori/voci esistenti);
  `DEPENDENCIES` si appoggia all'idempotenza di `uv add` (stessa dep → no-op) e salta `uv init` se
  `.sertor/pyproject.toml` esiste.
- **Segreti:** i template `.env` non contengono mai valori per chiavi `*_API_KEY`.
- **install ≠ run:** nessun `kind` indicizza; `DEPENDENCIES` esegue solo `uv init`/`uv add`.
- **exit code:** 0 (successo, anche tutto skipped) · 1 (errore di dominio: `uv` assente, `uv add`
  fallito, target invalido in dominio) · 2 (uso, da argparse).
