import os
import tempfile
import threading
import unittest

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import validate_config_document
from consumers.storefront_client import StorefrontApiError, StorefrontClient
from consumers.operations_client import OperationsClient

RATE_CARD = {
    "version": 1,
    "rates": {
        "DOMESTIC": {"STANDARD": {"base_cents": 500, "per_gram_cents": 1}},
    },
}


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


class ConsumerAdapterTests(unittest.TestCase):
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

    def test_storefront_client_requests_quote_and_books_it(self):
        client = StorefrontClient(self.base_url)
        quote = client.request_quote(weight_g=500, destination="DOMESTIC", service="STANDARD")
        self.assertEqual(quote["amount_cents"], 1000)

        booking = client.create_booking(quote["quote_id"], simulate_outcomes=["success"])
        self.assertEqual(booking["status"], "CONFIRMED")

    def test_operations_client_reads_booking_status(self):
        storefront = StorefrontClient(self.base_url)
        quote = storefront.request_quote(weight_g=500, destination="DOMESTIC", service="STANDARD")
        booking = storefront.create_booking(quote["quote_id"], simulate_outcomes=["success"])

        ops = OperationsClient(self.base_url)
        fetched = ops.get_booking(booking["booking_id"])
        self.assertEqual(fetched["booking_id"], booking["booking_id"])
        self.assertEqual(fetched["status"], "CONFIRMED")

        unknown_role_client = StorefrontClient(self.base_url, role="courier")
        with self.assertRaises(StorefrontApiError) as ctx:
            unknown_role_client.get_booking(booking["booking_id"])
        self.assertEqual(ctx.exception.status, 403)

    def test_operations_client_can_also_create_bookings_on_behalf_of_customer(self):
        storefront = StorefrontClient(self.base_url)
        quote = storefront.request_quote(weight_g=250, destination="DOMESTIC", service="STANDARD")

        ops = OperationsClient(self.base_url)
        booking = ops.create_booking(quote["quote_id"], simulate_outcomes=["success"])
        self.assertEqual(booking["status"], "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
