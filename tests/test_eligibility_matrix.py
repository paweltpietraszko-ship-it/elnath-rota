"""Consolidated eligibility matrix (tasks_r16.txt AUDITOR PROCESS DECISION).

After 16 audit rounds where exact reproducers kept getting fixed while a
sibling path of the same invariant stayed broken, the auditor asked for one
consolidated run of the already-established HARD/eligibility invariants
across: LOCAL/EXTERNAL, existing/solved, current-site/other-site/missing
membership, and enabled/disabled. This file adds no new requirement -- every
expected outcome below is already covered individually by
test_audit_r12/r13/r14/r15/r16_findings.py. This is the same MEMBERSHIP-01 /
EXTERNAL-01 invariant exercised systematically instead of one reproducer at
a time.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    Employee,
    ExternalSupportWindow,
    MembershipKind,
    ShiftDemand,
    SiteMembership,
)
from rota.planning.engine import plan
from rota.planning.validator import validate
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state

DEMAND_D = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
EMPLOYEE_ID = "M"

# (membership_kind, site_scope, enabled, expect_authorized)
# site_scope: "current" | "other" | "missing" (no membership record at all)
MATRIX = [
    (MembershipKind.LOCAL, "current", True, True),
    (MembershipKind.LOCAL, "current", False, False),
    (MembershipKind.LOCAL, "other", True, False),
    (MembershipKind.LOCAL, "other", False, False),
    (MembershipKind.LOCAL, "missing", None, False),
    (MembershipKind.EXTERNAL_SUPPORT, "current", True, True),
    (MembershipKind.EXTERNAL_SUPPORT, "current", False, False),
    (MembershipKind.EXTERNAL_SUPPORT, "other", True, False),
    (MembershipKind.EXTERNAL_SUPPORT, "other", False, False),
    (MembershipKind.EXTERNAL_SUPPORT, "missing", None, False),
]
MATRIX_IDS = [f"{kind.value}-{scope}-{enabled}" for kind, scope, enabled, _ in MATRIX]


def _build_state(kind, site_scope, enabled) -> object:
    employee = Employee(EMPLOYEE_ID, EMPLOYEE_ID, date(2026, 9, 1), None, False)
    memberships: tuple = ()
    windows: tuple = ()
    if site_scope != "missing":
        site_id = SITE_ID if site_scope == "current" else "other-site"
        memberships = (
            SiteMembership(EMPLOYEE_ID, site_id, kind, enabled, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
        )
        if kind == MembershipKind.EXTERNAL_SUPPORT:
            windows = (
                ExternalSupportWindow(
                    "win-1", EMPLOYEE_ID, site_id, datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 2, 0, 0), True, None
                ),
            )
    return base_state(
        employees=(employee,), memberships=memberships, external_windows=windows, shift_demands=(DEMAND_D,),
    )


@pytest.mark.parametrize("kind,site_scope,enabled,expect_authorized", MATRIX, ids=MATRIX_IDS)
def test_matrix_solved_path(kind, site_scope, enabled, expect_authorized):
    state = _build_state(kind, site_scope, enabled)
    result = plan(state)
    if expect_authorized:
        assert result.status == "FEASIBLE"
    else:
        assert result.status != "FEASIBLE"


@pytest.mark.parametrize("kind,site_scope,enabled,expect_authorized", MATRIX, ids=MATRIX_IDS)
def test_matrix_existing_path(kind, site_scope, enabled, expect_authorized):
    state = _build_state(kind, site_scope, enabled)
    existing = Assignment(
        "existing-1", "test-v1", EMPLOYEE_ID, DEMAND_D.start_datetime, DEMAND_D.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, DEMAND_D.demand_id, None,
    )
    report = validate(state, [existing])
    assert report.hard_pass == expect_authorized, report.violations


if __name__ == "__main__":
    print("test_eligibility_matrix module OK")
