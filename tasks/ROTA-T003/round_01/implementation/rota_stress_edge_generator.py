"""Ad-hoc edge-case stress run on top of benchmarks.rota_stress's generation
primitives. Reuses the existing generator building blocks but pushes them to
harder combinations:
- double PRIMARY coverage (count=2) on every case, not just 1/3
- more HARD_ABSENCES per employee (up to 8 instead of 3)
- much higher frozen ratio (~1/4 of witness instead of ~1/12)
- much higher REPLAN ratio (~1/6 instead of ~1/20)
- 6 holidays/month instead of 3

Does not modify PlanningEngine or benchmarks/rota_stress.py. Kept as
evidence/reproduction for the 2026-08-14 edge stress trace logged in
log/session.txt (see tasks/ROTA-T003/round_01/implementation/edge_stress_20260814.txt
for the run this file produced).

Run: PYTHONPATH=. python tasks/ROTA-T003/round_01/implementation/rota_stress_edge_generator.py
"""
import calendar
import math
import random
import time as clock
from dataclasses import replace
from datetime import date, time

from rota.domain import (
    AvailabilityKind, AvailabilityRecord, CalendarDay, MembershipKind,
    ReadinessSource, ReadinessState, ShiftKind, Site, SiteMembership,
    SiteProfile, StandardShift, WorkBalance,
)
from rota.planning.engine import plan
from rota.planning.state import PlanningState

from benchmarks.rota_stress import (
    HARD_ABSENCES, GeneratedCase, _boundary_assignments, _employees,
    _month_demands, _monthly_witness, _occupied_dates, candidate_errors,
)


def _edge_availability(rng, month, employees, witness, boundary):
    occupied = _occupied_dates([*witness, *boundary])
    days = [date(month.year, month.month, d) for d in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
    records = []
    for employee in employees:
        free = [d for d in days if d not in occupied.get(employee.employee_id, set())]
        rng.shuffle(free)
        take = min(8, len(free))
        for position, day in enumerate(free[:take]):
            kind = HARD_ABSENCES[(position + rng.randrange(len(HARD_ABSENCES))) % len(HARD_ABSENCES)]
            rid = f"edge-absence-{employee.employee_id}-{day}"
            records.append(AvailabilityRecord(rid, f"{rid}-v1", employee.employee_id, kind, day, day, True, None, "edge"))
        starts = {a.start_datetime.date() for a in witness if a.employee_id == employee.employee_id}
        off_starts = [d for d in days if d not in starts]
        if off_starts:
            for day in rng.sample(off_starts, min(2, len(off_starts))):
                rid = f"edge-dayoff-{employee.employee_id}-{day}"
                records.append(AvailabilityRecord(
                    rid, f"{rid}-v1", employee.employee_id, AvailabilityKind.DAY_SHIFT_OFF, day, day, True, None, "edge",
                ))
    return tuple(records)


def _edge_mark_existing(rng, witness):
    frozen_count = max(2, len(witness) // 4)
    frozen_ids = {a.assignment_id for a in rng.sample(witness, min(frozen_count, len(witness)))}
    remaining = [a for a in witness if a.assignment_id not in frozen_ids]
    replan_count = max(1, len(witness) // 6)
    replan_ids = {a.assignment_id for a in rng.sample(remaining, min(replan_count, len(remaining)))}
    updated, existing = [], []
    for a in witness:
        candidate = replace(a, frozen=a.assignment_id in frozen_ids)
        updated.append(candidate)
        if candidate.frozen or candidate.assignment_id in replan_ids:
            existing.append(candidate)
    return tuple(updated), tuple(existing)


def _edge_calendar_days(rng, month):
    count = calendar.monthrange(month.year, month.month)[1]
    holidays = set(rng.sample(range(1, count + 1), min(6, count)))
    return tuple(CalendarDay(date(month.year, month.month, d), d in holidays) for d in range(1, count + 1))


def generate_edge_case(index, seed):
    rng = random.Random(seed)
    month = date(rng.randint(2025, 2032), rng.randint(1, 12), 1)
    count = 2  # always double coverage -- harder than the 1/3 baseline
    start_hour = rng.choice((5, 6, 7, 8))
    version = f"edge-{index}-v1"
    demands = _month_demands(month, start_hour, count, version)
    employees, day_pool, night_pool = _employees(month, count)
    witness = _monthly_witness(demands, day_pool, night_pool, count)
    boundary = _boundary_assignments(month, start_hour, day_pool, night_pool, count, version)
    witness_tuple, existing = _edge_mark_existing(rng, witness)
    profile_id = f"EDGE-{index}"
    site_id = f"edge-site-{index}"
    shifts = [
        StandardShift(ShiftKind.D, time(start_hour), time(start_hour + 12), False, count),
        StandardShift(ShiftKind.N, time(start_hour + 12), time(start_hour), True, count),
    ]
    memberships = tuple(
        SiteMembership(e.employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
        for e in employees
    )
    targets = {e.employee_id: 0 for e in employees}
    for a in witness_tuple:
        targets[a.employee_id] += 12
    state = PlanningState(
        Site(site_id, profile_id, site_id, True),
        SiteProfile(profile_id, profile_id, True, shifts, True, False, False, True, 2, 60),
        month, _edge_calendar_days(rng, month), boundary, memberships, employees, (),
        _edge_availability(rng, month, employees, list(witness_tuple), boundary), (), (), demands, existing, (),
        tuple(WorkBalance(e.employee_id, month, targets[e.employee_id], 0, 0, 0, 0, 0) for e in employees),
        (), (), version,
    )
    generated = GeneratedCase(index, seed, state, witness_tuple, count)
    witness_errors = candidate_errors(state, list(witness_tuple))
    return generated, witness_errors


def main():
    rng = random.Random(20260814)
    n = 100
    passed = fail_infeasible_witness = 0
    status_counts = {}
    failures = []
    timings = []
    per_case = []
    for i in range(n):
        case_seed = rng.getrandbits(63)
        case, witness_errors = generate_edge_case(i, case_seed)
        if witness_errors:
            fail_infeasible_witness += 1
            failures.append((i, "INVALID_WITNESS", witness_errors[:3]))
            per_case.append((i, 0.0, "INVALID_WITNESS"))
            continue
        started = clock.perf_counter()
        result = plan(case.state)
        elapsed = clock.perf_counter() - started
        timings.append(elapsed)
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        if result.status != "FEASIBLE":
            failures.append((i, result.status, (result.error_message or str(result.decision_payload))[:200]))
            per_case.append((i, elapsed, result.status))
            continue
        errors = candidate_errors(case.state, result.candidates[0])
        if errors:
            failures.append((i, "CANDIDATE_INVALID", errors[:5]))
            per_case.append((i, elapsed, "CANDIDATE_INVALID"))
            continue
        per_case.append((i, elapsed, "FEASIBLE"))
        passed += 1
    print(f"EDGE STRESS n={n} witness_generation_failures={fail_infeasible_witness} "
          f"plan_passed={passed} status_counts={status_counts}")
    if timings:
        sorted_t = sorted(timings)

        def pct(fraction):
            return sorted_t[min(len(sorted_t) - 1, max(0, math.ceil(len(sorted_t) * fraction) - 1))]

        print(f"timing: mean={sum(timings)/len(timings):.3f}s p50={pct(0.5):.3f}s "
              f"p95={pct(0.95):.3f}s max={max(timings):.3f}s total={sum(timings):.3f}s")
    for f in failures[:20]:
        print("FAIL", f)
    print("--- per-case ---")
    for i, elapsed, status in per_case:
        print(f"case={i:03d} elapsed={elapsed:.3f}s status={status}")


if __name__ == "__main__":
    main()
