"""Field catalog and secret masking for `sertor configure` (feature 051, data-model §2).

`mask_secret` is the SINGLE point that decides how a secret is shown (T-100): prompts AND reports
go through it, so no secret value ever leaks in clear (FR-013/SC-008). `FIELD_CATALOG` is a static
**presentation** map (T-110): description + secret flag + default for the names that
`Settings.validate_backend()` can emit. It is NOT a second "which fields are required" list — that
is `validate_backend` (the single source, Principio VIII); a coverage test (T-110-COV) asserts the
catalog covers every name the validator can produce, so the core cannot add a required field
without the test failing (no silent drift).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


def mask_secret(value: str) -> str:
    """Mask a secret for display (the only place that decides how, research Punto 2).

    Empty / whitespace-only → `"(unset)"`; shorter than 8 chars → `"****"` (no suffix, too short to
    reveal a tail safely); otherwise `"****" + value[-4:]` (a short tail to recognise it without
    leaking it). Pure function, stdlib-only.
    """
    if not value or not value.strip():
        return "(unset)"
    if len(value) < 8:
        return "****"
    return "****" + value[-4:]


class FieldStatus(StrEnum):
    """Outcome of resolving a single field (data-model §3)."""

    SET = "set"               # a new value was resolved (flag/env/prompt/template-default)
    KEPT = "kept"             # an existing non-empty value was preserved (no overwrite)
    MISSING = "missing"       # no source resolved the value (irrisolto)
    OVERWRITTEN = "overwritten"  # an existing value was replaced on confirm/--overwrite


@dataclass(frozen=True)
class ConfigField:
    """Presentation metadata for a configuration field (data-model §2).

    `name` matches the env key that `validate_backend()` emits; `description` is shown in the
    prompt; `secret=True` → input via `getpass`, always masked in output; `default` is a non-secret
    proposed value (or `None`).
    """

    name: str
    description: str
    secret: bool
    default: str | None = None


# Static catalog (verified on `settings.py:203-214` + `env.azure.tmpl`). Only the names that
# `validate_backend` can emit appear here; the local profile needs none (Ollama/Chroma defaults).
FIELD_CATALOG: dict[str, ConfigField] = {
    "AZURE_OPENAI_ENDPOINT": ConfigField(
        "AZURE_OPENAI_ENDPOINT",
        "Azure OpenAI endpoint URL (e.g. https://my-resource.openai.azure.com/)",
        secret=False,
    ),
    "AZURE_OPENAI_API_KEY": ConfigField(
        "AZURE_OPENAI_API_KEY",
        "Azure OpenAI API key (secret)",
        secret=True,
    ),
    "AZURE_OPENAI_EMBED_DEPLOYMENT": ConfigField(
        "AZURE_OPENAI_EMBED_DEPLOYMENT",
        "Azure OpenAI embedding deployment name",
        secret=False,
        default="text-embedding-3-large",
    ),
    "AZURE_SEARCH_ENDPOINT": ConfigField(
        "AZURE_SEARCH_ENDPOINT",
        "Azure AI Search endpoint URL (only with --store azure)",
        secret=False,
    ),
    "AZURE_SEARCH_API_KEY": ConfigField(
        "AZURE_SEARCH_API_KEY",
        "Azure AI Search admin key (secret, only with --store azure)",
        secret=True,
    ),
}


def get_field(name: str) -> ConfigField:
    """Return the `ConfigField` for `name`, or raise `KeyError` if unknown (explicit, Princ. IV)."""
    return FIELD_CATALOG[name]
