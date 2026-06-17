"""End-to-end CLI tests for `sertor configure` (feature 051, Fasi 3-8).

All F.I.R.S.T.: no network, no cloud, no TTY (so the flow is flag-driven). The anti-leak and
install≠run tests are the structural guarantees (SC-008/SC-009). The `runner` is a real
SubprocessRunner only when `--check` is passed; these tests never pass `--check` (except the probe
file), so no subprocess is ever spawned.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from sertor_installer.__main__ import main

_AZURE_FLAGS = [
    "--set", "AZURE_OPENAI_ENDPOINT=https://x.openai.azure.com/",
    "--set", "AZURE_OPENAI_API_KEY=sk-mysecret-1234",
]


def _env(tmp_path: Path) -> Path:
    return tmp_path / ".sertor" / ".env"


# --- Fase 3: US1 wizard guidato -----------------------------------------------------------------


def test_configure_help_exit_0(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["configure", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "backend" in out
    assert "check" in out


def test_configure_local_exit_0(tmp_path: Path):
    rc = main(["configure", "--backend", "local", "--target", str(tmp_path), "--non-interactive"])
    assert rc == 0
    content = _env(tmp_path).read_text(encoding="utf-8")
    assert "RAG_BACKEND=local" in content


def test_configure_azure_flag_driven_exit_0(tmp_path: Path):
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", *_AZURE_FLAGS,
    ])
    assert rc == 0
    content = _env(tmp_path).read_text(encoding="utf-8")
    assert "AZURE_OPENAI_ENDPOINT=https://x.openai.azure.com/" in content
    assert "AZURE_OPENAI_API_KEY=sk-mysecret-1234" in content


def test_configure_missing_field_non_interactive_exit_1(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path), "--non-interactive",
        "--set", "AZURE_OPENAI_ENDPOINT=https://x/",
    ])
    assert rc == 1
    err = capsys.readouterr().err
    assert "AZURE_OPENAI_API_KEY" in err
    # No partial write: the api-key line, if present from the scaffold, stays EMPTY (no value).
    for line in _env(tmp_path).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("AZURE_OPENAI_API_KEY="):
            assert line.strip() == "AZURE_OPENAI_API_KEY="


def test_configure_set_without_equals_exit_2(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "local", "--target", str(tmp_path),
        "--non-interactive", "--set", "BADKEY",
    ])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_configure_bad_backend_exit_2():
    with pytest.raises(SystemExit) as exc:
        main(["configure", "--backend", "foo"])
    assert exc.value.code == 2


def test_configure_json_output(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", "--json", *_AZURE_FLAGS,
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert "exit_code" in payload
    assert payload["profile"]["backend"] == "azure"


def test_configure_does_not_index(tmp_path: Path, monkeypatch):
    # T-320-NORUN: no subprocess spawned (install != run). --check NOT passed.
    import sertor_installer.command_runner as cr

    def _boom(self, *a, **k):  # pragma: no cover - must not be called
        raise AssertionError("configure must not spawn a subprocess without --check")

    monkeypatch.setattr(cr.SubprocessRunner, "run", _boom)
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", *_AZURE_FLAGS,
    ])
    assert rc == 0


def test_configure_no_secret_in_stdout(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", "--set", "AZURE_OPENAI_API_KEY=mysecretvalue",
        "--set", "AZURE_OPENAI_ENDPOINT=https://x/",
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "mysecretvalue" not in captured.out
    assert "mysecretvalue" not in captured.err


# --- Fase 4: US2 CI-safe & idempotency ----------------------------------------------------------


def test_ci_complete_no_prompt(tmp_path: Path, monkeypatch):
    # T-400-CI-COMPLETE: no TTY + all fields via environment → exit 0, no prompt.
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://env/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "sk-env-1234")

    def _no_prompt(*a, **k):  # pragma: no cover
        raise AssertionError("must not prompt in CI")

    monkeypatch.setattr("builtins.input", _no_prompt)
    monkeypatch.setattr("getpass.getpass", _no_prompt)
    rc = main(["configure", "--backend", "azure", "--target", str(tmp_path)])
    assert rc == 0


def test_ci_missing_field_explicit_error(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--set", "AZURE_OPENAI_ENDPOINT=https://x/",
    ])
    assert rc == 1
    assert "AZURE_OPENAI_API_KEY" in capsys.readouterr().err


def test_configure_idempotent_double_run(tmp_path: Path):
    args = [
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", *_AZURE_FLAGS,
    ]
    assert main(args) == 0
    first = _env(tmp_path).read_bytes()
    assert main(args) == 0
    assert _env(tmp_path).read_bytes() == first


def test_configure_keeps_extra_env_vars(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=azure\nMY_CUSTOM_VAR=hello\n", encoding="utf-8")
    main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--non-interactive", *_AZURE_FLAGS,
    ])
    assert "MY_CUSTOM_VAR=hello" in env.read_text(encoding="utf-8")


# --- Fase 5: US3 local profile ------------------------------------------------------------------

_CLOUD_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_API_KEY",
)


def test_local_profile_no_cloud_fields(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "local", "--target", str(tmp_path),
        "--non-interactive", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    field_names = {f["name"] for f in payload["fields"]}
    for var in _CLOUD_VARS:
        assert var not in field_names


def test_local_profile_validation_complete(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "local", "--target", str(tmp_path),
        "--non-interactive", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["validation"]["complete"] is True
    assert payload["validation"]["missing"] == []


def test_local_profile_env_has_backend_local(tmp_path: Path):
    main(["configure", "--backend", "local", "--target", str(tmp_path), "--non-interactive"])
    assert "RAG_BACKEND=local" in _env(tmp_path).read_text(encoding="utf-8")


# --- Fase 6: US4 reconfiguration ----------------------------------------------------------------


def test_reconfigure_keeps_existing_without_overwrite(tmp_path: Path, capsys):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text(
        "RAG_BACKEND=azure\nSERTOR_STORE_BACKEND=local\n"
        "AZURE_OPENAI_ENDPOINT=https://vecchio.endpoint/\n"
        "AZURE_OPENAI_API_KEY=sk-old-1234\n"
        "AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large\n",
        encoding="utf-8",
    )
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path), "--non-interactive",
        "--set", "AZURE_OPENAI_ENDPOINT=https://nuovo.endpoint/",
    ])
    assert rc == 0
    content = env.read_text(encoding="utf-8")
    assert "https://vecchio.endpoint/" in content
    assert "https://nuovo.endpoint/" not in content
    out = json.loads(
        main_json(tmp_path, "azure", ["--set", "AZURE_OPENAI_ENDPOINT=https://nuovo.endpoint/"])
    )
    endpoint = next(f for f in out["fields"] if f["name"] == "AZURE_OPENAI_ENDPOINT")
    assert endpoint["status"] == "kept"


def test_reconfigure_overwrites_with_flag(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text(
        "RAG_BACKEND=azure\nSERTOR_STORE_BACKEND=local\n"
        "AZURE_OPENAI_ENDPOINT=https://vecchio.endpoint/\n"
        "AZURE_OPENAI_API_KEY=sk-old-1234\n"
        "AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large\n",
        encoding="utf-8",
    )
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path), "--non-interactive",
        "--overwrite", "--set", "AZURE_OPENAI_ENDPOINT=https://nuovo.endpoint/",
    ])
    assert rc == 0
    content = env.read_text(encoding="utf-8")
    assert "https://nuovo.endpoint/" in content
    assert "https://vecchio.endpoint/" not in content


def test_reconfigure_preserves_comments_and_unmanaged(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text(
        "# mio commento\nRAG_BACKEND=azure\nMY_CUSTOM=hello\n", encoding="utf-8"
    )
    main([
        "configure", "--backend", "azure", "--target", str(tmp_path), "--non-interactive",
        *_AZURE_FLAGS,
    ])
    content = env.read_text(encoding="utf-8")
    assert "# mio commento" in content
    assert "MY_CUSTOM=hello" in content


def main_json(tmp_path: Path, backend: str, extra: list[str]) -> str:
    """Helper: run configure with --json and capture the stdout via a fresh subprocess-free call."""
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main([
            "configure", "--backend", backend, "--target", str(tmp_path),
            "--non-interactive", "--json", *extra,
        ])
    return buf.getvalue().strip()


# --- Fase 7: US5 static validation --------------------------------------------------------------


def test_static_validation_complete_exit_0(tmp_path: Path, capsys):
    rc = main([
        "configure", "--backend", "local", "--target", str(tmp_path),
        "--non-interactive", "--json",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["validation"]["complete"] is True


def test_static_validation_missing_exit_1(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    # No --non-interactive but no TTY → flag-driven; missing api key → exit 1, names it.
    rc = main([
        "configure", "--backend", "azure", "--target", str(tmp_path),
        "--set", "AZURE_OPENAI_ENDPOINT=https://x/",
    ])
    assert rc == 1
    assert "AZURE_OPENAI_API_KEY" in capsys.readouterr().err


# --- Fase 8: host-agnostic + observability ------------------------------------------------------


def test_configure_host_agnostic(tmp_path: Path):
    # T-810: two distinct target dirs → each gets a valid .env with corpus from the dir name.
    a = tmp_path / "ProjAlpha"
    b = tmp_path / "proj_beta"
    a.mkdir()
    b.mkdir()
    main(["configure", "--backend", "local", "--target", str(a), "--non-interactive"])
    main(["configure", "--backend", "local", "--target", str(b), "--non-interactive"])
    ca = (a / ".sertor" / ".env").read_text(encoding="utf-8")
    cb = (b / ".sertor" / ".env").read_text(encoding="utf-8")
    assert "SERTOR_CORPUS=projalpha" in ca
    assert "SERTOR_CORPUS=proj_beta" in cb


def test_observability_event_no_secrets(tmp_path: Path, caplog):
    # T-830: the `configure` event carries counts only, never the secret value.
    with caplog.at_level(logging.INFO, logger="sertor_install_kit"):
        main([
            "configure", "--backend", "azure", "--target", str(tmp_path),
            "--non-interactive", "--set", "AZURE_OPENAI_API_KEY=sk-topsecret-9999",
            "--set", "AZURE_OPENAI_ENDPOINT=https://x/",
        ])
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "sk-topsecret-9999" not in text
    assert "op=configure" in text
