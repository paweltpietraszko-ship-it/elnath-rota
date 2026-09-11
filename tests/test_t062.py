"""ROTA-T062 (brief f5f76cd.../6e550a5): one coordinator-facing guidance
family for a blocked PLAN, structured navigation targets instead of Polish-
text prefix matching, THIRD_CONSECUTIVE_SHIFT_BLOCKED sharing the same
guidance as DECISION_REQUIRED, and no manual-correction-style suggestion
once there is no current ScheduleVersion to correct (ROTA-T061 retired).
"""
from __future__ import annotations

from datetime import date, time

from rota.application import bootstrap, durable_inputs, plan_ops
from rota.domain import (
    AvailabilityKind,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    Site,
    SiteMembership,
    SiteProfile,
    SitePlanningRegime,
    ShiftKind,
    StandardShift,
)
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.domain import CalendarDay
from rota.planning.decision_guidance import build_third_shift_payload, build_unblocking_options, drop_options_requiring_existing_schedule
from rota.planning.engine_types import Blocker, DecisionRequiredPayload, PlanningResult, UnblockingOption
from rota.persistence import site_memory
from tests.support.minimal_state import MONTH, base_state

COORD = "COORD-T62"
SITE_ID = "SITE-T62"
PROFILE_ID = "PROFILE-T62"
EMP1 = "EMP-T62-1"


def _employee(employee_id: str) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, False)


def _membership(employee_id: str) -> SiteMembership:
    from rota.domain import MembershipKind, ReadinessSource, ReadinessState

    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID, display_name="T62 Profile", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        coordinator=Coordinator(COORD, "Coord T62", True), site_profile=_profile(),
        site=Site(SITE_ID, PROFILE_ID, "Site T62", True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE_ID, True),
    )
    durable_inputs.update_employee(conn, coordinator_id=COORD, site_id=SITE_ID, employee=_employee(EMP1))
    durable_inputs.update_membership(conn, coordinator_id=COORD, site_id=SITE_ID, membership=_membership(EMP1))
    import calendar as _cal

    for day in range(1, _cal.monthrange(MONTH.year, MONTH.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date=date(MONTH.year, MONTH.month, day), holiday=False))


# T62-04/T62-05 -- NIGHT-STREAK-01 now has a stable target ------------------


def test_night_streak_option_carries_obsada_target():
    state = base_state(employees=(Employee("A", "Anna", date(2020, 1, 1), None, False),))
    options = build_unblocking_options(state, [Blocker("A", "NIGHT-STREAK-01")], None)
    assert len(options) == 1
    assert options[0] == UnblockingOption("Sprawdź obsadę i dostępność: Anna, i zaplanuj ponownie", target="obsada")


# T62-06 -- THIRD_CONSECUTIVE_SHIFT_BLOCKED shares the same guidance --------


def test_third_shift_payload_names_employees_with_obsada_target():
    state = base_state(employees=(Employee("A", "Anna", date(2020, 1, 1), None, False),))
    payload = build_third_shift_payload(state, ["A"])
    assert payload.blocking_shift_demands == []
    assert payload.blockers == []
    assert payload.unblocking_options == [
        UnblockingOption("Sprawdź obsadę i dostępność: Anna, i zaplanuj ponownie", target="obsada"),
    ]


def test_third_shift_payload_falls_back_when_no_employee_named():
    state = base_state(employees=())
    payload = build_third_shift_payload(state, [])
    assert [o.text for o in payload.unblocking_options] == [
        "Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.",
    ]


# T62-09 -- no-current: manual-correction-style options are dropped ---------


def test_drop_options_requiring_existing_schedule_strips_manual_correction_only():
    payload = DecisionRequiredPayload(
        blocking_shift_demands=[], blockers=[], load_blocker=None,
        unblocking_options=[
            UnblockingOption("Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: A", requires_existing_schedule=True),
            UnblockingOption("Zmień Ogólna dostępność: A", target="obsada"),
        ],
    )
    filtered = drop_options_requiring_existing_schedule(payload)
    assert [o.text for o in filtered.unblocking_options] == ["Zmień Ogólna dostępność: A"]


def test_drop_options_requiring_existing_schedule_falls_back_when_all_stripped():
    payload = DecisionRequiredPayload(
        blocking_shift_demands=[], blockers=[], load_blocker=None,
        unblocking_options=[
            UnblockingOption("Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: A", requires_existing_schedule=True),
        ],
    )
    filtered = drop_options_requiring_existing_schedule(payload)
    assert [o.text for o in filtered.unblocking_options] == [
        "Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.",
    ]


# T62-15 -- old list[str] snapshots stay readable, no migration -------------


def test_old_string_snapshot_reads_back_as_target_less_option():
    old_shaped = {
        "blocking_shift_demands": [], "blockers": [], "load_blocker": None,
        "unblocking_options": ["stary tekst bez celu"],
    }
    restored = site_memory._payload_from_dict(old_shaped)
    assert restored.unblocking_options == [UnblockingOption("stary tekst bez celu")]


# T62-09 real vertical: no-current DECISION_REQUIRED never suggests Korekta
# ręczna, since ROTA-T061 (first manual root without current) is retired --
# real plan_ops.plan_month() call, not a hand-built payload.


def test_no_current_leave_granted_conflict_never_suggests_manual_correction(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    # LEAVE_GRANTED for the whole month -- EMP1 is the only membership, so
    # every demand this month is blocked the same way.
    durable_inputs.append_availability(
        conn, coordinator_id=COORD, site_id=SITE_ID, availability_id="AV-1", employee_id=EMP1,
        kind=AvailabilityKind.LEAVE_GRANTED, start_date=MONTH, end_date=date(MONTH.year, MONTH.month, 28), active=True,
    )
    result = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert result.status == "DECISION_REQUIRED"
    texts = [o.text for o in result.decision_payload.unblocking_options]
    assert not any("Ręczna korekta" in t for t in texts)
    # Persisted readback must reflect the same stripped set, not the raw one.
    readback = site_memory.get_current_decision_required(conn, site_id=SITE_ID, month=MONTH)
    assert readback is not None
    assert not any("Ręczna korekta" in o.text for o in readback.payload.unblocking_options)


# T62-08/T62-11 -- a fresh THIRD result replaces a stale DECISION_REQUIRED
# readback instead of leaving it current (_persist_decision_readback is the
# one shared function all three plan_month/replan call sites use).


def test_third_shift_readback_replaces_stale_decision_required(tmp_path):
    conn = connect(tmp_path / "rota.db")
    _bootstrap(conn)
    stale = PlanningResult(
        "DECISION_REQUIRED", [], DecisionRequiredPayload(
            blocking_shift_demands=[], blockers=[Blocker(EMP1, "REST-01")], load_blocker=None,
            unblocking_options=[UnblockingOption("stary, nieaktualny problem")],
        ), None, [],
    )
    fresh_third = PlanningResult(
        "THIRD_CONSECUTIVE_SHIFT_BLOCKED", [], DecisionRequiredPayload(
            blocking_shift_demands=[], blockers=[], load_blocker=None,
            unblocking_options=[UnblockingOption("Sprawdź obsadę i dostępność: EMP-T62-1, i zaplanuj ponownie", target="obsada")],
        ), None, [],
    )
    plan_ops._persist_decision_readback(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, schedule_version_id=None, result=stale,
    )
    plan_ops._persist_decision_readback(
        conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, schedule_version_id=None, result=fresh_third,
    )
    readback = site_memory.get_current_decision_required(conn, site_id=SITE_ID, month=MONTH)
    assert readback is not None
    assert [o.text for o in readback.payload.unblocking_options] == [
        "Sprawdź obsadę i dostępność: EMP-T62-1, i zaplanuj ponownie",
    ]


if __name__ == "__main__":
    print("test_t062 module OK")
