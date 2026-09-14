"""Independent HARD validator (anti-drift rule 12, arch/spec.md SECTION 2/5).
Re-derives every HARD violation from PlanningState + a final Assignment list, from scratch, without CP-SAT.

2026-09 oversized-file refactor (owner-authorized, mechanical-only, zero
product-behavior change): the individual _check_* functions now live in
topic-grouped sibling modules (validator_checks_integrity.py,
validator_checks_availability.py, validator_checks_patterns.py,
validator_checks_rest_and_load.py), sharing dataclasses/pure helpers from
validator_shared.py. This module is the thin orchestrator: it imports
every check, calls them in the exact original order, and re-exports the
public names (ViolationDetail, IndependentValidationReport,
coverage_segments) so every existing external import path
(`from rota.planning.validator import ...`) keeps working unchanged --
see tests/test_t023.py::test_t23_55_shared_coverage_helper_used_by_validator_and_t023_capture
for the one frozen contract on coverage_segments's import path."""
from __future__ import annotations

from rota.domain import Assignment, AssignmentState
from rota.planning.state import PlanningState
from rota.planning.validator_checks_availability import (
    _check_day_only,
    _check_day_shift_off,
    _check_external,
    _check_leave_and_unavailable,
    _check_leave_plan,
    _check_membership_enabled,
    _check_role,
    _check_site_rules,
    _check_unavailable_time_window,
)
from rota.planning.validator_checks_integrity import (
    _check_coverage,
    _check_full_hour,
    _check_replan_preserves_fixed,
    _check_trainee_mentor_reference,
)
from rota.planning.validator_checks_patterns import (
    _check_24h_same_person,
    _check_emergency_pairs,
    _check_night_streak,
    _check_third_consecutive_shift,
)
from rota.planning.validator_checks_rest_and_load import _check_load, _check_rest, _check_weekly_rest
from rota.planning.validator_shared import (
    IndependentValidationReport,
    ViolationDetail,
    _monthly_hours,
    _not_cancelled,
    coverage_segments,
)

__all__ = [
    "ViolationDetail",
    "IndependentValidationReport",
    "coverage_segments",
    "validate",
]


def validate(state: PlanningState, assignments: list[Assignment]) -> IndependentValidationReport:
    """Recheck every HARD rule from scratch against the final Assignment set."""
    details: list[ViolationDetail] = []
    warnings: list[str] = []
    # T022-R2-2: full-hour is a structural input-shape check, not a real-work check -- it must see every Assignment
    # including CANCELLED, before state-based filtering makes a malformed boundary invisible.
    _check_full_hour(state, assignments, details)
    assignments = _not_cancelled(assignments)

    # REPLAN (ASSIGN-03: REALIZED work MUST NOT be changed): eligibility/availability HARD checks (membership,
    # DAY_ONLY, DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, EXTERNAL-01) only make sense going forward -- data
    # recorded after the fact must not retroactively break FEASIBLE for something REPLAN must leave untouched.
    # COVERAGE-01, ASSIGN-03/04, REST-01 and LOAD-01 still consider every assignment (real elapsed time/identity).
    for_eligibility_checks = [a for a in assignments if a.state != AssignmentState.REALIZED]

    _check_coverage(state, assignments, details)
    _check_replan_preserves_fixed(state, assignments, details)
    _check_trainee_mentor_reference(assignments, details)
    _check_membership_enabled(state, for_eligibility_checks, details)
    _check_role(state, for_eligibility_checks, details)
    _check_day_only(state, for_eligibility_checks, details, warnings)
    _check_night_streak(state, assignments, details)
    _check_third_consecutive_shift(state, assignments, details)
    _check_day_shift_off(state, for_eligibility_checks, details, warnings)
    _check_leave_and_unavailable(state, for_eligibility_checks, details)
    _check_unavailable_time_window(state, for_eligibility_checks, details)
    _check_leave_plan(state, for_eligibility_checks, warnings)
    _check_external(state, for_eligibility_checks, details)
    _check_site_rules(state, for_eligibility_checks, details)
    _check_24h_same_person(state, assignments, details)
    _check_emergency_pairs(state, assignments, details)
    min_rest = _check_rest(state, assignments, details, warnings)
    _check_weekly_rest(state, assignments, details, warnings)
    max_load, max_window, max_window_datetimes = _check_load(state, assignments, details)

    return IndependentValidationReport(
        hard_pass=not details,
        violations=[d.message for d in details],
        violation_details=details,
        warnings=warnings,
        monthly_hours=_monthly_hours(state, assignments),
        minimum_rest_hours=min_rest,
        maximum_rolling_7d_window=max_window,
        maximum_rolling_7d_window_datetimes=max_window_datetimes,
        maximum_rolling_7d_hours=max_load,
    )


if __name__ == "__main__":
    print("validator module OK")
