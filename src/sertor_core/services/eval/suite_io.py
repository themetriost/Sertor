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
    GraphSuiteValidationError,
    SuiteNotFoundError,
    SuiteValidationError,
    SuiteWriteError,
)
from sertor_core.services.eval.graph_eval import _SUPPORTED_RELATIONS
from sertor_core.services.eval.models import EvalCase, EvalSuite, GraphCase


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
    raw_graph = data.get("graph_case", [])
    if not isinstance(raw_graph, list):
        raise GraphSuiteValidationError(-1, "top-level `graph_case` must be an array of tables")
    graph_cases: list[GraphCase] = []
    for i, raw in enumerate(raw_graph):
        graph_cases.append(_parse_graph_case(i, raw))
    return EvalSuite(cases=tuple(cases), graph_cases=tuple(graph_cases))


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


def _parse_graph_case(index: int, raw: object) -> GraphCase:
    """Validate one `[[graph_case]]` table → `GraphCase`, or raise `GraphSuiteValidationError`.

    `expected` may be EMPTY (atteso «nessun chiamante» — REQ-004/005, asimmetria vs EvalCase). A
    relation outside the MVP set rejects the suite (REQ-005).
    """
    if not isinstance(raw, dict):
        raise GraphSuiteValidationError(index, "graph_case must be a table")
    relation = raw.get("relation")
    if not isinstance(relation, str) or not relation.strip():
        raise GraphSuiteValidationError(index, "missing or empty `relation`")
    if relation not in _SUPPORTED_RELATIONS:
        raise GraphSuiteValidationError(
            index,
            f"unsupported `relation`: {relation!r} "
            f"(allowed: {', '.join(sorted(_SUPPORTED_RELATIONS))})",
        )
    target = raw.get("target")
    if not isinstance(target, str) or not target.strip():
        raise GraphSuiteValidationError(index, "missing or empty `target`")
    expected = raw.get("expected")
    if not isinstance(expected, list):
        raise GraphSuiteValidationError(index, "missing or non-list `expected` (use [] for none)")
    for r in expected:
        if not isinstance(r, str) or not r.strip():
            raise GraphSuiteValidationError(index, f"invalid ref in `expected`: {r!r}")
    return GraphCase(relation=relation, target=target, expected=tuple(expected))


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
    """Serialize the suite: `[[case]]` (IR) then `[[graph_case]]` (navigation), hand-rolled.

    BOTH sections are emitted in a stable order so writing one never drops the other (DA-d,
    Principio VI/RNF-4). `graph_case.expected` may be an empty array.
    """
    lines = [
        "# Sertor eval suite. Versioned project data — no secrets.",
        '# [[case]]       = retrieval (IR) — query → expected paths (hit@k/MRR).',
        "# [[graph_case]] = graph navigation — relation + target → expected refs (P/R/F1).",
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
    for gc in suite.graph_cases:
        lines.append("[[graph_case]]")
        lines.append(f"relation = {_format_string(gc.relation)}")
        lines.append(f"target = {_format_string(gc.target)}")
        expected = ", ".join(_format_string(r) for r in gc.expected)
        lines.append(f"expected = [{expected}]")
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
    except (
        SuiteValidationError,
        GraphSuiteValidationError,
        SuiteNotFoundError,
        tomllib.TOMLDecodeError,
        OSError,
    ) as exc:
        raise SuiteWriteError(str(path)) from exc
    if reloaded.cases != suite.cases or reloaded.graph_cases != suite.graph_cases:
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
    write_suite(path, EvalSuite(cases=tuple(new_cases), graph_cases=suite.graph_cases))


def add_graph_case(path: Path, case: GraphCase) -> None:
    """Add a graph-navigation case (create the suite if absent), idempotent on `(relation, target)`.

    The IR `[[case]]` and existing `[[graph_case]]` are preserved (DA-d); a case with a
    `(relation, target)` already present is a no-op (no duplicate, REQ-041). New cases go in coda.
    """
    suite = load_suite(path) if path.exists() else EvalSuite()
    if any(
        gc.relation == case.relation and gc.target == case.target for gc in suite.graph_cases
    ):
        return  # idempotent: (relation, target) already in the suite
    write_suite(
        path,
        EvalSuite(cases=suite.cases, graph_cases=(*suite.graph_cases, case)),
    )


def amend_graph_case(
    path: Path, relation: str, target: str, expected: tuple[str, ...]
) -> None:
    """Amend the `expected` of the graph-case identified by `(relation, target)` (DA-c).

    The suite must exist and contain the case (else `GraphSuiteValidationError` naming it). Only the
    `expected` set is updated; the rest is preserved and the order of cases is stable. The IR
    `[[case]]` are preserved.
    """
    suite = load_suite(path)
    found = False
    new_graph: list[GraphCase] = []
    for gc in suite.graph_cases:
        if gc.relation == relation and gc.target == target:
            found = True
            new_graph.append(GraphCase(relation=relation, target=target, expected=expected))
        else:
            new_graph.append(gc)
    if not found:
        raise GraphSuiteValidationError(
            -1, f"no graph_case with relation={relation!r} target={target!r} to amend"
        )
    write_suite(path, EvalSuite(cases=suite.cases, graph_cases=tuple(new_graph)))
