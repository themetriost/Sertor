# Contract — CLI surface (`sertor-wiki-tools`)

Entry-point sottile: `python -m sertor_core.wiki_tools <op> [opzioni]` (equivalente al console-script
`sertor-wiki-tools <op> ...`). Tutte le operazioni accettano `--config` e `--json`. **Zero LLM, offline.**

## Opzioni comuni

| Opzione | Default | Descrizione |
|---|---|---|
| `--config <path>` | `./wiki.config.toml` | percorso del profilo dell'ospite (TOML) |
| `--root <path>` | da config | override della radice del progetto-ospite (stile Transcriptio `--root`) |
| `--json` | off | emette il contratto JSON su stdout (altrimenti output umano sintetico) |

**Exit code**: `0` ok · `1` errore esplicito (es. `ConfigError`: config assente/malformata) — messaggio su stderr.

## Operazioni

| Comando | Cosa fa | Output (con `--json`) | Requisiti |
|---|---|---|---|
| `scan` | conta i file-sorgente più recenti dell'ultima voce di registro (mtime) | `wiki.scan/1` | FR-005 |
| `structure init` | crea la struttura del wiki da config, idempotente, non-distruttiva | `wiki.structure/1` | FR-003 |
| `validate` | valida le convenzioni delle pagine (frontmatter/wikilink/naming/area) | `wiki.lint/1` (sezione `missing_frontmatter` + naming) | FR-004 |
| `lint` | lint strutturale: link rotti, orfani, frontmatter mancante | `wiki.lint/1` | FR-006 |
| `collect` | enumera le pagine + metadati (mappa, senza corpo) | `wiki.collect/1` | FR-007 |
| `index` | (US5) indicizza il wiki in collezione separata, rigenerabile | `wiki.index/1` (no-op se `rag.enabled=false`) | FR-010 |

> `validate` e `lint` condividono lo schema `wiki.lint/1` (validate = sottoinsieme convenzioni; lint = struttura completa).
> Le mechanics di registro/index (append voce, inserisci link+summary) sono esposte come funzioni di libreria
> (`registry.py`) consumate dalla metà LLM; non hanno un sottocomando CLI proprio nell'MVP (FR-008).

## Esempi

```bash
# scan su Sertor (profilo di default)
uv run sertor-wiki-tools scan --config wiki.config.toml --json
# → {"schema":"wiki.scan/1","pending":3,"anchor":"2026-06-05T10:00:00","dirs_scanned":["src","specs"],"message":"..."}

# lint strutturale
uv run sertor-wiki-tools lint --config wiki.config.toml --json

# stessa operazione su un ospite finto doc-only (prova Principio X / SC-001)
uv run sertor-wiki-tools scan --config tests/fixtures/doc_only_host/wiki.config.toml --json
```

## Invariante host-agnostico (Principio X)
Nessun comando contiene path o nomi dell'ospite: tutto deriva da `--config`/`--root`. Lo stesso binario gira su
qualsiasi ospite cambiando solo il file di config (SC-001).
