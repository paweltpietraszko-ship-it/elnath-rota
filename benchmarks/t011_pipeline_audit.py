"""Operational T011 A-E audit scenarios and lightweight schedule artifacts.

This is an audit harness, not a product export feature.  Business state is
created and read through ``rota.application.*``.  SVG/CSV/JSON files are a
small, deterministic projection of the FINAL snapshot after reopening the
SQLite store.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import tempfile
import time as _time
from dataclasses import dataclass, replace
from datetime import date, time
from html import escape
from pathlib import Path

from rota.application import (
    availability_matrix,
    balance_read,
    bootstrap,
    durable_inputs,
    lifecycle_ops,
    manual_edit,
    open_month,
    plan_ops,
    rule_decisions,
    store,
)
from rota.application.assembler import assemble_planning_state
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
)
from rota.planning.validator import validate

MONTH = date(2026, 10, 1)
QUARTER_MONTHS = (date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1))
COORDINATOR_ID = "COORD-T011-PIPELINE"
SITE_ID = "SITE-T011-PIPELINE"
PROFILE_ID = "PROFILE-T011-PIPELINE"
DAY_ONLY_EMPLOYEE = "FILIP"
DAY_ONLY_EXCEPTION_KIND = "EMPLOYEE_DAY_ONLY_N_EXCEPTION"


@dataclass(frozen=True)
class EmployeeInput:
    employee_id: str
    target_hours: int
    day_only: bool = False


@dataclass(frozen=True)
class AvailabilityInput:
    availability_id: str
    employee_id: str
    kind: AvailabilityKind
    start_date: date
    end_date: date
    note: str


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    employees: tuple[EmployeeInput, ...]
    availability: tuple[AvailabilityInput, ...]
    exception_window: tuple[date, date] | None
    expected_status: str
    require_exception_assignment: bool = False


@dataclass(frozen=True)
class ScenarioOutcome:
    name: str
    status: str
    plan_seconds: float
    assignments: tuple[Assignment, ...]
    employees: tuple[Employee, ...]
    availability: tuple
    warnings: tuple[str, ...]
    deviation_count: int
    quarter_balance_warnings: tuple[str, ...]
    blocking_demand_ids: tuple[str, ...]
    blockers: tuple[tuple[str, str], ...]
    unblocking_options: tuple[str, ...]


BASE_EMPLOYEES = (
    EmployeeInput("ANNA", 72),
    EmployeeInput("BARTEK", 120),
    EmployeeInput("CELINA", 132),
    EmployeeInput("DAMIAN", 132),
    EmployeeInput("EWA", 132),
    EmployeeInput(DAY_ONLY_EMPLOYEE, 156, day_only=True),
)

BASE_AVAILABILITY = (
    AvailabilityInput("AV-ANNA-LEAVE", "ANNA", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 5), date(2026, 10, 18), "14-day approved leave"),
    AvailabilityInput("AV-BARTEK-SICK", "BARTEK", AvailabilityKind.SICK_LEAVE, date(2026, 10, 10), date(2026, 10, 14), "5-day sick leave"),
    AvailabilityInput("AV-CELINA-D-OFF", "CELINA", AvailabilityKind.DAY_SHIFT_OFF, date(2026, 10, 7), date(2026, 10, 7), "day shift off; N remains allowed"),
    AvailabilityInput("AV-DAMIAN-D-OFF", "DAMIAN", AvailabilityKind.DAY_SHIFT_OFF, date(2026, 10, 20), date(2026, 10, 20), "day shift off; N remains allowed"),
    AvailabilityInput("AV-EWA-D-OFF", "EWA", AvailabilityKind.DAY_SHIFT_OFF, date(2026, 10, 27), date(2026, 10, 27), "day shift off; N remains allowed"),
)


def normal_spec() -> ScenarioSpec:
    return ScenarioSpec("normal_month", BASE_EMPLOYEES, BASE_AVAILABILITY, None, "FEASIBLE")


def boundary_spec() -> ScenarioSpec:
    extra = AvailabilityInput(
        "AV-EWA-SICK", "EWA", AvailabilityKind.SICK_LEAVE,
        date(2026, 10, 15), date(2026, 10, 21), "additional 7-day sick leave",
    )
    return ScenarioSpec(
        "boundary_month", BASE_EMPLOYEES, BASE_AVAILABILITY + (extra,),
        (date(2026, 10, 15), date(2026, 10, 21)), "FEASIBLE", True,
    )


def coordinator_wall_spec() -> ScenarioSpec:
    employees = (BASE_EMPLOYEES[0], BASE_EMPLOYEES[1], BASE_EMPLOYEES[-1])
    availability = (
        BASE_AVAILABILITY[0],
        AvailabilityInput(
            "AV-BARTEK-SICK-WALL", "BARTEK", AvailabilityKind.SICK_LEAVE,
            date(2026, 10, 14), date(2026, 10, 18), "overlaps leave; only one person remains",
        ),
    )
    return ScenarioSpec(
        "coordinator_wall", employees, availability,
        (date(2026, 10, 14), date(2026, 10, 18)), "DECISION_REQUIRED",
    )


def exception_retry_spec() -> ScenarioSpec:
    return ScenarioSpec(
        "exception_retry",
        (
            EmployeeInput("BARTEK", 156),
            EmployeeInput("CELINA", 156),
            EmployeeInput(DAY_ONLY_EMPLOYEE, 24, day_only=True),
        ),
        (
            AvailabilityInput(
                "AV-BARTEK-SICK-RETRY", "BARTEK", AvailabilityKind.SICK_LEAVE,
                date(2026, 10, 14), date(2026, 10, 14), "isolates the overnight exception boundary",
            ),
            AvailabilityInput(
                "AV-CELINA-SICK-RETRY", "CELINA", AvailabilityKind.SICK_LEAVE,
                date(2026, 10, 14), date(2026, 10, 14), "isolates the overnight exception boundary",
            ),
        ),
        (date(2026, 10, 14), date(2026, 10, 14)),
        "DECISION_REQUIRED",
    )


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID,
        display_name="T011 operational profile",
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(6), time(18), False, 1),
            StandardShift(ShiftKind.N, time(18), time(6), True, 1),
        ],
        day_only_blocks_n=True,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=60,
    )


def _night_only_profile() -> SiteProfile:
    return replace(
        _profile(),
        display_name="T011 retry-isolation profile",
        standard_shifts=[StandardShift(ShiftKind.N, time(18), time(6), True, 1)],
    )


def _bootstrap_and_roster(conn, spec: ScenarioSpec, profile: SiteProfile | None = None) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=SITE_ID,
        coordinator=Coordinator(COORDINATOR_ID, "Coordinator before rename", True),
        site_profile=profile or _profile(),
        site=Site(SITE_ID, PROFILE_ID, "Site before rename", True),
        association=CoordinatorSiteAssociation(COORDINATOR_ID, SITE_ID, True),
    )
    durable_inputs.update_coordinator(
        conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
        coordinator=Coordinator(COORDINATOR_ID, "Coordinator T011 operational audit", True),
    )
    durable_inputs.update_site(
        conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
        site=Site(SITE_ID, PROFILE_ID, "Site T011 operational audit", True),
    )
    for item in spec.employees:
        durable_inputs.update_employee(
            conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
            employee=Employee(item.employee_id, item.employee_id.title(), date(2020, 1, 1), None, item.day_only),
        )
        durable_inputs.update_membership(
            conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
            membership=SiteMembership(
                item.employee_id, SITE_ID, MembershipKind.LOCAL, True,
                ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            ),
        )
        for target_month in QUARTER_MONTHS:
            durable_inputs.set_target_hours(
                conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
                employee_id=item.employee_id, month=target_month, target_hours=item.target_hours,
            )
    for day_number in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        durable_inputs.set_calendar_day(
            conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID,
            day=CalendarDay(date(MONTH.year, MONTH.month, day_number), holiday=False),
        )


def _write_availability_and_exception(conn, spec: ScenarioSpec) -> None:
    for item in spec.availability:
        durable_inputs.append_availability(
            conn,
            coordinator_id=COORDINATOR_ID,
            site_id=SITE_ID,
            availability_id=item.availability_id,
            employee_id=item.employee_id,
            kind=item.kind,
            start_date=item.start_date,
            end_date=item.end_date,
            active=True,
            note=item.note,
        )
    if spec.exception_window is None:
        return
    start, end = spec.exception_window
    rule_decisions.record_structured_rule_decision(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=SITE_ID,
        rule_id=f"RULE-DAYONLY-N-{spec.name}",
        statement=f"Temporary N exception for {DAY_ONLY_EMPLOYEE}, {start} through {end}.",
        effective_from=start,
        rel=None,
        rule_content=rule_decisions.NewRuleContent(
            category=RuleCategory.CONFIRMED_EXCEPTION,
            rule_kind=DAY_ONLY_EXCEPTION_KIND,
            structured_parameters={"employee_id": DAY_ONLY_EMPLOYEE},
            enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED,
            effective_to=end,
            description="Temporary operational cover during sickness",
            source="owner-requested T011 integrated audit",
            reason="Seven-day staffing gap",
        ),
    )


def _correct_exception_start(conn, spec: ScenarioSpec, corrected_start: date) -> None:
    assert spec.exception_window is not None
    _old_start, end = spec.exception_window
    rule_decisions.record_structured_rule_decision(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=SITE_ID,
        rule_id=f"RULE-DAYONLY-N-{spec.name}",
        statement=f"Corrected N exception for {DAY_ONLY_EMPLOYEE}, {corrected_start} through {end}.",
        effective_from=corrected_start,
        rel="corrects",
        rule_content=rule_decisions.NewRuleContent(
            category=RuleCategory.CONFIRMED_EXCEPTION,
            rule_kind=DAY_ONLY_EXCEPTION_KIND,
            structured_parameters={"employee_id": DAY_ONLY_EMPLOYEE},
            enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED,
            effective_to=end,
            description="Corrected exception includes the preceding overnight shift start",
            source="owner-requested T011 retry audit",
            reason="The N shift covering the first unavailable hours starts one day earlier",
        ),
    )


def _assert_discovery_and_inputs(conn, spec: ScenarioSpec) -> None:
    assert bootstrap.month_plan_readiness(
        conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID, month=MONTH,
    ).ready
    assert {c.coordinator_id for c in bootstrap.active_coordinators(conn)} == {COORDINATOR_ID}
    assert {s.site_id for s in bootstrap.active_sites_for_coordinator(conn, coordinator_id=COORDINATOR_ID)} == {SITE_ID}
    for item in spec.availability:
        history = availability_matrix.availability_history(conn, availability_id=item.availability_id)
        assert len(history) == 1
        assert history[0].kind == item.kind
    if spec.exception_window:
        matrix = availability_matrix.employee_availability_matrix(
            conn, site_id=SITE_ID, employee_id=DAY_ONLY_EMPLOYEE, month=MONTH,
        )
        assert any(rule.rule_kind == DAY_ONLY_EXCEPTION_KIND for rule in matrix.weekday_and_exception_rules)


def _apply_valid_exception_swap(conn, spec: ScenarioSpec) -> None:
    assert spec.exception_window is not None
    start, end = spec.exception_window
    state, _ = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    assignments = list(state.existing_assignments)
    night_targets = [
        item for item in assignments
        if item.start_datetime.hour == 18 and start <= item.start_datetime.date() <= end
        and item.employee_id != DAY_ONLY_EMPLOYEE
    ]
    filip_assignments = [item for item in assignments if item.employee_id == DAY_ONLY_EMPLOYEE]
    for night in night_targets:
        for filip_current in filip_assignments:
            updates = (
                replace(night, employee_id=DAY_ONLY_EMPLOYEE),
                replace(filip_current, employee_id=night.employee_id),
            )
            by_id = {item.assignment_id: item for item in assignments}
            by_id.update({item.assignment_id: item for item in updates})
            if validate(state, list(by_id.values())).hard_pass:
                manual_edit.apply_manual_correction(
                    conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID,
                    effective_from=MONTH, upsert_assignments=list(updates),
                )
                return
    raise AssertionError("no HARD-valid manual swap could exercise the dated day-only N exception")


def _finalize_and_restart(conn, db_path: Path, candidate: list[Assignment], spec: ScenarioSpec):
    state, _ = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    assert validate(state, candidate).hard_pass
    plan_ops.select_candidate(
        conn, site_id=SITE_ID, month=MONTH, candidate=candidate, coordinator_id=COORDINATOR_ID,
    )
    if spec.require_exception_assignment:
        _apply_valid_exception_swap(conn, spec)
    lifecycle_ops.revalidate(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID)
    state, warnings = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    deviations = {deviation.deviation_id for deviation in state.deviations}
    lifecycle_ops.finalize(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID,
        acknowledged_deviation_ids=deviations,
        reason="T011 integrated operational audit",
    )
    before_view = open_month.open_month(conn, site_id=SITE_ID, month=MONTH)
    before_state, _ = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    conn.close()
    reopened = store.open_store(db_path)
    after_view = open_month.open_month(reopened, site_id=SITE_ID, month=MONTH)
    after_state, after_warnings = assemble_planning_state(reopened, site_id=SITE_ID, month=MONTH)
    assert after_view == before_view
    assert after_state.existing_assignments == before_state.existing_assignments
    return reopened, after_view, after_state, tuple(warnings) + tuple(after_warnings)


def _decision_outcome(spec: ScenarioSpec, result, elapsed: float) -> ScenarioOutcome:
    payload = result.decision_payload
    assert payload is not None
    return ScenarioOutcome(
        name=spec.name,
        status=result.status,
        plan_seconds=elapsed,
        assignments=(),
        employees=tuple(Employee(e.employee_id, e.employee_id.title(), date(2020, 1, 1), None, e.day_only) for e in spec.employees),
        availability=spec.availability,
        warnings=tuple(result.warnings),
        deviation_count=0,
        quarter_balance_warnings=(),
        blocking_demand_ids=tuple(item.demand_id for item in payload.blocking_shift_demands),
        blockers=tuple((item.employee_id, item.condition) for item in payload.blockers),
        unblocking_options=tuple(payload.unblocking_options),
    )


def run_scenario(spec: ScenarioSpec, db_path: Path) -> ScenarioOutcome:
    conn = store.open_store(db_path)
    _bootstrap_and_roster(conn, spec)
    _write_availability_and_exception(conn, spec)
    _assert_discovery_and_inputs(conn, spec)
    started = _time.perf_counter()
    result = plan_ops.plan_month(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID, effective_from=MONTH,
    )
    elapsed = _time.perf_counter() - started
    assert result.status == spec.expected_status
    if result.status != "FEASIBLE":
        assert result.candidates == []
        outcome = _decision_outcome(spec, result, elapsed)
        conn.close()
        return outcome

    assert result.candidates
    reopened, view, state, warnings = _finalize_and_restart(conn, db_path, result.candidates[0], spec)
    assert view.current_version is not None
    assert view.current_version.status.value.startswith("FINAL")
    assert open_month.months_with_schedule(reopened, site_id=SITE_ID) == (MONTH,)
    quarter_warnings: list[str] = []
    for item in spec.employees:
        balances, employee_warnings = balance_read.quarter_balance(
            reopened, employee_id=item.employee_id, quarter_first_month=MONTH,
        )
        assert len(balances) == 3
        assert balances[0].planned_hours == sum(
            int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
            for assignment in state.existing_assignments
            if assignment.employee_id == item.employee_id and assignment.role == AssignmentRole.PRIMARY
        )
        quarter_warnings.extend(employee_warnings)
    outcome = ScenarioOutcome(
        name=spec.name,
        status=result.status,
        plan_seconds=elapsed,
        assignments=tuple(state.existing_assignments),
        employees=tuple(view.employees),
        availability=tuple(view.availability_records),
        warnings=warnings + tuple(result.warnings),
        deviation_count=len(state.deviations),
        quarter_balance_warnings=tuple(quarter_warnings),
        blocking_demand_ids=(),
        blockers=(),
        unblocking_options=(),
    )
    reopened.close()
    return outcome


def _run_exception_retry(
    spec: ScenarioSpec, db_path: Path, *, outcome_prefix: str, profile: SiteProfile | None = None,
) -> tuple[ScenarioOutcome, ScenarioOutcome]:
    """Retry PLAN on the same empty WORKING after correcting the dated rule."""
    conn = store.open_store(db_path)
    _bootstrap_and_roster(conn, spec, profile)
    _write_availability_and_exception(conn, spec)
    _assert_discovery_and_inputs(conn, spec)

    started = _time.perf_counter()
    first = plan_ops.plan_month(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID, effective_from=MONTH,
    )
    first_elapsed = _time.perf_counter() - started
    assert first.status == "DECISION_REQUIRED"
    before = replace(_decision_outcome(spec, first, first_elapsed), name=f"{outcome_prefix}_before")
    working = open_month.open_month(conn, site_id=SITE_ID, month=MONTH).current_version
    assert working is not None
    working_id = working.version_id

    _correct_exception_start(conn, spec, date(2026, 10, 13))
    started = _time.perf_counter()
    second = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORDINATOR_ID)
    second_elapsed = _time.perf_counter() - started
    retried = open_month.open_month(conn, site_id=SITE_ID, month=MONTH).current_version
    assert retried is not None
    assert retried.version_id == working_id
    if second.status != "FEASIBLE":
        after = replace(_decision_outcome(spec, second, second_elapsed), name=f"{outcome_prefix}_after")
        conn.close()
        return before, after

    assert second.candidates
    reopened, view, state, warnings = _finalize_and_restart(conn, db_path, second.candidates[0], spec)
    after = ScenarioOutcome(
        name=f"{outcome_prefix}_after",
        status=second.status,
        plan_seconds=second_elapsed,
        assignments=tuple(state.existing_assignments),
        employees=tuple(view.employees),
        availability=tuple(view.availability_records),
        warnings=warnings + tuple(second.warnings),
        deviation_count=len(state.deviations),
        quarter_balance_warnings=(),
        blocking_demand_ids=(),
        blockers=(),
        unblocking_options=(),
    )
    reopened.close()
    return before, after


def run_exception_retry(db_path: Path) -> tuple[ScenarioOutcome, ScenarioOutcome]:
    return _run_exception_retry(
        exception_retry_spec(), db_path,
        outcome_prefix="exception_retry", profile=_night_only_profile(),
    )


def run_coordinator_wall_retry(db_path: Path) -> tuple[ScenarioOutcome, ScenarioOutcome]:
    return _run_exception_retry(
        coordinator_wall_spec(), db_path, outcome_prefix="coordinator_wall_retry",
    )


def _assignment_kind(assignment: Assignment) -> str:
    return "D" if assignment.start_datetime.hour == 6 else "N"


def _availability_marker(kind: AvailabilityKind) -> str:
    return {
        AvailabilityKind.LEAVE_GRANTED: "U",
        AvailabilityKind.SICK_LEAVE: "L4",
        AvailabilityKind.DAY_SHIFT_OFF: "D-OFF",
        AvailabilityKind.UNAVAILABLE_24H: "X",
        AvailabilityKind.LEAVE_PLAN: "UP",
    }[kind]


def schedule_cells(outcome: ScenarioOutcome) -> dict[tuple[str, int], str]:
    cells: dict[tuple[str, int], list[str]] = {}
    for record in outcome.availability:
        for day_number in range(record.start_date.day, record.end_date.day + 1):
            cells.setdefault((record.employee_id, day_number), []).append(_availability_marker(record.kind))
    for assignment in outcome.assignments:
        if assignment.role != AssignmentRole.PRIMARY or assignment.state == AssignmentState.CANCELLED:
            continue
        cells.setdefault((assignment.employee_id, assignment.start_datetime.day), []).insert(0, _assignment_kind(assignment))
    return {key: "/".join(value) for key, value in cells.items()}


def write_csv(outcome: ScenarioOutcome, path: Path) -> None:
    cells = schedule_cells(outcome)
    days = range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["employee"] + [f"{day:02d}" for day in days])
        for employee in outcome.employees:
            writer.writerow([employee.display_name] + [cells.get((employee.employee_id, day), "") for day in days])


def write_svg(outcome: ScenarioOutcome, path: Path) -> None:
    cells = schedule_cells(outcome)
    days = list(range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1))
    cell_width, row_height, label_width = 34, 28, 120
    width = label_width + cell_width * len(days) + 20
    height = 100 + row_height * (len(outcome.employees) + 1)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;font-size:11px}.title{font-size:16px;font-weight:bold}.small{font-size:10px}</style>',
        f'<text x="10" y="22" class="title">{escape(outcome.name)} — October 2026</text>',
        f'<text x="10" y="42" class="small">status={escape(outcome.status)}, PLAN={outcome.plan_seconds:.3f}s, legend: D day, N night, U leave, L4 sick, D-OFF no day shift</text>',
    ]
    top = 60
    for index, day_number in enumerate(days):
        x = label_width + index * cell_width
        lines.append(f'<rect x="{x}" y="{top}" width="{cell_width}" height="{row_height}" fill="#eeeeee" stroke="#bbbbbb"/>')
        lines.append(f'<text x="{x + cell_width / 2}" y="{top + 18}" text-anchor="middle">{day_number}</text>')
    for row, employee in enumerate(outcome.employees, start=1):
        y = top + row * row_height
        lines.append(f'<text x="5" y="{y + 18}">{escape(employee.display_name)}</text>')
        for index, day_number in enumerate(days):
            value = cells.get((employee.employee_id, day_number), "")
            base = value.split("/", 1)[0]
            fill = {"D": "#fff2a8", "N": "#b9d7ff", "U": "#c9efc7", "L4": "#ffc6c6", "D-OFF": "#e7d4ff"}.get(base, "#ffffff")
            x = label_width + index * cell_width
            lines.append(f'<rect x="{x}" y="{y}" width="{cell_width}" height="{row_height}" fill="{fill}" stroke="#cccccc"/>')
            if value:
                lines.append(f'<text x="{x + cell_width / 2}" y="{y + 18}" text-anchor="middle" class="small">{escape(value)}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(outcome: ScenarioOutcome, path: Path) -> None:
    worked_hours: dict[str, int] = {}
    for assignment in outcome.assignments:
        if assignment.role != AssignmentRole.PRIMARY or assignment.state == AssignmentState.CANCELLED:
            continue
        hours = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        worked_hours[assignment.employee_id] = worked_hours.get(assignment.employee_id, 0) + hours
    payload = {
        "scenario": outcome.name,
        "status": outcome.status,
        "plan_seconds": round(outcome.plan_seconds, 6),
        "assignment_count": len(outcome.assignments),
        "worked_hours": worked_hours,
        "deviation_count": outcome.deviation_count,
        "warnings": list(outcome.warnings),
        "quarter_balance_warnings": list(outcome.quarter_balance_warnings),
        "blocking_demand_ids": list(outcome.blocking_demand_ids),
        "blockers": [{"employee_id": employee_id, "condition": condition} for employee_id, condition in outcome.blockers],
        "unblocking_options": list(outcome.unblocking_options),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_artifacts(outcome: ScenarioOutcome, output_dir: Path) -> tuple[Path, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = output_dir / f"{outcome.name}.json"
    write_summary(outcome, summary)
    paths: list[Path] = [summary]
    if outcome.assignments:
        csv_path = output_dir / f"{outcome.name}.csv"
        svg_path = output_dir / f"{outcome.name}.svg"
        write_csv(outcome, csv_path)
        write_svg(outcome, svg_path)
        paths.extend((csv_path, svg_path))
    return tuple(paths)


def run_all(output_dir: Path) -> dict[str, ScenarioOutcome]:
    outcomes: dict[str, ScenarioOutcome] = {}
    with tempfile.TemporaryDirectory(prefix="t011-pipeline-") as temp_dir:
        for spec in (normal_spec(), boundary_spec(), coordinator_wall_spec()):
            outcome = run_scenario(spec, Path(temp_dir) / f"{spec.name}.db")
            outcomes[spec.name] = outcome
            write_artifacts(outcome, output_dir)
        before, after = run_exception_retry(Path(temp_dir) / "exception_retry.db")
        for outcome in (before, after):
            outcomes[outcome.name] = outcome
            write_artifacts(outcome, output_dir)
        before, after = run_coordinator_wall_retry(Path(temp_dir) / "coordinator_wall_retry.db")
        for outcome in (before, after):
            outcomes[outcome.name] = outcome
            write_artifacts(outcome, output_dir)
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/t011_pipeline"))
    args = parser.parse_args()
    outcomes = run_all(args.output_dir)
    for outcome in outcomes.values():
        print(f"{outcome.name}: {outcome.status}, assignments={len(outcome.assignments)}, PLAN={outcome.plan_seconds:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
