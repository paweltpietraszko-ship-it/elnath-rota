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

from rota.domain import ShiftKind, SiteProfile, StandardShift


class SiteProfileNotFound(Exception):
    """Raised when profile_id has no row in site_profiles."""


def save_site_profile(conn: sqlite3.Connection, profile: SiteProfile) -> None:
    with conn:
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
        conn.execute("DELETE FROM standard_shifts WHERE profile_id = ?", (profile.profile_id,))
        for seq, shift in enumerate(profile.standard_shifts):
            conn.execute(
                """INSERT INTO standard_shifts
                   (profile_id, seq, kind, start_time, end_time, end_next_day, required_primary_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile.profile_id,
                    seq,
                    shift.kind.value,
                    shift.start_time.isoformat(),
                    shift.end_time.isoformat(),
                    int(shift.end_next_day),
                    shift.required_primary_count,
                ),
            )


def _row_to_shift(row: tuple) -> StandardShift:
    kind, start_time, end_time, end_next_day, required_primary_count = row
    return StandardShift(
        kind=ShiftKind(kind),
        start_time=time.fromisoformat(start_time),
        end_time=time.fromisoformat(end_time),
        end_next_day=bool(end_next_day),
        required_primary_count=required_primary_count,
    )


def _fetch_standard_shifts(conn: sqlite3.Connection, profile_id: str) -> list[StandardShift]:
    rows = conn.execute(
        """SELECT kind, start_time, end_time, end_next_day, required_primary_count
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
