# Baseline requirements

| ID | Requirement | Notes |
|---|---|---|
| REQ-QUOTE-1 | `POST /api/quotes` accepts integer `weight_g` (1-50000), enum `destination`, enum `service`. | No floats for weight or money. |
| REQ-QUOTE-2 | Quote amount is computed in integer cents from a versioned rate card. | `reference-data/rate_card.json` |
| REQ-QUOTE-3 | `EXPRESS` service is only quotable when `feature_flags.express_service_enabled` is true for the active environment. | Baseline: disabled in ST/SIT/UAT. |
| REQ-AUTH-1 | Every quote/booking request must present a known role (`customer`/`ops`/`admin`) via `X-Demo-Role`, checked against the environment's allow-list. | Demo-only; not production auth. |
| REQ-BOOK-1 | Booking confirmation retries against the simulated carrier gateway up to `gateway.retry_count` additional times on `timeout`. | `decline` is never retried. |
| REQ-BOOK-2 | If retries are exhausted and `gateway.fallback_enabled` is true, the booking is queued via fallback rather than failing. | |
| REQ-VALID-1 | Request bodies larger than 16KB are rejected before JSON parsing. | `validation.MAX_BODY_BYTES` |
| REQ-VALID-2 | Unknown fields in request bodies are rejected. | Strict shape validation. |
| REQ-CONFIG-1 | Configuration documents are validated for known environment name, known role names, and non-negative integer gateway timeout/retry values. | `config.py` |
| REQ-SEC-1 | Secret reference values must never appear in error messages or logs. | Enforced by `config.py` validation errors and `app.py` error handlers. |

These are baseline, non-exhaustive requirements -- sufficient to exercise
change-impact analysis across the scenario branches, not a claim of full
enterprise coverage.
