"""ROTA-T007 REQUIRED INTEGRATION SCENARIO -- TWO MONTHS (matrix item N).

Proves the full vertical path with a REAL SQLite-backed Decision Ledger,
not a fixture that inserts SiteRuleVersion directly into PlanningState: a
rule saved once through T005 is automatically rediscovered and applied by
real plan() across two separate months, after closing and reopening the
database, without the test ever passing a rule_id to the month assembler.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from rota.domain import (
    Employee,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    SiteMembership,
)
from rota.persistence.db import connect
from rota.persistence.decision_ledger import record_decision
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.planning.engine import plan
from rota.planning.site_rules import EMPLOYEE_ALLOWED_SHIFT_KINDS, EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS
from rota.site_memory_types import NewRuleContent
from tests.support.minimal_state import ReadinessSource, ReadinessState, SITE_ID, base_state


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _employee(employee_id: str) -> Employee:
    return Employee(employee_id, employee_id, date(2026, 9, 1), None, False)


def _friday_d(demand_id: str, day: int, month: int = 10) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, month, day, 5, 0), datetime(2026, month, day, 17, 0), 1)


def _friday_n(demand_id: str, day: int, month: int = 10) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, month, day, 17, 0), datetime(2026, month, day + 1, 5, 0), 1)


def _record(conn, *, rule_id: str, statement: str, rule_kind: str, parameters: dict) -> None:
    record_decision(
        conn,
        site_id=SITE_ID,
        rule_id=rule_id,
        statement=statement,
        coordinator_id="COORD-1",
        recorded_at=datetime(2026, 9, 1, 9, 0),
        effective_from=date(2026, 9, 1),
        rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE,
            rule_kind=rule_kind,
            structured_parameters=parameters,
            enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED,
            effective_to=None,
            description=None,
            source=None,
            reason=None,
        ),
    )


def _record_the_friday_d_ban(db_path: Path) -> None:
    """Step 1: save through T005 Decision Ledger a RESOLVED HARD rule for
    employee A, effective across both planning months, then close the
    connection (step 2 reopens it before month 1). A second rule keeps B
    D-only so B can't silently absorb the Friday-N demand -- without it,
    CP-SAT's tie-break could hand Friday N to either A or B, which would
    prove nothing about A's own eligibility (brief.md REQUIRED INTEGRATION
    SCENARIO: "N allowed" must be actually demonstrated, not merely
    untested)."""
    conn = connect(db_path)
    _record(
        conn, rule_id="R-FRIDAY-D-BAN", statement="Pracownik A nie pracuje w piatki na D.",
        rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": "A", "weekdays": [5], "forbidden_shift_kinds": ["D"]},
    )
    _record(
        conn, rule_id="R-B-DAY-ONLY", statement="Pracownik B pracuje tylko na D.",
        rule_kind=EMPLOYEE_ALLOWED_SHIFT_KINDS, parameters={"employee_id": "B", "allowed_shift_kinds": ["D"]},
    )
    conn.close()


def _run_one_month(db_path: Path, month: date, friday_day: int) -> tuple:
    """Steps 3-4 (month 1) / step 5 (month 2, reusing the same db_path
    without re-entering the rule): reopen the database, assemble the
    monthly SiteRule context with zero manually-supplied rule_ids, build
    PlanningState from that projection, and run real plan().

    B is D-only per its own remembered rule, so only A can cover Friday N --
    A actually covering it proves "N allowed", not merely "N untested"
    (brief.md REQUIRED INTEGRATION SCENARIO assertion)."""
    conn = connect(db_path)
    resolved, unresolved, applicability = assemble_monthly_site_rules(conn, SITE_ID, month)

    fri_d = _friday_d(f"FRI_D_{month.month}", friday_day, month.month)
    fri_n = _friday_n(f"FRI_N_{month.month}", friday_day, month.month)
    state = base_state(
        employees=(_employee("A"), _employee("B")), memberships=(_membership("A"), _membership("B")),
        shift_demands=(fri_d, fri_n),
        site_rules=resolved, unresolved_site_rules=unresolved, site_rule_applicability=applicability,
        month=month,
    )
    result = plan(state)
    conn.close()
    return result, fri_d.demand_id, fri_n.demand_id


def test_n_remembered_rule_automatically_blocks_friday_d_across_two_months_after_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    _record_the_friday_d_ban(db_path)

    result_october, fri_d_oct, fri_n_oct = _run_one_month(db_path, date(2026, 10, 1), friday_day=2)
    assert result_october.status == "FEASIBLE"
    october_pairs = {(a.employee_id, a.covers_demand_id) for a in result_october.candidates[0]}
    assert ("A", fri_d_oct) not in october_pairs
    assert ("B", fri_d_oct) in october_pairs
    assert ("A", fri_n_oct) in october_pairs  # A was the only one eligible/available -> "N allowed" proven

    # Step 5: second month, same remembered rule, no re-entry.
    result_november, fri_d_nov, fri_n_nov = _run_one_month(db_path, date(2026, 11, 1), friday_day=6)
    assert result_november.status == "FEASIBLE"
    november_pairs = {(a.employee_id, a.covers_demand_id) for a in result_november.candidates[0]}
    assert ("A", fri_d_nov) not in november_pairs
    assert ("B", fri_d_nov) in november_pairs
    assert ("A", fri_n_nov) in november_pairs
