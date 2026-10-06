"""Runnable entrypoint for local/demo use: `python -m parcelflow`.

Reads PARCELFLOW_ENVIRONMENT (default ST) and starts the loopback-bound
HTTP server with that environment's config and the current rate card.
"""
from __future__ import annotations

import json
import os

from parcelflow import db
from parcelflow.app import create_server
from parcelflow.config import default_config_dir, load_environment


def main() -> None:
    environment = os.environ.get("PARCELFLOW_ENVIRONMENT", "ST")
    cfg = load_environment(environment, config_dir=default_config_dir())

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(os.path.join(repo_root, "reference-data", "rate_card.json"), "r", encoding="utf-8") as fh:
        rate_card = json.load(fh)

    db_path = os.environ.get("PARCELFLOW_DB_PATH", os.path.join(repo_root, "parcelflow.db"))
    conn = db.connect(db_path)
    db.init_schema(conn)

    ui_dir = os.path.join(repo_root, "ui")
    server = create_server(cfg, rate_card, conn, host="127.0.0.1", port=cfg.api_port, ui_dir=ui_dir)
    print(f"ParcelFlow demo listening on http://127.0.0.1:{cfg.api_port} ({environment})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        conn.close()


if __name__ == "__main__":
    main()
