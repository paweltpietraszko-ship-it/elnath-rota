"""Deterministic coordinator/solver scenario lab (ROTA-T028)."""
from __future__ import annotations
import argparse
import calendar
import json
import random
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from rota.application.assembler import assemble_planning_state
from rota.application.bootstrap import bootstrap_or_resume_coordinator_context
from rota.application.durable_inputs import (
    add_external_support_window,
    append_availability,
    set_calendar_day,
    set_target_hours,
    update_employee,
    update_membership,
    update_site_profile,
)
from rota.application.plan_ops import plan_month, replan, select_candidate
from rota.application.rule_decisions import (
    create_employee_shift_unavailability,
    create_employee_weekday_unavailability,
)
from rota.domain import (
    Assignment,
    AssignmentRole,
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_schedule_snapshot
from rota.planning.shift_catalog import validate_standard_shift
from rota.planning.validator import validate

DEFAULT_SEED = 20260824
DEFAULT_OUTPUT = Path("artifacts/solver-scenario-lab")
CONDITIONS = ("baseline", "leave", "sickness", "matrix", "night_shortage")
MONTHS = (date(2027, 2, 1), date(2028, 2, 1), date(2027, 4, 1), date(2027, 7, 1))


@dataclass(frozen=True)
class ObjectVariant:
    name: str
    shift_hours: int
    required_primary_count: int
    local_count: int
    regime: SitePlanningRegime


OBJECT_VARIANTS = (
    ObjectVariant("ordinary_12h_single_5", 12, 1, 5, SitePlanningRegime.ORDINARY),
    ObjectVariant("ordinary_12h_double_10", 12, 2, 10, SitePlanningRegime.ORDINARY),
    ObjectVariant("ochrona_24h_single_4", 24, 1, 4, SitePlanningRegime.OCHRONA),
    ObjectVariant("ochrona_24h_single_5", 24, 1, 5, SitePlanningRegime.OCHRONA),
    ObjectVariant("ochrona_24h_double_8", 24, 2, 8, SitePlanningRegime.OCHRONA),
    ObjectVariant("ochrona_24h_double_10", 24, 2, 10, SitePlanningRegime.OCHRONA),
)
VARIANTS_BY_NAME = {variant.name: variant for variant in OBJECT_VARIANTS}


@dataclass(frozen=True)
class AbsenceInput:
    employee_id: str
    kind: AvailabilityKind
    start_date: date
    end_date: date


@dataclass(frozen=True)
class MatrixInput:
    employee_id: str
    cell: str
    value: int | str
    effective_from: date
    effective_to: date


@dataclass(frozen=True)
class ScenarioSpec:
    family: str
    case_seed: int
    month: date
    condition: str
    shift_hours: int
    required_primary_count: int
    local_employee_ids: tuple[str, ...]
    external_employee_id: str
    regime: SitePlanningRegime
    day_only_employee_ids: tuple[str, ...]
    cannot_work_24h_employee_ids: tuple[str, ...]
    leave: AbsenceInput | None
    sickness: AbsenceInput | None
    matrix: MatrixInput | None
    shortage_date: date | None
    target_hours: int = 168

    @property
    def site_id(self) -> str:
        return f"LAB-SITE-{self.case_seed}"

    @property
    def profile_id(self) -> str:
        return f"LAB-PROFILE-{self.case_seed}"

    @property
    def coordinator_id(self) -> str:
        return f"LAB-COORD-{self.case_seed}"

    def summary(self) -> dict[str, Any]:
        return _jsonify(asdict(self))


@dataclass
class CaseOutcome:
    ok: bool
    category: str
    message: str
    statuses: list[str]
    commands: list[dict[str, Any]]
    summary: dict[str, Any]
    candidates: list[dict[str, Any]]
    warnings: list[str]
    external_assignments: list[dict[str, Any]]


class ScenarioProblem(RuntimeError):
    def __init__(self, category: str, message: str):
        super().__init__(message)
        self.category = category


def _month_end(month: date) -> date:
    return date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])


def _bounded_period(rng: random.Random, month: date, length: int) -> tuple[date, date]:
    days = calendar.monthrange(month.year, month.month)[1]
    length = max(1, min(length, days))
    start_day = rng.randint(1, days - length + 1)
    return date(month.year, month.month, start_day), date(month.year, month.month, start_day + length - 1)


def build_scenario(family: str, case_seed: int) -> ScenarioSpec:
    if family not in VARIANTS_BY_NAME:
        raise ValueError(f"unknown family {family!r}; choose one of {sorted(VARIANTS_BY_NAME)}")
    variant = VARIANTS_BY_NAME[family]
    rng = random.Random(case_seed)
    family_index = next(i for i, item in enumerate(OBJECT_VARIANTS) if item.name == family)
    month = MONTHS[family_index % len(MONTHS)]
    condition = CONDITIONS[case_seed % len(CONDITIONS)]
    local_ids = tuple(f"LAB-EMP-{case_seed}-{i + 1}" for i in range(variant.local_count))
    external_id = f"LAB-EXTERNAL-{case_seed}"
    day_only = (local_ids[0],) if variant.shift_hours == 12 else ()
    cannot_24 = (local_ids[-1],) if variant.shift_hours == 24 else ()
    leave = sickness = None
    matrix = None
    shortage_date = None

    if condition == "leave":
        start, end = _bounded_period(rng, month, 14)
        leave_employee = rng.choice(local_ids)
        leave = AbsenceInput(leave_employee, AvailabilityKind.LEAVE_GRANTED, start, end)
        if variant.local_count not in (4, 8) and rng.choice((False, True)):
            length = rng.randint(1, 21)
            sick_start, sick_end = _bounded_period(rng, month, length)
            sickness = AbsenceInput(rng.choice(local_ids), AvailabilityKind.SICK_LEAVE, sick_start, sick_end)
    elif condition == "sickness":
        length = rng.randint(1, 21)
        start, end = _bounded_period(rng, month, length)
        sickness = AbsenceInput(rng.choice(local_ids), AvailabilityKind.SICK_LEAVE, start, end)
    elif condition == "matrix":
        cell = rng.choice(("D", "N", "weekday"))
        value: str | int = cell if cell != "weekday" else rng.randint(1, 7)
        matrix = MatrixInput(rng.choice(local_ids), cell, value, month, _month_end(month))
    elif condition == "night_shortage":
        shortage_date = date(month.year, month.month, rng.randint(1, calendar.monthrange(month.year, month.month)[1]))

    return ScenarioSpec(
        family, case_seed, month, condition, variant.shift_hours, variant.required_primary_count,
        local_ids, external_id, variant.regime, day_only, cannot_24, leave, sickness,
        matrix, shortage_date,
    )


def _shifts(spec: ScenarioSpec) -> list[StandardShift]:
    if spec.shift_hours == 12:
        return [
            StandardShift(ShiftKind.D, time(6), time(18), False, spec.required_primary_count,
                          catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11),
            StandardShift(ShiftKind.N, time(18), time(6), True, spec.required_primary_count,
                          catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11),
        ]
    return [
        StandardShift(ShiftKind.D, time(6), time(6), True, spec.required_primary_count,
                      catalog_kind=ShiftCatalogKind.H24, required_rest_hours=24),
    ]


def _record(commands: list[dict[str, Any]], name: str, **payload: Any) -> None:
    commands.append({"command": name, "input": _jsonify(payload)})


def _bootstrap(conn, spec: ScenarioSpec, commands: list[dict[str, Any]]) -> None:
    shifts = _shifts(spec)
    for shift in shifts:
        validate_standard_shift(shift)
    profile = SiteProfile(
        spec.profile_id, spec.profile_id, True, shifts, True, True, False, False, 1, 60,
    )
    coordinator = Coordinator(spec.coordinator_id, spec.coordinator_id, True)
    site = Site(spec.site_id, spec.profile_id, spec.site_id, True, spec.regime)
    association = CoordinatorSiteAssociation(spec.coordinator_id, spec.site_id, True)
    _record(commands, "bootstrap_or_resume_coordinator_context", site_id=spec.site_id,
            profile_id=spec.profile_id, regime=spec.regime, shifts=shifts)
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
        coordinator=coordinator, site_profile=profile, site=site, association=association,
    )
    _record(commands, "update_site_profile", profile_id=spec.profile_id, shifts=shifts)
    update_site_profile(conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id, profile=profile)

    all_ids = spec.local_employee_ids + (spec.external_employee_id,)
    for employee_id in all_ids:
        employee = Employee(
            employee_id, employee_id, date(2020, 1, 1), None,
            employee_id in spec.day_only_employee_ids,
        )
        kind = MembershipKind.LOCAL if employee_id in spec.local_employee_ids else MembershipKind.EXTERNAL_SUPPORT
        membership = SiteMembership(
            employee_id, spec.site_id, kind, True, ReadinessState.READY_FOR_PRIMARY,
            ReadinessSource.DEFAULT, employee_id not in spec.cannot_work_24h_employee_ids,
        )
        _record(commands, "update_employee", employee=employee)
        update_employee(conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id, employee=employee)
        _record(commands, "update_membership", membership=membership)
        update_membership(conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id, membership=membership)
        if kind == MembershipKind.LOCAL:
            _record(commands, "set_target_hours", employee_id=employee_id, month=spec.month,
                    target_hours=spec.target_hours)
            set_target_hours(
                conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
                employee_id=employee_id, month=spec.month, target_hours=spec.target_hours,
            )

    for day_number in range(1, calendar.monthrange(spec.month.year, spec.month.month)[1] + 1):
        day = CalendarDay(date(spec.month.year, spec.month.month, day_number), False)
        _record(commands, "set_calendar_day", day=day)
        set_calendar_day(conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id, day=day)


def _append_absence(conn, spec: ScenarioSpec, absence: AbsenceInput,
                    commands: list[dict[str, Any]], label: str) -> None:
    availability_id = f"LAB-{label}-{spec.case_seed}"
    _record(commands, "append_availability", availability_id=availability_id, absence=absence)
    append_availability(
        conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
        availability_id=availability_id, employee_id=absence.employee_id, kind=absence.kind,
        start_date=absence.start_date, end_date=absence.end_date, active=True,
    )


def _apply_initial_decisions(conn, spec: ScenarioSpec, commands: list[dict[str, Any]]) -> None:
    if spec.leave is not None:
        _append_absence(conn, spec, spec.leave, commands, "LEAVE")
    if spec.matrix is not None:
        item = spec.matrix
        if item.cell in ("D", "N"):
            _record(commands, "create_employee_shift_unavailability", matrix=item)
            create_employee_shift_unavailability(
                conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
                employee_id=item.employee_id, shift_kind=ShiftKind(item.value),
                effective_from=item.effective_from, effective_to=item.effective_to,
            )
        else:
            _record(commands, "create_employee_weekday_unavailability", matrix=item)
            create_employee_weekday_unavailability(
                conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
                employee_id=item.employee_id, iso_weekday=int(item.value),
                effective_from=item.effective_from, effective_to=item.effective_to,
            )
    if spec.shortage_date is not None:
        for employee_id in spec.local_employee_ids:
            _record(commands, "create_employee_shift_unavailability", employee_id=employee_id,
                    shift_kind="N", effective_from=spec.shortage_date, effective_to=spec.shortage_date)
            create_employee_shift_unavailability(
                conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id,
                employee_id=employee_id, shift_kind=ShiftKind.N,
                effective_from=spec.shortage_date, effective_to=spec.shortage_date,
            )


def _assignment_fact(assignment: Assignment) -> dict[str, Any]:
    return _jsonify({
        "assignment_id": assignment.assignment_id,
        "schedule_version_id": assignment.schedule_version_id,
        "employee_id": assignment.employee_id,
        "start": assignment.start_datetime,
        "end": assignment.end_datetime,
        "role": assignment.role,
        "state": assignment.state,
        "frozen": assignment.frozen,
        "covers_demand_id": assignment.covers_demand_id,
        "mentor_primary_assignment_id": assignment.mentor_primary_assignment_id,
        "operational_code": assignment.operational_code,
        "work_period_id": assignment.work_period_id,
        "required_rest_after_hours": assignment.required_rest_after_hours,
    })


def check_closed_world(state, assignments: Iterable[Assignment], spec: ScenarioSpec,
                       *, external_enabled: bool) -> list[str]:
    problems: list[str] = []
    employee_ids = set(spec.local_employee_ids) | {spec.external_employee_id}
    memberships = {(m.employee_id, m.site_id): m for m in state.memberships if m.enabled}
    demands = {d.demand_id: d for d in state.shift_demands}
    if any(shift.catalog_kind == ShiftCatalogKind.OTHER for shift in state.profile.standard_shifts):
        problems.append("profile contains INNY")
    if any(d.catalog_kind == ShiftCatalogKind.OTHER for d in state.shift_demands):
        problems.append("demands contain INNY")
    if state.other_site_assignments:
        problems.append("other-Site assignments present")
    for window in state.external_windows:
        if not external_enabled or window.employee_id != spec.external_employee_id or window.site_id != spec.site_id:
            problems.append(f"unauthorized external window {window.window_id}")
    for assignment in assignments:
        if assignment.employee_id not in employee_ids:
            problems.append(f"foreign employee {assignment.employee_id}")
            continue
        membership = memberships.get((assignment.employee_id, spec.site_id))
        expected_kind = MembershipKind.LOCAL if assignment.employee_id in spec.local_employee_ids else MembershipKind.EXTERNAL_SUPPORT
        if membership is None or membership.membership_kind != expected_kind:
            problems.append(f"invalid membership for {assignment.employee_id}")
        if assignment.employee_id == spec.external_employee_id and not external_enabled:
            problems.append("external employee used before coordinator consent")
        if assignment.role != AssignmentRole.PRIMARY or not assignment.covers_demand_id:
            problems.append(f"assignment {assignment.assignment_id} is not demand-backed PRIMARY")
            continue
        demand = demands.get(assignment.covers_demand_id)
        if demand is None:
            problems.append(f"foreign demand {assignment.covers_demand_id}")
        elif (assignment.start_datetime, assignment.end_datetime) != (demand.start_datetime, demand.end_datetime):
            problems.append(f"extra hours in {assignment.assignment_id}")
    return problems


def _external_proposed(result, spec: ScenarioSpec) -> bool:
    payload = result.decision_payload
    if payload is None:
        return False
    return any("Wsparcie zewn" in option and spec.external_employee_id in option
               for option in payload.unblocking_options)


def _add_support(conn, spec: ScenarioSpec, result, commands: list[dict[str, Any]]) -> bool:
    if not _external_proposed(result, spec):
        return False
    blocking = result.decision_payload.blocking_shift_demands
    if not blocking:
        return False
    for index, demand in enumerate(blocking):
        window = ExternalSupportWindow(
            f"LAB-WINDOW-{spec.case_seed}-{index}", spec.external_employee_id, spec.site_id,
            demand.start_datetime, demand.end_datetime, True, None,
        )
        _record(commands, "add_external_support_window", window=window,
                production_option=result.decision_payload.unblocking_options)
        add_external_support_window(
            conn, coordinator_id=spec.coordinator_id, site_id=spec.site_id, window=window,
        )
    return True


def _inspect_result(conn, spec: ScenarioSpec, result, *, external_enabled: bool,
                    statuses: list[str], candidates: list[dict[str, Any]], warnings: list[str]) -> bool:
    statuses.append(result.status)
    warnings.extend(result.warnings)
    if result.status == "TECHNICAL_ERROR":
        raise ScenarioProblem("SOLVER_MISMATCH", result.error_message or "TECHNICAL_ERROR")
    if result.status == "DECISION_REQUIRED":
        if result.candidates or result.decision_payload is None:
            raise ScenarioProblem("SOLVER_MISMATCH", "DECISION_REQUIRED lacks zero-candidate payload")
        if spec.shortage_date is not None:
            blocking = result.decision_payload.blocking_shift_demands
            if not any(item.start_datetime.date() == spec.shortage_date for item in blocking):
                raise ScenarioProblem("SOLVER_MISMATCH", "night shortage demand missing from payload")
        return False
    if result.status != "FEASIBLE" or not (1 <= len(result.candidates) <= 3):
        raise ScenarioProblem("SOLVER_MISMATCH", f"invalid FEASIBLE result: {result.status}/{len(result.candidates)}")
    state, _ = assemble_planning_state(conn, site_id=spec.site_id, month=spec.month)
    for candidate in result.candidates:
        report = validate(state, candidate)
        if not report.hard_pass:
            raise ScenarioProblem("CANDIDATE_INVALID", "; ".join(report.violations))
        problems = check_closed_world(state, candidate, spec, external_enabled=external_enabled)
        if problems:
            raise ScenarioProblem("CANDIDATE_INVALID", "; ".join(problems))
        candidates.append({"assignments": [_assignment_fact(a) for a in candidate], "warnings": list(report.warnings)})
    chosen = result.candidates[0]
    select_candidate(
        conn, site_id=spec.site_id, month=spec.month, candidate=chosen,
        coordinator_id=spec.coordinator_id,
    )
    readback = get_current_schedule_snapshot(conn, spec.site_id, spec.month)
    if readback is None:
        raise ScenarioProblem("PERSISTENCE_MISMATCH", "selected snapshot missing")
    _, snapshot = readback
    expected = sorted((_assignment_fact(a) for a in chosen), key=lambda item: item["assignment_id"])
    actual = sorted((_assignment_fact(a) for a in snapshot.assignments), key=lambda item: item["assignment_id"])
    if actual != expected:
        raise ScenarioProblem("PERSISTENCE_MISMATCH", "selected snapshot differs from candidate")
    return True


def _plan_and_maybe_support(conn, spec: ScenarioSpec, commands: list[dict[str, Any]], *, use_replan: bool,
                            statuses: list[str], candidates: list[dict[str, Any]], warnings: list[str],
                            external_enabled: bool = False) -> tuple[Any, bool, bool]:
    command = "replan" if use_replan else "plan_month"
    _record(commands, command, site_id=spec.site_id, month=spec.month, effective_from=spec.month)
    result = (replan if use_replan else plan_month)(
        conn, site_id=spec.site_id, month=spec.month, coordinator_id=spec.coordinator_id,
        effective_from=spec.month,
    )
    selected = _inspect_result(conn, spec, result, external_enabled=external_enabled,
                               statuses=statuses, candidates=candidates, warnings=warnings)
    if selected or result.status != "DECISION_REQUIRED":
        return result, external_enabled, selected
    support_added = _add_support(conn, spec, result, commands)
    if not support_added:
        return result, external_enabled, False
    _record(commands, "plan_month", site_id=spec.site_id, month=spec.month, after_external_consent=True)
    result = plan_month(
        conn, site_id=spec.site_id, month=spec.month, coordinator_id=spec.coordinator_id,
        effective_from=spec.month,
    )
    selected = _inspect_result(conn, spec, result, external_enabled=True,
                               statuses=statuses, candidates=candidates, warnings=warnings)
    return result, True, selected


def execute_scenario(spec: ScenarioSpec) -> CaseOutcome:
    commands: list[dict[str, Any]] = []
    statuses: list[str] = []
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    conn = None
    try:
        _record(commands, "connect", database=":memory:")
        conn = connect(":memory:")
        _bootstrap(conn, spec, commands)
        _apply_initial_decisions(conn, spec, commands)
        _, external_enabled, selected = _plan_and_maybe_support(
            conn, spec, commands, use_replan=False, statuses=statuses,
            candidates=candidates, warnings=warnings,
        )
        if spec.sickness is not None:
            if not selected:
                raise ScenarioProblem("GENERATOR_ERROR", "sickness requires a selected baseline schedule")
            _append_absence(conn, spec, spec.sickness, commands, "SICK")
            _, sick_external, _ = _plan_and_maybe_support(
                conn, spec, commands, use_replan=True, statuses=statuses,
                candidates=candidates, warnings=warnings, external_enabled=external_enabled,
            )
            external_enabled = external_enabled or sick_external
        readback = get_current_schedule_snapshot(conn, spec.site_id, spec.month)
        external_assignments = []
        if readback is not None:
            external_assignments = [
                _assignment_fact(a) for a in readback[1].assignments
                if a.employee_id == spec.external_employee_id
            ]
        return CaseOutcome(True, "PASS", "", statuses, commands, spec.summary(), candidates,
                           warnings, external_assignments)
    except ScenarioProblem as exc:
        return CaseOutcome(False, exc.category, str(exc), statuses, commands, spec.summary(),
                           candidates, warnings, [])
    except Exception as exc:  # backend/write failures are replayable lab failures
        return CaseOutcome(False, "GENERATOR_ERROR", f"{type(exc).__name__}: {exc}", statuses,
                           commands, spec.summary(), candidates, warnings, [])
    finally:
        if conn is not None:
            conn.close()


def _jsonify(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _jsonify(asdict(value))
    return value


def _build_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def _write_failure(output_dir: Path, root_seed: int, index: int, spec: ScenarioSpec,
                   outcome: CaseOutcome) -> Path:
    target = output_dir / f"run-{root_seed}" / f"case-{index}-{spec.case_seed}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    build_sha = _build_sha()
    replay = (f"python -m tools.solver_scenario_lab --family {spec.family} "
              f"--case-seed {spec.case_seed} --expected-sha {build_sha}")
    document = {
        "schema_version": 1, "build_sha": build_sha, "root_seed": root_seed,
        "case_index": index, "case_seed": spec.case_seed, "family": spec.family,
        "summary": outcome.summary, "commands": outcome.commands, "statuses": outcome.statuses,
        "category": outcome.category, "message": outcome.message, "warnings": outcome.warnings,
        "candidates": outcome.candidates, "external_assignments": outcome.external_assignments,
        "replay": replay,
    }
    with target.open("x", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return target


def run_cases(*, cases: int, seed: int, family: str | None = None, case_seed: int | None = None,
              output_dir: Path = DEFAULT_OUTPUT) -> int:
    rng = random.Random(seed)
    specs = (
        [build_scenario(family, case_seed)]
        if family is not None and case_seed is not None
        else [build_scenario(OBJECT_VARIANTS[index % len(OBJECT_VARIANTS)].name, rng.randrange(1, 2**31))
              for index in range(cases)]
    )
    passed = failed = 0
    for index, spec in enumerate(specs):
        outcome = execute_scenario(spec)
        if outcome.ok:
            passed += 1
            continue
        failed += 1
        replay = (f"python -m tools.solver_scenario_lab --family {spec.family} "
                  f"--case-seed {spec.case_seed} --expected-sha {_build_sha()}")
        try:
            path = _write_failure(output_dir, seed, index, spec, outcome)
            print(f"FAIL family={spec.family} seed={spec.case_seed} record={path} replay={replay}")
        except FileExistsError:
            print(f"FAIL family={spec.family} seed={spec.case_seed} record=EXISTS replay={replay}")
    print(f"CASES={len(specs)} PASS={passed} FAIL={failed} SEED={seed}")
    return 0 if failed == 0 else 1
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local coordinator/solver scenario lab")
    parser.add_argument("--cases", type=int, default=25)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--family", choices=sorted(VARIANTS_BY_NAME))
    parser.add_argument("--case-seed", type=int)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-sha", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.cases <= 0:
        parser.error("--cases must be positive")
    if (args.family is None) != (args.case_seed is None):
        parser.error("--family and --case-seed must be supplied together")
    if args.expected_sha and args.expected_sha != _build_sha():
        print(f"WARNING replay SHA={args.expected_sha} differs from current SHA={_build_sha()}")
    return run_cases(
        cases=args.cases, seed=args.seed, family=args.family, case_seed=args.case_seed,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
