"""Test US6 — distillazione (REQ-030..033)."""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import LLMNotConfiguredError
from sertor_core.wiki.conventions import Brief
from sertor_core.wiki.distill import distill

T = "2026-06-03"


def test_distill_produces_page_with_llm(wiki_sandbox, fake_llm):
    brief = Brief("Sessione design", "experiment", "brief condensato della sessione", tags=["x"])
    res = distill(wiki_sandbox, brief, llm=fake_llm, today=T)
    assert res.changed
    page = wiki_sandbox / "experiments" / "sessione-design.md"
    assert page.exists()
    assert "Sintesi distillata" in page.read_text(encoding="utf-8")    # corpo dall'LLM (REQ-030)
    assert fake_llm.calls == 1
    log = (wiki_sandbox / "log.md").read_text(encoding="utf-8")
    assert "] record | Sessione design" in log                        # come record (REQ-032)


def test_distill_without_llm_raises(wiki_sandbox):
    with pytest.raises(LLMNotConfiguredError):                         # REQ-031
        distill(wiki_sandbox, Brief("X", "experiment", "y"), llm=None, today=T)
