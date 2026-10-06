import http.client
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
    "version": 1,
    "rates": {
        "DOMESTIC": {
            "STANDARD": {"base_cents": 500, "per_gram_cents": 1},
            "EXPRESS": {"base_cents": 1200, "per_gram_cents": 2},
        },
    },
}


def _config_doc(**overrides):
    doc = {
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
    doc.update(overrides)
    return doc


class ApiTestCase(unittest.TestCase):
    def setUp(self, config_doc=None):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = db.connect(self.db_path)
        db.init_schema(self.conn)
        cfg = validate_config_document(config_doc or _config_doc())
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

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def _request(self, method, path, body=None, role="customer", headers=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self._url(path), data=data, method=method)
        if role is not None:
            req.add_header("X-Demo-Role", role)
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())


class StaticUiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = db.connect(self.db_path)
        db.init_schema(self.conn)
        cfg = validate_config_document(_config_doc())
        ui_dir = os.path.join(os.path.dirname(__file__), "..", "ui")
        self.server = create_server(cfg, RATE_CARD, self.conn, ui_dir=ui_dir)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)

    def _shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.conn.close()
        os.remove(self.db_path)

    def test_root_serves_index_html(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type"))
            self.assertIn(b"ParcelFlow Demo", resp.read())

    def test_static_asset_served_with_correct_content_type(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/ui/assets/app.js") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.headers.get("Content-Type"))

    def test_path_traversal_outside_ui_dir_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/ui/../../pyproject.toml")
        self.assertEqual(ctx.exception.code, 404)


class HealthEndpointTests(ApiTestCase):
    def test_health_returns_environment(self):
        status, payload = self._request("GET", "/health", role=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload["environment"], "ST")


class QuoteEndpointTests(ApiTestCase):
    def test_valid_quote_returns_integer_amount(self):
        status, payload = self._request(
            "POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["amount_cents"], 1000)
        self.assertIsInstance(payload["amount_cents"], int)

    def test_quote_without_role_header_is_forbidden(self):
        status, payload = self._request(
            "POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"}, role=None,
        )
        self.assertEqual(status, 403)

    def test_quote_with_invalid_weight_returns_400(self):
        status, payload = self._request(
            "POST", "/api/quotes", {"weight_g": -1, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        self.assertEqual(status, 400)

    def test_quote_for_express_when_disabled_returns_400(self):
        status, payload = self._request(
            "POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "EXPRESS"},
        )
        self.assertEqual(status, 400)

    def test_error_response_never_leaks_secret_reference(self):
        status, payload = self._request("POST", "/api/quotes", {"bogus": 1})
        self.assertEqual(status, 400)
        self.assertNotIn("secret://", json.dumps(payload))


class BookingEndpointTests(ApiTestCase):
    def _create_quote(self):
        _, payload = self._request(
            "POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
        )
        return payload["quote_id"]

    def test_booking_success_path(self):
        quote_id = self._create_quote()
        status, payload = self._request(
            "POST", "/api/bookings", {"quote_id": quote_id},
            headers={"X-Simulate-Gateway-Outcomes": "success"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["status"], "CONFIRMED")
        self.assertEqual(payload["attempts"], 1)

    def test_booking_retries_on_timeout_then_succeeds(self):
        quote_id = self._create_quote()
        status, payload = self._request(
            "POST", "/api/bookings", {"quote_id": quote_id},
            headers={"X-Simulate-Gateway-Outcomes": "timeout,success"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["attempts"], 2)

    def test_booking_falls_back_when_retries_exhausted(self):
        quote_id = self._create_quote()
        status, payload = self._request(
            "POST", "/api/bookings", {"quote_id": quote_id},
            headers={"X-Simulate-Gateway-Outcomes": "timeout,timeout"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["status"], "CONFIRMED_FALLBACK")

    def test_booking_for_missing_quote_returns_404(self):
        status, payload = self._request("POST", "/api/bookings", {"quote_id": "nope"})
        self.assertEqual(status, 404)

    def test_get_booking_returns_persisted_record(self):
        quote_id = self._create_quote()
        _, created = self._request(
            "POST", "/api/bookings", {"quote_id": quote_id},
            headers={"X-Simulate-Gateway-Outcomes": "success"},
        )
        status, fetched = self._request("GET", f"/api/bookings/{created['booking_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["status"], "CONFIRMED")

    def test_get_booking_without_role_header_is_forbidden(self):
        quote_id = self._create_quote()
        _, created = self._request(
            "POST", "/api/bookings", {"quote_id": quote_id},
            headers={"X-Simulate-Gateway-Outcomes": "success"},
        )
        status, _ = self._request("GET", f"/api/bookings/{created['booking_id']}", role=None)
        self.assertEqual(status, 403)

    def test_get_booking_with_role_outside_allow_list_is_forbidden(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = db.connect(db_path)
        db.init_schema(conn)
        doc = _config_doc()
        doc["roles"]["booking_allowed_roles"] = ["admin"]
        cfg = validate_config_document(doc)
        server = create_server(cfg, RATE_CARD, conn)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def cleanup():
            server.shutdown()
            server.server_close()
            conn.close()
            os.remove(db_path)

        self.addCleanup(cleanup)

        def request(method, path, body=None, role="customer", headers=None):
            data = json.dumps(body).encode("utf-8") if body is not None else None
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
            if role is not None:
                req.add_header("X-Demo-Role", role)
            for key, value in (headers or {}).items():
                req.add_header(key, value)
            if data is not None:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req) as resp:
                    return resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read())

        _, quote = request("POST", "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"})
        _, created = request(
            "POST", "/api/bookings", {"quote_id": quote["quote_id"]}, role="admin",
            headers={"X-Simulate-Gateway-Outcomes": "success"},
        )
        status, _ = request("GET", f"/api/bookings/{created['booking_id']}", role="customer")
        self.assertEqual(status, 403)

    def test_non_numeric_content_length_returns_400(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        conn.putrequest("POST", "/api/quotes")
        conn.putheader("X-Demo-Role", "customer")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", "not-a-number")
        conn.endheaders()
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        resp.read()
        conn.close()


if __name__ == "__main__":
    unittest.main()
