# ParcelFlow Demo

A synthetic parcel-shipping demo application (quote, booking, simulated
carrier gateway, role-gated demo auth, SQLite persistence, two real API
consumer adapters, and a minimal UI). Built for evaluating change analysis,
test discovery, and risk/coverage reasoning tooling -- **not** a production
service and not an AI agent implementation.

## Requirements

- Python >= 3.11 (stdlib only; no third-party packages)
- Node.js (optional, only for the small UI validation unit tests under
  `ui/assets/*.test.js`)

## Run the API locally

```bash
python -c "
from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import load_environment, default_config_dir
import json

cfg = load_environment('ST', config_dir=default_config_dir())
conn = db.connect('parcelflow-demo.db')
db.init_schema(conn)
rate_card = json.load(open('reference-data/rate_card.json'))
server = create_server(cfg, rate_card, conn, port=8101, ui_dir='ui')
print('Serving on http://127.0.0.1:8101')
server.serve_forever()
"
```

Then open `http://127.0.0.1:8101/` for the minimal UI, or see
`openapi/postman_collection.json` for example requests.

## Run the tests

```bash
python scripts/run_tests.py
```

See `docs/architecture.md` for the full component breakdown, and
`docs/journeys.md` / `docs/requirements.md` for behavior coverage.

## Repository layout

- `src/parcelflow/` -- application code
- `consumers/` -- real executable API consumer adapters
- `ui/` -- minimal static UI
- `config/` -- per-environment (ST/SIT/UAT) configuration
- `reference-data/` -- rate card used by pricing
- `openapi/` -- OpenAPI contract + Postman collection
- `testcatalogue/` -- approved test catalogue, risk policy, synthetic history
- `snapshots/` -- synthetic captured runtime snapshots (not live-environment claims)
- `docs/` -- architecture, journeys, requirements
- `tests/` -- the real automated test suite
