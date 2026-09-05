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

from rota.domain import Site, SitePlanningRegime


class SiteNotFound(Exception):
    """Raised when site_id has no matching row."""


class UnknownSiteProfile(Exception):
    """Raised when Site.profile_id does not identify an existing SiteProfile."""


class SiteRegimeChangeRejected(Exception):
    """ROTA-T023b: raised when a normal Site write attempts to change
    planning_regime -- only the dedicated correction primitive may do
    that (frozen addendum section 3: "ordinary Site editing cannot
    change the regime")."""


class UnsupportedSitePlanningRegime(Exception):
    """ROTA-T023b: raised when a stored planning_regime value is not a
    recognized SitePlanningRegime -- reads fail closed, never guess."""


class InvalidSitePrintSettings(Exception):
    """ROTA-T020 PRINT_SETTINGS_INVALID: raised at write time, and again if
    already-persisted settings fail revalidation on read (corrupt/legacy
    data must never silently pass into export). ROTA-T056 reuses this same
    exception for monthly extra D6+/N6+ code validation and the shared
    signature-collision invariant -- same family of "print configuration is
    malformed/inconsistent" errors, no new exception type."""


# Frozen owner legend (tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md A15-6):
# code -> exact hour value. Never persisted as mutable configuration.
FROZEN_WORK_CODE_HOURS = {
    "D1": 12, "D2": 4, "D3": 24, "D4": 2, "D5": 24,
    "N1": 12, "N2": 16, "N3": 24, "N4": 24, "N5": 24,
}
WORK_CODE_KEYS = tuple(FROZEN_WORK_CODE_HOURS)
RESERVE_SLOT_KEYS = ("U3", "U4", "U5", "C3", "C4", "C5")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

# ROTA-T056: monthly-only additional real-work D/N codes (brief section 5).
# Only the D/N family and only suffix >= 6 -- D1-5/N1-5 stay exclusively in
# FROZEN_WORK_CODE_HOURS/WORK_CODE_KEYS above, untouched. No upper bound on
# the suffix or on how many extra codes one (site, month) may define (brief:
# "Nie ograniczać liczby dodatkowych kodów do jednego slotu ani do D6/N6").
_EXTRA_CODE_RE = re.compile(r"^([DN])([6-9]|[1-9]\d+)$")


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
    # ROTA-T052 (brief section 4): S1 is NOT a WORK_CODE_KEYS entry -- it has
    # no fixed duration, only a default start/end the coordinator can reuse
    # when entering S1 in MonthlyPlanning. Never validated against
    # FROZEN_WORK_CODE_HOURS.
    s1_default_interval: Optional[WorkCodeInterval] = None


def interval_duration_hours(interval: WorkCodeInterval) -> float:
    """Public alias -- ROTA-T056: schedule_export.py needs this to compute a
    validated monthly extra code's real duration (never a separate stored
    duration_hours field, per brief section 5)."""
    return _interval_duration_hours(interval)


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


def _signature(interval: WorkCodeInterval) -> tuple[str, str, bool]:
    return (interval.start_time, interval.end_time, interval.end_next_day)


def _standard_signatures_by_family(intervals: dict[str, Optional[WorkCodeInterval]]) -> dict[str, set[tuple]]:
    by_family: dict[str, set[tuple]] = {"D": set(), "N": set()}
    for code, interval in intervals.items():
        if interval is not None:
            by_family[code[0]].add(_signature(interval))
    return by_family


def _validate_work_code_intervals(
    intervals: dict[str, Optional[WorkCodeInterval]], *, extra_signatures_by_family: Optional[dict[str, set[tuple]]] = None,
) -> None:
    if set(intervals) != set(WORK_CODE_KEYS):
        raise InvalidSitePrintSettings(f"work_code_intervals must have exactly keys {WORK_CODE_KEYS}")
    seen_by_family: dict[str, set[tuple[str, str, bool]]] = {"D": set(), "N": set()}
    for code, interval in intervals.items():
        if interval is None:
            continue
        if _interval_duration_hours(interval) != FROZEN_WORK_CODE_HOURS[code]:
            raise InvalidSitePrintSettings(f"{code} interval duration must equal {FROZEN_WORK_CODE_HOURS[code]}h")
        signature = _signature(interval)
        family = code[0]
        if signature in seen_by_family[family]:
            raise InvalidSitePrintSettings(f"duplicate {family}-family signature {signature}")
        seen_by_family[family].add(signature)
        # ROTA-T056 write-boundary 2 (brief section 5): editing a standard
        # code's clock times must not collide with any monthly D6+/N6+
        # extra code signature already saved for this Site, across every
        # month -- the standard signature is per-site, so it is checked
        # against ALL saved months, not just one.
        if extra_signatures_by_family is not None and signature in extra_signatures_by_family.get(family, ()):
            raise InvalidSitePrintSettings(
                f"{code}: interval collides with an already-saved monthly extra {family}-family code for this Site"
            )


def _validate_reserve_hours(reserve: dict[str, Optional[int]]) -> None:
    if set(reserve) != set(RESERVE_SLOT_KEYS):
        raise InvalidSitePrintSettings(f"reserve_hours must have exactly keys {RESERVE_SLOT_KEYS}")
    for slot, value in reserve.items():
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            raise InvalidSitePrintSettings(f"{slot} reserve value must be a positive integer or null, got {value!r}")


def _validate_s1_default_interval(interval: WorkCodeInterval) -> None:
    """ROTA-T052 (brief section 4): S1 has no fixed duration -- only full
    clock hours, same global rule as every other work code."""
    if not (_TIME_RE.match(interval.start_time) and _TIME_RE.match(interval.end_time)):
        raise InvalidSitePrintSettings(f"S1 interval: malformed time in {interval!r}")
    if not interval.start_time.endswith(":00") or not interval.end_time.endswith(":00"):
        raise InvalidSitePrintSettings(f"S1 interval: start/end must be a full clock hour, got {interval!r}")
    if _interval_duration_hours(interval) <= 0:
        raise InvalidSitePrintSettings(f"S1 interval: non-positive duration in {interval!r}")


def validate_site_print_settings(
    settings: SitePrintSettings, *, extra_signatures_by_family: Optional[dict[str, set[tuple]]] = None,
) -> None:
    if settings.base_regime not in ("12h", "24h"):
        raise InvalidSitePrintSettings(f"base_regime must be '12h' or '24h', got {settings.base_regime!r}")
    _validate_work_code_intervals(settings.work_code_intervals, extra_signatures_by_family=extra_signatures_by_family)
    _validate_reserve_hours(settings.reserve_hours)
    if settings.s1_default_interval is not None:
        _validate_s1_default_interval(settings.s1_default_interval)


def _regime_from_value(value: str) -> SitePlanningRegime:
    try:
        return SitePlanningRegime(value)
    except ValueError as exc:
        raise UnsupportedSitePlanningRegime(f"unsupported stored planning_regime {value!r}") from exc


def write_site_in_open_transaction(conn: sqlite3.Connection, site: Site) -> None:
    """Same write as save_site, without its own `with conn:` (see
    rota.persistence.coordinator_repository.write_coordinator_in_open_transaction).

    ROTA-T023b: rejects any attempt to change an existing Site's
    planning_regime -- the UPDATE SET clause below never touches that
    column, and this check raises explicitly rather than silently
    ignoring the caller's requested value. Only
    correct_site_planning_regime_in_open_transaction may change it."""
    row = conn.execute(
        "SELECT 1 FROM site_profiles WHERE profile_id = ?", (site.profile_id,)
    ).fetchone()
    if row is None:
        raise UnknownSiteProfile(site.profile_id)
    existing = conn.execute("SELECT planning_regime FROM sites WHERE site_id = ?", (site.site_id,)).fetchone()
    if existing is not None and existing[0] != site.planning_regime.value:
        raise SiteRegimeChangeRejected(
            f"{site.site_id}: ordinary Site write cannot change planning_regime "
            f"({existing[0]} -> {site.planning_regime.value}); "
            f"use correct_site_planning_regime_in_open_transaction"
        )
    conn.execute(
        """INSERT INTO sites (site_id, profile_id, display_name, active, planning_regime)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(site_id) DO UPDATE SET
            profile_id=excluded.profile_id,
            display_name=excluded.display_name,
            active=excluded.active""",
        (site.site_id, site.profile_id, site.display_name, int(site.active), site.planning_regime.value),
    )


def correct_site_planning_regime_in_open_transaction(
    conn: sqlite3.Connection, *, site_id: str, planning_regime: SitePlanningRegime,
) -> None:
    """ROTA-T023b: the one narrowly named primitive allowed to change an
    EXISTING Site's planning_regime -- updates only that column. Only
    rota.application.durable_inputs.correct_site_planning_regime calls
    this; ordinary Site writes above reject any regime change."""
    row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (site_id,)).fetchone()
    if row is None:
        raise SiteNotFound(site_id)
    conn.execute("UPDATE sites SET planning_regime = ? WHERE site_id = ?", (planning_regime.value, site_id))


def save_site(conn: sqlite3.Connection, site: Site) -> None:
    with conn:
        write_site_in_open_transaction(conn, site)


def get_site(conn: sqlite3.Connection, site_id: str) -> Site:
    row = conn.execute(
        "SELECT site_id, profile_id, display_name, active, planning_regime FROM sites WHERE site_id = ?", (site_id,)
    ).fetchone()
    if row is None:
        raise SiteNotFound(site_id)
    site_id_, profile_id, display_name, active, regime = row
    return Site(
        site_id=site_id_, profile_id=profile_id, display_name=display_name, active=bool(active),
        planning_regime=_regime_from_value(regime),
    )


def list_sites(conn: sqlite3.Connection) -> list[Site]:
    rows = conn.execute(
        "SELECT site_id, profile_id, display_name, active, planning_regime FROM sites ORDER BY site_id"
    ).fetchall()
    return [
        Site(
            site_id=site_id, profile_id=profile_id, display_name=display_name, active=bool(active),
            planning_regime=_regime_from_value(regime),
        )
        for site_id, profile_id, display_name, active, regime in rows
    ]


def _intervals_to_json(intervals: dict[str, Optional[WorkCodeInterval]]) -> str:
    payload = {
        code: (None if iv is None else {"start_time": iv.start_time, "end_time": iv.end_time, "end_next_day": iv.end_next_day})
        for code, iv in intervals.items()
    }
    return json.dumps(payload, sort_keys=True)


def _interval_from_value(code: str, value) -> Optional[WorkCodeInterval]:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"start_time", "end_time", "end_next_day"}:
        raise InvalidSitePrintSettings(f"{code}: work-code interval must be an object with exactly start_time/end_time/end_next_day")
    start_time, end_time, end_next_day = value["start_time"], value["end_time"], value["end_next_day"]
    if not isinstance(start_time, str) or not isinstance(end_time, str) or not isinstance(end_next_day, bool):
        raise InvalidSitePrintSettings(f"{code}: start_time/end_time must be strings and end_next_day a JSON boolean")
    return WorkCodeInterval(start_time, end_time, end_next_day)


def _intervals_from_json(raw: str) -> dict[str, Optional[WorkCodeInterval]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed work_code_intervals_json: {exc}") from exc
    if not isinstance(payload, dict):
        raise InvalidSitePrintSettings("work_code_intervals_json must decode to a JSON object")
    return {code: _interval_from_value(code, value) for code, value in payload.items()}


def _s1_interval_to_json(interval: Optional[WorkCodeInterval]) -> Optional[str]:
    if interval is None:
        return None
    return json.dumps(
        {"start_time": interval.start_time, "end_time": interval.end_time, "end_next_day": interval.end_next_day},
        sort_keys=True,
    )


def _s1_interval_from_json(raw: Optional[str]) -> Optional[WorkCodeInterval]:
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed s1_default_interval_json: {exc}") from exc
    return _interval_from_value("S1", payload)


def save_site_print_settings(conn: sqlite3.Connection, settings: SitePrintSettings) -> None:
    extra_signatures_by_family = _all_extra_signatures_for_site(conn, settings.site_id)
    validate_site_print_settings(settings, extra_signatures_by_family=extra_signatures_by_family)
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (settings.site_id,)).fetchone()
    if site_row is None:
        raise SiteNotFound(settings.site_id)
    with conn:
        conn.execute(
            """INSERT INTO site_print_settings
               (site_id, company_print_name, site_print_name, base_regime,
                work_code_intervals_json, reserve_hours_json, s1_default_interval_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(site_id) DO UPDATE SET
                company_print_name=excluded.company_print_name,
                site_print_name=excluded.site_print_name,
                base_regime=excluded.base_regime,
                work_code_intervals_json=excluded.work_code_intervals_json,
                reserve_hours_json=excluded.reserve_hours_json,
                s1_default_interval_json=excluded.s1_default_interval_json""",
            (
                settings.site_id, settings.company_print_name, settings.site_print_name, settings.base_regime,
                _intervals_to_json(settings.work_code_intervals), json.dumps(settings.reserve_hours, sort_keys=True),
                _s1_interval_to_json(settings.s1_default_interval),
            ),
        )


def get_site_print_settings(conn: sqlite3.Connection, site_id: str) -> Optional[SitePrintSettings]:
    row = conn.execute(
        "SELECT site_id, company_print_name, site_print_name, base_regime, "
        "work_code_intervals_json, reserve_hours_json, s1_default_interval_json FROM site_print_settings WHERE site_id = ?",
        (site_id,),
    ).fetchone()
    if row is None:
        return None
    site_id_, company, site_name, regime, intervals_json, reserve_json, s1_interval_json = row
    try:
        reserve = json.loads(reserve_json)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed reserve_hours_json: {exc}") from exc
    if not isinstance(reserve, dict):
        raise InvalidSitePrintSettings("reserve_hours_json must decode to a JSON object")
    settings = SitePrintSettings(
        site_id=site_id_, company_print_name=company, site_print_name=site_name, base_regime=regime,
        work_code_intervals=_intervals_from_json(intervals_json), reserve_hours=reserve,
        s1_default_interval=_s1_interval_from_json(s1_interval_json),
    )
    validate_site_print_settings(settings)  # revalidate: corrupt persisted rows must fail closed, never silently pass
    return settings


# ---------------------------------------------------------------------------
# ROTA-T056: monthly additional D6+/N6+ real-work codes, keyed by
# (site_id, month). Current-state, no history -- a save always overwrites
# the whole set for that month (brief section 4/13). D1-5/N1-5 and
# FROZEN_WORK_CODE_HOURS above are never touched by any function below.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MonthlyExtraWorkCodes:
    site_id: str
    month: date  # canonical first-of-month, same caller convention as PlanPreview (plan_preview_repository.py)
    codes: dict[str, WorkCodeInterval]  # keys match _EXTRA_CODE_RE; never null


def _validate_extra_code_shape(code: str, interval: WorkCodeInterval) -> None:
    if not _EXTRA_CODE_RE.match(code):
        raise InvalidSitePrintSettings(f"{code}: monthly extra code must be D or N family with an integer suffix >= 6")
    duration = _interval_duration_hours(interval)  # raises on malformed time / non-positive duration
    if duration != int(duration):
        raise InvalidSitePrintSettings(f"{code}: interval duration must be a whole number of hours, got {duration}")


def validate_monthly_extra_work_codes(
    codes: dict[str, WorkCodeInterval], *, standard_intervals: dict[str, Optional[WorkCodeInterval]],
) -> None:
    """ROTA-T056 write-boundary 1 (brief section 5): the one legal entry
    point for saving a (site, month)'s extra D6+/N6+ codes. `standard_intervals`
    is that Site's CURRENT frozen-duration standard work_code_intervals
    (site_print_settings) -- an extra code's signature must not collide with
    a configured standard code of the same family, nor with another extra
    code saved in this same call."""
    seen_by_family: dict[str, set[tuple]] = {"D": set(), "N": set()}
    standard_by_family = _standard_signatures_by_family(standard_intervals)
    for code, interval in codes.items():
        _validate_extra_code_shape(code, interval)
        family = code[0]
        signature = _signature(interval)
        if signature in standard_by_family[family]:
            raise InvalidSitePrintSettings(f"{code}: interval collides with a configured standard {family}-family code")
        if signature in seen_by_family[family]:
            raise InvalidSitePrintSettings(f"{code}: duplicate {family}-family signature {signature} within the same month")
        seen_by_family[family].add(signature)


def _extra_codes_to_json(codes: dict[str, WorkCodeInterval]) -> str:
    payload = {
        code: {"start_time": iv.start_time, "end_time": iv.end_time, "end_next_day": iv.end_next_day}
        for code, iv in codes.items()
    }
    return json.dumps(payload, sort_keys=True)


def _extra_codes_from_json(raw: str) -> dict[str, WorkCodeInterval]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidSitePrintSettings(f"malformed codes_json: {exc}") from exc
    if not isinstance(payload, dict):
        raise InvalidSitePrintSettings("codes_json must decode to a JSON object")
    result: dict[str, WorkCodeInterval] = {}
    for code, value in payload.items():
        interval = _interval_from_value(code, value)
        if interval is None:
            raise InvalidSitePrintSettings(f"{code}: monthly extra code interval must not be null")
        result[code] = interval
    return result


def _all_extra_signatures_for_site(conn: sqlite3.Connection, site_id: str) -> dict[str, set[tuple]]:
    """ROTA-T056 write-boundary 2 support (brief section 5.2): every
    monthly extra code's signature across every month saved for this Site
    -- used to reject a standard-code clock-time edit that would collide
    with any of them, wherever in time they live."""
    by_family: dict[str, set[tuple]] = {"D": set(), "N": set()}
    rows = conn.execute("SELECT codes_json FROM site_monthly_extra_work_codes WHERE site_id = ?", (site_id,)).fetchall()
    for (codes_json,) in rows:
        for code, interval in _extra_codes_from_json(codes_json).items():
            by_family[code[0]].add(_signature(interval))
    return by_family


def save_site_monthly_extra_work_codes_in_open_transaction(conn: sqlite3.Connection, extra: MonthlyExtraWorkCodes) -> None:
    """R8-01 fix: no own `with conn:` -- durable_inputs.save_monthly_extra_work_codes
    composes this with its action-history write in one outer transaction."""
    site_row = conn.execute("SELECT 1 FROM sites WHERE site_id = ?", (extra.site_id,)).fetchone()
    if site_row is None:
        raise SiteNotFound(extra.site_id)
    standard = get_site_print_settings(conn, extra.site_id)
    standard_intervals: dict[str, Optional[WorkCodeInterval]] = (
        standard.work_code_intervals if standard is not None else dict.fromkeys(WORK_CODE_KEYS)
    )
    validate_monthly_extra_work_codes(extra.codes, standard_intervals=standard_intervals)
    conn.execute(
        """INSERT INTO site_monthly_extra_work_codes (site_id, month, codes_json)
           VALUES (?, ?, ?)
           ON CONFLICT(site_id, month) DO UPDATE SET codes_json=excluded.codes_json""",
        (extra.site_id, extra.month.isoformat(), _extra_codes_to_json(extra.codes)),
    )


def save_site_monthly_extra_work_codes(conn: sqlite3.Connection, extra: MonthlyExtraWorkCodes) -> None:
    with conn:
        save_site_monthly_extra_work_codes_in_open_transaction(conn, extra)


def get_site_monthly_extra_work_codes(conn: sqlite3.Connection, site_id: str, month: date) -> dict[str, WorkCodeInterval]:
    row = conn.execute(
        "SELECT codes_json FROM site_monthly_extra_work_codes WHERE site_id = ? AND month = ?",
        (site_id, month.isoformat()),
    ).fetchone()
    if row is None:
        return {}
    return _extra_codes_from_json(row[0])


if __name__ == "__main__":
    print("persistence.site_repository module OK")
