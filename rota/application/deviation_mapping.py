"""Operation 8 (tasks/ROTA-T009/brief.md): one small explicit mapping from a
validator ViolationDetail's source to DeviationCategory, and materialization
of the current persistent Deviation set from a fresh validation report. Not
a classifier/rule engine -- a static lookup table; unknown sources fail
closed instead of being guessed.
"""
from __future__ import annotations

from rota.application.errors import UnknownDeviationSource
from rota.domain import Deviation, DeviationCategory, RuleCategory, SiteRuleVersion
from rota.planning.validator import ViolationDetail

_BUILTIN_RULE_CATEGORY: dict[str, DeviationCategory] = {
    "COVERAGE-01": DeviationCategory.COVERAGE,
    "DAY_SHIFT_OFF-01": DeviationCategory.LEAVE_OR_TIME_OFF,
    "LEAVE_GRANTED-01": DeviationCategory.LEAVE_OR_TIME_OFF,
    "UNAVAILABLE-01": DeviationCategory.LEAVE_OR_TIME_OFF,
    "SICK_LEAVE-01": DeviationCategory.LEAVE_OR_TIME_OFF,
    "LOAD-01": DeviationCategory.HOURS,
    "REST-01": DeviationCategory.LAW,
    "DAY_ONLY-01": DeviationCategory.PREFERENCE,
    "MEMBERSHIP-01": DeviationCategory.PREFERENCE,
    "EXTERNAL-01": DeviationCategory.PREFERENCE,
    # ROTA-T012 Part B (part_b_work_period_rest.md DEVIATION MAPPING):
    # frozen categories, activated in B alongside the built-in HARD codes.
    "SHIFT-24-01": DeviationCategory.PREFERENCE,
    "SHIFT-24-PAIR-01": DeviationCategory.COVERAGE,
}

_SITE_RULE_CATEGORY: dict[RuleCategory, DeviationCategory] = {
    RuleCategory.CLIENT_REQUIREMENT: DeviationCategory.CLIENT_REQUIREMENT,
    RuleCategory.LOCAL_RULE: DeviationCategory.PREFERENCE,
    RuleCategory.CONFIRMED_EXCEPTION: DeviationCategory.PREFERENCE,
}


def category_for_rule(rule_code: str, site_rules_by_version_id: dict[str, SiteRuleVersion]) -> DeviationCategory:
    """rule_code is either a built-in validator rule code, or (for a
    SiteRule-caused violation) the exact rule_version_id -- engine.py never
    reuses a built-in code for a SiteRule, so membership alone disambiguates."""
    if rule_code in _BUILTIN_RULE_CATEGORY:
        return _BUILTIN_RULE_CATEGORY[rule_code]
    if rule_code in site_rules_by_version_id:
        return _SITE_RULE_CATEGORY[site_rules_by_version_id[rule_code].category]
    raise UnknownDeviationSource(f"no DeviationCategory mapping for rule {rule_code!r}")


def _affected_target(detail: ViolationDetail) -> str:
    if detail.demand_ids:
        return detail.demand_ids[0]
    if detail.assignment_ids:
        return detail.assignment_ids[0]
    raise UnknownDeviationSource(f"rule {detail.rule!r} names neither an Assignment nor a ShiftDemand")


def materialize_deviations(
    violation_details: list[ViolationDetail], site_rules: tuple[SiteRuleVersion, ...],
) -> list[Deviation]:
    """Builds the complete current Deviation set from a fresh
    IndependentValidationReport.violation_details -- callers persist this as
    a full replacement (create/replace_working_snapshot), never a merge, so
    stale Deviations are dropped automatically by omission."""
    by_version_id = {r.rule_version_id: r for r in site_rules}
    deviations = []
    for index, detail in enumerate(violation_details):
        category = category_for_rule(detail.rule, by_version_id)
        deviations.append(Deviation(
            deviation_id=f"DEV-{index}-{detail.rule}"[:64], schedule_version_id="", category=category,
            source_reference=detail.rule, affected_assignment_or_employee=_affected_target(detail),
            acknowledged=False, acknowledged_by=None, acknowledged_at=None, reason=None,
        ))
    return deviations
