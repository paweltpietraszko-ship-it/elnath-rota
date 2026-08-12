"""Minimal PlanningState builder for hand-crafted adversarial regression tests.

Unlike tests/support/state_builder.py (which assembles a full month from a
ROTA-REG-001-shaped fixture), this gives each test just the handful of
objects it needs and dataclasses.replace() to override specific fields.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, time

from rota.domain import (
    ReadinessSource,
    ReadinessState,
    ShiftKind,
    Site,
    SiteProfile,
    StandardShift,
)
from rota.planning.state import PlanningState

SITE_ID = "test-site"
PROFILE_ID = "TESTPROF"
MONTH = date(2026, 10, 1)


def base_profile(rolling_threshold: int = 60) -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID,
        display_name="Test profile",
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(5, 0), time(17, 0), False, 1),
            StandardShift(ShiftKind.N, time(17, 0), time(5, 0), True, 1),
        ],
        day_only_blocks_n=True,
        external_support_enabled=True,
        training_s_enabled=False,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=rolling_threshold,
    )


def base_state(**overrides) -> PlanningState:
    """A PlanningState with every collection empty; override fields as needed."""
    state = PlanningState(
        site=Site(SITE_ID, PROFILE_ID, "Test Site", True),
        profile=base_profile(),
        month=MONTH,
        calendar_days=(),
        boundary_assignments=(),
        memberships=(),
        employees=(),
        external_windows=(),
        availability_records=(),
        site_rules=(),
        unresolved_site_rules=(),
        shift_demands=(),
        existing_assignments=(),
        deviations=(),
        work_balances=(),
        holiday_history=(),
        other_site_assignments=(),
        schedule_version_id="test-v1",
    )
    return replace(state, **overrides)


__all__ = ["ReadinessSource", "ReadinessState", "SITE_ID", "PROFILE_ID", "MONTH", "base_profile", "base_state"]
