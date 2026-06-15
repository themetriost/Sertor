"""US3 — coesistenza dei blocchi rituali in `CLAUDE.md` (T041, FR-015/DA-b).

Un `CLAUDE.md` che contiene già il blocco `SERTOR:WIKI-RITUAL` → l'install di
`sertor-flow` aggiunge un blocco `SERTOR:SDLC-RITUAL` DISTINTO senza toccare il blocco
wiki; un secondo run NON duplica il blocco SDLC.
"""
from __future__ import annotations

from pathlib import Path

from sertor_flow.__main__ import main
from sertor_flow.install_governance import MARKER_END_SDLC, MARKER_START_SDLC
from tests.conftest import FakeSpecifyRunner

# Wiki markers as written by `sertor` (kept verbatim here to test coexistence).
_WIKI_START = "<!-- SERTOR:WIKI-RITUAL START -->"
_WIKI_END = "<!-- SERTOR:WIKI-RITUAL END -->"


def _claude_md_with_wiki_block(root: Path) -> Path:
    claude_md = root / "CLAUDE.md"
    claude_md.write_text(
        "# Host project\n\nUser prose at the top.\n\n"
        f"{_WIKI_START}\nwiki ritual body\n{_WIKI_END}\n",
        encoding="utf-8",
    )
    return claude_md


def test_sdlc_block_added_without_touching_wiki(tmp_path: Path):
    claude_md = _claude_md_with_wiki_block(tmp_path)
    original = claude_md.read_text(encoding="utf-8")

    rc = main(["install", "--target", str(tmp_path)], runner=FakeSpecifyRunner())
    assert rc == 0

    text = claude_md.read_text(encoding="utf-8")
    # Wiki block preserved verbatim (still present, untouched).
    assert _WIKI_START in text
    assert _WIKI_END in text
    assert "wiki ritual body" in text
    assert original in text  # the whole original prefix is preserved byte-for-byte
    # SDLC block added, distinct from the wiki block.
    assert MARKER_START_SDLC in text
    assert MARKER_END_SDLC in text
    assert MARKER_START_SDLC != _WIKI_START


def test_sdlc_block_not_duplicated_on_rerun(tmp_path: Path):
    _claude_md_with_wiki_block(tmp_path)
    assert main(["install", "--target", str(tmp_path)], runner=FakeSpecifyRunner()) == 0
    assert main(["install", "--target", str(tmp_path)], runner=FakeSpecifyRunner()) == 0

    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.count(MARKER_START_SDLC) == 1
    assert text.count(MARKER_END_SDLC) == 1
    # Wiki block also still single.
    assert text.count(_WIKI_START) == 1
