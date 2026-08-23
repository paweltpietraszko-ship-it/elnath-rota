"""Independent implementation audit for ROTA-T021b, round 4.

The cases below exercise contract-owned equivalence classes omitted from the
delivery test matrix: malformed current matrix-family shapes on both mutation
paths, and semantically faithful statements for valid broader families.
"""
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
    record_structured_rule_decision,
    update_employee_matrix_rule_period,
)
from rota.domain import (
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftKind,
    Site,
    SitePlanningRegime,
    SiteProfile,
)
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee
from rota.persistence.site_memory import list_coordinator_actions, rule_history
from rota.planning.site_rules import (
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
)
from rota.site_memory_types import CoordinatorActionKind, NewRuleContent


COORD = "COORD-T021B-R4"
SITE = "SITE-T021B-R4"
PROFILE = "PROFILE-T021B-R4"


@pytest.fixture
def conn():
    connection = connect(":memory:")
    _bootstrap_context(connection)
    yield connection
    connection.close()


def _bootstrap_context(connection) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        connection,
        coordinator_id=COORD,
        site_id=SITE,
        coordinator=Coordinator(COORD, "Audytor", True),
        site_profile=SiteProfile(PROFILE, "Profil", True, [], True, True, False, False, 1, 40),
        site=Site(SITE, PROFILE, "Obiekt", True, SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE, True),
    )
    save_employee(connection, Employee("EMP-1", "Jan Kowalski", date(2026, 1, 1), None, False))
    save_employee(connection, Employee("EMP-2", "Anna Nowak", date(2026, 1, 1), None, True))


def _record_family(conn, *, rule_id: str, rule_kind: str, parameters: object) -> None:
    category = (
        RuleCategory.CONFIRMED_EXCEPTION
        if rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION
        else RuleCategory.LOCAL_RULE
    )
    record_structured_rule_decision(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id=rule_id,
        statement="rodzina wejściowa audytu",
        effective_from=date(2026, 9, 1),
        rule_content=NewRuleContent(
            category=category,
            rule_kind=rule_kind,
            structured_parameters=parameters,
            enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED,
            effective_to=date(2026, 9, 30),
            description=None,
            source=None,
            reason=None,
        ),
    )


def _material_counts(conn, rule_id: str) -> tuple[int, int]:
    actions = list_coordinator_actions(
        conn,
        site_id=SITE,
        action_kind=CoordinatorActionKind.RULE_DECISION_RECORDED,
    )
    return len(rule_history(conn, SITE, rule_id)), len(actions)


MALFORMED_MATRIX_SHAPES = [
    pytest.param(
        EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        {"employee_id": "EMP-1", "weekdays": list(range(1, 8)), "forbidden_shift_kinds": ["D"], "extra": True},
        id="forbidden-extra-key",
    ),
    pytest.param(
        EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        {"employee_id": "EMP-1", "weekdays": [1, 2], "forbidden_shift_kinds": ["X"]},
        id="forbidden-unknown-shift-kind",
    ),
    pytest.param(
        EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        {"employee_id": "EMP-1", "weekdays": [1, 2], "forbidden_shift_kinds": []},
        id="forbidden-empty-shift-kinds",
    ),
    pytest.param(
        EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        {"employee_id": "EMP-1", "extra": "not-part-of-the-shape"},
        id="day-only-extra-key",
    ),
]


@pytest.mark.parametrize("operation", ["update", "end"])
@pytest.mark.parametrize(("rule_kind", "parameters"), MALFORMED_MATRIX_SHAPES)
def test_mutation_rejects_every_malformed_current_matrix_shape_without_write(
    conn, operation, rule_kind, parameters
):
    """§3.4/§3.5 and §7: only a valid matrix-owned shape may be mutated."""
    rule_id = f"R-MALFORMED-{operation}-{rule_kind}-{len(str(parameters))}"
    _record_family(conn, rule_id=rule_id, rule_kind=rule_kind, parameters=parameters)
    before = _material_counts(conn, rule_id)

    caught = None
    try:
        if operation == "update":
            update_employee_matrix_rule_period(
                conn,
                coordinator_id=COORD,
                site_id=SITE,
                rule_id=rule_id,
                effective_from=date(2026, 10, 1),
                effective_to=date(2026, 10, 31),
            )
        else:
            end_employee_matrix_rule_early(
                conn,
                coordinator_id=COORD,
                site_id=SITE,
                rule_id=rule_id,
                effective_from=date(2026, 9, 15),
            )
    except (KeyError, TypeError, ValueError) as exc:
        caught = exc

    assert _material_counts(conn, rule_id) == before, "invalid family was materially mutated"
    assert caught is not None, "invalid family was accepted instead of rejected"


@pytest.mark.parametrize("operation", ["update", "end"])
def test_valid_broader_family_statement_does_not_selectively_describe_only_one_weekday(conn, operation):
    """§3.4 and §6: broader valid content is supported and its statement stays semantic."""
    rule_id = f"R-BROAD-{operation}"
    _record_family(
        conn,
        rule_id=rule_id,
        rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "EMP-1", "weekdays": [1, 2], "forbidden_shift_kinds": ["D", "N"]},
    )

    if operation == "update":
        decision = update_employee_matrix_rule_period(
            conn,
            coordinator_id=COORD,
            site_id=SITE,
            rule_id=rule_id,
            effective_from=date(2026, 10, 1),
            effective_to=date(2026, 10, 31),
        )
    else:
        decision = end_employee_matrix_rule_early(
            conn,
            coordinator_id=COORD,
            site_id=SITE,
            rule_id=rule_id,
            effective_from=date(2026, 9, 15),
        )

    statement = decision.statement.lower()
    mentioned = {
        weekday
        for weekday, token in ((1, "poniedział"), (2, "wtorek"))
        if token in statement
    }
    assert mentioned in (set(), {1, 2}), (
        "the generated semantic statement selectively names only part of the "
        f"preserved weekday set: {decision.statement!r}"
    )


def test_create_update_end_projection_survives_real_database_restarts(tmp_path):
    """§8/§10: projection remains callable and accurate after every reopen."""
    database = tmp_path / "t021b-restart.sqlite"
    connection = connect(str(database))
    _bootstrap_context(connection)
    created = create_employee_shift_unavailability(
        connection,
        coordinator_id=COORD,
        site_id=SITE,
        employee_id="EMP-1",
        shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1),
        effective_to=date(2026, 9, 30),
    )
    connection.close()

    connection = connect(str(database))
    after_create = employee_availability_matrix(
        connection, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1)
    )
    assert len(after_create.weekday_and_exception_rules) == 1
    updated = update_employee_matrix_rule_period(
        connection,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id=created.rule_id,
        effective_from=date(2026, 9, 2),
        effective_to=date(2026, 9, 30),
    )
    connection.close()

    connection = connect(str(database))
    after_update = employee_availability_matrix(
        connection, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1)
    )
    assert {r.rule_version_id for r in after_update.weekday_and_exception_rules} == {
        created.rule_version_id,
        updated.rule_version_id,
    }
    update_slices = {
        item.rule_version_id: (item.applies_from, item.applies_to)
        for item in after_update.rule_applicability
    }
    assert update_slices[created.rule_version_id] == (date(2026, 9, 1), date(2026, 9, 1))
    assert update_slices[updated.rule_version_id] == (date(2026, 9, 2), date(2026, 9, 30))
    end_employee_matrix_rule_early(
        connection,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id=created.rule_id,
        effective_from=date(2026, 9, 15),
    )
    connection.close()

    connection = connect(str(database))
    after_end = employee_availability_matrix(
        connection, site_id=SITE, employee_id="EMP-1", month=date(2026, 9, 1)
    )
    assert {r.rule_version_id for r in after_end.weekday_and_exception_rules} == {
        created.rule_version_id,
        updated.rule_version_id,
    }
    assert after_end.rule_applicability
    assert max(
        slice_.applies_to
        for slice_ in after_end.rule_applicability
        if slice_.rule_version_id == updated.rule_version_id
    ) == date(2026, 9, 14)
    connection.close()


def test_each_of_the_five_wrappers_adds_exactly_one_existing_material_action(conn):
    """§7/§10: one logical wrapper call produces exactly one ledger action."""
    action_kind = CoordinatorActionKind.RULE_DECISION_RECORDED

    def count() -> int:
        return len(list_coordinator_actions(conn, site_id=SITE, action_kind=action_kind))

    before = count()
    shift = create_employee_shift_unavailability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        employee_id="EMP-1",
        shift_kind=ShiftKind.D,
        effective_from=date(2026, 9, 1),
        effective_to=date(2026, 9, 30),
    )
    assert count() == before + 1

    create_employee_weekday_unavailability(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        employee_id="EMP-1",
        iso_weekday=5,
        effective_from=date(2026, 9, 1),
        effective_to=date(2026, 9, 30),
    )
    assert count() == before + 2

    create_day_only_n_exception(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        employee_id="EMP-2",
        effective_from=date(2026, 9, 1),
        effective_to=date(2026, 9, 30),
    )
    assert count() == before + 3

    update_employee_matrix_rule_period(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id=shift.rule_id,
        effective_from=date(2026, 9, 2),
        effective_to=date(2026, 9, 30),
    )
    assert count() == before + 4

    end_employee_matrix_rule_early(
        conn,
        coordinator_id=COORD,
        site_id=SITE,
        rule_id=shift.rule_id,
        effective_from=date(2026, 9, 15),
    )
    assert count() == before + 5
