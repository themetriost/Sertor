"""Additive merge of `.sertor/.env` (FR-014/015/016, M1).

Absent → create from template (empty secrets). Present → add ONLY missing keys, **never**
overwrite the value of an existing key (REQ-222). Targeted exception (M1): for
`SERTOR_EXCLUDE_PATTERNS`, always ensures `.sertor` is present (appends it to the existing value if
missing), because excluding the runtime from indexing is a correctness concern, not a user
preference. No secret is ever written with a value (templates leave them empty).
"""
from __future__ import annotations

from pathlib import Path

from sertor_install_kit.artifacts import Outcome

_EXCLUDE_KEY = "SERTOR_EXCLUDE_PATTERNS"
_SERTOR_DIR = ".sertor"


def _parse_pairs(text: str) -> dict[str, str]:
    """Extracts `KEY=value` pairs (ignores comments/blank lines). Last one wins (dotenv
    semantics)."""
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        pairs[k.strip()] = v.strip()
    return pairs


def _replace_key_line(text: str, key: str, new_line: str) -> str:
    """Replaces the `key=...` line with `new_line`, preserving everything else."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.split("=", 1)[0].strip() == key:
            out.append(new_line)
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def merge_env(env_path: Path, rendered: str) -> tuple[Outcome, str]:
    """Applies the additive merge. `rendered` = already-compiled template (corpus injected)."""
    template = _parse_pairs(rendered)

    if not env_path.exists():
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            rendered if rendered.endswith("\n") else rendered + "\n", encoding="utf-8"
        )
        return Outcome.CREATED, f"{len(template)} keys"

    existing_text = env_path.read_text(encoding="utf-8")
    existing = _parse_pairs(existing_text)
    new_text = existing_text
    added: list[str] = []
    ensured_sertor = False

    # M1: ensure `.sertor` is in the excludes even if the key already exists.
    if _EXCLUDE_KEY in existing:
        items = [p.strip() for p in existing[_EXCLUDE_KEY].split(",") if p.strip()]
        if _SERTOR_DIR not in items:
            items.append(_SERTOR_DIR)
            new_text = _replace_key_line(
                new_text, _EXCLUDE_KEY, f"{_EXCLUDE_KEY}={','.join(items)}"
            )
            ensured_sertor = True

    # Missing keys: append (never overwrite existing values).
    missing = [f"{k}={v}" for k, v in template.items() if k not in existing]
    if missing:
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += "\n".join(missing) + "\n"
        added = [line.split("=", 1)[0] for line in missing]

    if not missing and not ensured_sertor:
        return Outcome.SKIPPED, "already present"

    env_path.write_text(new_text, encoding="utf-8")
    parts: list[str] = []
    if added:
        parts.append(f"+{len(added)} keys")
    if ensured_sertor:
        parts.append(".sertor added to excludes")
    return Outcome.MERGED, "; ".join(parts)
