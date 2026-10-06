import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import validate_config_document

RATE_CARD = {
    "version": 2,
    "rates": {"DOMESTIC": {"STANDARD": {"base_cents": 500, "per_gram_cents": 1}}},
}


def _config_doc():
    return {
        "environment": "ST",
        "api": {"base_url": "http://parcelflow.st.internal.invalid", "port": 8101},
        "gateway": {
            "base_url": "http://carrier-gateway.st.internal.invalid",
            "timeout_ms": 2000, "retry_count": 1, "fallback_enabled": True, "simulation_enabled": True,
        },
        "feature_flags": {"express_service_enabled": False},
        "roles": {
            "quote_allowed_roles": ["customer", "ops", "admin"],
            "booking_allowed_roles": ["customer", "ops", "admin"],
            "dispatch_allowed_roles": ["ops", "admin"],
        },
        "secrets": {"gateway_api_key_ref": "secret://parcelflow/st/gateway-api-key"},
    }


class ApiV2TestCase(unittest.TestCase):
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

    def _shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.conn.close()
        os.remove(self.db_path)

    def _request(self, method, path, body=None, role="customer"):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if role is not None:
            req.add_header("X-Demo-Role", role)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())


class V1BehaviorUnchangedTests(ApiV2TestCase):
    def test_v1_quote_endpoint_still_returns_201_without_insured_value(self):
        status, payload = self._request(
            "POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["amount_cents"], 1000)
        self.assertNotIn("insured_value_cents", payload)
        self.assertNotIn("rate_card_version", payload)

    def test_v1_quote_endpoint_rejects_insured_value_as_unknown_field(self):
        status, payload = self._request(
            "POST", "/api/quotes",
            {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD", "insured_value_cents": 1000},
        )
        self.assertEqual(status, 400)


class V2QuoteEndpointTests(ApiV2TestCase):
    def test_v2_quote_requires_insured_value_cents(self):
        status, payload = self._request(
            "POST", "/api/v2/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        self.assertEqual(status, 400)

    def test_v2_quote_returns_200_with_insurance_fee_and_rate_card_version(self):
        status, payload = self._request(
            "POST", "/api/v2/quotes",
            {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD", "insured_value_cents": 20000},
        )
        self.assertEqual(status, 200)
        # base 1000 + 1% of 20000 (floor) = 1000 + 200 = 1200
        self.assertEqual(payload["amount_cents"], 1200)
        self.assertEqual(payload["insured_value_cents"], 20000)
        self.assertEqual(payload["rate_card_version"], 2)

    def test_v2_quote_rejects_negative_insured_value(self):
        status, payload = self._request(
            "POST", "/api/v2/quotes",
            {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD", "insured_value_cents": -1},
        )
        self.assertEqual(status, 400)

    def test_v2_quote_still_requires_role_header(self):
        status, payload = self._request(
            "POST", "/api/v2/quotes",
            {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD", "insured_value_cents": 0},
            role=None,
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
