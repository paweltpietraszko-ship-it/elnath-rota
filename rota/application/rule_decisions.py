"""Operation 7 (tasks/ROTA-T009/brief.md): structured SiteRule decision seam
for a future T010 caller. Every value is already resolved by the caller --
this function infers nothing from text and contains no parser/LLM/DSL.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from rota.application.context import require_active_coordinator_context
from rota.application.errors import require_real_date
from rota.persistence import site_memory
from rota.persistence.decision_ledger import record_decision_no_commit
from rota.persistence.site_memory import rule_history
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
