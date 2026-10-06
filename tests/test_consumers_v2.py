import os
import tempfile
import threading
import unittest

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import validate_config_document
from consumers.storefront_client import StorefrontClient
from consumers.operations_client import OperationsClient

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


class ConsumerV2ReachTests(unittest.TestCase):
    """Demonstrates both real consumer adapters reach the new v2 quote
    endpoint -- not just the storefront, and not just a shared base class
    claim without evidence."""

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
        self.base_url = f"http://127.0.0.1:{self.port}"

    def _shutdown(self):
        self.server.shutdown()
        self.server.server_close()
        self.conn.close()
        os.remove(self.db_path)

    def test_storefront_client_reaches_v2_quote_endpoint(self):
        client = StorefrontClient(self.base_url)
        quote = client.request_quote_v2(
            weight_g=500, destination="DOMESTIC", service="STANDARD", insured_value_cents=20000,
        )
        self.assertEqual(quote["amount_cents"], 1200)
        self.assertEqual(quote["rate_card_version"], 2)

    def test_operations_client_reaches_v2_quote_endpoint(self):
        client = OperationsClient(self.base_url)
        quote = client.request_quote_v2(
            weight_g=500, destination="DOMESTIC", service="STANDARD", insured_value_cents=0,
        )
        self.assertEqual(quote["amount_cents"], 1000)
        self.assertEqual(quote["insured_value_cents"], 0)

    def test_operations_client_requotes_v2_with_insured_value(self):
        client = OperationsClient(self.base_url)
        quote = client.requote_v2(
            weight_g=500, destination="DOMESTIC", service="STANDARD", insured_value_cents=20000,
        )
        self.assertEqual(quote["amount_cents"], 1200)
        self.assertEqual(quote["insured_value_cents"], 20000)
        self.assertEqual(quote["rate_card_version"], 2)


if __name__ == "__main__":
    unittest.main()
