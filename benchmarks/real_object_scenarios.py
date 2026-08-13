"""Deterministic scenario catalog for ROTA-REAL-OBJECT-01."""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta

from benchmarks.real_object_types import (
    AvailabilitySpec,
    DemandSpec,
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
    return datetime(day.year, day.month, day.day, hour)


def demands_for_month(scenario: ScenarioSpec) -> tuple[DemandSpec, ...]:
    days = calendar.monthrange(scenario.month.year, scenario.month.month)[1]
    demands = []
    for day_number in range(1, days + 1):
        day = scenario.month.replace(day=day_number)
        day_start = _dt(day, 5)
        night_start = _dt(day, 17)
        demands.append(DemandSpec(f"{day}-D", "D", day_start, day_start + timedelta(hours=12)))
        demands.append(DemandSpec(f"{day}-N", "N", night_start, night_start + timedelta(hours=12)))
    return tuple(demands)


def _absence(employee: str, kind: str, start: date, end: date | None = None) -> AvailabilitySpec:
    return AvailabilitySpec(employee, kind, start, end or start)


def _fixed_demand(
    employee: str, day: date, kind: str, *, state: str = "PLANNED", frozen: bool = True,
) -> FixedAssignmentSpec:
    start = _dt(day, 5 if kind == "D" else 17)
    demand_id = f"{day.isoformat()}-{kind}"
    return FixedAssignmentSpec(
        f"existing-{demand_id}-{employee}", employee, start,
        start + timedelta(hours=12), state, frozen, demand_id,
    )


def _window(
    employee: str, day: date, kind: str, *, active: bool = True,
    site_id: str = SITE_ID, start_delta_hours: int = 0, end_delta_hours: int = 0,
    allowed_shift_kind: str | None = None,
) -> ExternalWindowSpec:
    base = _dt(day, 5 if kind == "D" else 17)
    return ExternalWindowSpec(
        f"window-{employee}-{day}-{kind}-{active}-{site_id}-{start_delta_hours}-{end_delta_hours}-{allowed_shift_kind}",
        employee,
        base + timedelta(hours=start_delta_hours),
        base + timedelta(hours=12 + end_delta_hours),
        allowed_shift_kind if allowed_shift_kind is not None else kind,
        active,
        site_id,
    )


def _boundary_from_staff(
    month: date, day_staff: tuple[str, ...], night_staff: tuple[str, ...],
) -> tuple[FixedAssignmentSpec, ...]:
    assignments = []
    for index, offset in enumerate(range(-6, 0)):
        day = month + timedelta(days=offset)
        for kind, employee, hour in (("D", day_staff[index], 5), ("N", night_staff[index], 17)):
            start = _dt(day, hour)
            assignments.append(FixedAssignmentSpec(
                f"boundary-{day}-{kind}-{employee}", employee, start,
                start + timedelta(hours=12), "REALIZED", True, None,
            ))
    return tuple(assignments)


def standard_boundary(month: date) -> tuple[FixedAssignmentSpec, ...]:
    return _boundary_from_staff(
        month,
        ("C", "A", "B", "C", "D", "E"),
        ("D", "E", "D", "A", "B", "A"),
    )


def _load_boundary(month: date, e_day_count: int) -> tuple[FixedAssignmentSpec, ...]:
    if e_day_count == 4:
        day_staff = ("A", "A", "E", "E", "E", "E")
        night_staff = ("B", "B", "A", "A", "A", "B")
    elif e_day_count == 5:
        day_staff = ("A", "E", "E", "E", "E", "E")
        night_staff = ("B", "A", "A", "A", "A", "B")
    else:
        raise ValueError("e_day_count must be 4 or 5")
    return _boundary_from_staff(month, day_staff, night_staff)


def _base(
    case_id: str, month: date, *, seed: int, steps: tuple[int, ...],
    perturbations: tuple[str, ...] = (), **kwargs,
) -> ScenarioSpec:
    return ScenarioSpec(
        case_id=case_id, month=month, seed=seed, ladder_steps=steps,
        perturbations=perturbations, boundary_assignments=standard_boundary(month),
        external_support_enabled=True, **kwargs,
    )


def _baseline_october() -> ScenarioSpec:
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
        "reg-001-oct-2026", month, seed=1001, ladder_steps=(1,),
        perturbations=("literal ROTA-REG-001 availability", "A fixed PRIMARY on 2026-10-08 D"),
        availability=availability,
        fixed_demand_assignments=(_fixed_demand("A", date(2026, 10, 8), "D"),),
        external_support_enabled=False,
        declared_class=OracleClass.KNOWN_FEASIBLE,
        strict_monthly_hours=(("A", 156), ("B", 144), ("C", 156), ("D", 144), ("E", 144)),
        note="Literal five-person ROTA-REG-001 baseline; X/Y unavailable.",
    )


def _calendar_case(case_id: str, month: date, seed: int) -> ScenarioSpec:
    return _base(
        case_id, month, seed=seed, steps=(2, 3),
        perturbations=(f"clean {calendar.monthrange(month.year, month.month)[1]}-day month",),
        declared_class=OracleClass.KNOWN_FEASIBLE,
    )


def _replan_case() -> ScenarioSpec:
    month = date(2027, 1, 1)
    existing = (
        _fixed_demand("C", date(2027, 1, 1), "D", state="REALIZED", frozen=True),
        _fixed_demand("A", date(2027, 1, 1), "N", state="PLANNED", frozen=True),
        _fixed_demand("B", date(2027, 1, 2), "D", state="PLANNED", frozen=False),
    )
    return _base(
        "replan-realized-frozen-baseline", month, seed=4001, steps=(4,),
        perturbations=("REALIZED D fixed", "frozen N fixed", "redistributable PLANNED baseline"),
        fixed_demand_assignments=existing, declared_class=OracleClass.KNOWN_FEASIBLE,
    )


def _absence_ladder() -> tuple[ScenarioSpec, ...]:
    month = date(2027, 11, 1)
    day = date(2027, 11, 9)
    b_unavailable = _absence("B", "UNAVAILABLE_24H", day)
    a_off = _absence("A", "DAY_SHIFT_OFF", day)
    d_off = _absence("D", "DAY_SHIFT_OFF", day)
    e_off = _absence("E", "DAY_SHIFT_OFF", day)
    rows = ((), (b_unavailable,), (b_unavailable, a_off), (b_unavailable, a_off, d_off, e_off))
    cases = []
    for level, availability in enumerate(rows):
        cases.append(_base(
            f"absence-ladder-{level}", month, seed=5000 + level, steps=(5,),
            perturbations=(f"monotonic absence ladder level {level}",),
            series_id="absence-ladder", series_level=level,
            availability=availability,
            declared_class=OracleClass.PROVEN_STAFFING_SHORTAGE if level == 3 else None,
        ))
    return tuple(cases)


def _day_only_absence_case() -> ScenarioSpec:
    return _base(
        "absence-day-only-C", date(2027, 9, 1), seed=6001, steps=(6,),
        perturbations=("C DAY_ONLY unavailable on 2027-09-14",),
        availability=(_absence("C", "UNAVAILABLE_24H", date(2027, 9, 14)),),
    )


def _flexible_absence_case() -> ScenarioSpec:
    return _base(
        "absence-flexible-B", date(2027, 9, 1), seed=6002, steps=(6,),
        perturbations=("B flexible worker unavailable on 2027-09-14",),
        availability=(_absence("B", "UNAVAILABLE_24H", date(2027, 9, 14)),),
    )


def _hard_reshuffle_feasible() -> ScenarioSpec:
    return _base(
        "hard-reshuffle-still-feasible", date(2027, 4, 1), seed=7001, steps=(7,),
        perturbations=("A leave 8-10", "B unavailable 9-10", "C unavailable 10"),
        availability=(
            _absence("A", "LEAVE_GRANTED", date(2027, 4, 8), date(2027, 4, 10)),
            _absence("B", "UNAVAILABLE_24H", date(2027, 4, 9), date(2027, 4, 10)),
            _absence("C", "UNAVAILABLE_24H", date(2027, 4, 10)),
        ),
    )


def _load_decision_case() -> ScenarioSpec:
    month = date(2027, 3, 1)
    rules = tuple(
        RuleSpec(f"{employee}-N-only", "EMPLOYEE_ALLOWED_SHIFT_KINDS", employee, ("N",))
        for employee in ("A", "B", "D")
    )
    return _base(
        "load-decision-forced-72h", month, seed=8001, steps=(8,),
        perturbations=("C absent six days", "A/B/D N-only", "E forced to six D shifts"),
        availability=(_absence("C", "UNAVAILABLE_24H", date(2027, 3, 10), date(2027, 3, 15)),),
        site_rules=rules, declared_class=OracleClass.LOAD_DECISION_REQUIRED,
    )


def _simple_shortage_case() -> ScenarioSpec:
    day = date(2027, 6, 10)
    return _base(
        "simple-no-eligible-night", date(2027, 6, 1), seed=9001, steps=(9,),
        perturbations=("A/B/D/E DAY_SHIFT_OFF on 10 June; C is DAY_ONLY",),
        availability=tuple(_absence(e, "DAY_SHIFT_OFF", day) for e in ("A", "B", "D", "E")),
        declared_class=OracleClass.PROVEN_STAFFING_SHORTAGE,
    )


def _rest_boundary_case(case_id: str, gap_hours: int, seed: int) -> ScenarioSpec:
    month = date(2027, 8, 1)
    prior = month - timedelta(days=1)
    boundary = tuple(
        item for item in standard_boundary(month)
        if not (item.employee_id == "E" and item.start.date() == prior)
    )
    target_start = _dt(month, 5)
    context_end = target_start - timedelta(hours=gap_hours)
    context = FixedAssignmentSpec(
        f"other-site-{case_id}-E", "E", context_end - timedelta(hours=12),
        context_end, "REALIZED", True, None,
    )
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(10,),
        perturbations=(f"cross-site predecessor leaves exactly {gap_hours}h rest before day-1 D",),
        boundary_assignments=boundary,
        other_site_assignments=(context,),
        external_support_enabled=True,
        declared_class=OracleClass.KNOWN_FEASIBLE,
    )


def _load_boundary_case(case_id: str, e_history_days: int, expected: OracleClass, seed: int) -> ScenarioSpec:
    month = date(2027, 3, 1)
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(11,),
        perturbations=(f"E has {e_history_days * 12}h predecessor history", "E fixed on month day 1 D"),
        boundary_assignments=_load_boundary(month, e_history_days),
        fixed_demand_assignments=(_fixed_demand("E", month, "D"),),
        external_support_enabled=True, declared_class=expected,
    )


def _month_end_rest_case() -> ScenarioSpec:
    month = date(2027, 7, 1)
    last_day = date(2027, 7, 31)
    next_day = date(2027, 8, 1)
    future = FixedAssignmentSpec(
        "future-A-2027-08-01-D", "A", _dt(next_day, 5), _dt(next_day, 17),
        "PLANNED", True, None,
    )
    availability = tuple(_absence(e, "DAY_SHIFT_OFF", last_day) for e in ("B", "D", "E"))
    return ScenarioSpec(
        "month-end-N-vs-next-D", month, seed=12001, ladder_steps=(12,),
        perturbations=("A fixed next-month D", "B/D/E off on last-day starts", "C DAY_ONLY"),
        availability=availability,
        boundary_assignments=(*standard_boundary(month), future),
        external_support_enabled=False,
        declared_class=OracleClass.PROVEN_STAFFING_SHORTAGE,
    )


def _external_base(
    case_id: str, *, current_windows: tuple[ExternalWindowSpec, ...] = (),
    probe_windows: tuple[ExternalWindowSpec, ...] = (), enabled: bool = True,
    extra_availability: tuple[AvailabilitySpec, ...] = (), declared: OracleClass | None = None,
    seed: int,
) -> ScenarioSpec:
    month = date(2027, 5, 1)
    day = date(2027, 5, 12)
    shortage = tuple(_absence(e, "DAY_SHIFT_OFF", day) for e in ("A", "B", "D", "E"))
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(13, 14),
        perturbations=("local N shortage on 12 May", case_id),
        availability=(*shortage, *extra_availability),
        boundary_assignments=standard_boundary(month),
        external_windows=current_windows, external_probe_windows=probe_windows,
        external_support_enabled=enabled, declared_class=declared,
    )


def _external_cases() -> tuple[ScenarioSpec, ...]:
    day = date(2027, 5, 12)
    valid = _window("X", day, "N")
    return (
        _external_base(
            "external-before-confirmation", probe_windows=(valid,),
            declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=13001,
        ),
        _external_base(
            "external-after-confirmation", current_windows=(valid,),
            declared=OracleClass.KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT, seed=13002,
        ),
        _external_base(
            "external-window-wrong-employee", current_windows=(_window("Y", day, "N"),),
            probe_windows=(valid,), extra_availability=(_absence("Y", "DAY_SHIFT_OFF", day),),
            declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=14001,
        ),
        _external_base(
            "external-window-wrong-site", current_windows=(_window("X", day, "N", site_id="other-site"),),
            probe_windows=(valid,), declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=14002,
        ),
        _external_base(
            "external-window-inactive", current_windows=(_window("X", day, "N", active=False),),
            probe_windows=(valid,), declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=14003,
        ),
        _external_base(
            "external-window-partial", current_windows=(_window("X", day, "N", start_delta_hours=1),),
            probe_windows=(valid,), declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=14004,
        ),
        _external_base(
            "external-window-wrong-kind", current_windows=(_window("X", day, "N", allowed_shift_kind="D"),),
            probe_windows=(valid,), declared=OracleClass.EXTERNAL_SUPPORT_DECISION_REQUIRED, seed=14005,
        ),
        _external_base(
            "external-window-profile-disabled", current_windows=(valid,), probe_windows=(valid,),
            enabled=False, declared=OracleClass.PROVEN_STAFFING_SHORTAGE, seed=14006,
        ),
    )


def core_scenarios() -> tuple[ScenarioSpec, ...]:
    return (
        _baseline_october(),
        _calendar_case("calendar-28-feb-2027", date(2027, 2, 1), 2001),
        _calendar_case("calendar-29-feb-2028", date(2028, 2, 1), 2002),
        _calendar_case("calendar-30-apr-2027", date(2027, 4, 1), 2003),
        _calendar_case("calendar-31-jul-2027", date(2027, 7, 1), 2004),
        _replan_case(),
        *_absence_ladder(),
        _day_only_absence_case(),
        _flexible_absence_case(),
        _hard_reshuffle_feasible(),
        _load_decision_case(),
        _simple_shortage_case(),
        _rest_boundary_case("rest-boundary-exact-11h", 11, 10001),
        _rest_boundary_case("rest-boundary-below-11h", 10, 10002),
        _load_boundary_case("load-boundary-exact-60h", 4, OracleClass.KNOWN_FEASIBLE, 11001),
        _load_boundary_case("load-boundary-above-60h", 5, OracleClass.LOAD_DECISION_REQUIRED, 11002),
        _month_end_rest_case(),
        *_external_cases(),
    )


def calendar_scenarios() -> tuple[ScenarioSpec, ...]:
    scenarios = []
    year, month_number = 2027, 1
    for index in range(24):
        month = date(year, month_number, 1)
        scenarios.append(_calendar_case(f"calendar-sweep-{month.isoformat()}", month, 20000 + index))
        month_number += 1
        if month_number == 13:
            month_number = 1
            year += 1
    return tuple(scenarios)


def all_scenarios() -> tuple[ScenarioSpec, ...]:
    by_id = {scenario.case_id: scenario for scenario in (*core_scenarios(), *calendar_scenarios())}
    return tuple(by_id[key] for key in sorted(by_id))


if __name__ == "__main__":
    print(f"real_object_scenarios: {len(core_scenarios())} core cases")
