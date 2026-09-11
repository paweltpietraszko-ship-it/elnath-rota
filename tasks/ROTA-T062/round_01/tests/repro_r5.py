from datetime import date, datetime

from api.decision_payload import decision_payload_out
from rota.domain import (
    Employee,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    SiteRuleVersion,
)
from rota.persistence.site_memory import _payload_from_dict
from rota.planning.decision_guidance import (
    build_unblocking_options,
    drop_options_requiring_existing_schedule,
)
from rota.planning.engine_types import Blocker, DecisionRequiredPayload
from rota.planning.site_rules import EMPLOYEE_ALLOWED_SHIFT_KINDS
from tests.support.minimal_state import SITE_ID, base_state


def test_mixed_evidence_keeps_all_actions_and_safe_targets():
    employee = Employee("E1", "Anna", date(2020, 1, 1), None, False)
    rule = SiteRuleVersion(
        "RV-1", "R-1", SITE_ID, RuleCategory.LOCAL_RULE,
        EMPLOYEE_ALLOWED_SHIFT_KINDS,
        {"employee_id": "E1", "allowed_shift_kinds": ["N"]},
        RuleEnforcement.HARD, RuleResolution.RESOLVED,
        date(2026, 10, 1), None, datetime(2026, 9, 1), "C1",
        None, "Reguła bez istniejącego edytora", None, None,
    )
    state = base_state(employees=(employee,), site_rules=(rule,))
    options = build_unblocking_options(
        state,
        [
            Blocker("E1", "SICK_LEAVE-01"),
            Blocker("E1", "RV-1"),
            Blocker("E1", "NIGHT-STREAK-01"),
            Blocker("E1", "UNAVAILABLE-01"),
        ],
        None,
    )
    assert [(o.target, o.requires_existing_schedule) for o in options] == [
        ("obsada", False),
        ("obsada", False),
        (None, True),
        (None, False),
    ]
    assert "Reguła bez istniejącego edytora" in options[-1].text

    filtered = drop_options_requiring_existing_schedule(
        DecisionRequiredPayload([], [], None, options)
    )
    assert all(not o.requires_existing_schedule for o in filtered.unblocking_options)
    assert len(filtered.unblocking_options) == 3


def test_legacy_string_survives_persistence_decoder_and_public_adapter():
    restored = _payload_from_dict(
        {
            "blocking_shift_demands": [],
            "blockers": [],
            "load_blocker": None,
            "unblocking_options": ["historyczna informacja"],
        }
    )
    assert decision_payload_out(restored).model_dump()["unblocking_options"] == [
        {"text": "historyczna informacja", "target": None}
    ]
