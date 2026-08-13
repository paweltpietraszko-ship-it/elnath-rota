"""Deterministic scenario catalog for the real-object benchmark."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from benchmarks.real_object_types import (
    AvailabilitySpec, DemandSpec, ExpectedStatus, ExpectationKind,
    ExternalWindowSpec, FixedAssignmentSpec, RuleSpec, ScenarioSpec,
)

LOCAL_EMPLOYEES = ("A", "B", "C", "D", "E")
EXTERNAL_EMPLOYEES = ("X", "Y")
SITE_ID = "real-object"
LOAD_LIMIT_HOURS = 60
REST_MIN_HOURS = 11


def _dt(day: date, hour: int) -> datetime:
    return datetime(day.year, day.month, day.day, hour)


def demands_for_month(scenario: ScenarioSpec) -> tuple[DemandSpec, ...]:
    rows = []
    for number in range(1, calendar.monthrange(scenario.month.year, scenario.month.month)[1] + 1):
        day = scenario.month.replace(day=number)
        for kind, hour in (("D", 5), ("N", 17)):
            start = _dt(day, hour)
            rows.append(DemandSpec(f"{day}-{kind}", kind, start, start + timedelta(hours=12)))
    return tuple(rows)


def _absence(employee: str, kind: str, start: date, end: date | None = None) -> AvailabilitySpec:
    return AvailabilitySpec(employee, kind, start, end or start)


def _fixed_demand(
    employee: str, day: date, kind: str, *, state: str = "PLANNED", frozen: bool = True,
) -> FixedAssignmentSpec:
    start = _dt(day, 5 if kind == "D" else 17)
    demand_id = f"{day}-{kind}"
    return FixedAssignmentSpec(
        f"existing-{demand_id}-{employee}", employee, start, start + timedelta(hours=12),
        state, frozen, demand_id,
    )


def _window(
    employee: str, day: date, kind: str, *, active: bool = True, site_id: str = SITE_ID,
    start_delta_hours: int = 0, end_delta_hours: int = 0,
    allowed_shift_kind: str | None = None,
) -> ExternalWindowSpec:
    base = _dt(day, 5 if kind == "D" else 17)
    return ExternalWindowSpec(
        f"window-{employee}-{day}-{kind}-{active}-{site_id}-{start_delta_hours}-{end_delta_hours}-{allowed_shift_kind}",
        employee, base + timedelta(hours=start_delta_hours),
        base + timedelta(hours=12 + end_delta_hours),
        allowed_shift_kind if allowed_shift_kind is not None else kind, active, site_id,
    )


def _boundary_from_staff(
    month: date, day_staff: tuple[str, ...], night_staff: tuple[str, ...],
) -> tuple[FixedAssignmentSpec, ...]:
    rows = []
    for index, offset in enumerate(range(-6, 0)):
        day = month + timedelta(days=offset)
        for kind, employee, hour in (("D", day_staff[index], 5), ("N", night_staff[index], 17)):
            start = _dt(day, hour)
            rows.append(FixedAssignmentSpec(
                f"boundary-{day}-{kind}-{employee}", employee, start,
                start + timedelta(hours=12), "REALIZED", True, None,
            ))
    return tuple(rows)


def standard_boundary(month: date) -> tuple[FixedAssignmentSpec, ...]:
    return _boundary_from_staff(
        month, ("C", "A", "B", "C", "D", "E"), ("D", "E", "D", "A", "B", "A"),
    )


def _load_boundary(month: date, e_days: int) -> tuple[FixedAssignmentSpec, ...]:
    if e_days == 4:
        return _boundary_from_staff(
            month, ("A", "A", "E", "E", "E", "E"), ("B", "B", "A", "A", "A", "B"),
        )
    if e_days == 5:
        return _boundary_from_staff(
            month, ("A", "E", "E", "E", "E", "E"), ("B", "A", "A", "A", "A", "B"),
        )
    raise ValueError("e_days must be 4 or 5")


def _base(
    case_id: str, month: date, *, seed: int, steps: tuple[int, ...],
    expected_status: ExpectedStatus, reason: str,
    expectation_kind: ExpectationKind = ExpectationKind.FEASIBLE,
    perturbations: tuple[str, ...] = (), external_support_enabled: bool = True, **kwargs,
) -> ScenarioSpec:
    return ScenarioSpec(
        case_id=case_id, month=month, seed=seed, ladder_steps=steps,
        perturbations=perturbations, boundary_assignments=standard_boundary(month),
        external_support_enabled=external_support_enabled, expected_status=expected_status,
        expectation_kind=expectation_kind, expectation_reason=reason, **kwargs,
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
        strict_monthly_hours=(("A", 156), ("B", 144), ("C", 156), ("D", 144), ("E", 144)),
        expected_status=ExpectedStatus.FEASIBLE, expectation_kind=ExpectationKind.FEASIBLE,
        expectation_reason="Frozen five-person ROTA-REG-001 has a known legal schedule.",
        note="Literal five-person baseline; X/Y unavailable.",
    )


def _calendar_case(case_id: str, month: date, seed: int) -> ScenarioSpec:
    days = calendar.monthrange(month.year, month.month)[1]
    return _base(
        case_id, month, seed=seed, steps=(2, 3), expected_status=ExpectedStatus.FEASIBLE,
        reason=f"Clean {days}-day month with five local workers and legal six-day history.",
        perturbations=(f"clean {days}-day month",),
    )


def _replan_case(
    case_id: str, expected: int, unavailable: tuple[AvailabilitySpec, ...],
    baseline: tuple[FixedAssignmentSpec, ...], seed: int,
) -> ScenarioSpec:
    return _base(
        case_id, date(2027, 1, 1), seed=seed, steps=(4,),
        expected_status=ExpectedStatus.FEASIBLE, expectation_kind=ExpectationKind.REPLAN,
        reason=f"Exactly {expected} redistributable baseline placement(s) are forced to change.",
        perturbations=(f"known minimum reshuffle count {expected}",), availability=unavailable,
        fixed_demand_assignments=baseline, expected_reshuffles=expected,
    )


def _replan_cases() -> tuple[ScenarioSpec, ...]:
    return (
        _replan_case(
            "replan-min-0", 0, (),
            (_fixed_demand("B", date(2027, 1, 5), "D", frozen=False),), 4000,
        ),
        _replan_case(
            "replan-min-1", 1, (_absence("B", "DAY_SHIFT_OFF", date(2027, 1, 5)),),
            (_fixed_demand("B", date(2027, 1, 5), "D", frozen=False),), 4001,
        ),
        _replan_case(
            "replan-min-2", 2, (
                _absence("B", "DAY_SHIFT_OFF", date(2027, 1, 5)),
                _absence("D", "DAY_SHIFT_OFF", date(2027, 1, 8)),
            ), (
                _fixed_demand("B", date(2027, 1, 5), "D", frozen=False),
                _fixed_demand("D", date(2027, 1, 8), "N", frozen=False),
            ), 4002,
        ),
    )


def _absence_ladder() -> tuple[ScenarioSpec, ...]:
    month, day = date(2027, 11, 1), date(2027, 11, 9)
    rows = (
        (),
        (_absence("B", "UNAVAILABLE_24H", day),),
        (_absence("B", "UNAVAILABLE_24H", day), _absence("A", "DAY_SHIFT_OFF", day)),
        (
            _absence("B", "UNAVAILABLE_24H", day), _absence("A", "DAY_SHIFT_OFF", day),
            _absence("D", "DAY_SHIFT_OFF", day), _absence("E", "DAY_SHIFT_OFF", day),
        ),
    )
    cases = []
    for level, availability in enumerate(rows):
        shortage = level == 3
        cases.append(_base(
            f"absence-ladder-{level}", month, seed=5000 + level, steps=(5,),
            expected_status=ExpectedStatus.DECISION_REQUIRED if shortage else ExpectedStatus.FEASIBLE,
            expectation_kind=ExpectationKind.SIMPLE_SHORTAGE if shortage else ExpectationKind.FEASIBLE,
            reason=(
                "9 Nov N has no eligible worker after cumulative absences."
                if shortage else f"Cumulative absence level {level} still leaves a legal schedule."
            ),
            perturbations=(f"monotonic absence ladder level {level}",),
            series_id="absence-ladder", series_level=level, availability=availability,
            expected_demand_ids=(f"{day}-N",) if shortage else (),
        ))
    return tuple(cases)


def _ordinary_feasible_cases() -> tuple[ScenarioSpec, ...]:
    return (
        _base(
            "absence-day-only-C", date(2027, 9, 1), seed=6001, steps=(6,),
            expected_status=ExpectedStatus.FEASIBLE,
            reason="One-day absence of DAY_ONLY C still leaves sufficient local coverage.",
            perturbations=("C unavailable on 2027-09-14",),
            availability=(_absence("C", "UNAVAILABLE_24H", date(2027, 9, 14)),),
        ),
        _base(
            "absence-flexible-B", date(2027, 9, 1), seed=6002, steps=(6,),
            expected_status=ExpectedStatus.FEASIBLE,
            reason="One-day absence of flexible worker B still leaves sufficient local coverage.",
            perturbations=("B unavailable on 2027-09-14",),
            availability=(_absence("B", "UNAVAILABLE_24H", date(2027, 9, 14)),),
        ),
        _base(
            "hard-reshuffle-still-feasible", date(2027, 4, 1), seed=7001, steps=(7,),
            expected_status=ExpectedStatus.FEASIBLE,
            reason="Overlapping local absences are hard but still leave a legal schedule <=60h/7d.",
            perturbations=("A leave 8-10", "B unavailable 9-10", "C unavailable 10"),
            availability=(
                _absence("A", "LEAVE_GRANTED", date(2027, 4, 8), date(2027, 4, 10)),
                _absence("B", "UNAVAILABLE_24H", date(2027, 4, 9), date(2027, 4, 10)),
                _absence("C", "UNAVAILABLE_24H", date(2027, 4, 10)),
            ),
        ),
    )


def _load_decision_case() -> ScenarioSpec:
    month = date(2027, 3, 1)
    forced_days = tuple(date(2027, 3, number) for number in range(10, 16))
    rules = tuple(
        RuleSpec(f"{employee}-N-only", "EMPLOYEE_ALLOWED_SHIFT_KINDS", employee, ("N",))
        for employee in ("A", "B", "D")
    )
    return _base(
        "load-decision-forced-72h", month, seed=8001, steps=(8,),
        expected_status=ExpectedStatus.DECISION_REQUIRED,
        expectation_kind=ExpectationKind.FORCED_LOAD,
        reason="Six consecutive D shifts are forced to E, yielding 72h inside seven days.",
        perturbations=("C absent six days", "A/B/D N-only", "E forced to six D shifts"),
        availability=(_absence("C", "UNAVAILABLE_24H", forced_days[0], forced_days[-1]),),
        site_rules=rules, expected_demand_ids=tuple(f"{day}-D" for day in forced_days),
        expected_employee_id="E",
    )


def _simple_shortage_case() -> ScenarioSpec:
    day = date(2027, 6, 10)
    return _base(
        "simple-no-eligible-night", date(2027, 6, 1), seed=9001, steps=(9,),
        expected_status=ExpectedStatus.DECISION_REQUIRED,
        expectation_kind=ExpectationKind.SIMPLE_SHORTAGE,
        reason="A/B/D/E are off for the N start and C is DAY_ONLY; X/Y have no window.",
        perturbations=("no eligible worker for 10 June N",),
        availability=tuple(_absence(e, "DAY_SHIFT_OFF", day) for e in ("A", "B", "D", "E")),
        expected_demand_ids=(f"{day}-N",),
    )


def _rest_boundary_case(case_id: str, gap: int, seed: int) -> ScenarioSpec:
    month, prior = date(2027, 8, 1), date(2027, 7, 31)
    boundary = tuple(
        item for item in standard_boundary(month)
        if not (item.employee_id == "E" and item.start.date() == prior)
    )
    target = _dt(month, 5)
    context_end = target - timedelta(hours=gap)
    context = FixedAssignmentSpec(
        f"other-site-{case_id}-E", "E", context_end - timedelta(hours=12),
        context_end, "REALIZED", True, None,
    )
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(10,),
        perturbations=(f"cross-site predecessor leaves {gap}h rest before day-1 D",),
        boundary_assignments=boundary, other_site_assignments=(context,),
        external_support_enabled=True, expected_status=ExpectedStatus.FEASIBLE,
        expectation_kind=ExpectationKind.FEASIBLE,
        expectation_reason="Month is schedulable; independent checker enforces cross-site REST.",
    )


def _rest_pair_shortage_case() -> ScenarioSpec:
    month, day = date(2027, 9, 1), date(2027, 9, 13)
    return _base(
        "rest-pair-only-A", month, seed=10003, steps=(10,),
        expected_status=ExpectedStatus.DECISION_REQUIRED,
        expectation_kind=ExpectationKind.REST_PAIR_SHORTAGE,
        reason="Both D and N on 13 Sep have only A eligible; A cannot work both with REST-01.",
        perturbations=("only A eligible for same-day D and N",),
        availability=tuple(_absence(e, "DAY_SHIFT_OFF", day) for e in ("B", "C", "D", "E")),
        external_support_enabled=False, expected_demand_ids=(f"{day}-D", f"{day}-N"),
        expected_employee_id="A",
    )


def _load_boundary_case(
    case_id: str, e_days: int, expected: ExpectedStatus, seed: int,
) -> ScenarioSpec:
    month = date(2027, 3, 1)
    hours = (e_days + 1) * 12
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(11,),
        perturbations=(f"E has {e_days * 12}h predecessor history", "E fixed on month day 1 D"),
        boundary_assignments=_load_boundary(month, e_days),
        fixed_demand_assignments=(_fixed_demand("E", month, "D"),),
        external_support_enabled=True, expected_status=expected,
        expectation_kind=ExpectationKind.FIXED_LOAD,
        expectation_reason=f"Known E history plus fixed day-1 D gives {hours}h in a rolling window.",
        expected_employee_id="E",
    )


def _month_end_rest_case() -> ScenarioSpec:
    month, last_day, next_day = date(2027, 7, 1), date(2027, 7, 31), date(2027, 8, 1)
    future = FixedAssignmentSpec(
        "future-A-2027-08-01-D", "A", _dt(next_day, 5), _dt(next_day, 17),
        "PLANNED", True, None,
    )
    return ScenarioSpec(
        "month-end-N-vs-next-D", month, seed=12001, ladder_steps=(12,),
        perturbations=("A fixed next-month D", "B/D/E off on last-day starts", "C DAY_ONLY"),
        availability=tuple(_absence(e, "DAY_SHIFT_OFF", last_day) for e in ("B", "D", "E")),
        boundary_assignments=(*standard_boundary(month), future), external_support_enabled=False,
        expected_status=ExpectedStatus.DECISION_REQUIRED,
        expectation_kind=ExpectationKind.SIMPLE_SHORTAGE,
        expectation_reason="31 Jul N has no eligible worker after next-month REST context.",
        expected_demand_ids=(f"{last_day}-N",),
    )


def _external_base(
    case_id: str, *, current: tuple[ExternalWindowSpec, ...] = (),
    probe: tuple[ExternalWindowSpec, ...] = (), enabled: bool = True,
    extra_availability: tuple[AvailabilitySpec, ...] = (), expected: ExpectedStatus,
    kind: ExpectationKind, reason: str, seed: int,
) -> ScenarioSpec:
    month, day = date(2027, 5, 1), date(2027, 5, 12)
    shortage = tuple(_absence(e, "DAY_SHIFT_OFF", day) for e in ("A", "B", "D", "E"))
    return ScenarioSpec(
        case_id, month, seed=seed, ladder_steps=(13, 14),
        perturbations=("local N shortage on 12 May", case_id),
        availability=(*shortage, *extra_availability), boundary_assignments=standard_boundary(month),
        external_windows=current, external_probe_windows=probe, external_support_enabled=enabled,
        expected_status=expected, expectation_kind=kind, expectation_reason=reason,
        expected_demand_ids=(f"{day}-N",), expected_employee_id="X",
    )


def _external_cases() -> tuple[ScenarioSpec, ...]:
    day = date(2027, 5, 12)
    valid = _window("X", day, "N")
    before = "No local worker can cover 12 May N; X becomes eligible only with the probe window."
    rows = [
        ("external-before-confirmation", (), (valid,), True, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 13001),
        ("external-after-confirmation", (valid,), (), True, (), ExpectedStatus.FEASIBLE, ExpectationKind.EXTERNAL_AFTER, "Confirmed X window resolves 12 May N.", 13002),
        ("external-window-wrong-employee", (_window("Y", day, "N"),), (valid,), True, (_absence("Y", "DAY_SHIFT_OFF", day),), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 14001),
        ("external-window-wrong-site", (_window("X", day, "N", site_id="other-site"),), (valid,), True, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 14002),
        ("external-window-inactive", (_window("X", day, "N", active=False),), (valid,), True, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 14003),
        ("external-window-partial", (_window("X", day, "N", start_delta_hours=1),), (valid,), True, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 14004),
        ("external-window-wrong-kind", (_window("X", day, "N", allowed_shift_kind="D"),), (valid,), True, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.EXTERNAL_BEFORE, before, 14005),
        ("external-window-profile-disabled", (valid,), (), False, (), ExpectedStatus.DECISION_REQUIRED, ExpectationKind.SIMPLE_SHORTAGE, "Profile disables X/Y, so the valid window cannot supply 12 May N.", 14006),
    ]
    return tuple(
        _external_base(
            case_id, current=current, probe=probe, enabled=enabled,
            extra_availability=extra, expected=expected, kind=kind, reason=reason, seed=seed,
        )
        for case_id, current, probe, enabled, extra, expected, kind, reason, seed in rows
    )


def core_scenarios() -> tuple[ScenarioSpec, ...]:
    return (
        _baseline_october(),
        _calendar_case("calendar-28-feb-2027", date(2027, 2, 1), 2001),
        _calendar_case("calendar-29-feb-2028", date(2028, 2, 1), 2002),
        _calendar_case("calendar-30-apr-2027", date(2027, 4, 1), 2003),
        _calendar_case("calendar-31-jul-2027", date(2027, 7, 1), 2004),
        *_replan_cases(), *_absence_ladder(), *_ordinary_feasible_cases(),
        _load_decision_case(), _simple_shortage_case(),
        _rest_boundary_case("rest-boundary-exact-11h", 11, 10001),
        _rest_boundary_case("rest-boundary-below-11h", 10, 10002),
        _rest_pair_shortage_case(),
        _load_boundary_case("load-boundary-exact-60h", 4, ExpectedStatus.FEASIBLE, 11001),
        _load_boundary_case("load-boundary-above-60h", 5, ExpectedStatus.DECISION_REQUIRED, 11002),
        _month_end_rest_case(), *_external_cases(),
    )


def calendar_scenarios() -> tuple[ScenarioSpec, ...]:
    rows = []
    year, month_number = 2027, 1
    for index in range(24):
        month = date(year, month_number, 1)
        rows.append(_calendar_case(f"calendar-sweep-{month}", month, 20000 + index))
        month_number += 1
        if month_number == 13:
            month_number, year = 1, year + 1
    return tuple(rows)


def all_scenarios() -> tuple[ScenarioSpec, ...]:
    by_id = {s.case_id: s for s in (*core_scenarios(), *calendar_scenarios())}
    return tuple(by_id[key] for key in sorted(by_id))


if __name__ == "__main__":
    print(f"real_object_scenarios: {len(core_scenarios())} core cases")
