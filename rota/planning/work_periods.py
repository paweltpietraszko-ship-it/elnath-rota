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
from datetime import datetime
from typing import Optional

from rota.constants import REST_MIN_HOURS


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


def _period_key(component: PeriodComponent) -> tuple[str, str]:
    if component.period_id:
        return (component.employee_id, component.period_id)
    return (component.employee_id, f"__standalone__{component.component_id}")


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
        ))
    return periods


def find_malformed_periods(components: list[PeriodComponent]) -> list[tuple[str, tuple[str, ...], list[str]]]:
    """Fail-closed shape check (validator use): a period may not have more
    than 2 components, and components created together in the SAME
    ScheduleVersion must agree on required_rest_after_hours -- an explicit
    mismatch there is corruption, not the legitimate cross-month emergency
    extension (which spans two different schedule_version_id values and is
    exempt). Returns (period_key, component_ids, reasons) tuples, empty
    when nothing is malformed."""
    findings = []
    for (_employee_id, period_key), members in _group_by_period(components).items():
        reasons = []
        if len(members) > 2:
            reasons.append(f"{len(members)} components (max 2)")
        by_version: dict[Optional[str], set[int]] = {}
        for m in members:
            by_version.setdefault(m.schedule_version_id, set()).add(resolve_required_rest(m.required_rest_after_hours))
        for version_id, rests in by_version.items():
            if len(rests) > 1:
                reasons.append(f"inconsistent rest within schedule_version_id={version_id}: {sorted(rests)}")
        if reasons:
            findings.append((period_key, tuple(m.component_id for m in members), reasons))
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


if __name__ == "__main__":
    print("planning.work_periods module OK")
