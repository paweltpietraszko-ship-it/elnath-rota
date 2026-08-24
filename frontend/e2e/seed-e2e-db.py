"""ROTA-T021c e2e fixture: seeds the one coordinator row that
api/routers/bootstrap.py's create_site assumes already exists (Paweł's
real rota_dev.db has this from an earlier one-off bootstrap; a brand
new e2e-only db file does not). Not a T021c product change -- this
never touches rota_dev.db, only the dedicated e2e SQLite file.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from rota.domain import Coordinator
from rota.persistence.coordinator_repository import get_coordinator, save_coordinator
from rota.persistence.db import connect


def main() -> None:
    db_path = sys.argv[1]
    coordinator_id = sys.argv[2]
    conn = connect(db_path)
    try:
        try:
            get_coordinator(conn, coordinator_id)
            return  # already seeded
        except Exception:
            pass
        save_coordinator(conn, Coordinator(coordinator_id=coordinator_id, display_name="E2E Coordinator", active=True))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
