"""Read-only wrap of rota.application.memory_read -- ROTA-T021 §Historia i
audyt (arch/T021_spec.md). Two independent streams already exist there
(material action history + rule decision history); this router only
marshals their dataclasses to JSON, no new logic."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.memory_read import material_action_detail, material_action_history, rules_history_for_site
from rota.site_memory_types import ActionSourceKind, CoordinatorActionKind

router = APIRouter(prefix="/workspace", tags=["history"])


class AffectedEntityOut(BaseModel):
    entity_kind: str
    entity_id: str


class MaterialActionSummaryOut(BaseModel):
    action_id: str
    action_kind: CoordinatorActionKind
    origin_site_id: str
    affected_site_ids: list[str]
    coordinator_id: str
    recorded_at: str
    effective_from: str | None
    month: str | None
    schedule_version_id: str | None
    affected_entities: list[AffectedEntityOut]
    note: str | None
    responds_to_decision_required_id: str | None


class DecisionRequiredReadbackOut(BaseModel):
    decision_required_id: str
    site_id: str
    month: str
    schedule_version_id: str | None
    requested_by: str
    recorded_at: str
    linked_action_ids: list[str]


class MaterialActionDetailOut(MaterialActionSummaryOut):
    before_state: Optional[dict]
    after_state: Optional[dict]
    source_kind: ActionSourceKind
    source_id: str | None
    responds_to: Optional[DecisionRequiredReadbackOut]


class DecisionRecordOut(BaseModel):
    decision_id: str
    site_id: str
    rule_id: str
    chain_seq: int
    statement: str
    coordinator_id: str
    recorded_at: str
    effective_from: str
    rule_version_id: str | None
    rel: Optional[Literal["supersedes", "corrects", "rejects"]]
    predecessor_decision_id: str | None


def _summary_out(s) -> MaterialActionSummaryOut:
    return MaterialActionSummaryOut(
        action_id=s.action_id, action_kind=s.action_kind, origin_site_id=s.origin_site_id,
        affected_site_ids=list(s.affected_site_ids), coordinator_id=s.coordinator_id,
        recorded_at=s.recorded_at.isoformat(), effective_from=s.effective_from.isoformat() if s.effective_from else None,
        month=s.month.isoformat() if s.month else None, schedule_version_id=s.schedule_version_id,
        affected_entities=[AffectedEntityOut(entity_kind=e.entity_kind, entity_id=e.entity_id) for e in s.affected_entities],
        note=s.note, responds_to_decision_required_id=s.responds_to_decision_required_id,
    )


@router.get("/sites/{site_id}/history/actions", response_model=list[MaterialActionSummaryOut])
def get_action_history(
    site_id: str, action_kind: Optional[CoordinatorActionKind] = None, coordinator_id: Optional[str] = None,
    recorded_from: Optional[str] = None, recorded_to: Optional[str] = None, conn=Depends(get_conn),
) -> list[MaterialActionSummaryOut]:
    try:
        records = material_action_history(
            conn, site_id=site_id, action_kind=action_kind, coordinator_id=coordinator_id,
            recorded_from=datetime.fromisoformat(recorded_from) if recorded_from else None,
            recorded_to=datetime.fromisoformat(recorded_to) if recorded_to else None,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return [_summary_out(r) for r in records]


@router.get("/history/actions/{action_id}", response_model=MaterialActionDetailOut)
def get_action_detail(action_id: str, conn=Depends(get_conn)) -> MaterialActionDetailOut:
    try:
        detail = material_action_detail(conn, action_id=action_id)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    responds_to = None
    if detail.responds_to is not None:
        responds_to = DecisionRequiredReadbackOut(
            decision_required_id=detail.responds_to.decision_required_id, site_id=detail.responds_to.site_id,
            month=detail.responds_to.month.isoformat(), schedule_version_id=detail.responds_to.schedule_version_id,
            requested_by=detail.responds_to.requested_by, recorded_at=detail.responds_to.recorded_at.isoformat(),
            linked_action_ids=list(detail.responds_to.linked_action_ids),
        )
    base = _summary_out(detail)
    return MaterialActionDetailOut(
        **base.model_dump(), before_state=detail.before_state, after_state=detail.after_state,
        source_kind=detail.source_kind, source_id=detail.source_id, responds_to=responds_to,
    )


@router.get("/sites/{site_id}/history/rules", response_model=dict[str, list[DecisionRecordOut]])
def get_rule_history(site_id: str, conn=Depends(get_conn)) -> dict[str, list[DecisionRecordOut]]:
    try:
        history = rules_history_for_site(conn, site_id=site_id)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return {
        rule_id: [
            DecisionRecordOut(
                decision_id=d.decision_id, site_id=d.site_id, rule_id=d.rule_id, chain_seq=d.chain_seq,
                statement=d.statement, coordinator_id=d.coordinator_id, recorded_at=d.recorded_at.isoformat(),
                effective_from=d.effective_from.isoformat(), rule_version_id=d.rule_version_id, rel=d.rel,
                predecessor_decision_id=d.predecessor_decision_id,
            )
            for d in chain
        ]
        for rule_id, chain in history.items()
    }


if __name__ == "__main__":
    print("api.routers.history module OK")
