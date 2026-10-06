import os
import tempfile
import unittest

from parcelflow import db


class DbTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = db.connect(self.path)
        db.init_schema(self.conn)
        self.addCleanup(lambda: os.remove(self.path))
        self.addCleanup(self.conn.close)

    def test_insert_and_get_quote_roundtrip(self):
        quote_id = db.insert_quote(
            self.conn, weight_g=500, destination="DOMESTIC", service="STANDARD", amount_cents=1000,
        )
        row = db.get_quote(self.conn, quote_id)
        self.assertEqual(row["weight_g"], 500)
        self.assertEqual(row["amount_cents"], 1000)
        self.assertEqual(row["destination"], "DOMESTIC")

    def test_get_quote_missing_returns_none(self):
        self.assertIsNone(db.get_quote(self.conn, "does-not-exist"))

    def test_insert_and_get_booking_roundtrip(self):
        quote_id = db.insert_quote(
            self.conn, weight_g=500, destination="DOMESTIC", service="STANDARD", amount_cents=1000,
        )
        booking_id = db.insert_booking(self.conn, quote_id=quote_id, status="PENDING", attempts=0)
        row = db.get_booking(self.conn, booking_id)
        self.assertEqual(row["quote_id"], quote_id)
        self.assertEqual(row["status"], "PENDING")

    def test_update_booking_status(self):
        quote_id = db.insert_quote(
            self.conn, weight_g=500, destination="DOMESTIC", service="STANDARD", amount_cents=1000,
        )
        booking_id = db.insert_booking(self.conn, quote_id=quote_id, status="PENDING", attempts=0)
        db.update_booking_status(
            self.conn, booking_id, status="CONFIRMED", attempts=2, carrier_reference="CARR-x",
        )
        row = db.get_booking(self.conn, booking_id)
        self.assertEqual(row["status"], "CONFIRMED")
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["carrier_reference"], "CARR-x")


if __name__ == "__main__":
    unittest.main()
