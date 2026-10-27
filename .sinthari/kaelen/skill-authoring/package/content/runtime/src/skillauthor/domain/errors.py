"""Errori di dominio tipizzati (Constitution VI). Ogni errore nomina il file e, se c'è, il campo.

Tutti finiscono sul codice d'uscita 2 del CLI: sono errori d'uso o d'ingresso, non esiti di dominio.
"""

from __future__ import annotations


class SkillAuthorError(Exception):
    """Radice di tutti gli errori di SkillAuthor."""


class InputError(SkillAuthorError):
    """Un ingresso manca o non si legge: file assente, frontmatter non supportato, argomento errato."""

    def __init__(self, path: str, detail: str) -> None:
        self.path = path
        self.detail = detail
        super().__init__(f"{path}: {detail}")


class SchemaError(InputError):
    """Un documento JSON non rispetta il suo schema; `field` è il percorso del campo che fallisce."""

    def __init__(self, path: str, field: str, detail: str) -> None:
        self.field = field
        super().__init__(path, f"campo '{field}': {detail}")
