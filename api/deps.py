"""Connection-per-request lifecycle. Opening/closing is the API layer's
own concern (brief.md section 3.2) -- never exposed to the frontend.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from rota.persistence.db import connect

from api.config import DB_PATH


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
