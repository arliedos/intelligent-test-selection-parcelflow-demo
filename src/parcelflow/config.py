"""Environment configuration loading and validation for ParcelFlow.

Configuration is plain JSON per environment (ST/SIT/UAT). Nothing here reads
secrets directly; `secrets` fields hold opaque reference placeholders only
(e.g. "secret://..."), never real credential material, and must never be
echoed in error messages or logs.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

KNOWN_ENVIRONMENTS = ("ST", "SIT", "UAT")
KNOWN_ROLES = ("customer", "ops", "admin")

REQUIRED_TOP_LEVEL_KEYS = ("environment", "api", "gateway", "feature_flags", "roles", "secrets")
REQUIRED_API_KEYS = ("base_url", "port")
REQUIRED_GATEWAY_KEYS = ("base_url", "timeout_ms", "retry_count", "fallback_enabled", "simulation_enabled")
REQUIRED_ROLE_KEYS = ("quote_allowed_roles", "booking_allowed_roles", "dispatch_allowed_roles")


class ConfigValidationError(ValueError):
    """Raised when a configuration document fails validation.

    Messages must never include values from the `secrets` section.
    """


@dataclass(frozen=True)
class ParcelFlowConfig:
    environment: str
    api_base_url: str
    api_port: int
    gateway_base_url: str
    gateway_timeout_ms: int
    gateway_retry_count: int
    gateway_fallback_enabled: bool
    gateway_simulation_enabled: bool
    express_service_enabled: bool
    quote_allowed_roles: tuple = field(default_factory=tuple)
    booking_allowed_roles: tuple = field(default_factory=tuple)
    dispatch_allowed_roles: tuple = field(default_factory=tuple)
    secret_ref_keys: tuple = field(default_factory=tuple)
    raw: dict = field(default_factory=dict, repr=False, compare=False)


def _require_keys(obj: dict, keys: tuple, context: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ConfigValidationError(f"{context} missing required keys: {sorted(missing)}")


def _validate_roles(role_list: Any, context: str) -> tuple:
    if not isinstance(role_list, list) or not role_list:
        raise ConfigValidationError(f"{context} must be a non-empty list of role names")
    for role in role_list:
        if role not in KNOWN_ROLES:
            raise ConfigValidationError(f"{context} contains unknown role name")
    return tuple(role_list)


def validate_config_document(doc: dict) -> ParcelFlowConfig:
    if not isinstance(doc, dict):
        raise ConfigValidationError("configuration document must be a JSON object")

    _require_keys(doc, REQUIRED_TOP_LEVEL_KEYS, "configuration")

    environment = doc["environment"]
    if environment not in KNOWN_ENVIRONMENTS:
        raise ConfigValidationError(f"unknown environment name: {environment!r}")

    api = doc["api"]
    _require_keys(api, REQUIRED_API_KEYS, "api")
    if not isinstance(api["port"], int) or isinstance(api["port"], bool):
        raise ConfigValidationError("api.port must be an integer")

    gateway = doc["gateway"]
    _require_keys(gateway, REQUIRED_GATEWAY_KEYS, "gateway")
    for int_key in ("timeout_ms", "retry_count"):
        value = gateway[int_key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigValidationError(f"gateway.{int_key} must be an integer")
        if value < 0:
            raise ConfigValidationError(f"gateway.{int_key} must not be negative")
    for bool_key in ("fallback_enabled", "simulation_enabled"):
        if not isinstance(gateway[bool_key], bool):
            raise ConfigValidationError(f"gateway.{bool_key} must be a boolean")

    feature_flags = doc["feature_flags"]
    if "express_service_enabled" not in feature_flags:
        raise ConfigValidationError("feature_flags missing required keys: ['express_service_enabled']")
    if not isinstance(feature_flags["express_service_enabled"], bool):
        raise ConfigValidationError("feature_flags.express_service_enabled must be a boolean")

    roles = doc["roles"]
    _require_keys(roles, REQUIRED_ROLE_KEYS, "roles")
    quote_roles = _validate_roles(roles["quote_allowed_roles"], "roles.quote_allowed_roles")
    booking_roles = _validate_roles(roles["booking_allowed_roles"], "roles.booking_allowed_roles")
    dispatch_roles = _validate_roles(roles["dispatch_allowed_roles"], "roles.dispatch_allowed_roles")

    secrets = doc["secrets"]
    if not isinstance(secrets, dict):
        raise ConfigValidationError("secrets must be an object of reference placeholders")
    for key, value in secrets.items():
        if not isinstance(value, str) or not value.startswith("secret://"):
            raise ConfigValidationError(f"secrets.{key} must be an opaque 'secret://' reference placeholder")

    return ParcelFlowConfig(
        environment=environment,
        api_base_url=api["base_url"],
        api_port=api["port"],
        gateway_base_url=gateway["base_url"],
        gateway_timeout_ms=gateway["timeout_ms"],
        gateway_retry_count=gateway["retry_count"],
        gateway_fallback_enabled=gateway["fallback_enabled"],
        gateway_simulation_enabled=gateway["simulation_enabled"],
        express_service_enabled=feature_flags["express_service_enabled"],
        quote_allowed_roles=quote_roles,
        booking_allowed_roles=booking_roles,
        dispatch_allowed_roles=dispatch_roles,
        secret_ref_keys=tuple(sorted(secrets.keys())),
        raw=doc,
    )


def load_config_file(path: str) -> ParcelFlowConfig:
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    return validate_config_document(doc)


def load_environment(environment: str, config_dir: str) -> ParcelFlowConfig:
    if environment not in KNOWN_ENVIRONMENTS:
        raise ConfigValidationError(f"unknown environment name: {environment!r}")
    filename = f"{environment.lower()}.json"
    path = os.path.join(config_dir, filename)
    if not os.path.isfile(path):
        raise ConfigValidationError(f"no configuration file found for environment {environment!r}")
    return load_config_file(path)


def default_config_dir() -> str:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here, "config")
