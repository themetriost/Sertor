# Quickstart — Dogfooding di SpecLift nel repo Sertor (three-gear flow reale)

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

Come generare requisiti EARS ancorati dai changeset reali di Sertor, una volta vendorato
`packages/speclift` (da Sinthari `5ee6fc1`, versione pluggable). Il dogfood usa l'**Adapter B**: il
retrieval passa dal tool **MCP `search_code`** orchestrato dall'agente nella skill (Procedura B) — **non**
dalla CLI `sertor-rag`. Comandi **PowerShell** (Windows), dalla **root** del repo.

## Prerequisiti

1. Workspace sincronizzato: `uv sync --all-packages --extra dev`
2. **Indice RAG di Sertor costruito e fresco** (SpecLift lo *consuma* via l'agente, non lo costruisce):
   ```powershell
   uv run sertor-rag index .
   ```
   Se l'indice manca, il tool MCP `search_code` errerà: l'agente (guidato dalla skill, Procedura B) **si
   ferma** e lo segnala, raccomandando proprio questo comando (fail-loud, non prosegue con evidenza
   fabbricata).
3. Server MCP `sertor-rag` registrato/attivo (quello del repo, `.mcp.json`).

## Il three-gear flow (Procedura B della skill upstream)

L'agente ospite opera via la skill `speclift` (`.claude/skills/speclift/SKILL.md`), che sceglie la
**Procedura B** perché l'host Sertor espone i tool MCP ma non una CLI-vehicle `sertor-rag` da subprocess.

### Marcia 0 — Emetti il changeset grezzo (deterministico, no RAG)

```powershell
uv run speclift changeset <ref> --out $env:TEMP/speclift-changeset
```

- `<ref>` = un commit/sha/ref, oppure `--range A..B`, oppure `--staged` (default `HEAD`).
- Esegue `ingest → parse_diff → filter_sources` e scrive `…speclift-changeset.changeset.json`: per ogni
  file non-fonte, gli hunk con `candidate_identifiers` **e** le `lines` del diff (l'agente le legge per
  decidere cosa cercare). **Non tocca il RAG** → funziona anche a indice assente. Filtro sorgenti sempre
  attivo (`specs/`/`requirements/`/`.specify/` esclusi; doc salvo `--include-docs`); gli esclusi in
  `excluded_sources`.

### Passo agente — Localizza l'evidenza via MCP (giudizio dell'agente)

Per ogni hunk, l'agente deriva le query con la **regola G6** (identificatori deduplicati, max
`max_queries_per_symbol`; fallback alla 1ª riga snippet solo se è un identificatore singolo), interroga
il tool MCP **`search_code`** (e, dove utile, `find_symbol`/`who_calls`) per proporre simboli e i test
che li coprono, e scrive `located.json` — chiavi **composite** `"<file_path>::<query>"` per i simboli,
nome-simbolo per i test:

```json
{
  "symbols": {
    "src/sertor_core/composition.py::build_facade": [
      { "name": "build_facade", "path": "src/sertor_core/composition.py",
        "line": 0, "kind": "function", "provenance": "src/sertor_core/composition.py#12" }
    ]
  },
  "tests": {
    "build_facade": [
      { "name": "test_build_facade", "path": "tests/unit/test_composition.py",
        "covers_symbol": "build_facade" }
    ]
  }
}
```

Scrivi in `$env:TEMP/speclift-located.json`. Una chiave che non trovi nulla: **omettila** (o `[]`) — non
inventare un simbolo/test. **Se `search_code` erra (MCP/indice giù), fermati e segnala** (componente +
rimedio `sertor-rag index .`): mai proseguire con evidenza vuota o inventata. Il moat (marcia 2)
scarterà comunque ciò che non regge sul filesystem.

### Marcia 1 — Assembla il fascicolo dal changeset localizzato (deterministico)

```powershell
uv run speclift bundle `
  --changeset $env:TEMP/speclift-changeset.changeset.json `
  --located   $env:TEMP/speclift-located.json `
  --out       $env:TEMP/speclift-evidence
```

- Ricostruisce il changeset, crea un `ProvidedEvidenceLocator(located.json)` (Adapter B), completa
  `locate → bundle`. **Non** passa dall'Adapter A / CLI `sertor-rag`.
- Produce lo **stesso** `…speclift-evidence.bundle.json` del percorso di default: per ogni item, `index`
  + àncora + `diff` da descrivere.
- **Vincoli fail-loud** (upstream): `--changeset`/`--located` incompleti o misti a `<ref>` → exit **2**;
  changeset/located **malformato** → exit **5** (non exit 6), nessun bundle prodotto.

### Passo agente — Scrivi le frasi EARS (giudizio dell'agente)

L'agente legge il bundle e scrive `speclift-authored.json`, agganciando ogni frase a un item **per
indice** (mai un'àncora nuova):

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

### Marcia 2 — Assembla e riverifica (il "moat", deterministico)

```powershell
uv run speclift assemble `
  --bundle   $env:TEMP/speclift-evidence.bundle.json `
  --authored $env:TEMP/speclift-authored.json `
  --repo     . `
  --out      $env:TEMP/speclift-report
```

Produce `…speclift-report.speclift.json` (canonico) + `.speclift.md`. La CLI **riverifica ogni àncora sul
filesystem** di Sertor (mai via RAG): ciò che non regge finisce in `excluded` con motivo — **mai scartato
in silenzio**. Questa marcia è **identica** al percorso di default: non distingue da dove è arrivato il
bundle.

## Verifica del self-host (mappa ai criteri di successo)

| Verifica | Comando / azione | Criterio |
|----------|------------------|----------|
| gira nel repo Sertor | `changeset` → (agente: `search_code`) → `bundle --changeset --located` → bundle non vuoto con path Sertor reali | CS-1 |
| report riverificato | `speclift assemble …` → report con àncore verificate sul filesystem | CS-2 |
| core invariato | `git diff -- src/sertor_core pyproject.toml` = solo le 2 righe di workspace/ruff | CS-3 |
| test verdi | `uv run pytest packages/speclift/tests -m "not cloud"` (suite completa ~122) | CS-4 |
| nessun ciclo | `uv sync --all-packages` risolve pulito | CS-5 |
| fail-loud azionabile | MCP/indice giù → l'agente si ferma; located malformato → `bundle --changeset/--located` exit 5 | CS-6 |
| provenienza + onestà | `packages/speclift/VENDORING.md` (commit `5ee6fc1`); doc dichiara MCP `search_code` + gap code-graph | CS-7 |
| Adapter B (no CLI) | il flow B non spawna `sertor-rag`; `rag_sertor.py` presente ma dormiente | FR-004 |

## Nota di onestà (Gruppo H)

Il legame runtime del self-host con Sertor è il tool MCP **`search_code`**, orchestrato dall'agente nella
skill (Procedura B) — **non più una divergenza dal codice vendorato**: l'Adapter B è **prima classe
upstream** (`5ee6fc1`, recepimento del nostro feedback). Resta un **gap più piccolo e spostato**:
`search_code` è **ricerca semantica**, non navigazione del code-graph (`find_symbol`/`who_calls`); la
verifica delle àncore resta **deterministica sul filesystem**. L'adozione va confermata a Sinthari con una
voce su `wiki/sources/input-other-agents/` (ringraziamento/conferma, non più un feedback di divergenza).
