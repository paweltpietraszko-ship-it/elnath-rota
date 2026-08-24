"""Operation 12 (tasks/ROTA-T009/brief.md): backup and diagnostic ZIP.
Both stay behind the application boundary so a future UI never implements
storage/privacy logic itself. No cloud behavior, no telemetry/upload.

R4-11-B: actual SQL/table access lives in
rota.persistence.backup_repository -- this module is a thin wrapper only.
"""
from __future__ import annotations

import json
import sqlite3
import zipfile

from rota.persistence.backup_repository import backup_to, diagnostics_payload


def backup_database(conn: sqlite3.Connection, destination: str) -> None:
    backup_to(conn, destination)


def build_diagnostic_zip(
    conn: sqlite3.Connection,
    destination: str,
    *,
    frontend_report: dict | None = None,
) -> None:
    payload = diagnostics_payload(conn)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(payload, indent=2))
        if frontend_report is not None:
            archive.writestr("frontend_diagnostics.json", json.dumps(frontend_report, indent=2))
