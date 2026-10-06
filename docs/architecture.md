# ParcelFlow Demo: Architecture

Synthetic demo application. Not a production system. All third-party URLs
in this repo use `.invalid` hostnames and are never called over the network.

## Runtime shape

- **HTTP API** (`src/parcelflow/app.py`): stdlib `http.server.ThreadingHTTPServer`.
  Binds to `127.0.0.1` by default. Serves the JSON API and the minimal static
  UI (`ui/`) under `/` and `/ui/*`.
- **Pricing** (`src/parcelflow/pricing.py`): integer-cents quote calculation
  from a JSON rate card (`reference-data/rate_card.json`). No floats are ever
  used for currency.
- **Booking + Gateway** (`src/parcelflow/gateway.py`): a locally simulated
  carrier gateway. No real network calls. Outcomes (`success` / `timeout` /
  `decline`) are explicit and test-injectable via the
  `X-Simulate-Gateway-Outcomes` header, gated by
  `gateway.simulation_enabled` in the active environment config. Retry count
  and fallback behavior are entirely config-driven.
- **Role authorization** (`src/parcelflow/auth.py`): explicit local demo
  role simulation via the `X-Demo-Role` header (`customer` / `ops` /
  `admin`). This is **not** production authentication -- there is no
  session, token, or identity verification.
- **Persistence** (`src/parcelflow/db.py`): SQLite. One connection per
  server process, shared across request-handling threads behind a lock
  (`check_same_thread=False` + a `threading.Lock`).
- **Configuration** (`src/parcelflow/config.py`): one JSON document per
  environment (`config/st.json`, `config/sit.json`, `config/uat.json`),
  strictly validated (known environment name, known role names, integer
  retry/timeout values, `secret://`-prefixed secret reference placeholders
  only). Validation errors never echo secret reference values.
- **Consumers** (`consumers/`): two real, executable API clients
  (`storefront_client.py`, `operations_client.py`) built on stdlib
  `urllib`, used both as runnable assets and as a consumer-reach map for
  change-impact analysis.
- **Contract** (`openapi/openapi.json`, `openapi/postman_collection.json`):
  versioned OpenAPI document plus a Postman collection. A hand-rolled,
  stdlib-only schema-subset validator (`src/parcelflow/contract_check.py`)
  checks real runtime responses against the documented schemas
  (`tests/test_contract.py`).

## Environments

| Environment | Config file | Purpose |
|---|---|---|
| ST | `config/st.json` | Smoke/system test |
| SIT | `config/sit.json` | System integration test |
| UAT | `config/uat.json` | User acceptance test |

Runtime snapshot evidence under `snapshots/` is **synthetic captured data**,
not a claim of a live running service; see the `_provenance` field in each
snapshot file.

## Running locally

```
python scripts/run_tests.py
```

Runs the full Python stdlib `unittest` suite plus the Node built-in test
runner for the small UI validation module, and writes a JUnit-style XML
report plus a plain-text summary to `reports/` (gitignored). Exit code
reflects aggregate pass/fail.
