"""Test SC-004 (T032): zero riferimenti Sertor-specifici negli artefatti installati.

Scansiona ogni file installato in `<tmp_repo>` dopo `install wiki` con la regex `\\bsertor\\b`
(case-insensitive). La **whitelist (F7)** ammette i soli nomi-comando di prodotto e il marker:
- `sertor-wiki-tools` — console-script del nucleo deterministico;
- `sertor-rag` — console-script MCP/retrieval;
- `SERTOR:WIKI-RITUAL` — namespace del marker nel CLAUDE.md (nome del prodotto, non host-specifico).
Tutto il resto è giudicato un riferimento al progetto Sertor → il test fallisce.
"""
from __future__ import annotations

import re
from pathlib import Path

from sertor_installer.config_gen import build_host_profile
from sertor_installer.install_wiki import build_install_plan, execute_plan

# Whitelist host-agnosticità (F7): nomi-comando di prodotto + marker (rimossi prima del match).
_WHITELIST = ("sertor-wiki-tools", "sertor-rag", "SERTOR:WIKI-RITUAL")
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
            # raccogli le righe colpevoli per un messaggio diagnostico
            for i, line in enumerate(residual.splitlines(), 1):
                if _SERTOR.search(line):
                    offenders.append(f"{path.relative_to(tmp_path)}:{i}: {line.strip()[:80]}")

    assert not offenders, "Riferimenti Sertor-specifici trovati:\n" + "\n".join(offenders)
