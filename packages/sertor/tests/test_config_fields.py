"""Tests for the field catalog + secret masking (feature 051, T-100/T-110).

The coverage test (T-110-COV) is the no-drift invariant between the static catalog and the single
source `Settings.validate_backend()`: a CI-safe, offline, pure test (no network, no cloud env).
"""
from __future__ import annotations

from itertools import product

from sertor_core.config.settings import Settings
from sertor_installer.configure_fields import (
    FIELD_CATALOG,
    ConfigField,
    FieldStatus,
    get_field,
    mask_secret,
)

# --- T-100: mask_secret ------------------------------------------------------------------------


def test_mask_secret_empty():
    assert mask_secret("") == "(unset)"
    assert mask_secret("   ") == "(unset)"


def test_mask_secret_short():
    assert mask_secret("abcd") == "****"  # 4 chars: no suffix revealed


def test_mask_secret_long():
    assert mask_secret("abcdefghwxyz") == "****wxyz"  # 12 chars → last 4


def test_mask_secret_pure():
    secret = "sk-my-secret-key"
    masked = mask_secret(secret)
    assert secret not in masked  # anti-leak: the original never appears in the masked form


# --- T-110: catalog ----------------------------------------------------------------------------


def test_field_catalog_secret_flags():
    assert FIELD_CATALOG["AZURE_OPENAI_API_KEY"].secret is True
    assert FIELD_CATALOG["AZURE_SEARCH_API_KEY"].secret is True
    assert FIELD_CATALOG["AZURE_OPENAI_ENDPOINT"].secret is False
    assert FIELD_CATALOG["AZURE_OPENAI_EMBED_DEPLOYMENT"].secret is False
    assert FIELD_CATALOG["AZURE_SEARCH_ENDPOINT"].secret is False


def test_field_catalog_default_deployment():
    assert FIELD_CATALOG["AZURE_OPENAI_EMBED_DEPLOYMENT"].default == "text-embedding-3-large"


def test_get_field_unknown_raises():
    try:
        get_field("NOT_A_FIELD")
    except KeyError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected KeyError for an unknown field name")


def test_field_status_values():
    assert FieldStatus.SET.value == "set"
    assert FieldStatus.KEPT.value == "kept"
    assert FieldStatus.MISSING.value == "missing"
    assert FieldStatus.OVERWRITTEN.value == "overwritten"


def test_config_field_is_presentation_only():
    f = ConfigField("X", "desc", secret=True, default=None)
    assert f.name == "X"
    assert f.secret is True
    assert f.default is None


# --- T-110-COV: catalog ↔ validate_backend coverage (no drift) --------------------------------


def test_catalog_covers_all_validate_backend_fields():
    """For every (backend, store) combo, every name `validate_backend()` emits is in the catalog.

    Builds a `Settings` with empty cloud fields so the validator reports every required name; if the
    core adds a required field not covered by the catalog, this test fails (Principio V / no drift).
    """
    for provider, store in product(("azure", "glove", "hash", "ollama"), ("local", "azure")):
        settings = Settings(
            embed_provider=provider,
            store_backend=store,
            azure_openai_endpoint="",
            azure_openai_api_key="",
            azure_openai_embed_deployment="",
            azure_search_endpoint="",
            azure_search_api_key="",
        )
        for name in settings.validate_backend():
            assert name in FIELD_CATALOG, (
                f"validate_backend emits {name!r} for provider={provider}/store={store} "
                f"but the catalog does not cover it (drift)"
            )


def test_local_profile_no_required_fields():
    """provider=glove, store=local → validate_backend returns [] (SC-007: local-only, no cloud)."""
    settings = Settings(embed_provider="glove", store_backend="local")
    assert settings.validate_backend() == []
