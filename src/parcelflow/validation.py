"""Request body validation: size limits, JSON shape, and required fields.

Keeps HTTP-layer concerns (bytes in, size caps, JSON shape) out of the
pricing/booking domain logic, which validates domain values separately.
"""
from __future__ import annotations

import json

from parcelflow.models import InvalidBookingRequest, InvalidQuoteRequest

MAX_BODY_BYTES = 16_384

QUOTE_REQUIRED_FIELDS = {"weight_g", "destination", "service"}
QUOTE_V2_REQUIRED_FIELDS = {"weight_g", "destination", "service", "insured_value_cents"}
BOOKING_REQUIRED_FIELDS = {"quote_id"}


def _parse_json_object(body: bytes, error_cls):
    if len(body) > MAX_BODY_BYTES:
        raise error_cls(f"request body exceeds maximum size of {MAX_BODY_BYTES} bytes")
    try:
        doc = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error_cls("request body is not valid JSON") from exc
    if not isinstance(doc, dict):
        raise error_cls("request body must be a JSON object")
    return doc


def parse_quote_request(body: bytes) -> dict:
    doc = _parse_json_object(body, InvalidQuoteRequest)
    missing = QUOTE_REQUIRED_FIELDS - doc.keys()
    if missing:
        raise InvalidQuoteRequest(f"missing required field(s): {sorted(missing)}")
    unknown = doc.keys() - QUOTE_REQUIRED_FIELDS
    if unknown:
        raise InvalidQuoteRequest(f"unknown field(s): {sorted(unknown)}")
    return doc


def parse_quote_request_v2(body: bytes) -> dict:
    doc = _parse_json_object(body, InvalidQuoteRequest)
    missing = QUOTE_V2_REQUIRED_FIELDS - doc.keys()
    if missing:
        raise InvalidQuoteRequest(f"missing required field(s): {sorted(missing)}")
    unknown = doc.keys() - QUOTE_V2_REQUIRED_FIELDS
    if unknown:
        raise InvalidQuoteRequest(f"unknown field(s): {sorted(unknown)}")
    insured_value = doc["insured_value_cents"]
    if not isinstance(insured_value, int) or isinstance(insured_value, bool) or insured_value < 0:
        raise InvalidQuoteRequest("insured_value_cents must be a non-negative integer")
    return doc


def parse_booking_request(body: bytes) -> dict:
    doc = _parse_json_object(body, InvalidBookingRequest)
    missing = BOOKING_REQUIRED_FIELDS - doc.keys()
    if missing:
        raise InvalidBookingRequest(f"missing required field(s): {sorted(missing)}")
    unknown = doc.keys() - BOOKING_REQUIRED_FIELDS
    if unknown:
        raise InvalidBookingRequest(f"unknown field(s): {sorted(unknown)}")
    if not isinstance(doc["quote_id"], str) or not doc["quote_id"]:
        raise InvalidBookingRequest("quote_id must be a non-empty string")
    return doc
