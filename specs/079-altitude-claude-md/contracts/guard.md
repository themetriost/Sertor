# Contract — guardie (parità, closure, non-reintroduzione, sync)

Le guardie sono **estensioni delle suite esistenti**, offline (no rete, no `uv`). Riusano i lettori di
asset (`read_asset_text`, `iter_asset_dir`, `kit_read("sertor_flow", …)`) e i renderer dei piani
(`build_rag_plan`, `build_install_plan`, `build_governance_plan`).

## G1 — Non-reintroduzione «How to invoke» nei blocchi (REQ-012) — `test_assets_cli_invocation.py` (sertor) + `sertor-flow`

```
assert "How to invoke Sertor's commands" not in read_asset_text("claude-md-block.md")
assert "How to invoke Sertor's commands" not in read_asset_text("rag/claude-md-block-rag-usage.md")
assert "pywin32_bootstrap" not in read_asset_text("rag/claude-md-block-rag-usage.md")
assert "uvx --from"        not in read_asset_text("rag/claude-md-block-rag-usage.md")
# SDLC (sertor-flow): kit_read("sertor_flow", "claude-md-block-sdlc.md")
assert "How to invoke" not in sdlc_block
assert "pywin32_bootstrap" not in sdlc_block
```
**Negativo (non vacuità):** reintroducendo l'heading o la Windows note in un blocco, almeno un assert
fallisce.

## G2 — Fonte unica (CS-2) — sertor

```
# esattamente UNA sede con la sezione completa + Windows note
guide = "How to invoke Sertor's commands"
hits = [a for a in ALL_DISTRIBUTED_MD_ASSETS if guide in read_asset_text(a)]
assert hits == ["rag/sertor-cli-reference.md"]
# Windows note esiste solo nel reference
note_hits = [a for a in ALL_DISTRIBUTED_MD_ASSETS if "pywin32_bootstrap" in read_asset_text(a)]
assert note_hits == ["rag/sertor-cli-reference.md"]
```
*(`ALL_DISTRIBUTED_MD_ASSETS` = enumerazione via `iter_asset_dir` dei `.md` distribuiti del bundle
`sertor`; le mini-note eval «How to invoke `sertor-rag`» NON contengono la substringa esatta «How to
invoke Sertor's commands» né `pywin32_bootstrap` → non falsano il conteggio.)*

## G3 — Pointer presenti (REQ-014/015) — sertor

```
assert "sertor-cli-reference.md" in read_asset_text("rag/claude-md-block-rag-usage.md")
assert "sertor-cli-reference.md" in read_asset_text("rag/skills/guided-setup/SKILL.md")
assert "wiki-playbook.md"        in read_asset_text("claude-md-block.md")
```

## G4 — Closure del reference (REQ-010, NFR-5) — estensione di `test_assets_copilot_parity.py`

Estende lo schema closure (gemello di `_usability_closure_offenders`): il basename
`sertor-cli-reference.md`, quando citato in un body RAG (RAG block MARKER_BLOCK + `guided-setup`
FILE), DEVE essere il basename di un target del **piano RAG** (per `AssistantId.CLAUDE` **e**
`AssistantId.COPILOT_CLI`).

```
def _reference_closure_offenders(plan, render):
    deposited = {Path(t.target_rel).name for t in plan}
    out = []
    for target_rel, _src, body in _rendered_bodies(plan, render):
        if "`sertor-cli-reference.md`" in body and "sertor-cli-reference.md" not in deposited:
            out.append(target_rel)
    return out

assert _reference_closure_offenders(_rag_plan(CLAUDE, tmp), _render_rag) == []
assert _reference_closure_offenders(_rag_plan(COPILOT_CLI, tmp), _render_rag) == []
```
**Negativo:** un piano RAG che non deposita `.sertor/sertor-cli-reference.md` → la closure nomina il
body offendente. Il `wiki-playbook` non cita il filename → non entra nello scope (no falso-positivo su
piano wiki).

## G5 — Rework dei test di presenza guida (`test_assets_cli_invocation.py`)

| Test | Prima | Dopo |
|---|---|---|
| `test_canonical_guide_present_where_first_invoked` | guida in `_RAG_USAGE` + `_GUIDED_SETUP` | guida in `sertor-cli-reference.md`; pointer (non copia) in `_RAG_USAGE`/`_GUIDED_SETUP` |
| `test_wiki_playbook_ships_runtime_invocation_guide` | heading «How to invoke the runtime CLIs» + robusto + `not on PATH` | forma robusta minima (§2) + **assenza** della sottosezione + Windows note |
| `test_rag_usage_block_uv_run_replaces_bare_search` | `uv run --project .sertor sertor-rag search` | **invariato** (verde) |
| `test_invoking_assets_carry_robust_form` | `_ROBUST` in ogni invoking asset | **invariato**: il robusto sopravvive in RAG block (search-first), `guided-setup` (Step), `wiki-playbook` (§2) |
| `_INVOKING_ASSETS` / footgun | senza reference | **aggiunto** `rag/sertor-cli-reference.md` (mai `uv run` nudo / `--directory`) |

## G6 — Parità host-agnostica (CS-5) — `test_assets_copilot_parity.py` (invariata, copre il nuovo asset)

I rendered bodies del piano RAG per Copilot includono il reference (FILE `.md`, byte-copia): gli
assert (a) no `.claude/`, (b) no slash-command, (c) no `Claude Code`, (c') no `Claude`/`Opus`/`Haiku`/
`CLAUDE.md`/`$ARGUMENTS` devono restare verdi sul reference e sui blocchi/skill ridotti.

## G7 — Sync dogfood↔bundle (CS-6) — `tests/unit/test_assets_sync.py` (invariata)

Dopo l'edit del `wiki-playbook.md` (sotto `assets/claude/**`) e `python -m sertor_installer.sync`, la
copia `.claude/skills/wiki-author/wiki-playbook.md` è byte-identica alla sorgente → guardia verde.

## Mappa contratto → requisito → criterio
| Guardia | Requisiti | Criteri |
|---|---|---|
| G1 | REQ-012 | CS-2 |
| G2 | REQ-005 | CS-2 |
| G3 | REQ-002/014/015 | CS-3/CS-4 |
| G4 | REQ-003/007/010 | CS-3 |
| G5 | REQ-008/009/015 | CS-1/CS-2/CS-4 |
| G6 | REQ-004/006 | CS-5 |
| G7 | REQ-011 | CS-6 |
