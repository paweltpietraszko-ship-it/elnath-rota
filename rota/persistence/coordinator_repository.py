"""Coordinator + CoordinatorSiteAssociation persistence
(tasks/ROTA-T008/brief.md MUTABLE CURRENT-STATE ENTITIES).
"""
from __future__ import annotations

import sqlite3

from rota.domain import Coordinator, CoordinatorSiteAssociation


class CoordinatorNotFound(Exception):
    """Raised when coordinator_id has no matching row."""


class UnknownCoordinatorOrSite(Exception):
    """Raised when an association references a missing Coordinator or Site."""


def write_coordinator_in_open_transaction(conn: sqlite3.Connection, coordinator: Coordinator) -> None:
    """Same write as save_coordinator, without its own `with conn:` -- for a
    caller that must combine this write with others in a single already-open
    transaction (see rota/application/bootstrap.py)."""
    conn.execute(
        """INSERT INTO coordinators (coordinator_id, display_name, active)
           VALUES (?, ?, ?)
           ON CONFLICT(coordinator_id) DO UPDATE SET
            display_name=excluded.display_name, active=excluded.active""",
        (coordinator.coordinator_id, coordinator.display_name, int(coordinator.active)),
    )


def save_coordinator(conn: sqlite3.Connection, coordinator: Coordinator) -> None:
    with conn:
        write_coordinator_in_open_transaction(conn, coordinator)


def get_coordinator(conn: sqlite3.Connection, coordinator_id: str) -> Coordinator:
    row = conn.execute(
        "SELECT coordinator_id, display_name, active FROM coordinators WHERE coordinator_id = ?",
        (coordinator_id,),
    ).fetchone()
    if row is None:
        raise CoordinatorNotFound(coordinator_id)
    coordinator_id_, display_name, active = row
    return Coordinator(coordinator_id=coordinator_id_, display_name=display_name, active=bool(active))


def list_coordinators(conn: sqlite3.Connection) -> list[Coordinator]:
    rows = conn.execute(
        "SELECT coordinator_id, display_name, active FROM coordinators ORDER BY coordinator_id"
    ).fetchall()
    return [
        Coordinator(coordinator_id=cid, display_name=name, active=bool(active))
        for cid, name, active in rows
    ]


def write_coordinator_site_association_in_open_transaction(
    conn: sqlite3.Connection, association: CoordinatorSiteAssociation
) -> None:
    """Same write as save_coordinator_site_association, without its own
    `with conn:` (see write_coordinator_in_open_transaction)."""
    coordinator_row = conn.execute(
        "SELECT 1 FROM coordinators WHERE coordinator_id = ?", (association.coordinator_id,)
    ).fetchone()
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (association.site_id,)).fetchone()
    if coordinator_row is None or site_row is None:
        raise UnknownCoordinatorOrSite((association.coordinator_id, association.site_id))
    conn.execute(
        """INSERT INTO coordinator_site_associations (coordinator_id, site_id, active)
           VALUES (?, ?, ?)
           ON CONFLICT(coordinator_id, site_id) DO UPDATE SET active=excluded.active""",
        (association.coordinator_id, association.site_id, int(association.active)),
    )


def save_coordinator_site_association(conn: sqlite3.Connection, association: CoordinatorSiteAssociation) -> None:
    with conn:
        write_coordinator_site_association_in_open_transaction(conn, association)


def activate_association_if_not_already_active_in_open_transaction(
    conn: sqlite3.Connection, association: CoordinatorSiteAssociation
) -> bool:
    """ROTA-T010-A / R3-2: atomic compare-and-swap for
    bootstrap_or_resume_coordinator_context's real concurrency guard --
    unlike write_coordinator_site_association_in_open_transaction's plain
    upsert, this single statement only writes when the existing row (if
    any) is NOT already active=1, and reports via the return value whether
    IT was the write that won. A pre-check-then-write pattern across two
    separate statements cannot be race-safe against another connection
    writing in between; SQLite serializes concurrent writers of the same
    row at this one UPSERT...WHERE statement instead. Returns False (does
    not raise) when it lost the race -- the caller decides what that means."""
    coordinator_row = conn.execute(
        "SELECT 1 FROM coordinators WHERE coordinator_id = ?", (association.coordinator_id,)
    ).fetchone()
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (association.site_id,)).fetchone()
    if coordinator_row is None or site_row is None:
        raise UnknownCoordinatorOrSite((association.coordinator_id, association.site_id))
    cursor = conn.execute(
        """INSERT INTO coordinator_site_associations (coordinator_id, site_id, active)
           VALUES (?, ?, ?)
           ON CONFLICT(coordinator_id, site_id) DO UPDATE SET active=excluded.active
           WHERE coordinator_site_associations.active = 0""",
        (association.coordinator_id, association.site_id, int(association.active)),
    )
    return cursor.rowcount > 0


def list_associations_for_coordinator(conn: sqlite3.Connection, coordinator_id: str) -> list[CoordinatorSiteAssociation]:
    rows = conn.execute(
        "SELECT coordinator_id, site_id, active FROM coordinator_site_associations "
        "WHERE coordinator_id = ? ORDER BY site_id",
        (coordinator_id,),
    ).fetchall()
    return [CoordinatorSiteAssociation(c, s, bool(a)) for c, s, a in rows]


def list_associations_for_site(conn: sqlite3.Connection, site_id: str) -> list[CoordinatorSiteAssociation]:
    rows = conn.execute(
        "SELECT coordinator_id, site_id, active FROM coordinator_site_associations "
        "WHERE site_id = ? ORDER BY coordinator_id",
        (site_id,),
    ).fetchall()
    return [CoordinatorSiteAssociation(c, s, bool(a)) for c, s, a in rows]


if __name__ == "__main__":
    print("persistence.coordinator_repository module OK")
