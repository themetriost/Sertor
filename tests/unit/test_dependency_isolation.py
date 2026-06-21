"""Dependency-isolation tests (068, TASK-C03): lexical floor without numpy, no download."""
from __future__ import annotations

import subprocess
import sys


def test_hashing_importable_without_numpy():
    """Importing the hashing adapter never requires numpy (REQ-010/053)."""
    code = (
        "import sys;"
        "sys.modules['numpy'] = None;"  # make numpy un-importable
        "import sertor_core.adapters.embeddings.hashing as h;"
        "print(h.HashingEmbedder().embed(['x'])[0][:1])"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.returncode == 0
    assert out.stdout.strip().startswith("[")


def test_hash_provider_does_not_import_numpy():
    """build_embedder with hash never pulls numpy into sys.modules (RNF-2/REQ-053)."""
    code = (
        "import sys;"
        "from sertor_core.composition import build_embedder;"
        "from sertor_core.config.settings import Settings;"
        "build_embedder(Settings(embed_provider='hash'));"
        "print('numpy' in sys.modules)"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"


def test_hash_provider_does_not_resolve_glove(monkeypatch):
    """Selecting hash never touches the GloVe resolver/downloader (REQ-024)."""
    from sertor_core.adapters.embeddings import glove_cache
    from sertor_core.composition import build_embedder
    from sertor_core.config.settings import Settings

    def boom(*a, **k):
        raise AssertionError("glove resolver/downloader must not be called for hash")

    monkeypatch.setattr(glove_cache, "resolve_glove_file", boom)
    monkeypatch.setattr(glove_cache, "ensure_glove", boom)
    build_embedder(Settings(embed_provider="hash"))
