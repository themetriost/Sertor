# Quickstart — Verifica della feature 016 (igiene radice host)

**Data**: 2026-06-13 · **Branch**: `016-igiene-radice-host`

Come dimostrare i criteri di successo, senza rete dove possibile.

---

## SC-001 — Radice host minima dopo l'install

Su un repo ospite pulito di prova:

```
sertor install wiki --target <host>
sertor install rag  --target <host> --backend local --no-deps
```

Verifica: la radice di `<host>` contiene **solo** `.claude/`, `CLAUDE.md`, `wiki/`, `.gitignore`,
`.mcp.json` (scope project) e `.sertor/`. Nessun `wiki.config.toml` in radice (è in `wiki/`).
La guardia di test (D2) lo verifica sul piano: nessun artefatto runtime con `target_rel` in radice
oltre `.mcp.json`/`.gitignore`.

## SC-002 — Wiki autocontenuto, invocazioni senza intervento manuale

Con `wiki.config.toml` in `wiki/`:

```
cd <host>
sertor-wiki-tools scan --json          # auto-discovery: trova wiki/wiki.config.toml, root = CWD
sertor-wiki-tools collect --json
sertor-wiki-tools lint --json
```

Tutte completano risolvendo i path (source_dirs, wiki root) dalla radice host. Equivalente esplicito:
`--config wiki/wiki.config.toml --root .`.

## SC-003 — Scope MCP local: niente file nel repo

```
sertor install rag --target <host> --mcp-scope local --no-deps
```

Verifica: **non** esiste `<host>/.mcp.json`; `claude mcp get sertor-rag` lo trova registrato. Nei test
unit: `FakeCommandRunner` registra la chiamata `claude mcp add-json … --scope local` e l'assenza di
scrittura file.

## SC-004 — Sertor stesso (dogfood) dopo lo spostamento one-shot

```
uv run pytest packages/sertor/tests/test_host_agnostic.py   # sync asset → .claude/ verde
uv run sertor-wiki-tools scan --json                        # da radice repo Sertor, auto-discovery
```

`wiki/wiki.config.toml` esiste; nessun `wiki.config.toml` in radice repo. Il hook
`.claude/hooks/wiki-pending-check.ps1` punta a `wiki/wiki.config.toml`.

## SC-005 — Scope local non realizzabile: fail-fast, nessun file silenzioso

Con `claude` non sul PATH:

```
sertor install rag --target <host> --mcp-scope local --no-deps
```

Verifica: exit 1, messaggio leggibile + comando manuale; `<host>/.mcp.json` **non** creato. Nei test:
`FakeCommandRunner(is_available=False)` → `McpRegistrationError`, nessuna scrittura.

## SC-006 — Idempotenza della collocazione

Ripetere gli install: nessun nuovo file di tooling in radice; `wiki/wiki.config.toml` → `skipped`;
scope local già registrato → `skipped`.
