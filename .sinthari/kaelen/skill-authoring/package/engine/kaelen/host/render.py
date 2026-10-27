"""The closed wrapper set of the placement rule, rendered (specs/017 research R-5).

One pure function per wrapper. The item's body stays byte-identical inside its wrapper, except
`mcp-toml-entry`, which re-expresses the same server definition as a TOML table (spec 016 R-5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


class RenderError(Exception):
    """The item cannot be carried by this wrapper: it is reported, not installed (R-5)."""


@dataclass(frozen=True)
class Rendered:
    kind: str  # file | tree | section | member | element
    data: object  # bytes (file), str (section/member/element)
    address: str | None = None  # section identity
    path: list[str] = field(default_factory=list)  # JSON path of the container
    key: str | None = None  # JSON member name


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RenderError(f"the item is not UTF-8 text: {exc}") from exc


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    body = text.replace("\r\n", "\n")
    if not body.startswith("---\n"):
        return {}, text
    end = body.find("\n---\n", 4)
    if end < 0:
        return {}, text
    meta = {}
    for line in body[4:end].split("\n"):
        key, sep, value = line.partition(":")
        if sep and key.strip() and not line.startswith((" ", "\t")):
            meta[key.strip()] = value.strip().strip("\"'")
    return meta, body[end + 5 :]


def _command(context: dict, claude: bool) -> str:
    script = context["script"]
    root = "$CLAUDE_PROJECT_DIR/" if claude else ""
    quoted = f'"{root}{script}"'
    launcher = context.get("launcher")
    if launcher:  # the script runs with the capability's interpreter (specs/022 research R-4)
        return f'python "{root}{launcher}" --script {quoted}'
    return f"python {quoted}" if script.endswith(".py") else quoted


def _event(context: dict) -> str:
    section = context.get("section") or ""
    return section.split(".", 1)[1] if "." in section else section


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def verbatim(data, context):
    return Rendered("tree" if isinstance(data, list) else "file", data)


def markdown_section(data, context):
    return Rendered("section", _text(data), address=context["section"])


def git_section(data, context):
    """A section of a git file: the item's lines between hash markers (specs/025 R-4)."""
    return Rendered("section", _text(data), address=context["section"])


def copilot_instructions_file(data, context):
    if _text(data).replace("\r\n", "\n").startswith("---\n"):
        return Rendered("file", data)
    return Rendered("file", b'---\napplyTo: "**"\n---\n' + data)


def codex_agent_toml(data, context):
    meta, body = _frontmatter(_text(data))
    description = meta.get("description")
    if not description:
        raise RenderError("a Codex agent needs a description in the item's frontmatter")
    if "'''" in body:
        raise RenderError("the agent body contains ''' and cannot be a TOML literal string")
    name = meta.get("name") or context["name"]
    text = (
        f"name = {json.dumps(name, ensure_ascii=False)}\n"
        f"description = {json.dumps(description, ensure_ascii=False)}\n"
        f"developer_instructions = '''\n{body}'''\n"
    )
    return Rendered("file", text.encode("utf-8"))


def _definition(data) -> dict:
    try:
        value = json.loads(_text(data))
    except ValueError as exc:
        raise RenderError(f"the MCP server definition is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RenderError("the MCP server definition is not a JSON object")
    return value


def mcp_json_entry(data, context):
    _definition(data)
    return Rendered("member", _text(data).strip(), path=["mcpServers"], key=context["name"])


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list) and all(isinstance(v, (str, int, float, bool)) for v in value):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    raise RenderError(f"a value of the MCP definition has no TOML form here: {value!r}")


def mcp_toml_entry(data, context):
    definition = _definition(data)
    name = context["name"]
    lines = [f"[mcp_servers.{name}]"]
    tables = []
    for key, value in definition.items():
        if isinstance(value, dict):
            if not all(isinstance(v, str) for v in value.values()):
                raise RenderError(f"{key!r} must map names to strings")
            tables.append((key, value))
            continue
        lines.append(f"{json.dumps(key)} = {_toml_value(value)}")
    for key, value in tables:
        lines.append(f"[mcp_servers.{name}.{key}]")
        lines.extend(
            f"{json.dumps(k)} = {json.dumps(v, ensure_ascii=False)}" for k, v in value.items()
        )
    address = f"{context['capability']}/{name}"
    return Rendered("section", "\n".join(lines) + "\n", address=address)


_TOOL_EVENTS = ("PreToolUse", "PostToolUse")


def _hook_entry(context, claude: bool):
    event = _event(context)
    entry: dict = {}
    if event in _TOOL_EVENTS:
        entry["matcher"] = ""
    entry["hooks"] = [{"type": "command", "command": _command(context, claude)}]
    return Rendered("element", _json(entry), path=["hooks", event])


def claude_hook_entry(data, context):
    return _hook_entry(context, claude=True)


def codex_hook_entry(data, context):
    return _hook_entry(context, claude=False)


def copilot_hook_file(data, context):
    command = _command(context, claude=False)
    hook = {"type": "command", "bash": command, "powershell": command, "cwd": "."}
    doc = {"version": 1, "hooks": {_event(context): [hook]}}
    return Rendered("file", (_json(doc) + "\n").encode("utf-8"))


RENDERERS = {
    "verbatim": verbatim,
    "markdown-section": markdown_section,
    "git-section": git_section,
    "copilot-instructions-file": copilot_instructions_file,
    "codex-agent-toml": codex_agent_toml,
    "mcp-json-entry": mcp_json_entry,
    "mcp-toml-entry": mcp_toml_entry,
    "claude-hook-entry": claude_hook_entry,
    "codex-hook-entry": codex_hook_entry,
    "copilot-hook-file": copilot_hook_file,
}


def render(wrapper: str, data, context: dict) -> Rendered:
    return RENDERERS[wrapper](data, context)
