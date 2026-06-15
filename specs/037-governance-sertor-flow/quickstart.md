# Quickstart — `sertor-flow`

## Per un ospite (uso finale)

Installa il metodo di sviluppo (SDLC) su un repository, con un comando, senza il RAG:

```bash
# Distribuzione interim via git+url (PyPI fuori ambito)
uvx --from "git+<repo-url>#subdirectory=packages/sertor-flow" sertor-flow install
# oppure, su un target esplicito:
uvx --from "git+<repo-url>#subdirectory=packages/sertor-flow" sertor-flow install --target /path/al/repo
```

Dopo l'install l'ospite ha: skill/agenti SpecKit, skill `requirements` + agente analista, agente
`configuration-manager`, macchinario `.specify/` (templates, script ps+bash, estensione git, workflow),
una **costituzione-starter** in `.specify/memory/constitution.md` da personalizzare, e un **blocco
rituale SDLC** nel `CLAUDE.md`. **Nessuna** fase è partita (install ≠ run): il primo passo è, ad
esempio, `speckit-constitution` per adattare la costituzione, poi `requirements` → `speckit-specify`.

Verifica idempotenza/non-distruttività:
```bash
sertor-flow install            # seconda volta → tutti "skipped", zero modifiche
```

## Per chi cerca dalla CLI ombrello

```bash
sertor install governance      # → messaggio: la governance è il pacchetto `sertor-flow`, installalo con …
```

## Per lo sviluppo (su Sertor)

```bash
uv sync --extra dev
uv run pytest packages/sertor-flow/tests          # test del nuovo pacchetto
uv run pytest packages/sertor/tests               # NON-regressione dopo l'estrazione del kit
uv run pytest                                      # intera suite (root + membri)
uv run ruff check .
# guardia anti-drift asset governance ↔ dogfood (.claude/.specify del repo)
uv run pytest packages/sertor-flow/tests/unit/test_assets_sync.py
```

## Smoke manuale (su un repo ospite temporaneo)

1. `sertor-flow install --target <tmpdir>` → resoconto con artefatti `created`.
2. Verifica presenza di `.claude/skills/speckit-specify/`, `.claude/agents/requirements-analyst.md`,
   `.specify/templates/plan-template.md`, `.specify/scripts/{bash,powershell}/`,
   `.specify/memory/constitution.md`, `.specify/NOTICE`, blocco `<!-- SERTOR:SDLC-RITUAL … -->` in
   `CLAUDE.md`.
3. Verifica assenza di `.specify/feature.json` (stato runtime non distribuito).
4. Re-run → tutti `skipped`.
5. In un venv senza `sertor-core`: l'install completa lo stesso (indipendenza dal RAG).
