"""Tests for the write/scaffold/resolve logic of `sertor configure` (feature 051, Fase 2).

All offline, no network, no cloud. The idempotency (T-220-IDEM) and no-partial-write (T-220) tests
are the structural guarantees of non-destructiveness (FR-014/SC-005, FR-005).
"""
from __future__ import annotations

from pathlib import Path

from sertor_installer.configure import (
    resolve_field,
    scaffold_env_if_absent,
    write_resolved_fields,
)
from sertor_installer.configure_fields import FIELD_CATALOG, FieldStatus

_ENDPOINT = FIELD_CATALOG["AZURE_OPENAI_ENDPOINT"]
_APIKEY = FIELD_CATALOG["AZURE_OPENAI_API_KEY"]
_DEPLOY = FIELD_CATALOG["AZURE_OPENAI_EMBED_DEPLOYMENT"]


def _env(tmp_path: Path) -> Path:
    return tmp_path / ".sertor" / ".env"


# --- T-200: scaffold ----------------------------------------------------------------------------


def test_scaffold_creates_env_from_template_azure(tmp_path: Path):
    created = scaffold_env_if_absent(tmp_path, "azure")
    assert created is True
    content = _env(tmp_path).read_text(encoding="utf-8")
    assert "RAG_BACKEND=azure" in content


def test_scaffold_creates_env_from_template_local(tmp_path: Path):
    created = scaffold_env_if_absent(tmp_path, "local")
    assert created is True
    content = _env(tmp_path).read_text(encoding="utf-8")
    assert "RAG_BACKEND=local" in content


def test_scaffold_skips_if_existing(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=local\nMY=1\n", encoding="utf-8")
    created = scaffold_env_if_absent(tmp_path, "azure")
    assert created is False
    assert env.read_text(encoding="utf-8") == "RAG_BACKEND=local\nMY=1\n"  # untouched


def test_scaffold_no_uv_no_index(tmp_path: Path, monkeypatch):
    # No subprocess of any kind: scaffold must never reach a CommandRunner.
    import sertor_installer.command_runner as cr

    def _boom(*a, **k):  # pragma: no cover - must not be called
        raise AssertionError("scaffold must not invoke any subprocess (install != run)")

    monkeypatch.setattr(cr.SubprocessRunner, "run", _boom)
    monkeypatch.setattr(cr.SubprocessRunner, "is_available", _boom)
    scaffold_env_if_absent(tmp_path, "azure")


# --- T-210: resolve_field -----------------------------------------------------------------------


def test_resolve_from_flag(tmp_path: Path):
    env = _env(tmp_path)
    res = resolve_field(_ENDPOINT, {"AZURE_OPENAI_ENDPOINT": "https://x/"}, env, interactive=False)
    assert res.status is FieldStatus.SET
    assert res.source == "flag"
    assert res.value == "https://x/"


def test_resolve_from_existing_env(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("AZURE_OPENAI_ENDPOINT=https://existing/\n", encoding="utf-8")
    res = resolve_field(_ENDPOINT, {}, env, interactive=False)
    assert res.status is FieldStatus.KEPT
    assert res.source == "existing"
    assert res.value == "https://existing/"


def test_resolve_from_template_default(tmp_path: Path):
    env = _env(tmp_path)
    res = resolve_field(_DEPLOY, {}, env, interactive=False)
    assert res.status is FieldStatus.SET
    assert res.source == "template-default"
    assert res.value == "text-embedding-3-large"


def test_resolve_missing_non_interactive(tmp_path: Path):
    # T-210-CI: no source, interactive=False → MISSING, never a prompt (CI-safe, FR-005).
    env = _env(tmp_path)
    res = resolve_field(_APIKEY, {}, env, interactive=False)
    assert res.status is FieldStatus.MISSING
    assert res.value is None


def test_resolve_secret_not_echoed(tmp_path: Path):
    env = _env(tmp_path)
    res = resolve_field(
        _APIKEY, {"AZURE_OPENAI_API_KEY": "sk-supersecret-xyz"}, env, interactive=False
    )
    assert res.field.secret is True
    assert res.display_value == "****-xyz"
    assert "sk-supersecret-xyz" != res.display_value


def test_resolve_from_process_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://from-env/")
    res = resolve_field(_ENDPOINT, {}, _env(tmp_path), interactive=False)
    assert res.status is FieldStatus.SET
    assert res.source == "env"
    assert res.value == "https://from-env/"


# --- T-220: write_resolved_fields ---------------------------------------------------------------


def _set(field, value, status=FieldStatus.SET, source="flag"):
    from sertor_installer.configure_report import FieldResolution

    return FieldResolution(field, value, status, source)


def test_write_adds_missing_key(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=azure\n", encoding="utf-8")
    write_resolved_fields(env, [_set(_ENDPOINT, "https://x/")], overwrite=False)
    assert "AZURE_OPENAI_ENDPOINT=https://x/" in env.read_text(encoding="utf-8")


def test_write_keeps_existing_without_overwrite(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("AZURE_OPENAI_ENDPOINT=https://old/\n", encoding="utf-8")
    final = write_resolved_fields(env, [_set(_ENDPOINT, "https://new/")], overwrite=False)
    assert "https://old/" in env.read_text(encoding="utf-8")
    assert "https://new/" not in env.read_text(encoding="utf-8")
    assert final[0].status is FieldStatus.KEPT


def test_write_overwrites_with_flag(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("AZURE_OPENAI_ENDPOINT=https://old/\n", encoding="utf-8")
    final = write_resolved_fields(env, [_set(_ENDPOINT, "https://new/")], overwrite=True)
    assert "https://new/" in env.read_text(encoding="utf-8")
    assert "https://old/" not in env.read_text(encoding="utf-8")
    assert final[0].status is FieldStatus.OVERWRITTEN


def test_write_preserves_unmanaged_lines(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("# my comment\nMY_CUSTOM=hello\nRAG_BACKEND=azure\n", encoding="utf-8")
    write_resolved_fields(env, [_set(_ENDPOINT, "https://x/")], overwrite=False)
    content = env.read_text(encoding="utf-8")
    assert "# my comment" in content
    assert "MY_CUSTOM=hello" in content


def test_write_no_partial_on_missing(tmp_path: Path):
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=azure\n", encoding="utf-8")
    write_resolved_fields(
        env, [_set(_APIKEY, None, status=FieldStatus.MISSING, source="none")], overwrite=False
    )
    assert "AZURE_OPENAI_API_KEY" not in env.read_text(encoding="utf-8")


def test_write_idempotent(tmp_path: Path):
    # T-220-IDEM: two identical runs → byte-identical .env (FR-014/SC-005).
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=azure\n", encoding="utf-8")
    res = [_set(_ENDPOINT, "https://x/"), _set(_DEPLOY, "text-embedding-3-large")]
    write_resolved_fields(env, list(res), overwrite=False)
    first = env.read_bytes()
    write_resolved_fields(env, list(res), overwrite=False)
    assert env.read_bytes() == first


def test_secret_not_in_versioned_file(tmp_path: Path):
    # T-220-NOVCS: only .sertor/.env is touched; nothing else under target (SC-003/FR-012).
    env = _env(tmp_path)
    env.parent.mkdir(parents=True)
    env.write_text("RAG_BACKEND=azure\n", encoding="utf-8")
    write_resolved_fields(env, [_set(_APIKEY, "sk-secret-1234")], overwrite=False)
    others = [
        p for p in tmp_path.rglob("*")
        if p.is_file() and p != env
    ]
    assert others == [], f"unexpected files written: {others}"
