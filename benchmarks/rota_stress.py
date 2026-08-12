"""Deterministic end-to-end stress benchmark for PlanningEngine.

Every generated case has a known feasible witness schedule. The benchmark
then discards that schedule, calls production ``plan()``, and checks the
returned candidate with two independent oracles.

Run: python -m benchmarks.rota_stress --cases 100 --seed 20260812
"""
from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
import json
import math
import random
import statistics
import time as clock

from rota.domain import (
    Assignment, AssignmentRole, AssignmentState, AvailabilityKind,
    AvailabilityRecord, CalendarDay, Employee, MembershipKind,
    ReadinessSource, ReadinessState, ShiftDemand, ShiftKind, Site,
    SiteMembership, SiteProfile, StandardShift, WorkBalance,
)
from rota.planning.engine import plan
from rota.planning.state import PlanningState
from rota.planning.validator import validate

DEFAULT_SEED = 20260812
HARD_ABSENCES = (
    AvailabilityKind.UNAVAILABLE_24H,
    AvailabilityKind.LEAVE_GRANTED,
    AvailabilityKind.SICK_LEAVE,
)


@dataclass(frozen=True)
class GeneratedCase:
    index: int
    seed: int
    state: PlanningState
    witness: tuple[Assignment, ...]
    required_primary_count: int


@dataclass(frozen=True)
class CaseResult:
    index: int
    seed: int
    month: str
    employees: int
    required_primary_count: int
    elapsed_seconds: float
    status: str
    errors: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkSummary:
    seed: int
    results: tuple[CaseResult, ...]

    @property
    def passed(self) -> int:
        return sum(not result.errors for result in self.results)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed

    @property
    def ok(self) -> bool:
        return self.failed == 0


def _month_demands(month: date, start_hour: int, count: int, version: str) -> tuple[ShiftDemand, ...]:
    days = calendar.monthrange(month.year, month.month)[1]
    demands = []
    for number in range(1, days + 1):
        current = date(month.year, month.month, number)
        day_start = datetime.combine(current, time(start_hour))
        night_start = day_start + timedelta(hours=12)
        demands.extend((
            ShiftDemand(f"{current}-D", version, day_start, night_start, count),
            ShiftDemand(f"{current}-N", version, night_start, day_start + timedelta(days=1), count),
        ))
    return tuple(demands)


def _employees(month: date, count: int) -> tuple[tuple[Employee, ...], tuple[str, ...], tuple[str, ...]]:
    pool_size = count * 2
    ids = [f"E{i:02d}" for i in range(pool_size * 2 + 2)]
    day_pool = tuple(ids[:pool_size])
    night_pool = tuple(ids[pool_size:pool_size * 2])
    employees = tuple(
        Employee(employee_id, employee_id, month - timedelta(days=365), None, employee_id in day_pool)
        for employee_id in ids
    )
    return employees, day_pool, night_pool


def _rotation_ids(pool: tuple[str, ...], offset: int, count: int) -> tuple[str, ...]:
    group_start = (offset % 2) * count
    return pool[group_start:group_start + count]


def _assignment(demand: ShiftDemand, employee_id: str, slot: int) -> Assignment:
    return Assignment(
        f"w-{demand.demand_id}-{slot}", demand.schedule_version_id, employee_id,
        demand.start_datetime, demand.end_datetime, AssignmentRole.PRIMARY,
        AssignmentState.PLANNED, False, demand.demand_id, None,
    )


def _monthly_witness(
    demands: tuple[ShiftDemand, ...], day_pool: tuple[str, ...], night_pool: tuple[str, ...], count: int,
) -> list[Assignment]:
    assignments = []
    first_day = demands[0].start_datetime.date()
    for demand in demands:
        offset = (demand.start_datetime.date() - first_day).days
        pool = day_pool if demand.demand_id.endswith("-D") else night_pool
        for slot, employee_id in enumerate(_rotation_ids(pool, offset, count)):
            assignments.append(_assignment(demand, employee_id, slot))
    return assignments


def _boundary_assignments(
    month: date, start_hour: int, day_pool: tuple[str, ...], night_pool: tuple[str, ...], count: int, version: str,
) -> tuple[Assignment, ...]:
    assignments = []
    for offset in range(-6, 0):
        current = month + timedelta(days=offset)
        day_start = datetime.combine(current, time(start_hour))
        for kind, start, pool in (
            ("D", day_start, day_pool),
            ("N", day_start + timedelta(hours=12), night_pool),
        ):
            for slot, employee_id in enumerate(_rotation_ids(pool, offset, count)):
                assignments.append(Assignment(
                    f"boundary-{current}-{kind}-{slot}", version, employee_id, start, start + timedelta(hours=12),
                    AssignmentRole.PRIMARY, AssignmentState.REALIZED, True, None, None,
                ))
    return tuple(assignments)


def _occupied_dates(assignments: list[Assignment]) -> dict[str, set[date]]:
    occupied: dict[str, set[date]] = {}
    for assignment in assignments:
        current = assignment.start_datetime.date()
        last = (assignment.end_datetime - timedelta(microseconds=1)).date()
        while current <= last:
            occupied.setdefault(assignment.employee_id, set()).add(current)
            current += timedelta(days=1)
    return occupied


def _availability(
    rng: random.Random, month: date, employees: tuple[Employee, ...], witness: list[Assignment],
    boundary: tuple[Assignment, ...],
) -> tuple[AvailabilityRecord, ...]:
    occupied = _occupied_dates([*witness, *boundary])
    days = [date(month.year, month.month, day) for day in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
    records = []
    for employee in employees:
        free = [day for day in days if day not in occupied.get(employee.employee_id, set())]
        rng.shuffle(free)
        for position, day in enumerate(free[:min(3, len(free))]):
            kind = HARD_ABSENCES[(position + rng.randrange(len(HARD_ABSENCES))) % len(HARD_ABSENCES)]
            record_id = f"absence-{employee.employee_id}-{day}"
            records.append(AvailabilityRecord(
                record_id, f"{record_id}-v1", employee.employee_id, kind, day, day, True, None, "stress",
            ))
        starts = {a.start_datetime.date() for a in witness if a.employee_id == employee.employee_id}
        off_starts = [day for day in days if day not in starts]
        if off_starts:
            day = rng.choice(off_starts)
            record_id = f"day-off-{employee.employee_id}-{day}"
            records.append(AvailabilityRecord(
                record_id, f"{record_id}-v1", employee.employee_id,
                AvailabilityKind.DAY_SHIFT_OFF, day, day, True, None, "stress",
            ))
    return tuple(records)


def _mark_existing(
    rng: random.Random, witness: list[Assignment],
) -> tuple[tuple[Assignment, ...], tuple[Assignment, ...]]:
    frozen_count = max(2, len(witness) // 12)
    frozen_ids = {assignment.assignment_id for assignment in rng.sample(witness, frozen_count)}
    remaining = [assignment for assignment in witness if assignment.assignment_id not in frozen_ids]
    replan_ids = {assignment.assignment_id for assignment in rng.sample(remaining, max(1, len(witness) // 20))}
    updated = []
    existing = []
    for assignment in witness:
        candidate = replace(assignment, frozen=assignment.assignment_id in frozen_ids)
        updated.append(candidate)
        if candidate.frozen or candidate.assignment_id in replan_ids:
            existing.append(candidate)
    return tuple(updated), tuple(existing)


def _calendar_days(rng: random.Random, month: date) -> tuple[CalendarDay, ...]:
    count = calendar.monthrange(month.year, month.month)[1]
    holidays = set(rng.sample(range(1, count + 1), 3))
    return tuple(CalendarDay(date(month.year, month.month, day), day in holidays) for day in range(1, count + 1))


def generate_case(index: int, seed: int) -> GeneratedCase:
    rng = random.Random(seed)
    month = date(rng.randint(2025, 2032), rng.randint(1, 12), 1)
    count = 2 if index % 3 == 2 else 1
    start_hour = rng.choice((5, 6, 7, 8))
    version = f"stress-{index}-v1"
    demands = _month_demands(month, start_hour, count, version)
    employees, day_pool, night_pool = _employees(month, count)
    witness = _monthly_witness(demands, day_pool, night_pool, count)
    boundary = _boundary_assignments(month, start_hour, day_pool, night_pool, count, version)
    witness_tuple, existing = _mark_existing(rng, witness)
    profile_id = f"STRESS-{index}"
    site_id = f"stress-site-{index}"
    shifts = [
        StandardShift(ShiftKind.D, time(start_hour), time(start_hour + 12), False, count),
        StandardShift(ShiftKind.N, time(start_hour + 12), time(start_hour), True, count),
    ]
    memberships = tuple(
        SiteMembership(e.employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
        for e in employees
    )
    targets = {employee.employee_id: 0 for employee in employees}
    for assignment in witness_tuple:
        targets[assignment.employee_id] += 12
    state = PlanningState(
        Site(site_id, profile_id, site_id, True),
        SiteProfile(profile_id, profile_id, True, shifts, True, False, False, True, 2, 60),
        month, _calendar_days(rng, month), boundary, memberships, employees, (),
        _availability(rng, month, employees, list(witness_tuple), boundary), (), (), (), demands, existing, (),
        tuple(WorkBalance(e.employee_id, month, targets[e.employee_id], 0, 0, 0, 0, 0) for e in employees),
        (), (), version,
    )
    generated = GeneratedCase(index, seed, state, witness_tuple, count)
    errors = candidate_errors(state, list(witness_tuple))
    if errors:
        raise AssertionError(f"benchmark generator created invalid witness: {errors}")
    return generated


def _overlaps_absence(assignment: Assignment, record: AvailabilityRecord) -> bool:
    start = datetime.combine(record.start_date, time())
    end = datetime.combine(record.end_date + timedelta(days=1), time())
    return assignment.start_datetime < end and assignment.end_datetime > start


def _coverage_errors(state: PlanningState, assignments: list[Assignment]) -> list[str]:
    demands = {d.demand_id: d for d in state.shift_demands}
    counts = {demand_id: 0 for demand_id in demands}
    errors = []
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY or not assignment.covers_demand_id:
            continue
        demand = demands.get(assignment.covers_demand_id)
        if demand is None:
            errors.append(f"unknown demand {assignment.covers_demand_id}")
            continue
        counts[demand.demand_id] += 1
        if (assignment.start_datetime, assignment.end_datetime) != (demand.start_datetime, demand.end_datetime):
            errors.append(f"interval mismatch {assignment.assignment_id}")
    for demand_id, demand in demands.items():
        if counts[demand_id] != demand.required_primary_count:
            errors.append(f"coverage {demand_id}: {counts[demand_id]}/{demand.required_primary_count}")
    return errors


def _eligibility_errors(state: PlanningState, assignments: list[Assignment]) -> list[str]:
    employees = {employee.employee_id: employee for employee in state.employees}
    memberships = {m.employee_id for m in state.memberships if m.site_id == state.site.site_id and m.enabled}
    records = [record for record in state.availability_records if record.active and record.kind in HARD_ABSENCES]
    night_start = state.profile.standard_shifts[1].start_time
    errors = []
    for assignment in assignments:
        employee = employees.get(assignment.employee_id)
        if employee is None or assignment.employee_id not in memberships:
            errors.append(f"unauthorized employee {assignment.employee_id}")
            continue
        if assignment.start_datetime.date() < employee.active_from or (
            employee.active_to is not None and assignment.end_datetime.date() > employee.active_to
        ):
            errors.append(f"inactive employee {assignment.employee_id}")
        if employee.day_only and assignment.start_datetime.time() == night_start:
            errors.append(f"DAY_ONLY on N {assignment.assignment_id}")
        for record in records:
            if record.employee_id == assignment.employee_id and _overlaps_absence(assignment, record):
                errors.append(f"absence overlap {assignment.assignment_id}/{record.availability_id}")
    return errors


def _load_errors(state: PlanningState, employee_id: str, assignments: list[Assignment]) -> list[str]:
    days = calendar.monthrange(state.month.year, state.month.month)[1]
    month_start = datetime.combine(state.month, time())
    errors = []
    for offset in range(-6, days - 6):
        window_start = month_start + timedelta(days=offset)
        window_end = window_start + timedelta(days=7)
        seconds = sum(
            max(0.0, (min(a.end_datetime, window_end) - max(a.start_datetime, window_start)).total_seconds())
            for a in assignments
        )
        hours = int(seconds // 3600)
        if hours > state.profile.rolling_7d_decision_threshold_hours:
            errors.append(f"LOAD {employee_id}: {hours}h from {window_start.date()}")
    return errors


def _time_errors(state: PlanningState, assignments: list[Assignment]) -> list[str]:
    work = [*assignments, *state.boundary_assignments, *state.other_site_assignments]
    by_employee: dict[str, list[Assignment]] = {}
    for assignment in work:
        by_employee.setdefault(assignment.employee_id, []).append(assignment)
    errors = []
    for employee_id, employee_work in by_employee.items():
        ordered = sorted(employee_work, key=lambda assignment: assignment.start_datetime)
        for earlier, later in zip(ordered, ordered[1:]):
            gap = (later.start_datetime - earlier.end_datetime).total_seconds() / 3600
            if gap < 11:
                errors.append(f"REST {employee_id}: {gap:g}h")
        errors.extend(_load_errors(state, employee_id, ordered))
    return errors


def candidate_errors(state: PlanningState, assignments: list[Assignment]) -> tuple[str, ...]:
    errors = []
    ids = [assignment.assignment_id for assignment in assignments]
    if len(ids) != len(set(ids)):
        errors.append("duplicate assignment_id")
    errors.extend(_coverage_errors(state, assignments))
    errors.extend(_eligibility_errors(state, assignments))
    errors.extend(_time_errors(state, assignments))
    by_id = {assignment.assignment_id: assignment for assignment in assignments}
    for existing in state.existing_assignments:
        if existing.frozen or existing.state == AssignmentState.REALIZED:
            if by_id.get(existing.assignment_id) != existing:
                errors.append(f"fixed assignment changed: {existing.assignment_id}")
    report = validate(state, assignments)
    if not report.hard_pass:
        errors.extend(f"validator: {violation}" for violation in report.violations)
    return tuple(dict.fromkeys(errors))


def run_case(case: GeneratedCase, max_case_seconds: float | None = None) -> CaseResult:
    started = clock.perf_counter()
    result = plan(case.state)
    elapsed = clock.perf_counter() - started
    errors = []
    if result.status != "FEASIBLE":
        errors.append(f"status={result.status}: {result.error_message or result.decision_payload}")
    elif not result.candidates:
        errors.append("FEASIBLE without candidate")
    else:
        errors.extend(candidate_errors(case.state, result.candidates[0]))
    if max_case_seconds is not None and elapsed > max_case_seconds:
        errors.append(f"deadline exceeded: {elapsed:.3f}s > {max_case_seconds:.3f}s")
    return CaseResult(
        case.index, case.seed, case.state.month.isoformat(), len(case.state.employees),
        case.required_primary_count, elapsed, result.status, tuple(errors),
    )


def run_benchmark(cases: int = 100, seed: int = DEFAULT_SEED, max_case_seconds: float | None = None) -> BenchmarkSummary:
    rng = random.Random(seed)
    results = []
    for index in range(cases):
        case_seed = rng.getrandbits(63)
        results.append(run_case(generate_case(index, case_seed), max_case_seconds))
    return BenchmarkSummary(seed, tuple(results))


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def summary_dict(summary: BenchmarkSummary) -> dict:
    timings = [result.elapsed_seconds for result in summary.results]
    return {
        "seed": summary.seed,
        "cases": len(summary.results),
        "passed": summary.passed,
        "failed": summary.failed,
        "status_counts": {
            status: sum(result.status == status for result in summary.results)
            for status in sorted({result.status for result in summary.results})
        },
        "timing_seconds": {
            "mean": statistics.fmean(timings) if timings else 0.0,
            "p50": _percentile(timings, 0.50) if timings else 0.0,
            "p95": _percentile(timings, 0.95) if timings else 0.0,
            "max": max(timings, default=0.0),
            "total": sum(timings),
        },
        "failures": [result.__dict__ for result in summary.results if result.errors],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--max-case-seconds", type=float)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    if args.cases <= 0:
        parser.error("--cases must be positive")
    summary = run_benchmark(args.cases, args.seed, args.max_case_seconds)
    payload = summary_dict(summary)
    if args.as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        timing = payload["timing_seconds"]
        print(
            f"ROTA STRESS seed={args.seed} cases={args.cases} "
            f"PASS={summary.passed} FAIL={summary.failed} "
            f"p50={timing['p50']:.3f}s p95={timing['p95']:.3f}s "
            f"max={timing['max']:.3f}s total={timing['total']:.3f}s"
        )
        for failure in payload["failures"]:
            print(f"FAIL case={failure['index']} seed={failure['seed']} month={failure['month']}: {failure['errors']}")
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
