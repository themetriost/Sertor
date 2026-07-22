"""Test di `distill-audit` (E10-FEAT-039): scoperta cross-sessione del debito di distillazione.

Il tool è **sola lettura, zero-LLM, deterministico**: trova entità referenziate da ≥k punti senza
pagina (wikilink penzolanti + identificatori in backtick), l'agente giudica la durevolezza (D↔N).
"""
from __future__ import annotations

from pathlib import Path

from sertor_core.wiki_tools.distill_audit import distill_audit
from sertor_core.wiki_tools.profile import load_profile
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

_CONFIG_STOPWORDS = _CONFIG + """
[ritual]
audit_stopwords = ["subscribe"]
"""

_CONFIG_THRESHOLD = _CONFIG + """
[ritual]
audit_threshold = 3
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


def _names(result) -> list[str]:
    return [c["name"] for c in result.candidates]


def _by_name(result, name: str) -> dict | None:
    for c in result.candidates:
        if c["name"] == name:
            return c
    return None


def test_dangling_wikilink_from_two_points_is_a_candidate(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "See [[subscribe]] for details.\n")
    _page(p, "experiments/b.md", "Also relies on [[subscribe]].\n")
    result = distill_audit(p)
    cand = _by_name(result, "subscribe")
    assert cand is not None
    assert cand["points"] == 2
    assert cand["signal"] == "wikilink"
    assert result.debt == 1


def test_reference_from_a_single_point_is_below_threshold(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "Only here: [[subscribe]].\n")
    result = distill_audit(p)
    assert _by_name(result, "subscribe") is None
    assert result.debt == 0


def test_prose_backtick_identifier_is_a_candidate(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "The `search_combined` tool returns two flows.\n")
    _page(p, "experiments/b.md", "We call `search_combined` in the facade.\n")
    result = distill_audit(p)
    cand = _by_name(result, "search_combined")
    assert cand is not None
    assert cand["points"] == 2
    assert cand["signal"] == "prose"


def test_candidate_with_existing_page_is_excluded(tmp_path):
    p = _wiki(tmp_path)
    # subscribe HAS a home page → not a candidate even if referenced widely.
    _page(p, "concepts/subscribe.md", "---\ntitle: Subscribe\ntype: concept\n---\nThe entity.\n")
    _page(p, "experiments/a.md", "See [[subscribe]].\n")
    _page(p, "experiments/b.md", "Also [[subscribe]] and `subscribe`.\n")
    result = distill_audit(p)
    assert _by_name(result, "subscribe") is None


def test_wikilink_path_form_matches_existing_page(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "concepts/subscribe.md", "---\ntitle: Subscribe\ntype: concept\n---\nx.\n")
    _page(p, "experiments/a.md", "See [[concepts/subscribe]].\n")
    _page(p, "experiments/b.md", "See [[concepts/subscribe]].\n")
    result = distill_audit(p)
    # stem 'subscribe' resolves to the existing page → not dangling.
    assert _by_name(result, "concepts/subscribe") is None
    assert result.debt == 0


def test_both_signals_merge_into_one_candidate(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "[[auto-heal]] matters.\n")
    _page(p, "experiments/b.md", "The `auto-heal` mechanism.\n")
    result = distill_audit(p)
    cand = _by_name(result, "auto-heal")
    assert cand is not None
    assert cand["points"] == 2
    assert cand["signal"] == "both"


def test_stopword_backtick_is_excluded(tmp_path):
    p = _wiki(tmp_path, _CONFIG_STOPWORDS)
    _page(p, "experiments/a.md", "`subscribe` here.\n")
    _page(p, "experiments/b.md", "`subscribe` there.\n")
    result = distill_audit(p)
    assert _by_name(result, "subscribe") is None


def test_default_stopword_literals_excluded(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "returns `true` and `None`.\n")
    _page(p, "experiments/b.md", "also `true`, `None`.\n")
    result = distill_audit(p)
    assert result.debt == 0


def test_fenced_code_block_is_ignored(tmp_path):
    p = _wiki(tmp_path)
    # a compound identifier that would match the prose rule if not stripped with the fence.
    body = "```\n`inside-thing` in a fence\n```\ntext\n"
    _page(p, "experiments/a.md", body)
    _page(p, "experiments/b.md", body)
    result = distill_audit(p)
    assert _by_name(result, "inside-thing") is None


def test_threshold_override_and_config(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "[[widget]]\n")
    _page(p, "experiments/b.md", "[[widget]]\n")
    # default k=2 → candidate; override k=3 → not.
    assert _by_name(distill_audit(p), "widget") is not None
    assert _by_name(distill_audit(p, threshold=3), "widget") is None
    # config [ritual].audit_threshold = 3
    sub = tmp_path / "sub"
    sub.mkdir()
    p3 = _wiki(sub, _CONFIG_THRESHOLD)
    _page(p3, "experiments/a.md", "[[widget]]\n")
    _page(p3, "experiments/b.md", "[[widget]]\n")
    assert _by_name(distill_audit(p3), "widget") is None


def test_log_partition_reference_counts_as_a_point(tmp_path):
    p = _wiki(tmp_path)
    # A single content page + a mention in the (single-file) log = 2 distinct points.
    _page(p, "experiments/a.md", "[[floortest]]\n")
    (p.root_path / "log.md").write_text(
        "# log.md\n\nAppend-only.\n\n## entry\n[[floortest]] again.\n", encoding="utf-8"
    )
    result = distill_audit(p)
    cand = _by_name(result, "floortest")
    assert cand is not None and cand["points"] == 2


def test_deterministic_and_read_only(tmp_path):
    p = _wiki(tmp_path)
    _page(p, "experiments/a.md", "[[alpha]] [[beta]]\n")
    _page(p, "experiments/b.md", "[[alpha]] [[beta]]\n")
    before = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    r1 = distill_audit(p)
    r2 = distill_audit(p)
    after = {f: f.read_bytes() for f in p.root_path.rglob("*.md")}
    assert r1.to_dict() == r2.to_dict()  # determinism (SC-002)
    assert before == after  # no file written (read-only, SC-002)
    # sorted by points desc then name asc; both have points 2 → alphabetical.
    assert _names(r1) == ["alpha", "beta"]


def test_empty_corpus_zero_debt(tmp_path):
    p = _wiki(tmp_path)
    result = distill_audit(p)
    assert result.debt == 0
    assert result.candidates == []
    assert result.schema == "wiki.distill_audit/1"
