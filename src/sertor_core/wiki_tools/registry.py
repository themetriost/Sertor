"""Mechanical, idempotent log and index writes (FR-008, SC-002).

`append_log` appends **one** log entry to the right place: in **rotation** mode (`log_dir`
configured) the daily partition for the entry date, otherwise the single log file (back-compat).
Receives an optional **curated body** (lead/bullets/outcome, `log-craft` format) and places it
**without reformatting** — the deterministic↔judgment boundary: the code does the placement,
the LLM provides the content. `migrate_log` retroactively splits the monolithic log into
partitions. `upsert_index` inserts/updates a link+summary row in the index. Everything is
**idempotent**. A log entry's identity is its **heading** (`date + op + title`); a page's identity
is its relative POSIX path.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.contracts import AppendLogResult, MigrateResult, UpsertIndexResult
from sertor_core.wiki_tools.profile import WikiProfile

_PARTITION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ENTRY_HEADING = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]")


def _partition_seed(day: date) -> str:
    """Minimal header seed for a daily partition (append-only file, no frontmatter)."""
    return f"# Log {day.isoformat()}\n\nLog entries for {day.isoformat()}.\n"


def _rel_to_root(profile: WikiProfile, path: Path) -> str:
    """Relative POSIX path with respect to the wiki root (stable, host-agnostic identity)."""
    try:
        return path.relative_to(profile.root_path).as_posix()
    except ValueError:
        return path.name


def _target_log(profile: WikiProfile, day: date) -> tuple[Path, bool]:
    """Target file for the given date + `created` flag.

    Rotation: the day's partition, created with the seed if absent (FR-002). Single-file
    (back-compat): the `log_path` log, which must already exist (Principio IV).
    """
    if profile.rotation_enabled:
        path = profile.partition_path(day)
        if path.is_file():
            return path, False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_partition_seed(day), encoding="utf-8")
        return path, True
    path = profile.log_path
    if not path.is_file():
        raise ConfigError("wiki log not found (initialize the structure first)",
                          key=str(path))
    return path, False


def _append_block(path: Path, block: str) -> None:
    """Appends `block` separated from the previous content by a blank line; ends with newline."""
    existing = path.read_text(encoding="utf-8")
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    path.write_text(prefix + block.rstrip() + "\n", encoding="utf-8")


def append_log(
    profile: WikiProfile,
    op: str,
    title: str,
    *,
    on_date: date | None = None,
    body: str | None = None,
) -> AppendLogResult:
    """Appends a log entry to the file for its date; returns the outcome (`wiki.append_log/1`).

    The heading is built from the profile's `log_format`; if `body` is given, the **curated body**
    is appended **without reformatting**. Idempotent: if an entry with the same heading already
    exists in the target file, nothing is written (SC-002, DA-5).
    """
    day = on_date or date.today()
    heading = profile.log_format.format(date=day.isoformat(), op=op, title=title)
    entry = heading if not body else f"{heading}\n\n{body.strip()}"

    target, created = _target_log(profile, day)
    rel = _rel_to_root(profile, target)
    existing_lines = {
        line.strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    if heading.strip() in existing_lines:
        log_event(logging.INFO, "registry", profile=profile.profile, target="log",
                  action="noop-duplicate")
        return AppendLogResult(written=False, partition=rel, created=False)

    _append_block(target, entry)
    if created and profile.rotation_enabled:
        update_log_index(profile)
    log_event(logging.INFO, "registry", profile=profile.profile, target="log",
              action="append", partition=rel)
    return AppendLogResult(written=True, partition=rel, created=created)


def update_log_index(profile: WikiProfile) -> bool:
    """Regenerates the partition index (`<log_dir>/<log_index_file>`); idempotent.

    No-op if rotation is not active or the directory does not exist. Uses relative Markdown links
    (not wikilinks) to avoid interfering with the taxonomy wikilink lint.
    """
    if not profile.rotation_enabled or not profile.log_dir_path.is_dir():
        return False
    days = sorted(p.stem for p in profile.log_dir_path.glob("*.md") if _PARTITION_RE.match(p.stem))
    lines = ["# Log Index", "", "Daily partitions (chronological):", ""]
    lines += [f"- [{d}]({d}.md)" for d in days]
    content = "\n".join(lines) + "\n"

    idx = profile.log_index_path
    if idx.is_file() and idx.read_text(encoding="utf-8") == content:
        return False
    idx.write_text(content, encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="log-index",
              action="update", days=len(days))
    return True


def migrate_log(profile: WikiProfile) -> MigrateResult:
    """Splits the monolithic log (`log_path`) into daily partitions (`wiki.migrate/1`).

    Segments by dated heading `## [YYYY-MM-DD] ...`, groups by date, writes one partition per
    distinct date (preserving order and content). **Idempotent** (date already present → skip) and
    **non-destructive** (does not delete the monolithic log). The preamble before the first entry
    is ignored. Requires rotation to be active.
    """
    if not profile.rotation_enabled:
        raise ConfigError("rotation not active: configure `log_dir` before migrating",
                          key="log_dir")
    src = profile.log_path
    if not src.is_file():
        return MigrateResult(migrated_entries=0)

    groups: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []

    def _flush() -> None:
        nonlocal buf, current
        if current is not None and buf:
            groups.setdefault(current, []).append("\n".join(buf).rstrip())
        buf = []

    for line in src.read_text(encoding="utf-8").splitlines():
        match = _ENTRY_HEADING.match(line)
        if match:
            _flush()
            current = match.group(1)
            buf = [line]
        elif current is not None:
            buf.append(line)
        # preamble (frontmatter/intro before the first entry): ignored
    _flush()

    created: list[str] = []
    skipped: list[str] = []
    migrated = 0
    for d_iso in sorted(groups):
        day = date.fromisoformat(d_iso)
        path = profile.partition_path(day)
        if path.is_file():
            skipped.append(path.name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_partition_seed(day) + "\n" + "\n\n".join(groups[d_iso]) + "\n",
                        encoding="utf-8")
        created.append(path.name)
        migrated += len(groups[d_iso])

    if created:
        update_log_index(profile)
    log_event(logging.INFO, "registry", profile=profile.profile, target="log", action="migrate",
              created=len(created), skipped=len(skipped), migrated=migrated)
    return MigrateResult(migrated_entries=migrated, created=created, skipped=skipped)


def upsert_index(profile: WikiProfile, page: str, summary: str) -> UpsertIndexResult:
    """Inserts/updates the index row for `page` (id = relative path); idempotent.

    The row has the form `- [[page]] — summary`. If a row for the same `page` with the same
    summary already exists, nothing is written (SC-002); if the summary changed, the row is
    updated. The summary is **externally authored** and written verbatim (trim only, FR-014):
    empty or multiline → explicit error, no write and no normalisation (FR-018).
    """
    summary = summary.strip()
    if not summary:
        raise ConfigError("empty summary: upsert-index requires a non-empty line of text",
                          key=page)
    if "\n" in summary or "\r" in summary:
        raise ConfigError(
            "multiline summary: the index row is a single line (provide the text on one line, "
            "no automatic normalisation)", key=page,
        )

    index_path = profile.index_path
    if not index_path.is_file():
        raise ConfigError("wiki index not found (initialize the structure first)",
                          key=str(index_path))

    line = f"- [[{page}]] — {summary}"
    existing = index_path.read_text(encoding="utf-8")
    lines = existing.splitlines()

    marker = f"[[{page}]]"
    out: list[str] = []
    replaced = False
    already = False
    for current in lines:
        if marker in current:
            if current.strip() == line.strip():
                already = True
                out.append(current)
            else:
                out.append(line)
                replaced = True
        else:
            out.append(current)

    if already:
        log_event(logging.INFO, "registry", profile=profile.profile,
                  target="index", action="noop-duplicate")
        return UpsertIndexResult(written=False, action="noop", page=page)

    if not replaced:
        out.append(line)

    action = "update" if replaced else "insert"
    index_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    log_event(logging.INFO, "registry", profile=profile.profile, target="index", action=action)
    return UpsertIndexResult(written=True, action=action, page=page)
