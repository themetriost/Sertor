"""The ordered checks of `kaelen validate` (data-model.md, "Verdict transitions")."""

from __future__ import annotations

import tomllib
from pathlib import Path

from kaelen import producer as producer_checks
from kaelen.contract import coherence, load_schema, supported_versions
from kaelen.contract.schema_eval import evaluate
from kaelen.outcome import CHECK_IDS, INVALID, UNABLE_TO_CHECK, VALID, Outcome, Problem


def validate(declaration: Path, producer: Path | None = None) -> Outcome:
    return validate_document(declaration, producer)[0]


def validate_document(
    declaration: Path, producer: Path | None = None
) -> tuple[Outcome, dict | None, bytes | None]:
    """The checks of `validate`, also returning what packaging needs (spec 015 R-6).

    Returns the outcome, the parsed document (only when valid) and the declaration's bytes as
    read (once): the bytes that are validated are the bytes that get packaged.
    """
    outcome, document, raw = _run(declaration, producer)
    if outcome.verdict != VALID:
        document = None
    return outcome, document, raw


def _run(declaration: Path, producer: Path | None) -> tuple[Outcome, dict | None, bytes | None]:
    outcome = Outcome(
        declaration=declaration.as_posix(),
        producer=producer.as_posix() if producer is not None else None,
        verdict=VALID,
    )

    raw: bytes | None = None
    document: dict | None = None

    def stop(verdict: str, reason: str | None = None):
        outcome.verdict = verdict
        outcome.reason = reason
        outcome.not_run = [c for c in CHECK_IDS if c not in outcome.ran]
        return outcome, document, raw

    # read
    try:
        raw = declaration.read_bytes()
    except OSError as exc:
        return stop(UNABLE_TO_CHECK, f"cannot open declaration: {exc.strerror or exc}")
    outcome.ran.append("read")
    try:
        document = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        outcome.errors.append(Problem("toml-syntax", "", f"not readable as TOML: {exc}"))
        return stop(INVALID)

    # contract-version
    outcome.ran.append("contract-version")
    supported = supported_versions()
    version = document.get("contract")
    if version is None:
        outcome.errors.append(
            Problem(
                "contract-missing",
                "contract",
                "the declaration does not state its contract version",
                tuple(str(v) for v in supported),
            )
        )
        return stop(INVALID)
    if isinstance(version, bool) or not isinstance(version, int) or version not in supported:
        outcome.errors.append(
            Problem(
                "contract-unsupported",
                "contract",
                f"contract version {version!r} is not supported; supported: "
                + ", ".join(str(v) for v in supported),
                tuple(str(v) for v in supported),
            )
        )
        return stop(INVALID)

    # schema
    outcome.ran.append("schema")
    for err in evaluate(load_schema(version), document):
        outcome.errors.append(Problem(err.rule, err.path, err.message, err.known))
    if outcome.errors:
        return stop(INVALID)

    # coherence
    outcome.ran.append("coherence")
    outcome.errors.extend(coherence.check(document))
    if outcome.errors:
        return stop(INVALID)

    # producer-sources, producer-undeclared
    if producer is not None:
        if not producer.is_dir():
            return stop(
                UNABLE_TO_CHECK, f"producer {producer.as_posix()!r} is not a readable directory"
            )
        outcome.ran.append("producer-sources")
        outcome.errors.extend(producer_checks.missing_sources(document, producer))
        outcome.ran.append("producer-undeclared")
        outcome.findings.extend(producer_checks.undeclared_files(document, producer))
        if outcome.errors:
            return stop(INVALID)

    outcome.summary = _summary(document)
    return stop(VALID)


def _summary(document: dict) -> dict:
    counts: dict[str, int] = {}
    for item in document["items"]:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    return {
        "contract": document["contract"],
        "node": document["node"],
        "capability": document["capability"],
        "version": document["version"],
        "targets": list(document["targets"]),
        "items": dict(sorted(counts.items())),
    }
