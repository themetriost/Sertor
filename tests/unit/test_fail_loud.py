"""Fail-loud tests for the local embedder (068, TASK-C01): no silent degradation."""
from __future__ import annotations

import logging
from pathlib import Path
from urllib.error import URLError

import pytest

from sertor_core.adapters.embeddings import glove_cache
from sertor_core.composition import build_embedder
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import ConfigError, GloveUnavailableError


def test_glove_unavailable_names_both_exits():
    err = GloveUnavailableError("missing", reason="cache_miss")
    msg = str(err)
    assert "SERTOR_GLOVE_PATH" in msg
    assert "SERTOR_EMBED_PROVIDER=hash" in msg


def test_no_silent_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "cache")

    def boom(url):
        raise URLError("offline")

    monkeypatch.setattr(glove_cache, "urlopen", boom)
    # build_embedder on the indexing path (allow_download=True) must propagate, not fall back.
    with pytest.raises(GloveUnavailableError):
        build_embedder(Settings(embed_provider="glove"), allow_download=True)


def test_config_error_on_invalid_value():
    with pytest.raises(ConfigError) as exc:
        build_embedder(Settings(embed_provider="typo"))
    assert exc.value.key == "SERTOR_EMBED_PROVIDER"
    for value in ("glove", "hash", "ollama", "azure"):
        assert value in str(exc.value)


def test_provider_selected_event_has_no_secrets(caplog):
    fixture = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        build_embedder(Settings(embed_provider="glove", glove_path=fixture))
    for record in caplog.records:
        msg = record.getMessage()
        if "embeddings_provider_selected" in msg:
            assert "provider=glove" in msg
            assert str(fixture) not in msg  # no local path leak
            assert "~" not in msg


def test_glove_download_event_fields_only(monkeypatch, tmp_path, caplog):
    import io
    import zipfile

    cache = tmp_path / "cache"
    fixture = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"

    def fake_zip():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("glove.6B.300d.txt", fixture.read_bytes())
        return buf.getvalue()

    class _Resp:
        def __init__(self, data):
            self._data = data
            self._pos = 0

        def read(self, n=-1):
            chunk = self._data[self._pos:] if n < 0 else self._data[self._pos:self._pos + n]
            self._pos += len(chunk)
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)
    monkeypatch.setattr(glove_cache, "urlopen", lambda url: _Resp(fake_zip()))
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        glove_cache.ensure_glove(Settings())
    dl = [r for r in caplog.records if "glove_download" in r.getMessage()]
    assert dl
    msg = dl[0].getMessage()
    assert "size_mb=822" in msg
    assert "source_host=nlp.stanford.edu" in msg
    assert "https://" not in msg  # full URL not leaked
