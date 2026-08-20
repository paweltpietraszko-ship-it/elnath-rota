"""Site persistence (tasks/ROTA-T008/brief.md MUTABLE CURRENT-STATE ENTITIES).

Current-state entity: save/upsert overwrites, no hidden history. No
physical delete API -- active=false represents disabling.

ROTA-T020 Checkpoint B (tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md Section 5/6):
SitePrintSettings is also current mutable state -- no history table, saving
it never creates a ScheduleVersion. Owned here rather than a new module per
the frozen contract ("no new repository module is created").
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from rota.domain import Site


class SiteNotFound(Exception):
    """Raised when site_id has no matching row."""


class UnknownSiteProfile(Exception):
    """Raised when Site.profile_id does not identify an existing SiteProfile."""


class InvalidSitePrintSettings(Exception):
    """ROTA-T020 PRINT_SETTINGS_INVALID: raised at write time, and again if
    already-persisted settings fail revalidation on read (corrupt/legacy
    data must never silently pass into export)."""


# Frozen owner legend (tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md A15-6):
# code -> exact hour value. Never persisted as mutable configuration.
FROZEN_WORK_CODE_HOURS = {
    "D1": 12, "D2": 4, "D3": 24, "D4": 2, "D5": 24,
    "N1": 12, "N2": 16, "N3": 24, "N4": 24, "N5": 24,
}
WORK_CODE_KEYS = tuple(FROZEN_WORK_CODE_HOURS)
RESERVE_SLOT_KEYS = ("U3", "U4", "U5", "C3", "C4", "C5")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class WorkCodeInterval:
    start_time: str  # zero-padded "HH:MM"
    end_time: str
    end_next_day: bool


@dataclass(frozen=True)
class SitePrintSettings:
    site_id: str
    company_print_name: str
    site_print_name: str
    base_regime: str  # "12h" | "24h"
    work_code_intervals: dict[str, Optional[WorkCodeInterval]]  # exactly WORK_CODE_KEYS
    reserve_hours: dict[str, Optional[int]]  # exactly RESERVE_SLOT_KEYS


def _interval_duration_hours(interval: WorkCodeInterval) -> float:
    if not (_TIME_RE.match(interval.start_time) and _TIME_RE.match(interval.end_time)):
        raise InvalidSitePrintSettings(f"malformed time in {interval!r}")
    anchor = date(2000, 1, 1)
    start = datetime.combine(anchor, datetime.strptime(interval.start_time, "%H:%M").time())
    end = datetime.combine(anchor, datetime.strptime(interval.end_time, "%H:%M").time())
    if interval.end_next_day:
        end += timedelta(days=1)
    duration = (end - start).total_seconds() / 3600
    if duration <= 0:
        raise InvalidSitePrintSettings(f"non-positive duration in {interval!r}")
    return duration


def _validate_work_code_intervals(intervals: dict[str, Optional[WorkCodeInterval]]) -> None:
    if set(intervals) != set(WORK_CODE_KEYS):
        raise InvalidSitePrintSettings(f"work_code_intervals must have exactly keys {WORK_CODE_KEYS}")
    seen_by_family: dict[str, set[tuple[str, str, bool]]] = {"D": set(), "N": set()}
    for code, interval in intervals.items():
        if interval is None:
            continue
        if _interval_duration_hours(interval) != FROZEN_WORK_CODE_HOURS[code]:
            raise InvalidSitePrintSettings(f"{code} interval duration must equal {FROZEN_WORK_CODE_HOURS[code]}h")
        signature = (interval.start_time, interval.end_time, interval.end_next_day)
        family = code[0]
        if signature in seen_by_family[family]:
            raise InvalidSitePrintSettings(f"duplicate {family}-family signature {signature}")
        seen_by_family[family].add(signature)


def _validate_reserve_hours(reserve: dict[str, Optional[int]]) -> None:
    if set(reserve) != set(RESERVE_SLOT_KEYS):
        raise InvalidSitePrintSettings(f"reserve_hours must have exactly keys {RESERVE_SLOT_KEYS}")
    for slot, value in reserve.items():
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            raise InvalidSitePrintSettings(f"{slot} reserve value must be a positive integer or null, got {value!r}")


def validate_site_print_settings(settings: SitePrintSettings) -> None:
    if settings.base_regime not in ("12h", "24h"):
        raise InvalidSitePrintSettings(f"base_regime must be '12h' or '24h', got {settings.base_regime!r}")
    _validate_work_code_intervals(settings.work_code_intervals)
    _validate_reserve_hours(settings.reserve_hours)


def write_site_in_open_transaction(conn: sqlite3.Connection, site: Site) -> None:
    """Same write as save_site, without its own `with conn:` (see
    rota.persistence.coordinator_repository.write_coordinator_in_open_transaction)."""
    row = conn.execute(
        "SELECT 1 FROM site_profiles WHERE profile_id = ?", (site.profile_id,)
    ).fetchone()
    if row is None:
        raise UnknownSiteProfile(site.profile_id)
    conn.execute(
        """INSERT INTO sites (site_id, profile_id, display_name, active)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(site_id) DO UPDATE SET
            profile_id=excluded.profile_id,
            display_name=excluded.display_name,
            active=excluded.active""",
        (site.site_id, site.profile_id, site.display_name, int(site.active)),
    )


def save_site(conn: sqlite3.Connection, site: Site) -> None:
    with conn:
        write_site_in_open_transaction(conn, site)


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


def _intervals_to_json(intervals: dict[str, Optional[WorkCodeInterval]]) -> str:
    payload = {
        code: (None if iv is None else {"start_time": iv.start_time, "end_time": iv.end_time, "end_next_day": iv.end_next_day})
        for code, iv in intervals.items()
    }
    return json.dumps(payload, sort_keys=True)


def _intervals_from_json(raw: str) -> dict[str, Optional[WorkCodeInterval]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed work_code_intervals_json: {exc}") from exc
    result: dict[str, Optional[WorkCodeInterval]] = {}
    for code, value in payload.items():
        if value is None:
            result[code] = None
            continue
        if set(value) != {"start_time", "end_time", "end_next_day"}:
            raise InvalidSitePrintSettings(f"{code}: work-code interval must have exactly start_time/end_time/end_next_day")
        result[code] = WorkCodeInterval(value["start_time"], value["end_time"], bool(value["end_next_day"]))
    return result


def save_site_print_settings(conn: sqlite3.Connection, settings: SitePrintSettings) -> None:
    validate_site_print_settings(settings)
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (settings.site_id,)).fetchone()
    if site_row is None:
        raise SiteNotFound(settings.site_id)
    with conn:
        conn.execute(
            """INSERT INTO site_print_settings
               (site_id, company_print_name, site_print_name, base_regime,
                work_code_intervals_json, reserve_hours_json)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(site_id) DO UPDATE SET
                company_print_name=excluded.company_print_name,
                site_print_name=excluded.site_print_name,
                base_regime=excluded.base_regime,
                work_code_intervals_json=excluded.work_code_intervals_json,
                reserve_hours_json=excluded.reserve_hours_json""",
            (
                settings.site_id, settings.company_print_name, settings.site_print_name, settings.base_regime,
                _intervals_to_json(settings.work_code_intervals), json.dumps(settings.reserve_hours, sort_keys=True),
            ),
        )


def get_site_print_settings(conn: sqlite3.Connection, site_id: str) -> Optional[SitePrintSettings]:
    row = conn.execute(
        "SELECT site_id, company_print_name, site_print_name, base_regime, "
        "work_code_intervals_json, reserve_hours_json FROM site_print_settings WHERE site_id = ?",
        (site_id,),
    ).fetchone()
    if row is None:
        return None
    site_id_, company, site_name, regime, intervals_json, reserve_json = row
    try:
        reserve = json.loads(reserve_json)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed reserve_hours_json: {exc}") from exc
    settings = SitePrintSettings(
        site_id=site_id_, company_print_name=company, site_print_name=site_name, base_regime=regime,
        work_code_intervals=_intervals_from_json(intervals_json), reserve_hours=reserve,
    )
    validate_site_print_settings(settings)  # revalidate: corrupt persisted rows must fail closed, never silently pass
    return settings


if __name__ == "__main__":
    print("persistence.site_repository module OK")
