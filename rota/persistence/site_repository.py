"""Site persistence (tasks/ROTA-T008/brief.md MUTABLE CURRENT-STATE ENTITIES).

Current-state entity: save/upsert overwrites, no hidden history. No
physical delete API -- active=false represents disabling.
"""
from __future__ import annotations

import sqlite3

from rota.domain import Site


class SiteNotFound(Exception):
    """Raised when site_id has no matching row."""


class UnknownSiteProfile(Exception):
    """Raised when Site.profile_id does not identify an existing SiteProfile."""


def save_site(conn: sqlite3.Connection, site: Site) -> None:
    row = conn.execute(
        "SELECT 1 FROM site_profiles WHERE profile_id = ?", (site.profile_id,)
    ).fetchone()
    if row is None:
        raise UnknownSiteProfile(site.profile_id)
    with conn:
        conn.execute(
            """INSERT INTO sites (site_id, profile_id, display_name, active)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(site_id) DO UPDATE SET
                profile_id=excluded.profile_id,
                display_name=excluded.display_name,
                active=excluded.active""",
            (site.site_id, site.profile_id, site.display_name, int(site.active)),
        )


def get_site(conn: sqlite3.Connection, site_id: str) -> Site:
    row = conn.execute(
        "SELECT site_id, profile_id, display_name, active FROM sites WHERE site_id = ?", (site_id,)
    ).fetchone()
    if row is None:
        raise SiteNotFound(site_id)
    site_id_, profile_id, display_name, active = row
    return Site(site_id=site_id_, profile_id=profile_id, display_name=display_name, active=bool(active))


def list_sites(conn: sqlite3.Connection) -> list[Site]:
    rows = conn.execute(
        "SELECT site_id, profile_id, display_name, active FROM sites ORDER BY site_id"
    ).fetchall()
    return [
        Site(site_id=site_id, profile_id=profile_id, display_name=display_name, active=bool(active))
        for site_id, profile_id, display_name, active in rows
    ]


if __name__ == "__main__":
    print("persistence.site_repository module OK")
