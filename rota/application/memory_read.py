"""Operation 11 (tasks/ROTA-T009/brief.md): simple application reads over
the SiteMemory already stored by T005 -- not a new audit subsystem.

ROTA-T019b: extended with structured reads over the coordinator-action index
and final DECISION_REQUIRED readback added by T019b (brief.md section 17).
No SQL here -- everything delegates to rota.persistence.site_memory.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from rota.persistence import site_memory
from rota.persistence.site_memory import decision_for_rule_version, rule_history, rule_provenance
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.persistence.site_rule_repository import list_rule_ids_for_site
from rota.planning.engine_types import DecisionRequiredPayload
from rota.site_memory_types import AffectedEntity, CoordinatorActionKind


def effective_rules_for_month(conn, *, site_id: str, month: date):
    """Returns (resolved, unresolved, applicability) exactly as
    assembled for a PlanningState -- the same source of truth."""
    return assemble_monthly_site_rules(conn, site_id, month)


def rules_history_for_site(conn, *, site_id: str):
    return {rule_id: rule_history(conn, site_id, rule_id) for rule_id in list_rule_ids_for_site(conn, site_id)}


def decision_chain_for_rule_family(conn, *, site_id: str, rule_id: str):
    return rule_history(conn, site_id, rule_id)


def provenance_for_rule_version(conn, *, rule_version_id: str):
    return rule_provenance(conn, rule_version_id)


def decision_for_rule(conn, *, rule_version_id: str):
    return decision_for_rule_version(conn, rule_version_id)


@dataclass(frozen=True)
class MaterialActionSummary:
    """ROTA-T019b brief.md section 17.1. No Polish presentation strings --
    T021 owns human-language labels; this is structured data only."""

    action_id: str
    action_kind: CoordinatorActionKind
    origin_site_id: str
    affected_site_ids: tuple[str, ...]
    coordinator_id: str
    recorded_at: datetime
    effective_from: Optional[date]
    month: Optional[date]
    schedule_version_id: Optional[str]
    affected_entities: tuple[AffectedEntity, ...]
    note: Optional[str]
    responds_to_decision_required_id: Optional[str]


@dataclass(frozen=True)
class MaterialActionDetail:
    action_id: str
    action_kind: CoordinatorActionKind
    origin_site_id: str
    affected_site_ids: tuple[str, ...]
    coordinator_id: str
    recorded_at: datetime
    effective_from: Optional[date]
    month: Optional[date]
    schedule_version_id: Optional[str]
    affected_entities: tuple[AffectedEntity, ...]
    note: Optional[str]
    responds_to_decision_required_id: Optional[str]
    before_state: Optional[dict]
    after_state: Optional[dict]
    source_kind: str
    source_id: Optional[str]
    responds_to: Optional["DecisionRequiredReadback"]


@dataclass(frozen=True)
class DecisionRequiredReadback:
    decision_required_id: str
    site_id: str
    month: date
    schedule_version_id: Optional[str]
    requested_by: str
    recorded_at: datetime
    payload: DecisionRequiredPayload
    linked_action_ids: tuple[str, ...]


def _to_summary(record) -> MaterialActionSummary:
    return MaterialActionSummary(
        action_id=record.action_id, action_kind=record.action_kind, origin_site_id=record.origin_site_id,
        affected_site_ids=record.affected_site_ids, coordinator_id=record.coordinator_id,
        recorded_at=record.recorded_at, effective_from=record.effective_from, month=record.month,
        schedule_version_id=record.schedule_version_id, affected_entities=record.affected_entities,
        note=record.note, responds_to_decision_required_id=record.responds_to_decision_required_id,
    )


def material_action_history(
    conn, *, site_id: Optional[str] = None, affected_entity_kind: Optional[str] = None,
    affected_entity_id: Optional[str] = None, action_kind: Optional[CoordinatorActionKind] = None,
    coordinator_id: Optional[str] = None, recorded_from: Optional[datetime] = None,
    recorded_to: Optional[datetime] = None,
) -> tuple[MaterialActionSummary, ...]:
    records = site_memory.list_coordinator_actions(
        conn, site_id=site_id, affected_entity_kind=affected_entity_kind, affected_entity_id=affected_entity_id,
        action_kind=action_kind, coordinator_id=coordinator_id, recorded_from=recorded_from, recorded_to=recorded_to,
    )
    return tuple(_to_summary(r) for r in records)


def material_action_detail(conn, *, action_id: str) -> MaterialActionDetail:
    record = site_memory.get_coordinator_action(conn, action_id)
    responds_to = None
    if record.responds_to_decision_required_id is not None:
        snapshot = site_memory.get_decision_required_snapshot(conn, record.responds_to_decision_required_id)
        if snapshot is not None:
            linked = site_memory.list_action_ids_linking_to(conn, snapshot.decision_required_id)
            responds_to = DecisionRequiredReadback(
                decision_required_id=snapshot.decision_required_id, site_id=snapshot.site_id,
                month=snapshot.month, schedule_version_id=snapshot.schedule_version_id,
                requested_by=snapshot.requested_by, recorded_at=snapshot.recorded_at, payload=snapshot.payload,
                linked_action_ids=linked,
            )
    return MaterialActionDetail(
        action_id=record.action_id, action_kind=record.action_kind, origin_site_id=record.origin_site_id,
        affected_site_ids=record.affected_site_ids, coordinator_id=record.coordinator_id,
        recorded_at=record.recorded_at, effective_from=record.effective_from, month=record.month,
        schedule_version_id=record.schedule_version_id, affected_entities=record.affected_entities,
        note=record.note, responds_to_decision_required_id=record.responds_to_decision_required_id,
        before_state=record.before_state, after_state=record.after_state,
        source_kind=record.source_kind.value, source_id=record.source_id, responds_to=responds_to,
    )


def current_decision_required(conn, *, site_id: str, month: date) -> Optional[DecisionRequiredReadback]:
    if month.day != 1:
        raise ValueError(f"month {month} is not the first day of its month")
    snapshot = site_memory.get_current_decision_required(conn, site_id=site_id, month=month)
    if snapshot is None:
        return None
    linked = site_memory.list_action_ids_linking_to(conn, snapshot.decision_required_id)
    return DecisionRequiredReadback(
        decision_required_id=snapshot.decision_required_id, site_id=snapshot.site_id, month=snapshot.month,
        schedule_version_id=snapshot.schedule_version_id, requested_by=snapshot.requested_by,
        recorded_at=snapshot.recorded_at, payload=snapshot.payload, linked_action_ids=linked,
    )
