"""Test FEAT-007 (Gruppo H) — lint semantico: rilevazione, gate, degrado, parsing (US1)."""
from __future__ import annotations

import json

from sertor_core.wiki.semantic import (
    SemanticIssueKind,
    Severity,
    semantic_lint,
)
from tests.fixtures.mocks import ScriptedLLM

_FM = ("---\ntitle: {t}\ntype: concept\ntags: []\ncreated: 2026-06-03\n"
       "updated: 2026-06-03\nsources: []\n---\n\n# {t}\n\n{b}\n")


def _add(root, slug, title, body="Corpo."):
    (root / "concepts" / f"{slug}.md").write_text(_FM.format(t=title, b=body), encoding="utf-8")
    return f"concepts/{slug}.md"


def _mtimes(root):
    return {p: p.stat().st_mtime_ns for p in root.rglob("*.md")}


_ALL_KINDS = json.dumps([
    {"kind": "obsolete", "claim": "Usa Ollama come default", "severity": "high",
     "detail": "il codice usa Azure", "evidence": "src/x.py#1"},
    {"kind": "coverage_gap", "claim": "", "severity": "medium",
     "detail": "manca doc di Y", "evidence": "src/y.py#2"},
    {"kind": "semantic_contradiction", "claim": "A", "severity": "low",
     "detail": "contraddice beta", "evidence": "concepts/beta.md"},
    {"kind": "stale_summary", "claim": "sommario X", "severity": "medium",
     "detail": "sommario vecchio", "evidence": "index.md"},
])


def test_detects_all_four_kinds_per_claim(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    llm = ScriptedLLM([_ALL_KINDS])
    report = semantic_lint(wiki_sandbox, llm, facade=None, pages=[rel])

    kinds = {i.kind for i in report.issues}
    assert kinds == set(SemanticIssueKind)                      # REQ-071..074
    obsolete = next(i for i in report.issues if i.kind == SemanticIssueKind.OBSOLETE)
    assert obsolete.claim == "Usa Ollama come default"          # granularità per claim (REQ-098)
    assert obsolete.severity == Severity.HIGH
    assert report.pages_checked == 1 and report.pages_total == 1 and report.llm_calls == 1


def test_semantic_lint_is_read_only(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    before = _mtimes(wiki_sandbox)
    semantic_lint(wiki_sandbox, ScriptedLLM([_ALL_KINDS]), pages=[rel])
    assert _mtimes(wiki_sandbox) == before                      # Principio VI (sola lettura)


def test_gate_threshold(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    low = json.dumps([{"kind": "stale_summary", "claim": "x", "severity": "low", "detail": "d"}])
    assert semantic_lint(wiki_sandbox, ScriptedLLM([low]), pages=[rel]).ok is True   # low < HIGH
    assert semantic_lint(wiki_sandbox, ScriptedLLM([_ALL_KINDS]), pages=[rel]).ok is False  # HIGH


def test_degrade_without_llm(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha")
    report = semantic_lint(wiki_sandbox, llm=None)              # REQ-081
    assert report.skipped is True and report.issues == [] and report.ok is True


def test_max_pages_bounds_cost_and_reports_coverage(wiki_sandbox):
    _add(wiki_sandbox, "alpha", "Alpha")
    _add(wiki_sandbox, "beta", "Beta")
    llm = ScriptedLLM([json.dumps([])])
    report = semantic_lint(wiki_sandbox, llm, max_pages=1)      # REQ-083
    assert report.pages_checked == 1
    assert report.pages_total >= 3                              # index.md + log.md + 2 pagine
    assert report.llm_calls == 1


def test_defensive_parsing(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    # Niente JSON → nessuna issue, nessun crash
    assert semantic_lint(wiki_sandbox, ScriptedLLM(["non e' json"]), pages=[rel]).issues == []
    # Array con una voce valida + una malformata (kind mancante) → solo la valida
    valid = {"kind": "obsolete", "claim": "c", "severity": "high", "evidence": "x.py#1"}
    mixed = json.dumps([{"severity": "high"}, valid])
    issues = semantic_lint(wiki_sandbox, ScriptedLLM([mixed]), pages=[rel]).issues
    assert len(issues) == 1 and issues[0].claim == "c"


def test_drops_ungrounded_issues(wiki_sandbox):
    """Filtro anti-rumore: scarta obsolete senza evidenza e contraddizioni che non citano pagine."""
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    noisy = json.dumps([
        # obsolete senza evidence → drop
        {"kind": "obsolete", "claim": "a", "severity": "high", "evidence": ""},
        # contraddizione che cita CODICE → drop
        {"kind": "semantic_contradiction", "claim": "b", "severity": "high",
         "evidence": "src/x.py#1"},
        # contraddizione che cita un'altra PAGINA → keep
        {"kind": "semantic_contradiction", "claim": "c", "severity": "high",
         "evidence": "concepts/beta.md"},
        # obsolete ancorata al codice → keep
        {"kind": "obsolete", "claim": "d", "severity": "high", "evidence": "src/y.py#2"},
    ])
    issues = semantic_lint(wiki_sandbox, ScriptedLLM([noisy]), pages=[rel]).issues
    assert {i.claim for i in issues} == {"c", "d"}             # solo le due ancorate


def test_reports_missing_code_context(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    # facade=None → nessun contesto codice: va dichiarato, non taciuto (REQ-083/097)
    report = semantic_lint(wiki_sandbox, ScriptedLLM([json.dumps([])]), facade=None, pages=[rel])
    assert report.pages_without_code_context == report.pages_checked == 1
    assert "obsolescenza vs codice è PARZIALE" in report.render()


def test_detection_is_idempotent(wiki_sandbox):
    rel = _add(wiki_sandbox, "alpha", "Alpha")
    a = semantic_lint(wiki_sandbox, ScriptedLLM([_ALL_KINDS]), pages=[rel]).issues
    b = semantic_lint(wiki_sandbox, ScriptedLLM([_ALL_KINDS]), pages=[rel]).issues
    assert [(i.kind, i.claim, i.severity) for i in a] == [(i.kind, i.claim, i.severity) for i in b]
