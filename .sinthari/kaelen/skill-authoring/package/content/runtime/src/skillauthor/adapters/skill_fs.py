"""Adapter filesystem di `SkillSource`: legge SKILL.md, il frontmatter e l'elenco degli allegati.

Il frontmatter è letto come sottoinsieme di YAML (data-model.md): chiavi di primo livello e il blocco
`metadata:`. Fuori da quel sottoinsieme è un errore d'ingresso, non un'interpretazione.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import PARITY_IGNORE
from ..domain.errors import InputError
from ..domain.models import SkillDoc


class FsSkillSource:
    def read(self, skill_dir: Path) -> SkillDoc:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise InputError(str(skill_md), "SKILL.md mancante")
        lines = skill_md.read_text(encoding="utf-8").splitlines()
        frontmatter, body_start = _split_frontmatter(lines, str(skill_md))
        body = tuple((n, text) for n, text in enumerate(lines[body_start:], start=body_start + 1))
        files = frozenset(_list_files(skill_dir))
        vendor = skill_dir / "vendor"
        vendor_dirs = tuple(sorted(p.name for p in vendor.iterdir() if p.is_dir())) if vendor.is_dir() else ()
        return SkillDoc(
            dir_name=skill_dir.resolve().name,  # un percorso come "skill/.." ha il nome della cartella reale
            frontmatter=frontmatter,
            body=body,
            files=files,
            has_vendor=vendor.is_dir(),
            vendor_dirs=vendor_dirs,
        )


def _split_frontmatter(lines: list[str], path: str) -> tuple[dict, int]:
    if not lines or lines[0].strip() != "---":
        raise InputError(path, "frontmatter mancante (la prima riga deve essere '---')")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise InputError(path, "frontmatter non chiuso (manca il secondo '---')") from None
    return _parse_frontmatter(lines[1:end], path), end + 1


def _parse_frontmatter(lines: list[str], path: str) -> dict:
    data: dict = {}
    current_key: str | None = None  # la chiave di primo livello che ha aperto il blocco corrente
    for raw in lines:
        if not raw.strip():
            continue
        indented = raw[0] in " \t"
        if indented and raw.strip().startswith("- "):
            # lista a blocco: le intestazioni d'agente la usano per `tools`
            _append_item(data, current_key, raw.strip()[2:].strip(), path)
            continue
        key, sep, value = raw.strip().partition(":")
        if not sep or not key:
            raise InputError(path, f"riga di frontmatter non riconosciuta: {raw.strip()!r}")
        # `chiave:` senza valore apre un blocco; `chiave: ""` è una stringa vuota.
        opens_block = value.strip() == ""
        value = _unquote(value.strip())
        if indented:
            if current_key is None or not isinstance(data[current_key], dict):
                raise InputError(path, f"chiave rientrata fuori da un blocco: {key!r}")
            data[current_key][key] = _decode_metadata(key, value, path)
            continue
        if opens_block:
            data.setdefault(key, {})
            current_key = key
        else:
            current_key = None
            data[key] = value
    return data


def _append_item(data: dict, key: str | None, item: str, path: str) -> None:
    if key is None:
        raise InputError(path, f"voce di lista fuori da un blocco: {item!r}")
    if data[key] == {}:
        data[key] = []
    if not isinstance(data[key], list):
        raise InputError(path, f"il blocco {key!r} mescola chiavi e voci di lista")
    data[key].append(_unquote(item))


def _decode_metadata(key: str, value: str, path: str):
    if key != "lint-allow":
        return value
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as exc:
        raise InputError(path, f"metadata.lint-allow non è un array JSON valido: {exc.msg}") from None
    if not isinstance(decoded, list):
        raise InputError(path, "metadata.lint-allow deve essere un array JSON")
    return decoded


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _list_files(root: Path) -> list[str]:
    out = []
    for path in root.rglob("*"):
        if path.is_file() and not any(part in PARITY_IGNORE for part in path.relative_to(root).parts):
            out.append(path.relative_to(root).as_posix())
    return out
