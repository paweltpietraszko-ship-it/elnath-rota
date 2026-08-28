"""ROTA-T038 (tasks/ROTA-T038/brief.md, KOREKTA 3 - OWNER_CORRECTED
2026-08-28, Codex round-1 FAIL fixed): Symulator Koordynatora.

A thin "ticks checkboxes and reports" layer, explicitly NOT a layer that
judges whether the solver is right (that role stays with
benchmarks/REAL_OBJECT_BENCHMARK.md, unchanged).

Frozen owner rules (KOREKTA 3, fixing Codex round-1 FINDING T38-R1-01..03):
- staffing is the EXACT computed minimum for the object's own hourly
  workload (ceil(monthly_hours / REALISTIC_HOURS_PER_EMPLOYEE), no safety
  margin -- a coordinator does not pre-provision extra people "just in
  case"; that assumption is explicitly retired);
- every LOCAL employee gets a REAL target_hours for the studied month --
  the statutory full-time norm per Kodeks pracy art. 130 SS1, independent
  of headcount, never a share of this object's own workload (Codex round-2
  FINDING T38-R2-01) -- set through the real target-hours endpoint, never
  left null;
- external support does NOT exist before PLAN. It is created only as a
  reaction to a real DECISION_REQUIRED, exactly like a coordinator who
  "must find someone, even if it means covering the post themselves" --
  see hire_one_more_local() in the driver, called only after a failure,
  never during initial object construction.

For each seed this: invents an object (workload-derived staffing, varying
shift shape/regime), ticks real availability/absence "checkboxes", runs
PLAN -- reactively hiring one more LOCAL and re-PLANning on
DECISION_REQUIRED, exactly as a real coordinator must -- and only then,
if a schedule was actually produced, sometimes exercises REPLAN as a
DISTINCT, separately-reported mid-month event (never an automatic step
after an already-successful PLAN). See test_coordinator_simulator.py for
the driver and report writer. The only judgment made anywhere in this
module is "did anything crash" -- every status and headcount fact is
reported, never asserted as right or wrong.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, time, timedelta

from fastapi.testclient import TestClient

from rota.domain import AvailabilityKind, CalendarDay, ShiftKind, StandardShift
from rota.persistence.calendar_repository import save_calendar_day
from rota.planning.shift_catalog import shift_duration_hours

REALISTIC_HOURS_PER_EMPLOYEE = 160  # a plain, documented approximation of a full-time month, not a hidden constant

WEEKDAYS = (1, 2, 3, 4, 5)  # ISO Mon-Fri
WEEKEND = (6, 7)  # ISO Sat-Sun
ALL_WEEK = (1, 2, 3, 4, 5, 6, 7)

# Owner request 2026-08-28: heterogeneous catalogs, not just one uniform
# shift shape per object. Each row is (kind, start, end, required_primary_count,
# active_weekdays) -- rota/planning/shift_catalog.py::generate_catalog_demands
# already documents "Multiple entries and overlaps are legal and generate
# independent occurrences", confirmed by reading the code, not assumed.
_CATALOG_ROWS: dict[str, list[tuple[str, time, time, int, tuple[int, ...]]]] = {
    "D_N_12H": [
        ("D", time(5, 0), time(17, 0), 1, ALL_WEEK),
        ("N", time(17, 0), time(5, 0), 1, ALL_WEEK),
    ],
    "SINGLE_24H": [
        ("D", time(8, 0), time(8, 0), 1, ALL_WEEK),
    ],
    # Weekday 12h D/N, weekend a single 24h shift -- same total daily hours
    # (24h either way) but a different catalog SHAPE by day of week.
    "WEEKDAY_12H_WEEKEND_24H": [
        ("D", time(6, 0), time(18, 0), 1, WEEKDAYS),
        ("N", time(18, 0), time(6, 0), 1, WEEKDAYS),
        ("D", time(6, 0), time(6, 0), 1, WEEKEND),
    ],
}
_SHAPES_WITH_NIGHT = ("D_N_12H", "WEEKDAY_12H_WEEKEND_24H")

# NOT IMPLEMENTED (owner ruling 2026-08-28, ROTA-T039 Codex round-1 FAIL):
# a night post covered by two people of different durations (owner's real
# example: one works 18-6 continuously (12h), the other only 22-6 (8h)).
# Two attempts failed for structural reasons, not test bugs:
#   1. two truly OVERLAPPING demands (18-6 req=1, 22-6 req=1) -- validator's
#      _check_coverage counts ANY geometrically-overlapping PRIMARY toward
#      EVERY demand it overlaps (explicitly "not covers_demand_id tagging"),
#      so they falsely double-count each other as COVERAGE-01 excess
#      -> TECHNICAL_ERROR;
#   2. two ADJACENT, non-overlapping demands (18-22 req=1, 22-6 req=2) --
#      passes the validator, but nothing forces employee continuity across
#      them: the solver split the actual FEASIBLE candidate into three
#      unrelated fragments (4h+8h+8h across 3 different employees), never
#      one continuous 18-6 person (confirmed via Codex's independent
#      reproduction, tasks/ROTA-T039/round_01/tests/tests_r1.txt T39-R1-01).
#      The only same-employee-continuity mechanism in the product
#      (rota/planning/constraints.py:493-535) is hardcoded to
#      catalog_kind=H24 pairs, not general-purpose.
# Owner decision: leave this pattern unhandled until a real need shows up --
# do not keep guessing workarounds. A real fix needs either a validator
# change (overlapping demands with independent requirements) or a
# generalized continuity mechanism, both out of this simulator's scope.


def _row_hours(start: time, end: time) -> float:
    return shift_duration_hours(StandardShift(ShiftKind.D, start, end, end <= start, 1))


def monthly_hours_for_shape(shift_shape: str, month: date) -> int:
    """Sums the REAL implied workload from the catalog rows themselves --
    no separate hardcoded formula to drift out of sync with the catalog."""
    rows = _CATALOG_ROWS[shift_shape]
    total = 0.0
    for day in _month_dates(month):
        for _kind, start, end, required, active_weekdays in rows:
            if day.isoweekday() in active_weekdays:
                total += _row_hours(start, end) * required
    return round(total)


@dataclass(frozen=True)
class ObjectSpec:
    """One invented, internally-consistent Site: staffing is the EXACT
    computed minimum for this object's own hourly workload -- never a
    margin, never an independent random draw."""

    seed: int
    month: date
    shift_shape: str  # one of _CATALOG_ROWS's keys
    regime: str  # "ORDINARY" | "OCHRONA"
    rolling_7d_threshold_hours: int
    monthly_hours_needed: int
    employee_count: int  # ceil(monthly_hours_needed / REALISTIC_HOURS_PER_EMPLOYEE), no margin
    target_hours_per_employee: int  # real statutory monthly norm (art. 130 KP), independent of headcount
    day_only_indices: tuple[int, ...]


def _days_in_month(month: date) -> int:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return (next_month - month).days


def _month_dates(month: date) -> list[date]:
    count = _days_in_month(month)
    return [month + timedelta(days=i) for i in range(count)]


def nominal_monthly_hours_kp(month: date, holidays: frozenset[date] = frozenset()) -> int:
    """Codex round-2 FINDING T38-R2-01: target_hours must be the REAL
    statutory full-time monthly norm (Kodeks pracy art. 130 SS1), not a
    per-object workload share. 40h per full Mon-Sun week fully inside the
    month, + 8h per remaining Mon-Fri day outside those weeks, - 8h per
    holiday landing on a non-Sunday. Verified by hand for 2026-09
    (3 full weeks + 4+3 remainder weekdays = 120+56 = 176h, no holiday
    that month) against the owner-cited art. 130 reference."""
    days = _month_dates(month)
    hours, i, n = 0, 0, len(days)
    while i < n:
        d = days[i]
        if d.weekday() == 0 and i + 6 < n:  # Monday with a full week still inside the month
            hours += 40
            i += 7
        else:
            if d.weekday() < 5:  # Mon-Fri
                hours += 8
            i += 1
    for h in holidays:
        if h.year == month.year and h.month == month.month and h.weekday() != 6:
            hours -= 8
    return hours


def random_object_spec(seed: int, month: date) -> ObjectSpec:
    """seed=0 is reserved for the simplest realistic object (plain D/N,
    ORDINARY) -- the "everyone available -> nice schedule" baseline from
    the owner's own description. Every other seed cycles DETERMINISTICALLY
    through _CATALOG_ROWS's shapes (Codex round-1 FINDING T39-R1-02: a
    random.choice() left the default 5-seed sweep never exercising any new
    shape at all) -- guarantees every shape appears within the default seed
    range instead of leaving it to chance."""
    rng = random.Random(seed)
    shapes = list(_CATALOG_ROWS)

    if seed == 0:
        shift_shape, regime = "D_N_12H", "ORDINARY"
    else:
        shift_shape = shapes[(seed - 1) % len(shapes)]
        regime = "OCHRONA" if shift_shape in ("SINGLE_24H", "WEEKDAY_12H_WEEKEND_24H") else rng.choice(["ORDINARY", "OCHRONA"])

    # Summed from the actual catalog rows (see monthly_hours_for_shape) --
    # never a separate hardcoded formula that could drift from the catalog.
    monthly_hours_needed = monthly_hours_for_shape(shift_shape, month)
    employee_count = math.ceil(monthly_hours_needed / REALISTIC_HOURS_PER_EMPLOYEE)
    # T38-R2-01: the REAL statutory monthly norm for every full-time
    # employee (art. 130 KP), independent of headcount -- never a share of
    # this object's own workload.
    target_hours_per_employee = nominal_monthly_hours_kp(month)

    if shift_shape in _SHAPES_WITH_NIGHT:
        max_day_only = max(0, employee_count - 3)
        day_only_count = rng.randint(0, max_day_only) if seed != 0 else 0
        day_only_indices = tuple(sorted(rng.sample(range(employee_count), day_only_count)))
    else:
        # A single 24h shift catalog has no distinct night kind to block --
        # DAY_ONLY has nothing to mean here.
        day_only_indices = ()

    return ObjectSpec(
        seed=seed, month=month, shift_shape=shift_shape, regime=regime,
        rolling_7d_threshold_hours=rng.choice([48, 56, 60]) if seed != 0 else 60,
        monthly_hours_needed=monthly_hours_needed, employee_count=employee_count,
        target_hours_per_employee=target_hours_per_employee, day_only_indices=day_only_indices,
    )


@dataclass(frozen=True)
class AbsenceDraw:
    employee_index: int  # index into the LOCAL roster only (as it exists at draw time)
    kind: str  # AvailabilityKind value
    start_date: date
    end_date: date


def random_absence_set(seed: int, spec: ObjectSpec, employee_count: int, *, allow_sick_leave: bool) -> list[AbsenceDraw]:
    """seed=0 draws zero absences -- the explicit "everyone available"
    baseline. employee_count is passed separately from spec.employee_count
    because the roster may have grown via hire_one_more_local() by the time
    a later absence draw (e.g. before REPLAN) happens.

    allow_sick_leave=False for any draw applied before a plan exists yet:
    see arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md -- SICK_LEAVE
    with no accepted plan anywhere in scope is a known, reported product
    gap (IncompleteAbsenceReferenceError -> unhandled 500), not something
    this simulator should silently route around by testing it anyway."""
    if seed == 0 or employee_count == 0:
        return []
    rng = random.Random(seed * 7919 + 1)  # distinct stream from the object generator's own rng
    count = rng.randint(0, 3)
    kinds = [k.value for k in AvailabilityKind if allow_sick_leave or k != AvailabilityKind.SICK_LEAVE]
    days = _month_dates(spec.month)
    draws = []
    for _ in range(count):
        employee_index = rng.randrange(employee_count)
        kind = rng.choice(kinds)
        start_idx = rng.randrange(len(days))
        span = rng.randint(1, min(5, len(days) - start_idx))
        draws.append(AbsenceDraw(
            employee_index=employee_index, kind=kind,
            start_date=days[start_idx], end_date=days[start_idx + span - 1],
        ))
    return draws


def local_employee_id(spec: ObjectSpec, index: int) -> str:
    return f"SIM-{spec.seed}-EMP-{index}"


def seed_calendar(conn, month: date) -> None:
    for day in _month_dates(month):
        save_calendar_day(conn, CalendarDay(day, False))


def _create_site(client: TestClient, spec: ObjectSpec) -> str:
    resp = client.post(
        "/api/workspace/sites",
        json={
            "display_name": f"SIM-{spec.seed}", "profile_display_name": f"SIM-PROFILE-{spec.seed}",
            "rolling_7d_decision_threshold_hours": spec.rolling_7d_threshold_hours, "planning_regime": spec.regime,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["site_id"]


def _put_shift_catalog(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    shifts = [
        {
            "kind": kind, "start_time": start.strftime("%H:%M"), "end_time": end.strftime("%H:%M"),
            "required_primary_count": required, "active_weekdays": list(active_weekdays),
        }
        for kind, start, end, required, active_weekdays in _CATALOG_ROWS[spec.shift_shape]
    ]
    resp = client.put(f"/api/workspace/sites/{site_id}/shift-catalog", json={"shifts": shifts})
    assert resp.status_code == 204, resp.text


def add_local_employee(client: TestClient, site_id: str, spec: ObjectSpec, index: int, day_only: bool) -> str:
    """One real coordinator action: create + attach roster + set a real
    target_hours for the studied month. Reused both for the initial roster
    and for hire_one_more_local()'s reactive hire."""
    employee_id = local_employee_id(spec, index)
    resp = client.post(
        "/api/workspace/employees",
        json={"employee_id": employee_id, "site_id": site_id, "display_name": employee_id, "day_only": day_only},
    )
    assert resp.status_code == 204, resp.text
    resp = client.post(f"/api/workspace/sites/{site_id}/roster", json={"employee_id": employee_id})
    assert resp.status_code == 204, resp.text
    resp = client.post(
        f"/api/workspace/employees/{employee_id}/target-hours",
        json={"site_id": site_id, "month": spec.month.isoformat(), "target_hours": spec.target_hours_per_employee},
    )
    assert resp.status_code == 204, resp.text
    return employee_id


def _add_local_roster(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    for i in range(spec.employee_count):
        add_local_employee(client, site_id, spec, i, day_only=i in spec.day_only_indices)


def hire_one_more_local(client: TestClient, site_id: str, spec: ObjectSpec, current_count: int) -> str:
    """The reactive step, per owner ruling 2026-08-28: a coordinator facing
    DECISION_REQUIRED must find someone -- this is that hire, never done
    upfront. Returns the new employee_id."""
    return add_local_employee(client, site_id, spec, current_count, day_only=False)


def declared_roster(spec: ObjectSpec, current_count: int) -> list[str]:
    """The FULL, honest headcount as of `current_count` local employees --
    grows only via hire_one_more_local(), never pre-provisioned."""
    return [local_employee_id(spec, i) for i in range(current_count)]


def build_object(client: TestClient, conn, spec: ObjectSpec) -> str:
    """The initial object: exactly the computed minimum roster, real
    target_hours for everyone, no external support -- see module docstring."""
    site_id = _create_site(client, spec)
    _put_shift_catalog(client, site_id, spec)
    seed_calendar(conn, spec.month)
    _add_local_roster(client, site_id, spec)
    return site_id


def apply_absences(client: TestClient, site_id: str, spec: ObjectSpec, draws: list[AbsenceDraw]) -> None:
    """The real 'ticking checkboxes' step -- same endpoint a coordinator's
    browser calls (api/routers/durable_inputs.py::create_availability)."""
    for i, draw in enumerate(draws):
        employee_id = local_employee_id(spec, draw.employee_index)
        resp = client.post(
            f"/api/workspace/employees/{employee_id}/availability",
            json={
                "site_id": site_id, "availability_id": f"SIM-{spec.seed}-AVAIL-{i}-{draw.start_date.isoformat()}",
                "kind": draw.kind, "start_date": draw.start_date.isoformat(), "end_date": draw.end_date.isoformat(),
            },
        )
        assert resp.status_code == 204, resp.text
