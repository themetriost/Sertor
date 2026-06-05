# Quickstart — FEAT-003-D (nucleo wiki deterministico host-agnostico)

## Prerequisiti
- Python ≥ 3.11, `uv`. Nessuna nuova dipendenza (solo stdlib + `sertor-core` esistente).
```bash
uv sync --extra dev
```

## Config dell'ospite
Il comportamento è guidato da `wiki.config.toml` alla radice dell'ospite. Esempio (profilo Sertor):
```toml
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"
[[taxonomy]]
name = "tech"
dir = "tech"
type = "tech"
# … experiments / syntheses / sources …

source_dirs = ["src", "specs", "requirements", ".claude"]
exclude = [".git", ".venv*", "__pycache__", ".ruff_cache", ".pytest_cache", "node_modules", ".index*"]
frontmatter_required = ["title", "type", "tags", "created", "updated"]

[rag]
enabled = true
corpus = "wiki"

[strings]
pending = "Lavoro non ancora registrato nel wiki: {n} file più recenti dell'ultima voce di log."
```

## Uso (CLI)
```bash
# c'è lavoro non registrato? (mtime vs ultima voce di log)
uv run sertor-wiki-tools scan --config wiki.config.toml --json

# lint strutturale (link rotti / orfani / frontmatter mancante)
uv run sertor-wiki-tools lint --config wiki.config.toml --json

# mappa delle pagine (per i consumatori a valle)
uv run sertor-wiki-tools collect --config wiki.config.toml --json

# inizializza la struttura su un progetto senza wiki (idempotente, non-distruttivo)
uv run sertor-wiki-tools structure init --config wiki.config.toml
```

## Prova di host-agnosticità (Principio X / SC-001)
Lo **stesso** comando gira su un ospite diverso cambiando solo la config:
```bash
uv run sertor-wiki-tools scan --config tests/fixtures/doc_only_host/wiki.config.toml --json
# radice 'knowledge/', source-dirs ['docs'], lingua 'en' → output adattato, codice immutato
```

## Verifica
```bash
uv run pytest -m "not cloud" tests/unit/test_wiki_tools_*.py   # unit offline, repo finto in tmp_path
uv run ruff check .                                            # E,F,I,UP,B; line-length 100
```
Atteso: SC-001 (≥2 profili, codice immutato), SC-002 (idempotenza: re-run identico), SC-004 (lint 100% difetti, 0
falsi positivi), SC-005 (zero LLM/offline), SC-006 (non-distruttività).

## Integrazione hook (parte del lavoro)
`.claude/hooks/wiki-pending-check.ps1` diventa un thin wrapper:
```powershell
$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }
$j = uv run sertor-wiki-tools scan --config (Join-Path $d 'wiki.config.toml') --json | ConvertFrom-Json
# mappa $j.pending / $j.message → additionalContext (Stop) o systemMessage (SessionEnd)
```
