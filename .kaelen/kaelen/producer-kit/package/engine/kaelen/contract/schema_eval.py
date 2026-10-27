"""A JSON Schema (2020-12) evaluator for the subset of keywords the contract uses.

The engine carries no runtime dependency (research R-1), so it evaluates its own schema
artefacts. The subset is closed: a schema using any other keyword is refused at load time
(`check_keywords`), because a rule the engine silently ignores is worse than no rule.
The test suite cross-checks this evaluator against the reference `jsonschema` library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ASSERTIONS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "minItems",
        "uniqueItems",
        "enum",
        "const",
        "pattern",
        "minLength",
        "$ref",
        "$defs",
        "allOf",
        "if",
        "then",
        "else",
        "not",
    }
)
ANNOTATIONS = frozenset({"$schema", "$id", "title", "description", "$comment", "default"})


class UnsupportedKeyword(Exception):
    """A schema artefact uses a keyword this evaluator does not implement."""

    def __init__(self, keyword: str, location: str):
        super().__init__(f"unsupported schema keyword {keyword!r} at {location or '#'}")
        self.keyword = keyword
        self.location = location


@dataclass(frozen=True)
class SchemaError:
    rule: str
    path: str
    message: str
    known: tuple[str, ...] | None = None


def check_keywords(schema, location: str = "") -> None:
    """Refuse any keyword outside the implemented subset, anywhere in the schema."""
    if isinstance(schema, bool):
        return
    for key, value in schema.items():
        if key not in ASSERTIONS and key not in ANNOTATIONS:
            raise UnsupportedKeyword(key, location)
        here = f"{location}/{key}"
        if key in ("properties", "$defs"):
            for name, sub in value.items():
                check_keywords(sub, f"{here}/{name}")
        elif key == "allOf":
            for i, sub in enumerate(value):
                check_keywords(sub, f"{here}/{i}")
        elif key in ("items", "additionalProperties", "if", "then", "else", "not"):
            check_keywords(value, here)


def evaluate(schema, instance) -> list[SchemaError]:
    """Every violation of `schema` by `instance`, in document order."""
    errors: list[SchemaError] = []
    _Evaluator(schema).run(schema, instance, (), errors)
    return errors


def format_path(tokens: tuple) -> str:
    out = ""
    for token in tokens:
        if isinstance(token, int):
            out += f"[{token}]"
        else:
            out += f".{token}" if out else str(token)
    return out


def _type_ok(name: str, value) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if name == "null":
        return value is None
    return False


def _describe(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _equal(a, b) -> bool:
    # JSON equality: booleans are not numbers.
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


class _Evaluator:
    def __init__(self, root):
        self.root = root

    def resolve(self, ref: str):
        if not ref.startswith("#"):
            raise UnsupportedKeyword("$ref (non-local)", ref)
        node = self.root
        for part in ref[1:].split("/")[1:]:
            node = node[part.replace("~1", "/").replace("~0", "~")]
        return node

    def valid(self, schema, instance) -> bool:
        probe: list[SchemaError] = []
        self.run(schema, instance, (), probe)
        return not probe

    def run(self, schema, instance, path: tuple, errors: list[SchemaError]) -> None:
        here = format_path(path)
        if schema is True:
            return
        if schema is False:
            errors.append(SchemaError("false-schema", here, "this element is not allowed here"))
            return

        if "$ref" in schema:
            self.run(self.resolve(schema["$ref"]), instance, path, errors)

        if "type" in schema and not _type_ok(schema["type"], instance):
            errors.append(
                SchemaError("type", here, f"expected {schema['type']}, found {_describe(instance)}")
            )
            return  # the remaining keywords would only repeat the type mismatch

        if "const" in schema and not _equal(schema["const"], instance):
            errors.append(SchemaError("const", here, f"must be {schema['const']!r}"))

        if "enum" in schema and not any(_equal(v, instance) for v in schema["enum"]):
            known = tuple(str(v) for v in schema["enum"])
            errors.append(SchemaError("enum", here, f"{instance!r} is not an allowed value", known))

        if isinstance(instance, str):
            if "minLength" in schema and len(instance) < schema["minLength"]:
                errors.append(
                    SchemaError("minLength", here, f"must be at least {schema['minLength']} long")
                )
            if "pattern" in schema and not re.search(schema["pattern"], instance):
                errors.append(
                    SchemaError("pattern", here, f"{instance!r} does not match {schema['pattern']}")
                )

        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                errors.append(
                    SchemaError("minItems", here, f"must have at least {schema['minItems']} entry")
                )
            if schema.get("uniqueItems"):
                seen: list = []
                for value in instance:
                    if any(_equal(value, s) for s in seen):
                        errors.append(SchemaError("uniqueItems", here, f"{value!r} is repeated"))
                        break
                    seen.append(value)
            if "items" in schema:
                for i, value in enumerate(instance):
                    self.run(schema["items"], value, path + (i,), errors)

        if isinstance(instance, dict):
            for name in schema.get("required", ()):
                if name not in instance:
                    errors.append(
                        SchemaError(
                            "required",
                            format_path(path + (name,)),
                            f"missing required field {name!r}",
                        )
                    )
            props = schema.get("properties", {})
            extra = schema.get("additionalProperties", True)
            for name, value in instance.items():
                if name in props:
                    self.run(props[name], value, path + (name,), errors)
                elif extra is False:
                    errors.append(
                        SchemaError(
                            "additionalProperties",
                            format_path(path + (name,)),
                            f"unknown field {name!r}",
                        )
                    )
                elif extra is not True:
                    self.run(extra, value, path + (name,), errors)

        for sub in schema.get("allOf", ()):
            self.run(sub, instance, path, errors)

        if "if" in schema:
            branch = "then" if self.valid(schema["if"], instance) else "else"
            if branch in schema:
                self.run(schema[branch], instance, path, errors)

        if "not" in schema and self.valid(schema["not"], instance):
            errors.append(SchemaError("not", here, "matches a form that is not allowed"))
