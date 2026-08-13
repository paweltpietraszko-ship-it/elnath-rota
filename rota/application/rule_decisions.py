"""Operation 7 (tasks/ROTA-T009/brief.md): structured SiteRule decision seam
for a future T010 caller. Every value is already resolved by the caller --
this function infers nothing from text and contains no parser/LLM/DSL.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from rota.application.context import require_active_coordinator_context
from rota.persistence.decision_ledger import record_decision
from rota.site_memory_types import DecisionRecord, NewRuleContent


def record_structured_rule_decision(
    conn, *, coordinator_id: str, site_id: str, rule_id: str, statement: str, effective_from: date,
    rel: Optional[str] = None, rule_content: Optional[NewRuleContent] = None,
    recorded_at: Optional[datetime] = None,
) -> DecisionRecord:
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    return record_decision(
        conn, site_id=site_id, rule_id=rule_id, statement=statement, coordinator_id=coordinator_id,
        recorded_at=recorded_at or datetime.now(), effective_from=effective_from, rel=rel, rule_content=rule_content,
    )
