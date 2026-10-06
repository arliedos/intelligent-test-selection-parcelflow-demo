"""SQLite persistence for quotes and bookings."""
from __future__ import annotations

import sqlite3
import uuid

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    weight_g INTEGER NOT NULL,
    destination TEXT NOT NULL,
    service TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES quotes(quote_id),
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    carrier_reference TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""


def connect(path: str) -> sqlite3.Connection:
    # check_same_thread=False: the demo HTTP server handles each request on a
    # worker thread: callers are responsible for serializing access (see
    # app.py's connection lock).
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def insert_quote(conn, *, weight_g: int, destination: str, service: str, amount_cents: int) -> str:
    quote_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO quotes (quote_id, weight_g, destination, service, amount_cents) VALUES (?, ?, ?, ?, ?)",
        (quote_id, weight_g, destination, service, amount_cents),
    )
    conn.commit()
    return quote_id


def get_quote(conn, quote_id: str):
    row = conn.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,)).fetchone()
    return row


def insert_booking(conn, *, quote_id: str, status: str, attempts: int = 0) -> str:
    booking_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO bookings (booking_id, quote_id, status, attempts) VALUES (?, ?, ?, ?)",
        (booking_id, quote_id, status, attempts),
    )
    conn.commit()
    return booking_id


def get_booking(conn, booking_id: str):
    row = conn.execute("SELECT * FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
    return row


def update_booking_status(conn, booking_id: str, *, status: str, attempts: int, carrier_reference: str | None) -> None:
    conn.execute(
        "UPDATE bookings SET status = ?, attempts = ?, carrier_reference = ? WHERE booking_id = ?",
        (status, attempts, carrier_reference, booking_id),
    )
    conn.commit()
