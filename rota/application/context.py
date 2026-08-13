"""Coordinator context integrity (tasks/ROTA-T009/brief.md COORDINATOR
CONTEXT): basic active-triple check, not a new authorization subsystem.
"""
from __future__ import annotations

import sqlite3

from rota.application.errors import InvalidCoordinatorContext


def require_active_coordinator_context(conn: sqlite3.Connection, *, coordinator_id: str, site_id: str) -> None:
    coordinator_row = conn.execute(
        "SELECT active FROM coordinators WHERE coordinator_id = ?", (coordinator_id,)
    ).fetchone()
    if coordinator_row is None or not coordinator_row[0]:
        raise InvalidCoordinatorContext(f"coordinator {coordinator_id!r} is not active")

    site_row = conn.execute("SELECT active FROM sites WHERE site_id = ?", (site_id,)).fetchone()
    if site_row is None or not site_row[0]:
        raise InvalidCoordinatorContext(f"site {site_id!r} is not active")

    association_row = conn.execute(
        "SELECT active FROM coordinator_site_associations WHERE coordinator_id = ? AND site_id = ?",
        (coordinator_id, site_id),
    ).fetchone()
    if association_row is None or not association_row[0]:
        raise InvalidCoordinatorContext(
            f"coordinator {coordinator_id!r} has no active CoordinatorSiteAssociation for site {site_id!r}"
        )
