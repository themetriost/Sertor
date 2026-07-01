# Quickstart — Dogfooding di SpecLift nel repo Sertor (design MCP-skill)

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

Come generare requisiti EARS ancorati dai changeset reali di Sertor, una volta vendorato
`packages/speclift`. Il retrieval passa dal **server MCP** (tool `search_code`) orchestrato dall'agente
nella skill — **non** dalla CLI `sertor-rag`. Comandi **PowerShell** (Windows), dalla **root** del repo.

## Prerequisiti

1. Workspace sincronizzato: `uv sync --all-packages --extra dev`
2. **Indice RAG di Sertor costruito e fresco** (SpecLift lo *consuma* via l'agente, non lo costruisce):
   ```powershell
   uv run sertor-rag index .
   ```
   Se l'indice manca, il tool MCP `search_code` errerà: l'agente (guidato dalla skill) **si ferma** e lo
   segnala, raccomandando proprio questo comando (fail-loud, non prosegue con evidenza fabbricata).
3. Server MCP `sertor-rag` registrato/attivo (quello del repo, `.mcp.json`).

## Ciclo (tre passi deterministici + due stadi di giudizio dell'agente)

L'agente ospite opera via la skill `speclift` (`.claude/skills/speclift/SKILL.md`).

### 1 — Emetti i candidati da localizzare (deterministico)

```powershell
uv run speclift bundle <ref> --candidates-out $env:TEMP/speclift-candidates.json
```

- `<ref>` = un commit/sha/ref, oppure `--range A..B`, oppure `--staged` (default `HEAD`).
- Esegue `ingest → parse_diff → filter_sources` e scrive la *localization request*: per ogni file
  non-fonte, gli identificatori candidati (+ snippet). **Non tocca il RAG** → funziona anche a indice
  assente. Filtro sorgenti sempre attivo (`specs/`/`requirements/`/`.specify/` esclusi; doc salvo
  `--include-docs`); gli esclusi in `excluded_sources`.

### 2 — Localizza l'evidenza via MCP (giudizio dell'agente)

Per ogni identificatore candidato, l'agente interroga il tool MCP **`search_code`**, mappa gli hit
(`path`/`chunk`) a `Symbol`, giudica quali hit sono test di copertura (`test_*`/`*_test.py`/`/tests/`) →
`TestRef`, e scrive l'artefatto di evidenza (forma `Symbol`/`TestRef`, come il `FakeLocator`):

```json
{
  "changeset_ref": "<lo stesso dei candidati>",
  "symbols": {
    "src/sertor_core/composition.py": [
      { "name": "build_facade", "path": "src/sertor_core/composition.py",
        "line": 0, "kind": "function", "provenance": "src/sertor_core/composition.py#12" }
    ]
  },
  "tests": {
    "build_facade": [
      { "name": "test_build_facade", "path": "tests/unit/test_composition.py",
        "covers_symbol": "build_facade", "provenance": "…#3" }
    ]
  }
}
```

Scrivi in `$env:TEMP/speclift-evidence-input.json`. **Se `search_code` erra (MCP/indice giù), fermati e
segnala** (componente + rimedio `sertor-rag index .`): mai proseguire con evidenza vuota o inventata.

### 3 — Emetti il fascicolo di evidenza (deterministico)

```powershell
uv run speclift bundle <ref> `
  --evidence $env:TEMP/speclift-evidence-input.json `
  --out $env:TEMP/speclift-evidence
```

- Inietta l'`AgentEvidenceLocator` (alimentato dall'evidenza) e completa `locate → bundle`.
- Produce `$env:TEMP/speclift-evidence.bundle.json`: per ogni item, `index` + àncora + `diff` da descrivere.
- **Evidenza malformata/assente → `EvidenceInputError` (exit 6)**, esplicito, nessun fascicolo prodotto.

### 4 — L'agente scrive le frasi EARS (giudizio dell'agente)

L'agente legge il bundle e scrive `speclift-authored.json`, agganciando ogni frase a un item **per indice**
(mai un'àncora nuova):

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

### 5 — Assembla e riverifica (il "moat", deterministico)

```powershell
uv run speclift assemble `
  --bundle $env:TEMP/speclift-evidence.bundle.json `
  --authored $env:TEMP/speclift-authored.json `
  --out $env:TEMP/speclift-report
```

Produce `…speclift-report.speclift.json` (canonico) + `.speclift.md`. La CLI **riverifica ogni àncora sul
filesystem** di Sertor (mai via RAG): ciò che non regge finisce in `excluded` con motivo — **mai scartato
in silenzio**.

## Verifica del self-host (mappa ai criteri di successo)

| Verifica | Comando / azione | Criterio |
|----------|------------------|----------|
| gira nel repo Sertor | candidati → (agente: `search_code`) → `bundle --evidence` → bundle non vuoto con path Sertor reali | CS-1 |
| report riverificato | `speclift assemble …` → report con àncore verificate sul filesystem | CS-2 |
| core invariato | `git diff -- src/sertor_core pyproject.toml` = vuoto | CS-3 |
| test verdi | `uv run pytest packages/speclift/tests -m "not cloud"` | CS-4 |
| nessun ciclo | `uv sync --all-packages` risolve pulito | CS-5 |
| fail-loud azionabile | MCP/indice giù → l'agente si ferma; evidenza malformata → `bundle --evidence` exit 6 | CS-6 |
| provenienza + onestà divergenza | `packages/speclift/VENDORING.md` presente; doc dichiara MCP `search_code` vs CLI vendorata + gap code-graph | CS-7 |
| nessun aggancio CLI | `grep -rn "sertor-rag\|rag_sertor" packages/speclift/src` = 0 | FR-004 |

## Nota di onestà (Gruppo H, invertito)

Il legame runtime del self-host con Sertor è il tool MCP **`search_code`**, orchestrato dall'agente nella
skill — in **divergenza intenzionale dal codice vendorato/upstream** (che usa la CLI `sertor-rag search`,
adapter ora **rimosso**). Questa adozione **non realizza del tutto** la narrativa upstream di navigazione
del code-graph (`find_symbol`/`who_calls`): `search_code` è **ricerca semantica**, non navigazione del
grafo — resta un gap più piccolo e spostato, **dichiarato**. La verifica delle àncore resta **deterministica
sul filesystem**. La divergenza è **feedback registrato a Sinthari** (`wiki/sources/input-other-agents/`).
