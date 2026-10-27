"""Form checks and hook-command resolution for verify (specs/023-verify-what-runs).

A form check asks whether an installed item is written in the form its assistant documents, so that
an item intact byte for byte but ignored by the assistant is reported (the masked failure). The
checks each placement needs are declared in the placement rule; this module is their one
implementation, over a closed vocabulary. Nothing here writes or runs anything.
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import tomllib
from pathlib import Path, PurePosixPath

# The closed vocabulary (research R-1). Each id names what its parameters mean.
CHECKS = {
    "file-present": ("file",),  # a directory item holds this file
    "frontmatter": ("fields", "file"),  # these frontmatter fields are present and non-empty
    "name-matches": ("file",),  # the frontmatter name equals the directory or file stem
    "json": (),  # the whole file parses as JSON
    "toml": ("keys",),  # the whole file parses as TOML (and the table holds these keys)
}


def check_problems(check) -> list[str]:
    """Why a rule's check is malformed, or nothing (the rule is refused otherwise)."""
    if not isinstance(check, dict) or check.get("id") not in CHECKS:
        ident = check.get("id") if isinstance(check, dict) else check
        return [f"check {ident!r} is not one of {', '.join(CHECKS)}"]
    out = []
    for key in check:
        if key != "id" and key not in CHECKS[check["id"]]:
            out.append(f"check {check['id']!r} takes no parameter {key!r}")
    if check["id"] == "frontmatter" and not check.get("fields"):
        out.append("check 'frontmatter' needs fields")
    return out


def _frontmatter(text: str) -> dict[str, str] | None:
    body = text.replace("\r\n", "\n")
    if not body.startswith("---\n"):
        return None
    end = body.find("\n---", 4)
    if end < 0:
        return None
    meta = {}
    for line in body[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if sep and key.strip() and not line.startswith((" ", "\t")):
            meta[key.strip()] = value.strip().strip("\"'")
    return meta


def _target_file(host: Path, rel: str, check: dict) -> Path:
    path = host / rel
    return path / check["file"] if check.get("file") and path.is_dir() else path


def run(host: Path, rel: str, checks: list[dict], name: str | None = None) -> list[dict]:
    """The checks a location fails, as [{check, detail}]; empty when it passes them all."""
    failed = []
    for check in checks:
        ident = check["id"]
        target = _target_file(host, rel, check)
        if ident == "file-present":
            if not target.is_file():
                failed.append({"check": ident, "detail": f"{check['file']} is missing"})
            continue
        if not target.is_file():
            continue  # absent is the byte state's to report, not the form's
        try:
            text = target.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            failed.append({"check": ident, "detail": "not UTF-8 text"})
            continue
        if ident == "frontmatter":
            meta = _frontmatter(text)
            if meta is None:
                failed.append({"check": ident, "detail": "no frontmatter"})
                continue
            missing = [f for f in check["fields"] if not meta.get(f)]
            if missing:
                failed.append({"check": ident, "detail": "missing " + ", ".join(missing)})
        elif ident == "name-matches":
            meta = _frontmatter(text) or {}
            stem = PurePosixPath(rel.rstrip("/")).name
            stem = stem.split(".", 1)[0] if not (host / rel).is_dir() else stem
            if meta.get("name") != stem:
                failed.append(
                    {"check": ident, "detail": f"name {meta.get('name')!r} is not {stem!r}"}
                )
        elif ident == "json":
            try:
                json.loads(text)
            except ValueError as exc:
                failed.append({"check": ident, "detail": f"not JSON: {exc}"})
        elif ident == "toml":
            try:
                table = tomllib.loads(text)
            except tomllib.TOMLDecodeError as exc:
                failed.append({"check": ident, "detail": f"not TOML: {exc}"})
                continue
            missing = [k for k in check.get("keys", ()) if not table.get(k)]
            if missing:
                failed.append({"check": ident, "detail": "missing " + ", ".join(missing)})
    return failed


# --- hook commands (research R-4) ---------------------------------------------------------------

_ROOTS = ("$CLAUDE_PROJECT_DIR/", "${CLAUDE_PROJECT_DIR}/", "./")


def hook_commands(content: str) -> list[str]:
    """The command strings a rendered hook registration carries (any of the three shapes)."""
    found: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                if key in ("command", "bash", "powershell") and isinstance(inner, str):
                    found.append(inner)
                else:
                    walk(inner)
        elif isinstance(value, list):
            for inner in value:
                walk(inner)

    walk(json.loads(content))
    return list(dict.fromkeys(found))


def resolve(host: Path, command: str, which=shutil.which) -> list[str]:
    """The parts of a hook command that do not exist: its interpreter, and every script path."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return [f"cannot parse {command!r}"]
    if not tokens:
        return ["empty command"]
    missing = []
    head = tokens[0]
    if not re.search(r"[/\\]", head) and which(head) is None:
        missing.append(f"{head} (not on PATH)")
    for token in tokens[1:] if not re.search(r"[/\\]", head) else tokens:
        if not re.search(r"[/\\]", token) or token.startswith("-"):
            continue
        rel = token
        for root in _ROOTS:
            if rel.startswith(root):
                rel = rel[len(root) :]
        if not (host / rel).exists():
            missing.append(rel)
    return missing
