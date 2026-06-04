"""Test US5 — comando `sertor wiki semantic-gate`: mapping status → exit code (REQ-094/095)."""
from __future__ import annotations

import sertor_cli.commands.semantic_gate_cmd as gate_cmd
from sertor_cli.cli import main
from sertor_core.services.semantic_gate import GateOutcome, GateStatus
from sertor_core.wiki.semantic import SemanticReport


def _stub_builders(monkeypatch):
    """Evita LLM/facade/git reali: il comando non deve toccare config/rete nei test."""
    monkeypatch.setattr(gate_cmd, "build_llm", lambda: None)
    monkeypatch.setattr(gate_cmd, "build_facade", lambda: None)
    monkeypatch.setattr(gate_cmd, "SubprocessGitAdapter", lambda **kw: None)


def _patch_gate(monkeypatch, outcome):
    _stub_builders(monkeypatch)
    monkeypatch.setattr(gate_cmd, "run_semantic_gate", lambda *a, **k: outcome)


def test_blocked_exits_nonzero(monkeypatch, tmp_path):
    outcome = GateOutcome(status=GateStatus.BLOCKED, report=SemanticReport())
    _patch_gate(monkeypatch, outcome)
    assert main(["wiki", "semantic-gate", str(tmp_path)]) == 1     # blocked → exit ≠ 0


def test_pass_exits_zero(monkeypatch, tmp_path):
    outcome = GateOutcome(status=GateStatus.PASS, report=SemanticReport())
    _patch_gate(monkeypatch, outcome)
    assert main(["wiki", "semantic-gate", str(tmp_path)]) == 0


def test_warning_exits_zero(monkeypatch, tmp_path):
    outcome = GateOutcome(status=GateStatus.WARNING, report=SemanticReport())
    _patch_gate(monkeypatch, outcome)
    assert main(["wiki", "semantic-gate", str(tmp_path)]) == 0     # warning non blocca


def test_override_passes_and_reports(monkeypatch, tmp_path, capsys):
    outcome = GateOutcome(status=GateStatus.PASS, report=SemanticReport(),
                          override=True, override_record="override: hotfix (1 issue bloccanti)")
    _patch_gate(monkeypatch, outcome)
    code = main(["wiki", "semantic-gate", str(tmp_path), "--override", "--reason", "hotfix"])
    assert code == 0
    err = capsys.readouterr().err
    assert "OVERRIDE" in err and "hotfix" in err                   # override tracciato a video
