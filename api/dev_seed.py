"""ROTA-T021 brief.md section 4 Writes: "the dev-config coordinator is
created once as a separate, one-time dev-setup step (outside this
per-Site-creation call, not part of Screen 1)". This is that step.

Run once against a fresh dev database: `python -m api.dev_seed`
"""
from __future__ import annotations

from rota.domain import Coordinator
from rota.persistence.coordinator_repository import CoordinatorNotFound, get_coordinator, save_coordinator
from rota.persistence.db import connect

from api.config import DB_PATH, DEV_COORDINATOR_ID


def seed(db_path: str = DB_PATH) -> None:
    conn = connect(db_path)
    try:
        try:
            get_coordinator(conn, DEV_COORDINATOR_ID)
            print(f"dev coordinator {DEV_COORDINATOR_ID!r} already exists")
            return
        except CoordinatorNotFound:
            pass
        save_coordinator(conn, Coordinator(DEV_COORDINATOR_ID, "Dev Coordinator", True))
        print(f"dev coordinator {DEV_COORDINATOR_ID!r} created")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
