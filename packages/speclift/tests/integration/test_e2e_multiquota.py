"""T035 — US2 e2e: il report contiene le tre quote per gli elementi rilevanti."""

from __future__ import annotations

import pytest

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.adapters.git_diff import GitDiffSource
from speclift.domain.models import ALL_QUOTAS, Symbol, TestRef
from speclift.pipeline import Components, RunOptions, run

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


def test_e2e_three_quotas(tmp_path):
    fx = make_repo(tmp_path)
    comps = Components(
        diff_source=GitDiffSource(fx.path),
        locator=FakeLocator(),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(fx.path),
    )
    report = run(RunOptions(ref=fx.head_sha), comps)

    by_source: dict[str, set] = {}
    for r in report.requirements:
        by_source.setdefault(r.source_item, set()).add(r.quota)

    assert by_source, "atteso almeno un elemento con requisiti"
    # Ogni elemento confermato copre tutte e tre le quote.
    for quotas in by_source.values():
        assert quotas == set(ALL_QUOTAS)
