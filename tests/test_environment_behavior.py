import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import KNOWN_ENVIRONMENTS, load_environment

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_DIR = os.path.join(REPO_ROOT, "config")
RATE_CARD = json.load(open(os.path.join(REPO_ROOT, "reference-data", "rate_card.json"), encoding="utf-8"))


class EnvironmentDrivenBehaviorTests(unittest.TestCase):
    """Loads the real config/<env>.json for every known environment and
    asserts that runtime behavior genuinely follows whatever that file says
    -- not a fixed expectation baked into the test. This is the mechanism
    scenario/sit-routing-policy relies on: changing only config/sit.json
    changes what this (unchanged) test observes for SIT, while ST/UAT are
    unaffected.
    """

    def _start_server(self, cfg):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = db.connect(db_path)
        db.init_schema(conn)
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
        return port

    def _post(self, port, path, body, role, extra_headers=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode("utf-8"), method="POST",
        )
        if role is not None:
            req.add_header("X-Demo-Role", role)
        req.add_header("Content-Type", "application/json")
        for key, value in (extra_headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_express_service_availability_follows_each_environments_feature_flag(self):
        for environment in KNOWN_ENVIRONMENTS:
            with self.subTest(environment=environment):
                cfg = load_environment(environment, config_dir=CONFIG_DIR)
                port = self._start_server(cfg)
                allowed_role = cfg.quote_allowed_roles[0]
                status, payload = self._post(
                    port, "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "EXPRESS"},
                    role=allowed_role,
                )
                if cfg.express_service_enabled:
                    self.assertEqual(status, 201, f"{environment}: EXPRESS should be quotable when the flag is enabled")
                    self.assertIsInstance(payload["amount_cents"], int)
                else:
                    self.assertEqual(status, 400, f"{environment}: EXPRESS should be rejected when the flag is disabled")

    def test_quote_role_restriction_follows_each_environments_allow_list(self):
        for environment in KNOWN_ENVIRONMENTS:
            with self.subTest(environment=environment):
                cfg = load_environment(environment, config_dir=CONFIG_DIR)
                port = self._start_server(cfg)
                for role in ("customer", "ops", "admin"):
                    status, _ = self._post(
                        port, "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
                        role=role,
                    )
                    if role in cfg.quote_allowed_roles:
                        self.assertEqual(
                            status, 201, f"{environment}: role {role!r} is in quote_allowed_roles and should be allowed",
                        )
                    else:
                        self.assertEqual(
                            status, 403, f"{environment}: role {role!r} is not in quote_allowed_roles and should be forbidden",
                        )

    def test_gateway_retry_count_bounds_total_attempts_per_environment(self):
        for environment in KNOWN_ENVIRONMENTS:
            with self.subTest(environment=environment):
                cfg = load_environment(environment, config_dir=CONFIG_DIR)
                port = self._start_server(cfg)
                allowed_role = cfg.quote_allowed_roles[0]
                status, quote = self._post(
                    port, "/api/quotes", {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"},
                    role=allowed_role,
                )
                self.assertEqual(status, 201)

                all_timeouts = ",".join(["timeout"] * (cfg.gateway_retry_count + 5))
                status, booking = self._post(
                    port, "/api/bookings", {"quote_id": quote["quote_id"]},
                    role=cfg.booking_allowed_roles[0],
                    extra_headers={"X-Simulate-Gateway-Outcomes": all_timeouts},
                )
                self.assertEqual(status, 201, f"{environment}: booking with retried timeouts should still succeed")
                # Every attempt times out: total attempts made must equal
                # retry_count + 1, regardless of how many timeouts were queued.
                self.assertEqual(booking["attempts"], cfg.gateway_retry_count + 1)


if __name__ == "__main__":
    unittest.main()
