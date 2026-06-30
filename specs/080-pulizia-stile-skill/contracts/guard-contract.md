# Contract — Guardia anti-regressione (FR-014, DA-D-4)

## G1 — `packages/sertor/tests/test_assets_skill_style.py` (NUOVO)
Legge gli asset via `sertor_installer.resources.read_asset_text`. Helper puro `_strip_code(text)`:
rimuove fenced block (```` ```...``` ````, regex DOTALL) poi inline span (`` `...` ``).

Costanti:
```
_IN_SCOPE = (
    "rag/skills/guided-setup/SKILL.md",
    "rag/skills/eval-suite-author/SKILL.md",
    "rag/skills/eval-feedback/SKILL.md",
    "claude/skills/wiki-author/wiki-playbook.md",
)
_ALLOW = {RAG,CLI,MCP,API,JSON,JSONL,YAML,TOML,URL,NL,POSIX,HTTP,SDLC,MRR,STOP,PASS,FAIL,PATH}
_EVAL = ("rag/skills/eval-suite-author/SKILL.md", "rag/skills/eval-feedback/SKILL.md")
```

Test:
- `test_no_emphatic_allcaps`: per ogni `_IN_SCOPE`, `{m for m in re.findall(r"\b[A-Z]{4,}\b",
  _strip_code(body))} - _ALLOW == set()`. Messaggio nomina file + token offending.
- `test_no_orphan_wikilink`: per ogni `_IN_SCOPE`, `"[[" not in _strip_code(body)`.
- `test_eval_skills_use_pointer`: per ogni `_EVAL`, `"`sertor-cli-reference.md`" in body` **e**
  `"How to invoke `sertor-rag`" ` non come callout espanso — verifica che il blockquote inline non
  ci sia più (assenza della frase «is not on `PATH`. Invoke it via» del callout originale).
- `test_semantic_pins`: per ogni file, ogni pin di `stable-substrings.md` ∈ body.
- meta `test_guard_catches_reintroduced_allcaps`: `{"MANDATORY"} - _ALLOW != set()` (non vacuo).
- meta `test_guard_catches_reintroduced_wikilink`: `"[[" in _strip_code("see [[x]] here")`.

## G2 — `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (NUOVO)
Legge via `sertor_install_kit.read_asset_text("sertor_flow", "claude/skills/requirements/SKILL.md")`.
Allowlist = `_ALLOW ∪ {EARS, FEAT, REQ}`.
- `test_requirements_no_emphatic_allcaps`: `{...} - allow == set()` (atteso: `SEMPRE` rimosso).

## G3 — Estensione `packages/sertor/tests/test_assets_cli_invocation.py`
Aggiungere:
- `test_eval_skills_point_to_reference`: per `_EVAL_SUITE`/`_EVAL_FEEDBACK`,
  `"`sertor-cli-reference.md`" in read_asset_text(asset)`.

La **closure** del reference (target depositato dal piano RAG) è già garantita da
`test_cli_reference_closure_in_rag_plan` (parity guard): le eval-skill sono nel piano RAG, quindi
citare il reference è closure-safe automaticamente. La presence della forma robusta
`uv run --project .sertor` nelle eval-skill è già asserita da
`test_invoking_assets_carry_robust_form` (restano in `_INVOKING_ASSETS`).

## G4 — Guardie esistenti che DEVONO restare verdi (nessuna modifica)
- `tests/unit/test_assets_sync.py` — dopo `python -m sertor_installer.sync` (A4).
- `packages/sertor-flow/tests/unit/test_assets_sync.py` — dopo `python -m sertor_flow.sync` (A5).
- `packages/sertor/tests/test_assets_copilot_parity.py` — no `.claude/`/slash/Claude + closure.
- `packages/sertor/tests/test_assets_cli_invocation.py` — forma robusta + «How to invoke» in 1 fonte
  + footgun + reference closure (la rimozione del callout eval non rompe nessuno di questi).

## Confine di esclusione del grep ALL-CAPS (preciso)
1. fenced block: `re.sub(r"```.*?```", " ", body, flags=re.S)`;
2. inline span: `re.sub(r"`[^`]*`", " ", body)`;
3. su quel testo: `re.findall(r"\b[A-Z]{4,}\b", …)`; sottrai allowlist. Niente esclusione per
   sole-righe-con-backtick: il vero confine è lo strip dei code span (più robusto della riga).
