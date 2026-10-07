"""Test 137 — the `openai` provider against the real service (marker `cloud`, not in local CI).

Skipped unless `OPENAI_API_KEY` is set in the environment. Embeds two texts through the
composition root, as a vehicle would, and checks count and dimension of the default model.
"""
from __future__ import annotations

import os

import pytest

from sertor_core.composition import build_embedder
from sertor_core.config.settings import Settings

pytestmark = [pytest.mark.cloud, pytest.mark.integration]


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set")
def test_openai_embeds_with_default_model():
    settings = Settings(
        embed_provider="openai",
        openai_api_key=os.environ["OPENAI_API_KEY"],
        embed_cache_enabled=False,
    )
    embedder = build_embedder(settings)
    vectors = embedder.embed(["where is the embedding provider selected?", "def build_embedder"])
    assert len(vectors) == 2
    assert embedder.dim == 3072          # text-embedding-3-large
    assert all(len(v) == 3072 for v in vectors)
