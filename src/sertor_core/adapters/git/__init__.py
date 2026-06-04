"""Adapter git (fuori dal dominio): implementazioni concrete di `GitPort`."""
from __future__ import annotations

from sertor_core.adapters.git.subprocess_git import SubprocessGitAdapter

__all__ = ["SubprocessGitAdapter"]
