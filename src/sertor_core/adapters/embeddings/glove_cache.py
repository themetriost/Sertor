"""GloVe acquisition & cache resolver (068, FEAT-011, DA-4).

Resolves the `glove.6B.300d.txt` data file for the GloVe embedder, with a machine-wide user cache
and an on-demand download bound to the INDEXING path (install≠run). Sola stdlib (`urllib`,
`zipfile`, `os`, `pathlib`): no new dependency, respects `HTTP(S)_PROXY`.

Resolution priority (REQ-032/035/040):
  1. `settings.glove_path` if set and existing → that file, no download.
  2. `glove.6B.300d.txt` in the user cache → reuse, no download.
  3. during indexing (`allow_download=True`) → download + extract atomically.
  4. otherwise → `GloveUnavailableError` (fail-loud, both exits named).

Acquisition is never triggered by `search`/`install`: only `build_indexer` passes
`allow_download=True` (REQ-034).
"""
from __future__ import annotations

import logging
import os
import tempfile
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from sertor_core.config.settings import Settings
from sertor_core.domain.errors import GloveUnavailableError
from sertor_core.observability.logging import log_event

_GLOVE_FILE = "glove.6B.300d.txt"
_GLOVE_ZIP_URL = "https://nlp.stanford.edu/data/glove.6B.zip"
_GLOVE_ZIP_MEMBER = "glove.6B.300d.txt"
_GLOVE_SIZE_MB = 822
_GLOVE_SOURCE_HOST = "nlp.stanford.edu"


def glove_cache_dir() -> Path:
    """Machine-wide user cache directory for GloVe data (stdlib, host-agnostic — REQ-031).

    Windows: `%LOCALAPPDATA%\\sertor\\glove`. POSIX: `$XDG_CACHE_HOME/sertor/glove` if set, else
    `~/.cache/sertor/glove`. Shared across projects (not tied to the host layout — Principio X).
    """
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "sertor" / "glove"
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "sertor" / "glove"


def resolve_glove_file(settings: Settings, *, allow_download: bool = False) -> Path:
    """Resolve the GloVe data file, downloading on-demand only when `allow_download` (REQ-032/034).

    `allow_download` is passed `True` only by the indexing path (`build_indexer`); query/search
    paths pass `False`, so a missing cache fails loud instead of triggering a 822 MB download.
    """
    if settings.glove_path is not None and settings.glove_path.exists():
        log_event(logging.INFO, "glove_cache_hit", hit=True)
        return settings.glove_path

    cached = glove_cache_dir() / _GLOVE_FILE
    if cached.exists():
        log_event(logging.INFO, "glove_cache_hit", hit=True)
        return cached

    log_event(logging.INFO, "glove_cache_hit", hit=False)
    if allow_download:
        return ensure_glove(settings)
    raise GloveUnavailableError(
        "GloVe vectors are not in the cache and acquisition is not allowed on this path",
        reason="cache_miss",
    )


def ensure_glove(settings: Settings) -> Path:
    """Acquire the GloVe data file on-demand: download + extract atomically (REQ-030/033/041).

    Emits a one-time `glove_download` warning before the (~822 MB) download. Downloads
    `glove.6B.zip` via `urllib`, extracts only `glove.6B.300d.txt` with `zipfile`, and installs it
    with an atomic `os.replace` (concurrency-safe without an explicit lock — DA-4). Network/HTTP or
    parse failures → `GloveUnavailableError` (fail-loud, never a silent fallback).
    """
    if settings.glove_path is not None and settings.glove_path.exists():
        return settings.glove_path
    cache_dir = glove_cache_dir()
    target = cache_dir / _GLOVE_FILE
    if target.exists():
        log_event(logging.INFO, "glove_cache_hit", hit=True)
        return target

    cache_dir.mkdir(parents=True, exist_ok=True)
    log_event(
        logging.WARNING, "glove_download",
        size_mb=_GLOVE_SIZE_MB, source_host=_GLOVE_SOURCE_HOST,
    )
    zip_fd, zip_tmp = tempfile.mkstemp(suffix=".zip", dir=cache_dir)
    os.close(zip_fd)
    zip_path = Path(zip_tmp)
    try:
        with urlopen(_GLOVE_ZIP_URL) as response, zip_path.open("wb") as out:  # noqa: S310
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    except (URLError, OSError) as exc:
        zip_path.unlink(missing_ok=True)
        raise GloveUnavailableError(
            "could not download the GloVe vectors", reason=type(exc).__name__
        ) from exc

    txt_fd, txt_tmp = tempfile.mkstemp(suffix=".txt", dir=cache_dir)
    os.close(txt_fd)
    txt_path = Path(txt_tmp)
    try:
        with zipfile.ZipFile(zip_path) as zf, zf.open(_GLOVE_ZIP_MEMBER) as src, \
                txt_path.open("wb") as dst:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        txt_path.unlink(missing_ok=True)
        zip_path.unlink(missing_ok=True)
        raise GloveUnavailableError(
            "could not extract the GloVe vectors from the archive", reason=type(exc).__name__
        ) from exc

    os.replace(txt_path, target)  # atomic install
    zip_path.unlink(missing_ok=True)
    return target
