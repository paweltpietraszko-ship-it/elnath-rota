"""SiteProfile persistence (tasks/ROTA-T004/brief.md).

Persists exactly the existing SiteProfile/StandardShift fields (DOMAIN
BOUNDARY) -- no new product fields, no SiteProfileVersion/history (NO
SITEPROFILE VERSIONING). A save replaces the current row and its whole
standard_shifts list atomically (STORAGE MODEL / TRANSACTION RULE); there is
no UPDATE-in-place SQL, since the whole profile+shifts set is small and
always rewritten together as one fact.
"""
from __future__ import annotations

import sqlite3
from datetime import time

from rota.domain import ShiftCatalogKind, ShiftKind, SiteProfile, StandardShift


class SiteProfileNotFound(Exception):
    """Raised when profile_id has no row in site_profiles."""


def _standard_shifts_has_t012_columns(conn: sqlite3.Connection) -> bool:
    """R3-5-style legacy migration tests (tests/test_local_store_schema_migration.py)
    write through this repository against a connection deliberately held at
    an old PRAGMA user_version (pre-migration-5), before ever calling
    connect()/migrate(). Detecting the real column set -- instead of
    assuming the latest schema -- keeps that established testing technique
    working without weakening it: this repository writes whatever the
    connection's actual schema supports, and a later connect() migration
    fills the T012 columns in as NULL/legacy-default on ALTER TABLE, same as
    any other pre-T012 row."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(standard_shifts)").fetchall()}
    return "catalog_kind" in columns


def _write_site_profile_header(conn: sqlite3.Connection, profile: SiteProfile) -> None:
    conn.execute(
        """INSERT INTO site_profiles
           (profile_id, display_name, active, day_only_blocks_n,
            external_support_enabled, training_s_enabled,
            training_s_weekdays_only, training_s_default_readiness_threshold,
            rolling_7d_decision_threshold_hours)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(profile_id) DO UPDATE SET
            display_name=excluded.display_name,
            active=excluded.active,
            day_only_blocks_n=excluded.day_only_blocks_n,
            external_support_enabled=excluded.external_support_enabled,
            training_s_enabled=excluded.training_s_enabled,
            training_s_weekdays_only=excluded.training_s_weekdays_only,
            training_s_default_readiness_threshold=excluded.training_s_default_readiness_threshold,
            rolling_7d_decision_threshold_hours=excluded.rolling_7d_decision_threshold_hours""",
        (
            profile.profile_id,
            profile.display_name,
            int(profile.active),
            int(profile.day_only_blocks_n),
            int(profile.external_support_enabled),
            int(profile.training_s_enabled),
            int(profile.training_s_weekdays_only),
            profile.training_s_default_readiness_threshold,
            profile.rolling_7d_decision_threshold_hours,
        ),
    )


def _write_standard_shift(conn: sqlite3.Connection, profile_id: str, seq: int, shift: StandardShift, has_t012_columns: bool) -> None:
    # T012 shape validation intentionally does NOT run here -- persistence
    # stays permissive (module docstring: exactly the existing fields, no
    # new domain rules), matching the pre-T012 precedent that
    # bootstrap._is_valid_standard_shift, not save, is what flags an
    # unusable shift. rota.planning.shift_catalog.generate_catalog_demands
    # validates at actual catalog-generation (PLAN) time instead.
    if not has_t012_columns:
        conn.execute(
            """INSERT INTO standard_shifts
               (profile_id, seq, kind, start_time, end_time, end_next_day, required_primary_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id, seq, shift.kind.value, shift.start_time.isoformat(),
                shift.end_time.isoformat(), int(shift.end_next_day), shift.required_primary_count,
            ),
        )
        return
    conn.execute(
        """INSERT INTO standard_shifts
           (profile_id, seq, kind, start_time, end_time, end_next_day, required_primary_count,
            catalog_kind, required_rest_hours, active_weekdays)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            profile_id,
            seq,
            shift.kind.value,
            shift.start_time.isoformat(),
            shift.end_time.isoformat(),
            int(shift.end_next_day),
            shift.required_primary_count,
            shift.catalog_kind.value if shift.catalog_kind else None,
            shift.required_rest_hours,
            ",".join(str(w) for w in shift.active_weekdays),
        ),
    )


def write_site_profile_in_open_transaction(conn: sqlite3.Connection, profile: SiteProfile) -> None:
    """Same write as save_site_profile, without its own `with conn:` (see
    rota.persistence.coordinator_repository.write_coordinator_in_open_transaction)."""
    _write_site_profile_header(conn, profile)
    conn.execute("DELETE FROM standard_shifts WHERE profile_id = ?", (profile.profile_id,))
    has_t012_columns = _standard_shifts_has_t012_columns(conn)
    for seq, shift in enumerate(profile.standard_shifts):
        _write_standard_shift(conn, profile.profile_id, seq, shift, has_t012_columns)


def save_site_profile(conn: sqlite3.Connection, profile: SiteProfile) -> None:
    with conn:
        write_site_profile_in_open_transaction(conn, profile)


def _row_to_shift(row: tuple) -> StandardShift:
    (kind, start_time, end_time, end_next_day, required_primary_count,
     catalog_kind, required_rest_hours, active_weekdays) = row
    return StandardShift(
        kind=ShiftKind(kind),
        start_time=time.fromisoformat(start_time),
        end_time=time.fromisoformat(end_time),
        end_next_day=bool(end_next_day),
        required_primary_count=required_primary_count,
        # Legacy (pre-T012) rows have NULL here: catalog_kind stays None
        # (normalized on demand by rota.planning.shift_catalog), rest
        # defaults to the legacy REST_MIN_HOURS compatibility value, and
        # weekdays default to every day.
        catalog_kind=ShiftCatalogKind(catalog_kind) if catalog_kind else None,
        required_rest_hours=required_rest_hours if required_rest_hours is not None else 11,
        active_weekdays=tuple(int(w) for w in active_weekdays.split(",")) if active_weekdays else (1, 2, 3, 4, 5, 6, 7),
    )


def _fetch_standard_shifts(conn: sqlite3.Connection, profile_id: str) -> list[StandardShift]:
    rows = conn.execute(
        """SELECT kind, start_time, end_time, end_next_day, required_primary_count,
                  catalog_kind, required_rest_hours, active_weekdays
           FROM standard_shifts WHERE profile_id = ? ORDER BY seq""",
        (profile_id,),
    ).fetchall()
    return [_row_to_shift(row) for row in rows]


def get_site_profile(conn: sqlite3.Connection, profile_id: str) -> SiteProfile:
    row = conn.execute(
        """SELECT profile_id, display_name, active, day_only_blocks_n,
                  external_support_enabled, training_s_enabled,
                  training_s_weekdays_only, training_s_default_readiness_threshold,
                  rolling_7d_decision_threshold_hours
           FROM site_profiles WHERE profile_id = ?""",
        (profile_id,),
    ).fetchone()
    if row is None:
        raise SiteProfileNotFound(profile_id)
    (
        profile_id_, display_name, active, day_only_blocks_n, external_support_enabled,
        training_s_enabled, training_s_weekdays_only,
        training_s_default_readiness_threshold, rolling_7d_decision_threshold_hours,
    ) = row

    return SiteProfile(
        profile_id=profile_id_,
        display_name=display_name,
        active=bool(active),
        standard_shifts=_fetch_standard_shifts(conn, profile_id),
        day_only_blocks_n=bool(day_only_blocks_n),
        external_support_enabled=bool(external_support_enabled),
        training_s_enabled=bool(training_s_enabled),
        training_s_weekdays_only=bool(training_s_weekdays_only),
        training_s_default_readiness_threshold=training_s_default_readiness_threshold,
        rolling_7d_decision_threshold_hours=rolling_7d_decision_threshold_hours,
    )


def list_site_profile_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT profile_id FROM site_profiles ORDER BY profile_id").fetchall()
    return [row[0] for row in rows]


if __name__ == "__main__":
    print("persistence.site_profile_repository module OK")
