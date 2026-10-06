# User journeys

## J1: Customer requests a quote and books a shipment

1. Customer opens the storefront UI (or calls the storefront consumer
   adapter) and submits weight, destination, and service.
2. System validates the request shape (`validation.py`) and domain values
   (`pricing.py`), and returns an integer-cents quote.
3. Customer submits a booking referencing the `quote_id`.
4. System persists the booking (`PENDING`), calls the simulated carrier
   gateway with the environment's retry policy, and returns the final
   status (`CONFIRMED`, `CONFIRMED_FALLBACK`, or an error).

Covered by: `tests/test_api.py::QuoteEndpointTests`,
`tests/test_api.py::BookingEndpointTests`,
`tests/test_consumers.py::ConsumerAdapterTests::test_storefront_client_requests_quote_and_books_it`.

## J2: Ops reviews a booking's status

1. Ops dashboard (operations consumer adapter) fetches a booking by id.
2. System returns the persisted booking record, including attempt count and
   carrier reference (if any).

Covered by:
`tests/test_consumers.py::ConsumerAdapterTests::test_operations_client_reads_booking_status`.

## J3: Express service availability depends on environment

1. A customer requests an `EXPRESS` service quote.
2. If the active environment's `feature_flags.express_service_enabled` is
   `false` (the baseline default in ST/SIT/UAT), the request is rejected
   with `400`.
3. If enabled (see `scenario/sit-routing-policy`), the same request
   succeeds with EXPRESS-tier pricing.

Covered by: `tests/test_pricing.py::PricingTests::test_rejects_express_when_feature_flag_disabled`.

## J4: Carrier gateway degradation is retried and, if needed, falls back

1. Booking confirmation hits a simulated `timeout` outcome.
2. System retries up to `gateway.retry_count` additional times (config
   driven).
3. If retries are exhausted and `gateway.fallback_enabled` is true, the
   booking is queued via fallback instead of failing outright.

Covered by: `tests/test_gateway.py`, `tests/test_api.py::BookingEndpointTests`.

## J5: Service selector visibility narrows by demo role in the quote UI

1. Customer selects the `customer` demo role in the quote form.
2. The Service selector only offers `STANDARD`; `EXPRESS` is not listed.
3. Selecting `ops` or `admin` repopulates the Service selector with both
   `STANDARD` and `EXPRESS`.
4. This is a client-side UI affordance only -- it narrows what is *offered*,
   independent of the server-side environment gate in J3. It also conflicts
   with REQ-UI-1's original role-agnostic selector requirement; see that
   entry in `docs/requirements.md`.

Covered by: `ui/assets/form-validation.test.js` (role-to-visible-services
mapping, Node's built-in test runner). The role-driven DOM repopulation in
`ui/assets/app.js` is UI wiring and is not covered by an automated browser
test in this demo -- verifying it end-to-end would require manual or
browser-automation steps, which are out of scope here.
