"""Adapter filesystem di `AgentSource`: legge un file d'agente nelle forme che Kaelen colloca (R2).

- `.md` e `.agent.md`: intestazione fra `---` (Claude Code, Copilot), letta col parser delle skill;
- `.toml`: `name`, `description`, `developer_instructions` (Codex).

Ogni altra forma, o un file che non si legge, è un errore d'ingresso che nomina il file.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from ..config import AGENT_SUFFIXES
from ..domain.errors import InputError
from ..domain.models import AgentDoc
from .skill_fs import _split_frontmatter


class FsAgentSource:
    def read(self, agent_file: Path) -> AgentDoc:
        form, stem = _form_of(agent_file)
        if not agent_file.is_file():
            raise InputError(str(agent_file), "file d'agente mancante")
        text = agent_file.read_text(encoding="utf-8")
        header, body = _read_toml(text, agent_file) if form == "toml" else _read_markdown(text, agent_file)
        return AgentDoc(
            path=str(agent_file),
            file_name=agent_file.name,
            form=form,
            stem=stem,
            header=header,
            body=body,
            dir=str(agent_file.parent),
        )


def _form_of(agent_file: Path) -> tuple[str, str]:
    name = agent_file.name
    for suffix, form in AGENT_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return form, name[: -len(suffix)]
    accepted = ", ".join(s for s, _ in AGENT_SUFFIXES)
    raise InputError(str(agent_file), f"forma d'agente non riconosciuta (attese: {accepted})")


def _read_markdown(text: str, agent_file: Path) -> tuple[dict, tuple]:
    lines = text.splitlines()
    header, body_start = _split_frontmatter(lines, str(agent_file))
    body = tuple((n, line) for n, line in enumerate(lines[body_start:], start=body_start + 1))
    return header, body


def _read_toml(text: str, agent_file: Path) -> tuple[dict, tuple]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise InputError(str(agent_file), f"TOML non valido: {exc}") from None
    prompt = data.pop("developer_instructions", "")
    if not isinstance(prompt, str):
        raise InputError(str(agent_file), "developer_instructions deve essere una stringa")
    # nella forma Codex il prompt è un campo: le righe si numerano dentro il campo
    body = tuple(enumerate(prompt.splitlines(), start=1))
    return data, body
