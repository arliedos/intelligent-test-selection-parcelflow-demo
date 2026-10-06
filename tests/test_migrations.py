"""Real SQLite migration/rollback tests (migration 002: bookings.service_level)."""
import os
import tempfile
import unittest

from parcelflow import db, migrations


class Migration002Tests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = db.connect(self.db_path)
        db.init_schema(self.conn)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.conn.close()
        os.remove(self.db_path)

    def _columns(self):
        return {row[1] for row in self.conn.execute("PRAGMA table_info(bookings)")}

    def test_apply_adds_service_level_column_with_default(self):
        quote_id = db.insert_quote(self.conn, weight_g=100, destination="DOMESTIC", service="STANDARD", amount_cents=600)
        booking_id = db.insert_booking(self.conn, quote_id=quote_id, status="PENDING", attempts=0)

        self.assertNotIn("service_level", self._columns())
        migrations.apply_migration_002(self.conn)
        self.assertIn("service_level", self._columns())

        row = db.get_booking(self.conn, booking_id)
        self.assertEqual(row["service_level"], "STANDARD")

    def test_rollback_removes_service_level_column_and_preserves_other_data(self):
        quote_id = db.insert_quote(self.conn, weight_g=250, destination="REGIONAL", service="EXPRESS", amount_cents=1800)
        booking_id = db.insert_booking(self.conn, quote_id=quote_id, status="CONFIRMED", attempts=1)

        migrations.apply_migration_002(self.conn)
        migrations.rollback_migration_002(self.conn)

        self.assertNotIn("service_level", self._columns())
        row = db.get_booking(self.conn, booking_id)
        self.assertEqual(row["status"], "CONFIRMED")
        self.assertEqual(row["attempts"], 1)
        self.assertEqual(row["quote_id"], quote_id)

    def test_apply_is_idempotent(self):
        migrations.apply_migration_002(self.conn)
        migrations.apply_migration_002(self.conn)
        self.assertIn("service_level", self._columns())


if __name__ == "__main__":
    unittest.main()
