"""Tests for `rag_profile`: compose_extras (DA-3), default corpus, validations (T009)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.domain.errors import ConfigError
from sertor_installer.rag_profile import (
    RagHostProfile,
    RagInstallOptions,
    compose_extras,
    sanitize_corpus,
)


def test_compose_extras_azure_all():
    assert compose_extras("azure", True, True) == ["azure", "mcp", "graph", "rerank"]


def test_compose_extras_local_no_azure():
    assert compose_extras("local", True, True) == ["mcp", "graph", "rerank"]


def test_compose_extras_optout():
    assert compose_extras("azure", False, False) == ["azure", "mcp"]


def test_mcp_always_present():
    assert "mcp" in compose_extras("local", False, False)


def test_sanitize_corpus():
    assert sanitize_corpus("My App 2!") == "my-app-2"
    assert sanitize_corpus("") == "corpus"


def test_default_corpus_from_dir(tmp_path: Path):
    opts = RagInstallOptions(target_root=tmp_path / "MyApp")
    assert opts.resolved_corpus() == "myapp"


def test_explicit_corpus_wins(tmp_path: Path):
    opts = RagInstallOptions(target_root=tmp_path / "MyApp", corpus="custom")
    assert opts.resolved_corpus() == "custom"


def test_invalid_backend_raises():
    with pytest.raises(ConfigError):
        RagInstallOptions(target_root=Path("."), backend="foo")


def test_dep_spec_azure(tmp_path: Path):
    profile = RagHostProfile.from_options(
        RagInstallOptions(target_root=tmp_path / "X", backend="azure")
    )
    assert profile.dep_spec().startswith("sertor-core[azure,mcp,graph,rerank] @ git+")
    assert profile.sertor_dir == (tmp_path / "X" / ".sertor")
