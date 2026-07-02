"""T013 — ingest dell'output SpecLift: mapping + fail-loud (versione/changeset/malformato)."""

from __future__ import annotations

import json

import pytest

from specaudit.adapters.speclift_json import SpecLiftJsonSource
from specaudit.domain.errors import (
    ChangesetMismatchError,
    SpecLiftArtifactError,
    SpecLiftVersionError,
)
from tests.specaudit.helpers import speclift_output


def _write(tmp_path, data) -> str:
    p = tmp_path / "report.speclift.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_maps_requirements_and_drifts(tmp_path):
    path = _write(tmp_path, speclift_output("abc123"))
    ref, items = SpecLiftJsonSource(path).load(None)
    assert ref == "abc123"
    assert len(items) == 3  # 2 requirements + 1 drift
    assert items[0].origin == "requirement"
    assert items[-1].origin == "drift"
    # test object → citazione stringa
    assert items[0].anchor.test == "tests/test_view.py::test_flush"
    # àncora inalterata: lo status del drift resta unverified
    assert items[-1].anchor.status == "unverified"


def test_missing_file_fails_loud(tmp_path):
    with pytest.raises(SpecLiftArtifactError):
        SpecLiftJsonSource(str(tmp_path / "nope.json")).load(None)


def test_bad_version_fails_loud(tmp_path):
    path = _write(tmp_path, speclift_output("abc123", version="2"))
    with pytest.raises(SpecLiftVersionError):
        SpecLiftJsonSource(path).load(None)


def test_changeset_mismatch_fails_loud(tmp_path):
    path = _write(tmp_path, speclift_output("abc123"))
    with pytest.raises(ChangesetMismatchError):
        SpecLiftJsonSource(path).load("different-ref")


def test_malformed_json_fails_loud(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(SpecLiftArtifactError):
        SpecLiftJsonSource(str(p)).load(None)
