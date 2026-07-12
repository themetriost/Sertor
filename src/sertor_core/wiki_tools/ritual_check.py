"""`ritual-check`: deterministic discovery of ritual candidates (E10-FEAT-026).

Read-only, zero-LLM, offline. Given the pages of a step (git diff vs a base, or explicit `--pages`),
it FINDS structural candidates the agent then JUDGES (D↔N):

- distill candidates: groups of ≥2 changed pages sharing ≥2 **new** cross-backlinks with no **new**
  distill-home page (`concepts/`/`tech/`, from taxonomy) — a durable entity surfaced, not distilled;
- drift candidates: pages worth a semantic lint — `stale-updated` (changed but `updated:` lags the
  freshest changed page), `neighbor-of-change` (linked from a non-hub changed page but not itself
  changed), and the config-driven `capability-exec` (capability files changed, EXEC page untouched).

It also emits a declaration scaffold so a step closure has a concrete artefact to answer. The tool
never judges (create a page / fix drift) — that stays with the agent (Principio XI).
"""
from __future__ import annotations

import fnmatch
import logging
import subprocess
from pathlib import Path

from sertor_core.domain.errors import ConfigError
from sertor_core.observability.logging import log_event
from sertor_core.wiki_tools.collect import iter_pages
from sertor_core.wiki_tools.contracts import RitualCheckResult
from sertor_core.wiki_tools.frontmatter import extract_wikilinks, parse_frontmatter
from sertor_core.wiki_tools.profile import WikiProfile


def _git(args: list[str], cwd: Path) -> tuple[int, str]:
    """Run `git <args>` at `cwd`; return (returncode, stdout). Never raises (caller decides)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
        )
    except OSError:
        return 1, ""
    return proc.returncode, proc.stdout


def _link_aliases(rel_path: str) -> set[str]:
    """Forms by which a wikilink can refer to this page (mirror of `lint._link_targets`)."""
    no_ext = rel_path[:-3] if rel_path.endswith(".md") else rel_path
    stem = no_ext.rsplit("/", 1)[-1]
    return {rel_path, no_ext, stem}


def _resolve_base(config_dir: Path, base: str | None) -> str:
    """Resolve the diff base: explicit `base`, else merge-base with `master` (fail-loud if none)."""
    if base:
        return base
    rc, out = _git(["merge-base", "HEAD", "master"], config_dir)
    if rc == 0 and out.strip():
        return out.strip()
    raise ConfigError(
        "cannot determine a git diff base (no merge-base with 'master'); pass --base <ref> or "
        "--pages <a.md,...>",
        key="--base",
    )


def _wiki_prefix(config_dir: Path, profile: WikiProfile) -> str:
    """Repo-root-relative prefix of the wiki root (e.g. `wiki`), for mapping git paths to pages."""
    rc, out = _git(["rev-parse", "--show-prefix"], config_dir)
    show_prefix = out.strip() if rc == 0 else ""
    parts = [p for p in (show_prefix.rstrip("/"), profile.root.strip("/")) if p and p != "."]
    return "/".join(parts)


def _changed_repo_paths(config_dir: Path, base: str) -> list[str]:
    """Repo-root-relative paths changed in `base...HEAD` (fail-loud if git is unavailable)."""
    rc, out = _git(["diff", "--name-only", f"{base}...HEAD"], config_dir)
    if rc != 0:
        raise ConfigError(
            f"git diff failed for base '{base}' (not a git repo, or bad ref); pass --pages instead",
            key="--base",
        )
    return [line.strip() for line in out.splitlines() if line.strip()]


def _links_at(config_dir: Path, base: str, repo_path: str) -> set[str]:
    """Wikilink targets of a page at revision `base` (empty if absent — i.e. a newly added page)."""
    rc, out = _git(["show", f"{base}:{repo_path}"], config_dir)
    if rc != 0:
        return set()
    return extract_wikilinks(out)


def _distill_candidates(
    profile: WikiProfile,
    config_dir: Path,
    base: str,
    wiki_prefix: str,
    changed_pages: dict[str, str],          # rel_to_root -> current text
    added_pages: set[str],                   # rel_to_root of pages ADDED in this step
    target_index: dict[str, str],            # alias -> rel_to_root (existing pages)
) -> list[dict]:
    """Groups of changed pages linked by ≥2 NEW cross-backlinks, with no new distill-home page."""
    distill_dirs = _distill_dirs(profile)
    has_new_distill_page = any(
        rel.split("/", 1)[0] in distill_dirs for rel in added_pages
    )
    changed_set = set(changed_pages)

    new_cross: list[tuple[str, str]] = []
    for rel, text in changed_pages.items():
        repo_path = f"{wiki_prefix}/{rel}" if wiki_prefix else rel
        old_targets = _links_at(config_dir, base, repo_path)
        for target in extract_wikilinks(text):
            if target in old_targets:
                continue  # not new
            dst = target_index.get(target)
            if dst is not None and dst != rel and dst in changed_set:
                new_cross.append((rel, dst))

    involved = sorted({p for pair in new_cross for p in pair})
    if len(new_cross) >= 2 and len(involved) >= 2 and not has_new_distill_page:
        return [{
            "pages": involved,
            "shared_new_backlinks": len(new_cross),
            "reason": "≥2 changed pages linked by new cross-backlinks, 0 new concepts/tech page",
        }]
    return []


def _distill_dirs(profile: WikiProfile) -> set[str]:
    """Taxonomy dirs that are distill homes: config `[ritual].distill_dirs`, else concept/tech."""
    configured = profile.ritual.get("distill_dirs")
    if isinstance(configured, list) and all(isinstance(d, str) for d in configured):
        return {d.strip("/") for d in configured}
    return {
        entry.dir.strip("/")
        for entry in profile.taxonomy
        if entry.type.lower() in ("concept", "tech") or entry.dir.strip("/") in ("concepts", "tech")
    }


def _hub_threshold(profile: WikiProfile) -> int:
    """Max outgoing wikilinks for a changed page to still emit `neighbor-of-change` candidates.

    Config `[ritual].hub_threshold`; default 8. A page above it is a hub (roadmap/index) and its
    neighbors are skipped.
    """
    value = profile.ritual.get("hub_threshold")
    return value if isinstance(value, int) and value > 0 else 8


def _drift_candidates(
    profile: WikiProfile,
    changed_pages: dict[str, str],
    all_pages: dict[str, str],
    target_index: dict[str, str],
    changed_repo_paths: list[str],
) -> list[dict]:
    """Structural drift candidates: stale-updated, neighbor-of-change, capability-exec (config)."""
    out: list[dict] = []
    seen: set[str] = set()

    # (a) stale-updated: a changed page whose `updated:` lags the freshest changed page.
    updates = {
        rel: str(parse_frontmatter(text).get("updated", "")).strip()
        for rel, text in changed_pages.items()
    }
    freshest = max((u for u in updates.values() if u), default="")
    for rel, upd in sorted(updates.items()):
        if freshest and upd and upd < freshest and rel not in seen:
            out.append({"page": rel, "signal": "stale-updated",
                        "detail": f"updated {upd} < freshest changed page {freshest}"})
            seen.add(rel)

    # (b) neighbor-of-change: a page linked FROM a NON-HUB changed page but not itself changed.
    # Hub pages (roadmap/index) link to everything → their neighbors are not meaningfully made stale
    # by the change, so they are skipped (avoids drowning the signal — R-1).
    hub_threshold = _hub_threshold(profile)
    changed_set = set(changed_pages)
    for rel, text in sorted(changed_pages.items()):
        links = extract_wikilinks(text)
        if len(links) > hub_threshold:
            continue
        for target in links:
            dst = target_index.get(target)
            if dst is not None and dst not in changed_set and dst not in seen and dst in all_pages:
                out.append({"page": dst, "signal": "neighbor-of-change",
                            "detail": f"linked from changed page {rel}, not itself updated"})
                seen.add(dst)

    # (c) capability-exec (config-driven): capability files changed but the EXEC page untouched.
    globs = profile.ritual.get("capability_globs")
    exec_page = profile.ritual.get("exec_page")
    if isinstance(globs, list) and isinstance(exec_page, str) and exec_page.strip():
        exec_rel = exec_page.strip()
        touched_capability = any(
            any(fnmatch.fnmatch(p, str(g)) for g in globs) for p in changed_repo_paths
        )
        if touched_capability and exec_rel not in changed_set and exec_rel not in seen:
            out.append({"page": exec_rel, "signal": "capability-exec",
                        "detail": "capability files changed but the exec_page was not touched"})
    return out


def ritual_check(
    profile: WikiProfile,
    *,
    base: str | None = None,
    pages: list[str] | None = None,
) -> RitualCheckResult:
    """Deterministic ritual candidates for the current step (read-only; the agent judges).

    Scope: explicit `pages` (rel to the wiki root) or the git diff `base...HEAD`. Indeterminable
    scope (no git, no `pages`) → `ConfigError` (Principio XII, no silent-empty).
    """
    config_dir = profile.config_dir
    all_pages: dict[str, str] = {}
    for rel_path, full_path in iter_pages(profile):
        try:
            all_pages[rel_path] = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    target_index: dict[str, str] = {}
    for rel in all_pages:
        for alias in _link_aliases(rel):
            target_index.setdefault(alias, rel)

    added_pages: set[str] = set()
    changed_repo_paths: list[str] = []
    if pages:
        changed_pages = {p: all_pages[p] for p in pages if p in all_pages}
        scope = f"explicit:{len(changed_pages)}"
        wiki_prefix = _wiki_prefix(config_dir, profile)
        base_ref = base or ""
    else:
        base_ref = _resolve_base(config_dir, base)
        changed_repo_paths = _changed_repo_paths(config_dir, base_ref)
        wiki_prefix = _wiki_prefix(config_dir, profile)
        prefix = f"{wiki_prefix}/" if wiki_prefix else ""
        changed_pages = {}
        for repo_path in changed_repo_paths:
            if prefix and not repo_path.startswith(prefix):
                continue
            rel = repo_path[len(prefix):] if prefix else repo_path
            if rel.endswith(".md") and rel in all_pages:
                changed_pages[rel] = all_pages[rel]
        # ADDED (new) pages in this diff, for the "0 new distill page" check.
        rc, out = _git(["diff", "--name-only", "--diff-filter=A", f"{base_ref}...HEAD"], config_dir)
        if rc == 0:
            for repo_path in (line.strip() for line in out.splitlines() if line.strip()):
                if prefix and repo_path.startswith(prefix):
                    added_pages.add(repo_path[len(prefix):])
        scope = f"git:{base_ref}...HEAD"

    distill = (
        _distill_candidates(profile, config_dir, base_ref, wiki_prefix,
                            changed_pages, added_pages, target_index)
        if not pages else
        _distill_candidates(profile, config_dir, base or "HEAD", wiki_prefix,
                            changed_pages, added_pages, target_index)
    )
    drift = _drift_candidates(profile, changed_pages, all_pages, target_index, changed_repo_paths)

    d_word = "candidato" if len(distill) == 1 else "candidati"
    l_word = "pagina" if len(drift) == 1 else "pagine"
    scaffold = (
        f"Rituale: record: <?> · distill: <{len(distill)} {d_word} → verdetto?> "
        f"· lint: <{len(drift)} {l_word} drift → verdetto?>"
    )

    result = RitualCheckResult(
        scope=scope,
        pages_in_scope=sorted(changed_pages),
        distill_candidates=distill,
        drift_candidates=drift,
        declaration_scaffold=scaffold,
    )
    log_event(logging.INFO, "ritual_check", profile=profile.profile, scope=scope,
              pages=len(changed_pages), distill=len(distill), drift=len(drift))
    return result
