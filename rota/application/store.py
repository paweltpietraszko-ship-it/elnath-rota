"""ROTA-T011-A (A-2): open/create the local SQLite store and migrate it to
the latest schema, so a caller's first action never needs to import
rota.persistence.db directly. Deliberately the one application-layer
function that does not take an already-open conn -- it is conn's producer.
Errors (including UnsupportedSchemaVersion) propagate untranslated, the
same way rota.application.backup.backup_database lets sqlite3.Error
propagate; translating them into an application-layer error type is a
separate product question, out of scope here.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from rota.persistence.db import connect


def open_store(db_path: str | Path) -> sqlite3.Connection:
    return connect(db_path)
