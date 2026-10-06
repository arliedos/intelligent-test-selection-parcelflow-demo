"""Minimal stdlib-only JSON Schema subset validator for OpenAPI conformance checks.

Deliberately not a full JSON Schema implementation -- supports only the
subset used by openapi.json in this repo: type, required, properties, enum,
and additionalProperties: false. Raises AssertionError (not a custom
exception) so failures show up as plain, unambiguous assertion failures in
test output, matching "a real check must detect the discrepancy".
"""
from __future__ import annotations

import json

_TYPE_MAP = {
    "object": dict,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "null": type(None),
}


def load_openapi(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _check_type(value, type_decl, path: str) -> None:
    types = type_decl if isinstance(type_decl, list) else [type_decl]
    py_types = tuple(_TYPE_MAP[t] for t in types)
    if bool in py_types and isinstance(value, bool):
        return
    if int in py_types and not isinstance(value, bool) and isinstance(value, int):
        return
    assert isinstance(value, py_types), f"{path}: expected type in {types}, got {type(value).__name__}"


def validate_against_schema(instance, schema: dict, path: str = "$") -> None:
    if "type" in schema:
        _check_type(instance, schema["type"], path)

    if "enum" in schema:
        assert instance in schema["enum"], f"{path}: value {instance!r} not in enum {schema['enum']}"

    if schema.get("type") == "object" or (isinstance(instance, dict) and "properties" in schema):
        assert isinstance(instance, dict), f"{path}: expected object"
        for required_key in schema.get("required", []):
            assert required_key in instance, f"{path}: missing required property '{required_key}'"
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(instance.keys()) - set(properties.keys())
            assert not unknown, f"{path}: unexpected properties {sorted(unknown)}"
        for key, value in instance.items():
            if key in properties:
                validate_against_schema(value, properties[key], path=f"{path}.{key}")
