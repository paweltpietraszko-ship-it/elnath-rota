"""Deterministic scenarios for the real-object benchmark.

The local roster never changes: A-E, with C DAY_ONLY.  X/Y are always
EXTERNAL_SUPPORT and are usable only through explicit windows.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

from benchmarks.real_object_types import (
    AvailabilitySpec,
    ExternalWindowSpec,
    FixedAssignmentSpec,
    OracleClass,
    RuleSpec,
    ScenarioSpec,
)

LOCAL_EMPLOYEES = ("A", "B", "C", "D", "E")
EXTERNAL_EMPLOYEES = ("X", "Y")
SITE_ID = "real-object"
DAY_START = time(5, 0)
NIGHT_START = time(17, 0)
SHIFT_HOURS = 12
LOAD_LIMIT_HOURS = 60
REST_MIN_HOURS = 11


def _dt(day: date, hour: int) -> datetime:
    """Build a benchmark local/naive datetime."""
    return datetime(day.year, day.month, day.day, hour)


def _absence(employee: str, kind: str, start: date, end: date | None = None) -> AvailabilitySpec:
    """Create one inclusive availability range."""
    return AvailabilitySpec(employee, kind, start, end or start)


def _fixed_demand(employee: str, day: date, kind: str) -> FixedAssignmentSpec:
    """Create a full-shift fixed assignment for one benchmark demand."""
    start = _dt(day, 5 if kind == "D" else 17)
    end = start + timedelta(hours=SHIFT_HOURS)
    demand_id = f"{day.isoformat()}-{kind}"
    return FixedAssignmentSpec(f"fixed-{demand_id}-{employee}", employee, start, end, "PLANNED", True, demand_id)


def _window(employee: str, day: date, kind: str, *, active: bool = True, site_id: str = SITE_ID) -> ExternalWindowSpec:
    """Create an exact one-shift ExternalSupportWindow."""
    start = _dt(day, 5 if kind == "D" else 17)
    return ExternalWindowSpec(
        f"window-{employee}-{day}-{kind}", employee, start, start + timedelta(hours=SHIFT_HOURS),
        kind, active, site_id,
    )


def standard_boundary(month: date) -> tuple[FixedAssignmentSpec, ...]:
    """Return six valid days of history before month start.

    The pattern has one D and one N per day, never gives C a night, keeps at
    least 12h rest, and keeps every employee below 60h in the six-day slice.
    """
    day_staff = ("C", "A", "B", "C", "D", "E")
    night_staff = ("D", "E", "D", "A", "B", "A")
    assignments = []
    for index, offset in enumerate(range(-6, 0)):
        day = month + timedelta(days=offset)
        for kind, employee, hour in (("D", day_staff[index], 5), ("N", night_staff[index], 17)):
            start = _dt(day, hour)
            assignments.append(FixedAssignmentSpec(
                f"boundary-{day}-{kind}-{employee}", employee, start,
                start + timedelta(hours=SHIFT_HOURS), "REALIZED", True, None,
            ))
    return tuple(assignments)


def _baseline_october() -> ScenarioSpec:
    """Literal ROTA-REG-001 operational baseline."""
    month = date(2026, 10, 1)
    availability = (
        _absence("A", "DAY_SHIFT_OFF", date(2026, 10, 6)),
        _absence("A", "DAY_SHIFT_OFF", date(2026, 10, 17)),
        _absence("A", "DAY_SHIFT_OFF", date(2026, 10, 26)),
        _absence("B", "LEAVE_GRANTED", date(2026, 10, 12), date(2026, 10, 18)),
        _absence("D", "UNAVAILABLE_24H", date(2026, 10, 9)),
        _absence("D", "UNAVAILABLE_24H", date(2026, 10, 23), date(2026, 10, 24)),
    )
    return ScenarioSpec(
        "reg-001-oct-2026", month, availability=availability,
        fixed_demand_assignments=(_fixed_demand("A", date(2026, 10, 8), "D"),),
        declared_class=OracleClass.KNOWN_FEASIBLE,
        strict_monthly_hours=(("A", 156), ("B", 144), ("C", 156), ("D", 144), ("E", 144)),
        note="Literal ROTA-REG-001: no external window and A fixed on 8 Oct D.",
    )


def _calendar_case(case_id: str, month: date) -> ScenarioSpec:
    """Create a clean real-roster calendar-shape case."""
    return ScenarioSpec(
        case_id, month, boundary_assignments=standard_boundary(month),
        external_support_enabled=True, declared_class=OracleClass.KNOWN_FEASIBLE,
        note=f"Clean {calendar.monthrange(month.year, month.month)[1]}-day month.",
    )


def _load_decision_case() -> ScenarioSpec:
    """Force E onto six D shifts in seven days; uncapped LOAD remains feasible."""
    month = date(2027, 3, 1)
    unavailable = _absence("C", "UNAVAILABLE_24H", date(2027, 3, 10), date(2027, 3, 15))
    rules = tuple(
        RuleSpec(f"{employee}-N-only", "EMPLOYEE_ALLOWED_SHIFT_KINDS", employee, ("N",))
        for employee in ("A", "B", "D")
    )
    return ScenarioSpec(
        "load-decision-forced-72h", month, availability=(unavailable,), site_rules=rules,
        boundary_assignments=standard_boundary(month), external_support_enabled=True,
        declared_class=OracleClass.LOAD_DECISION_REQUIRED,
        note="C absent for six days; A/B/D N-only means E is the only local D worker on those days.",
    )


def _external_pair() -> tuple[ScenarioSpec, ScenarioSpec]:
    """Return the same shortage before and after explicit X confirmation."""
    month = date(2027, 5, 1)
    day = date(2027, 5, 12)
    availability = tuple(_absence(employee, "UNAVAILABLE_24H", day) for employee in ("A", "B", "D", "E"))
    x_window = _window("X", day, "N")
    common = dict(
        month=month, availability=availability, boundary_assignments=standard_boundary(month),
        external_support_enabled=True,
    )
    before = ScenarioSpec(
        "external-before-confirmation", external_probe_windows=(x_window,),
        declared_class=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED,
        note="Only C can cover D; no LOCAL can cover N. X could solve N, but has no current window.",
        **common,
    )
    after = ScenarioSpec(
        "external-after-confirmation", external_windows=(x_window,),
        declared_class=OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT,
        note="Same state after coordinator explicitly opens X window for the missing N.",
        **common,
    )
    return before, after


def _proven_shortage_case() -> ScenarioSpec:
    """Create a demand with no eligible LOCAL or explicitly-windowed external."""
    month = date(2027, 6, 1)
    day = date(2027, 6, 10)
    availability = tuple(
        _absence(employee, "UNAVAILABLE_24H", day) for employee in ("A", "B", "D", "E", "X", "Y")
    )
    windows = (_window("X", day, "N"), _window("Y", day, "N"))
    return ScenarioSpec(
        "proven-staffing-shortage", month, availability=availability,
        boundary_assignments=standard_boundary(month), external_windows=windows,
        external_probe_windows=windows, external_support_enabled=True,
        declared_class=OracleClass.PROVEN_STAFFING_SHORTAGE,
        note="C can cover D; every flexible LOCAL and both explicitly offered external workers are unavailable for N.",
    )


def _rest_boundary_case(case_id: str, end_hour: int) -> ScenarioSpec:
    """Create a boundary interval whose rest to day-1 D is 11h or 10h for E."""
    month = date(2027, 8, 1)
    prior = month - timedelta(days=1)
    boundary = list(standard_boundary(month))
    boundary = [item for item in boundary if not (item.employee_id == "E" and item.start.date() == prior)]
    start = _dt(prior, end_hour - 12)
    boundary.append(FixedAssignmentSpec(
        f"{case_id}-E-boundary", "E", start, _dt(prior, end_hour), "REALIZED", True, None,
    ))
    return ScenarioSpec(
        case_id, month, boundary_assignments=tuple(boundary), external_support_enabled=True,
        declared_class=OracleClass.KNOWN_FEASIBLE,
        note=f"E boundary work ends {end_hour:02d}:00 before 05:00 D on day 1.",
    )


def core_scenarios() -> tuple[ScenarioSpec, ...]:
    """Return the fixed correctness matrix used by default."""
    external_before, external_after = _external_pair()
    return (
        _baseline_october(),
        _calendar_case("calendar-28-feb-2027", date(2027, 2, 1)),
        _calendar_case("calendar-29-feb-2028", date(2028, 2, 1)),
        _calendar_case("calendar-30-apr-2027", date(2027, 4, 1)),
        _calendar_case("calendar-31-jul-2027", date(2027, 7, 1)),
        ScenarioSpec(
            "single-absence", date(2027, 9, 1),
            availability=(_absence("B", "UNAVAILABLE_24H", date(2027, 9, 14)),),
            boundary_assignments=standard_boundary(date(2027, 9, 1)), external_support_enabled=True,
        ),
        ScenarioSpec(
            "overlapping-absence-two-local", date(2027, 11, 1),
            availability=(
                _absence("A", "LEAVE_GRANTED", date(2027, 11, 8), date(2027, 11, 10)),
                _absence("B", "UNAVAILABLE_24H", date(2027, 11, 9), date(2027, 11, 10)),
            ),
            boundary_assignments=standard_boundary(date(2027, 11, 1)), external_support_enabled=True,
        ),
        _load_decision_case(),
        external_before,
        external_after,
        _proven_shortage_case(),
        _rest_boundary_case("rest-boundary-exact-11h", 18),
        _rest_boundary_case("rest-boundary-below-11h", 19),
    )


def calendar_scenarios() -> tuple[ScenarioSpec, ...]:
    """Return 24 clean consecutive months to catch calendar-shape regressions."""
    scenarios = []
    year, month_number = 2027, 1
    for _ in range(24):
        month = date(year, month_number, 1)
        scenarios.append(_calendar_case(f"calendar-sweep-{month.isoformat()}", month))
        month_number += 1
        if month_number == 13:
            month_number = 1
            year += 1
    return tuple(scenarios)


def all_scenarios() -> tuple[ScenarioSpec, ...]:
    """Return core plus calendar sweep without duplicate case ids."""
    by_id = {scenario.case_id: scenario for scenario in (*core_scenarios(), *calendar_scenarios())}
    return tuple(by_id[key] for key in sorted(by_id))


if __name__ == "__main__":
    print(f"real_object_scenarios: {len(core_scenarios())} core cases")
