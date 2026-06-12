# Contract — `sertor install rag` (CLI)

Contratto di superficie del sottocomando. Stessa grammatica di `sertor install wiki`
(`__main__.py`): layer sottile argparse → funzioni dell'installer → report. Exit `0/1/2`.

## Sintassi

```
sertor install rag [--target PATH] [--backend {azure|local}] [--corpus NAME]
                    [--no-graph] [--no-rerank] [--no-deps] [--json]
```

## Opzioni

| Flag | Default | Effetto |
|---|---|---|
| `--target PATH` | cwd | Radice del repo ospite. Inesistente/non-dir → errore (exit 1, FR-002). |
| `--backend {azure\|local}` | `azure` | Backend embeddings → set di extra e template `.env` (FR-003/009). |
| `--corpus NAME` | nome dir target (sanitizzato) | `SERTOR_CORPUS` nel `.env` e nell'env del server (FR-004). |
| `--no-graph` | (incluso) | Esclude l'extra `graph` (FR-004/009). |
| `--no-rerank` | (incluso) | Esclude l'extra `rerank` (FR-004/009). |
| `--no-deps` | (esegue) | Salta il bootstrap dipendenze; solo scaffold config (FR-004/007). |
| `--json` | (umano) | Report come JSON `install.report/1` (FR-004/022). |

## Comportamento (sequenza)

1. Valida `--target` (FR-002). Costruisce `RagInstallOptions` + `RagHostProfile`.
2. Se `--no-deps` non impostato: verifica `uv` disponibile (assente → exit 1 leggibile, FR-012);
   crea `<target>/.sertor/` ed esegue `uv init --bare` (se manca pyproject) + `uv add
   "sertor-core[<extras>] @ git+url"` dentro `.sertor/` (FR-007/008). Mai indicizza (FR-011).
3. Scrive/merge `<target>/.sertor/.env` (template per backend, segreti vuoti, merge additivo,
   FR-014/015/016).
4. Scrive/merge `<target>/.mcp.json` in **radice** (server `sertor-rag` via `uv run --directory
   .sertor python -m sertor_mcp.server`, env del corpus; merge additivo, FR-017/018).
5. Append dedup in `<target>/.gitignore` (FR-019).
6. Stampa `InstallReport` (umano o `--json`), exit secondo gli esiti.

## Artefatti prodotti (esempio, `--backend azure`, target `MyApp`)

```
MyApp/
├─ .sertor/
│  ├─ pyproject.toml         # uv init --bare  (created)
│  ├─ uv.lock / .venv/       # uv add          (created)
│  └─ .env                   # template azure, segreti vuoti (created/merged)
├─ .mcp.json                 # server sertor-rag (created/merged)  ← radice
└─ .gitignore                # + .sertor/.venv/ .sertor/.index* .sertor/.env (merged)
```

### `.env` generato (azure) — segreti vuoti
```
RAG_BACKEND=azure
SERTOR_STORE_BACKEND=local
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large
SERTOR_CORPUS=myapp
SERTOR_EXCLUDE_PATTERNS=.venv,venv,env,node_modules,__pycache__,.pytest_cache,.ruff_cache,.mypy_cache,dist,build,target,bin,obj,out,.index,chroma,.idea,.vscode,*.key,*.pem,.env,.sertor
```
> `SERTOR_EXCLUDE_PATTERNS` ri-elenca i default del core **+ `.sertor`** (il core sostituisce i
> default quando la variabile è presente). Il backend `local` sostituisce le chiavi Azure con
> `OLLAMA_HOST=http://localhost:11434`.

### `.mcp.json` (frammento del server, merge additivo)
```json
{
  "mcpServers": {
    "sertor-rag": {
      "command": "uv",
      "args": ["run", "--directory", ".sertor", "python", "-m", "sertor_mcp.server"],
      "env": { "SERTOR_CORPUS": "myapp" }
    }
  }
}
```

## Exit code
- `0` — successo, incluso re-run idempotente (tutti `skipped`/`merged`).
- `1` — errore di dominio: target invalido · `uv` assente · `uv add` fallito · file di config
  malformato (es. `.mcp.json`/`.env` non parsabili) → report con `failed_step`.
- `2` — errore d'uso (argparse: flag/valori non validi, es. `--backend foo`).

## Invarianti verificabili (mappano i SC della spec)
- Dopo un run riuscito senza `--no-deps`: `.sertor/` con dipendenze + `.env`/`.mcp.json`/`.gitignore`
  presenti e coerenti (SC-001).
- Nessun indice creato (SC-002). Re-run → stato identico, 0 duplicati (SC-003).
- `.env`: chiavi `*_API_KEY` vuote (SC-004). `--backend local` ≠ chiavi azure (SC-006).
- Target non-Python: sorgenti host immutati, novità confinata in `.sertor/` (+ root config) (SC-007).
