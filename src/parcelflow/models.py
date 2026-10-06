"""Shared value types for ParcelFlow. Kept dependency-free (stdlib only)."""
from __future__ import annotations

DESTINATIONS = ("DOMESTIC", "REGIONAL", "INTERNATIONAL")
SERVICES = ("STANDARD", "EXPRESS")
ROLES = ("customer", "ops", "admin")

MAX_WEIGHT_G = 50_000  # 50kg demo ceiling


class InvalidQuoteRequest(ValueError):
    """Raised when a quote request fails validation."""


class InvalidBookingRequest(ValueError):
    """Raised when a booking request fails validation."""


class AuthorizationError(PermissionError):
    """Raised when a role is not permitted to perform an action."""


class GatewayUnavailableError(RuntimeError):
    """Raised when the simulated carrier gateway exhausts retries without success."""
