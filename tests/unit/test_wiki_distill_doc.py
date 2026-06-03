"""Test FEAT-007 — distillazione di un artifact in documentazione ufficiale (US4)."""
from __future__ import annotations

import pytest

from sertor_core.domain.errors import LLMNotConfiguredError
from sertor_core.wiki.distill import distill_artifact

T = "2026-06-03"


def test_distill_artifact_creates_page_with_backlink(wiki_sandbox, fake_llm, tmp_path):
    artifact = tmp_path / "spec.md"
    artifact.write_text("# Spec del nucleo\n\nDettagli del requisito.\n", encoding="utf-8")
    src = str(artifact)

    res = distill_artifact(wiki_sandbox, source=src, kind="synthesis",
                           title="Architettura del nucleo", llm=fake_llm, today=T)
    assert res.changed and fake_llm.calls == 1
    page = wiki_sandbox / "syntheses" / "architettura-del-nucleo.md"
    text = page.read_text(encoding="utf-8")
    assert f"sources: [{src}]" in text          # backlink in frontmatter (REQ-062)
    assert f"]({src})" in text                   # riga di rimando alla fonte (REQ-061)


def test_distill_artifact_does_not_overwrite_curated_page(wiki_sandbox, fake_llm):
    page = wiki_sandbox / "syntheses" / "architettura-del-nucleo.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("CURATO A MANO\n", encoding="utf-8")

    res = distill_artifact(wiki_sandbox, source="specs/x/spec.md", kind="synthesis",
                           title="Architettura del nucleo", llm=fake_llm, today=T)
    assert res.changed is False                                             # non distruttivo (DA-3)
    assert page.read_text(encoding="utf-8") == "CURATO A MANO\n"


def test_distill_artifact_without_llm_raises(wiki_sandbox):
    with pytest.raises(LLMNotConfiguredError):                              # REQ-065
        distill_artifact(wiki_sandbox, source="specs/x/spec.md", kind="synthesis",
                         title="X", llm=None, today=T)
