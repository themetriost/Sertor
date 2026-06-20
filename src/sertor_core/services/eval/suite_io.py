"""Read/write the eval suite `eval/suite.toml` (065, contract artifacts-toml.md).

Read with `tomllib` (stdlib); WRITE with a minimal hand-rolled TOML serializer (research DA-a — no
`tomli-w`, Principio II/III: the schema is a flat array of `[[case]]`). Every write is validated by
ROUND-TRIP (re-read with `tomllib`); a non-parsing result raises `SuiteWriteError` rather than
persisting an ambiguous file (fail-safe, Principio VI). Non-distruttivo/idempotente: existing cases
and their order are preserved, dedup is by `query` (REQ-011).
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from sertor_core.domain.errors import (
    SuiteNotFoundError,
    SuiteValidationError,
    SuiteWriteError,
)
from sertor_core.services.eval.models import EvalCase, EvalSuite


def load_suite(path: Path) -> EvalSuite:
    """Load and validate the suite at `path` (REQ-001/004).

    File absent → `SuiteNotFoundError` (REQ-032). A malformed case (missing `query`/`expected`,
    wrong type, empty `expected`, empty path) → `SuiteValidationError` naming the offending case.
    """
    if not path.exists():
        raise SuiteNotFoundError(str(path))
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    raw_cases = data.get("case", [])
    if not isinstance(raw_cases, list):
        raise SuiteValidationError(-1, "top-level `case` must be an array of tables")
    cases: list[EvalCase] = []
    for i, raw in enumerate(raw_cases):
        cases.append(_parse_case(i, raw))
    return EvalSuite(cases=tuple(cases))


def _parse_case(index: int, raw: object) -> EvalCase:
    """Validate one `[[case]]` table → `EvalCase`, or raise `SuiteValidationError` (REQ-004)."""
    if not isinstance(raw, dict):
        raise SuiteValidationError(index, "case must be a table")
    query = raw.get("query")
    if not isinstance(query, str) or not query.strip():
        raise SuiteValidationError(index, "missing or empty `query`")
    expected = raw.get("expected")
    if not isinstance(expected, list) or not expected:
        raise SuiteValidationError(index, "missing or empty `expected` (need at least one path)")
    for p in expected:
        if not isinstance(p, str) or not p.strip():
            raise SuiteValidationError(index, f"invalid path in `expected`: {p!r}")
    kind = raw.get("kind")
    if kind is not None and not isinstance(kind, str):
        raise SuiteValidationError(index, "`kind` must be a string when present")
    return EvalCase(query=query, expected=tuple(expected), kind=kind)


def _escape_basic(value: str) -> str:
    """Escape a TOML basic string: backslash first, then double-quote."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_string(value: str) -> str:
    """Render a string as a TOML value: multiline basic for newlines, basic otherwise."""
    if "\n" in value:
        # Basic multiline: escape backslash/quote, keep newlines literal inside `"""…"""`.
        body = value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return f'"""\n{body}"""'
    return f'"{_escape_basic(value)}"'


def _serialize_suite(suite: EvalSuite) -> str:
    """Serialize the suite as an array of `[[case]]` tables (hand-rolled, schema-flat)."""
    lines = [
        "# Sertor eval suite. Versioned project data — no secrets.",
        '# kind is optional (e.g. "symbol"/"nl"). Paths are POSIX, relative to the indexed root.',
        "",
    ]
    for c in suite.cases:
        lines.append("[[case]]")
        lines.append(f"query = {_format_string(c.query)}")
        expected = ", ".join(_format_string(p) for p in c.expected)
        lines.append(f"expected = [{expected}]")
        if c.kind is not None:
            lines.append(f"kind = {_format_string(c.kind)}")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_suite(path: Path, suite: EvalSuite) -> None:
    """Persist the suite with round-trip validation (REQ-011, fail-safe).

    Writes the serialized text, then re-reads it with `load_suite`; if the round-trip fails (parse
    error, or the loaded suite differs from what we meant to write) → `SuiteWriteError`, leaving no
    ambiguous TOML behind beyond the failed file (the caller is informed and can fix the input).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _serialize_suite(suite)
    path.write_text(text, encoding="utf-8")
    try:
        reloaded = load_suite(path)
    except (SuiteValidationError, SuiteNotFoundError, tomllib.TOMLDecodeError, OSError) as exc:
        raise SuiteWriteError(str(path)) from exc
    if reloaded.cases != suite.cases:
        raise SuiteWriteError(str(path))


def add_case(path: Path, case: EvalCase) -> None:
    """Add a case to the suite (create the suite if absent), idempotent on `query` (REQ-010/011).

    Existing cases and their order are preserved; a case with a `query` already present is a no-op
    (no duplicate). New cases go in coda.
    """
    suite = load_suite(path) if path.exists() else EvalSuite(cases=())
    if any(c.query == case.query for c in suite.cases):
        return  # idempotent: query already in the suite
    write_suite(path, EvalSuite(cases=(*suite.cases, case)))


def amend_case(
    path: Path,
    query: str,
    *,
    expected: tuple[str, ...] | None = None,
    kind: str | None = None,
) -> None:
    """Amend the case identified by `query` (REQ-051 feedback path).

    The suite must exist and contain the case (else `SuiteNotFoundError` / `SuiteValidationError`).
    Only the provided fields are updated (`expected`/`kind`); the rest is preserved. The order of
    cases is stable. `kind=None` is treated as "leave unchanged" (use `expected` to change paths).
    """
    suite = load_suite(path)
    found = False
    new_cases: list[EvalCase] = []
    for c in suite.cases:
        if c.query == query:
            found = True
            new_cases.append(
                EvalCase(
                    query=c.query,
                    expected=expected if expected is not None else c.expected,
                    kind=kind if kind is not None else c.kind,
                )
            )
        else:
            new_cases.append(c)
    if not found:
        raise SuiteValidationError(-1, f"no case with query {query!r} to amend")
    write_suite(path, EvalSuite(cases=tuple(new_cases)))
