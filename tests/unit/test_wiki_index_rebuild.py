"""Test FEAT-007 — rigenerazione idempotente dell'indice + fix sicuro (US3)."""
from __future__ import annotations

from sertor_core.wiki.conventions import CATALOG_BEGIN, CATALOG_END
from sertor_core.wiki.maintenance import IssueKind, lint, regenerate_index

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\nCorpo.\n")


def _add(root, slug, title):
    (root / "concepts" / f"{slug}.md").write_text(_FM.format(t=title), encoding="utf-8")


def test_regenerate_updates_only_managed_block(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha")
    index = wiki_sandbox / "index.md"
    before = index.read_text(encoding="utf-8")
    assert regenerate_index(wiki_sandbox) is True                       # REQ-010
    after = index.read_text(encoding="utf-8")
    assert "## Pagine" in after                                         # resto preservato (REQ-011)
    assert CATALOG_BEGIN in after and CATALOG_END in after
    assert "[[alpha]]" in after.split(CATALOG_BEGIN)[1]                 # pagina nel catalogo
    assert before.split("## Pagine")[0] == after.split("## Pagine")[0]  # header intatto


def test_regenerate_is_idempotent(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha")
    assert regenerate_index(wiki_sandbox) is True
    snapshot = (wiki_sandbox / "index.md").read_text(encoding="utf-8")
    assert regenerate_index(wiki_sandbox) is False         # nessun cambiamento (REQ-012)
    assert (wiki_sandbox / "index.md").read_text(encoding="utf-8") == snapshot


def test_lint_fix_reindexes_but_never_touches_links(wiki_with_issues):
    fixed = lint(wiki_with_issues, fix=True)
    # la rigenerazione indice risolve orfani/fuori-indice...
    assert IssueKind.INDEX_MISSING not in {i.kind for i in fixed.issues}     # REQ-006
    # ...ma il link rotto resta (mai auto-fix dei link, DA-4)
    assert any(i.kind == IssueKind.BROKEN_LINK for i in fixed.issues)
