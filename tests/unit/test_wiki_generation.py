"""Test della generazione del wiki (FEAT-010, US2): baseline/incrementale/no-op + invarianti.

Solo ScriptedLLM + FakeGit + wiki sandbox: nessuna rete (Principio V). Verifica idempotenza
(corpo invariato → 0 scritture), incrementalità via `sources:`, no-op su changeset irrilevante,
fallback `stale-index` e non-distruttività di `manual_edited/` (Principio VI).
"""
from __future__ import annotations

from pathlib import Path

from sertor_core.wiki.conventions import MANUAL_EDITED_DIR, write_watermark
from sertor_core.wiki.generation import generate
from tests.fixtures.mocks import FakeGit, ScriptedLLM

_BODY_A = "Corpo originale A."
_BODY_B = "Corpo originale B."


def _page(root: Path, relpath: str, *, body: str, sources: list[str]) -> Path:
    """Scrive una pagina wiki con frontmatter `sources:` e corpo dato."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    title = Path(relpath).stem
    fm = (
        "---\n"
        f"title: {title}\n"
        "type: concept\n"
        "tags: []\n"
        "created: 2026-06-03\n"
        "updated: 2026-06-03\n"
        f"sources: [{', '.join(sources)}]\n"
        "---\n"
    )
    path.write_text(f"{fm}\n# {title}\n\n{body}\n", encoding="utf-8")
    return path


def test_baseline_targets_all_generated_pages(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    _page(wiki_sandbox, "concepts/b.md", body=_BODY_B, sources=["src/b.py"])

    llm = ScriptedLLM(["Nuovo corpo A.", "Nuovo corpo B."])
    report = generate(wiki_sandbox, llm)  # no git → baseline

    assert report.mode == "baseline"
    assert report.pages_total == 2
    assert report.pages_written == 2
    assert report.llm_calls == 2


def test_incremental_only_linked_pages(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    _page(wiki_sandbox, "concepts/b.md", body=_BODY_B, sources=["src/b.py"])
    write_watermark(wiki_sandbox, "base000")

    # Solo src/a.py cambia → solo la pagina a.
    git = FakeGit(changed=["src/a.py"], head="head111")
    llm = ScriptedLLM(["Corpo A aggiornato."])
    report = generate(wiki_sandbox, llm, git=git, scope="since_watermark")

    assert report.mode == "incremental"
    assert report.pages_total == 1
    assert report.pages_written == 1
    assert "Corpo A aggiornato." in (wiki_sandbox / "concepts/a.md").read_text(encoding="utf-8")
    assert _BODY_B in (wiki_sandbox / "concepts/b.md").read_text(encoding="utf-8")


def test_incremental_noop_on_irrelevant_changeset(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    write_watermark(wiki_sandbox, "base000")

    git = FakeGit(changed=["docs/unrelated.txt"], head="head111")
    llm = ScriptedLLM(["non dovrebbe essere chiamato"])
    report = generate(wiki_sandbox, llm, git=git)

    assert report.mode == "incremental"
    assert report.pages_total == 0
    assert report.pages_written == 0
    assert report.llm_calls == 0
    assert llm.calls == 0


def test_fallbacks_contains_stale_index(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    report = generate(wiki_sandbox, ScriptedLLM(["x"]))
    assert "stale-index" in report.fallbacks


def test_manual_edited_never_modified(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    manual = wiki_sandbox / MANUAL_EDITED_DIR / "note.md"
    manual.parent.mkdir(parents=True, exist_ok=True)
    manual.write_text("# Nota umana\n\nContenuto curato a mano.\n", encoding="utf-8")
    before = manual.read_text(encoding="utf-8")

    generate(wiki_sandbox, ScriptedLLM(["qualsiasi cosa"]))

    assert manual.read_text(encoding="utf-8") == before  # invariato (Principio VI)


def test_idempotent_when_llm_returns_same_body(wiki_sandbox: Path):
    _page(wiki_sandbox, "concepts/a.md", body=_BODY_A, sources=["src/a.py"])
    # L'LLM restituisce esattamente il corpo esistente → nessuna scrittura.
    llm = ScriptedLLM([_BODY_A])
    report = generate(wiki_sandbox, llm)

    assert report.pages_total == 1
    assert report.llm_calls == 1
    assert report.pages_written == 0
