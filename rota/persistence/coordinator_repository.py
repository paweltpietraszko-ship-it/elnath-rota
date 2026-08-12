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


def save_coordinator(conn: sqlite3.Connection, coordinator: Coordinator) -> None:
    with conn:
        conn.execute(
            """INSERT INTO coordinators (coordinator_id, display_name, active)
               VALUES (?, ?, ?)
               ON CONFLICT(coordinator_id) DO UPDATE SET
                display_name=excluded.display_name, active=excluded.active""",
            (coordinator.coordinator_id, coordinator.display_name, int(coordinator.active)),
        )


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


def save_coordinator_site_association(conn: sqlite3.Connection, association: CoordinatorSiteAssociation) -> None:
    coordinator_row = conn.execute(
        "SELECT 1 FROM coordinators WHERE coordinator_id = ?", (association.coordinator_id,)
    ).fetchone()
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (association.site_id,)).fetchone()
    if coordinator_row is None or site_row is None:
        raise UnknownCoordinatorOrSite((association.coordinator_id, association.site_id))
    with conn:
        conn.execute(
            """INSERT INTO coordinator_site_associations (coordinator_id, site_id, active)
               VALUES (?, ?, ?)
               ON CONFLICT(coordinator_id, site_id) DO UPDATE SET active=excluded.active""",
            (association.coordinator_id, association.site_id, int(association.active)),
        )


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
