"""T031 — CLI: mappatura errori → exit code (2/3/4/5) e percorso felice (0)."""

from __future__ import annotations

from dataclasses import replace

from speclift.adapters.ears_requirements import StubEarsAuthor
from speclift.cli import main
from speclift.domain.errors import (
    EarsAuthorUnavailableError,
    InvalidRefError,
    RagUnavailableError,
)
from speclift.domain.models import Anchor, Symbol, TestRef
from speclift.pipeline import Components

_DIFF = """diff --git a/calc.py b/calc.py
index 111..222 100644
--- a/calc.py
+++ b/calc.py
@@ -1,1 +1,2 @@
 x = 1
+def multiply(a, b): return a * b
"""


class DiffSrc:
    def __init__(self, text=_DIFF, invalid=False):
        self.text, self.invalid = text, invalid

    def raw_diff(self, ref, kind):
        if self.invalid:
            raise InvalidRefError("bad ref")
        return self.text


class LocOk:
    def locate_symbols(self, file_path, identifiers, snippet):
        return [Symbol(name="multiply", path="calc.py", line=0)]

    def locate_tests(self, symbol):
        return [TestRef(name="t", path="test_calc.py", covers_symbol="multiply")]


class LocDown:
    def locate_symbols(self, *a):
        raise RagUnavailableError("rag down")

    def locate_tests(self, *a):
        raise RagUnavailableError("rag down")


class AuthorDown:
    def author(self, bundle):
        raise EarsAuthorUnavailableError("requirements unavailable")


class ResolverYes:
    def verify(self, anchor: Anchor) -> Anchor:
        return replace(anchor, status="verified")


def _components(diff=None, loc=None, author=None, resolver=None):
    return Components(
        diff_source=diff or DiffSrc(),
        locator=loc or LocOk(),
        author=author or StubEarsAuthor(),
        resolver=resolver or ResolverYes(),
    )


def test_invalid_ref_exit_2():
    code = main(["badref"], components=_components(diff=DiffSrc(invalid=True)))
    assert code == 2


def test_rag_down_exit_3():
    code = main(["HEAD"], components=_components(loc=LocDown()))
    assert code == 3


def test_ears_author_down_exit_4():
    code = main(["HEAD"], components=_components(author=AuthorDown()))
    assert code == 4


def test_bundle_contract_error_exit_5():
    foreign = Anchor(file="evil.py", lines=(1, 1), granularity="hunk")

    class RogueAuthor:
        def author(self, bundle):
            from speclift.domain.models import EarsRequirement, Quota
            from speclift.domain.ports import EarsAuthoringResult

            return EarsAuthoringResult(
                requirements=[
                    EarsRequirement(id="X", quota=Quota.IMPLEMENTATION, statement="s", anchor=foreign)
                ]
            )

    code = main(["HEAD"], components=_components(author=RogueAuthor()))
    assert code == 5


def test_happy_path_exit_0(capsys):
    code = main(["HEAD", "--format", "json"], components=_components())
    assert code == 0
    out = capsys.readouterr().out
    assert '"version": "1"' in out
    assert '"requirements"' in out


def test_empty_diff_exit_0(capsys):
    code = main(["HEAD", "--format", "json"], components=_components(diff=DiffSrc(text="\n")))
    assert code == 0
    assert '"requirements": []' in capsys.readouterr().out
