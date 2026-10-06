"""Versioned SQLite migrations for the bookings table.

SQLite's ALTER TABLE cannot conditionally add a column, so apply/rollback
here use PRAGMA table_info to make both operations idempotent and safe to
re-run.
"""
from __future__ import annotations

import sqlite3

DEFAULT_SERVICE_LEVEL = "STANDARD"


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row[1] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def apply_migration_002(conn: sqlite3.Connection) -> None:
    """Add bookings.service_level, backfilled from the default service level."""
    if _has_column(conn, "bookings", "service_level"):
        return
    conn.execute(
        f"ALTER TABLE bookings ADD COLUMN service_level TEXT NOT NULL DEFAULT '{DEFAULT_SERVICE_LEVEL}'"
    )
    conn.commit()


def rollback_migration_002(conn: sqlite3.Connection) -> None:
    """Remove bookings.service_level by rebuilding the table without it."""
    if not _has_column(conn, "bookings", "service_level"):
        return
    conn.executescript(
        """
        CREATE TABLE bookings_rollback_tmp (
            booking_id TEXT PRIMARY KEY,
            quote_id TEXT NOT NULL REFERENCES quotes(quote_id),
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            carrier_reference TEXT,
            created_at TEXT NOT NULL
        );
        INSERT INTO bookings_rollback_tmp
            (booking_id, quote_id, status, attempts, carrier_reference, created_at)
            SELECT booking_id, quote_id, status, attempts, carrier_reference, created_at FROM bookings;
        DROP TABLE bookings;
        ALTER TABLE bookings_rollback_tmp RENAME TO bookings;
        """
    )
    conn.commit()
