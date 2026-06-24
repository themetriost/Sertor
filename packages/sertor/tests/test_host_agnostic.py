"""Test SC-004 (T032): zero Sertor-specific references in installed artifacts.

Scans every file installed in `<tmp_repo>` after `install wiki` with the regex `\\bsertor\\b`
(case-insensitive). The **whitelist (F7)** allows only product command names, the runtime dotfolder,
the interim install URL and the marker — all host-agnostic (identical on every host), not references
to the Sertor *project*:
- `sertor-wiki-tools` — console-script of the deterministic core;
- `sertor-rag` — MCP/retrieval console-script;
- `.sertor` — the runtime dotfolder the installer creates on every host (the venv/index live there;
  agent-facing assets invoke the CLIs via `uv run --directory .sertor …`, the same form the MCP
  server uses) — FEAT-010;
- `github.com/themetriost/Sertor` — the interim `git+url`/`uvx --from` distribution URL the
  installer-invocation guidance cites (FEAT-010);
- `SERTOR:WIKI-RITUAL` — namespace of the marker in CLAUDE.md (product name, not host-specific).
Everything else is considered a reference to the Sertor project → the test fails.
"""
from __future__ import annotations

import re
from pathlib import Path

from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan

# Host-agnostic whitelist (F7): product command names, runtime dotfolder, install URL + marker
# (stripped before matching). Order matters: longer/qualified tokens first so they are removed
# before their substrings (e.g. the URL before a bare `Sertor`, `.sertor` before `sertor`).
_WHITELIST = (
    "github.com/themetriost/Sertor",
    "sertor-wiki-tools",
    "sertor-rag",
    ".sertor",
    "SERTOR:WIKI-RITUAL",
)
_SERTOR = re.compile(r"sertor", re.IGNORECASE)


def _strip_whitelist(text: str) -> str:
    for token in _WHITELIST:
        text = text.replace(token, "")
        text = text.replace(token.lower(), "")
    return text


def test_installed_artifacts_have_no_sertor_references(tmp_path: Path):
    profile = build_host_profile(tmp_path, language="it")
    execute_plan(build_install_plan(), profile)

    offenders: list[str] = []
    for path in tmp_path.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        residual = _strip_whitelist(text)
        if _SERTOR.search(residual):
            # collect the offending lines for a diagnostic message
            for i, line in enumerate(residual.splitlines(), 1):
                if _SERTOR.search(line):
                    offenders.append(f"{path.relative_to(tmp_path)}:{i}: {line.strip()[:80]}")

    assert not offenders, "Riferimenti Sertor-specifici trovati:\n" + "\n".join(offenders)
