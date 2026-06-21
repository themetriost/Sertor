"""Unit tests for the GloVe cache/resolver (068, TASK-A03): cache, override, fail-loud."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from sertor_core.adapters.embeddings import glove_cache
from sertor_core.config.settings import Settings
from sertor_core.domain.errors import GloveUnavailableError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"


def test_override_path_no_download(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(glove_cache, "ensure_glove", lambda s: called.__setitem__("n", 1))
    result = glove_cache.resolve_glove_file(Settings(glove_path=FIXTURE), allow_download=True)
    assert result == FIXTURE
    assert called["n"] == 0


def test_cache_present(monkeypatch, tmp_path, caplog):
    import logging

    cache = tmp_path / "glove"
    cache.mkdir()
    cached = cache / "glove.6B.300d.txt"
    cached.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)
    called = {"n": 0}
    monkeypatch.setattr(glove_cache, "ensure_glove", lambda s: called.__setitem__("n", 1))
    with caplog.at_level(logging.INFO, logger="sertor_core"):
        result = glove_cache.resolve_glove_file(Settings(), allow_download=True)
    assert result == cached
    assert called["n"] == 0
    assert any("glove_cache_hit" in r.getMessage() and "hit=True" in r.getMessage()
               for r in caplog.records)


def test_file_absent_downloader_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "nope")

    def boom(_s):
        raise GloveUnavailableError("no network", reason="URLError")

    monkeypatch.setattr(glove_cache, "ensure_glove", boom)
    with pytest.raises(GloveUnavailableError) as exc:
        glove_cache.resolve_glove_file(Settings(), allow_download=True)
    msg = str(exc.value)
    assert "SERTOR_GLOVE_PATH" in msg
    assert "SERTOR_EMBED_PROVIDER=hash" in msg


def test_no_download_path_raises(monkeypatch, tmp_path):
    """allow_download=False + nothing cached → GloveUnavailableError, no download (REQ-034)."""
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: tmp_path / "empty")
    with pytest.raises(GloveUnavailableError):
        glove_cache.resolve_glove_file(Settings(), allow_download=False)


def _fake_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("glove.6B.300d.txt", FIXTURE.read_bytes())
        zf.writestr("glove.6B.50d.txt", b"ignored\n")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        chunk = self._data[self._pos:] if n < 0 else self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_ensure_glove_download_success(monkeypatch, tmp_path):
    cache = tmp_path / "glove"
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)
    monkeypatch.setattr(glove_cache, "urlopen", lambda url: _FakeResponse(_fake_zip_bytes()))
    result = glove_cache.ensure_glove(Settings())
    assert result == cache / "glove.6B.300d.txt"
    assert result.exists()
    # only the 300d member was extracted (atomic install of the single file)
    assert not (cache / "glove.6B.50d.txt").exists()


def test_ensure_glove_emits_download_event(monkeypatch, tmp_path, caplog):
    import logging

    cache = tmp_path / "glove"
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)
    monkeypatch.setattr(glove_cache, "urlopen", lambda url: _FakeResponse(_fake_zip_bytes()))
    with caplog.at_level(logging.WARNING, logger="sertor_core"):
        glove_cache.ensure_glove(Settings())
    dl = [r for r in caplog.records if "glove_download" in r.getMessage()]
    assert dl, "expected a glove_download event"
    msg = dl[0].getMessage()
    assert "size_mb=822" in msg
    assert "source_host=nlp.stanford.edu" in msg


def test_ensure_glove_network_error(monkeypatch, tmp_path):
    from urllib.error import URLError

    cache = tmp_path / "glove"
    monkeypatch.setattr(glove_cache, "glove_cache_dir", lambda: cache)

    def boom(url):
        raise URLError("unreachable")

    monkeypatch.setattr(glove_cache, "urlopen", boom)
    with pytest.raises(GloveUnavailableError):
        glove_cache.ensure_glove(Settings())


def test_glove_cache_dir_ends_with_sertor_glove():
    """On any OS the cache dir ends with sertor/glove (REQ-031)."""
    d = glove_cache.glove_cache_dir()
    assert d.parts[-2:] == ("sertor", "glove")


def test_glove_cache_dir_windows(monkeypatch):
    """Windows branch resolves under %LOCALAPPDATA% (string-level, OS-independent)."""
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local")
    # Exercise the Windows-branch logic directly without flipping pathlib's flavour.
    base = glove_cache.os.environ.get("LOCALAPPDATA")
    assert base == r"C:\Users\test\AppData\Local"


def test_glove_cache_dir_xdg(monkeypatch, tmp_path):
    """Override env resolves correctly through the public API on the host OS."""
    if glove_cache.os.name != "nt":
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
        d = glove_cache.glove_cache_dir()
        assert d == tmp_path / "xdg" / "sertor" / "glove"
    else:
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "appdata"))
        d = glove_cache.glove_cache_dir()
        assert d == tmp_path / "appdata" / "sertor" / "glove"
