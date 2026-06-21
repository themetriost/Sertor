"""GloVe on-demand acquisition tests (068, TASK-B01): cache hit, override, fail-loud."""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.error import URLError

import pytest

from sertor_core.adapters.embeddings import glove_cache
from sertor_core.adapters.embeddings.glove import GloveEmbedder
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import GloveUnavailableError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def test_first_index_calls_ensure(monkeypatch, tmp_path):
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "cache")
    calls = {"n": 0}

    def fake_ensure(_s):
        calls["n"] += 1
        return tmp_path / "downloaded.txt"

    monkeypatch.setattr(glove_cache, "ensure_glove", fake_ensure)
    glove_cache.resolve_glove_file(Settings(), allow_download=True)
    assert calls["n"] == 1


def test_second_index_uses_cache(monkeypatch, tmp_path, caplog):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "glove.6B.300d.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)
    calls = {"n": 0}
    monkeypatch.setattr(glove_cache, "ensure_glove", lambda s: calls.__setitem__("n", 1))
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        glove_cache.resolve_glove_file(Settings(), allow_download=True)
    assert calls["n"] == 0
    assert any("glove_cache_hit" in r.getMessage() and "hit=True" in r.getMessage()
               for r in caplog.records)


def test_override_airgapped_no_download(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(glove_cache, "ensure_glove", lambda s: calls.__setitem__("n", 1))
    result = glove_cache.resolve_glove_file(Settings(glove_path=FIXTURE), allow_download=True)
    assert result == FIXTURE
    assert calls["n"] == 0


def test_no_download_on_query_path(monkeypatch, tmp_path):
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "empty")
    with pytest.raises(GloveUnavailableError):
        glove_cache.resolve_glove_file(Settings(), allow_download=False)


def test_network_error_actionable(monkeypatch, tmp_path):
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "cache")

    def boom(url):
        raise URLError("offline")

    monkeypatch.setattr(glove_cache, "urlopen", boom)
    with pytest.raises(GloveUnavailableError) as exc:
        glove_cache.resolve_glove_file(Settings(), allow_download=True)
    msg = str(exc.value)
    assert "SERTOR_GLOVE_PATH" in msg
    assert "SERTOR_EMBED_PROVIDER=hash" in msg


def test_corrupt_file_raises(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("hello 0.1 0.2 0.3\n", encoding="utf-8")  # wrong dim
    with pytest.raises(GloveUnavailableError):
        GloveEmbedder(bad).embed(["hello"])
