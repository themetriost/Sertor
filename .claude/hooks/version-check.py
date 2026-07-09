"""Deterministic end-of-session version-update check — a thin HTTP+file wrapper. Portable (A-09).

SessionEnd hook that checks whether the installed Sertor is older than the latest published version
(E2-FEAT-013). Consumes NO CLI vehicle and NO LLM: a simple HTTPS GET of the remote `/VERSION`, reads
the install-time stamp, compares them, persists the verdict. NEVER imports `sertor_core`.

Orchestration: reuse `.version-check.json` if `checked_at` is within ~24h (unless forced) and re-confirm
vs the current stamp; else GET the URL (env override honoured **only over https** — A-08 security),
short timeout; compare semantically; write `.sertor/.version-check.json`. Exit 0 always; GET/parse
failure → verdict `unknown`, no error.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib  # noqa: E402

_DEFAULT_URL = "https://raw.githubusercontent.com/themetriost/Sertor/master/VERSION"


def _compare_version(a: str, b: str) -> int | None:
    """-1 if a<b, 0 if ==, 1 if a>b; None if unparsable. Numeric segments, lexical fallback (D-4)."""
    if not a or not b:
        return None
    sa, sb = a.strip().split("."), b.strip().split(".")
    for i in range(max(len(sa), len(sb))):
        pa = sa[i] if i < len(sa) else "0"
        pb = sb[i] if i < len(sb) else "0"
        if pa.isdigit() and pb.isdigit():
            ia, ib = int(pa), int(pb)
            if ia != ib:
                return -1 if ia < ib else 1
        else:
            if pa != pb:
                return -1 if pa < pb else 1
    return 0


def _read_stamp(path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except Exception:
        return ""


def main() -> None:
    event = _hooklib.read_event()
    root = _hooklib.project_root()
    if not os.environ.get("CLAUDE_PROJECT_DIR") and isinstance(event.get("cwd"), str):
        from pathlib import Path

        root = Path(event["cwd"])
    sertor_dir = root / ".sertor"
    state_path = sertor_dir / ".version-check.json"

    installed = _read_stamp(sertor_dir / ".sertor-version")
    dimensions: dict[str, str] = {}
    if installed:
        dimensions["sertor"] = installed
    flow = _read_stamp(sertor_dir / ".sertor-flow-version")
    if flow:
        dimensions["sertor-flow"] = flow

    # cache: reuse if checked_at within ~24h and not forced
    latest = ""
    cache_fresh = False
    if state_path.is_file() and not os.environ.get("SERTOR_VERSION_CHECK_FORCE"):
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            checked_at = prev.get("checked_at")
            if checked_at:
                dt = datetime.strptime(checked_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                if 0 <= age_h < 24:
                    cache_fresh = True
                    latest = str(prev.get("latest") or "")
        except Exception:
            cache_fresh = False

    if not cache_fresh:
        # A-08: honour the env override ONLY over TLS; else fall back to the trusted default.
        override = os.environ.get("SERTOR_VERSION_CHECK_URL", "")
        url = override if override.startswith("https://") else _DEFAULT_URL
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310 — https-only enforced
                latest = resp.read().decode("utf-8").strip()
        except Exception:
            latest = ""  # offline / GET failed → inconclusive, verdict unknown

    verdict = "unknown"
    if installed and latest:
        cmp = _compare_version(installed, latest)
        if cmp is None:
            verdict = "unknown"
        elif cmp < 0:
            verdict = "behind"
        elif cmp == 0:
            verdict = "up-to-date"
        else:
            verdict = "ahead"

    sertor_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "schema": "version.check/1",
        "verdict": verdict,
        "installed": installed,
        "latest": latest,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if dimensions:
        state["dimensions"] = dimensions
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


if __name__ == "__main__":
    _hooklib.run("version-check", main)
