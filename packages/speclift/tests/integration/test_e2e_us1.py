"""T032 — e2e US1 su fixture git generica (NON Kaelen): commit → report JSON con àncore verificate.

Hermetico (Constitution IV): usa l'adapter `git` reale e il verifier filesystem reale; il solo
componente RAG è un fake in-memory (la CLI RAG non è invocabile in modo deterministico nei test). La
proprietà del moat verificata: ogni requisito emesso ha un'àncora che risolve; nessuna àncora inventata
sopravvive.
"""

from __future__ import annotations

import json

import pytest

from speclift.adapters.anchor_fs import FilesystemAnchorResolver
from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.adapters.git_diff import GitDiffSource
from speclift.domain.models import Symbol, TestRef
from speclift.pipeline import Components, RunOptions, run
from speclift.serialize import report_to_dict

from ._gitfixture import make_repo

pytestmark = pytest.mark.integration


class FakeLocator:
    """Localizza il simbolo `multiply` nel file toccato + il suo test (simula il RAG, hermetico)."""

    def locate_symbols(self, file_path, identifiers, snippet):
        if "multiply" in identifiers and file_path == "calc.py":
            return [Symbol(name="multiply", path="calc.py", line=0)]
        return []

    def locate_tests(self, symbol):
        if symbol.name == "multiply":
            return [TestRef(name="test_calc", path="test_calc.py", covers_symbol="multiply")]
        return []


def _components(repo_path):
    return Components(
        diff_source=GitDiffSource(repo_path),
        locator=FakeLocator(),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(repo_path),
    )


def test_e2e_produces_verified_anchored_report(tmp_path):
    fx = make_repo(tmp_path)
    report = run(RunOptions(ref=fx.head_sha), _components(fx.path))

    assert report.requirements, "ci si attende almeno un requisito ancorato"
    # Ogni requisito emesso ha un'àncora VERIFICATA che risolve su file reali del changeset.
    for req in report.requirements:
        assert req.anchor.status == "verified"
        assert req.anchor.file in {"calc.py", "test_calc.py"}

    # Il report è serializzabile (contratto output) e cita il simbolo localizzato.
    payload = report_to_dict(report)
    assert payload["changeset_ref"] == fx.head_sha
    assert any(r["anchor"]["symbol"] == "multiply" for r in payload["requirements"])


def test_e2e_invented_anchor_does_not_survive(tmp_path):
    """Un'àncora che non risolve sul filesystem viene esclusa, non emessa come confermata."""
    fx = make_repo(tmp_path)

    class GhostLocator:
        def locate_symbols(self, file_path, identifiers, snippet):
            return [Symbol(name="ghost", path="does_not_exist.py", line=0)]

        def locate_tests(self, symbol):
            return []

    comps = Components(
        diff_source=GitDiffSource(fx.path),
        locator=GhostLocator(),
        author=StubEarsAuthor(),
        resolver=FilesystemAnchorResolver(fx.path),
    )
    report = run(RunOptions(ref=fx.head_sha), comps)
    # Nessun simbolo same-file → fallback hunk su calc.py (verificabile) resta confermato;
    # l'evidenza cross-layer inventata (does_not_exist.py) non genera àncore confermate.
    for req in report.requirements:
        assert req.anchor.status == "verified"
        assert req.anchor.file != "does_not_exist.py"


def test_e2e_json_serializes(tmp_path):
    fx = make_repo(tmp_path)
    report = run(RunOptions(ref=fx.head_sha), _components(fx.path))
    text = json.dumps(report_to_dict(report))
    assert "multiply" in text
