# Component / dependency / consumer map

## Components

| Component | File | Depends on |
|---|---|---|
| HTTP app | `src/parcelflow/app.py` | config, pricing, auth, validation, gateway, db |
| Config loader | `src/parcelflow/config.py` | (none -- stdlib `json` only) |
| Pricing | `src/parcelflow/pricing.py` | models, reference-data/rate_card.json |
| Gateway simulator | `src/parcelflow/gateway.py` | models |
| Role auth | `src/parcelflow/auth.py` | models |
| Persistence | `src/parcelflow/db.py` | stdlib `sqlite3`, migrations |
| Migrations | `src/parcelflow/migrations.py` | db (operates on connections produced by `db.connect`) |
| Request validation | `src/parcelflow/validation.py` | models |
| Contract checker | `src/parcelflow/contract_check.py` | (none -- stdlib `json` only) |
| Shared models | `src/parcelflow/models.py` | (none) |

## Consumers (real executable clients)

| Consumer | File | Role used | Calls |
|---|---|---|---|
| Storefront | `consumers/storefront_client.py` | `customer` (default, overridable) | `POST /api/quotes`, `POST /api/bookings`, `GET /api/bookings/{id}` |
| Operations | `consumers/operations_client.py` | `ops` (default, overridable) | same endpoints as storefront (subclass) |

## UI

| Asset | File | Notes |
|---|---|---|
| Markup | `ui/index.html` | Quote form, role selector, error/result regions |
| Validation/escaping | `ui/assets/validation.js` | Tested with Node's built-in test runner (`node --test`) |
| Wiring | `ui/assets/app.js` | fetch() calls into same-origin API |
| Styles | `ui/assets/styles.css` | Minimal, no framework |

## Contract assets

| Asset | File |
|---|---|
| OpenAPI | `openapi/openapi.json` |
| Postman collection | `openapi/postman_collection.json` |

This map reflects the baseline. Scenario branches that move or rename files
intentionally update only the entries relevant to that branch's diff; see
each branch's section of the external `scenario-manifest.json` for the
actual changed-files list from `git diff`.
