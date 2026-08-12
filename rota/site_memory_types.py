"""Types for ROTA-T005 SiteMemory (Rule Store + Decision Ledger).

Decision Record is a new concept introduced by T005, not part of the frozen
rota/domain.py -- kept separate the same way rota/planning/engine_types.py
is separate from domain.py, rather than adding it to the frozen module.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Union

from rota.domain import RuleCategory, RuleEnforcement, RuleResolution, SiteRuleVersion

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


if __name__ == "__main__":
    print("site_memory_types module OK")
