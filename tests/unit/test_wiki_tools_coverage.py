"""Coverage block format and set semantics (E10-FEAT-062, T003/T004/T006).

The contract these guard is `specs/124-copertura-changeset-scan/contracts/sertor-covers.1.md`.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from sertor_core.wiki_tools.coverage import (
    ABSENT,
    covers,
    has_block,
    has_entry,
    parse,
    serialize,
)
from sertor_core.wiki_tools.vcs import content_ids

# --- format: serialise / parse / round-trip -------------------------------------------------


def test_round_trip_preserves_the_set():
    items = {("src/a.py", "aaa111"), ("wiki/b.md", "bbb222")}
    assert parse(serialize(items)) == items


def test_serialisation_is_deterministic():
    """The block lands in a versioned file: two runs covering the same thing must not differ."""
    items = [("src/z.py", "z"), ("src/a.py", "a")]
    assert serialize(items) == serialize(reversed(items))


def test_nothing_covered_writes_no_block():
    assert serialize([]) == ""


def test_path_containing_at_sign_survives():
    """`rpartition`, not `split`: the LAST `@` separates, so `@` inside a path stays valid."""
    items = {("src/pkg@2/mod.py", "abc123")}
    assert parse(serialize(items)) == items


def test_deleted_item_is_coverable():
    """A deletion is work, so it must be expressible — otherwise it could never be recorded."""
    items = {("src/gone.py", ABSENT)}
    assert parse(serialize(items)) == items


def test_union_across_several_blocks_in_one_file():
    """A day's partition holds several entries; their coverages compose."""
    text = serialize({("a", "1")}) + "\n\nprosa fra le voci\n\n" + serialize({("b", "2")})
    assert parse(text) == {("a", "1"), ("b", "2")}


def test_text_without_a_block_covers_nothing():
    assert parse("# Log\n\n## [2026-07-29] record | senza copertura\n") == set()


def test_malformed_lines_are_skipped_not_raised():
    """Runs inside a Stop-time gate: a half-written block must narrow coverage, never crash."""
    text = "<!-- sertor-covers/1\nsenza-chiocciola\n@\nsrc/ok.py@abc\n-->"
    assert parse(text) == {("src/ok.py", "abc")}


# --- set semantics ----------------------------------------------------------------------------


def test_same_path_different_content_is_not_covered():
    """The core of the feature: coverage is about content, so it expires on its own."""
    coverage = {("src/a.py", "old")}
    assert covers(coverage, "src/a.py", "old")
    assert not covers(coverage, "src/a.py", "new")


def test_union_is_commutative_and_idempotent():
    a, b = {("x", "1")}, {("y", "2")}
    assert a | b == b | a
    assert a | a == a


# --- has_block / has_entry --------------------------------------------------------------------


def test_has_block_distinguishes_absent_from_empty():
    assert has_block(serialize({("a", "1")}))
    assert not has_block("## [2026-07-29] record | voce senza blocco\n")


def test_has_entry_uses_the_HOST_format_not_ours():
    """Derived from `log_format`: hardcoding `## [` would be silently wrong on other hosts."""
    ours = "## [{date}] {op} | {title}"
    theirs = "### {date} · {op} — {title}"
    text_theirs = "### 2026-07-29 · record — qualcosa\n"
    assert has_entry(text_theirs, theirs)
    assert not has_entry(text_theirs, ours)


def test_has_entry_is_false_on_an_empty_or_seed_only_partition():
    """An empty partition is not a recording: it must not earn the compatibility rule."""
    fmt = "## [{date}] {op} | {title}"
    assert not has_entry("", fmt)
    assert not has_entry("# Log 2026-07-29\n\nLog entries for 2026-07-29.\n", fmt)


def test_has_entry_is_conservative_without_a_literal_prefix():
    """No anchor to match on → claim nothing, so the gate stays strict rather than lax."""
    assert not has_entry("qualunque cosa\n", "{date} {op}")


# --- content identity (T006) --------------------------------------------------------------------


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), capture_output=True, check=True)
    return tmp_path


def test_content_id_matches_the_committed_identity_when_untouched(tmp_path):
    """Same value git itself would report — the property the whole design rests on."""
    host = _repo(tmp_path)
    (host / "a.txt").write_text("contenuto\n", encoding="utf-8")
    for args in (["add", "-A"], ["-c", "user.email=t@e.invalid", "-c", "user.name=T",
                                 "commit", "-qm", "seed"]):
        subprocess.run(["git", *args], cwd=str(host), capture_output=True, check=True)
    proc = subprocess.run(["git", "rev-parse", "HEAD:a.txt"], cwd=str(host),
                          capture_output=True, text=True, check=True)
    assert content_ids(["a.txt"], host) == {"a.txt": proc.stdout.strip()}


def test_content_id_changes_with_the_content(tmp_path):
    host = _repo(tmp_path)
    (host / "a.txt").write_text("prima\n", encoding="utf-8")
    before = content_ids(["a.txt"], host)
    (host / "a.txt").write_text("dopo\n", encoding="utf-8")
    assert content_ids(["a.txt"], host) != before


def test_absent_path_gets_the_sentinel(tmp_path):
    host = _repo(tmp_path)
    assert content_ids(["mai-esistito.txt"], host) == {"mai-esistito.txt": ABSENT}


def test_many_paths_are_hashed_in_one_call(tmp_path, monkeypatch):
    """One process for N paths: this runs at the end of every turn, where startup dominates."""
    host = _repo(tmp_path)
    for name in ("a.txt", "b.txt", "c.txt"):
        (host / name).write_text(name, encoding="utf-8")

    import sertor_core.wiki_tools.vcs as vcs_mod

    calls: list[list[str]] = []
    real = vcs_mod.run_git

    def counting(args, cwd, **kwargs):
        calls.append(args)
        return real(args, cwd, **kwargs)

    monkeypatch.setattr(vcs_mod, "run_git", counting)
    ids = vcs_mod.content_ids(["a.txt", "b.txt", "c.txt"], host)
    assert len(ids) == 3
    assert len(calls) == 1, f"attesa UNA invocazione, ottenute {len(calls)}"
