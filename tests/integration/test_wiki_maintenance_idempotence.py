"""Integration FEAT-007 — idempotenza e non-distruttività di lint + regenerate_index (SC-002)."""
from __future__ import annotations

import hashlib

from sertor_core.wiki.maintenance import lint, regenerate_index

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\nCorpo.\n")


def _digests(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*.md"))}


def test_lint_then_reindex_converges_and_is_stable(wiki_sandbox):
    (wiki_sandbox / "concepts" / "alpha.md").write_text(_FM.format(t="Alpha"), encoding="utf-8")
    (wiki_sandbox / "tech" / "beta.md").write_text(_FM.format(t="Beta"), encoding="utf-8")

    # prima rigenerazione: cambia; lint dopo il fix deve essere pulito
    assert regenerate_index(wiki_sandbox) is True
    report1 = lint(wiki_sandbox)
    after_first = _digests(wiki_sandbox)

    # ri-eseguire su wiki invariato: nessun cambiamento, esito identico (idempotenza)
    assert regenerate_index(wiki_sandbox) is False
    report2 = lint(wiki_sandbox)
    assert _digests(wiki_sandbox) == after_first            # nessun file toccato
    assert len(report1.issues) == len(report2.issues)
    assert report1.ok == report2.ok
