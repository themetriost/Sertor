"""Adapter git (fuori dal dominio): implementa `GitPort` via `subprocess`.

Isola la dipendenza da git/`subprocess` qui, così il dominio wiki resta puro (Principio I).
"""
from __future__ import annotations

from sertor_core.adapters.git.subprocess_git import SubprocessGitAdapter

__all__ = ["SubprocessGitAdapter"]
