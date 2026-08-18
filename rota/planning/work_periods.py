"""ROTA-T012 Part B: pure work-period/rest semantics, shared by the CP-SAT
constraint builder (rota.planning.constraints) and the independent HARD
validator (rota.planning.validator). No CP-SAT, no persistence I/O --
callers normalize whatever they have (SolverSlot/ShiftDemand for the
not-yet-decided solver side, Assignment for the already-decided validator/
cross-site side) into PeriodComponent first.

WYMAGANIA REST (tasks/ROTA-T012/part_b_work_period_rest.md):
1. After work period A, before B: gap >= A.required_rest_after_hours.
2. B's rest never applies backward onto the wall after A (directional).
3. Two components of the SAME work period have no internal REST.
4. Two DIFFERENT work periods must not overlap.
5. A normal 24h pair is one period, component 1 start to component 2 end,
   with the pair's configured 24h rest.
6. A plain 12h/INNY period has its own configured rest.
7. A legacy Assignment with no provenance is its own standalone period,
   rest 11h (REST_MIN_HOURS).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from rota.constants import REST_MIN_HOURS
from rota.domain import AssignmentRole, AssignmentState, ShiftCatalogKind


def resolve_required_rest(value: Optional[int]) -> int:
    """Legacy/missing rest provenance defaults to REST_MIN_HOURS (11h) --
    the only place that compatibility fallback still applies after T012."""
    return value if value is not None else REST_MIN_HOURS


@dataclass(frozen=True)
class PeriodComponent:
    component_id: str
    employee_id: str
    start: datetime
    end: datetime
    # None (legacy, or a standalone 12h/INNY occurrence) means this
    # component is its own period -- never merged with any other
    # component, even one with the same None period_id.
    period_id: Optional[str]
    required_rest_after_hours: Optional[int]
    # Only meaningful for find_malformed_periods (validator use) -- None for
    # solver-side prospective components, which cannot be malformed by
    # construction.
    schedule_version_id: Optional[str] = None


@dataclass(frozen=True)
class WorkPeriod:
    employee_id: str
    period_key: str
    start: datetime
    end: datetime
    required_rest_after_hours: int
    component_ids: tuple[str, ...]
    # (schedule_version_id, component_id) pairs, parallel to component_ids --
    # this system's real Assignment identity (tests/test_audit_t009_r6.py),
    # used for target-vs-history membership tests. component_ids alone
    # stays the bare local id, since that is what callers report/compare
    # against real assignment_ids elsewhere (e.g. engine.py).
    component_keys: tuple[tuple[Optional[str], str], ...] = ()


def _period_key(component: PeriodComponent) -> tuple[str, str]:
    if component.period_id:
        return (component.employee_id, component.period_id)
    # Real identity is (schedule_version_id, assignment_id), not the bare
    # local id alone (tests/test_audit_t009_r6.py: two different
    # ScheduleVersions can legitimately reuse the same local assignment_id)
    # -- component_id itself stays the raw assignment_id for reporting.
    return (component.employee_id, f"__standalone__{component.schedule_version_id}:{component.component_id}")


def _group_by_period(components: list[PeriodComponent]) -> dict[tuple[str, str], list[PeriodComponent]]:
    groups: dict[tuple[str, str], list[PeriodComponent]] = {}
    for c in components:
        groups.setdefault(_period_key(c), []).append(c)
    return groups


def group_into_periods(components: list[PeriodComponent]) -> list[WorkPeriod]:
    """Groups by (employee_id, period_id); a None period_id becomes its own
    singleton group keyed by the component's own id, so two independent
    legacy/standalone components are never merged just for sharing None.

    The period's resolved rest comes from its LATEST (highest start)
    component -- the cross-month emergency-extension shape (T012 brief
    ARCHITECTURE DECISIONS #6): an earlier, already-persisted component may
    carry a different historical rest snapshot than the later component
    that actually governs the gap after this period ends."""
    periods = []
    for (employee_id, period_key), members in _group_by_period(components).items():
        ordered = sorted(members, key=lambda m: m.start)
        rest = resolve_required_rest(ordered[-1].required_rest_after_hours)
        periods.append(WorkPeriod(
            employee_id, period_key, ordered[0].start, max(m.end for m in ordered), rest,
            tuple(m.component_id for m in ordered),
            tuple((m.schedule_version_id, m.component_id) for m in ordered),
        ))
    return periods


def find_malformed_periods(components: list[PeriodComponent]) -> list[tuple[str, tuple[str, ...], list[str]]]:
    """Fail-closed shape check (validator use):
    - a period may not have more than 2 components;
    - components sharing a period must form a directly continuous,
      non-overlapping chain (prev.end == cur.start) -- a gap or overlap
      between them is corruption, not two rest-checkable periods;
    - explicit (non-legacy, period_id is not None) T012 provenance must
      supply a non-negative required_rest_after_hours -- missing/negative
      is corruption and is NEVER silently defaulted to the legacy 11h
      fallback (that fallback is legacy-only, i.e. period_id is None);
    - components created together in the SAME ScheduleVersion must agree
      on required_rest_after_hours -- an explicit mismatch there is
      corruption, not the legitimate cross-month emergency extension
      (which spans two different schedule_version_id values and is
      exempt). Returns (period_key, component_ids, reasons) tuples, empty
      when nothing is malformed."""
    findings = []
    for (_employee_id, period_key), members in _group_by_period(components).items():
        reasons = []
        if len(members) > 2:
            reasons.append(f"{len(members)} components (max 2)")
        ordered = sorted(members, key=lambda m: m.start)
        for prev, cur in zip(ordered, ordered[1:]):
            if prev.end != cur.start:
                reasons.append(f"{prev.component_id}->{cur.component_id} not directly continuous (gap or overlap)")
        by_version: dict[Optional[str], set[int]] = {}
        for m in ordered:
            if m.period_id is None:
                continue
            if m.required_rest_after_hours is None or m.required_rest_after_hours < 0:
                reasons.append(f"{m.component_id}: explicit work_period_id requires non-negative required_rest_after_hours, got {m.required_rest_after_hours!r}")
                continue
            by_version.setdefault(m.schedule_version_id, set()).add(m.required_rest_after_hours)
        for version_id, rests in by_version.items():
            if len(rests) > 1:
                reasons.append(f"inconsistent rest within schedule_version_id={version_id}: {sorted(rests)}")
        if reasons:
            findings.append((period_key, tuple(m.component_id for m in ordered), reasons))
    return findings


def periods_overlap(a: WorkPeriod, b: WorkPeriod) -> bool:
    return a.start < b.end and b.start < a.end


def violates_rest(earlier: WorkPeriod, later: WorkPeriod) -> bool:
    """Caller guarantees earlier.start <= later.start (or passes either
    order -- overlap is symmetric and directionality is resolved here)."""
    if later.start < earlier.start:
        earlier, later = later, earlier
    if periods_overlap(earlier, later):
        return True
    gap_hours = (later.start - earlier.end).total_seconds() / 3600
    return gap_hours < earlier.required_rest_after_hours


def _is_plain_12h(demand) -> bool:
    return (
        demand.catalog_kind == ShiftCatalogKind.H12
        and demand.end_datetime - demand.start_datetime == timedelta(hours=12)
    )


@dataclass(frozen=True)
class EmergencyPairCandidate:
    first_demand_id: str
    second_demand_id: str
    rest_hours: int


def find_same_month_pair_candidates(shift_demands) -> list[EmergencyPairCandidate]:
    """T012 Part C (part_c_emergency_24h.md PAIR CANDIDATE): pure structural
    detection, no CP-SAT/persistence/eligibility. A same-month emergency pair
    is two contiguous plain 12h demands with opposite D/N and an explicit
    emergency_24h_rest_hours snapshot on the earlier one. Which employee(s)
    may actually use a candidate (base eligibility, can_work_24h) is decided
    by the caller, not here."""
    by_start: dict[datetime, list] = {}
    for demand in shift_demands:
        by_start.setdefault(demand.start_datetime, []).append(demand)
    candidates = []
    for first in shift_demands:
        if not _is_plain_12h(first) or first.emergency_24h_rest_hours is None:
            continue
        for second in by_start.get(first.end_datetime, []):
            if not _is_plain_12h(second):
                continue
            if first.shift_kind is None or second.shift_kind is None or first.shift_kind == second.shift_kind:
                continue
            candidates.append(EmergencyPairCandidate(first.demand_id, second.demand_id, first.emergency_24h_rest_hours))
    return candidates


@dataclass(frozen=True)
class CrossMonthPairCandidate:
    employee_id: str
    current_demand_id: str
    boundary_work_period_id: str
    rest_hours: int


def find_cross_month_pair_candidates(
    boundary_assignments, boundary_shift_demands, shift_demands,
) -> list[CrossMonthPairCandidate]:
    """T012 Part C section 3 (Reprezentacja techniczna): pure structural
    detection of a persisted boundary Assignment eligible to be the first
    half of a cross-month emergency pair with a CURRENT-month plain 12h
    demand. Eligibility/can_work_24h and which employee CP-SAT actually
    assigns are decided by the caller, not here."""
    demand_by_key = {(d.schedule_version_id, d.demand_id): d for d in boundary_shift_demands}
    live = [a for a in boundary_assignments if a.state != AssignmentState.CANCELLED]
    component_count: dict[tuple[str, str], int] = {}
    for a in live:
        if a.work_period_id:
            key = (a.employee_id, a.work_period_id)
            component_count[key] = component_count.get(key, 0) + 1

    candidates = []
    for a in live:
        if a.role != AssignmentRole.PRIMARY or not a.covers_demand_id or not a.work_period_id:
            continue
        boundary_demand = demand_by_key.get((a.schedule_version_id, a.covers_demand_id))
        if boundary_demand is None or not _is_plain_12h(boundary_demand) or boundary_demand.shift_kind is None:
            continue
        if boundary_demand.emergency_24h_rest_hours is None:
            continue
        if component_count.get((a.employee_id, a.work_period_id), 0) != 1:
            continue
        for demand in shift_demands:
            if not _is_plain_12h(demand) or demand.start_datetime != a.end_datetime:
                continue
            if demand.shift_kind is None or demand.shift_kind == boundary_demand.shift_kind:
                continue
            candidates.append(CrossMonthPairCandidate(
                a.employee_id, demand.demand_id, a.work_period_id, boundary_demand.emergency_24h_rest_hours,
            ))
    return candidates


@dataclass(frozen=True)
class EmergencyPeriodFinding:
    assignment_ids: tuple[str, ...]
    code: str
    reason: str


def check_emergency_pair_structure(
    members: list, demand_by_key: dict, can_work_24h: bool, all_24h_profile: bool,
) -> list[EmergencyPeriodFinding]:
    """T012 Part C section 11: independent structural re-check of one
    (employee, work_period_id) group already known to be emergency-shaped
    (no H24 demand among its components) -- caller decides which groups
    qualify and never trusts the solver's own pair literals. `members` are
    Assignment-shaped objects (.assignment_id/.start_datetime/.end_datetime/
    .required_rest_after_hours/.covers_demand_id/.schedule_version_id)."""
    ordered = sorted(members, key=lambda m: m.start_datetime)
    ids = tuple(m.assignment_id for m in ordered)
    if len(ordered) != 2:
        return [EmergencyPeriodFinding(ids, "SHIFT-24-PAIR-01", f"{len(ordered)} emergency components (expected 2)")]
    first, second = ordered
    first_d = demand_by_key.get((first.schedule_version_id, first.covers_demand_id))
    second_d = demand_by_key.get((second.schedule_version_id, second.covers_demand_id))
    if first_d is None or second_d is None:
        return [EmergencyPeriodFinding(ids, "SHIFT-24-PAIR-01", "missing demand provenance for an emergency component")]
    problems = []
    if not _is_plain_12h(first_d) or not _is_plain_12h(second_d):
        problems.append("not both plain 12h (INNY or mismatched catalog_kind)")
    if first_d.shift_kind is None or second_d.shift_kind is None or first_d.shift_kind == second_d.shift_kind:
        problems.append("shift_kind not opposite D/N")
    if first.end_datetime != second.start_datetime:
        problems.append("not directly continuous")
    if first_d.emergency_24h_rest_hours is None:
        problems.append("first demand has no emergency_24h_rest_hours snapshot")
    elif second.required_rest_after_hours != first_d.emergency_24h_rest_hours:
        problems.append(f"terminal rest {second.required_rest_after_hours} != emergency snapshot {first_d.emergency_24h_rest_hours}")
    if problems:
        return [EmergencyPeriodFinding(ids, "SHIFT-24-PAIR-01", "; ".join(problems))]
    if not can_work_24h and not all_24h_profile:
        return [EmergencyPeriodFinding(ids, "SHIFT-24-01", "employee lacks can_work_24h on a mixed profile")]
    return []


if __name__ == "__main__":
    print("planning.work_periods module OK")
