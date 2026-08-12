"""Map a ShiftDemand back to the SiteProfile StandardShift that generated it.

ShiftDemand only carries a start/end datetime (SECTION 1 arch/spec.md). The
solver and validator both need to know whether a given demand is a D or an N
occurrence to apply SHIFT-01/DAY_ONLY-01/DAY_SHIFT_OFF-01. Matching is done
by time-of-day against the profile's own standard_shifts, so this works for
any month or profile configuration, not just OCHRONA/October.
"""
from __future__ import annotations

from rota.domain import ShiftDemand, ShiftKind, SiteProfile, StandardShift


class UnclassifiedShiftError(Exception):
    """Raised when a ShiftDemand's time-of-day matches no StandardShift."""


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
    from datetime import datetime

    demand = ShiftDemand(
        demand_id="d1",
        schedule_version_id="v1",
        start_datetime=datetime(2026, 10, 1, 5, 0),
        end_datetime=datetime(2026, 10, 1, 17, 0),
        required_primary_count=1,
    )
    print(f"classify_demand -> {classify_demand(demand, profile)}")
