"""T027 — CLI: exit code (args invalidi→2; output SpecLift malformato/versione/changeset→3)."""

from __future__ import annotations

import json

from specaudit.cli import main
from tests.specaudit.helpers import requirements_md, speclift_output


def _speclift(tmp_path, data=None):
    p = tmp_path / "report.speclift.json"
    p.write_text(json.dumps(data or speclift_output("abc123")), encoding="utf-8")
    return str(p)


def _requirements(tmp_path):
    d = tmp_path / "requirements"
    d.mkdir()
    (d / "req.md").write_text(requirements_md(), encoding="utf-8")
    return str(d)


def test_audit_ok(tmp_path, capsys):
    sp, req = _speclift(tmp_path), _requirements(tmp_path)
    code = main(["audit", "--speclift", sp, "--requirements", req, "--format", "json"])
    assert code == 0
    assert '"version": "1"' in capsys.readouterr().out


def test_audit_md_renders_unicode(tmp_path, capsys):
    sp, req = _speclift(tmp_path), _requirements(tmp_path)
    code = main(["audit", "--speclift", sp, "--requirements", req, "--format", "md"])
    assert code == 0
    out = capsys.readouterr().out
    assert "# SpecAudit" in out
    assert "Àncora" in out  # carattere non-ASCII reso senza crash


def test_bad_version_exit_3(tmp_path):
    sp = _speclift(tmp_path, speclift_output("abc123", version="9"))
    req = _requirements(tmp_path)
    code = main(["audit", "--speclift", sp, "--requirements", req])
    assert code == 3


def test_changeset_mismatch_exit_3(tmp_path):
    sp, req = _speclift(tmp_path), _requirements(tmp_path)
    code = main(["audit", "--speclift", sp, "--requirements", req, "--changeset-ref", "other"])
    assert code == 3


def test_provided_deferred_exit_2(tmp_path):
    sp = _speclift(tmp_path)
    code = main(["audit", "--speclift", sp, "--provided", "x.json"])
    assert code == 2


def test_mutually_exclusive_original_requirements_exit_2(tmp_path):
    sp, req = _speclift(tmp_path), _requirements(tmp_path)
    code = main(["audit", "--speclift", sp, "--original", "a.md", "--requirements", req])
    assert code == 2


def test_prepare_then_report_roundtrip(tmp_path):
    sp, req = _speclift(tmp_path), _requirements(tmp_path)
    base = tmp_path / "audit"
    code = main(["prepare", "--speclift", sp, "--requirements", req, "--out", str(base)])
    assert code == 0
    assert (tmp_path / "audit.audit-bundle.json").is_file()
