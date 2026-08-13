"""Coordinator context integrity (tasks/ROTA-T009/brief.md COORDINATOR
CONTEXT): basic active-triple check, not a new authorization subsystem.

R4-11-B: DEPENDENCY BOUNDARY says application contains no SQL/table names --
uses only existing repository functions, never raw DB calls directly.
"""
from __future__ import annotations

import sqlite3

from rota.application.errors import InvalidCoordinatorContext
from rota.persistence.coordinator_repository import (
    CoordinatorNotFound,
    get_coordinator,
    list_associations_for_coordinator,
)
from rota.persistence.site_repository import SiteNotFound, get_site


def require_active_coordinator_context(conn: sqlite3.Connection, *, coordinator_id: str, site_id: str) -> None:
    try:
        coordinator = get_coordinator(conn, coordinator_id)
    except CoordinatorNotFound as exc:
        raise InvalidCoordinatorContext(f"coordinator {coordinator_id!r} is not active") from exc
    if not coordinator.active:
        raise InvalidCoordinatorContext(f"coordinator {coordinator_id!r} is not active")

    try:
        site = get_site(conn, site_id)
    except SiteNotFound as exc:
        raise InvalidCoordinatorContext(f"site {site_id!r} is not active") from exc
    if not site.active:
        raise InvalidCoordinatorContext(f"site {site_id!r} is not active")

    associations = list_associations_for_coordinator(conn, coordinator_id)
    match = next((a for a in associations if a.site_id == site_id), None)
    if match is None or not match.active:
        raise InvalidCoordinatorContext(
            f"coordinator {coordinator_id!r} has no active CoordinatorSiteAssociation for site {site_id!r}"
        )
