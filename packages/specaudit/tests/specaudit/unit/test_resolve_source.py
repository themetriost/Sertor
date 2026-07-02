"""T015 — risoluzione della fonte originale: estrazione EARS, cascata, assente vs vuota."""

from __future__ import annotations

from specaudit.adapters.requirements_fs import RequirementsFsResolver, extract_ears_bullets
from specaudit.stages.resolve_source import resolve_original
from tests.specaudit.helpers import requirements_md


def test_extract_ears_bullets():
    bullets = extract_ears_bullets(requirements_md(), "x.md", ("REQ-", "FR-"))
    ids = [b[0] for b in bullets]
    assert ids == ["FR-001", "FR-002", "FR-003"]
    assert "Esc" in bullets[0][1]


def test_extract_ears_bullets_req_prefix():
    """Regressione (trovato in validazione T048): il suffisso deve valere anche per REQ-, non solo FR-."""
    text = (
        "- **REQ-001** *(Event-driven)* — **When** X, **the** system **shall** Y.\n"
        "- **REQ-A02** *(Ubiquitous)* — **The** system **shall** Z.\n"
        "- **FR-010** — the system shall W.\n"
    )
    bullets = extract_ears_bullets(text, "x.md", ("REQ-", "FR-"))
    assert [b[0] for b in bullets] == ["REQ-001", "REQ-A02", "FR-010"]


def test_resolve_from_dir(tmp_path):
    (tmp_path / "requirements.md").write_text(requirements_md(), encoding="utf-8")
    reqs, provenance, gaps = resolve_original(RequirementsFsResolver(tmp_path), "ref")
    assert len(reqs) == 3
    assert reqs[0].id == "FR-001"
    assert gaps == []
    assert provenance == str(tmp_path)


def test_absent_source_declares_gap(tmp_path):
    missing = tmp_path / "does-not-exist"
    reqs, provenance, gaps = resolve_original(RequirementsFsResolver(missing), "ref")
    assert reqs == []
    assert provenance == "absent"
    assert gaps == ["original_source: absent"]


def test_present_but_empty_distinguished(tmp_path):
    (tmp_path / "empty.md").write_text("# Titolo\n\nNessun bullet EARS qui.\n", encoding="utf-8")
    reqs, provenance, gaps = resolve_original(RequirementsFsResolver(tmp_path), "ref")
    assert reqs == []
    assert provenance.startswith("present-but-empty")
    assert gaps == ["original_source: present-but-empty"]
