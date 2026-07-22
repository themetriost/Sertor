"""Daily distill floor — BLOCK the merge until the day has a distill (E10-FEAT-039).

The `distill` ritual step is judgment (semantic) and was silently skippable for weeks. This hook gives
it a hard floor at the one irreversible, consequential moment — the **merge** (a step's delivery to
the mainline): you MUST NOT merge on a day with no `distill` entry.

Modes (`--mode`, rendered NATIVELY per assistant):
  - **PreToolUse** — the teeth: inspects the Bash command; if it is a delivery merge
    (`gh pr merge`, or `git merge <feature-branch>` — NOT `git merge <mainline>`, which is just an
    update) and today's log partition has NO `distill` entry, it **denies** the tool call with a
    reason telling the agent to distill (or log a reasoned "no") first. No deadlock: distilling
    needs pages + `append-log`, never a merge.
  - **SessionStart** — a non-blocking heads-up when today has no distill yet (so the agent knows it
    will be gated at merge time).

The gate is deterministic, read from `wiki.config.toml` (host-agnostic, Principio X): a `distill`
entry in today's dated log partition. The hook never performs or judges the distill (D↔N) — it only
demands it, and attaches the `distill-audit` candidates as an advisory HINT (CLI vehicle, Principio
XI). If the floor can't be determined (no config, single-file log) it FAILS OPEN (never traps a
merge). Exit 0 always; stdlib only; breadcrumb on config error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

_MAX_ADVISORY = 5
_MAINLINE = {"master", "main", "origin/master", "origin/main", "upstream/master", "upstream/main"}
_GH_PR_MERGE = re.compile(r"\bgh\s+pr\s+merge\b")
_GIT_MERGE = re.compile(r"\bgit\s+merge\b([^&|;]*)")


def _is_delivery_merge(command: str) -> bool:
    """True when `command` delivers a branch to the mainline (a real merge), not just updating it.

    `gh pr merge` is always a delivery. `git merge <ref>` is a delivery UNLESS `<ref>` is a mainline
    ref (`git merge master` on a feature branch just pulls mainline in). No ref / only flags (e.g.
    `git merge --abort`) → not a delivery.
    """
    if _GH_PR_MERGE.search(command):
        return True
    for match in _GIT_MERGE.finditer(command):
        args = match.group(1).split()
        ref = next((a for a in args if not a.startswith("-")), None)
        if ref is not None and ref not in _MAINLINE:
            return True
    return False


def _load_wiki_layout(config: Path) -> tuple[str, str] | None:
    """`(wiki_root, log_dir)` from `wiki.config.toml` (host-agnostic); `None` if unreadable."""
    try:
        with config.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    root = data.get("root")
    if not isinstance(root, str) or not root:
        return None
    log_dir = data.get("log_dir")
    return root, (log_dir if isinstance(log_dir, str) else "")


_ENTRY = re.compile(r"^## \[[^\]]*\]\s+(?P<op>\S+)", re.MULTILINE)


def _has_distill_today(host_root: Path, wiki_root: str, log_dir: str, today: date) -> bool | None:
    """Whether today's dated partition holds a `distill` entry. `None` = undeterminable (fail open).

    `None` when rotation is off (single-file log — no reliable daily scope) or the partition is
    unreadable: the gate then does NOT block (never trap a merge on an unenforceable floor).
    """
    if not log_dir:
        return None  # single-file log: cannot date-scope "today"
    partition = host_root / wiki_root / log_dir / f"{today.isoformat()}.md"
    if not partition.is_file():
        return False  # rotation on, no partition today → no distill logged today
    try:
        text = partition.read_text(encoding="utf-8")
    except OSError:
        return None
    return any(op == "distill" for op in _ENTRY.findall(text))


def _audit_advisory(host_root: Path, config: Path) -> list[str]:
    """Best-effort deterministic HINT: candidate entity names from `distill-audit` (CLI vehicle).

    Prefers the high-precision wikilink-bearing candidates. Never raises (advisory, not the gate).
    """
    sertor_dir = host_root / ".sertor"
    base = (["uv", "run", "--project", str(sertor_dir), "sertor-wiki-tools"]
            if sertor_dir.is_dir() else ["sertor-wiki-tools"])
    cmd = [*base, "distill-audit", "--config", str(config), "--root", str(host_root), "--json"]
    try:
        out = subprocess.run(cmd, cwd=str(host_root), capture_output=True, text=True,
                             timeout=90).stdout
    except Exception:
        return []
    lines = [ln for ln in out.splitlines() if ln.strip()]
    try:
        data = json.loads(lines[-1]) if lines else {}
    except Exception:
        return []
    if data.get("schema") != "wiki.distill_audit/1":
        return []
    candidates = data.get("candidates") or []
    precise = [c for c in candidates if c.get("signal") in ("wikilink", "both")]
    ranked = precise or candidates
    return [str(c.get("name", "")).strip() for c in ranked[:_MAX_ADVISORY] if c.get("name")]


def _reason(host_root: Path, config: Path, *, blocking: bool) -> str:
    advisory = _audit_advisory(host_root, config)
    hint = f" Advisory candidates (deterministic hint — judge them): {', '.join(advisory)}." \
        if advisory else ""
    lead = ("BLOCKED: daily distill floor not met — you may NOT merge today without a distill."
            if blocking else "Daily distill floor: today has no distill entry yet (merges gated).")
    return (
        f"{lead} Before merging, either (a) perform the distill step — give durable entities their "
        "own concepts/tech page and log it — or (b) log a reasoned 'no' that NAMES the candidates "
        "considered and why they are not durable: "
        "`sertor-wiki-tools append-log --entry-op distill --title \"no: <why>\"`. Then merge."
        f"{hint}"
    )


def _resolve_config(root: Path) -> Path | None:
    config = root / "wiki" / "wiki.config.toml"
    if config.is_file():
        return config
    legacy = root / "wiki.config.toml"
    return legacy if legacy.is_file() else None


def _host_root(event: dict) -> Path:
    root = _hooklib.project_root()
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(event.get("cwd"), str):
        root = Path(event["cwd"])
    try:
        return root.resolve()
    except Exception:
        return root


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="PreToolUse", choices=["PreToolUse", "SessionStart"])
    parser.add_argument("--assistant", default="claude")
    args, _ = parser.parse_known_args()
    event = _hooklib.read_event()

    # PreToolUse: only a delivery-merge command is in scope; everything else fails open immediately.
    if args.mode == "PreToolUse":
        tool_input = event.get("tool_input")
        command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
        if not command or not _is_delivery_merge(command):
            return

    root = _host_root(event)
    config = _resolve_config(root)
    if config is None:
        return  # no host wiki config → nothing to enforce (fail open)

    layout = _load_wiki_layout(config)
    if layout is None:
        _hooklib.write_breadcrumb("distill-floor", "wiki.config.toml unreadable")
        return  # fail open
    wiki_root, log_dir = layout
    has_distill = _has_distill_today(root, wiki_root, log_dir, datetime.now().date())

    if has_distill is None or has_distill:
        return  # floor met, or undeterminable → do not block

    if args.mode == "PreToolUse":
        reason = _reason(root, config, blocking=True)
        if args.assistant == "copilot":
            print(reason)  # copilot preToolUse is fail-closed: any stdout denies the tool
        else:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
        return

    # SessionStart heads-up (non-blocking).
    msg = _reason(root, config, blocking=False)
    if args.assistant == "copilot":
        print(json.dumps({"additionalContext": msg}))
    else:
        print(msg)


if __name__ == "__main__":
    _hooklib.run("distill-floor", main)
