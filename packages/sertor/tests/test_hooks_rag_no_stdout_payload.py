"""Source-level guard: rag SessionEnd hooks emit no Copilot 'decision' payload (E10-FEAT-024, US5).

On Copilot CLI a SessionEnd hook that writes a `decision` key to stdout confuses the client (the
breadcrumb/freshness side-effect must be silent on that channel). The three rag SessionEnd scripts
legitimately use `Write-HookBreadcrumb -Reason '…'` (FEAT-019): banning `\\breason\\b` would be a
vacuous false-positive. The banned pattern is the `decision` payload key only. This file is
**separate** from `test_hooks_script_copilot.py` (which has a module-level `skipif(pwsh is None)`):
this guard must run ALWAYS, offline, with no `pwsh` installed (FR-012/CS-5).
"""
from __future__ import annotations

import re

from sertor_installer.resources import iter_asset_dir

# Payload Copilot vietato: la chiave `decision` in JSON ("decision":) o hashtable PS
# (decision =). NON vietiamo `reason`/`-Reason`: sono parametri legittimi del breadcrumb
# Write-HookBreadcrumb -Reason '…' (FEAT-019) — false-positive se vietati (research DA-D-3).
_DECISION_PAYLOAD = re.compile(r"""["']?decision["']?\s*[:=]""")
# PowerShell block comment `<# … #>` (may span lines).
_BLOCK_COMMENT = re.compile(r"<#.*?#>", re.DOTALL)
# I tre script rag SessionEnd soggetti alla guardia.
_RAG_SESSION_END_SCRIPTS = frozenset({
    "rag-freshness.py",
    "memory-capture.py",
    "version-check.py",
})


def _code_lines(body: str) -> list[str]:
    """Code only: drop `<# … #>` blocks and whole-line `#` comments.

    Prose that merely mentions 'decision' or 'reason' (e.g. in a docstring comment)
    is not mistaken for a payload-emitting code line (FR-010).
    """
    without_block = _BLOCK_COMMENT.sub("", body)
    return [ln for ln in without_block.splitlines() if not ln.strip().startswith("#")]


def _rag_session_end_bodies() -> dict[str, str]:
    """Load the three rag SessionEnd scripts by name from the bundled assets."""
    all_hooks = dict(iter_asset_dir("rag/hooks"))
    missing = _RAG_SESSION_END_SCRIPTS - set(all_hooks)
    assert not missing, f"script rag SessionEnd mancanti dagli asset: {missing}"
    return {name: all_hooks[name] for name in _RAG_SESSION_END_SCRIPTS}


def test_rag_sessionend_scripts_emit_no_decision_payload():
    """No rag SessionEnd script emits a Copilot 'decision' payload key on stdout.

    Comments are stripped before scanning so prose that mentions 'decision'
    is not mistaken for code (FR-010/C-C1). Vieta la chiave 'decision' soltanto;
    '-Reason' è un parametro legittimo di Write-HookBreadcrumb (FR-009/research DA-D-3).
    """
    for name, body in _rag_session_end_bodies().items():
        offenders = [
            ln.strip()
            for ln in _code_lines(body)
            if _DECISION_PAYLOAD.search(ln)
        ]
        assert not offenders, (
            f"{name}: codice che emette payload 'decision' trovato "
            f"(confonde il client Copilot su sessionEnd): {offenders}"
        )


def test_rag_payload_guard_not_vacuous():
    """Anti-pattern: a snippet emitting a 'decision' key is flagged by the guard."""
    snippet_ps = "@{ decision = 'block'; reason = 'x' } | ConvertTo-Json"
    snippet_json = 'Write-Output \'{"decision":"block"}\''
    assert _DECISION_PAYLOAD.search(snippet_ps), (
        "guard must flag @{ decision = … } (PowerShell hashtable)"
    )
    assert _DECISION_PAYLOAD.search(snippet_json), (
        "guard must flag '\"decision\":\"block\"' (JSON write)"
    )


def test_rag_payload_guard_ignores_comment():
    """Comment lines mentioning 'decision'/'reason' are stripped and not flagged (FR-010)."""
    comment_line = "# emits a decision/reason payload on sessionEnd (see Copilot docs)"
    block_comment = "<# This hook must never write a decision key to stdout. #>"
    # Line comment stripped → no match
    code = _code_lines(comment_line)
    assert not any(_DECISION_PAYLOAD.search(ln) for ln in code)
    # Block comment stripped → no match
    code_block = _code_lines(block_comment)
    assert not any(_DECISION_PAYLOAD.search(ln) for ln in code_block)
