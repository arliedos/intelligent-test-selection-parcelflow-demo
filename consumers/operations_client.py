"""Operations consumer adapter: the internal ops dashboard.

Real executable HTTP client (stdlib urllib only) against the ParcelFlow
demo API, operating with the "ops" demo role rather than "customer".
"""
from __future__ import annotations

from consumers.storefront_client import StorefrontApiError, StorefrontClient

DEFAULT_ROLE = "ops"


class OperationsClient(StorefrontClient):
    """Shares the same wire protocol as the storefront; differs only by role.

    Kept as a distinct consumer adapter (not a type alias) because it
    represents a separate deployed caller for consumer-reach analysis.
    """

    def __init__(self, base_url: str, role: str = DEFAULT_ROLE):
        super().__init__(base_url, role=role)

    def requote_v2(self, *, weight_g: int, destination: str, service: str, insured_value_cents: int) -> dict:
        """Ops-side re-quote against the v2 endpoint with insured value."""
        return self._call(
            "POST", "/api/v2/quotes",
            {
                "weight_g": weight_g, "destination": destination, "service": service,
                "insured_value_cents": insured_value_cents,
            },
        )


__all__ = ["OperationsClient", "StorefrontApiError"]
