"""Parità byte per byte (FR-027) fra la sorgente di una skill e la sua copia installata.

Il confronto è byte per byte di proposito: anche una differenza di sole terminazioni di riga è una
differenza, perché è proprio quella che un `git status` può nascondere e un'impronta registrata no.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import PARITY_IGNORE
from .domain.errors import InputError


@dataclass(frozen=True)
class ParityResult:
    identical: bool
    first_difference: dict | None

    def to_dict(self) -> dict:
        return {"identical": self.identical, "first_difference": self.first_difference}


def compare(a: Path, b: Path) -> ParityResult:
    for p in (a, b):
        if not p.exists():
            raise InputError(str(p), "percorso inesistente")
    if a.is_file() and b.is_file():
        same = a.read_bytes() == b.read_bytes()
        return ParityResult(same, None if same else {"path": b.name, "kind": "content"})
    if a.is_dir() != b.is_dir():
        raise InputError(f"{a} / {b}", "si confrontano due cartelle o due file, non una cartella con un file")
    return _compare_trees(a, b)


def _files(root: Path) -> set[str]:
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not any(part in PARITY_IGNORE for part in p.relative_to(root).parts)
    }


def _compare_trees(a: Path, b: Path) -> ParityResult:
    files_a, files_b = _files(a), _files(b)
    for rel in sorted(files_a | files_b):
        if rel not in files_a:
            return ParityResult(False, {"path": rel, "kind": "missing-in-a"})
        if rel not in files_b:
            return ParityResult(False, {"path": rel, "kind": "missing-in-b"})
        if (a / rel).read_bytes() != (b / rel).read_bytes():
            return ParityResult(False, {"path": rel, "kind": "content"})
    return ParityResult(True, None)
