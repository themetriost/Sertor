"""T013 (integration) — adapter GitDiffSource su un repo git reale (fixture temporanea)."""

from __future__ import annotations

import pytest

from speclift.adapters.git_diff import GitDiffSource
from speclift.domain.errors import InvalidRefError
from speclift.stages.parse_diff import parse_diff

from ._gitfixture import _git, make_repo

pytestmark = pytest.mark.integration


def test_commit_diff_contains_new_function(tmp_path):
    fx = make_repo(tmp_path)
    src = GitDiffSource(fx.path)
    text = src.raw_diff(fx.head_sha, "commit")
    assert "diff --git" in text
    assert "def multiply" in text


def test_range_diff(tmp_path):
    fx = make_repo(tmp_path)
    src = GitDiffSource(fx.path)
    text = src.raw_diff(f"{fx.base_sha}..{fx.head_sha}", "range")
    assert "multiply" in text


def test_parse_real_commit_diff(tmp_path):
    fx = make_repo(tmp_path)
    src = GitDiffSource(fx.path)
    cs = parse_diff_from(src, fx.head_sha)
    paths = {f.path for f in cs.files}
    assert "calc.py" in paths
    assert "test_calc.py" in paths
    ids = [i for f in cs.files for h in f.hunks for i in h.candidate_identifiers]
    assert "multiply" in ids


def test_invalid_ref_raises(tmp_path):
    fx = make_repo(tmp_path)
    src = GitDiffSource(fx.path)
    with pytest.raises(InvalidRefError):
        src.raw_diff("deadbeefdeadbeef", "commit")


def test_non_utf8_diff_does_not_crash(tmp_path):
    """G0 (regressione): un diff con byte non-UTF-8 non deve far crashare l'adapter.

    `git_diff` cattura byte e decodifica UTF-8 con `errors="replace"`. Prima della fix usava
    l'encoding di locale (`text=True` → cp1252 su Windows) e sollevava `UnicodeDecodeError` sul
    byte `0x8f` (invalido sia in UTF-8 sia in cp1252), degenerando poi in `raw.text is None`.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    # File di testo con un byte non-UTF-8 (0x8f, niente NUL → git lo tratta come testo nel diff).
    (repo / "weird.txt").write_bytes(b"prima riga\nbyte strano: \x8f qui\n")
    _git(repo, "add", "weird.txt")
    _git(repo, "commit", "-q", "-m", "add weird bytes")
    head = _git(repo, "rev-parse", "HEAD")

    text = GitDiffSource(repo).raw_diff(head, "commit")  # NON deve sollevare

    assert isinstance(text, str)
    assert "weird.txt" in text
    assert "�" in text  # il byte non-decodificabile è sostituito, non esplode


def parse_diff_from(src: GitDiffSource, ref: str):
    from speclift.domain.models import RawDiff

    return parse_diff(RawDiff(ref=ref, kind="commit", text=src.raw_diff(ref, "commit")))
