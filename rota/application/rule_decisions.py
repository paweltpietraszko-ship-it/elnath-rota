"""Operation 7 (tasks/ROTA-T009/brief.md): structured SiteRule decision seam
for a future T010 caller. Every value is already resolved by the caller --
this function infers nothing from text and contains no parser/LLM/DSL.

ROTA-T021b (tasks/ROTA-T021b/brief.md): thin semantic commands over
record_structured_rule_decision() for the frozen employee matrix (Dniówka/
Nocka/weekday + the day_only temporary N exception). These do not add a
rule engine or a new persistence model -- every write still goes through
record_structured_rule_decision(); this module only builds the correct
NewRuleContent shape and validates the matrix-owned family boundary.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from rota.application.context import require_active_coordinator_context
from rota.application.errors import require_real_date
from rota.domain import RuleCategory, RuleEnforcement, RuleResolution, ShiftKind
from rota.persistence import site_memory
from rota.persistence.decision_ledger import record_decision_no_commit
from rota.persistence.employee_repository import get_employee
from rota.persistence.site_memory import rule_history
from rota.persistence.site_rule_repository import get_site_rule_version
from rota.planning.site_rules import EMPLOYEE_DAY_ONLY_N_EXCEPTION, EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind, DecisionRecord, NewRuleContent


def _rule_content_state(rule_content: Optional[NewRuleContent]) -> Optional[dict]:
    if rule_content is None:
        return None
    return {
        "category": rule_content.category.value, "rule_kind": rule_content.rule_kind,
        "structured_parameters": rule_content.structured_parameters,
        "enforcement": rule_content.enforcement.value, "resolution_status": rule_content.resolution_status.value,
        "effective_to": rule_content.effective_to, "description": rule_content.description,
        "source": rule_content.source, "reason": rule_content.reason,
    }


def _add_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _months_intersecting_interval(months: list[date], effective_from: date, effective_to: Optional[date]) -> list[date]:
    return [
        month for month in months
        if (_add_month(month) - timedelta(days=1)) >= effective_from and (effective_to is None or month <= effective_to)
    ]


def record_structured_rule_decision(
    conn, *, coordinator_id: str, site_id: str, rule_id: str, statement: str, effective_from: date,
    rel: Optional[str] = None, rule_content: Optional[NewRuleContent] = None,
    recorded_at: Optional[datetime] = None, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    require_real_date(effective_from)
    stamp = recorded_at or datetime.now()
    with conn:
        site_memory.validate_decision_required_link_no_commit(
            conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
        )
        predecessor_chain = rule_history(conn, site_id, rule_id)
        predecessor = predecessor_chain[-1] if predecessor_chain else None
        decision = record_decision_no_commit(
            conn, site_id=site_id, rule_id=rule_id, statement=statement, coordinator_id=coordinator_id,
            recorded_at=stamp, effective_from=effective_from, rel=rel, rule_content=rule_content,
        )
        site_memory.record_coordinator_action_no_commit(
            conn, action_kind=CoordinatorActionKind.RULE_DECISION_RECORDED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=stamp,
            effective_from=effective_from, month=None, schedule_version_id=None,
            affected_entities=[AffectedEntity("SITE_RULE", rule_id)],
            before_state={
                "predecessor_decision_id": None if predecessor is None else predecessor.decision_id,
                "predecessor_rule_version_id": None if predecessor is None else predecessor.rule_version_id,
            },
            after_state={
                "decision_id": decision.decision_id, "rule_version_id": decision.rule_version_id,
                "rel": decision.rel, "content": _rule_content_state(rule_content),
            },
            note=note, source_kind=ActionSourceKind.DECISION_RECORD, source_id=decision.decision_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        effective_to = rule_content.effective_to if rule_content is not None else None
        stored_months = site_memory.current_decision_required_months_for_site(conn, site_id=site_id)
        stale_months = _months_intersecting_interval(stored_months, effective_from, effective_to)
        site_memory.invalidate_current_decision_required_no_commit(conn, site_ids=[site_id], months=stale_months)
    return decision


# --- ROTA-T021b: employee matrix wrappers (tasks/ROTA-T021b/brief.md) ---

_WEEKDAY_NAMES_PL = {
    1: "poniedziałek", 2: "wtorek", 3: "środa", 4: "czwartek",
    5: "piątek", 6: "sobota", 7: "niedziela",
}
_ALL_WEEKDAYS = list(range(1, 8))


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _new_matrix_rule_id() -> str:
    return f"R-EMP-MATRIX-{uuid.uuid4().hex}"


def _require_employee_exists(conn, employee_id: str) -> None:
    get_employee(conn, employee_id)  # raises EmployeeNotFound; no write has happened yet


def _shift_kind_statement(shift_kind: ShiftKind, effective_from: date, effective_to: date) -> str:
    label = "Dniówka" if shift_kind == ShiftKind.D else "Nocka"
    return f"{label}: niedostępna od {_fmt(effective_from)} do {_fmt(effective_to)}"


def _weekday_statement(iso_weekday: int, effective_from: date, effective_to: date) -> str:
    name = _WEEKDAY_NAMES_PL[iso_weekday]
    return f"Brak dostępności w {name}: od {_fmt(effective_from)} do {_fmt(effective_to)}"


def _day_only_exception_statement(effective_from: date, effective_to: date) -> str:
    return f"Nocka: czasowo dozwolona od {_fmt(effective_from)} do {_fmt(effective_to)}"


def _describe_matrix_family_for_reject(rule_kind: str, structured_parameters: dict) -> str:
    """Statement for end_employee_matrix_rule_early() -- derives the
    human label from the family's own saved content, since the caller
    only supplies rule_id."""
    if rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION:
        return "Nocka"
    weekdays = structured_parameters["weekdays"]
    forbidden = structured_parameters["forbidden_shift_kinds"]
    if weekdays == _ALL_WEEKDAYS and forbidden == ["D"]:
        return "Dniówka"
    if weekdays == _ALL_WEEKDAYS and forbidden == ["N"]:
        return "Nocka"
    return _WEEKDAY_NAMES_PL[weekdays[0]].capitalize()


_MATRIX_OWNED_SHAPES = {
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS: (RuleCategory.LOCAL_RULE, RuleEnforcement.HARD, RuleResolution.RESOLVED),
    EMPLOYEE_DAY_ONLY_N_EXCEPTION: (RuleCategory.CONFIRMED_EXCEPTION, RuleEnforcement.HARD, RuleResolution.RESOLVED),
}


def _resolve_matrix_owned_rule(conn, site_id: str, rule_id: str):
    """Shared validation for update_employee_matrix_rule_period() and
    end_employee_matrix_rule_early() (brief.md section 3.4/3.5): the
    family must exist for this Site, its current chain end must carry an
    active rule version, that version's (rule_kind, category,
    enforcement, resolution_status) must match one of the two
    matrix-owned shapes, and its retained employee_id must still exist.
    Returns the current SiteRuleVersion. Raises ValueError (mapped to
    HTTP 400) on any rejection, before any write."""
    history = rule_history(conn, site_id, rule_id)
    if not history:
        raise ValueError(f"no rule family {rule_id!r} at site {site_id!r}")
    current = history[-1]
    if current.rule_version_id is None:
        raise ValueError(f"rule family {rule_id!r} has already ended (no active rule version)")
    version = get_site_rule_version(conn, current.rule_version_id)
    if version.site_id != site_id:
        raise ValueError(f"rule family {rule_id!r} does not belong to site {site_id!r}")
    expected = _MATRIX_OWNED_SHAPES.get(version.rule_kind)
    if expected is None or (version.category, version.enforcement, version.resolution_status) != expected:
        raise ValueError(f"rule family {rule_id!r} is not a matrix-owned employee restriction")
    employee_id = version.structured_parameters["employee_id"]
    _require_employee_exists(conn, employee_id)
    return version


def create_employee_shift_unavailability(
    conn, *, coordinator_id: str, site_id: str, employee_id: str, shift_kind: ShiftKind,
    effective_from: date, effective_to: date, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    if effective_from > effective_to:
        raise ValueError("effective_from must not be after effective_to")
    _require_employee_exists(conn, employee_id)
    rule_id = _new_matrix_rule_id()
    return record_structured_rule_decision(
        conn, coordinator_id=coordinator_id, site_id=site_id, rule_id=rule_id,
        statement=_shift_kind_statement(shift_kind, effective_from, effective_to),
        effective_from=effective_from, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE, rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
            structured_parameters={
                "employee_id": employee_id, "weekdays": _ALL_WEEKDAYS, "forbidden_shift_kinds": [shift_kind.value],
            },
            enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
            effective_to=effective_to, description=None, source=None, reason=None,
        ),
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )


def create_employee_weekday_unavailability(
    conn, *, coordinator_id: str, site_id: str, employee_id: str, iso_weekday: int,
    effective_from: date, effective_to: date, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    if isinstance(iso_weekday, bool) or not isinstance(iso_weekday, int) or not (1 <= iso_weekday <= 7):
        raise ValueError(f"iso_weekday must be an int 1..7, got {iso_weekday!r}")
    if effective_from > effective_to:
        raise ValueError("effective_from must not be after effective_to")
    _require_employee_exists(conn, employee_id)
    rule_id = _new_matrix_rule_id()
    return record_structured_rule_decision(
        conn, coordinator_id=coordinator_id, site_id=site_id, rule_id=rule_id,
        statement=_weekday_statement(iso_weekday, effective_from, effective_to),
        effective_from=effective_from, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE, rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
            structured_parameters={
                "employee_id": employee_id, "weekdays": [iso_weekday], "forbidden_shift_kinds": ["D", "N"],
            },
            enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
            effective_to=effective_to, description=None, source=None, reason=None,
        ),
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )


def create_day_only_n_exception(
    conn, *, coordinator_id: str, site_id: str, employee_id: str,
    effective_from: date, effective_to: date, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    if effective_from > effective_to:
        raise ValueError("effective_from must not be after effective_to")
    employee = get_employee(conn, employee_id)  # no write yet
    if not employee.day_only:
        raise ValueError(f"employee {employee_id!r} is not day_only -- the N exception does not apply")
    rule_id = _new_matrix_rule_id()
    return record_structured_rule_decision(
        conn, coordinator_id=coordinator_id, site_id=site_id, rule_id=rule_id,
        statement=_day_only_exception_statement(effective_from, effective_to),
        effective_from=effective_from, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.CONFIRMED_EXCEPTION, rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION,
            structured_parameters={"employee_id": employee_id},
            enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
            effective_to=effective_to, description=None, source=None, reason=None,
        ),
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )


def update_employee_matrix_rule_period(
    conn, *, coordinator_id: str, site_id: str, rule_id: str,
    effective_from: date, effective_to: date, note: Optional[str] = None,
    responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    if effective_from > effective_to:
        raise ValueError("effective_from must not be after effective_to")
    version = _resolve_matrix_owned_rule(conn, site_id, rule_id)
    if version.rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION:
        statement = _day_only_exception_statement(effective_from, effective_to)
    else:
        params = version.structured_parameters
        if params["weekdays"] == _ALL_WEEKDAYS and params["forbidden_shift_kinds"] == ["D"]:
            statement = _shift_kind_statement(ShiftKind.D, effective_from, effective_to)
        elif params["weekdays"] == _ALL_WEEKDAYS and params["forbidden_shift_kinds"] == ["N"]:
            statement = _shift_kind_statement(ShiftKind.N, effective_from, effective_to)
        else:
            statement = _weekday_statement(params["weekdays"][0], effective_from, effective_to)
    return record_structured_rule_decision(
        conn, coordinator_id=coordinator_id, site_id=site_id, rule_id=rule_id, statement=statement,
        effective_from=effective_from, rel="supersedes",
        rule_content=NewRuleContent(
            category=version.category, rule_kind=version.rule_kind, structured_parameters=version.structured_parameters,
            enforcement=version.enforcement, resolution_status=version.resolution_status,
            effective_to=effective_to, description=version.description, source=version.source, reason=version.reason,
        ),
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )


def end_employee_matrix_rule_early(
    conn, *, coordinator_id: str, site_id: str, rule_id: str, effective_from: date,
    note: Optional[str] = None, responds_to_decision_required_id: Optional[str] = None,
) -> DecisionRecord:
    version = _resolve_matrix_owned_rule(conn, site_id, rule_id)
    if version.effective_to is None:
        if effective_from < version.effective_from:
            raise ValueError("effective_from is before the rule's own effective_from")
    else:
        if effective_from < version.effective_from or effective_from > version.effective_to:
            raise ValueError("effective_from is outside the rule's own effective period")
    label = _describe_matrix_family_for_reject(version.rule_kind, version.structured_parameters)
    return record_structured_rule_decision(
        conn, coordinator_id=coordinator_id, site_id=site_id, rule_id=rule_id,
        statement=f"Przywrócono bazowy stan {label} od {_fmt(effective_from)}",
        effective_from=effective_from, rel="rejects", rule_content=None,
        note=note, responds_to_decision_required_id=responds_to_decision_required_id,
    )
