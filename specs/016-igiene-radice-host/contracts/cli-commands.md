# Contract — CLI (feature 016)

**Data**: 2026-06-13 · **Branch**: `016-igiene-radice-host`

Delta contrattuali rispetto alle feature 012/015. Due superfici toccate: l'installer `sertor` e il
CLI `sertor-wiki-tools`.

---

## 1. `sertor install rag` — nuovo flag `--mcp-scope`

```
sertor install rag [--target DIR] [--backend {azure,local}] [--corpus NAME]
                   [--no-graph] [--no-rerank] [--no-deps]
                   [--mcp-scope {project,local}]   # NUOVO, default: project
                   [--json]
```

Comportamento:

| `--mcp-scope` | Effetto | Outcome nel report |
|---------------|---------|--------------------|
| `project` (default) | merge additivo di `.mcp.json` in radice host (invariato) | `.mcp.json`: `created`/`merged`/`skipped` |
| `local` | registra `sertor-rag` nel client via `claude mcp add-json … --scope local`; **nessun** file nel repo | `<client mcp registry>`: `created`/`skipped` |

Errori (exit 1, `SertorError`):
- `--mcp-scope local` ma `claude` non disponibile sul PATH → `McpRegistrationError` con messaggio +
  comando manuale; **nessun** `.mcp.json` scritto.
- `claude mcp add` fallito → `McpRegistrationError` (stderr riportato).
- valore di `--mcp-scope` non valido → exit 2 (argparse `choices`).

Idempotenza: re-run con scope local e server già registrato → `skipped` (verifica via
`claude mcp get`/`list` prima dell'add). Scope project → `skipped` (merge esistente).

Invarianza: con `--no-deps` o `--json` il comportamento dello scope MCP è identico.

---

## 2. `sertor-wiki-tools` — auto-discovery del `--config`

Quando `--config` **non** è passato, la risoluzione del file di profilo segue quest'ordine
deterministico (prima corrispondenza vince):

1. `./wiki.config.toml` (retro-compat: config in radice)
2. `./wiki/wiki.config.toml` (nuova collocazione) → se scelto e `--root` assente, `root` = CWD
3. nessuna → `ConfigError` "configurazione del wiki non trovata" (exit 1)

`--config` esplicito **bypassa** la ricerca (comportamento odierno invariato). `--root` esplicito ha
sempre precedenza sull'auto-impostazione del passo 2.

Forma canonica documentata negli asset installati:

```
sertor-wiki-tools <op> --config wiki/wiki.config.toml --root . [--json]
```

equivalente, dalla radice host, a:

```
sertor-wiki-tools <op> [--json]      # via auto-discovery
```

---

## 3. Collocazione prodotta da `install wiki` (delta)

`wiki.config.toml` non è più in radice host ma in `wiki/wiki.config.toml`. Tutti gli asset installati
(skill/comando/agente/hook) e il blocco rituale in `CLAUDE.md` puntano alla nuova sede (o si affidano
all'auto-discovery). Nessun altro cambiamento al set di artefatti di `install wiki`.
