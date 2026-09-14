"""Shared dataclasses and pure helpers for rota.planning.validator's split
check modules (validator_checks_*.py). No behavior here -- straight
extraction from validator.py as part of the 2026-09 oversized-file
refactor (owner-authorized, mechanical-only, zero product-behavior
change). Every _check_* module imports from here, never from validator.py
itself or from a sibling _check_* module, so the import graph stays a
simple DAG (validator.py depends on everything; nothing depends on
validator.py)."""
from __future__ import annotations

from dataclasses import dataclass, field

from rota.domain import Assignment, AssignmentRole
from rota.planning.shift_catalog import UnclassifiedShiftError, classify_demand
from rota.planning.state import PlanningState


@dataclass(frozen=True)
class ViolationDetail:
    """A HARD violation tagged with the rule and exact Assignment(s) it is about (R23-2: assignment_ids is
    authoritative, never parsed back out of message text -- assignment_id has no contractual format/length)."""

    rule: str
    assignment_ids: tuple[str, ...]
    message: str
    demand_ids: tuple[str, ...] = ()  # COVERAGE-01 gap/excess: only the demand can be blamed, no Assignment exists
    # ROTA-T036: explicit employee seam for REST-01/WEEKLY-REST-01 only -- the
    # persistent Deviation target for these two rules is this Employee, never
    # one of assignment_ids (which may be a cross-context boundary/other-site
    # Assignment not resolvable in the target ScheduleVersion). Every other
    # rule leaves this None and keeps its existing demand/assignment target.
    affected_employee_id: str | None = None


@dataclass
class IndependentValidationReport:
    hard_pass: bool
    violations: list[str] = field(default_factory=list)
    violation_details: list[ViolationDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    monthly_hours: dict[str, int] = field(default_factory=dict)
    minimum_rest_hours: float | None = None
    maximum_rolling_7d_hours: dict[str, float] = field(default_factory=dict)
    maximum_rolling_7d_window: dict[str, tuple] = field(default_factory=dict)
    # R5-1: raw datetime window bounds, for real hour-overlap relevance.
    maximum_rolling_7d_window_datetimes: dict[str, tuple] = field(default_factory=dict)


def _by_employee(assignments: list[Assignment]) -> dict[str, list[Assignment]]:
    grouped: dict[str, list[Assignment]] = {}
    for assignment in assignments:
        grouped.setdefault(assignment.employee_id, []).append(assignment)
    return grouped


def _not_cancelled(assignments) -> list[Assignment]:
    """CANCELLED Assignments are not actual work (arch/spec.md:257) and must not participate in any HARD check (R13-2)."""
    from rota.domain import AssignmentState

    return [a for a in assignments if a.state != AssignmentState.CANCELLED]


def coverage_segments(window_start, window_end, overlapping: list[tuple]) -> list[tuple]:
    """Sweep-line over [window_start, window_end): each resulting sub-segment
    has one well-defined coverage count -- how many of `overlapping`
    intervals fully contain it. Pure, general-purpose; the single shared
    coverage-overlap algorithm (R3-6, ROTA-T023 tests/test_t023.py T23-55):
    COVERAGE-01 below uses it for ShiftDemand-vs-PRIMARY-count coverage, the
    absence-reference repository module reuses it unchanged for
    per-employee-per-date PRIMARY overlap/ambiguity detection. Do not
    reimplement this sweep anywhere else -- import and call this."""
    points = sorted({window_start, window_end, *(p for iv in overlapping for p in iv)})
    segments = []
    for a, b in zip(points, points[1:]):
        if a >= b:
            continue
        count = sum(1 for s, e in overlapping if s <= a and b <= e)
        segments.append((a, b, count))
    return segments


def _coverage_violation_detail(demand, bad_segments: list[tuple]) -> ViolationDetail:
    first_start, first_end, first_count = bad_segments[0]
    kind = "gap" if first_count < demand.required_primary_count else "excess"
    return ViolationDetail(
        "COVERAGE-01", (),
        f"COVERAGE-01: demand {demand.demand_id} has a coverage {kind} in "
        f"{len(bad_segments)} interval(s), e.g. {first_count}/{demand.required_primary_count} "
        f"PRIMARY during {first_start}-{first_end}",
        demand_ids=(demand.demand_id,),
    )


def _attributed_overlap_intervals(assignment: Assignment, demand, demand_by_id: dict) -> list[tuple]:
    """ROTA-T045: single shared owner of "which sub-interval of this PRIMARY
    actually counts as coverage of this demand", reused by both COVERAGE-01
    and SHIFT-24-PAIR-01 (previously duplicated only in COVERAGE-01; T045
    fixed SHIFT-24-PAIR-01 falsely trusting raw time-overlap alone).

    ROTA-T041 OWNER-T041-01 section 4.2 / AUDIT-1 C-03: pure geometry over
    every PRIMARY overlapping a demand double-counted a PRIMARY that
    actually belongs to a DIFFERENT, independently legal, CONCURRENT
    demand -- two legal overlapping demands, one person each correctly
    tagged, produced a false COVERAGE-01 excess on both (arch/spec.md:58,
    485 and ROTA-T012 explicitly allow overlapping catalog occurrences,
    one demand per occurrence).

    covers_demand_id now disambiguates, but only where it matters: when
    the assignment's own tagged demand genuinely overlaps (competes in
    time with) the demand being checked, and only for the actually
    competing sub-interval. A ROTA-T022-accepted manual PRIMARY spanning
    two ADJACENT (non-overlapping) demands with a single tag is still
    counted by real time for both -- there is no competition to resolve
    there, so geometry alone still governs exactly as before (T022
    requires this: a spanning/manual PRIMARY's real covered time, not its
    tag, decides what it covers). A tag pointing nowhere in this version's
    demands, or whose own claimed target it doesn't actually overlap,
    falls back to plain geometry against whatever it really does overlap
    -- a false or absent tag can never hide real coverage.

    ROTA-T041 AUDIT round-2 FINDING T41-A-R2-03 (tests_r2.txt): the tag
    used to exclude the WHOLE assignment from `demand` once any part of the
    tagged demand and `demand` overlapped, even for a sub-interval where
    the tagged demand had already ended (or not yet started) and so was
    never actually competing there. Only the genuinely competing
    sub-interval (the overlap of the tagged demand and `demand` themselves)
    is now excluded; a non-concurrent tail/head of the same assignment
    still counts toward `demand` by plain geometry, exactly as T022
    requires for a spanning/manual PRIMARY."""
    a_start = max(assignment.start_datetime, demand.start_datetime)
    a_end = min(assignment.end_datetime, demand.end_datetime)
    if a_start >= a_end:
        return []
    excluded_start = excluded_end = None
    tagged = demand_by_id.get(assignment.covers_demand_id)
    if tagged is not None and tagged.demand_id != demand.demand_id:
        competes = tagged.start_datetime < demand.end_datetime and tagged.end_datetime > demand.start_datetime
        tag_is_real = assignment.start_datetime < tagged.end_datetime and assignment.end_datetime > tagged.start_datetime
        if competes and tag_is_real:
            excluded_start = max(tagged.start_datetime, demand.start_datetime)
            excluded_end = min(tagged.end_datetime, demand.end_datetime)
    if excluded_start is None:
        return [(a_start, a_end)]
    result = []
    if a_start < excluded_start:
        result.append((a_start, min(a_end, excluded_start)))
    if a_end > excluded_end:
        result.append((max(a_start, excluded_end), a_end))
    return result


def _covering_demand(assignment: Assignment, state: PlanningState):
    for demand in state.shift_demands:
        if demand.demand_id == assignment.covers_demand_id:
            return demand
    for demand in state.boundary_shift_demands:
        if demand.demand_id == assignment.covers_demand_id and demand.schedule_version_id == assignment.schedule_version_id:
            return demand
    return None


def _covered_demands(assignment: Assignment, state: PlanningState) -> list:
    """T022-F1: every state.shift_demands whose interval actually overlaps this Assignment (same interval-truth
    COVERAGE-01 uses) -- a spanning PRIMARY cannot hide a covered demand behind a different covers_demand_id tag.
    Falls back to the tagged demand only when the interval overlaps no current-month demand at all."""
    overlapping = [d for d in state.shift_demands if assignment.start_datetime < d.end_datetime and assignment.end_datetime > d.start_datetime]
    if overlapping:
        return overlapping
    demand = _covering_demand(assignment, state)
    return [demand] if demand is not None else []


def _demand_kind(demand, profile):
    # T022-R3-1: classify_demand is the frozen, single legacy-fallback implementation (brief.md:124-126) -- no local duplicate.
    try:
        return classify_demand(demand, profile)
    except UnclassifiedShiftError:
        return None


def _is_well_formed_normal_h24_pair(d1, d2) -> bool:
    """T022-F3: fail-closed shape check -- components 1 and 2, each exactly 12h, directly consecutive, opposite D/N,
    matching template id, and matching required_rest_hours/required_primary_count (T022-R1-3)."""
    if {d1.work_period_component, d2.work_period_component} != {1, 2}:
        return False
    first, second = (d1, d2) if d1.work_period_component == 1 else (d2, d1)
    if first.shift_kind is None or second.shift_kind is None or first.shift_kind == second.shift_kind:
        return False
    if first.end_datetime != second.start_datetime:
        return False
    if first.required_rest_hours != second.required_rest_hours or first.required_primary_count != second.required_primary_count:
        return False
    hours1 = (first.end_datetime - first.start_datetime).total_seconds() / 3600
    hours2 = (second.end_datetime - second.start_datetime).total_seconds() / 3600
    return hours1 == 12 and hours2 == 12


def _is_full_hour(dt) -> bool:
    return dt.minute == 0 and dt.second == 0 and dt.microsecond == 0


def _monthly_hours(state: PlanningState, assignments: list[Assignment]) -> dict[str, int]:
    hours: dict[str, int] = {}
    for assignment in assignments:
        if assignment.role != AssignmentRole.PRIMARY:
            continue
        worked = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        hours[assignment.employee_id] = hours.get(assignment.employee_id, 0) + worked
    return hours


if __name__ == "__main__":
    print("planning.validator_shared module OK")
