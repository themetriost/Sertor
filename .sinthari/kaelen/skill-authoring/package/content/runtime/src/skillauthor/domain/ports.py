"""Porte di SkillAuthor (Principio I): il dominio dipende da queste, gli adapter le implementano."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .models import AgentDoc, SkillDoc


class SkillSource(Protocol):
    def read(self, skill_dir: Path) -> SkillDoc: ...


class GradingSource(Protocol):
    def runs(self, workspace: Path) -> dict[tuple[int, str], list[dict]]:
        """Le valutazioni per (eval_id, config), una per giro; config ∈ {with_skill, without_skill}."""
        ...


class AgentSource(Protocol):
    def read(self, agent_file: Path) -> AgentDoc: ...
