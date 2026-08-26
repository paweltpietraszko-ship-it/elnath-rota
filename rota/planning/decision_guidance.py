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

from rota.planning.engine_types import Blocker, DecisionRequiredPayload
from rota.planning.state import PlanningState

# INSUFFICIENT_COVERAGE/UNKNOWN are internal solver-only markers, never a
# coordinator-facing code. MEMBERSHIP_DISABLED/MEMBERSHIP-01 are invisible by
# owner decision -- only the coordinator decides current staffing.
_HIDDEN_RAW_CONDITIONS = frozenset({
    "MEMBERSHIP_DISABLED", "MEMBERSHIP-01", "INSUFFICIENT_COVERAGE", "UNKNOWN",
})

_BUILT_IN_CONDITION_TEXT = {
    "UNAVAILABLE-01": "Koliduje z checkbox: Ogólna dostępność",
    "DAY_ONLY-01": "Koliduje z checkbox: Nocka",
    "SICK_LEAVE-01": "Koliduje z zapisem: Chorobowe",
    "LEAVE_GRANTED-01": "Koliduje z zapisem: Urlop",
    "REST-01": "Koliduje z odpoczynkiem dobowym",
    "LOAD-01": "Koliduje z tygodniowym czasem pracy",
    "EXTERNAL-01": "Wsparcie zewnętrzne",
    "EXTERNAL_SUPPORT_DISABLED": "Wsparcie zewnętrzne",
    "SHIFT-24-01": "Koliduje z checkbox: 24",
    "NIGHT-STREAK-01": "Koliduje z limitem dwóch nocek pod rząd",
}
_GENERIC_SITE_RULE_TEXT = "Koliduje z zapisaną regułą obiektu"

_ACTION_TEMPLATES = {
    "UNAVAILABLE-01": "Zmień Ogólna dostępność: {names}",
    "DAY_ONLY-01": "Zmień Nocka: {names}",
    "SHIFT-24-01": "Zmień 24: {names}",
    "SICK_LEAVE-01": "Ręczna korekta mimo zapisu Chorobowe zgodnie z kontraktem: {names}",
    "LEAVE_GRANTED-01": "Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: {names}",
    "REST-01": "Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: {names}",
}
_EXTERNAL_CONDITIONS = ("EXTERNAL-01", "EXTERNAL_SUPPORT_DISABLED")
_UNFREEZE_OPTION = "Odmroź zapisane przypisania i uruchom planowanie ponownie"
_LOAD_OPTION = "Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy"
_NO_SOLUTION_OPTION = "Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."


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
    if raw_condition == "DAY_SHIFT_OFF-01":
        return raw_condition
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


def build_unblocking_options(
    state: PlanningState, raw_blockers: list[Blocker], load_blocker, *, frozen_boundary: bool = False,
) -> list[str]:
    """Evidence-backed dynamic guidance (brief.md section F): an option
    exists only when a matching raw blocker/final fact is actually present
    in this diagnosis. Family order is fixed (addendum DETERMINISM)."""
    site_rules_by_id = _site_rules_by_id(state)
    options: list[str] = []

    for condition in ("UNAVAILABLE-01", "DAY_ONLY-01", "SHIFT-24-01"):
        names = _names_for(state, raw_blockers, (condition,))
        if names:
            options.append(_ACTION_TEMPLATES[condition].format(names=", ".join(names)))

    external_names = _names_for(state, raw_blockers, _EXTERNAL_CONDITIONS)
    if external_names:
        options.append(f"Skonfiguruj Wsparcie zewnętrzne: {', '.join(external_names)}")

    for condition in ("SICK_LEAVE-01", "LEAVE_GRANTED-01", "REST-01"):
        names = _names_for(state, raw_blockers, (condition,))
        if names:
            options.append(_ACTION_TEMPLATES[condition].format(names=", ".join(names)))

    for description in _site_rule_descriptions(raw_blockers, site_rules_by_id):
        options.append(f"Zmień zapisaną regułę: {description}")

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


if __name__ == "__main__":
    print("decision_guidance module OK")
