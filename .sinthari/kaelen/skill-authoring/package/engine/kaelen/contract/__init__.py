"""The declaration contract: one schema artefact per contract major version.

The supported versions are discovered from the artefacts this package carries — never
listed beside them — so what the engine claims to support is what it can actually read.
"""

from __future__ import annotations

import json
import re
from functools import cache
from importlib import resources

from kaelen.contract.schema_eval import check_keywords

_ARTEFACT = re.compile(r"^declaration-v(\d+)\.schema\.json$")


def supported_versions() -> list[int]:
    found = []
    for entry in resources.files(__name__).iterdir():
        match = _ARTEFACT.match(entry.name)
        if match:
            found.append(int(match.group(1)))
    return sorted(found)


def raw_schema(version: int) -> dict:
    """The schema artefact of `version` exactly as shipped, before the targets are injected."""
    text = (
        resources.files(__name__)
        .joinpath(f"declaration-v{version}.schema.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(text)


@cache
def load_schema(version: int) -> dict:
    """The schema of `version`, with the known targets injected from the placement rule.

    The rule is the only list of targets (specs/016 FR-002); refuses (fails loud) a keyword the
    evaluator lacks.
    """
    from kaelen.placement import load_rule

    schema = raw_schema(version)
    schema["$defs"]["target"]["enum"] = list(load_rule()["targets"])
    check_keywords(schema)
    return schema
