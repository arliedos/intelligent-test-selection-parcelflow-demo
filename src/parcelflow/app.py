"""ParcelFlow demo HTTP application (stdlib http.server only).

Binds to loopback by default. Not a production server (no TLS, no auth
beyond the explicit demo role header). Intended for local/CI test runs only.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from parcelflow import auth, db, pricing, validation
from parcelflow.config import ParcelFlowConfig
from parcelflow.gateway import GatewaySimulator
from parcelflow.models import (
    AuthorizationError,
    GatewayUnavailableError,
    InvalidBookingRequest,
    InvalidQuoteRequest,
)

logger = logging.getLogger("parcelflow.app")

DEFAULT_ROLE_HEADER = "X-Demo-Role"
SIMULATE_OUTCOMES_HEADER = "X-Simulate-Gateway-Outcomes"

DISPATCH_STATUS_BY_BOOKING_STATUS = {
    "PENDING": "AWAITING_DISPATCH",
    "CONFIRMED": "DISPATCHED",
    "CONFIRMED_FALLBACK": "DISPATCHED",
    "FAILED": "DISPATCH_FAILED",
}

_STATIC_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


def _error_body(message: str) -> bytes:
    return json.dumps({"error": message}).encode("utf-8")


def make_handler(cfg: ParcelFlowConfig, rate_card: dict, conn, ui_dir: str | None = None):
    db_lock = threading.Lock()
    static_root = os.path.realpath(ui_dir) if ui_dir else None

    class Handler(BaseHTTPRequestHandler):
        server_version = "ParcelFlowDemo/1.0"

        def log_message(self, fmt, *args):  # quiet, no secret-bearing data ever logged
            logger.info("%s - %s", self.address_string(), fmt % args)

        def _send_json(self, status: int, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error_json(self, status: int, message: str):
            body = _error_body(message)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_body(self) -> bytes:
            raw_length = self.headers.get("Content-Length", "0") or "0"
            try:
                length = int(raw_length)
            except ValueError:
                raise InvalidQuoteRequest("Content-Length header must be numeric")
            if length > validation.MAX_BODY_BYTES:
                raise InvalidQuoteRequest("request body exceeds maximum size")
            return self.rfile.read(length) if length else b""

        def do_GET(self):
            try:
                if self.path == "/health":
                    self._send_json(200, {"status": "ok", "environment": cfg.environment})
                    return
                if self.path.startswith("/api/bookings/") and self.path.endswith("/dispatch-status"):
                    self._handle_dispatch_status()
                    return
                if self.path.startswith("/api/bookings/"):
                    self._handle_get_booking()
                    return
                if static_root and self._serve_static():
                    return
                self._send_error_json(404, "not found")
            except (InvalidQuoteRequest, InvalidBookingRequest) as exc:
                self._send_error_json(400, str(exc))
            except AuthorizationError as exc:
                self._send_error_json(403, str(exc))
            except Exception:  # pragma: no cover - defensive, never leak internals
                logger.exception("unhandled error handling request")
                self._send_error_json(500, "internal error")

        def _handle_get_booking(self):
            role = self.headers.get(DEFAULT_ROLE_HEADER)
            auth.require_role(role, allowed_roles=cfg.booking_allowed_roles)
            booking_id = self.path.rsplit("/", 1)[-1]
            with db_lock:
                row = db.get_booking(conn, booking_id)
            if row is None:
                self._send_error_json(404, "booking not found")
                return
            self._send_json(200, dict(row))

        def _handle_dispatch_status(self):
            role = self.headers.get(DEFAULT_ROLE_HEADER)
            auth.require_role(role, allowed_roles=cfg.dispatch_allowed_roles)
            booking_id = self.path[len("/api/bookings/"):-len("/dispatch-status")]
            with db_lock:
                row = db.get_booking(conn, booking_id)
            if row is None:
                self._send_error_json(404, "booking not found")
                return
            self._send_json(
                200,
                {
                    "booking_id": booking_id,
                    "dispatch_status": DISPATCH_STATUS_BY_BOOKING_STATUS.get(row["status"], "UNKNOWN"),
                },
            )

        def _serve_static(self) -> bool:
            request_path = "/index.html" if self.path == "/" else self.path
            if not request_path.startswith("/ui/") and request_path != "/index.html":
                return False
            relative = request_path[len("/ui/"):] if request_path.startswith("/ui/") else request_path.lstrip("/")
            candidate = os.path.realpath(os.path.join(static_root, relative))
            if os.path.commonpath([candidate, static_root]) != static_root or not os.path.isfile(candidate):
                return False
            ext = os.path.splitext(candidate)[1]
            content_type = _STATIC_CONTENT_TYPES.get(ext, "application/octet-stream")
            with open(candidate, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True

        def do_POST(self):
            try:
                if self.path == "/api/quotes":
                    self._handle_quote()
                elif self.path == "/api/bookings":
                    self._handle_booking()
                else:
                    self._send_error_json(404, "not found")
            except (InvalidQuoteRequest, InvalidBookingRequest) as exc:
                self._send_error_json(400, str(exc))
            except AuthorizationError as exc:
                self._send_error_json(403, str(exc))
            except GatewayUnavailableError as exc:
                self._send_error_json(502, str(exc))
            except Exception:  # pragma: no cover - defensive, never leak internals
                logger.exception("unhandled error handling request")
                self._send_error_json(500, "internal error")

        def _handle_quote(self):
            role = self.headers.get(DEFAULT_ROLE_HEADER)
            auth.require_role(role, allowed_roles=cfg.quote_allowed_roles)
            body = self._read_body()
            parsed = validation.parse_quote_request(body)
            amount_cents = pricing.compute_quote_cents(
                weight_g=parsed["weight_g"],
                destination=parsed["destination"],
                service=parsed["service"],
                rate_card=rate_card,
                express_enabled=cfg.express_service_enabled,
            )
            with db_lock:
                quote_id = db.insert_quote(
                    conn,
                    weight_g=parsed["weight_g"],
                    destination=parsed["destination"],
                    service=parsed["service"],
                    amount_cents=amount_cents,
                )
            self._send_json(
                201,
                {
                    "quote_id": quote_id,
                    "amount_cents": amount_cents,
                    "currency": "USD",
                    "destination": parsed["destination"],
                    "service": parsed["service"],
                    "weight_g": parsed["weight_g"],
                },
            )

        def _handle_booking(self):
            role = self.headers.get(DEFAULT_ROLE_HEADER)
            auth.require_role(role, allowed_roles=cfg.booking_allowed_roles)
            body = self._read_body()
            parsed = validation.parse_booking_request(body)
            with db_lock:
                quote_row = db.get_quote(conn, parsed["quote_id"])
            if quote_row is None:
                self._send_error_json(404, "quote not found")
                return

            with db_lock:
                booking_id = db.insert_booking(conn, quote_id=parsed["quote_id"], status="PENDING", attempts=0)

            outcomes = self._resolve_outcomes()
            simulator = GatewaySimulator(
                retry_count=cfg.gateway_retry_count,
                fallback_enabled=cfg.gateway_fallback_enabled,
                outcomes=outcomes,
            )
            try:
                result = simulator.confirm_booking(booking_id=booking_id)
            except GatewayUnavailableError:
                with db_lock:
                    db.update_booking_status(conn, booking_id, status="FAILED", attempts=cfg.gateway_retry_count + 1, carrier_reference=None)
                raise

            status = "CONFIRMED_FALLBACK" if result.used_fallback else "CONFIRMED"
            with db_lock:
                db.update_booking_status(
                    conn, booking_id, status=status, attempts=result.attempts, carrier_reference=result.carrier_reference,
                )
            self._send_json(
                201,
                {
                    "booking_id": booking_id,
                    "quote_id": parsed["quote_id"],
                    "status": status,
                    "attempts": result.attempts,
                    "carrier_reference": result.carrier_reference,
                },
            )

        def _resolve_outcomes(self):
            max_attempts = cfg.gateway_retry_count + 1
            if cfg.gateway_simulation_enabled:
                header_value = self.headers.get(SIMULATE_OUTCOMES_HEADER)
                if header_value:
                    return [v.strip() for v in header_value.split(",") if v.strip()]
            return ["success"] * max_attempts

    return Handler


def create_server(
    cfg: ParcelFlowConfig, rate_card: dict, conn, host: str = "127.0.0.1", port: int = 0, ui_dir: str | None = None,
) -> ThreadingHTTPServer:
    handler_cls = make_handler(cfg, rate_card, conn, ui_dir=ui_dir)
    server = ThreadingHTTPServer((host, port), handler_cls)
    return server
