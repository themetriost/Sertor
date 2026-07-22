"""`distill-audit`: cross-session distill-debt discovery (E10-FEAT-039).

Read-only, zero-LLM, offline. Where `ritual-check` (FEAT-026) looks at the git-diff of ONE step,
this audits the WHOLE corpus so entities made durable **by accumulation** surface regardless of when
they were introduced — the blind spot Acta and our own 5-week distill debt both hit.

It FINDS structural candidates the agent then JUDGES (D↔N). A candidate is an entity referenced from
≥k distinct points with **no dedicated page**, by two deterministic signals:

- **dangling wikilinks** — `[[x]]` whose target has no page (high precision);
- **prose backtick identifiers** — `` `x` `` identifier-like tokens with no page (a durable term
  mentioned in prose but never given a home), a FIXED rule (stop-words + identifier shape), NOT NLP.

The tool never judges durability nor creates a page — that stays with the agent (Principio XI).
"""
from __future__ import annotations

import logging
import re

from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import DistillAuditResult
from sertor_core.wiki_tools.frontmatter import body_after_frontmatter, extract_wikilinks
from sertor_core.wiki_tools.profile import WikiProfile

_DEFAULT_THRESHOLD = 2

# Prose signal: an inline `token` is a candidate only when it is a **compound domain identifier** —
# starts with a letter, contains a `_` or `-` (a multi-segment name like `search_combined` /
# `distill-audit`), and NO `.` or `/` (which would make it a filename/path: `wiki.config.toml`,
# `src/foo`). This precision rule is what keeps the audit signal meaningful on a real corpus: bare
# single words (`sertor`, `master`, `index`) and file/path tokens are pervasive backtick NOISE, not
# durable entities (R-1). Free-text capitalisation is likewise excluded (noisy, erodes D↔N —
# research DA-1). Bare-word prose entities are caught only via the wikilink signal (a future lever).
_COMPOUND_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9]*[_-][A-Za-z0-9_-]*[A-Za-z0-9]$")
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)

# Field-level default (a generic noise list, not a host specific): language keywords / literals /
# extensions that are backticked constantly but are not durable entities. Host-overridable via
# `[ritual].audit_stopwords` (Principio VIII).
_DEFAULT_STOPWORDS = frozenset({
    "true", "false", "none", "null", "nil", "self", "cls", "todo", "fixme", "nan",
    "int", "str", "bool", "list", "dict", "set", "float", "bytes", "none.",
    "yaml", "json", "toml", "md", "txt", "py", "ps1", "sh", "env",
    "http", "https", "url", "uri", "id", "ok", "n/a",
})


def _norm(name: str) -> str:
    """Normalised identity of a candidate/page: last path segment, no `.md`, lowercased."""
    stem = name.strip().rsplit("/", 1)[-1]
    if stem.endswith(".md"):
        stem = stem[:-3]
    return stem.lower()


def _page_alias_set(profile: WikiProfile) -> set[str]:
    """Normalised identities of every CONTENT page (a candidate matching one already HAS a home).

    Content pages only (`iter_pages` excludes index + log): the log is where undistilled entities
    accumulate, not where they get a home.
    """
    aliases: set[str] = set()
    for rel_path, _ in iter_pages(profile):
        aliases.add(_norm(rel_path))
    return aliases


def _iter_corpus(profile: WikiProfile) -> list[tuple[str, str]]:
    """`(rel_path_posix, text)` for every `.md` under the wiki root EXCEPT the index file.

    Unlike `iter_pages`, this KEEPS the log partitions: a reference from a dated record is a real
    point of accumulation (research DA-1). Deterministic order (sorted) for repeatable output.
    """
    root = profile.root_path
    if not root.is_dir():
        return []
    index_name = profile.index_file
    files: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.md"), key=lambda p: p.as_posix()):
        rel = path.relative_to(root)
        if len(rel.parts) == 1 and rel.name == index_name:
            continue
        try:
            files.append((rel.as_posix(), path.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue
    return files


def _stopwords(profile: WikiProfile) -> frozenset[str]:
    configured = profile.ritual.get("audit_stopwords")
    if isinstance(configured, list) and all(isinstance(s, str) for s in configured):
        return frozenset(s.strip().lower() for s in configured if s.strip())
    return _DEFAULT_STOPWORDS


def _threshold(profile: WikiProfile, override: int | None) -> int:
    if override is not None and override > 0:
        return override
    configured = profile.ritual.get("audit_threshold")
    if isinstance(configured, int) and configured > 0:
        return configured
    return _DEFAULT_THRESHOLD


def _prose_identifiers(text: str, stopwords: frozenset[str]) -> set[str]:
    """Distinct backtick identifiers in `text`'s body (fenced code stripped), minus stop-words."""
    body = _FENCED_CODE.sub(" ", body_after_frontmatter(text))
    found: set[str] = set()
    for raw in _INLINE_CODE.findall(body):
        token = raw.strip()
        if _COMPOUND_IDENTIFIER.match(token) and _norm(token) not in stopwords:
            found.add(token)
    return found


def distill_audit(profile: WikiProfile, *, threshold: int | None = None) -> DistillAuditResult:
    """Deterministic cross-session distill-debt (read-only; the agent judges durability).

    A candidate is an entity referenced from ≥`threshold` distinct points (pages/log entries) with
    no content page, by dangling-wikilink or prose-backtick signal. Returns debt N + candidate list.
    """
    k = _threshold(profile, threshold)
    stopwords = _stopwords(profile)
    page_aliases = _page_alias_set(profile)
    corpus = _iter_corpus(profile)

    # norm_name -> {points: set[rel], signals: set[str], display: str}
    acc: dict[str, dict] = {}

    def _record(name: str, rel: str, signal: str) -> None:
        norm = _norm(name)
        if not norm or norm in page_aliases or norm in stopwords:
            return
        entry = acc.setdefault(norm, {"points": set(), "signals": set(), "display": name.strip()})
        entry["points"].add(rel)
        entry["signals"].add(signal)

    for rel, text in corpus:
        for target in extract_wikilinks(text):
            if _norm(target) not in page_aliases:
                _record(target, rel, "wikilink")
        for token in _prose_identifiers(text, stopwords):
            _record(token, rel, "prose")

    candidates: list[dict] = []
    for entry in acc.values():
        points = len(entry["points"])
        if points < k:
            continue
        signals = entry["signals"]
        signal = "both" if len(signals) > 1 else next(iter(signals))
        candidates.append({
            "name": entry["display"],
            "points": points,
            "signal": signal,
            "sample_refs": sorted(entry["points"])[:3],
        })
    candidates.sort(key=lambda c: (-c["points"], _norm(c["name"])))

    result = DistillAuditResult(
        debt=len(candidates),
        threshold=k,
        corpus_files=len(corpus),
        candidates=candidates,
    )
    log_event(logging.INFO, "distill_audit", profile=profile.profile,
              corpus_files=len(corpus), threshold=k, debt=len(candidates))
    return result
