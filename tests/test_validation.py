import unittest

from parcelflow import validation
from parcelflow.models import InvalidBookingRequest, InvalidQuoteRequest


class RequestValidationTests(unittest.TestCase):
    def test_parse_quote_request_accepts_valid_body(self):
        body = b'{"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"}'
        parsed = validation.parse_quote_request(body)
        self.assertEqual(parsed, {"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD"})

    def test_parse_quote_request_rejects_oversized_body(self):
        oversized = b'{"weight_g": 1}' + b" " * validation.MAX_BODY_BYTES
        with self.assertRaises(InvalidQuoteRequest):
            validation.parse_quote_request(oversized)

    def test_parse_quote_request_rejects_invalid_json(self):
        with self.assertRaises(InvalidQuoteRequest):
            validation.parse_quote_request(b"{not json")

    def test_parse_quote_request_rejects_non_object_json(self):
        with self.assertRaises(InvalidQuoteRequest):
            validation.parse_quote_request(b"[1, 2, 3]")

    def test_parse_quote_request_rejects_missing_field(self):
        body = b'{"weight_g": 500, "destination": "DOMESTIC"}'
        with self.assertRaises(InvalidQuoteRequest):
            validation.parse_quote_request(body)

    def test_parse_quote_request_rejects_unknown_field(self):
        body = b'{"weight_g": 500, "destination": "DOMESTIC", "service": "STANDARD", "extra": 1}'
        with self.assertRaises(InvalidQuoteRequest):
            validation.parse_quote_request(body)

    def test_parse_booking_request_accepts_valid_body(self):
        body = b'{"quote_id": "abc-123"}'
        parsed = validation.parse_booking_request(body)
        self.assertEqual(parsed, {"quote_id": "abc-123"})

    def test_parse_booking_request_rejects_missing_quote_id(self):
        with self.assertRaises(InvalidBookingRequest):
            validation.parse_booking_request(b"{}")

    def test_parse_booking_request_rejects_non_string_quote_id(self):
        with self.assertRaises(InvalidBookingRequest):
            validation.parse_booking_request(b'{"quote_id": 123}')


if __name__ == "__main__":
    unittest.main()
