"""Differenza fra due versioni di un agente (feature 006, research R5a).

Una correzione che tocca l'intestazione cambia cosa l'agente può fare, e chi delega non lo vede leggendo il
prompt. Qui quel cambio diventa un dato: ogni campo aggiunto, tolto o cambiato, `tools` come insieme di
strumenti, e quante righe del prompt sono entrate e uscite. I fine riga non contano.
"""

from __future__ import annotations

import difflib
from pathlib import Path

from .domain.errors import InputError
from .domain.models import AgentDiff, AgentDoc, FieldChange
from .domain.ports import AgentSource


def diff_agents(before: Path, after: Path, source: AgentSource) -> AgentDiff:
    old, new = source.read(before), source.read(after)
    if _shape(old) != _shape(new):
        raise InputError(
            str(after), "forma diversa da quella di prima: per confrontare forme diverse usa agent-forms"
        )
    return AgentDiff(
        before=str(before),
        after=str(after),
        fields=_field_changes(old.header, new.header),
        tools=_tools_change(old.header, new.header),
        prompt=_prompt_change(old, new),
    )


def _shape(doc: AgentDoc) -> str:
    return "agent.md" if doc.file_name.endswith(".agent.md") else doc.form


def _field_changes(old: dict, new: dict) -> tuple[FieldChange, ...]:
    changes = []
    for name in sorted(set(old) | set(new)):
        if name not in new:
            changes.append(FieldChange(name, "removed", old[name], None))
        elif name not in old:
            changes.append(FieldChange(name, "added", None, new[name]))
        elif _comparable(name, old[name]) != _comparable(name, new[name]):
            changes.append(FieldChange(name, "changed", old[name], new[name]))
    return tuple(changes)


def _comparable(name: str, value):
    # `tools: Read, Bash` e una lista a blocco con gli stessi strumenti sono la stessa intestazione
    return frozenset(tool_items(value)) if name == "tools" else value


def _tools_change(old: dict, new: dict) -> dict | None:
    if "tools" not in old and "tools" not in new:
        return None
    before, after = set(tool_items(old.get("tools", []))), set(tool_items(new.get("tools", [])))
    return {"added": sorted(after - before), "removed": sorted(before - after)}


def tool_items(value) -> list[str]:
    """Gli strumenti dichiarati, filtro compreso: `Bash(git *)` e `Bash` sono strumenti diversi."""

    items = value if isinstance(value, list) else str(value).strip().strip("[]").split(",")
    return [str(i).strip().strip("'\"") for i in items if str(i).strip()]


def _prompt_change(old: AgentDoc, new: AgentDoc) -> dict:
    a, b = prompt_lines(old), prompt_lines(new)
    added = removed = 0
    for line in difflib.ndiff(a, b):
        added += line.startswith("+ ")
        removed += line.startswith("- ")
    return {"changed": a != b, "lines_added": added, "lines_removed": removed}


def prompt_lines(doc: AgentDoc) -> list[str]:
    """Le righe del prompt senza le righe vuote in testa e in coda (Kaelen apre il TOML con una vuota)."""

    lines = [text.rstrip("\r") for _, text in doc.body]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines
