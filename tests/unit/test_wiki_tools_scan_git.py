"""`scan` in derived mode: the anchor is a fact, not a clock (E10-FEAT-045, T014-T016).

The two tests that define the feature are `test_answer_does_not_depend_on_file_clocks` (SC-002) and
`test_merge_then_pull_does_not_block_the_session` (the deadlock itself). The rest guard the pieces.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.scan import (
    ANCHOR_GIT,
    ANCHOR_MTIME,
    REASON_LOG_NEVER_COMMITTED,
    REASON_NOT_A_REPOSITORY,
    scan,
)

_CONFIG = """\
profile = "code+doc"
root = "wiki"
language = "en"
log_dir = "log"
source_dirs = ["src", "specs"]
exclude = ["__pycache__"]

[[taxonomy]]
name = "Concepts"
dir = "concepts"
type = "concept"
"""


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, check=True)


def _run_out(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
    return proc.stdout


def _host(tmp_path: Path, *, git: bool = True) -> Path:
    """A minimal wiki host; optionally a git repository."""
    (tmp_path / "wiki" / "log").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "specs").mkdir()
    (tmp_path / "wiki.config.toml").write_text(_CONFIG, encoding="utf-8")
    if git:
        _run(tmp_path, "init", "-q")
        _run(tmp_path, "config", "user.email", "t@example.invalid")
        _run(tmp_path, "config", "user.name", "T")
        (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
        _run(tmp_path, "add", "-A")
        _run(tmp_path, "commit", "-qm", "seed")
    return tmp_path


def _profile(host: Path):
    return load_profile(host / "wiki.config.toml")


def _write_log(host: Path, day: str = "2026-07-27") -> Path:
    path = host / "wiki" / "log" / f"{day}.md"
    path.write_text(f"# Log {day}\n\n## [{day}] record | entry\n", encoding="utf-8")
    return path


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


# --- the anchor is derived --------------------------------------------------------------------

def test_work_and_log_in_the_same_commit_leaves_nothing_pending(tmp_path):
    host = _host(tmp_path)
    (host / "src" / "feature.py").write_text("x = 1\n", encoding="utf-8")
    _write_log(host, _today())
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "work + log")

    result = scan(_profile(host))
    assert result.pending == 0
    assert result.anchor_kind == ANCHOR_GIT
    assert result.anchor_ref  # derived anchors must be citable (C-2)


def test_work_committed_without_a_log_entry_is_pending(tmp_path):
    """The gate must keep biting when it should (SC-007)."""
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")

    (host / "src" / "later.py").write_text("y = 2\n", encoding="utf-8")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "work, unrecorded")

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.pending_paths == ["src/later.py"]


def test_uncommitted_work_is_pending(tmp_path):
    """At Stop time the session's work is typically NOT committed — the case the gate exists for."""
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")

    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.pending_paths == ["src/wip.py"]


def test_todays_uncommitted_entry_satisfies_the_gate_without_a_commit(tmp_path):
    """FR-004: demanding a commit would be a new deadlock in place of the old one."""
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")

    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")
    assert scan(_profile(host)).pending == 1

    _write_log(host, _today())  # written, NOT committed
    assert scan(_profile(host)).pending == 0


def test_an_entry_from_another_day_does_not_count_but_is_named(tmp_path):
    """FR-004a: otherwise the journal looks updated while the gate blocks anyway."""
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")

    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")
    _write_log(host, "2026-07-24")  # uncommitted, but NOT today

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.stale_recording == "wiki/log/2026-07-24.md"


def test_deleted_source_file_counts_as_pending(tmp_path):
    host = _host(tmp_path)
    (host / "src" / "doomed.py").write_text("k = 0\n", encoding="utf-8")
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "seed work")

    (host / "src" / "doomed.py").unlink()

    result = scan(_profile(host))
    assert result.pending_paths == ["src/doomed.py"]


# --- the two that define the feature ------------------------------------------------------------

def test_answer_does_not_depend_on_file_clocks(tmp_path):
    """SC-002. The old implementation compared mtimes, so this assertion could not hold."""
    host = _host(tmp_path)
    (host / "src" / "feature.py").write_text("x = 1\n", encoding="utf-8")
    _write_log(host, _today())
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "work + log")

    before = scan(_profile(host))

    # Make every source file look newer than the journal — the exact shape a merge+pull produces.
    future = time.time() + 10_000
    for path in list((host / "src").rglob("*")) + list((host / "specs").rglob("*")):
        if path.is_file():
            os.utime(path, (future, future))
    past = time.time() - 10_000
    for path in (host / "wiki" / "log").glob("*.md"):
        os.utime(path, (past, past))

    after = scan(_profile(host))
    assert after.pending == before.pending == 0
    assert after.anchor_ref == before.anchor_ref


def test_merge_then_pull_does_not_block_the_session(tmp_path):
    """The deadlock itself: a session must be able to close on its own last merge.

    Reproduces the shape reported seven times in one day by the Acta node — work and journal
    delivered together on a branch, merged into the mainline, then every merged file rewritten on
    disk (which is what `git pull` does to the working copy).
    """
    host = _host(tmp_path)
    _run(host, "checkout", "-q", "-b", "feature")
    (host / "src" / "feature.py").write_text("x = 1\n", encoding="utf-8")
    _write_log(host, _today())
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "work + log")
    _run(host, "checkout", "-q", "master")
    _run(host, "merge", "-q", "--no-ff", "-m", "merge feature", "feature")

    # `git pull` rewrites the merged files: same content, brand-new clocks, arbitrary order.
    now = time.time()
    for path in list((host / "src").rglob("*")) + list((host / "wiki" / "log").glob("*.md")):
        if path.is_file():
            os.utime(path, (now, now))

    assert scan(_profile(host)).pending == 0


# --- ignored files, absorbed for free (E10-FEAT-048) --------------------------------------------

def test_vcs_ignored_files_are_not_pending(tmp_path):
    """A scratch nobody will ever deliver must not block a session."""
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")

    (host / "src" / "ignored").mkdir()
    (host / "src" / "ignored" / "draft.md").write_text("scratch\n", encoding="utf-8")

    assert scan(_profile(host)).pending == 0


def test_paths_are_named_and_truncation_is_declared(tmp_path):
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")
    for i in range(12):
        (host / "src" / f"f{i:02d}.py").write_text("v = 1\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.pending == 12                      # the COUNT is always exact (C-5)
    assert len(result.pending_paths) == 10           # the LIST is what gets truncated
    assert result.pending_truncated == 2
    assert result.pending == len(result.pending_paths) + result.pending_truncated


# --- the declared proxy (Principle X + XIV) -----------------------------------------------------

def test_non_repository_host_falls_back_and_says_so(tmp_path):
    """A host without version control is a SUPPORTED shape, not a fault."""
    host = _host(tmp_path, git=False)
    log = _write_log(host, "2026-07-01")
    work = host / "src" / "wip.py"
    work.write_text("z = 3\n", encoding="utf-8")
    # Set the clocks explicitly: in proxy mode the answer DEPENDS on them, which is the point.
    os.utime(log, (time.time() - 1000, time.time() - 1000))
    os.utime(work, (time.time(), time.time()))

    result = scan(_profile(host))
    assert result.anchor_kind == ANCHOR_MTIME
    assert result.anchor_fallback_reason == REASON_NOT_A_REPOSITORY  # never a mute proxy (C-3)
    assert result.pending >= 1


def test_line_ending_only_change_is_not_work(tmp_path):
    """A file whose ONLY difference is line-ending normalisation must not block a session.

    Found on the very first real use of this gate: `git status` reports such a file as modified,
    but nobody authored anything — there is nothing to record. `git diff` is content-aware and does
    not report it, which is why the two halves of the work-tree scan use different commands.
    """
    host = _host(tmp_path)
    _run(host, "config", "core.autocrlf", "input")
    (host / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    target = host / "src" / "normalized.py"
    target.write_bytes(b"a = 1\nb = 2\n")
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "seed with LF")

    target.write_bytes(b"a = 1\r\nb = 2\r\n")  # same content, CRLF endings
    assert "normalized.py" in _run_out(host, "status", "--porcelain")  # git DOES flag it

    result = scan(_profile(host))
    assert result.pending == 0, f"line-ending-only change counted as work: {result.pending_paths}"


def test_proxy_mode_also_names_the_paths(tmp_path):
    """FR-006 is not conditional on the mode: only the "is it ignored?" filter is (A-6)."""
    host = _host(tmp_path, git=False)
    log = _write_log(host, "2026-07-01")
    work = host / "src" / "wip.py"
    work.write_text("z = 3\n", encoding="utf-8")
    os.utime(log, (time.time() - 1000, time.time() - 1000))
    os.utime(work, (time.time(), time.time()))

    result = scan(_profile(host))
    assert result.pending_paths == ["src/wip.py"]


def test_host_template_without_files_placeholder_is_left_verbatim(tmp_path):
    """FR-008: a host that knows nothing about this change must not have to do anything.

    `message` is the HOST's localised string. Appending to it unconditionally would silently change
    a contract the host owns — which is why the naming lives in the structured field instead.
    """
    host = _host(tmp_path)
    (host / "wiki.config.toml").write_text(
        _CONFIG + '\n[strings]\npending = "Pendenti: {n}"\n', encoding="utf-8",
    )
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")
    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.message == "Pendenti: 1"
    assert result.pending_paths == ["src/wip.py"]  # named, but not by mangling the host's string


def test_host_template_with_files_placeholder_opts_in(tmp_path):
    """A host that DOES want the names inline controls where they go."""
    host = _host(tmp_path)
    (host / "wiki.config.toml").write_text(
        _CONFIG + '\n[strings]\npending = "Pendenti: {n} -> {files}"\n', encoding="utf-8",
    )
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log only")
    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")

    assert scan(_profile(host)).message == "Pendenti: 1 -> src/wip.py"


def test_repository_whose_log_was_never_committed_declares_the_reason(tmp_path):
    host = _host(tmp_path)
    (host / "src" / "wip.py").write_text("z = 3\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.anchor_kind == ANCHOR_MTIME
    assert result.anchor_fallback_reason == REASON_LOG_NEVER_COMMITTED
    assert result.anchor_ref is None


# --- E10-FEAT-062: coverage instead of presence -------------------------------------------------
# These exercise the REAL path (`append_log` writes the coverage) rather than hand-written journals:
# a hand-written entry carries no coverage block and would exercise the compatibility shim instead
# of the feature itself.

import importlib  # noqa: E402
from datetime import date  # noqa: E402

from sertor_core.wiki_tools.coverage import parse as _parse_coverage  # noqa: E402
from sertor_core.wiki_tools.registry import append_log  # noqa: E402
from sertor_core.wiki_tools.scan import DETERMINATION_FAILED, DETERMINATION_OK  # noqa: E402

_scan_mod = importlib.import_module("sertor_core.wiki_tools.scan")


def _host_git(tmp_path):
    """A host whose journal HAS been delivered, so `scan` runs in derived (git) mode.

    Without a committed journal the anchor falls back to the declared proxy and the coverage branch
    is never exercised — the tests would pass while testing nothing.
    """
    host = _host(tmp_path)
    _write_log(host, "2026-07-01")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "journal delivered")
    return host


def _record(host, title="voce"):
    return append_log(_profile(host), "record", title)


def test_work_authored_after_a_recording_comes_back_pending(tmp_path):
    """Scenario G — the defect itself: writing the entry switched the gate off for the day."""
    host = _host_git(tmp_path)
    (host / "src" / "prima.py").write_text("a = 1\n", encoding="utf-8")
    _record(host, "copre prima.py")

    (host / "src" / "dopo.py").write_text("b = 2\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.pending_paths == ["src/dopo.py"]
    assert result.legacy_coverage == 0


def test_a_recording_covers_what_existed_when_it_was_written(tmp_path):
    host = _host_git(tmp_path)
    (host / "src" / "prima.py").write_text("a = 1\n", encoding="utf-8")
    res = _record(host)
    assert res.covered == 1
    assert scan(_profile(host)).pending == 0


def test_an_item_recorded_then_edited_again_is_pending(tmp_path):
    """Coverage is about content: the same path with new content is not the same work."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    _record(host)
    assert scan(_profile(host)).pending == 0

    (host / "src" / "f.py").write_text("a = 2\n", encoding="utf-8")
    assert scan(_profile(host)).pending_paths == ["src/f.py"]


def test_two_recordings_in_one_day_compose_by_union(tmp_path):
    host = _host_git(tmp_path)
    (host / "src" / "uno.py").write_text("a = 1\n", encoding="utf-8")
    first = _record(host, "prima")
    (host / "src" / "due.py").write_text("b = 2\n", encoding="utf-8")
    second = _record(host, "seconda")

    assert first.covered == 1
    assert second.covered == 1  # only the delta, because the first coverage already applies
    assert scan(_profile(host)).pending == 0


def test_an_empty_partition_does_not_satisfy_the_gate(tmp_path):
    """H/I: an empty partition is not a recording — it must not earn the compatibility rule."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    (host / "wiki" / "log" / (_today() + ".md")).write_text("", encoding="utf-8")

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.legacy_coverage == 0


def test_a_whitespace_touch_does_not_satisfy_the_gate(tmp_path):
    """J: the partition exists and is touched, but nothing was written."""
    host = _host_git(tmp_path)
    _write_log(host, _today())
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log today")
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    partition = host / "wiki" / "log" / (_today() + ".md")
    partition.write_text(partition.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    assert scan(_profile(host)).pending == 1


def test_a_second_session_is_not_covered_by_the_first(tmp_path):
    """R3: two sessions share the day's partition; one recording must not cover the other's work."""
    host = _host_git(tmp_path)
    (host / "src" / "sessione1.py").write_text("a = 1\n", encoding="utf-8")
    _record(host, "sessione 1")
    (host / "src" / "sessione2.py").write_text("b = 2\n", encoding="utf-8")

    assert scan(_profile(host)).pending_paths == ["src/sessione2.py"]


def test_committed_unrecorded_work_is_covered_then_new_work_is_not(tmp_path):
    """F: already-delivered work is pending until a recording covers it — and only that."""
    host = _host_git(tmp_path)
    (host / "src" / "consegnato.py").write_text("a = 1\n", encoding="utf-8")
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "work, unrecorded")
    (host / "src" / "altro.py").write_text("b = 2\n", encoding="utf-8")
    _record(host, "copre entrambi")

    assert scan(_profile(host)).pending == 0
    (host / "src" / "terzo.py").write_text("c = 3\n", encoding="utf-8")
    assert scan(_profile(host)).pending_paths == ["src/terzo.py"]


def test_coverage_does_not_depend_on_the_partition_date(tmp_path):
    """The date is the file's name, not a rule: coverage in another day's partition still counts."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    append_log(_profile(host), "record", "voce datata prima", on_date=date(2026, 7, 15))

    assert scan(_profile(host)).pending == 0


# --- compatibility rule (declared, narrow, self-extinguishing) -----------------------------------


def test_legacy_undelivered_entry_is_honoured_AND_declared(tmp_path):
    """An entry written before coverage existed keeps working — and the derogation is visible."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    _write_log(host, _today())  # never delivered, an entry with NO coverage block

    result = scan(_profile(host))
    assert result.pending == 0
    assert result.legacy_coverage == 1, "la deroga deve essere dichiarata, non implicita"


def test_a_delivered_legacy_entry_grants_no_derogation(tmp_path):
    """Once delivered the anchor moves past it: the shim extinguishes itself."""
    host = _host_git(tmp_path)
    _write_log(host, _today())
    _run(host, "add", "-A")
    _run(host, "commit", "-qm", "log today")
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.pending == 1
    assert result.legacy_coverage == 0


# --- determination: a clean verdict cannot come from a failed check ------------------------------


def test_a_failed_check_is_declared_not_reported_as_clean(tmp_path, monkeypatch):
    """US2: `pending == 0` is a claim about the world ONLY when the determination succeeded."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")

    real = _scan_mod.run_git

    def flaky(args, cwd, **kwargs):
        if args and args[0] in {"diff", "status"}:
            return 128, ""  # git: "Unable to create index.lock: File exists"
        return real(args, cwd, **kwargs)

    monkeypatch.setattr(_scan_mod, "run_git", flaky)
    result = scan(_profile(host))
    assert result.determination == DETERMINATION_FAILED
    assert result.determination_reason
    assert result.schema == "wiki.scan/1"  # never bumped, even on the failure path


def test_counter_proof_the_same_tree_with_git_healthy_reports_the_work(tmp_path):
    """The other half of the previous test: that `0` was NOT the truth."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")

    result = scan(_profile(host))
    assert result.determination == DETERMINATION_OK
    assert result.pending == 1


def test_the_coverage_block_lands_in_the_journal(tmp_path):
    """US3: the recording says what it covers, in the artefact itself."""
    host = _host_git(tmp_path)
    (host / "src" / "f.py").write_text("a = 1\n", encoding="utf-8")
    _record(host)

    text = (host / "wiki" / "log" / (_today() + ".md")).read_text(encoding="utf-8")
    assert {path for path, _ in _parse_coverage(text)} == {"src/f.py"}
