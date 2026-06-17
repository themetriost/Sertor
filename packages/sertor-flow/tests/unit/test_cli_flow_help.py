"""Help/naming tests for `sertor-flow` (FEAT-012, FR-006, SC-002).

Every subcommand that takes `--assistant` must offer exactly `{claude, copilot-cli}` and reject the
legacy VS Code value `copilot` (argparse `choices`, exit 2). Offline, no host side effects.
"""
from __future__ import annotations

import pytest

from sertor_flow.__main__ import main


@pytest.mark.parametrize("command", ["install", "upgrade", "uninstall"])
def test_sertor_flow_help_assistant_choices(command, capsys):
    """`<command> --help` lists `copilot-cli` and `claude`, never a bare `copilot` choice."""
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "copilot-cli" in out, f"{command}: missing copilot-cli"
    assert "claude" in out, f"{command}: missing claude"


@pytest.mark.parametrize("command", ["install", "upgrade", "uninstall"])
def test_sertor_flow_rejects_legacy_copilot(command, capsys, tmp_path):
    """The legacy `copilot` value is rejected by argparse `choices` (exit 2), naming copilot-cli."""
    with pytest.raises(SystemExit) as exc:
        main([command, "--assistant", "copilot", "--target", str(tmp_path)])
    assert exc.value.code == 2
    assert "copilot-cli" in capsys.readouterr().err
