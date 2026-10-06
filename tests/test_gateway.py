import unittest

from parcelflow.gateway import GatewaySimulator
from parcelflow.models import GatewayUnavailableError


class GatewaySimulatorTests(unittest.TestCase):
    def test_success_on_first_attempt_returns_reference(self):
        gw = GatewaySimulator(retry_count=2, fallback_enabled=False, outcomes=["success"])
        result = gw.confirm_booking(booking_id="b1")
        self.assertEqual(result.attempts, 1)
        self.assertTrue(result.carrier_reference.startswith("CARR-"))

    def test_timeout_then_success_retries_and_reports_attempts(self):
        gw = GatewaySimulator(retry_count=2, fallback_enabled=False, outcomes=["timeout", "success"])
        result = gw.confirm_booking(booking_id="b2")
        self.assertEqual(result.attempts, 2)
        self.assertTrue(result.carrier_reference.startswith("CARR-"))

    def test_exhausted_retries_without_fallback_raises(self):
        gw = GatewaySimulator(retry_count=1, fallback_enabled=False, outcomes=["timeout", "timeout"])
        with self.assertRaises(GatewayUnavailableError):
            gw.confirm_booking(booking_id="b3")

    def test_decline_is_not_retried_even_with_retries_remaining(self):
        gw = GatewaySimulator(retry_count=3, fallback_enabled=False, outcomes=["decline", "success"])
        with self.assertRaises(GatewayUnavailableError):
            gw.confirm_booking(booking_id="b4")

    def test_fallback_used_after_retries_exhausted_when_enabled(self):
        gw = GatewaySimulator(retry_count=1, fallback_enabled=True, outcomes=["timeout", "timeout"])
        result = gw.confirm_booking(booking_id="b5")
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.carrier_reference, "FALLBACK-QUEUED")
        self.assertTrue(result.used_fallback)

    def test_retry_count_bounds_total_attempts(self):
        gw = GatewaySimulator(retry_count=0, fallback_enabled=False, outcomes=["success"])
        result = gw.confirm_booking(booking_id="b6")
        self.assertEqual(result.attempts, 1)

        gw2 = GatewaySimulator(retry_count=0, fallback_enabled=False, outcomes=["timeout", "success"])
        with self.assertRaises(GatewayUnavailableError):
            gw2.confirm_booking(booking_id="b7")


if __name__ == "__main__":
    unittest.main()
