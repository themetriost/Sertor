"""T041 — US4 e2e: equivalenza JSON↔Markdown su fixture git reale."""

from __future__ import annotations

import json
import re

import pytest

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.adapters.git_diff import GitDiffSource
from speclift.domain.models import Symbol, TestRef
from speclift.pipeline import Components, RunOptions, run
from speclift.stages.render import render_json, render_markdown

from ._gitfixture import make_repo

pytestmark = pytest.mark.integration


class FakeLocator:
    def locate_symbols(self, file_path, identifiers, snippet):
        if "multiply" in identifiers and file_path == "calc.py":
            return [Symbol(name="multiply", path="calc.py", line=0)]
        return []

    def locate_tests(self, symbol):
        if symbol.name == "multiply":
            return [TestRef(name="test_calc", path="test_calc.py", covers_symbol="multiply")]
        return []


def test_json_and_markdown_have_same_requirements(tmp_path):
    fx = make_repo(tmp_path)
    comps = Components(
        diff_source=GitDiffSource(fx.path),
        locator=FakeLocator(),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(fx.path),
    )
    report = run(RunOptions(ref=fx.head_sha), comps)

    payload = json.loads(render_json(report))
    md = render_markdown(report)

    json_ids = {r["id"] for r in payload["requirements"]}
    md_ids = set(re.findall(r"^## (REQ-\S+) ·", md, flags=re.MULTILINE))
    assert json_ids == md_ids
    assert json_ids  # non vuoto: il report ha requisiti
