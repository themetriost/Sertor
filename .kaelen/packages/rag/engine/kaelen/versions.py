"""Versions and version ranges of capabilities (specs/029 R-3).

A version is semver (`MAJOR.MINOR.PATCH`, optionally `-prerelease` and `+build`); a range is a
comma-separated list of comparators (`>=1.2,<2`). A version that is not semver is never compared:
the caller names it.
"""

from __future__ import annotations

import re

_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$"
)
_SHORT = re.compile(r"^(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?(?:\.(0|[1-9]\d*))?$")
_OPS = (">=", "<=", "==", "!=", ">", "<")


class NotSemver(ValueError):
    """A version that cannot be compared."""


def parse(text: str) -> tuple | None:
    """(major, minor, patch, prerelease identifiers) or None when not semver."""
    m = _SEMVER.match(str(text).strip())
    if m is None:
        return None
    pre = tuple(int(p) if p.isdigit() else p for p in m.group(4).split(".")) if m.group(4) else ()
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), pre


def _bound(text: str) -> tuple | None:
    """A bound in a range: full semver, or a short form (`1`, `1.2`) filled with zeros."""
    full = parse(text)
    if full is not None:
        return full
    m = _SHORT.match(text.strip())
    if m is None:
        return None
    return int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0), ()


def parse_range(text: str) -> list[tuple[str, tuple]] | None:
    """[(operator, bound)] or None when the range cannot be read."""
    out = []
    for part in str(text).split(","):
        part = part.strip()
        op = next((o for o in _OPS if part.startswith(o)), None)
        if op is None:
            return None
        bound = _bound(part[len(op) :])
        if bound is None:
            return None
        out.append((op, bound))
    return out or None


def _key(v: tuple) -> tuple:
    """Semver precedence: a pre-release sorts before its release; identifiers compare per semver."""
    major, minor, patch, pre = v
    if not pre:
        return (major, minor, patch, 1, ())
    ids = tuple((0, p, "") if isinstance(p, int) else (1, 0, p) for p in pre)
    return (major, minor, patch, 0, ids)


def satisfies(version: str, range_text: str) -> bool:
    """Whether `version` is in `range_text`; raises NotSemver for a version that is not semver.

    A pre-release satisfies the range only if a bound is a pre-release of its MAJOR.MINOR.PATCH.
    """
    v = parse(version)
    if v is None:
        raise NotSemver(f"{version!r} is not a semver version")
    bounds = parse_range(range_text)
    if bounds is None:
        raise ValueError(f"{range_text!r} is not a version range")
    if v[3] and not any(b[3] and b[:3] == v[:3] for _, b in bounds):
        return False
    k = _key(v)
    checks = {
        ">=": lambda b: k >= b,
        ">": lambda b: k > b,
        "<=": lambda b: k <= b,
        "<": lambda b: k < b,
        "==": lambda b: k == b,
        "!=": lambda b: k != b,
    }
    return all(checks[op](_key(b)) for op, b in bounds)
