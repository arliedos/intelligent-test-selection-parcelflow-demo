"""Quote pricing. All monetary arithmetic is integer cents -- no floats."""
from __future__ import annotations

from parcelflow.models import DESTINATIONS, MAX_WEIGHT_G, SERVICES, InvalidQuoteRequest


def compute_quote_cents(*, weight_g, destination: str, service: str, rate_card: dict, express_enabled: bool) -> int:
    if not isinstance(weight_g, int) or isinstance(weight_g, bool):
        raise InvalidQuoteRequest("weight_g must be an integer number of grams")
    if weight_g <= 0:
        raise InvalidQuoteRequest("weight_g must be a positive integer")
    if weight_g > MAX_WEIGHT_G:
        raise InvalidQuoteRequest(f"weight_g exceeds maximum of {MAX_WEIGHT_G} grams")
    if destination not in DESTINATIONS:
        raise InvalidQuoteRequest(f"unknown destination: {destination!r}")
    if service not in SERVICES:
        raise InvalidQuoteRequest(f"unknown service: {service!r}")
    if service == "EXPRESS" and not express_enabled:
        raise InvalidQuoteRequest("EXPRESS service is not enabled in this environment")

    rates = rate_card.get("rates", {})
    zone_rates = rates.get(destination)
    if zone_rates is None or service not in zone_rates:
        raise InvalidQuoteRequest("no rate defined for destination/service combination")

    rate = zone_rates[service]
    base_cents = rate["base_cents"]
    per_gram_cents = rate["per_gram_cents"]
    return base_cents + per_gram_cents * weight_g
