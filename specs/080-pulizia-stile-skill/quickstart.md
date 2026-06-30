# Quickstart — Pulizia stile delle skill distribuite (E10-FEAT-022)

Sequenza operativa per `/speckit-tasks` → `/speckit-implement`. Tutto è forma `.md` + guardie:
**zero `sertor_core`**.

## 0. Pre-flight
```powershell
cd C:\Workspace\Git\Sertor
uv sync --all-packages --extra dev
```

## 1. Pulizia ALL-CAPS (R1) — A1..A5
Applica `contracts/style-rules.md` R1 ai 5 file. Verifica deterministica (deve dare ∅):
```powershell
# residuo ALL-CAPS >=4 fuori allowlist, post-strip (lo fa la guardia; qui un check rapido):
uv run python -c "import re,pathlib; t=pathlib.Path('packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md').read_text(encoding='utf-8'); t=re.sub(r'```.*?```',' ',t,flags=re.S); t=re.sub(r'`[^`]*`',' ',t); print(sorted(set(re.findall(r'\b[A-Z]{4,}\b',t))))"
```

## 2. ToC + wikilink orfano (R2/R3) — A4
- Inserisci `## Contents` + 8 voci (anchor in `data-model.md` §3) dopo il blockquote introduttivo.
- Rimuovi la frase `See `[[assistant-targeting]]` for the targeting mechanism.` (R3).

## 3. «How to invoke» pointer (R4) — A2, A3
Sostituisci il blockquote callout con il pointer di `data-model.md` §4.

## 4. Condensazione sezioni (R5) — A1, A2, A3
Applica R5 verificando i pin di `stable-substrings.md` prima di rimuovere ogni item.

## 5. Guardie nuove + estensione (DA-D-4)
- crea `packages/sertor/tests/test_assets_skill_style.py` (G1);
- crea `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (G2);
- estendi `packages/sertor/tests/test_assets_cli_invocation.py` (G3).

## 6. Sync dogfood (CS-6)
```powershell
uv run python -m sertor_installer.sync          # A4 -> .claude/skills/wiki-author/wiki-playbook.md
uv run python -m sertor_flow.sync               # A5 -> .claude/skills/requirements/SKILL.md
```
> NOTA (F-6): i dogfood `.claude/skills/eval-*` sono un fork IT non guardato, **fuori ambito**: non
> riconciliarli qui.

## 7. Suite (deve essere verde)
```powershell
uv run pytest packages/sertor/tests/test_assets_skill_style.py `
  packages/sertor/tests/test_assets_cli_invocation.py `
  packages/sertor/tests/test_assets_copilot_parity.py `
  tests/unit/test_assets_sync.py
uv run pytest packages/sertor-flow/tests/unit
uv run ruff check .
```

## 8. Definition of Done
- CS-1 ALL-CAPS=0 (A1–A5) · CS-2 nessun duplicato inline↔sezione · CS-3 ToC in A4 · CS-4 zero `[[`
  orfani · CS-5 pin presenti + parità Copilot verde · CS-6 dogfood A4/A5 in sync.
- Re-index dogfood del corpus toccato (`assets/`/`.claude/`/`specs/`): `uv run sertor-rag index .`
  (rituale step 5) + smoke `sertor-rag doctor`.
- Commit delegato al `configuration-manager` (vedi brief nel report).
