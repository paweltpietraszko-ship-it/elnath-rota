"""
Elnath Rota — minimal OR-Tools CP-SAT proof of concept.
Scenario: October 2026, Frozen Execution Contract v0.3 HARD subset.

Purpose:
- Prove that CP-SAT can model the real scheduling core.
- Generate one HARD-valid monthly schedule.
- Independently validate the returned schedule in plain Python.

Not production code.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from ortools.sat.python import cp_model

YEAR = 2026
MONTH = 10
EMPLOYEES = ["A", "B", "C", "D", "E"]
DAYS = list(range(1, 32))
SHIFTS = ["D", "N"]

DAY_ONLY = {"C"}
DAY_SHIFT_OFF = {"A": {6, 17, 26}}
LEAVE_GRANTED = {"B": [(12, 18)]}  # inclusive calendar dates
UNAVAILABLE_DATES = {"D": {9, 23, 24}}
FORCED_PRIMARY = {("A", 8, "D"): 1}  # S: mentor A on PRIMARY D, Oct 8

TARGET_HOURS = {"A": 156, "B": 144, "C": 156, "D": 144, "E": 144}


def shift_interval(day: int, shift: str):
    base = datetime(YEAR, MONTH, day)
    if shift == "D":
        return base.replace(hour=5), base.replace(hour=17)
    return base.replace(hour=17), base + timedelta(days=1, hours=5)


def date_interval(day: int):
    start = datetime(YEAR, MONTH, day)
    return start, start + timedelta(days=1)


def overlap_hours(a_start, a_end, b_start, b_end) -> int:
    seconds = max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())
    return int(seconds // 3600)


def intervals_violate_rest(a_start, a_end, b_start, b_end) -> bool:
    if a_start <= b_start:
        rest = (b_start - a_end).total_seconds() / 3600
    else:
        rest = (a_start - b_end).total_seconds() / 3600
    return rest < 11


def build_and_solve():
    model = cp_model.CpModel()

    x = {
        (e, d, s): model.new_bool_var(f"x_{e}_{d}_{s}")
        for e in EMPLOYEES
        for d in DAYS
        for s in SHIFTS
    }

    # COVERAGE-01: exactly one PRIMARY on every required D and N.
    for d in DAYS:
        for s in SHIFTS:
            model.add(sum(x[e, d, s] for e in EMPLOYEES) == 1)

    # DAY_ONLY-01.
    for e in DAY_ONLY:
        for d in DAYS:
            model.add(x[e, d, "N"] == 0)

    # DAY_SHIFT_OFF-01 v0.3:
    # no D or N may START on the day off.
    # N started on previous day may end at 05:00 on the day off.
    for e, off_days in DAY_SHIFT_OFF.items():
        for d in off_days:
            model.add(x[e, d, "D"] == 0)
            model.add(x[e, d, "N"] == 0)

    # LEAVE_GRANTED-01: block every assignment whose real interval overlaps leave.
    for e, ranges in LEAVE_GRANTED.items():
        for d in DAYS:
            for s in SHIFTS:
                st, en = shift_interval(d, s)
                blocked = False
                for first, last in ranges:
                    for dd in range(first, last + 1):
                        ls, le = date_interval(dd)
                        if st < le and en > ls:
                            blocked = True
                            break
                    if blocked:
                        break
                if blocked:
                    model.add(x[e, d, s] == 0)

    # UNAVAILABLE-01: block every assignment whose real interval overlaps
    # any unavailable calendar-day interval.
    for e, unavailable_days in UNAVAILABLE_DATES.items():
        for d in DAYS:
            for s in SHIFTS:
                st, en = shift_interval(d, s)
                if any(
                    st < date_interval(ud)[1] and en > date_interval(ud)[0]
                    for ud in unavailable_days
                ):
                    model.add(x[e, d, s] == 0)

    # REST-01: any two assignments with less than 11h rest cannot both be selected.
    for e in EMPLOYEES:
        slots = [(d, s, *shift_interval(d, s)) for d in DAYS for s in SHIFTS]
        for i in range(len(slots)):
            d1, s1, st1, en1 = slots[i]
            for j in range(i + 1, len(slots)):
                d2, s2, st2, en2 = slots[j]
                if intervals_violate_rest(st1, en1, st2, en2):
                    model.add(x[e, d1, s1] + x[e, d2, s2] <= 1)

    # LOAD-01:
    # each rolling window of 7 consecutive calendar days inside October.
    # Count actual hours of each assignment overlapping the window.
    for e in EMPLOYEES:
        for start_day in range(1, 26):  # 1-7 ... 25-31
            ws = datetime(YEAR, MONTH, start_day)
            we = ws + timedelta(days=7)
            terms = []
            for d in DAYS:
                for s in SHIFTS:
                    st, en = shift_interval(d, s)
                    hrs = overlap_hours(st, en, ws, we)
                    if hrs:
                        terms.append(hrs * x[e, d, s])
            model.add(sum(terms) <= 60)

    # Training S: mentor A's existing PRIMARY D shift on Oct 8 is preserved.
    for key, required in FORCED_PRIMARY.items():
        if required:
            model.add(x[key] == 1)

    # Minimal SOFT objective: get close to target hours.
    # This does NOT turn target_hours into HARD.
    deviation_vars = []
    for e in EMPLOYEES:
        worked_hours = sum(12 * x[e, d, s] for d in DAYS for s in SHIFTS)
        pos = model.new_int_var(0, 744, f"target_over_{e}")
        neg = model.new_int_var(0, 744, f"target_under_{e}")
        model.add(worked_hours - TARGET_HOURS[e] == pos - neg)
        deviation_vars.extend([pos, neg])

    model.minimize(sum(deviation_vars))

    solver = cp_model.CpSolver()
    # Single worker makes the PoC easier to reproduce.
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = 30.0

    status = solver.solve(model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return status_name, None

    schedule = {}
    for d in DAYS:
        schedule[d] = {}
        for s in SHIFTS:
            chosen = [e for e in EMPLOYEES if solver.value(x[e, d, s])]
            schedule[d][s] = chosen[0] if len(chosen) == 1 else None

    return status_name, schedule


def validate(schedule):
    """Independent HARD validator. Does not use CP-SAT."""
    errors = []
    warnings = []

    # Coverage and assignment list.
    by_emp = defaultdict(list)
    for d in DAYS:
        for s in SHIFTS:
            e = schedule[d][s]
            if e not in EMPLOYEES:
                errors.append(f"COVERAGE-01: invalid {d} {s}: {e}")
                continue
            st, en = shift_interval(d, s)
            by_emp[e].append((st, en, d, s))

    # DAY_ONLY-01.
    for e in DAY_ONLY:
        for _, _, d, s in by_emp[e]:
            if s == "N":
                errors.append(f"DAY_ONLY-01: {e} has N on {d}")

    # DAY_SHIFT_OFF-01.
    for e, off_days in DAY_SHIFT_OFF.items():
        for _, _, d, s in by_emp[e]:
            if d in off_days:
                errors.append(f"DAY_SHIFT_OFF-01: {e} starts {s} on day off {d}")
        for off in off_days:
            for _, en, d, s in by_emp[e]:
                if s == "N" and d == off - 1 and en > date_interval(off)[0]:
                    warnings.append(
                        f"DAY_SHIFT_OFF SOFT: {e} prior N enters day off {off} until 05:00"
                    )

    # LEAVE_GRANTED-01.
    for e, ranges in LEAVE_GRANTED.items():
        for st, en, d, s in by_emp[e]:
            for first, last in ranges:
                for dd in range(first, last + 1):
                    ls, le = date_interval(dd)
                    if st < le and en > ls:
                        errors.append(
                            f"LEAVE_GRANTED-01: {e} {d}{s} overlaps leave day {dd}"
                        )

    # UNAVAILABLE-01.
    for e, unavailable_days in UNAVAILABLE_DATES.items():
        for st, en, d, s in by_emp[e]:
            for ud in unavailable_days:
                us, ue = date_interval(ud)
                if st < ue and en > us:
                    errors.append(
                        f"UNAVAILABLE-01: {e} {d}{s} overlaps unavailable day {ud}"
                    )

    # REST-01.
    min_rest = None
    min_rest_pair = None
    for e, arr in by_emp.items():
        arr = sorted(arr)
        for prev, cur in zip(arr, arr[1:]):
            _, prev_end, pd, ps = prev
            cur_start, _, cd, cs = cur
            rest = (cur_start - prev_end).total_seconds() / 3600
            if min_rest is None or rest < min_rest:
                min_rest = rest
                min_rest_pair = (e, pd, ps, cd, cs, rest)
            if rest < 11:
                errors.append(
                    f"REST-01: {e} {pd}{ps}->{cd}{cs}: only {rest:.1f}h"
                )

    # LOAD-01.
    max_load = (0.0, None, None)
    for e, arr in by_emp.items():
        for start_day in range(1, 26):
            ws = datetime(YEAR, MONTH, start_day)
            we = ws + timedelta(days=7)
            hours = sum(overlap_hours(st, en, ws, we) for st, en, _, _ in arr)
            if hours > max_load[0]:
                max_load = (hours, e, (start_day, start_day + 6))
            if hours > 60:
                errors.append(
                    f"LOAD-01: {e} has {hours}h in {start_day}-{start_day + 6}"
                )

    # Training S / mentor PRIMARY.
    if schedule[8]["D"] != "A":
        errors.append("S: mentor A is not PRIMARY D on Oct 8")

    monthly_hours = {
        e: 12 * len(by_emp[e])
        for e in EMPLOYEES
    }

    return {
        "hard_pass": not errors,
        "errors": errors,
        "warnings": warnings,
        "minimum_rest": min_rest_pair,
        "maximum_rolling_7d_load": max_load,
        "monthly_hours": monthly_hours,
    }


def main():
    status, schedule = build_and_solve()
    print(f"CP-SAT status: {status}")

    if schedule is None:
        print("No schedule returned.")
        raise SystemExit(2)

    print("\nSchedule:")
    for d in DAYS:
        print(f"{d:02d}: D={schedule[d]['D']} N={schedule[d]['N']}")

    report = validate(schedule)
    print("\nIndependent validator:")
    print("HARD:", "PASS" if report["hard_pass"] else "FAIL")
    print("minimum_rest:", report["minimum_rest"])
    print("maximum_rolling_7d_load:", report["maximum_rolling_7d_load"])
    print("monthly_hours:", report["monthly_hours"])
    for warning in report["warnings"]:
        print("WARNING:", warning)
    for error in report["errors"]:
        print("ERROR:", error)

    if not report["hard_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
