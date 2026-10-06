import json
import os
import tempfile
import threading
import unittest

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import validate_config_document
from parcelflow.contract_check import load_openapi, validate_against_schema

RATE_CARD = {
    "version": 1,
    "rates": {"DOMESTIC": {"STANDARD": {"base_cents": 500, "per_gram_cents": 1}}},
}

OPENAPI_PATH = os.path.join(os.path.dirname(__file__), "..", "openapi", "openapi.json")


def _config_doc():
    return {
        "environment": "ST",
        "api": {"base_url": "http://parcelflow.st.internal.invalid", "port": 8101},
        "gateway": {
            "base_url": "http://carrier-gateway.st.internal.invalid",
            "timeout_ms": 2000,
            "retry_count": 1,
            "fallback_enabled": True,
            "simulation_enabled": True,
        },
        "feature_flags": {"express_service_enabled": False},
        "roles": {
            "quote_allowed_roles": ["customer", "ops", "admin"],
            "booking_allowed_roles": ["customer", "ops", "admin"],
            "dispatch_allowed_roles": ["ops", "admin"],
        },
        "secrets": {"gateway_api_key_ref": "secret://parcelflow/st/gateway-api-key"},
    }


class OpenApiSchemaValidatorTests(unittest.TestCase):
    """Unit-level tests of the validator itself, independent of the running API."""

    def test_valid_document_passes(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        validate_against_schema({"a": 1}, schema)  # no raise

    def test_missing_required_field_fails(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        with self.assertRaises(AssertionError):
            validate_against_schema({}, schema)

    def test_wrong_type_fails(self):
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}
        with self.assertRaises(AssertionError):
            validate_against_schema({"a": "not an int"}, schema)

    def test_enum_violation_fails(self):
        schema = {"type": "string", "enum": ["X", "Y"]}
        with self.assertRaises(AssertionError):
            validate_against_schema("Z", schema)


class RuntimeContractConformanceTests(unittest.TestCase):
    """Exercises the real running API and checks responses against openapi.json.

    This is the mechanism scenario/openapi-drift relies on to detect contract
    claims diverging from implementation -- unchanged here, intentionally
    reused as-is by that branch.
    """

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = db.connect(self.db_path)
        db.init_schema(self.conn)
        cfg = validate_config_document(_config_doc())
        self.server = create_server(cfg, RATE_CARD, self.conn)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.spec = load_openapi(OPENAPI_PATH)

    def _shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.conn.close()
        os.remove(self.db_path)

    def _get(self, path):
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as resp:
            return json.loads(resp.read())

    def _post(self, path, body, role="customer"):
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
        )
        req.add_header("X-Demo-Role", role)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def test_health_response_matches_documented_schema(self):
        payload = self._get("/health")
        schema = self.spec["components"]["schemas"]["HealthResponse"]
        validate_against_schema(payload, schema)

    def test_quote_response_matches_documented_schema(self):
        payload = self._post(
            "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        schema = self.spec["components"]["schemas"]["QuoteResponseV1"]
        validate_against_schema(payload, schema)

    def test_booking_response_matches_documented_schema(self):
        quote = self._post(
            "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        booking = self._post("/api/bookings", {"quote_id": quote["quote_id"]})
        schema = self.spec["components"]["schemas"]["BookingResponse"]
        validate_against_schema(booking, schema)


if __name__ == "__main__":
    unittest.main()
