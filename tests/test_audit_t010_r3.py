"""Adversarial implementation audit for ROTA-T010, round 3.

The assertions below are traced to the approved T010 A/B/D contracts.  They
cover bug classes omitted by the author's happy-path tests; they do not define
new product behaviour.
"""
from __future__ import annotations

import calendar
import threading
from datetime import date, datetime, time

import pytest

import rota.application.bootstrap as bootstrap_module
from rota.application.availability_matrix import employee_availability_matrix
from rota.application.bootstrap import (
    bootstrap_or_resume_coordinator_context,
    coordinator_context_completeness,
)
from rota.application.errors import CoordinatorContextAlreadyActive
from rota.application.manual_edit import mark_not_worked
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    SiteRuleVersion,
    StandardShift,
    SitePlanningRegime,
)
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import (
    save_coordinator,
    save_coordinator_site_association,
)
from rota.persistence.db import connect
from rota.persistence.decision_ledger import record_decision
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_repository import get_current_version_id
from rota.persistence.site_memory import effective_rule_on
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.engine import plan
from rota.planning.site_rules import (
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
)
from rota.planning.state import SiteRuleApplicability
from rota.site_memory_types import EffectiveRule, NewRuleContent, NoActiveRule
from tests.support.minimal_state import base_state


COORDINATOR_ID = "COORD-T010-R3"
SITE_ID = "SITE-T010-R3"
PROFILE_ID = "PROFILE-T010-R3"
EMPLOYEE_ID = "EMP-T010-R3"
MONTH = date(2026, 10, 1)


def _profile(*, shifts: list[StandardShift] | None = None, display_name: str = "Profile") -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID,
        display_name=display_name,
        active=True,
        standard_shifts=shifts
        if shifts is not None
        else [StandardShift(ShiftKind.D, time(5), time(17), False, 1)],
        day_only_blocks_n=True,
        external_support_enabled=False,
        training_s_enabled=True,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=60,
    )


def _seed_context(conn, *, shifts: list[StandardShift] | None = None, day_only: bool = False) -> None:
    save_site_profile(conn, _profile(shifts=shifts))
    save_site(conn, Site(SITE_ID, PROFILE_ID, "Site", True, planning_regime=SitePlanningRegime.ORDINARY))
    save_coordinator(conn, Coordinator(COORDINATOR_ID, "Coordinator", True))
    save_coordinator_site_association(
        conn, CoordinatorSiteAssociation(COORDINATOR_ID, SITE_ID, True)
    )
    save_employee(conn, Employee(EMPLOYEE_ID, "Employee", date(2020, 1, 1), None, day_only))
    save_site_membership(
        conn,
        SiteMembership(
            EMPLOYEE_ID,
            SITE_ID,
            MembershipKind.LOCAL,
            True,
            ReadinessState.READY_FOR_PRIMARY,
            ReadinessSource.DEFAULT,
        ),
    )


def _fill_calendar(conn) -> None:
    for day in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        save_calendar_day(conn, CalendarDay(date(MONTH.year, MONTH.month, day), False))


@pytest.mark.parametrize(
    "invalid_shift",
    [
        pytest.param(
            StandardShift(ShiftKind.D, time(5), time(17), False, 0),
            id="non_positive_required_primary_count",
        ),
        pytest.param(
            StandardShift(ShiftKind.D, time(5), time(5), False, 1),
            id="non_positive_same_day_interval",
        ),
    ],
)
def test_r3_a_context_is_not_complete_with_an_invalid_standard_shift(tmp_path, invalid_shift) -> None:
    """Part A requires at least one *valid* standard shift, not merely a row."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn, shifts=[invalid_shift])

    result = coordinator_context_completeness(
        conn, coordinator_id=COORDINATOR_ID, site_id=SITE_ID
    )

    assert not result.complete
    assert any("shift" in missing.lower() for missing in result.missing)


def test_r3_a_two_inflight_bootstraps_of_the_same_context_do_not_both_succeed(
    tmp_path, monkeypatch
) -> None:
    """The guard must cover the race, not only a later sequential retry."""
    db_path = tmp_path / "rota.db"
    connect(db_path).close()  # migrate once before starting competing writers
    barrier = threading.Barrier(2)
    # ROTA-T011-C (FINDING C-R4-1): bootstrap_or_resume_coordinator_context's
    # fast-path check is _has_full_active_context since C-R3-1, not
    # _has_active_association -- patching the old helper no longer
    # synchronizes anything on the actual bootstrap entry path.
    original_check = bootstrap_module._has_full_active_context

    def synchronized_check(conn, *, coordinator_id: str, site_id: str) -> bool:
        result = original_check(conn, coordinator_id=coordinator_id, site_id=site_id)
        barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(bootstrap_module, "_has_full_active_context", synchronized_check)
    outcomes: list[str] = []

    def worker(label: str) -> None:
        conn = connect(db_path)
        try:
            bootstrap_or_resume_coordinator_context(
                conn,
                coordinator_id=COORDINATOR_ID,
                site_id=SITE_ID,
                coordinator=Coordinator(COORDINATOR_ID, f"Coordinator {label}", True),
                site_profile=_profile(display_name=f"Profile {label}"),
                site=Site(SITE_ID, PROFILE_ID, f"Site {label}", True, planning_regime=SitePlanningRegime.ORDINARY),
                association=CoordinatorSiteAssociation(COORDINATOR_ID, SITE_ID, True),
            )
        except CoordinatorContextAlreadyActive:
            outcomes.append("rejected")
        except Exception as exc:  # a database lock/crash is not the contracted refusal
            outcomes.append(f"technical-error:{type(exc).__name__}")
        else:
            outcomes.append("success")
        finally:
            conn.close()

    threads = [threading.Thread(target=worker, args=(label,)) for label in ("A", "B")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(outcomes) == ["rejected", "success"]


@pytest.mark.parametrize(
    "wrong_category",
    [RuleCategory.LOCAL_RULE, RuleCategory.CLIENT_REQUIREMENT],
)
def test_r3_b_day_only_exception_requires_confirmed_exception_category(wrong_category) -> None:
    """A differently categorized rule must not grant the day-only exception."""
    rule = SiteRuleVersion(
        rule_version_id="RV-WRONG-CATEGORY",
        rule_id="R-WRONG-CATEGORY",
        site_id="test-site",
        category=wrong_category,
        rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        structured_parameters={"employee_id": EMPLOYEE_ID},
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_from=date(2026, 10, 1),
        effective_to=date(2026, 10, 31),
        changed_at=datetime(2026, 9, 1, 9),
        changed_by=COORDINATOR_ID,
        supersedes_rule_version_id=None,
        description=None,
        source=None,
        reason=None,
    )
    demand = ShiftDemand(
        "N-12",
        "test-v1",
        datetime(2026, 10, 12, 17),
        datetime(2026, 10, 13, 5),
        1,
    )
    state = base_state(
        employees=(Employee(EMPLOYEE_ID, "Employee", date(2020, 1, 1), None, True),),
        memberships=(
            SiteMembership(
                EMPLOYEE_ID,
                "test-site",
                MembershipKind.LOCAL,
                True,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
            ),
        ),
        shift_demands=(demand,),
        site_rules=(rule,),
        site_rule_applicability=(
            SiteRuleApplicability(rule.rule_version_id, date(2026, 10, 1), date(2026, 10, 31)),
        ),
    )

    result = plan(state)

    assert result.status != "FEASIBLE"


def test_r3_b_projection_distinguishes_early_restore_from_unchanged_ban(tmp_path) -> None:
    """Dropping applicability slices makes an early restore invisible in the matrix."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    content = NewRuleContent(
        category=RuleCategory.LOCAL_RULE, rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        structured_parameters={
            "employee_id": EMPLOYEE_ID, "weekdays": list(range(1, 8)), "forbidden_shift_kinds": ["N"],
        },
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_to=date(2026, 10, 31), description=None, source=None, reason=None,
    )
    record_decision(
        conn, site_id=SITE_ID, rule_id="R-N-BAN", statement="N disabled", coordinator_id=COORDINATOR_ID,
        recorded_at=datetime(2026, 9, 1, 9), effective_from=date(2026, 10, 1), rel=None, rule_content=content,
    )
    before_effective = effective_rule_on(conn, SITE_ID, "R-N-BAN", date(2026, 10, 20))
    before_matrix = employee_availability_matrix(conn, site_id=SITE_ID, employee_id=EMPLOYEE_ID, month=MONTH)

    record_decision(
        conn, site_id=SITE_ID, rule_id="R-N-BAN", statement="N restored early", coordinator_id=COORDINATOR_ID,
        recorded_at=datetime(2026, 10, 10, 9), effective_from=date(2026, 10, 15), rel="rejects", rule_content=None,
    )
    after_effective = effective_rule_on(conn, SITE_ID, "R-N-BAN", date(2026, 10, 20))
    after_matrix = employee_availability_matrix(conn, site_id=SITE_ID, employee_id=EMPLOYEE_ID, month=MONTH)

    assert isinstance(before_effective, EffectiveRule)
    assert isinstance(after_effective, NoActiveRule)
    assert before_matrix != after_matrix


def _demand() -> ShiftDemand:
    return ShiftDemand(
        "DEMAND-1", "", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), 1
    )


def _primary(*, state: AssignmentState, operational_code: str | None) -> Assignment:
    return Assignment(
        "PRIMARY-1",
        "",
        EMPLOYEE_ID,
        datetime(2026, 10, 1, 5),
        datetime(2026, 10, 1, 17),
        AssignmentRole.PRIMARY,
        state,
        False,
        "DEMAND-1",
        None,
        operational_code,
    )


def _trainee(*, state: AssignmentState, operational_code: str | None) -> Assignment:
    return Assignment(
        "TRAINEE-1",
        "",
        EMPLOYEE_ID,
        datetime(2026, 10, 1, 5),
        datetime(2026, 10, 1, 17),
        AssignmentRole.TRAINEE,
        state,
        False,
        None,
        "PRIMARY-1",
        operational_code,
    )


@pytest.mark.parametrize(
    "assignments",
    [
        pytest.param(
            [_primary(state=AssignmentState.PLANNED, operational_code="NN")],
            id="nn_on_planned_primary",
        ),
        pytest.param(
            [
                _primary(state=AssignmentState.PLANNED, operational_code=None),
                _trainee(state=AssignmentState.CANCELLED, operational_code="NN"),
            ],
            id="nn_on_cancelled_trainee",
        ),
        pytest.param(
            [_primary(state=AssignmentState.CANCELLED, operational_code="OTHER")],
            id="unsupported_operational_code",
        ),
    ],
)
def test_r3_d_schedule_write_rejects_every_illegal_operational_code_shape(
    tmp_path, assignments
) -> None:
    """Only CANCELLED PRIMARY + NN, and ordinary None, are legal in T010."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)

    with pytest.raises(Exception):
        lifecycle.create_schedule_version(
            conn,
            version_id="SV-INVALID-NN",
            site_id=SITE_ID,
            month=MONTH,
            parent_version_id=None,
            created_at=datetime(2026, 9, 25, 9),
            created_by=COORDINATOR_ID,
            applied_rule_version_ids=[],
            shift_demands=[_demand()],
            assignments=assignments,
            deviations=[],
            effective_from=date(2026, 9, 25),
        )

    assert get_current_version_id(conn, SITE_ID, MONTH) is None


def test_r3_d_mark_not_worked_rejects_a_trainee_without_creating_a_child(tmp_path) -> None:
    """The named NN command is restricted to a previously PLANNED PRIMARY."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _fill_calendar(conn)
    lifecycle.create_schedule_version(
        conn,
        version_id="SV-PARENT",
        site_id=SITE_ID,
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 9, 25, 9),
        created_by=COORDINATOR_ID,
        applied_rule_version_ids=[],
        shift_demands=[_demand()],
        assignments=[
            _primary(state=AssignmentState.PLANNED, operational_code=None),
            _trainee(state=AssignmentState.PLANNED, operational_code=None),
        ],
        deviations=[],
        effective_from=date(2026, 9, 25),
    )
    versions_before = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]

    with pytest.raises(Exception):
        mark_not_worked(
            conn,
            site_id=SITE_ID,
            month=MONTH,
            coordinator_id=COORDINATOR_ID,
            effective_from=date(2026, 10, 2),
            assignment_id="TRAINEE-1",
        )

    versions_after = conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0]
    assert versions_after == versions_before
