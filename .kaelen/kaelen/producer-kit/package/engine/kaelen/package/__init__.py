"""`kaelen package`: a self-contained package for one capability (specs/015-packaging-injection).

The order is the data model's "Verdict transitions": validate (the very checks of
`kaelen validate`, never restated here) → declaration inside the producer → content plan →
package location → inject and write in staging → atomic swap.
"""

from __future__ import annotations

from pathlib import Path

from kaelen import provenance
from kaelen.outcome import (
    INTERNAL,
    INVALID,
    PACKAGE_CHECK_IDS,
    PACKAGED,
    REFUSED,
    UNABLE_TO_CHECK,
    WOULD_PACKAGE,
    PackageOutcome,
    Problem,
)
from kaelen.package import distribution, inject, location, record
from kaelen.package.plan import leave_out, plan_content, targets_report
from kaelen.placement import RuleError, rule_digest
from kaelen.validate import validate_document

DECLARATION = "declaration.toml"


def package(
    declaration: Path,
    producer: Path,
    engine_version: str,
    dry_run: bool = False,
    sign_key: Path | None = None,
    keygen: provenance.Keygen | None = None,
    git=None,
) -> PackageOutcome:
    outcome = PackageOutcome(
        declaration=declaration.as_posix(),
        producer=producer.as_posix(),
        dry_run=dry_run,
        verdict=WOULD_PACKAGE if dry_run else PACKAGED,
    )

    def stop(verdict: str, reason: str | None = None) -> PackageOutcome:
        outcome.verdict = verdict
        outcome.reason = reason
        outcome.not_run = [c for c in PACKAGE_CHECK_IDS if c not in outcome.ran]
        return outcome

    checked, document, raw = validate_document(declaration, producer)
    outcome.ran = list(checked.ran)
    outcome.errors = list(checked.errors)
    outcome.findings = list(checked.findings)
    if checked.verdict == INVALID:
        return stop(REFUSED)
    if checked.verdict == UNABLE_TO_CHECK:
        return stop(UNABLE_TO_CHECK, checked.reason)

    if not _inside(declaration, producer):
        reason = "the declaration must lie inside the producer repository it describes"
        outcome.errors.append(Problem("declaration-outside-producer", "", reason))
        return stop(UNABLE_TO_CHECK, reason)

    keygen = keygen or provenance.DEFAULT_KEYGEN
    signer = document.get("signer")
    missing = _signing_problem(signer, sign_key, keygen)
    if missing is not None:
        outcome.errors.append(Problem("signing-unavailable", "signer", missing))
        return stop(REFUSED)

    planned, problems = plan_content(document, producer)
    if problems:
        outcome.errors.extend(problems)
        return stop(REFUSED)
    git = git or provenance.DEFAULT_GIT
    planned, outcome.left_out, problems, unread = leave_out(planned, document, producer, git)
    if problems:
        outcome.errors.extend(problems)
        return stop(REFUSED)
    if outcome.left_out:
        caches = sum(1 for e in outcome.left_out if e["reason"] == "python-cache")
        outcome.findings.append(
            Problem(
                "left-out",
                "",
                f"{len(outcome.left_out)} file(s) left out of the package: "
                f"{len(outcome.left_out) - caches} ignored by the producer's repository, "
                f"{caches} Python cache(s); see left_out",
            )
        )
    if unread:
        outcome.findings.append(
            Problem(
                "ignore-rules-unread",
                "",
                "git could not say what the producer's repository ignores; only Python caches "
                "were left out",
            )
        )
    try:
        content = [(rel, path.read_bytes()) for rel, path in planned]
    except OSError as exc:
        return stop(UNABLE_TO_CHECK, f"cannot read a declared source: {exc}")
    outcome.findings.extend(_line_endings([rel for rel, _ in planned], producer, git))

    capability = document["capability"]
    outcome.ran.append("location")
    state = location.inspect(producer, capability)
    if state.state == location.FOREIGN:
        outcome.errors.append(
            Problem(
                "location-foreign",
                "",
                f"{location.relative(capability)}: {state.detail}; packaging never overwrites "
                "content it did not produce",
            )
        )
        return stop(REFUSED)

    try:
        targets, gaps = targets_report(document, producer)
        digest = rule_digest()
    except RuleError as exc:
        return stop(INTERNAL, str(exc))
    outcome.findings.extend(gaps)
    dist, dist_findings = distribution.files(document)
    outcome.findings.extend(dist_findings)

    outcome.ran.append("inject")
    try:
        if dry_run:
            engine = inject.engine_files(engine_version)
        else:
            engine = _write_staging(producer, capability, engine_version, raw, content + dist)
    except (inject.InjectionError, OSError) as exc:
        if not dry_run:
            location.discard_staging(producer, capability)
        return stop(INTERNAL, str(exc))

    files = [(DECLARATION, raw), *content, *dist, *engine]
    rec = record.build_record(
        document=document,
        engine_version=engine_version,
        engine_digest=record.digest_tree([(p, d) for p, d in engine if p.startswith("engine/")]),
        rule_digest=digest,
        producer_state=record.producer_state(raw, content),
        targets=targets,
        files=[{"path": p, "size": len(d), "sha256": record.sha256(d)} for p, d in files],
    )

    if not dry_run:
        try:
            staging = location.staging_dir(producer, capability)
            (staging / record.FILENAME).write_bytes(record.serialise(rec))
            if signer:  # beside the record, not in it: it signs the record (specs/028 R-2)
                try:
                    keygen.sign(sign_key, staging / record.FILENAME)
                except (OSError, provenance.NotChecked) as exc:
                    location.discard_staging(producer, capability)
                    outcome.errors.append(Problem("signing-unavailable", "signer", str(exc)))
                    return stop(REFUSED)
            outcome.ran.append("write")
            location.swap(producer, capability)
        except OSError as exc:
            location.discard_staging(producer, capability)
            return stop(INTERNAL, f"cannot write the package: {exc}")

    outcome.package = location.relative(capability)
    outcome.files = rec["files"]
    outcome.targets = targets
    outcome.size = {
        "total": sum(len(d) for _, d in files),
        "engine": sum(len(d) for p, d in engine),
    }
    outcome.record = rec
    outcome.launch = distribution.launch(document, distribution.PYPROJECT in dict(dist))
    return stop(outcome.verdict)


def _line_endings(planned: list[str], producer: Path, git) -> list[Problem]:
    """Content files whose bytes git would change on commit (specs/033 R-5).

    Asked of git itself: the hash with the path's filters (eol conversion) against the hash of
    the bytes as they are. The package keeps the working copy; the finding says so.
    """
    rels = [rel.removeprefix("content/") for rel in planned]
    if not rels:
        return []
    paths = "".join(r + "\n" for r in rels)
    code, filtered = git.run(["hash-object", "--stdin-paths"], producer, input=paths)
    code2, raw = git.run(["hash-object", "--no-filters", "--stdin-paths"], producer, input=paths)
    a, b = filtered.split(), raw.split()
    if code != 0 or code2 != 0 or len(a) != len(rels) or len(b) != len(rels):
        return []  # git cannot answer: nothing is claimed either way
    return [
        Problem(
            "line-endings",
            rel,
            "git would commit different bytes for this file (line endings or a clean filter); "
            "the package carries the working copy's",
        )
        for rel, x, y in zip(rels, a, b, strict=True)
        if x != y
    ]


def _signing_problem(signer, sign_key, keygen) -> str | None:
    """Why this package cannot be signed as its declaration asks (specs/028 FR-013)."""
    if sign_key is not None and not signer:
        return "--sign-key was given but the declaration names no signer"
    if not signer:
        return None
    if sign_key is None:
        return f"the declaration names signer {signer!r}: pass --sign-key with that signer's key"
    if not keygen.available():
        return "ssh-keygen is not available: it is needed to sign the package"
    if not Path(sign_key).is_file():
        return f"the signing key {Path(sign_key).as_posix()} is not a file"
    return None


def _write_staging(producer, capability, engine_version, raw, content):
    """Recover from an earlier run, then build the whole package in staging."""
    location.recover(producer, capability)
    staging = location.staging_dir(producer, capability)
    staging.mkdir(parents=True)
    engine = inject.inject_engine(staging, engine_version)
    (staging / DECLARATION).write_bytes(raw)
    for rel, data in content:
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return engine


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
