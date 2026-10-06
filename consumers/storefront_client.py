"""Storefront consumer adapter: the customer-facing checkout flow.

Real executable HTTP client (stdlib urllib only) against the ParcelFlow
demo API. Used both as a runnable asset and as a consumer-reach example for
contract-change impact analysis.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_ROLE = "customer"


class StorefrontApiError(RuntimeError):
    def __init__(self, status: int, payload: dict):
        super().__init__(f"storefront API error {status}: {payload}")
        self.status = status
        self.payload = payload


class StorefrontClient:
    def __init__(self, base_url: str, role: str = DEFAULT_ROLE):
        self.base_url = base_url.rstrip("/")
        self.role = role

    def _call(self, method: str, path: str, body: dict | None = None, extra_headers: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method)
        req.add_header("X-Demo-Role", self.role)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        for key, value in (extra_headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read())
            raise StorefrontApiError(exc.code, payload) from exc

    def request_quote(self, *, weight_g: int, destination: str, service: str) -> dict:
        return self._call(
            "POST", "/api/quotes", {"weight_g": weight_g, "destination": destination, "service": service},
        )

    def request_quote_v2(self, *, weight_g: int, destination: str, service: str, insured_value_cents: int) -> dict:
        return self._call(
            "POST", "/api/v2/quotes",
            {
                "weight_g": weight_g, "destination": destination, "service": service,
                "insured_value_cents": insured_value_cents,
            },
        )

    def create_booking(self, quote_id: str, simulate_outcomes: list[str] | None = None) -> dict:
        headers = {}
        if simulate_outcomes:
            headers["X-Simulate-Gateway-Outcomes"] = ",".join(simulate_outcomes)
        return self._call("POST", "/api/bookings", {"quote_id": quote_id}, extra_headers=headers)

    def get_booking(self, booking_id: str) -> dict:
        return self._call("GET", f"/api/bookings/{booking_id}")
