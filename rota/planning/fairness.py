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
TARGET_EQUITY_WEIGHT = 1
DN_RHYTHM_REWARD_WEIGHT = 1
THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT = 1
MAX_COMPLETION_PCT = 100 * MAX_MONTHLY_HOURS


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


def _holiday_hours_upper_bound(by_employee: dict[str, list], holiday_dates: set, historical_holiday_hours: dict[str, int]) -> int:
    """FINDING R22-1: bound each employee's possible total (historical +
    every holiday-dated demand they could take this run), not a fixed
    monthly constant -- historical_holiday_hours is cumulative and can
    legitimately exceed one month's hours."""
    return max(
        (
            historical_holiday_hours.get(employee_id, 0)
            + sum(_demand_hours(s.demand) for s in employee_slots if s.demand.start_datetime.date() in holiday_dates)
            for employee_id, employee_slots in by_employee.items()
        ),
        default=0,
    )


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
    this run), which is monotonic in the actual resulting inequality.

    FINDING R22-1 (tests_r22.txt): the per-employee hours_var domain was
    hardcoded to 0..MAX_MONTHLY_HOURS (744). historical_holiday_hours is a
    cumulative, potentially multi-year figure with no reason to stay under
    one month's hours -- a legitimately large history (e.g. 63 historical
    12h holiday shifts = 756h) fell outside that domain and made the whole
    CP-SAT model INFEASIBLE/invalid on a SOFT term, even though the current
    demand had a perfectly HARD-valid solution. The domain is now sized per
    run from the actual historical hours plus every holiday-dated demand's
    hours this run, not a fixed constant."""
    if not holiday_dates or len(by_employee) < 2:
        return
    upper_bound = _holiday_hours_upper_bound(by_employee, holiday_dates, historical_holiday_hours)

    holiday_hours_vars = []
    for employee_id, employee_slots in by_employee.items():
        terms = [
            _demand_hours(s.demand) * x[employee_id, s.demand.demand_id]
            for s in employee_slots
            if s.demand.start_datetime.date() in holiday_dates
        ]
        hours_var = model.new_int_var(0, upper_bound, f"holiday_hours_{employee_id}")
        model.add(hours_var == sum(terms) + historical_holiday_hours.get(employee_id, 0))
        holiday_hours_vars.append(hours_var)

    max_holiday = model.new_int_var(0, upper_bound, "holiday_hours_max")
    min_holiday = model.new_int_var(0, upper_bound, "holiday_hours_min")
    model.add_max_equality(max_holiday, holiday_hours_vars)
    model.add_min_equality(min_holiday, holiday_hours_vars)
    penalties.append(HOLIDAY_FAIRNESS_WEIGHT * (max_holiday - min_holiday))


def add_target_equity_fairness(
    model: cp_model.CpModel, worked_hours_by_employee: dict[str, object],
    effective_targets: dict[str, int], penalties: list,
) -> None:
    """TARGET EQUITY (ROTA-T032 section 4, owner-corrected 2026-08-25): after
    TARGET-01 is proven OPTIMAL and frozen by the caller (solver.py), prefer
    a smaller spread of completion_pct = floor(100 * actual_hours /
    effective_target) among employees with effective_target > 0.
    effective_target == 0 is excluded from this ratio only -- TARGET-01
    itself still counts that employee's deviation from 0 on its own frozen
    phase; never a division by zero here. worked_hours_by_employee must
    already be the exact IntVar TARGET-01 solved for (single owner of actual
    hours, section 4.1) -- this function never recomputes worked hours."""
    completion_vars = []
    for employee_id, target in effective_targets.items():
        if target <= 0:
            continue
        worked = worked_hours_by_employee.get(employee_id)
        if worked is None:
            continue
        completion = model.new_int_var(0, MAX_COMPLETION_PCT, f"completion_pct_{employee_id}")
        model.add_division_equality(completion, worked * 100, target)
        completion_vars.append(completion)
    if len(completion_vars) < 2:
        return
    max_completion = model.new_int_var(0, MAX_COMPLETION_PCT, "completion_pct_max")
    min_completion = model.new_int_var(0, MAX_COMPLETION_PCT, "completion_pct_min")
    model.add_max_equality(max_completion, completion_vars)
    model.add_min_equality(min_completion, completion_vars)
    penalties.append(TARGET_EQUITY_WEIGHT * (max_completion - min_completion))


def _exactly_one(model: cp_model.CpModel, term: object, name: str) -> object:
    """Collapse a possibly-summed CP-SAT term into a tight 'exactly one'
    boolean -- only called lazily, per window, for a term that already
    survived every cheap skip in add_dn_rhythm_reward (never eagerly for
    the whole month, see that function's docstring)."""
    is_one = model.new_bool_var(name)
    model.add(term == 1).only_enforce_if(is_one)
    model.add(term != 1).only_enforce_if(is_one.Not())
    return is_one


def _occupied_bool(model: cp_model.CpModel, term: object, name: str) -> object:
    """ROTA-T040: tight Boolean 'occupied <=> term >= 1' for a non-negative
    CP-SAT count term -- never treat the raw count itself as if it were
    already 0/1. any_term is a SUM of non-CANCELLED starts on one date
    (solver._build_day_kind_terms), which for a normal H24 occurrence is
    2 (SHIFT-24-PAIR-01 forces its D and N components to the same
    employee, both starting the same date) -- using any_term directly in
    `match + any_term <= 1` silently forced the H24 employee's own
    assignment to 0 even when match was already 0, turning this pure SOFT
    reward into an accidental HARD ban on legal H24 assignments. Only
    called lazily for a term that already survived every cheap skip below
    (same reasoning as _exactly_one)."""
    occupied = model.new_bool_var(name)
    model.add(term >= 1).only_enforce_if(occupied)
    model.add(term == 0).only_enforce_if(occupied.Not())
    return occupied


def add_dn_rhythm_reward(
    model: cp_model.CpModel, month, day_kind_terms: dict[str, dict], penalties: list,
) -> int:
    """D -> N -> wolne -> wolne REWARD (ROTA-T032 section 5, owner decision
    2026-08-25): same-month only, no shared phase between employees -- a
    loose per-employee preference, never a rigid brigade rotation. For every
    window of four consecutive start dates (d, d+1, d+2, d+3) fully inside
    `month`, a match exists only when d is exactly D, d+1 is exactly N, and
    neither d+2 nor d+3 has any non-CANCELLED start for that employee.

    day_kind_terms[employee_id][date] is (d_term, n_term, any_term, n_demand_id),
    built once by solver.py._build_day_kind_terms from the same source
    add_max_two_consecutive_night_constraints/validator._check_night_streak
    use for D/N classification (the reward can never disagree with the HARD
    rule about what counts as D or N). d_term/n_term/any_term may be raw
    sums there -- this function tightens d_term/n_term to 'exactly one'
    lazily, per window, only when a window survives every cheap skip below
    (never eagerly for the whole month: an earlier version that reified
    every date up front measurably slowed down every solve, including ones
    with this reward disabled entirely, since it bloated the shared model
    itself for no benefit those solves ever used).

    Correction (2026-08-25, isolated timing measurement): match is encoded
    with ONLY the upper-bound implications (match <= each literal),
    mirroring constraints.py's own emergency-24h pair-literal pattern
    (_create_pair_literals) -- since this is a pure reward with nothing else
    forcing match down, a linear objective MAXIMIZING sum(match) already
    pushes every match to 1 whenever all literals allow it, so no reverse
    ">=4 vs <=3" reified branch is needed. That reverse branch produced a
    very weak LP relaxation bound (a large optimality gap CP-SAT could not
    close in useful time) for no behavioural benefit -- dropping it changes
    nothing about what the model can optimize to, only how fast it proves it."""
    import calendar as _calendar
    from datetime import timedelta as _timedelta
    num_days = _calendar.monthrange(month.year, month.month)[1]
    month_start = month.replace(day=1)
    _empty = (0, 0, 0, None)
    match_terms = []
    # ROTA-T040: one lazily-created occupancy literal per (employee_id, date),
    # reused across the overlapping 4-day windows that share a date -- never
    # eagerly booleanized for the whole month (same performance reasoning as
    # d_bool/n_bool above).
    occupied_cache: dict[tuple[str, object], object] = {}
    for employee_id, by_date in day_kind_terms.items():
        window_start = month_start
        last_start = month_start + _timedelta(days=num_days - 4)
        while window_start <= last_start:
            d0, d1, d2, d3 = (window_start + _timedelta(days=i) for i in range(4))
            d_term = by_date.get(d0, _empty)[0]
            n_term = by_date.get(d1, _empty)[1]
            any2 = by_date.get(d2, _empty)[2]
            any3 = by_date.get(d3, _empty)[2]
            if (isinstance(d_term, int) and d_term == 0) or (isinstance(n_term, int) and n_term == 0):
                # Neither literal can ever be 1 -- this window can never
                # match, skip it entirely: no variable, no constraint.
                window_start += _timedelta(days=1)
                continue
            if (isinstance(any2, int) and any2 > 0) or (isinstance(any3, int) and any3 > 0):
                # d+2 or d+3 is guaranteed occupied -- can never be "wolne".
                window_start += _timedelta(days=1)
                continue
            free2_proven = isinstance(any2, int)  # already known ==0 above
            free3_proven = isinstance(any3, int)
            if isinstance(d_term, int) and isinstance(n_term, int) and free2_proven and free3_proven:
                if d_term == 1 and n_term == 1:
                    match_terms.append(1)
                window_start += _timedelta(days=1)
                continue
            # Lazily tighten to "exactly one" only for a window that already
            # survived every cheap skip above (owner correction point 2,
            # 2026-08-25) -- doing this eagerly for every day of the month
            # regardless of use (as an earlier version did) measurably
            # slowed down every solve, including ones with the reward
            # disabled entirely, since it bloated the shared model itself.
            d_bool = d_term if isinstance(d_term, int) else _exactly_one(model, d_term, f"is_d_{employee_id}_{d0.isoformat()}")
            n_bool = n_term if isinstance(n_term, int) else _exactly_one(model, n_term, f"is_n_{employee_id}_{d1.isoformat()}")
            match = model.new_bool_var(f"dn_rhythm_{employee_id}_{d0.isoformat()}")
            model.add(match <= d_bool)
            model.add(match <= n_bool)
            if not free2_proven:
                key2 = (employee_id, d2)
                if key2 not in occupied_cache:
                    occupied_cache[key2] = _occupied_bool(model, any2, f"occupied_{employee_id}_{d2.isoformat()}")
                model.add(match + occupied_cache[key2] <= 1)
            if not free3_proven:
                key3 = (employee_id, d3)
                if key3 not in occupied_cache:
                    occupied_cache[key3] = _occupied_bool(model, any3, f"occupied_{employee_id}_{d3.isoformat()}")
                model.add(match + occupied_cache[key3] <= 1)
            match_terms.append(match)
            window_start += _timedelta(days=1)
    if not match_terms:
        return 0
    penalties.append(-DN_RHYTHM_REWARD_WEIGHT * sum(match_terms))
    # OWNER_CORRECTED 2026-08-25: the caller uses this count -- the maximum
    # possible reward this call could ever contribute (every match_terms[i]
    # is bounded above by 1) -- to size TARGET_DEVIATION_WEIGHT so target
    # accuracy can never be knowingly traded for rhythm (see
    # solver._add_combined_objective).
    return len(match_terms)


def add_third_consecutive_shift_penalty(
    model: cp_model.CpModel, month, day_kind_terms: dict[str, dict], penalties: list,
) -> int:
    """SOFT: prefer avoiding a third consecutive day-shift-adjacent sequence
    (ROTA-T034, owner ruling 2026-08-26, contract SHA f4a1e0b). For every
    window of three consecutive start dates (d, d+1, d+2) intersecting
    `month` (first possible start month_start-2 days, last month_end), one
    bad_window bool is active iff D/D/D, D/D/N or D/N/N holds (D = existing
    d_term==1, N = existing n_term==1, same day_kind_terms NIGHT-STREAK-01
    and add_dn_rhythm_reward already share -- no second D/N classifier, no
    second boundary read). One window contributes at most one penalty
    regardless of how many of the three patterns match. N/N/N is out of
    scope -- it stays exclusively NIGHT-STREAK-01 HARD.

    A window built only from already-fixed/boundary facts (no decision
    variable involved) is skipped entirely -- contract section 3.2: it
    cannot change this solve's ranking, so it must not enter the objective
    at all, even as a constant (unlike add_dn_rhythm_reward's own eager-match
    branch, which still counts a fully-fixed match as a constant reward)."""
    import calendar as _calendar
    from datetime import timedelta as _timedelta
    num_days = _calendar.monthrange(month.year, month.month)[1]
    month_start = month.replace(day=1)
    month_end = month_start + _timedelta(days=num_days - 1)
    first_start = month_start - _timedelta(days=2)
    _empty = (0, 0, 0, None)
    lit_cache: dict[tuple, object] = {}

    def _is_zero(v: object) -> bool:
        return isinstance(v, int) and v == 0

    def _is_one(v: object) -> bool:
        return isinstance(v, int) and v == 1

    def _lit(employee_id: str, d, raw_term: object, kind: str) -> object:
        if isinstance(raw_term, int):
            return raw_term
        key = (employee_id, d, kind)
        cached = lit_cache.get(key)
        if cached is not None:
            return cached
        lit = _exactly_one(model, raw_term, f"t34_is_{kind}_{employee_id}_{d.isoformat()}")
        lit_cache[key] = lit
        return lit

    bad_windows = []
    for employee_id, by_date in day_kind_terms.items():
        window_start = first_start
        while window_start <= month_end:
            d0, d1, d2 = window_start, window_start + _timedelta(days=1), window_start + _timedelta(days=2)
            d0_raw = by_date.get(d0, _empty)[0]
            d1_raw, n1_raw = by_date.get(d1, _empty)[0], by_date.get(d1, _empty)[1]
            d2_raw, n2_raw = by_date.get(d2, _empty)[0], by_date.get(d2, _empty)[1]

            raw_patterns = [
                (d0_raw, d1_raw, d2_raw),  # D / D / D
                (d0_raw, d1_raw, n2_raw),  # D / D / N
                (d0_raw, n1_raw, n2_raw),  # D / N / N
            ]
            possible = [not any(_is_zero(v) for v in p) for p in raw_patterns]
            if not any(possible):
                # Every pattern is already provably false -- this window can
                # never match, skip it entirely: no variable, no constraint.
                window_start += _timedelta(days=1)
                continue
            if any(possible[i] and all(_is_one(v) for v in raw_patterns[i]) for i in range(3)):
                # A fully-fixed match -- constant, cannot change this solve's
                # ranking, must not enter the objective (contract 3.2).
                window_start += _timedelta(days=1)
                continue
            if all(isinstance(v, int) for i in range(3) if possible[i] for v in raw_patterns[i]):
                # Fully fixed and provably not a match -- also constant.
                window_start += _timedelta(days=1)
                continue

            # Lazily tighten only for a window that already survived every
            # cheap skip above (mirrors add_dn_rhythm_reward's own timing
            # correction) -- never eagerly for the whole month.
            lit0d = _lit(employee_id, d0, d0_raw, "d")
            lit1d = _lit(employee_id, d1, d1_raw, "d")
            lit2d = _lit(employee_id, d2, d2_raw, "d")
            lit1n = _lit(employee_id, d1, n1_raw, "n")
            lit2n = _lit(employee_id, d2, n2_raw, "n")
            lit_patterns = [
                (lit0d, lit1d, lit2d),
                (lit0d, lit1d, lit2n),
                (lit0d, lit1n, lit2n),
            ]

            bad_window = model.new_bool_var(f"third_shift_{employee_id}_{d0.isoformat()}")
            for i in range(3):
                if not possible[i]:
                    continue
                a, b, c = lit_patterns[i]
                model.add(bad_window >= a + b + c - 2)
            bad_windows.append(bad_window)
            window_start += _timedelta(days=1)

    if not bad_windows:
        return 0
    penalties.append(THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT * sum(bad_windows))
    return len(bad_windows)


if __name__ == "__main__":
    print("fairness module OK")
