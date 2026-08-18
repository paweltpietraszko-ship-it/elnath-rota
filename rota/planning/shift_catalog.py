"""SiteProfile shift catalog: legacy demand->StandardShift classification,
plus (ROTA-T012 Part A) ShiftCatalogKind normalization, StandardShift
validation, and per-profile ShiftDemand generation.

ShiftDemand only carries a start/end datetime (SECTION 1 arch/spec.md). The
solver and validator both need to know whether a given demand is a D or an N
occurrence to apply SHIFT-01/DAY_ONLY-01/DAY_SHIFT_OFF-01. classify_demand
matches by time-of-day against the profile's own standard_shifts, so this
works for any month or profile configuration -- ROTA-T012-generated demands
carry ShiftDemand.shift_kind explicitly and never need it, but legacy
demands (shift_kind=None) still rely on it.

A 24h catalog entry never becomes a new ShiftKind or a continuous 24h
demand: it always expands into two directly-consecutive 12h D/N
ShiftDemand components sharing one work_period_template_id (owner mandate
2026-08-18, arch/spec.md T012 amendment) -- the printed schedule grid keeps
its existing two-shifts-per-day layout.

Pure data expansion only: no roster/eligibility/solver semantics here (that
is rota.planning.eligibility/solver, and Part C's emergency pairing).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from rota.domain import ShiftCatalogKind, ShiftDemand, ShiftKind, SiteProfile, StandardShift


class UnclassifiedShiftError(Exception):
    """Raised when a ShiftDemand's time-of-day matches no StandardShift."""


class InvalidStandardShift(Exception):
    """Raised when a StandardShift's T012 fields violate the frozen shape
    rules (required_primary_count/required_rest_hours/active_weekdays/
    catalog_kind-vs-duration)."""


class AmbiguousEmergency24hCapability(Exception):
    """Raised when a profile has two matching 24h capabilities (same
    start time-of-day/kind) with different required_rest_hours -- a
    config/model error that must fail closed rather than guess which
    rest value an emergency rescue would owe."""


def classify_demand(demand: ShiftDemand, profile: SiteProfile) -> ShiftKind:
    """Return the ShiftKind of demand by matching its start time against profile shifts."""
    start_time = demand.start_datetime.time()
    for shift in profile.standard_shifts:
        if shift.start_time == start_time:
            return shift.kind
    raise UnclassifiedShiftError(
        f"demand {demand.demand_id} start {start_time} matches no StandardShift "
        f"in profile {profile.profile_id}"
    )


def standard_shift_for(kind: ShiftKind, profile: SiteProfile) -> StandardShift:
    """Return the StandardShift definition of the given kind from profile."""
    for shift in profile.standard_shifts:
        if shift.kind == kind:
            return shift
    raise UnclassifiedShiftError(f"profile {profile.profile_id} has no StandardShift of kind {kind}")


def shift_duration_hours(shift: StandardShift) -> float:
    anchor = date(2000, 1, 1)
    start = datetime.combine(anchor, shift.start_time)
    end = datetime.combine(anchor + timedelta(days=1 if shift.end_next_day else 0), shift.end_time)
    return (end - start).total_seconds() / 3600


def normalized_catalog_kind(shift: StandardShift) -> ShiftCatalogKind:
    """Legacy StandardShift.catalog_kind=None is normalized from actual
    duration -- 24h/12h exactly, anything else is INNY."""
    if shift.catalog_kind is not None:
        return shift.catalog_kind
    hours = shift_duration_hours(shift)
    if hours == 24:
        return ShiftCatalogKind.H24
    if hours == 12:
        return ShiftCatalogKind.H12
    return ShiftCatalogKind.OTHER


def validate_standard_shift(shift: StandardShift) -> None:
    if shift.required_primary_count <= 0:
        raise InvalidStandardShift(f"required_primary_count must be > 0, got {shift.required_primary_count}")
    if shift.required_rest_hours < 0:
        raise InvalidStandardShift(f"required_rest_hours must be >= 0, got {shift.required_rest_hours}")
    if not shift.active_weekdays:
        raise InvalidStandardShift("active_weekdays must not be empty")
    if len(set(shift.active_weekdays)) != len(shift.active_weekdays):
        raise InvalidStandardShift(f"active_weekdays must not contain duplicates: {shift.active_weekdays}")
    if any(w < 1 or w > 7 for w in shift.active_weekdays):
        raise InvalidStandardShift(f"active_weekdays must be ISO 1..7: {shift.active_weekdays}")
    if shift.catalog_kind is None:
        return
    hours = shift_duration_hours(shift)
    if shift.catalog_kind == ShiftCatalogKind.H24 and hours != 24:
        raise InvalidStandardShift(f"catalog_kind=24h requires exactly 24h duration, got {hours}h")
    if shift.catalog_kind == ShiftCatalogKind.H12 and hours != 12:
        raise InvalidStandardShift(f"catalog_kind=12h requires exactly 12h duration, got {hours}h")
    if shift.catalog_kind == ShiftCatalogKind.OTHER and (hours <= 0 or hours in (12, 24)):
        raise InvalidStandardShift(f"catalog_kind=INNY requires a positive duration that is not 12h/24h, got {hours}h")


def _opposite(kind: ShiftKind) -> ShiftKind:
    return ShiftKind.N if kind == ShiftKind.D else ShiftKind.D


@dataclass(frozen=True)
class _Component:
    start: datetime
    end: datetime
    kind: ShiftKind
    required_primary_count: int
    template_id: Optional[str]
    component: Optional[int]
    catalog_kind: ShiftCatalogKind
    required_rest_hours: int


def _components_for_shift(shift: StandardShift, template_id: str, current: date) -> list[_Component]:
    kind = normalized_catalog_kind(shift)
    if kind != ShiftCatalogKind.H24:
        start = datetime.combine(current, shift.start_time)
        end_date = current + (timedelta(days=1) if shift.end_next_day else timedelta())
        end = datetime.combine(end_date, shift.end_time)
        return [_Component(start, end, shift.kind, shift.required_primary_count, template_id, 1, kind, shift.required_rest_hours)]
    first_start = datetime.combine(current, shift.start_time)
    first_end = first_start + timedelta(hours=12)
    second_end = first_start + timedelta(hours=24)
    return [
        _Component(first_start, first_end, shift.kind, shift.required_primary_count, template_id, 1, kind, shift.required_rest_hours),
        _Component(first_end, second_end, _opposite(shift.kind), shift.required_primary_count, template_id, 2, kind, shift.required_rest_hours),
    ]


def _emergency_rest_lookup(profile: SiteProfile) -> dict[tuple, int]:
    """Maps (kind, start_time_of_day) -> required_rest_hours for every
    unambiguous matching 24h capability's two halves. AmbiguousEmergency24hCapability
    is raised eagerly here (at lookup-table build time) so every demand
    generated from an ambiguous profile fails closed identically."""
    by_key: dict[tuple, set[int]] = {}
    for shift in profile.standard_shifts:
        if normalized_catalog_kind(shift) != ShiftCatalogKind.H24:
            continue
        first_key = (shift.kind, shift.start_time)
        second_start = (datetime.combine(date(2000, 1, 1), shift.start_time) + timedelta(hours=12)).time()
        second_key = (_opposite(shift.kind), second_start)
        by_key.setdefault(first_key, set()).add(shift.required_rest_hours)
        by_key.setdefault(second_key, set()).add(shift.required_rest_hours)
    resolved: dict[tuple, int] = {}
    for key, rests in by_key.items():
        if len(rests) > 1:
            raise AmbiguousEmergency24hCapability(
                f"conflicting required_rest_hours {sorted(rests)} for matching 24h capability kind={key[0]}, start={key[1]}"
            )
        resolved[key] = next(iter(rests))
    return resolved


def generate_catalog_demands(profile: SiteProfile, month: date) -> tuple[ShiftDemand, ...]:
    """T012 replacement for the legacy per-day D/N expansion: every active
    StandardShift (12h/INNY/24h) generates its occurrence(s) for each
    active_weekdays day in month, anchored to the occurrence's start day.
    Multiple entries and overlaps are legal and generate independent
    occurrences; deterministic demand_id assignment matches the legacy
    "{date}-{kind}[-{n}]" shape, extended to stay collision-free across
    every occurrence (including both halves of a 24h pair) landing on the
    same (date, kind)."""
    for shift in profile.standard_shifts:
        validate_standard_shift(shift)
    emergency_rest = _emergency_rest_lookup(profile)

    days_in_month = calendar.monthrange(month.year, month.month)[1]
    components: list[_Component] = []
    for idx, shift in enumerate(profile.standard_shifts):
        template_id = f"{profile.profile_id}-shift{idx}"
        for day in range(1, days_in_month + 1):
            current = date(month.year, month.month, day)
            if current.isoweekday() not in shift.active_weekdays:
                continue
            components.extend(_components_for_shift(shift, template_id, current))

    components.sort(key=lambda c: (c.start, c.kind.value))
    kind_counts: dict[tuple, int] = {}
    for c in components:
        key = (c.start.date(), c.kind)
        kind_counts[key] = kind_counts.get(key, 0) + 1

    demands = []
    kind_seen: dict[tuple, int] = {}
    for c in components:
        day = c.start.date()
        key = (day, c.kind)
        occurrence = kind_seen.get(key, 0)
        kind_seen[key] = occurrence + 1
        suffix = f"-{occurrence}" if kind_counts[key] > 1 else ""
        demand_id = f"{day.isoformat()}-{c.kind.value}{suffix}"
        emergency = None if c.catalog_kind == ShiftCatalogKind.H24 else emergency_rest.get((c.kind, c.start.time()))
        demands.append(ShiftDemand(
            demand_id, "", c.start, c.end, c.required_primary_count,
            shift_kind=c.kind, catalog_kind=c.catalog_kind, required_rest_hours=c.required_rest_hours,
            work_period_template_id=c.template_id, work_period_component=c.component,
            emergency_24h_rest_hours=emergency,
        ))
    return tuple(demands)


if __name__ == "__main__":
    from datetime import time

    profile = SiteProfile(
        profile_id="OCHRONA",
        display_name="Ochrona",
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1),
            StandardShift(ShiftKind.N, time(17, 0), time(5, 0), True, 1),
        ],
        day_only_blocks_n=True,
        external_support_enabled=False,
        training_s_enabled=True,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=60,
    )
    demand = ShiftDemand(
        demand_id="d1",
        schedule_version_id="v1",
        start_datetime=datetime(2026, 10, 1, 5, 0),
        end_datetime=datetime(2026, 10, 1, 17, 0),
        required_primary_count=1,
    )
    print(f"classify_demand -> {classify_demand(demand, profile)}")
