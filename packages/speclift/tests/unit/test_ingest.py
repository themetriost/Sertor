"""T011 — ingest con fake DiffSource: commit/range/staged, ref invalido, diff vuoto."""

from __future__ import annotations

import pytest

from speclift.domain.errors import InvalidRefError
from speclift.domain.models import STAGED_REF
from speclift.stages.ingest import ingest


class FakeDiffSource:
    def __init__(self, text: str = "diff --git a/x b/x\n", *, invalid: bool = False) -> None:
        self.text = text
        self.invalid = invalid
        self.calls: list[tuple[str, str]] = []

    def raw_diff(self, ref: str, kind: str) -> str:
        self.calls.append((ref, kind))
        if self.invalid:
            raise InvalidRefError(f"ref non risolto: {ref}")
        return self.text


def test_commit_default_head():
    src = FakeDiffSource()
    raw = ingest(src, ref=None, staged=False, range_spec=None)
    assert raw.kind == "commit"
    assert raw.ref == "HEAD"
    assert src.calls == [("HEAD", "commit")]


def test_explicit_commit():
    src = FakeDiffSource()
    raw = ingest(src, ref="abc123", staged=False, range_spec=None)
    assert raw.kind == "commit"
    assert raw.ref == "abc123"


def test_range():
    src = FakeDiffSource()
    raw = ingest(src, ref=None, staged=False, range_spec="main..HEAD")
    assert raw.kind == "range"
    assert raw.ref == "main..HEAD"
    assert src.calls == [("main..HEAD", "range")]


def test_staged_uses_sentinel():
    src = FakeDiffSource()
    raw = ingest(src, ref="ignored", staged=True, range_spec=None)
    assert raw.kind == "staged"
    assert raw.ref == STAGED_REF
    assert src.calls == [(STAGED_REF, "staged")]


def test_invalid_ref_raises():
    src = FakeDiffSource(invalid=True)
    with pytest.raises(InvalidRefError):
        ingest(src, ref="nope", staged=False, range_spec=None)


def test_empty_diff_is_not_error():
    src = FakeDiffSource(text="   \n")
    raw = ingest(src, ref="HEAD", staged=False, range_spec=None)
    assert raw.is_empty
