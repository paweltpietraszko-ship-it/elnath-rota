"""ROTA-T011-C (tasks/ROTA-T011-C/brief.md): Site/Coordinator/
CoordinatorSiteAssociation lifecycle after bootstrap (B-2=W1, plain
upserts on MUTABLE CURRENT-STATE ENTITIES). Depends on T011-B (merged):
verification uses active_coordinators/all_coordinators/
active_sites_for_coordinator/all_sites_for_coordinator, never
rota.persistence.
"""
from __future__ import annotations

import calendar as _calendar
from datetime import date, time

import pytest

from rota.application import store
from rota.application.bootstrap import (
    active_coordinators,
    active_sites_for_coordinator,
    all_coordinators,
    all_sites_for_coordinator,
    bootstrap_or_resume_coordinator_context,
)
from rota.application.durable_inputs import (
    set_calendar_day,
    update_association,
    update_coordinator,
    update_employee,
    update_membership,
    update_site,
)
from rota.application.errors import CoordinatorContextAlreadyActive, InvalidCoordinatorContext
from rota.application.lifecycle_ops import finalize, revalidate
from rota.application.memory_read import decision_chain_for_rule_family
from rota.application.open_month import open_month
from rota.application.plan_ops import plan_month, select_candidate
from rota.application.rule_decisions import record_structured_rule_decision
from rota.application.assembler import assemble_planning_state
from rota.domain import (
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
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    SitePlanningRegime,
)
from rota.site_memory_types import NewRuleContent

RULE_ID = "RULE-T011C-LOCKOUT"

COORD_A = "COORD-T011C-A"
COORD_B = "COORD-T011C-B"
SITE_A = "SITE-T011C-A"
SITE_OTHER = "SITE-T011C-OTHER"
PROFILE_A = "PROFILE-T011C-A"
PROFILE_OTHER = "PROFILE-T011C-OTHER"
EMP = "EMP-T011C"
EMP2 = "EMP-T011C-2"
MONTH = date(2026, 9, 1)


def _profile(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=f"Profile {profile_id}", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _site(site_id: str, profile_id: str, display_name: str, active: bool = True) -> Site:
    return Site(site_id=site_id, profile_id=profile_id, display_name=display_name, active=active, planning_regime=SitePlanningRegime.ORDINARY)


def _bootstrap(
    conn, *, coordinator_id: str, site_id: str, profile_id: str = PROFILE_A,
    coordinator_active: bool = True, site_active: bool = True, association_active: bool = True,
) -> None:
    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coordinator_id, site_id=site_id,
        coordinator=Coordinator(coordinator_id, f"Coord {coordinator_id}", coordinator_active),
        site_profile=_profile(profile_id), site=_site(site_id, profile_id, f"Site {site_id}", site_active),
        association=CoordinatorSiteAssociation(coordinator_id, site_id, association_active),
    )


def _staff_and_fill_calendar(conn, *, coordinator_id: str, site_id: str, month: date) -> None:
    update_employee(conn, coordinator_id=coordinator_id, site_id=site_id, employee=Employee(EMP, EMP, date(2020, 1, 1), None, False))
    update_membership(
        conn, coordinator_id=coordinator_id, site_id=site_id,
        membership=SiteMembership(EMP, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    # ROTA-T058 (owner-authorized fixture fix, 2026-09-08): a single employee
    # covering every day of the month now genuinely trips the new HARD
    # max-two-consecutive-PRIMARY-shifts rule -- this helper is about
    # site/coordinator lifecycle mechanics, not staffing tightness, so a
    # second employee restores real slack without touching what these tests
    # actually assert.
    update_employee(conn, coordinator_id=coordinator_id, site_id=site_id, employee=Employee(EMP2, EMP2, date(2020, 1, 1), None, False))
    update_membership(
        conn, coordinator_id=coordinator_id, site_id=site_id,
        membership=SiteMembership(EMP2, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
    )
    days = _calendar.monthrange(month.year, month.month)[1]
    for d in range(1, days + 1):
        set_calendar_day(conn, coordinator_id=coordinator_id, site_id=site_id, day=CalendarDay(date(month.year, month.month, d), False))


def _plan_and_finalize(conn, *, coordinator_id: str, site_id: str, month: date) -> None:
    result = plan_month(conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=month)
    assert result.status == "FEASIBLE"
    select_candidate(conn, site_id=site_id, month=month, candidate=result.candidates[0], coordinator_id=coordinator_id)
    revalidate(conn, site_id=site_id, month=month, coordinator_id=coordinator_id)
    state, _warnings = assemble_planning_state(conn, site_id=site_id, month=month)
    finalize(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id,
        acknowledged_deviation_ids={d.deviation_id for d in state.deviations},
    )


def _site_view(conn, *, coordinator_id: str, site_id: str) -> Site:
    return next(s for s in all_sites_for_coordinator(conn, coordinator_id=coordinator_id) if s.site_id == site_id)


def test_1_site_display_name_change_persists_other_fields_unchanged(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, "Renamed A"))
    view = _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A)
    assert view.display_name == "Renamed A"
    assert view.profile_id == PROFILE_A
    assert view.active is True
    assert view.site_id == SITE_A


def test_2_payload_with_foreign_site_id_rejected(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    with pytest.raises(InvalidCoordinatorContext):
        update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_OTHER, PROFILE_A, "Wrong site"))
    view = _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A)
    assert view.display_name == f"Site {SITE_A}"


def test_3_profile_rebind_rejected_before_any_write(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A, profile_id=PROFILE_A)
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_OTHER, profile_id=PROFILE_OTHER)  # PROFILE_OTHER now exists

    with pytest.raises(InvalidCoordinatorContext):
        update_site(
            conn, coordinator_id=COORD_A, site_id=SITE_A,
            site=_site(SITE_A, PROFILE_OTHER, "Renamed while rebinding"),
        )

    view = _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A)
    assert view.profile_id == PROFILE_A  # not switched
    assert view.display_name == f"Site {SITE_A}"  # not renamed either -- rejected before any partial write


def test_4_update_site_without_active_context_rejected(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    with pytest.raises(InvalidCoordinatorContext):
        update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, "No context"))


def test_5_deactivating_association_locks_out_further_edits_but_not_reads(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff_and_fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH)
    record_structured_rule_decision(
        conn, coordinator_id=COORD_A, site_id=SITE_A, rule_id=RULE_ID, statement="Lockout probe rule.",
        effective_from=MONTH, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE, rule_kind=None, structured_parameters=None,
            enforcement=RuleEnforcement.INFORMATIONAL, resolution_status=RuleResolution.RESOLVED,
            effective_to=None, description=None, source=None, reason=None,
        ),
    )

    update_association(conn, coordinator_id=COORD_A, site_id=SITE_A, association=CoordinatorSiteAssociation(COORD_A, SITE_A, False))

    with pytest.raises(InvalidCoordinatorContext):
        update_employee(conn, coordinator_id=COORD_A, site_id=SITE_A, employee=Employee(EMP, "New name", date(2020, 1, 1), None, False))

    view = open_month(conn, site_id=SITE_A, month=MONTH)  # reads never check the guard
    assert view.site.site_id == SITE_A
    chain = decision_chain_for_rule_family(conn, site_id=SITE_A, rule_id=RULE_ID)  # WYMAGANE TESTY pt.5: memory_read too
    assert len(chain) == 1
    assert chain[0].statement == "Lockout probe rule."


def test_5b_deactivating_site_or_coordinator_is_also_reversible(tmp_path) -> None:
    # C-R3-1 closure: bootstrap resume must work identically no matter which
    # of the three entities caused the lockout, not only Association -- see
    # bootstrap._has_full_active_context's docstring.
    for entity in ("site", "coordinator"):
        conn = store.open_store(tmp_path / f"rota-{entity}.db")
        _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
        if entity == "site":
            update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, f"Site {SITE_A}", active=False))
        else:
            update_coordinator(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_A, f"Coord {COORD_A}", False))

        with pytest.raises(InvalidCoordinatorContext):
            update_employee(conn, coordinator_id=COORD_A, site_id=SITE_A, employee=Employee(EMP, "X", date(2020, 1, 1), None, False))

        reactivated = _site(SITE_A, PROFILE_A, f"Site {SITE_A}") if entity == "site" else None
        reactivated_coordinator = Coordinator(COORD_A, f"Coord {COORD_A}", True) if entity == "coordinator" else None
        bootstrap_or_resume_coordinator_context(
            conn, coordinator_id=COORD_A, site_id=SITE_A, site=reactivated, coordinator=reactivated_coordinator,
        )
        update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, f"Recovered after {entity}"))
        assert _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A).display_name == f"Recovered after {entity}"


def test_6_resume_after_self_lockout_restores_editing(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    update_association(conn, coordinator_id=COORD_A, site_id=SITE_A, association=CoordinatorSiteAssociation(COORD_A, SITE_A, False))

    bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD_A, site_id=SITE_A, association=CoordinatorSiteAssociation(COORD_A, SITE_A, True),
    )

    update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, "Resumed edit"))
    assert _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A).display_name == "Resumed edit"


def test_7_bootstrap_still_refuses_while_context_is_active(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    with pytest.raises(CoordinatorContextAlreadyActive):
        bootstrap_or_resume_coordinator_context(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_A, "X", True))


def test_8_deactivating_site_keeps_finalized_history_readable(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff_and_fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH)
    _plan_and_finalize(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH)

    update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, f"Site {SITE_A}", active=False))

    view = open_month(conn, site_id=SITE_A, month=MONTH)
    assert view.current_version is not None
    assert view.current_version.status.value.startswith("FINAL")
    assert SITE_A not in {s.site_id for s in active_sites_for_coordinator(conn, coordinator_id=COORD_A)}
    assert SITE_A in {s.site_id for s in all_sites_for_coordinator(conn, coordinator_id=COORD_A)}


def test_9_restart_yields_the_same_lifecycle_state(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _staff_and_fill_calendar(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH)
    _plan_and_finalize(conn, coordinator_id=COORD_A, site_id=SITE_A, month=MONTH)
    update_coordinator(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_A, "Coord before restart", True))
    # active=False LAST -- any durable_inputs call for SITE_A after this would
    # itself be blocked by the guard (WYMAGANE TESTY pt.9: a changed active
    # flag must be part of what restart proves, per C-R3-3).
    update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, "Before restart", active=False))

    before = (
        tuple(all_coordinators(conn)), tuple(all_sites_for_coordinator(conn, coordinator_id=COORD_A)),
        open_month(conn, site_id=SITE_A, month=MONTH),
    )
    conn.close()

    reopened = store.open_store(db_path)
    after = (
        tuple(all_coordinators(reopened)), tuple(all_sites_for_coordinator(reopened, coordinator_id=COORD_A)),
        open_month(reopened, site_id=SITE_A, month=MONTH),
    )
    assert after == before
    assert before[1][0].active is False  # the flag actually changed, not just the name


def test_10_association_payload_with_foreign_site_id_rejected(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    with pytest.raises(InvalidCoordinatorContext):
        update_association(
            conn, coordinator_id=COORD_A, site_id=SITE_A,
            association=CoordinatorSiteAssociation(COORD_A, SITE_OTHER, True),
        )


def test_11_coordinator_changes_own_display_name(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    update_coordinator(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_A, "New Name A", True))
    assert [c.display_name for c in all_coordinators(conn) if c.coordinator_id == COORD_A] == ["New Name A"]


def test_12_writing_another_coordinators_own_record_is_permitted_by_design(tmp_path) -> None:
    # ROTA-T011-C (ROZSTRZYGNIĘCIE WŁAŚCICIELA 2026-08-14): no coordinator-
    # identity check is a deliberate product decision, not a gap -- this
    # product has no multi-user-per-installation model. This test proves
    # the accepted behavior, not a vulnerability.
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _bootstrap(conn, coordinator_id=COORD_B, site_id=SITE_A)

    update_coordinator(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_B, "Renamed by A", True))
    update_coordinator(conn, coordinator_id=COORD_A, site_id=SITE_A, coordinator=Coordinator(COORD_B, "Renamed by A", False))

    assert [c.display_name for c in all_coordinators(conn) if c.coordinator_id == COORD_B] == ["Renamed by A"]
    assert COORD_B not in {c.coordinator_id for c in active_coordinators(conn)}


def test_13_revoking_another_coordinators_association_removes_their_edit_access(tmp_path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap(conn, coordinator_id=COORD_A, site_id=SITE_A)
    _bootstrap(conn, coordinator_id=COORD_B, site_id=SITE_A)

    update_association(conn, coordinator_id=COORD_A, site_id=SITE_A, association=CoordinatorSiteAssociation(COORD_B, SITE_A, False))

    with pytest.raises(InvalidCoordinatorContext):
        update_coordinator(conn, coordinator_id=COORD_B, site_id=SITE_A, coordinator=Coordinator(COORD_B, "Still trying", True))

    update_site(conn, coordinator_id=COORD_A, site_id=SITE_A, site=_site(SITE_A, PROFILE_A, "A still can edit"))
    assert _site_view(conn, coordinator_id=COORD_A, site_id=SITE_A).display_name == "A still can edit"


def test_14_this_file_never_imports_rota_persistence_at_module_scope() -> None:
    import ast
    from pathlib import Path

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("rota.persistence"), alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("rota.persistence"), node.module
