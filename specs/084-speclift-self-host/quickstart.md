# Quickstart — Dogfooding di SpecLift nel repo Sertor

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

Come generare requisiti EARS ancorati dai changeset reali di Sertor, una volta vendorato
`packages/speclift`. Comandi **PowerShell** (Windows), dalla **root** del repo Sertor.

## Prerequisiti

1. Workspace sincronizzato: `uv sync --all-packages --extra dev`
2. **Indice RAG di Sertor costruito e fresco** (SpecLift lo *consuma*, non lo costruisce):
   ```powershell
   uv run sertor-rag index .
   ```
   Se l'indice manca, SpecLift fallisce **fail-loud** con **exit 3** e raccomanda proprio questo comando.

## Ciclo a due marce (il "sandwich deterministico")

### Marcia 1 — emetti il fascicolo di evidenza (deterministica)

```powershell
uv run speclift bundle <ref> --out $env:TEMP/speclift-evidence
```

- `<ref>` = un commit/sha/ref, oppure `--range A..B`, oppure `--staged` (default `HEAD`).
- Produce `$env:TEMP/speclift-evidence.bundle.json`: per ogni item, `index` + àncora (`file`/`lines`/
  `symbol?`/`test?`/`granularity`) + `diff` da descrivere.
- Filtro sorgenti **sempre attivo**: `specs/`, `requirements/`, `.specify/` esclusi (circolari); doc
  esclusa salvo `--include-docs`. Gli esclusi sono in `excluded_sources` (trasparenza).

### Marcia 2 — l'agente scrive le frasi EARS (l'unico stadio di giudizio)

L'agente ospite (via la skill `speclift`, `.claude/skills/speclift/SKILL.md`) legge il bundle e scrive
`speclift-authored.json`, agganciando ogni frase a un item **per indice** (mai un'àncora nuova):

```json
{
  "changeset_ref": "<lo stesso del bundle>",
  "requirements": [
    { "item": 0, "quota": "user_capability", "statement": "WHEN …, the system SHALL …." },
    { "item": 0, "quota": "behaviour",       "statement": "WHILE …, the … SHALL …." },
    { "item": 0, "quota": "implementation",  "statement": "The … SHALL call `symbol()` …." }
  ],
  "open_questions": ["…lacune…"]
}
```

### Marcia 2 — assembla e riverifica (il "moat", deterministica)

```powershell
uv run speclift assemble `
  --bundle $env:TEMP/speclift-evidence.bundle.json `
  --authored $env:TEMP/speclift-authored.json `
  --out $env:TEMP/speclift-report
```

Produce `…speclift-report.speclift.json` (canonico) + `.speclift.md` (vista). La CLI **riverifica ogni
àncora sul filesystem** di Sertor: ciò che non regge finisce in `excluded` con motivo — **mai scartato
in silenzio**.

## Verifica del self-host (mappa ai criteri di successo)

| Verifica | Comando | Criterio |
|----------|---------|----------|
| gira nel repo Sertor | `uv run speclift bundle HEAD --out $env:TEMP/e` → bundle non vuoto con path Sertor reali | CS-1 |
| report riverificato | `uv run speclift assemble …` → report con àncore verificate | CS-2 |
| core invariato | `git diff -- src/sertor_core pyproject.toml` = vuoto | CS-3 |
| test verdi | `uv run pytest packages/speclift/tests -m "not cloud"` | CS-4 |
| nessun ciclo | `uv sync --all-packages` risolve pulito | CS-5 |
| fail-loud azionabile | esegui bundle **senza** indice → exit 3 + rimedio `sertor-rag index .` | CS-6 |
| provenienza + onestà | `packages/speclift/VENDORING.md` presente; doc dichiara il legame = 1 solo comando CLI | CS-7 |

## Nota di onestà (Gruppo H)

Il legame runtime reale di SpecLift con Sertor è **un solo comando**:
`sertor-rag search --type code --json`. SpecLift **non** usa i tool MCP di navigazione del code-graph
(`find_symbol`/`who_calls`), nonostante l'handoff/wiki Sinthari li descrivano. La localizzazione è solo
`search`; la verifica delle àncore è **deterministica sul filesystem**.
