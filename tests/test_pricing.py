import unittest

from parcelflow import pricing
from parcelflow.models import InvalidQuoteRequest

RATE_CARD = {
    "version": 1,
    "rates": {
        "DOMESTIC": {
            "STANDARD": {"base_cents": 500, "per_gram_cents": 1},
            "EXPRESS": {"base_cents": 1200, "per_gram_cents": 2},
        },
        "REGIONAL": {
            "STANDARD": {"base_cents": 900, "per_gram_cents": 2},
            "EXPRESS": {"base_cents": 1800, "per_gram_cents": 3},
        },
        "INTERNATIONAL": {
            "STANDARD": {"base_cents": 1500, "per_gram_cents": 3},
            "EXPRESS": {"base_cents": 2600, "per_gram_cents": 4},
        },
    },
}


class PricingTests(unittest.TestCase):
    def test_domestic_standard_quote_is_integer_cents(self):
        amount = pricing.compute_quote_cents(
            weight_g=500, destination="DOMESTIC", service="STANDARD",
            rate_card=RATE_CARD, express_enabled=True,
        )
        self.assertEqual(amount, 500 + 500 * 1)
        self.assertIsInstance(amount, int)

    def test_international_express_quote(self):
        amount = pricing.compute_quote_cents(
            weight_g=250, destination="INTERNATIONAL", service="EXPRESS",
            rate_card=RATE_CARD, express_enabled=True,
        )
        self.assertEqual(amount, 2600 + 250 * 4)

    def test_rejects_zero_or_negative_weight(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=0, destination="DOMESTIC", service="STANDARD",
                rate_card=RATE_CARD, express_enabled=True,
            )
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=-5, destination="DOMESTIC", service="STANDARD",
                rate_card=RATE_CARD, express_enabled=True,
            )

    def test_rejects_non_integer_weight(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=2.5, destination="DOMESTIC", service="STANDARD",
                rate_card=RATE_CARD, express_enabled=True,
            )

    def test_rejects_unknown_destination(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=500, destination="MOON", service="STANDARD",
                rate_card=RATE_CARD, express_enabled=True,
            )

    def test_rejects_unknown_service(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=500, destination="DOMESTIC", service="OVERNIGHT",
                rate_card=RATE_CARD, express_enabled=True,
            )

    def test_rejects_express_when_feature_flag_disabled(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=500, destination="DOMESTIC", service="EXPRESS",
                rate_card=RATE_CARD, express_enabled=False,
            )

    def test_weight_exceeding_maximum_is_rejected(self):
        with self.assertRaises(InvalidQuoteRequest):
            pricing.compute_quote_cents(
                weight_g=10_000_000, destination="DOMESTIC", service="STANDARD",
                rate_card=RATE_CARD, express_enabled=True,
            )


if __name__ == "__main__":
    unittest.main()
