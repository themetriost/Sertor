"""T024 — verify (il moat): verified/unverified, esclusione segnalata, idempotenza."""

from __future__ import annotations

from dataclasses import replace

from speclift.domain.models import Anchor, EarsRequirement, Quota
from speclift.stages.verify import verify


class FakeResolver:
    """Verifica un'àncora come `verified` se il suo file è nell'allowlist; idempotente."""

    def __init__(self, verified_files: set[str]) -> None:
        self._ok = verified_files

    def verify(self, anchor: Anchor) -> Anchor:
        status = "verified" if anchor.file in self._ok else "unverified"
        return replace(anchor, status=status)


def _req(rid: str, file: str) -> EarsRequirement:
    return EarsRequirement(
        id=rid,
        quota=Quota.IMPLEMENTATION,
        statement=f"req {rid}",
        anchor=Anchor(file=file, lines=(1, 2), granularity="hunk"),
    )


def test_verified_kept_unverified_excluded():
    reqs = [_req("A", "real.py"), _req("B", "ghost.py")]
    result = verify(reqs, FakeResolver({"real.py"}))
    assert [r.id for r in result.requirements] == ["A"]
    assert result.requirements[0].anchor.status == "verified"
    assert len(result.excluded) == 1
    assert "ghost.py" in result.excluded[0].reason


def test_excluded_is_reported_not_silent():
    reqs = [_req("B", "ghost.py")]
    result = verify(reqs, FakeResolver(set()))
    assert result.requirements == []
    assert result.excluded[0].statement == "req B"


def test_idempotent():
    reqs = [_req("A", "real.py")]
    resolver = FakeResolver({"real.py"})
    first = verify(reqs, resolver)
    second = verify(first.requirements, resolver)
    assert [r.id for r in second.requirements] == ["A"]
    assert second.excluded == []
