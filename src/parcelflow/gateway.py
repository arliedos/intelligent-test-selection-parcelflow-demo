"""Locally simulated carrier gateway with explicit injectable outcomes.

No real network calls are made. `outcomes` is an explicit, test-injectable
sequence of simulated results ("success" | "timeout" | "decline") consumed in
order as attempts are made. Retry policy (retry_count, fallback_enabled) is
driven entirely by environment configuration, never hardcoded.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterable, Sequence

from parcelflow.models import GatewayUnavailableError

VALID_OUTCOMES = ("success", "timeout", "decline")


@dataclass(frozen=True)
class GatewayConfirmation:
    attempts: int
    carrier_reference: str
    used_fallback: bool = False


class GatewaySimulator:
    def __init__(self, *, retry_count: int, fallback_enabled: bool, outcomes: Sequence[str]):
        if retry_count < 0:
            raise ValueError("retry_count must be >= 0")
        for outcome in outcomes:
            if outcome not in VALID_OUTCOMES:
                raise ValueError(f"invalid simulated outcome: {outcome!r}")
        self._retry_count = retry_count
        self._fallback_enabled = fallback_enabled
        self._outcomes = list(outcomes)

    def confirm_booking(self, *, booking_id: str) -> GatewayConfirmation:
        max_attempts = self._retry_count + 1
        attempts = 0
        for attempts, outcome in enumerate(itertools.islice(self._outcomes, max_attempts), start=1):
            if outcome == "success":
                return GatewayConfirmation(attempts=attempts, carrier_reference=f"CARR-{booking_id}")
            if outcome == "decline":
                break
            # "timeout": continue retry loop if attempts remain
        if self._fallback_enabled:
            return GatewayConfirmation(
                attempts=attempts, carrier_reference="FALLBACK-QUEUED", used_fallback=True,
            )
        raise GatewayUnavailableError(
            f"carrier gateway unavailable for booking {booking_id} after {attempts} attempt(s)"
        )
