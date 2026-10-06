#!/usr/bin/env python3
"""Compares a runtime snapshot's observed fields against a repository config file
for the same environment, reporting any mismatched field names and values.

Usage:
    python scripts/check_runtime_snapshot.py <snapshot.json> <config.json>

Exit codes: 0 match, 1 mismatch, 2 invalid input (missing file, malformed
JSON, or a snapshot/config missing required fields).

Never prints secret references: only the four comparison fields below are
read from either file.
"""
from __future__ import annotations

import json
import sys
from typing import Any

COMPARED_FIELDS = (
    "gateway_base_url",
    "gateway_timeout_ms",
    "gateway_retry_count",
    "express_service_enabled",
)


class InvalidInputError(ValueError):
    pass


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidInputError(f"could not read JSON from {path!r}: {exc}") from exc


def _extract_snapshot_fields(snapshot: dict) -> dict:
    try:
        observed = snapshot["observed"]
        return {
            "gateway_base_url": observed["gateway_base_url"],
            "gateway_timeout_ms": observed["gateway_timeout_ms"],
            "gateway_retry_count": observed["gateway_retry_count"],
            "express_service_enabled": observed["feature_flags"]["express_service_enabled"],
        }
    except (KeyError, TypeError) as exc:
        raise InvalidInputError(f"snapshot missing required field: {exc}") from exc


def _extract_config_fields(config: dict) -> dict:
    try:
        gateway = config["gateway"]
        return {
            "gateway_base_url": gateway["base_url"],
            "gateway_timeout_ms": gateway["timeout_ms"],
            "gateway_retry_count": gateway["retry_count"],
            "express_service_enabled": config["feature_flags"]["express_service_enabled"],
        }
    except (KeyError, TypeError) as exc:
        raise InvalidInputError(f"config missing required field: {exc}") from exc


def check_snapshot_against_config(snapshot_path: str, config_path: str) -> dict[str, Any]:
    snapshot = _load_json(snapshot_path)
    config = _load_json(config_path)

    snapshot_fields = _extract_snapshot_fields(snapshot)
    config_fields = _extract_config_fields(config)

    differences = []
    for field_name in COMPARED_FIELDS:
        snapshot_value = snapshot_fields[field_name]
        config_value = config_fields[field_name]
        if snapshot_value != config_value:
            differences.append(
                {
                    "field": field_name,
                    "snapshot_value": snapshot_value,
                    "config_value": config_value,
                }
            )

    return {"match": not differences, "differences": differences}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(json.dumps({"error": "usage: check_runtime_snapshot.py <snapshot.json> <config.json>"}))
        return 2

    snapshot_path, config_path = argv
    try:
        report = check_snapshot_against_config(snapshot_path, config_path)
    except InvalidInputError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2

    print(json.dumps(report, indent=2))
    return 0 if report["match"] else 1


if __name__ == "__main__":
    sys.exit(main())
