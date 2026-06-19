"""Per-assistant rendering of FILE surfaces from a SINGLE canonical source (feature 044/045).

Anti-drift (REQ-021, Principio III/VI): the *content* of a command/skill, of the agent persona and
of the instruction block has ONE source — the existing `assets/claude/**` (and `assets/*.md`) used
by Claude. The Copilot artifacts are **derived** from that source by translating only the
*container* (the frontmatter / file naming), never by keeping a second hand-maintained copy. Guard
tests (`sertor`: `test_assets_copilot_guard.py`; `sertor-flow`: governance parity) fail on
divergence.

The renderer lives in the shared kit (feature 045) so BOTH `sertor` (wiki/rag) and `sertor-flow`
(governance) translate per-assistant surfaces from one implementation (anti-drift/DRY).

Pure functions (stdlib-only): they take the canonical text and produce the rendered text. The body
below the frontmatter is preserved verbatim, so the shared substrate cannot drift.
"""
from __future__ import annotations

from dataclasses import dataclass

_FRONTMATTER_FENCE = "---"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Splits a Markdown asset into `(frontmatter, body)`.

    Frontmatter is the leading `---`-fenced block (YAML). If absent, returns `("", text)`. The body
    is everything after the closing fence, kept byte-for-byte (the shared substrate).
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return "", text
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONTMATTER_FENCE:
            frontmatter = "".join(lines[1:i])
            body = "".join(lines[i + 1 :])
            return frontmatter, body
    # malformed (no closing fence) → treat all as body, no frontmatter
    return "", text


def render_prompt_file(canonical_text: str) -> str:
    """Renders a Copilot prompt-file (`*.prompt.md`) from the canonical command/skill asset.

    Copilot prompt-files use a minimal frontmatter whose mode key is **`agent:`** (FEAT-011/FR-016:
    `mode:` is NOT a valid Copilot prompt-file key and is silently ignored). The instructional
    **body** is the shared substrate, reused verbatim from the Claude command/skill (anti-drift).
    """
    _front, body = split_frontmatter(canonical_text)
    header = f"{_FRONTMATTER_FENCE}\nagent: agent\n{_FRONTMATTER_FENCE}\n\n"
    return header + body.lstrip("\n")


def render_custom_agent(canonical_text: str, *, include_model: bool = False) -> str:
    """Renders a Copilot custom-agent (`*.agent.md`) from the canonical agent asset.

    The persona **body** is the shared substrate (reused verbatim); the frontmatter is translated to
    the Copilot custom-agent shape (`name`/`description`/`tools` preserved when present).

    FEAT-011/FR-017 (Q6=a): the Claude `model:` value (e.g. `haiku`) is INVALID on Copilot, so the
    `model` field is OMITTED by default (`include_model=False`). The Claude plan never uses this
    renderer (it keeps the `.claude/**` byte-copy layout), so omitting `model` causes no Claude
    regression. The parameter makes the omission an explicit caller decision, not a side effect.
    """
    front, body = split_frontmatter(canonical_text)
    fields = _parse_simple_frontmatter(front)
    keys = ("name", "description", "tools", "model") if include_model \
        else ("name", "description", "tools")
    lines = [_FRONTMATTER_FENCE]
    for key in keys:
        if key in fields:
            lines.append(f"{key}: {_yaml_scalar(fields[key])}")
    lines.append(_FRONTMATTER_FENCE)
    lines.append("")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def render_native_skill(canonical_text: str, name: str) -> str:
    """Renders a native agent-skill `SKILL.md` from a canonical command/skill asset.

    Native agent skills (Copilot `.github/skills/<name>/`, Claude `.claude/skills/<name>/`) require
    a `SKILL.md` whose frontmatter carries `name` (lowercase, hyphenated identifier) and
    `description` (when the assistant should use it). The instructional **body** is the shared
    substrate, reused verbatim from the canonical asset (anti-drift); `description` is taken from
    the canonical frontmatter. Claude-command-only keys (e.g. `argument-hint`) are dropped — not
    native agent-skill keys.

    Used on Copilot CLI to deposit the `wiki-author` skill as a single native skill whose SKILL.md
    is the dispatcher derived from the `/wiki` command body (the CLI has no custom slash-commands,
    so the skill absorbs the command role).
    """
    front, body = split_frontmatter(canonical_text)
    fields = _parse_simple_frontmatter(front)
    lines = [_FRONTMATTER_FENCE, f"name: {_yaml_scalar(name)}"]
    if "description" in fields:
        lines.append(f"description: {_yaml_scalar(fields['description'])}")
    lines.append(_FRONTMATTER_FENCE)
    lines.append("")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def _yaml_scalar(value: str) -> str:
    """Render a single-line frontmatter value as a YAML-safe scalar.

    A canonical Claude `description:` often contains a colon (e.g. "Phase: tasks") which, emitted as
    a plain scalar, makes the value parse as a nested mapping — Copilot then rejects the whole
    custom-agent frontmatter ("mapping values are not allowed", verified on Copilot CLI 1.0.63,
    wiki/log/2026-06-17). Quote (double-quoted, escaped) only when the value would break a plain
    scalar; leave safe scalars and flow collections (`[...]`/`{...}`, e.g. a `tools` list) untouched
    so their YAML structure is preserved.
    """
    if value == "" or value[0] in "[{":
        return value
    needs_quote = (
        ": " in value
        or value.endswith(":")
        or " #" in value
        or value[0] in "#&*!|>%@`\"'"
    )
    if not needs_quote:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _parse_simple_frontmatter(front: str) -> dict[str, str]:
    """Parses flat `key: value` lines of a frontmatter (no nesting needed for our assets)."""
    fields: dict[str, str] = {}
    for line in front.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


# --- Copilot hook wiring (FEAT-011, US1/US4; contract `copilot-hook-schema.md`) ---------------
#
# The Copilot hooks file (`.github/hooks/sertor-hooks.json`) has a SCHEMA DISTINCT from Claude's
# `.claude/settings.json`: a top-level `"version": 1`, a flat list of entries under each event name,
# `timeoutSec` (not Claude's `timeout`), and NO Claude-only fields (`shell`, `statusMessage`, nested
# `{matcher, hooks:[]}`). The audit (wiki/log/2026-06-17.md) showed the Claude-format static assets
# were silently DISCARDED by Copilot. `render_copilot_hooks` generates the native shape natively
# (no compatibility hack), from a single logical model shared with the Claude wiring.


@dataclass(frozen=True)
class HookEntrySpec:
    """Assistant-independent logical model of a single hook entry (data-model §2).

    Fonte unica from which both the Claude (nested) and the Copilot (flat) wiring are rendered, so
    the two cannot drift. `event` is the logical PascalCase name (`SessionStart`/`Stop`/
    `SessionEnd`/`PreToolUse`); `type` is `command` or `prompt` (prompt only for SessionStart on
    copilot-cli); `matcher` is optional (PreToolUse).
    """

    event: str
    type: str
    command: str
    timeout_sec: int
    matcher: str | None = None


def render_copilot_hooks(events: list[HookEntrySpec]) -> dict:
    """Renders the NATIVE Copilot hook wiring `dict` from logical entries (FR-001..005).

    Pure/deterministic, stdlib-only, no I/O. Output shape (contract `copilot-hook-schema.md` §1):

        {"version": 1, "hooks": {"<Event>": [{"type", "command", "timeoutSec", ["matcher"]}]}}

    MUST rules enforced by construction:
      - R1: top-level `"version": 1` is always present.
      - R2: each event maps to a FLAT list of entries (no nested `hooks[]`).
      - R3: entries carry only Copilot schema fields (`type`/`command`/`timeoutSec`/`matcher`) — no
        `shell`/`statusMessage`/nested wrapper.
      - R4: the timeout uses `timeoutSec`, never `timeout`.
    The logical PascalCase event name is kept verbatim (R5: the tests treat the documented aliases
    `agentStop`/`sessionEnd`/… as equivalent). `matcher` is emitted only when present.
    """
    hooks: dict[str, list[dict]] = {}
    for spec in events:
        # A `prompt`-type entry carries its payload in the `prompt` field; a `command`-type in
        # `command`. Copilot ignores a `command` field on a `type:"prompt"` hook → emitting the
        # payload under `command` silently dropped the SessionStart prompt (verified on Copilot CLI
        # 1.0.63, wiki/log/2026-06-17). The dataclass keeps one `command` field as the payload; the
        # rendered key follows the type.
        payload_key = "prompt" if spec.type == "prompt" else "command"
        entry: dict = {"type": spec.type, payload_key: spec.command, "timeoutSec": spec.timeout_sec}
        if spec.matcher is not None:
            entry["matcher"] = spec.matcher
        hooks.setdefault(spec.event, []).append(entry)
    return {"version": 1, "hooks": hooks}
