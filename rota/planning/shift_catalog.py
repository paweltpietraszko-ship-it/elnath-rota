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
    """Return the ShiftKind of demand. ROTA-T012 (A-R4-3): a demand carrying
    an explicit ShiftDemand.shift_kind (every T012-generated demand does)
    is authoritative and never needs -- or gets -- reconstructed from the
    current profile; the profile-matching fallback below is legacy-only
    (shift_kind=None)."""
    if demand.shift_kind is not None:
        return demand.shift_kind
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


def validate_standard_shift_shape(shift: StandardShift) -> None:
    """A-R4-4: the T012 shape boundaries (rest/weekdays/catalog-kind-vs-
    duration) a create/update write must reject immediately -- deliberately
    NOT including required_primary_count, which stays a separate, already-
    established pre-T012 concern (tests/test_audit_t010_r3.py: an
    incomplete-but-saved StandardShift is a bootstrap/readiness gate, not a
    persistence-time rejection)."""
    if shift.required_rest_hours < 0:
        raise InvalidStandardShift(f"required_rest_hours must be >= 0, got {shift.required_rest_hours}")
    if not shift.active_weekdays:
        raise InvalidStandardShift("active_weekdays must not be empty")
    if len(set(shift.active_weekdays)) != len(shift.active_weekdays):
        raise InvalidStandardShift(f"active_weekdays must not contain duplicates: {shift.active_weekdays}")
    if any(w < 1 or w > 7 for w in shift.active_weekdays):
        raise InvalidStandardShift(f"active_weekdays must be ISO 1..7: {shift.active_weekdays}")
    # OWNER-T022-01: no partial-hour work -- start/end must land on a full clock hour.
    if shift.start_time.minute or shift.start_time.second or shift.start_time.microsecond:
        raise InvalidStandardShift(f"start_time must be a full hour, got {shift.start_time}")
    if shift.end_time.minute or shift.end_time.second or shift.end_time.microsecond:
        raise InvalidStandardShift(f"end_time must be a full hour, got {shift.end_time}")
    if shift.catalog_kind is None:
        return
    hours = shift_duration_hours(shift)
    if shift.catalog_kind == ShiftCatalogKind.H24 and hours != 24:
        raise InvalidStandardShift(f"catalog_kind=24h requires exactly 24h duration, got {hours}h")
    if shift.catalog_kind == ShiftCatalogKind.H12 and hours != 12:
        raise InvalidStandardShift(f"catalog_kind=12h requires exactly 12h duration, got {hours}h")
    if shift.catalog_kind == ShiftCatalogKind.OTHER and (hours <= 0 or hours in (12, 24)):
        raise InvalidStandardShift(f"catalog_kind=INNY requires a positive duration that is not 12h/24h, got {hours}h")


def validate_standard_shift(shift: StandardShift) -> None:
    """Full PLAN-time validation: the write-time shape boundaries above,
    plus required_primary_count > 0 (a usable-catalog concern, not a
    storage-shape one)."""
    if shift.required_primary_count <= 0:
        raise InvalidStandardShift(f"required_primary_count must be > 0, got {shift.required_primary_count}")
    validate_standard_shift_shape(shift)


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
    unambiguous matching 24h capability -- keyed ONLY by the capability's
    own start (kind, start_time), i.e. where an emergency 24h occurrence
    would BEGIN (A-R4-2). The derived second-half slot is deliberately not
    registered: it is not itself a place a new emergency 24h can start, and
    registering it caused two legitimate, directionally distinct 24h
    capabilities (e.g. D@05 and N@17) to collide as a false conflict.
    AmbiguousEmergency24hCapability is raised eagerly here (at lookup-table
    build time) so every demand generated from a genuinely ambiguous
    profile -- two 24h capabilities with the same (kind, start_time) but
    different required_rest_hours -- fails closed identically."""
    by_key: dict[tuple, set[int]] = {}
    for shift in profile.standard_shifts:
        if normalized_catalog_kind(shift) != ShiftCatalogKind.H24:
            continue
        key = (shift.kind, shift.start_time)
        by_key.setdefault(key, set()).add(shift.required_rest_hours)
    resolved: dict[tuple, int] = {}
    for key, rests in by_key.items():
        if len(rests) > 1:
            raise AmbiguousEmergency24hCapability(
                f"conflicting required_rest_hours {sorted(rests)} for matching 24h capability kind={key[0]}, start={key[1]}"
            )
        resolved[key] = next(iter(rests))
    return resolved


def _all_components(profile: SiteProfile, month: date) -> list[_Component]:
    days_in_month = calendar.monthrange(month.year, month.month)[1]
    components: list[_Component] = []
    for idx, shift in enumerate(profile.standard_shifts):
        for day in range(1, days_in_month + 1):
            current = date(month.year, month.month, day)
            if current.isoweekday() not in shift.active_weekdays:
                continue
            # A-R4-1: template_id identifies ONE occurrence (this catalog
            # entry, on this start day), not the whole catalog entry across
            # the month -- 12h/INNY forms a group of exactly one demand,
            # normal 24h a group of exactly the two components of that one
            # occurrence, never all 31 days' worth.
            template_id = f"{profile.profile_id}-shift{idx}-{current.isoformat()}"
            components.extend(_components_for_shift(shift, template_id, current))
    return components


def _components_to_demands(components: list[_Component], emergency_rest: dict[tuple, int]) -> tuple[ShiftDemand, ...]:
    """Deterministic demand_id assignment matches the legacy
    "{date}-{kind}[-{n}]" shape, extended to stay collision-free across
    every occurrence (including both halves of a 24h pair) landing on the
    same (date, kind)."""
    components = sorted(components, key=lambda c: (c.start, c.kind.value))
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
        # A-R4-2: only a plain 12h demand may snapshot an emergency rest --
        # never a 24h component itself (it IS the capability, not a rescue
        # candidate) and never INNY (excluded from emergency pairing).
        emergency = emergency_rest.get((c.kind, c.start.time())) if c.catalog_kind == ShiftCatalogKind.H12 else None
        demands.append(ShiftDemand(
            demand_id, "", c.start, c.end, c.required_primary_count,
            shift_kind=c.kind, catalog_kind=c.catalog_kind, required_rest_hours=c.required_rest_hours,
            work_period_template_id=c.template_id, work_period_component=c.component,
            emergency_24h_rest_hours=emergency,
        ))
    return tuple(demands)


def generate_catalog_demands(profile: SiteProfile, month: date) -> tuple[ShiftDemand, ...]:
    """T012 replacement for the legacy per-day D/N expansion: every active
    StandardShift (12h/INNY/24h) generates its occurrence(s) for each
    active_weekdays day in month, anchored to the occurrence's start day.
    Multiple entries and overlaps are legal and generate independent
    occurrences."""
    for shift in profile.standard_shifts:
        validate_standard_shift(shift)
    emergency_rest = _emergency_rest_lookup(profile)
    components = _all_components(profile, month)
    return _components_to_demands(components, emergency_rest)


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
