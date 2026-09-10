"""Coordinator-facing DECISION_REQUIRED presentation (ROTA-T013,
arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md).

Pure translation layer: consumes raw Blocker/facts already computed by
engine.py's four terminal autonomy-boundary paths and renders the
coordinator-facing DecisionRequiredPayload contents. Never re-derives
eligibility, never runs a second solve, never mutates roster/persistence,
and never sees intermediate T018 retry stages -- those are filtered out by
engine.py before any raw fact reaches this module.
"""
from __future__ import annotations

from dataclasses import replace

from rota.planning.engine_types import Blocker, DecisionRequiredPayload, UnblockingOption
from rota.planning.state import PlanningState

# INSUFFICIENT_COVERAGE/UNKNOWN are internal solver-only markers, never a
# coordinator-facing code. MEMBERSHIP_DISABLED/MEMBERSHIP-01 are invisible by
# owner decision -- only the coordinator decides current staffing.
_HIDDEN_RAW_CONDITIONS = frozenset({
    "MEMBERSHIP_DISABLED", "MEMBERSHIP-01", "INSUFFICIENT_COVERAGE", "UNKNOWN",
})

_BUILT_IN_CONDITION_TEXT = {
    "UNAVAILABLE-01": "Koliduje z ustawieniem: Ogólna dostępność",
    "DAY_ONLY-01": "Koliduje z ustawieniem: Nocka",
    "SICK_LEAVE-01": "Koliduje z zapisem: Chorobowe",
    "LEAVE_GRANTED-01": "Koliduje z zapisem: Urlop",
    "REST-01": "Koliduje z odpoczynkiem dobowym",
    "LOAD-01": "Koliduje z tygodniowym czasem pracy",
    "EXTERNAL-01": "Wsparcie zewnętrzne",
    "EXTERNAL_SUPPORT_DISABLED": "Wsparcie zewnętrzne",
    "SHIFT-24-01": "Koliduje z ustawieniem: 24",
    "NIGHT-STREAK-01": "Koliduje z limitem dwóch nocek pod rząd",
    "DAY_SHIFT_OFF-01": "Koliduje z zapisem: Wolne w dzień",
}
_GENERIC_SITE_RULE_TEXT = "Koliduje z zapisaną regułą obiektu"

# ROTA-T062: target="obsada" for actions the coordinator performs on the
# roster/availability screen; requires_existing_schedule=True marks the
# three manual-correction-style suggestions that only make sense once a
# current ScheduleVersion exists to correct (T061 is retired -- plan_ops
# drops these for a no-current result instead of pointing at a dead end).
_ACTION_TEMPLATES = {
    "UNAVAILABLE-01": UnblockingOption("Zmień Ogólna dostępność: {names}", target="obsada"),
    "DAY_ONLY-01": UnblockingOption("Zmień Nocka: {names}", target="obsada"),
    "SHIFT-24-01": UnblockingOption("Zmień 24: {names}", target="obsada"),
    "SICK_LEAVE-01": UnblockingOption(
        "Ręczna korekta mimo zapisu Chorobowe zgodnie z kontraktem: {names}", requires_existing_schedule=True,
    ),
    "LEAVE_GRANTED-01": UnblockingOption(
        "Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: {names}", requires_existing_schedule=True,
    ),
    "REST-01": UnblockingOption(
        "Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: {names}",
        requires_existing_schedule=True,
    ),
    # ROTA-T062 (brief section 4 point 5): NIGHT-STREAK-01 had a condition
    # description but no suggested action at all -- the accepted recovery is
    # the same as every other roster-shaped blocker, check staffing/
    # availability and plan again, no outcome guarantee.
    "NIGHT-STREAK-01": UnblockingOption("Sprawdź obsadę i dostępność: {names}, i zaplanuj ponownie", target="obsada"),
}
_EXTERNAL_CONDITIONS = ("EXTERNAL-01", "EXTERNAL_SUPPORT_DISABLED")
_UNFREEZE_OPTION = UnblockingOption("Odmroź zapisane przypisania i uruchom planowanie ponownie")
_LOAD_OPTION = UnblockingOption("Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy")
_NO_SOLUTION_OPTION = UnblockingOption("Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.")
# ROTA-T062 (brief section 4 point 6): THIRD_CONSECUTIVE_SHIFT_BLOCKED never
# built a decision_payload before -- same guidance family as NIGHT-STREAK-01
# (staffing/availability + replan), never a solver override or a candidate
# that breaks the rule.
_THIRD_SHIFT_OPTION = UnblockingOption("Sprawdź obsadę i dostępność: {names}, i zaplanuj ponownie", target="obsada")


def _display_name(state: PlanningState, employee_id: str) -> str:
    for employee in state.employees:
        if employee.employee_id == employee_id:
            return employee.display_name
    return employee_id


def _site_rules_by_id(state: PlanningState) -> dict:
    return {rule.rule_version_id: rule for rule in state.site_rules}


def _render_condition(raw_condition: str, site_rules_by_id: dict) -> str | None:
    if raw_condition in _HIDDEN_RAW_CONDITIONS:
        return None
    if raw_condition in _BUILT_IN_CONDITION_TEXT:
        return _BUILT_IN_CONDITION_TEXT[raw_condition]
    rule = site_rules_by_id.get(raw_condition)
    if rule is not None:
        description = (rule.description or "").strip()
        return description if description else _GENERIC_SITE_RULE_TEXT
    return raw_condition


def render_coordinator_blockers(state: PlanningState, raw_blockers: list[Blocker]) -> list[Blocker]:
    """Translate raw Blocker.condition codes into coordinator-facing text,
    dropping hidden conditions and deduplicating -- deterministic regardless
    of input order (brief.md section K)."""
    site_rules_by_id = _site_rules_by_id(state)
    rendered: set[tuple[str, str]] = set()
    for blocker in raw_blockers:
        condition = _render_condition(blocker.condition, site_rules_by_id)
        if condition is not None:
            rendered.add((blocker.employee_id, condition))
    return [Blocker(employee_id, condition) for employee_id, condition in sorted(rendered)]


def _names_for(state: PlanningState, raw_blockers: list[Blocker], conditions: tuple) -> list[str]:
    ids = {b.employee_id for b in raw_blockers if b.condition in conditions}
    return sorted({_display_name(state, employee_id) for employee_id in ids})


def _site_rule_descriptions(raw_blockers: list[Blocker], site_rules_by_id: dict) -> list[str]:
    descriptions: set[str] = set()
    for blocker in raw_blockers:
        rule = site_rules_by_id.get(blocker.condition)
        if rule is None:
            continue
        text = (rule.description or "").strip()
        descriptions.add(text if text else _GENERIC_SITE_RULE_TEXT)
    return sorted(descriptions)


def _formatted(option: UnblockingOption, names: list[str]) -> UnblockingOption:
    return replace(option, text=option.text.format(names=", ".join(names)))


def build_unblocking_options(
    state: PlanningState, raw_blockers: list[Blocker], load_blocker, *, frozen_boundary: bool = False,
) -> list[UnblockingOption]:
    """Evidence-backed dynamic guidance (brief.md section F): an option
    exists only when a matching raw blocker/final fact is actually present
    in this diagnosis. Family order is fixed (addendum DETERMINISM)."""
    site_rules_by_id = _site_rules_by_id(state)
    options: list[UnblockingOption] = []

    for condition in ("UNAVAILABLE-01", "DAY_ONLY-01", "SHIFT-24-01", "NIGHT-STREAK-01"):
        names = _names_for(state, raw_blockers, (condition,))
        if names:
            options.append(_formatted(_ACTION_TEMPLATES[condition], names))

    external_names = _names_for(state, raw_blockers, _EXTERNAL_CONDITIONS)
    if external_names:
        options.append(UnblockingOption(f"Skonfiguruj Wsparcie zewnętrzne: {', '.join(external_names)}", target="obsada"))

    for condition in ("SICK_LEAVE-01", "LEAVE_GRANTED-01", "REST-01"):
        names = _names_for(state, raw_blockers, (condition,))
        if names:
            options.append(_formatted(_ACTION_TEMPLATES[condition], names))

    # ROTA-T062 (brief section 4 point 9, R1 audit finding): the previous
    # target="obiekt" here was inherited unquestioned from Decisions.tsx's
    # old prefix-matching code -- verified against the real "Obiekt" tab
    # (frontend/src/screens/ControlPanel.tsx) and it only contains the
    # shift catalog and print settings, no editor for an arbitrary saved
    # SiteRuleVersion at all. Brief section 4 point 9 says exactly this
    # case in words: an unrecognized/general rule with no real editor is
    # honest information, never a fake button pointing at the catalog.
    for description in _site_rule_descriptions(raw_blockers, site_rules_by_id):
        options.append(UnblockingOption(f"Zmień zapisaną regułę: {description}"))

    if frozen_boundary:
        options.append(_UNFREEZE_OPTION)
    if load_blocker is not None:
        options.append(_LOAD_OPTION)

    return options or [_NO_SOLUTION_OPTION]


def build_decision_payload(
    state: PlanningState, blocking_shift_demands: list, raw_blockers: list[Blocker], load_blocker,
    *, frozen_boundary: bool = False,
):
    """Single owner of the final coordinator-facing DecisionRequiredPayload
    -- reuses the existing DTO shape, never a parallel model."""
    return DecisionRequiredPayload(
        blocking_shift_demands=blocking_shift_demands,
        blockers=render_coordinator_blockers(state, raw_blockers),
        load_blocker=load_blocker,
        unblocking_options=build_unblocking_options(state, raw_blockers, load_blocker, frozen_boundary=frozen_boundary),
    )


def build_third_shift_payload(state: PlanningState, employee_ids: list[str]) -> DecisionRequiredPayload:
    """ROTA-T062 (brief section 4 point 6): THIRD_CONSECUTIVE_SHIFT_BLOCKED
    shares this module's guidance family instead of building nothing --
    same staffing/availability + replan recovery as NIGHT-STREAK-01, never a
    solver override or a rule-breaking candidate (that stays retired, see
    ROTA-T061). Status stays THIRD_CONSECUTIVE_SHIFT_BLOCKED at the engine
    layer; only the coordinator-facing guidance is shared."""
    names = sorted({_display_name(state, employee_id) for employee_id in employee_ids})
    option = _formatted(_THIRD_SHIFT_OPTION, names) if names else _NO_SOLUTION_OPTION
    return DecisionRequiredPayload(
        blocking_shift_demands=[], blockers=[], load_blocker=None, unblocking_options=[option],
    )


def drop_options_requiring_existing_schedule(payload: DecisionRequiredPayload) -> DecisionRequiredPayload:
    """ROTA-T062 (brief section 4 point 8): with no current ScheduleVersion,
    a manual-correction-style suggestion (UnblockingOption.
    requires_existing_schedule) points at a dead end -- ROTA-T061 (first
    manual root without current) is retired, and T062 does not offer
    Korekta ręczna as no-current guidance at all. Sole owner of the
    fallback text stays this module, same as every other option."""
    filtered = [o for o in payload.unblocking_options if not o.requires_existing_schedule]
    return replace(payload, unblocking_options=filtered or [_NO_SOLUTION_OPTION])


if __name__ == "__main__":
    print("decision_guidance module OK")
