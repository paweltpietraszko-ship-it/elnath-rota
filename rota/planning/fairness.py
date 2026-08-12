"""SOFT ranking fairness terms for the CP-SAT objective (arch/spec.md SECTION 3).

Split out of solver.py to keep it under SIZE_FILE (arch/spec.md SECTION 9).
Deliberately takes already-derived fixed-hours dicts as plain arguments
rather than reaching back into solver.fixed_existing_assignments() itself --
solver.py owns REPLAN semantics (what counts as "fixed"), this module only
turns known facts into CP-SAT objective terms, and importing solver.py from
here would create a cycle since solver.py calls into this module.
"""
from __future__ import annotations

from ortools.sat.python import cp_model

WEEKEND_FAIRNESS_WEIGHT = 1
HOLIDAY_FAIRNESS_WEIGHT = 1
MAX_MONTHLY_HOURS = 744


def _demand_hours(demand) -> int:
    return int((demand.end_datetime - demand.start_datetime).total_seconds() // 3600)


def _is_weekend(day) -> bool:
    return day.weekday() >= 5


def add_weekend_fairness(
    model: cp_model.CpModel, x: dict, by_employee: dict[str, list],
    fixed_weekend_hours: dict[str, int], penalties: list,
) -> None:
    """Weekend fairness (arch/spec.md SECTION 3): monotonically prefer variants
    closer to an equal weekend workload among employees eligible this period.
    SOFT only -- weighted far below TARGET_DEVIATION_WEIGHT so it only breaks
    ties among equally target-optimal candidates, never trades away target
    accuracy (ROTA-REG-001 still requires exact monthly hours)."""
    if len(by_employee) < 2:
        return
    weekend_hours_vars = []
    for employee_id, employee_slots in by_employee.items():
        terms = [
            _demand_hours(s.demand) * x[employee_id, s.demand.demand_id]
            for s in employee_slots
            if _is_weekend(s.demand.start_datetime.date())
        ]
        hours_var = model.new_int_var(0, MAX_MONTHLY_HOURS, f"weekend_hours_{employee_id}")
        model.add(hours_var == sum(terms) + fixed_weekend_hours.get(employee_id, 0))
        weekend_hours_vars.append(hours_var)

    max_weekend = model.new_int_var(0, MAX_MONTHLY_HOURS, "weekend_hours_max")
    min_weekend = model.new_int_var(0, MAX_MONTHLY_HOURS, "weekend_hours_min")
    model.add_max_equality(max_weekend, weekend_hours_vars)
    model.add_min_equality(min_weekend, weekend_hours_vars)
    penalties.append(WEEKEND_FAIRNESS_WEIGHT * (max_weekend - min_weekend))


def add_holiday_fairness(
    model: cp_model.CpModel, x: dict, by_employee: dict[str, list],
    holiday_dates: set, historical_holiday_hours: dict[str, int], penalties: list,
) -> None:
    """Holiday fairness (arch/spec.md SECTION 3): prefer variants that reduce
    historical inequality of holiday work, derived from
    state.holiday_history (persisted REALIZED Assignments on
    CalendarDay(holiday=true)) -- not law, purely SOFT.

    FINDING R20-1 (tests_r20.txt): an earlier version penalized by a fixed
    pre-solve rank (least-historically-loaded employee = free), which stayed
    constant regardless of how many holiday-dated demands this run actually
    assigned to whom -- so it kept preferring the same employee past the
    point where doing so made the final distribution *more* unequal than an
    achievable alternative. Mirrors add_weekend_fairness instead: minimize
    the max-min spread of each employee's total holiday hours (historical +
    this run), which is monotonic in the actual resulting inequality."""
    if not holiday_dates or len(by_employee) < 2:
        return
    holiday_hours_vars = []
    for employee_id, employee_slots in by_employee.items():
        terms = [
            _demand_hours(s.demand) * x[employee_id, s.demand.demand_id]
            for s in employee_slots
            if s.demand.start_datetime.date() in holiday_dates
        ]
        hours_var = model.new_int_var(0, MAX_MONTHLY_HOURS, f"holiday_hours_{employee_id}")
        model.add(hours_var == sum(terms) + historical_holiday_hours.get(employee_id, 0))
        holiday_hours_vars.append(hours_var)

    max_holiday = model.new_int_var(0, MAX_MONTHLY_HOURS, "holiday_hours_max")
    min_holiday = model.new_int_var(0, MAX_MONTHLY_HOURS, "holiday_hours_min")
    model.add_max_equality(max_holiday, holiday_hours_vars)
    model.add_min_equality(min_holiday, holiday_hours_vars)
    penalties.append(HOLIDAY_FAIRNESS_WEIGHT * (max_holiday - min_holiday))


if __name__ == "__main__":
    print("fairness module OK")
