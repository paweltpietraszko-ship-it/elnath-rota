"""Types for ROTA-T005 SiteMemory (Rule Store + Decision Ledger).

Decision Record is a new concept introduced by T005, not part of the frozen
rota/domain.py -- kept separate the same way rota/planning/engine_types.py
is separate from domain.py, rather than adding it to the frozen module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional, Union

from rota.domain import RuleCategory, RuleEnforcement, RuleResolution, SiteRuleVersion
from rota.planning.engine_types import DecisionRequiredPayload

DECISION_RELATIONS = ("supersedes", "corrects", "rejects")


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    site_id: str
    rule_id: str
    chain_seq: int
    statement: str
    coordinator_id: str
    recorded_at: datetime
    effective_from: date
    rule_version_id: Optional[str]
    rel: Optional[str]
    predecessor_decision_id: Optional[str]


@dataclass(frozen=True)
class NewRuleContent:
    """Structural content for the SiteRuleVersion a decision creates.

    site_id/rule_id/changed_by/changed_at/effective_from are NOT here --
    they are taken from the enclosing decision (brief.md DECISION LEDGER
    consistency invariant), never supplied twice.
    """

    category: RuleCategory
    rule_kind: Optional[str]
    structured_parameters: Optional[object]
    enforcement: RuleEnforcement
    resolution_status: RuleResolution
    effective_to: Optional[date]
    description: Optional[str]
    source: Optional[str]
    reason: Optional[str]


@dataclass(frozen=True)
class NoActiveRule:
    site_id: str
    rule_id: str
    as_of: date


@dataclass(frozen=True)
class EffectiveRule:
    rule_version: SiteRuleVersion
    decision: DecisionRecord


EffectiveSelection = Union[EffectiveRule, NoActiveRule]


class CoordinatorActionKind(str, Enum):
    """ROTA-T019b: stable minimum action kinds (tasks/ROTA-T019b/brief.md
    section 6). No PLAN_ATTEMPT/SOLVER_RETRY/FALLBACK_STAGE/REVALIDATE
    kind -- those are never material coordinator actions."""

    CONTEXT_CONFIGURATION_SAVED = "CONTEXT_CONFIGURATION_SAVED"
    EXTERNAL_SUPPORT_WINDOW_CHANGED = "EXTERNAL_SUPPORT_WINDOW_CHANGED"
    AVAILABILITY_CHANGED = "AVAILABILITY_CHANGED"
    EMPLOYEE_DAY_ONLY_CHANGED = "EMPLOYEE_DAY_ONLY_CHANGED"
    SITE_MEMBERSHIP_CHANGED = "SITE_MEMBERSHIP_CHANGED"
    TARGET_HOURS_CHANGED = "TARGET_HOURS_CHANGED"
    CALENDAR_DAY_CHANGED = "CALENDAR_DAY_CHANGED"
    SITE_PROFILE_CHANGED = "SITE_PROFILE_CHANGED"
    SITE_ACTIVE_CHANGED = "SITE_ACTIVE_CHANGED"
    RULE_DECISION_RECORDED = "RULE_DECISION_RECORDED"
    SCHEDULE_CANDIDATE_SELECTED = "SCHEDULE_CANDIDATE_SELECTED"
    SCHEDULE_REPLAN_CREATED = "SCHEDULE_REPLAN_CREATED"
    MANUAL_SCHEDULE_CORRECTION = "MANUAL_SCHEDULE_CORRECTION"
    ASSIGNMENT_FREEZE_CHANGED = "ASSIGNMENT_FREEZE_CHANGED"
    ASSIGNMENT_NOT_WORKED = "ASSIGNMENT_NOT_WORKED"
    TRAINING_REALIZED = "TRAINING_REALIZED"
    SCHEDULE_FINALIZED = "SCHEDULE_FINALIZED"
    SCHEDULE_RESTORED = "SCHEDULE_RESTORED"


class ActionSourceKind(str, Enum):
    CURRENT_STATE = "CURRENT_STATE"
    AVAILABILITY_VERSION = "AVAILABILITY_VERSION"
    DECISION_RECORD = "DECISION_RECORD"
    SCHEDULE_VERSION = "SCHEDULE_VERSION"
    CURRENT_SCHEDULE_POINTER = "CURRENT_SCHEDULE_POINTER"


@dataclass(frozen=True)
class AffectedEntity:
    entity_kind: str
    entity_id: str


@dataclass(frozen=True)
class CoordinatorActionRecord:
    """ROTA-T019b append-only coordinator-action index row (brief.md
    section 5.1). before_state/after_state are structured, deterministically
    serialized snapshots of the facts this one action changed -- never a
    copy of the whole database, never used to reconstruct PlanningState."""

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
    before_state: Optional[dict]
    after_state: Optional[dict]
    note: Optional[str]
    source_kind: ActionSourceKind
    source_id: Optional[str]
    responds_to_decision_required_id: Optional[str]


@dataclass(frozen=True)
class DecisionRequiredSnapshotRecord:
    """ROTA-T019b immutable final DECISION_REQUIRED snapshot (brief.md
    section 5.2) -- exactly the already-rendered T013 DecisionRequiredPayload,
    never re-rendered against today's names/rules on readback."""

    decision_required_id: str
    site_id: str
    month: date
    schedule_version_id: Optional[str]
    requested_by: str
    recorded_at: datetime
    payload: DecisionRequiredPayload


if __name__ == "__main__":
    print("site_memory_types module OK")
