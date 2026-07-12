"""Test di `ritual-check` (E10-FEAT-026): scoperta deterministica di candidati distill/drift.

Il tool è **sola lettura, zero-LLM**: trova candidati strutturali, l'agente giudica (D↔N). I test
del drift esercitano le funzioni pure; distill/scope/fail-loud passano da `ritual_check`. In un tmp
NON-git, `git show`/`rev-parse` falliscono in modo grazioso → i link correnti contano come «nuovi».
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_core.wiki_tools.profile import load_profile
from sertor_core.wiki_tools.ritual_check import (
    _distill_candidates,
    _drift_candidates,
    ritual_check,
)
from sertor_core.wiki_tools.structure import init_structure

_CONFIG = """\
profile = "code+doc"
language = "it"
root = "wiki"
index_file = "index.md"
log_file = "log.md"
source_dirs = ["wiki"]

[[taxonomy]]
name = "concepts"
dir = "concepts"
type = "concept"

[[taxonomy]]
name = "experiments"
dir = "experiments"
type = "experiment"
"""

_CONFIG_RITUAL = _CONFIG + """
[ritual]
capability_globs = ["src/**", "specs/**"]
exec_page = "syntheses/roadmap.md"
hub_threshold = 8
"""


def _wiki(tmp_path: Path, config: str = _CONFIG):
    cfg = tmp_path / "wiki.config.toml"
    cfg.write_text(config, encoding="utf-8")
    p = load_profile(cfg)
    init_structure(p)
    return p


def _page(p, rel: str, body: str) -> None:
    f = p.root_path / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")


# ------------------------------------------------------------------ distill candidates (US1)

def test_distill_positive_two_pages_cross_linked(tmp_path):
    """≥2 changed pages con nuovi backlink incrociati e 0 nuove pagine concepts/tech → candidato."""
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "---\ntitle: A\ntype: experiment\n---\n[[experiments/b]]\n")
    _page(p, "experiments/b.md", "---\ntitle: B\ntype: experiment\n---\n[[experiments/a]]\n")
    res = ritual_check(p, pages=["experiments/a.md", "experiments/b.md"])
    assert len(res.distill_candidates) == 1
    cand = res.distill_candidates[0]
    assert set(cand["pages"]) == {"experiments/a.md", "experiments/b.md"}
    assert cand["shared_new_backlinks"] >= 2


def test_distill_negative_no_cross_links(tmp_path):
    """Pagine changed senza backlink incrociati → 0 candidati spuri."""
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "---\ntitle: A\ntype: experiment\n---\nNiente link.\n")
    _page(p, "experiments/b.md", "---\ntitle: B\ntype: experiment\n---\nNemmeno qui.\n")
    res = ritual_check(p, pages=["experiments/a.md", "experiments/b.md"])
    assert res.distill_candidates == []


def test_distill_suppressed_by_new_distill_page(tmp_path):
    """Se lo step ha creato una nuova pagina concepts/tech, nessun candidato (già distillato)."""
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "---\ntitle: A\ntype: experiment\n---\n[[experiments/b]]\n")
    _page(p, "experiments/b.md", "---\ntitle: B\ntype: experiment\n---\n[[experiments/a]]\n")
    _page(p, "concepts/x.md", "---\ntitle: X\ntype: concept\n---\nEntità.\n")
    idx = {a: rel for rel in ("experiments/a.md", "experiments/b.md", "concepts/x.md")
           for a in (rel, rel[:-3], rel.rsplit("/", 1)[-1][:-3])}
    changed = {r: (p.root_path / r).read_text(encoding="utf-8")
               for r in ("experiments/a.md", "experiments/b.md")}
    out = _distill_candidates(p, p.config_dir, "HEAD", "wiki", changed,
                              added_pages={"concepts/x.md"}, target_index=idx)
    assert out == []  # la nuova pagina concepts/ soddisfa già il distill


# ------------------------------------------------------------------ drift candidates (US3, pure)

def _idx(*rels: str) -> dict:
    out: dict = {}
    for rel in rels:
        for alias in (rel, rel[:-3] if rel.endswith(".md") else rel, rel.rsplit("/", 1)[-1][:-3]):
            out.setdefault(alias, rel)
    return out


def test_drift_stale_updated(tmp_path):
    p = _wiki(tmp_path)
    changed = {
        "tech/fresh.md": "---\ntitle: F\nupdated: 2026-07-12\n---\nx\n",
        "tech/stale.md": "---\ntitle: S\nupdated: 2026-06-01\n---\ny\n",
    }
    out = _drift_candidates(p, changed, changed, _idx(*changed), [])
    stale = [c for c in out if c["signal"] == "stale-updated"]
    assert [c["page"] for c in stale] == ["tech/stale.md"]


def test_drift_neighbor_of_change_and_hub_exclusion(tmp_path):
    p = _wiki(tmp_path)
    all_pages = {
        "tech/small.md": "---\ntitle: S\n---\nvedi [[tech/target]].\n",
        "tech/target.md": "---\ntitle: T\n---\nz\n",
        "syntheses/hub.md": "---\ntitle: H\n---\n" + " ".join(f"[[n{i}]]" for i in range(20)),
    }
    for i in range(20):
        all_pages[f"tech/n{i}.md"] = f"---\ntitle: N{i}\n---\nq\n"
    idx = _idx(*all_pages, *[f"n{i}" for i in range(20)])
    # small (non-hub) changed → target è neighbor; hub changed (>8 link) → i suoi n{i} esclusi
    changed = {"tech/small.md": all_pages["tech/small.md"],
               "syntheses/hub.md": all_pages["syntheses/hub.md"]}
    out = _drift_candidates(p, changed, all_pages, idx, [])
    neighbors = {c["page"] for c in out if c["signal"] == "neighbor-of-change"}
    assert "tech/target.md" in neighbors           # dal non-hub
    assert not any(pg.startswith("tech/n") for pg in neighbors)  # hub escluso


def test_drift_capability_exec_config_driven(tmp_path):
    p = _wiki(tmp_path, _CONFIG_RITUAL)
    changed = {"tech/x.md": "---\ntitle: X\n---\nx\n"}
    # capability file cambiato (src/**) ma exec_page NON toccata → candidato
    out = _drift_candidates(p, changed, changed, _idx("tech/x.md"), ["src/foo.py", "tech/x.md"])
    cap = [c for c in out if c["signal"] == "capability-exec"]
    assert [c["page"] for c in cap] == ["syntheses/roadmap.md"]


def test_drift_capability_exec_absent_without_config(tmp_path):
    p = _wiki(tmp_path)  # nessuna sezione [ritual] → segnale disattivato (host-agnostico)
    out = _drift_candidates(p, {"tech/x.md": "---\ntitle: X\n---\nx\n"},
                            {"tech/x.md": "x"}, _idx("tech/x.md"), ["src/foo.py"])
    assert not any(c["signal"] == "capability-exec" for c in out)


# -------------------------------------------------------------- fail-loud + read-only + scaffold

def test_fail_loud_when_scope_indeterminable(tmp_path):
    """Fuori da un repo git e senza --pages → ConfigError (mai liste vuote silenziose, REQ-006)."""
    p = _wiki(tmp_path)
    with pytest.raises(ConfigError):
        ritual_check(p)  # tmp non-git, nessun --pages, nessun --base risolvibile


def test_read_only_no_page_modified(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "---\ntitle: A\ntype: experiment\n---\n[[experiments/b]].\n")
    _page(p, "experiments/b.md", "---\ntitle: B\ntype: experiment\n---\n[[experiments/a]].\n")
    before = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    res = ritual_check(p, pages=["experiments/a.md", "experiments/b.md"])
    after = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    assert before == after                        # sola lettura (SC-003)
    assert res.schema == "wiki.ritual_check/1"
    assert "record" in res.declaration_scaffold and "distill" in res.declaration_scaffold
