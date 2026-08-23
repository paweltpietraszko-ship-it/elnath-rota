"""ROTA-T021b (tasks/ROTA-T021b/brief.md): focused tests for the employee
matrix wrapper commands added to rota/application/rule_decisions.py.
Reuses T005/T007/T010-B regressions unchanged (full suite run separately)."""
from __future__ import annotations

from datetime import date

import pytest

from rota.application import bootstrap
from rota.application.availability_matrix import employee_availability_matrix
from rota.application.rule_decisions import (
    create_day_only_n_exception,
    create_employee_shift_unavailability,
    create_employee_weekday_unavailability,
    end_employee_matrix_rule_early,
    update_employee_matrix_rule_period,
)
from rota.domain import (
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.persistence.site_memory import current_decision_required_months_for_site
from rota.site_memory_types import CoordinatorActionKind

COORD = "COORD-1"
SITE = "SITE-1"
PROFILE = "PROF-1"


@pytest.fixture
def conn():
    connection = connect(":memory:")
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection, coordinator_id=COORD, site_id=SITE,
        coordinator=Coordinator(COORD, "Coordinator", True),
        site_profile=SiteProfile(PROFILE, "Profile", True, [], True, True, False, False, 1, 40),
        site=Site(SITE, PROFILE, "Site", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    save_employee(connection, Employee("EMP-1", "Jan Kowalski", date(2026, 1, 1), None, False))
    save_employee(connection, Employee("EMP-2", "Anna Nowak", date(2026, 1, 1), None, True))
    try:
        yield connection
    finally:
        connection.close()


def _action_count(conn, kind: CoordinatorActionKind) -> int:
    from rota.persistence.site_memory import list_coordinator_actions
    return len(list_coordinator_actions(conn, site_id=SITE, action_kind=kind))


# 1. D and N creation
@pytest.mark.parametrize("shift_kind", [ShiftKind.D, ShiftKind.N])
def test_create_shift_unavailability(conn, shift_kind):
    rec = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=shift_kind,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    assert rec.rel is None
    assert rec.rule_version_id is not None
    matrix = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1))
    version = matrix.weekday_and_exception_rules[0]
    assert version.category.value == "LOCAL_RULE"
    assert version.enforcement.value == "HARD"
    assert version.resolution_status.value == "RESOLVED"
    assert version.structured_parameters == {
        "employee_id": "EMP-1", "weekdays": [1, 2, 3, 4, 5, 6, 7], "forbidden_shift_kinds": [shift_kind.value],
    }
    assert version.effective_from == date(2026, 9, 1)
    assert version.effective_to == date(2026, 9, 30)


# 2. weekday creation + invalid weekday/date range
def test_create_weekday_unavailability(conn):
    rec = create_employee_weekday_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", iso_weekday=5,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    matrix = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1))
    version = matrix.weekday_and_exception_rules[0]
    assert version.structured_parameters == {"employee_id": "EMP-1", "weekdays": [5], "forbidden_shift_kinds": ["D", "N"]}
    assert rec.rule_version_id is not None


@pytest.mark.parametrize("bad_weekday", [0, 8, True, False])
def test_create_weekday_unavailability_rejects_invalid_weekday(conn, bad_weekday):
    with pytest.raises(ValueError):
        create_employee_weekday_unavailability(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", iso_weekday=bad_weekday,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


def test_create_weekday_unavailability_rejects_reversed_range(conn):
    with pytest.raises(ValueError):
        create_employee_weekday_unavailability(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", iso_weekday=1,
            effective_from=date(2026, 9, 30), effective_to=date(2026, 9, 1),
        )


# 3. unknown employee across all creates, zero writes
@pytest.mark.parametrize(
    "call",
    [
        lambda conn: create_employee_shift_unavailability(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="NOPE", shift_kind=ShiftKind.D,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        ),
        lambda conn: create_employee_weekday_unavailability(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="NOPE", iso_weekday=1,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        ),
        lambda conn: create_day_only_n_exception(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="NOPE",
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        ),
    ],
)
def test_unknown_employee_rejected_with_no_write(conn, call):
    before = _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED)
    with pytest.raises(Exception):
        call(conn)
    after = _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED)
    assert before == after


# 4. day_only=true N exception content; day_only=false rejects
def test_day_only_n_exception_content(conn):
    rec = create_day_only_n_exception(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-2",
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 10),
    )
    matrix = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-2", month=date(2026, 9, 1))
    version = matrix.weekday_and_exception_rules[0]
    assert version.category.value == "CONFIRMED_EXCEPTION"
    assert version.rule_kind == "EMPLOYEE_DAY_ONLY_N_EXCEPTION"
    assert version.structured_parameters == {"employee_id": "EMP-2"}
    assert rec.rule_version_id is not None


def test_day_only_n_exception_rejects_non_day_only_employee(conn):
    before = _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED)
    with pytest.raises(ValueError):
        create_day_only_n_exception(
            conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1",
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 10),
        )
    assert _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED) == before


# 5. update dates
def test_update_period_supersedes_same_family(conn):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    updated = update_employee_matrix_rule_period(
        conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 10, 15),
    )
    assert updated.rule_id == created.rule_id
    assert updated.rel == "supersedes"
    assert updated.rule_version_id != created.rule_version_id
    matrix = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-1", month=date(2026, 10, 1))
    version = matrix.weekday_and_exception_rules[0]
    assert version.effective_to == date(2026, 10, 15)
    assert version.structured_parameters["forbidden_shift_kinds"] == ["D"]


# 6. early return boundaries, bounded rule
@pytest.mark.parametrize(
    ("reject_from", "should_pass"),
    [
        (date(2026, 8, 31), False),  # before start
        (date(2026, 9, 1), True),  # equal start
        (date(2026, 9, 15), True),  # inside
        (date(2026, 9, 30), True),  # equal end
        (date(2026, 10, 1), False),  # after end
    ],
)
def test_end_early_bounded_rule_boundaries(conn, reject_from, should_pass):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    if should_pass:
        rec = end_employee_matrix_rule_early(
            conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id, effective_from=reject_from,
        )
        assert rec.rel == "rejects"
        assert rec.rule_version_id is None
    else:
        with pytest.raises(ValueError):
            end_employee_matrix_rule_early(
                conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id, effective_from=reject_from,
            )


# 7. early return boundaries, open-ended rule (via update with far-future effective_to
# standing in for "legitimate pre-existing open-ended family" is not constructible
# through these wrappers -- exercised directly against record_structured_rule_decision)
def test_end_early_open_ended_rule_boundaries(conn):
    from rota.application.rule_decisions import record_structured_rule_decision
    from rota.domain import RuleCategory, RuleEnforcement, RuleResolution
    from rota.site_memory_types import NewRuleContent

    rule_id = "R-EMP-MATRIX-openended"
    record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE, rule_id=rule_id, statement="test open-ended",
        effective_from=date(2026, 9, 1), rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE, rule_kind="EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS",
            structured_parameters={"employee_id": "EMP-1", "weekdays": [1, 2, 3, 4, 5, 6, 7], "forbidden_shift_kinds": ["D"]},
            enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
            effective_to=None, description=None, source=None, reason=None,
        ),
    )
    with pytest.raises(ValueError):
        end_employee_matrix_rule_early(conn, coordinator_id=COORD, site_id=SITE, rule_id=rule_id, effective_from=date(2026, 8, 31))
    rec = end_employee_matrix_rule_early(conn, coordinator_id=COORD, site_id=SITE, rule_id=rule_id, effective_from=date(2026, 9, 1))
    assert rec.rel == "rejects"


# 8. new independent period uses a different rule_id
def test_new_period_uses_different_rule_id(conn):
    first = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 10),
    )
    second = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 10),
    )
    assert first.rule_id != second.rule_id


# 9. update/end rejects invalid families
def test_update_rejects_unknown_rule_id(conn):
    with pytest.raises(ValueError):
        update_employee_matrix_rule_period(
            conn, coordinator_id=COORD, site_id=SITE, rule_id="NOPE",
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


def test_update_rejects_wrong_site(conn):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    with pytest.raises(Exception):
        update_employee_matrix_rule_period(
            conn, coordinator_id=COORD, site_id="OTHER-SITE", rule_id=created.rule_id,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


def test_update_rejects_ended_family(conn):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    end_employee_matrix_rule_early(conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id, effective_from=date(2026, 9, 1))
    with pytest.raises(ValueError):
        update_employee_matrix_rule_period(
            conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


def test_update_rejects_non_matrix_family(conn):
    from rota.application.rule_decisions import record_structured_rule_decision
    from rota.domain import RuleCategory, RuleEnforcement, RuleResolution
    from rota.site_memory_types import NewRuleContent

    rule_id = "R-CLIENT-REQ"
    record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE, rule_id=rule_id, statement="client requirement",
        effective_from=date(2026, 9, 1), rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.CLIENT_REQUIREMENT, rule_kind=None, structured_parameters=None,
            enforcement=RuleEnforcement.INFORMATIONAL, resolution_status=RuleResolution.RESOLVED,
            effective_to=None, description="not a matrix rule", source=None, reason=None,
        ),
    )
    with pytest.raises(ValueError):
        update_employee_matrix_rule_period(
            conn, coordinator_id=COORD, site_id=SITE, rule_id=rule_id,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


def test_update_rejects_family_with_deleted_employee(conn):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    conn.execute("DELETE FROM employees WHERE employee_id = 'EMP-1'")
    conn.commit()
    with pytest.raises(Exception):
        update_employee_matrix_rule_period(
            conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id,
            effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
        )


# 10. generated statement is Polish, no statement param on the public functions
def test_statement_is_generated_not_supplied():
    import inspect

    for fn in (create_employee_shift_unavailability, create_employee_weekday_unavailability, create_day_only_n_exception):
        assert "statement" not in inspect.signature(fn).parameters


def test_generated_statement_is_polish(conn):
    rec = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    assert "Dniówka" in rec.statement
    assert "niedostępna" in rec.statement


# 11. effective projection round trip
def test_effective_projection_round_trip(conn):
    created = create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 10),
    )
    matrix = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1))
    assert len(matrix.rule_applicability) == 1
    assert matrix.rule_applicability[0].applies_to == date(2026, 9, 10)

    # equal-start reject: zero effective days for the cancelled family
    end_employee_matrix_rule_early(conn, coordinator_id=COORD, site_id=SITE, rule_id=created.rule_id, effective_from=date(2026, 9, 1))
    matrix_after = employee_availability_matrix(conn, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1))
    assert matrix_after.weekday_and_exception_rules == ()
    assert matrix_after.rule_applicability == ()


# 13. exactly one coordinator action per successful call, DECISION_REQUIRED invalidation reused
def test_one_coordinator_action_per_call(conn):
    before = _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED)
    create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    assert _action_count(conn, CoordinatorActionKind.RULE_DECISION_RECORDED) == before + 1


def test_current_decision_required_months_still_readable_after_writes(conn):
    create_employee_shift_unavailability(
        conn, coordinator_id=COORD, site_id=SITE, employee_id="EMP-1", shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1), effective_to=date(2026, 9, 30),
    )
    assert current_decision_required_months_for_site(conn, site_id=SITE) == []
