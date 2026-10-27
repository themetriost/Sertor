"""Lettura dei documenti JSON con validazione di schema.

È l'unico punto in cui nascono gli errori d'ingresso sui documenti.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .domain.errors import InputError, SchemaError
from .schemas import load_schema


def load_validated(path: Path, schema: str) -> dict:
    """Legge `path` e lo valida contro `<schema>.schema.json`. Errore che nomina file e campo."""

    if not path.is_file():
        raise InputError(str(path), "file mancante")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(str(path), f"JSON non valido alla riga {exc.lineno}: {exc.msg}") from None
    errors = sorted(
        Draft202012Validator(load_schema(schema)).iter_errors(doc), key=lambda e: list(e.absolute_path)
    )
    if errors:
        first = errors[0]
        field = "/".join(str(p) for p in first.absolute_path) or "(radice)"
        raise SchemaError(str(path), field, first.message)
    return doc
