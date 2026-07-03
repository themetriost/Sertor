# Quickstart — dogfood client-fedele

Come rendere fedele il dogfood e come **verificare** l'accettazione (mappa SC-1..SC-6 / AS-1..AS-7).

## Setup (materializzazione della machinery SpecKit)

Il dogfood ottiene la machinery come un ospite — è uno **step di setup**, come `uv sync`. La machinery è
**gitignorata** (rigenerabile), non vive in git.

```powershell
# Dalla root del repo. Idempotente; non tocca constitution.md / plan-template.md / feature.json.
.\scripts\dev\materialize-speckit.ps1
```

Cosa fa (D-1/D-2): lancia `specify init --ai claude` (pin `SPECKIT_VERSION`, overlay UTF-8) in una **dir
isolata**, poi copia nel repo **solo** la machinery rigenerabile (skill `speckit-*`, `.specify/scripts/`,
template non-custom, workflows/integrations). Fallisce **loud** se un artefatto Sertor-authored cambierebbe.

## Verifica (accettazione)

```powershell
# SC-1 / AS-1 — surface risolta: le 9 skill esistono
(Get-ChildItem .claude/skills -Directory | Where-Object Name -like 'speckit-*').Count   # atteso 9
Test-Path .specify/scripts/powershell/setup-plan.ps1                                     # atteso True

# SC-3 / AS-2 — nessun agente hand-authored
(Get-ChildItem .claude/agents -Filter 'speckit-*.md').Count                              # atteso 0

# SC-2 / AS-3 — no re-vendoring: nessuna machinery tracciata / da committare
git status --porcelain .claude/skills .specify/scripts                                   # atteso vuoto
git ls-files .claude/skills/speckit-* .specify/scripts                                    # atteso vuoto

# SC-4 / AS-4 — artefatti Sertor-authored invariati
git diff --quiet -- .specify/memory/constitution.md .specify/templates/plan-template.md .specify/feature.json
# exit 0 = invariati

# SC-6 / AS-5 — guardia verde (offline, anche senza machinery locale)
uv run pytest tests/unit/test_dogfood_speckit_fidelity.py -q

# SC-5 / AS-7 — zero core
git diff --stat master -- src/sertor_core                                                 # atteso vuoto
```

## Note
- **Clone fresco / CI (EC-1):** la machinery è assente finché non si esegue il setup; la **guardia** gira
  comunque (asserisce assenze/tracciamento, non presenze). Le fasi SpecKit che usano gli script richiedono
  il setup — documentato, non silenzioso (REQ-008).
- **Console non-UTF8 (EC-2):** lo script forza `PYTHONUTF8`/`PYTHONIOENCODING`; senza, `specify init` aborta.
- **Re-run (EC-3):** idempotente; gli artefatti Sertor-authored non vengono mai toccati.
