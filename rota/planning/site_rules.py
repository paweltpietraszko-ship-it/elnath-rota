"""Executable SiteRule catalog (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md,
tasks/ROTA-T007/brief.md). Pure parsing/validation/evaluation -- no I/O, no
persistence, no CP-SAT.

Only RESOLVED + HARD SiteRuleVersions are ever validated/executed here.
RESOLVED + SOFT is unconditionally unsupported by T007 (no ranking
semantics exist yet). RESOLVED + INFORMATIONAL and NEEDS_RESOLUTION are
never validated or executed (R1 clarification,
arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01_R1_CLARIFICATION.md).
"""
from __future__ import annotations

from datetime import date

from rota.domain import RuleCategory, RuleEnforcement, ShiftKind, SiteRuleVersion

EMPLOYEE_ALLOWED_SHIFT_KINDS = "EMPLOYEE_ALLOWED_SHIFT_KINDS"
EMPLOYEE_ALLOWED_WEEKDAYS = "EMPLOYEE_ALLOWED_WEEKDAYS"
EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS = "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS"
# ROTA-T010-B (arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md): a
# single named, narrow exception to DAY_ONLY-01 -- deliberately NOT part of
# the generic AND-gate below (rule_allows_assignment always returns True for
# it there); its only effect is via day_only_n_exception_applies, called
# only from the DAY_ONLY-01 check sites (eligibility._common_hard_gate,
# validator._check_day_only).
EMPLOYEE_DAY_ONLY_N_EXCEPTION = "EMPLOYEE_DAY_ONLY_N_EXCEPTION"

SUPPORTED_RULE_KINDS = frozenset({
    EMPLOYEE_ALLOWED_SHIFT_KINDS,
    EMPLOYEE_ALLOWED_WEEKDAYS,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
})

_VALID_SHIFT_KIND_VALUES = frozenset({"D", "N"})
_VALID_WEEKDAYS = frozenset(range(1, 8))


class UnsupportedOrMalformedSiteRule(Exception):
    """A RESOLVED rule claims to be executable but isn't -- unknown
    rule_kind, malformed parameters (HARD), or an unsupported enforcement
    (SOFT). Carries rule_version_id so callers can report it as provenance,
    never a generic condition code."""

    def __init__(self, rule_version_id: str, reason: str) -> None:
        self.rule_version_id = rule_version_id
        super().__init__(f"{rule_version_id}: {reason}")


def _require_keys(rule_version_id: str, params: object, required: set) -> dict:
    if not isinstance(params, dict):
        raise UnsupportedOrMalformedSiteRule(rule_version_id, "structured_parameters must be an object")
    if set(params.keys()) != required:
        raise UnsupportedOrMalformedSiteRule(
            rule_version_id, f"expected exactly keys {sorted(required)}, got {sorted(params.keys())}"
        )
    return params


def _require_nonempty_str(rule_version_id: str, params: dict, key: str) -> None:
    value = params[key]
    if not isinstance(value, str) or not value:
        raise UnsupportedOrMalformedSiteRule(rule_version_id, f"{key} must be a non-empty string")


def _require_shift_kind_list(rule_version_id: str, params: dict, key: str) -> None:
    # Audit round 3 FINDING R3-1: `v in _VALID_SHIFT_KIND_VALUES` alone raises
    # a raw TypeError for an unhashable v (a list or dict) -- valid JSON that
    # T005 legitimately transports but T007 must reject as a malformed
    # execution shape, not crash on. isinstance(v, str) must run first so
    # `in` is never reached for a non-string element.
    value = params[key]
    valid = isinstance(value, list) and bool(value) and all(
        isinstance(v, str) and v in _VALID_SHIFT_KIND_VALUES for v in value
    )
    if not valid:
        raise UnsupportedOrMalformedSiteRule(rule_version_id, f"{key} must be a non-empty list of 'D'/'N'")


def _require_weekday_list(rule_version_id: str, params: dict, key: str) -> None:
    value = params[key]
    valid = isinstance(value, list) and bool(value) and all(
        isinstance(v, int) and not isinstance(v, bool) and v in _VALID_WEEKDAYS for v in value
    )
    if not valid:
        raise UnsupportedOrMalformedSiteRule(rule_version_id, f"{key} must be a non-empty list of ISO weekdays 1..7")


def _validate_allowed_shift_kinds(rule_version_id: str, params: object) -> None:
    checked = _require_keys(rule_version_id, params, {"employee_id", "allowed_shift_kinds"})
    _require_nonempty_str(rule_version_id, checked, "employee_id")
    _require_shift_kind_list(rule_version_id, checked, "allowed_shift_kinds")


def _validate_allowed_weekdays(rule_version_id: str, params: object) -> None:
    checked = _require_keys(rule_version_id, params, {"employee_id", "allowed_weekdays"})
    _require_nonempty_str(rule_version_id, checked, "employee_id")
    _require_weekday_list(rule_version_id, checked, "allowed_weekdays")


def _validate_forbidden_shift_kinds_on_weekdays(rule_version_id: str, params: object) -> None:
    checked = _require_keys(rule_version_id, params, {"employee_id", "weekdays", "forbidden_shift_kinds"})
    _require_nonempty_str(rule_version_id, checked, "employee_id")
    _require_weekday_list(rule_version_id, checked, "weekdays")
    _require_shift_kind_list(rule_version_id, checked, "forbidden_shift_kinds")


def _validate_day_only_n_exception(rule_version_id: str, params: object) -> None:
    checked = _require_keys(rule_version_id, params, {"employee_id"})
    _require_nonempty_str(rule_version_id, checked, "employee_id")


_PARAM_VALIDATORS = {
    EMPLOYEE_ALLOWED_SHIFT_KINDS: _validate_allowed_shift_kinds,
    EMPLOYEE_ALLOWED_WEEKDAYS: _validate_allowed_weekdays,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS: _validate_forbidden_shift_kinds_on_weekdays,
    EMPLOYEE_DAY_ONLY_N_EXCEPTION: _validate_day_only_n_exception,
}


def validate_executable_site_rules(site_rules) -> None:
    """Prevalidation entry point (called once per plan()/REPLAN, before
    solve()): raises on the first RESOLVED rule that cannot be executed.
    INFORMATIONAL rules are never inspected (R1 clarification)."""
    for rule in site_rules:
        if rule.enforcement == RuleEnforcement.INFORMATIONAL:
            continue
        if rule.enforcement == RuleEnforcement.SOFT:
            raise UnsupportedOrMalformedSiteRule(
                rule.rule_version_id, "RESOLVED SOFT SiteRule ranking is not supported by T007"
            )
        if rule.rule_kind not in SUPPORTED_RULE_KINDS:
            raise UnsupportedOrMalformedSiteRule(rule.rule_version_id, f"unsupported rule_kind: {rule.rule_kind!r}")
        _PARAM_VALIDATORS[rule.rule_kind](rule.rule_version_id, rule.structured_parameters)


def rule_allows_assignment(rule: SiteRuleVersion, employee_id: str, demand_start_date: date, shift_kind: ShiftKind) -> bool:
    """Assumes rule.enforcement == HARD and has already passed
    validate_executable_site_rules -- the day anchor for weekday-based kinds
    is always the ShiftDemand's start date (arch/FROZEN_ADDENDUM_SITE_RULE_EXEC_01.md
    DAY ANCHOR), including for N shifts that end the next calendar day."""
    params = rule.structured_parameters
    if params["employee_id"] != employee_id:
        return True
    if rule.rule_kind == EMPLOYEE_ALLOWED_SHIFT_KINDS:
        return shift_kind.value in params["allowed_shift_kinds"]
    if rule.rule_kind == EMPLOYEE_ALLOWED_WEEKDAYS:
        return demand_start_date.isoweekday() in params["allowed_weekdays"]
    if rule.rule_kind == EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS:
        forbidden = (
            demand_start_date.isoweekday() in params["weekdays"]
            and shift_kind.value in params["forbidden_shift_kinds"]
        )
        return not forbidden
    if rule.rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION:
        # Narrow exception to DAY_ONLY-01 only (see day_only_n_exception_applies)
        # -- never a generic HARD gate, so it never blocks here.
        return True
    raise AssertionError(f"unreachable: unvalidated rule_kind {rule.rule_kind!r}")  # pragma: no cover


def day_only_n_exception_applies(applicable_hard_rules: list[SiteRuleVersion], employee_id: str) -> bool:
    """DAY-ONLY-TEMP-N-EXCEPTION-01
    (arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md): True when an
    applicable RESOLVED HARD EMPLOYEE_DAY_ONLY_N_EXCEPTION rule names
    employee_id. Exempts only DAY_ONLY-01 for N; every other HARD rule
    still applies via AND -- callers must only consult this at the
    DAY_ONLY-01 check site, never as a general override.

    R3-3: the addendum requires category=CONFIRMED_EXCEPTION -- a rule of
    this kind saved under any other category (e.g. an ordinary LOCAL_RULE)
    must not grant the exception."""
    return any(
        r.rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION
        and r.category == RuleCategory.CONFIRMED_EXCEPTION
        and r.structured_parameters.get("employee_id") == employee_id
        for r in applicable_hard_rules
    )


def hard_rules_applicable_on(site_rules, applicability, as_of: date) -> list[SiteRuleVersion]:
    """Every RESOLVED HARD SiteRuleVersion whose SiteRuleApplicability slice
    covers `as_of` (inclusive both ends)."""
    applicable_ids = {a.rule_version_id for a in applicability if a.applies_from <= as_of <= a.applies_to}
    return [r for r in site_rules if r.rule_version_id in applicable_ids and r.enforcement == RuleEnforcement.HARD]


if __name__ == "__main__":
    print("planning.site_rules module OK")
