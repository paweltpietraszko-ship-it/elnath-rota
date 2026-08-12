"""ROTA-T005 acceptance tests (tasks/ROTA-T005/brief.md)."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest

from rota.domain import RuleCategory, RuleEnforcement, RuleResolution, SiteRuleVersion
from rota.persistence.db import connect
from rota.persistence.decision_ledger import ChainIntegrityError, record_decision
from rota.persistence.site_memory import (
    DecisionRecordNotFound,
    decision_fate,
    effective_rule_on,
    rule_history,
    rule_provenance,
)
from rota.persistence.site_rule_assembly import assemble_site_rules
from rota.persistence.site_rule_repository import RuleFamilyIntegrityError, insert_site_rule_version
from rota.site_memory_types import EffectiveRule, NewRuleContent, NoActiveRule


def _content(**overrides) -> NewRuleContent:
    defaults = dict(
        category=RuleCategory.LOCAL_RULE,
        rule_kind=None,
        structured_parameters={"weekend_only": True},
        enforcement=RuleEnforcement.HARD,
        resolution_status=RuleResolution.RESOLVED,
        effective_to=None,
        description=None,
        source=None,
        reason=None,
    )
    defaults.update(overrides)
    return NewRuleContent(**defaults)


def _conn(tmp_path: Path) -> sqlite3.Connection:
    return connect(tmp_path / "rota.db")


def test_first_decision_creates_rule_and_is_active(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    decision = record_decision(
        conn, site_id="S1", rule_id="R1", statement="Pracownik A pracuje tylko w weekendy.",
        coordinator_id="COORD-1", recorded_at=datetime(2026, 3, 1, 9, 0),
        effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    assert decision.rule_version_id is not None
    assert decision.predecessor_decision_id is None
    assert decision_fate(conn, decision.decision_id) == "ACTIVE"


def test_first_decision_cannot_carry_a_rel_or_skip_rule_content(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    with pytest.raises(ChainIntegrityError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="x", coordinator_id="C",
            recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
            rel="supersedes", rule_content=_content(),
        )
    with pytest.raises(ChainIntegrityError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="x", coordinator_id="C",
            recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
            rel=None, rule_content=None,
        )


def test_supersedes_links_new_version_to_predecessor_and_updates_fate(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    first = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    second = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v2", coordinator_id="C",
        recorded_at=datetime(2026, 3, 10), effective_from=date(2026, 6, 1),
        rel="supersedes", rule_content=_content(),
    )
    version2 = effective_rule_on(conn, "S1", "R1", date(2026, 6, 2))
    assert isinstance(version2, EffectiveRule)
    assert version2.rule_version.supersedes_rule_version_id == first.rule_version_id
    assert decision_fate(conn, first.decision_id) == "SUPERSEDED"
    assert decision_fate(conn, second.decision_id) == "ACTIVE"


def test_non_first_decision_requires_a_rel(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    with pytest.raises(ChainIntegrityError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="v2", coordinator_id="C",
            recorded_at=datetime(2026, 3, 2), effective_from=date(2026, 3, 2), rel=None, rule_content=_content(),
        )


def test_rejects_creates_no_rule_version_and_gives_no_active_rule(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    rejection = record_decision(
        conn, site_id="S1", rule_id="R1", statement="odwolane", coordinator_id="C",
        recorded_at=datetime(2026, 4, 1), effective_from=date(2026, 4, 1), rel="rejects", rule_content=None,
    )
    assert rejection.rule_version_id is None
    result = effective_rule_on(conn, "S1", "R1", date(2026, 4, 2))
    assert isinstance(result, NoActiveRule)
    # before the rejection took effect, the original rule still holds
    still_active = effective_rule_on(conn, "S1", "R1", date(2026, 3, 15))
    assert isinstance(still_active, EffectiveRule)


def test_rejects_requires_rule_content_to_be_none(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    with pytest.raises(ChainIntegrityError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="x", coordinator_id="C",
            recorded_at=datetime(2026, 4, 1), effective_from=date(2026, 4, 1),
            rel="rejects", rule_content=_content(),
        )


def test_restoring_after_reject_has_no_supersedes_link(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="odwolane", coordinator_id="C",
        recorded_at=datetime(2026, 4, 1), effective_from=date(2026, 4, 1), rel="rejects", rule_content=None,
    )
    restored = record_decision(
        conn, site_id="S1", rule_id="R1", statement="przywrocone", coordinator_id="C",
        recorded_at=datetime(2026, 5, 1), effective_from=date(2026, 5, 1),
        rel="supersedes", rule_content=_content(),
    )
    version = effective_rule_on(conn, "S1", "R1", date(2026, 5, 2))
    assert isinstance(version, EffectiveRule)
    assert version.rule_version.supersedes_rule_version_id is None
    assert version.rule_version.rule_version_id == restored.rule_version_id


def test_corrects_requires_rule_version_id_on_both_sides(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="odwolane", coordinator_id="C",
        recorded_at=datetime(2026, 4, 1), effective_from=date(2026, 4, 1), rel="rejects", rule_content=None,
    )
    with pytest.raises(ChainIntegrityError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="korekta", coordinator_id="C",
            recorded_at=datetime(2026, 4, 5), effective_from=date(2026, 4, 5),
            rel="corrects", rule_content=_content(),
        )


def test_effective_selection_future_decision_example_from_brief(tmp_path: Path) -> None:
    """The exact A/B/C example from tasks/ROTA-T005/brief.md EFFECTIVE SELECTION."""
    conn = _conn(tmp_path)
    a = record_decision(
        conn, site_id="S1", rule_id="R1", statement="A", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="B", coordinator_id="C",
        recorded_at=datetime(2026, 3, 10), effective_from=date(2026, 6, 1),
        rel="supersedes", rule_content=_content(),
    )
    c = record_decision(
        conn, site_id="S1", rule_id="R1", statement="C", coordinator_id="C",
        recorded_at=datetime(2026, 4, 15), effective_from=date(2026, 5, 1),
        rel="supersedes", rule_content=_content(),
    )

    def _version_id_on(as_of: date) -> str | None:
        result = effective_rule_on(conn, "S1", "R1", as_of)
        return result.rule_version.rule_version_id if isinstance(result, EffectiveRule) else None

    assert _version_id_on(date(2026, 4, 20)) == a.rule_version_id
    assert _version_id_on(date(2026, 5, 20)) == c.rule_version_id
    assert _version_id_on(date(2026, 6, 10)) == c.rule_version_id


def test_effective_to_is_inclusive_and_does_not_resurrect_older_version(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
        rel=None, rule_content=_content(effective_to=date(2026, 5, 31)),
    )
    result_last_day = effective_rule_on(conn, "S1", "R1", date(2026, 5, 31))
    assert isinstance(result_last_day, EffectiveRule)
    result_after = effective_rule_on(conn, "S1", "R1", date(2026, 6, 1))
    assert isinstance(result_after, NoActiveRule)


def test_rule_history_returns_full_linear_chain_in_order(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v2", coordinator_id="C",
        recorded_at=datetime(2026, 3, 10), effective_from=date(2026, 4, 1),
        rel="supersedes", rule_content=_content(),
    )
    history = rule_history(conn, "S1", "R1")
    assert [d.statement for d in history] == ["v1", "v2"]
    assert history[1].predecessor_decision_id == history[0].decision_id


def test_rule_provenance_traces_back_to_creating_decision(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    second = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v2", coordinator_id="C",
        recorded_at=datetime(2026, 3, 10), effective_from=date(2026, 4, 1),
        rel="supersedes", rule_content=_content(),
    )
    creating_decision, earlier_chain = rule_provenance(conn, second.rule_version_id)
    assert creating_decision.decision_id == second.decision_id
    assert [d.statement for d in earlier_chain] == ["v1", "v2"]


def test_decision_for_unknown_rule_version_raises(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    with pytest.raises(DecisionRecordNotFound):
        rule_provenance(conn, "RV-does-not-exist")


def test_decision_and_rule_version_stay_consistent(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    decision = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="COORD-9",
        recorded_at=datetime(2026, 3, 1, 12, 30), effective_from=date(2026, 3, 5),
        rel=None, rule_content=_content(),
    )
    result = effective_rule_on(conn, "S1", "R1", date(2026, 3, 5))
    assert isinstance(result, EffectiveRule)
    version = result.rule_version
    assert version.site_id == decision.site_id
    assert version.rule_id == decision.rule_id
    assert version.changed_by == decision.coordinator_id
    assert version.changed_at == decision.recorded_at
    assert version.effective_from == decision.effective_from


def test_structured_parameters_json_round_trip(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    params = {"days": ["SAT", "SUN"], "weekend_only": True, "min_hours": 8}
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
        rel=None, rule_content=_content(structured_parameters=params),
    )
    result = effective_rule_on(conn, "S1", "R1", date(2026, 3, 1))
    assert isinstance(result, EffectiveRule)
    assert result.rule_version.structured_parameters == params


def test_structured_parameters_must_be_json_compatible(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    with pytest.raises(TypeError):
        record_decision(
            conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
            recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
            rel=None, rule_content=_content(structured_parameters={"bad": object()}),
        )


def test_records_and_versions_are_append_only_at_schema_level(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    decision = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE decision_records SET statement = 'changed' WHERE decision_id = ?",
            (decision.decision_id,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM decision_records WHERE decision_id = ?", (decision.decision_id,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE site_rule_versions SET effective_to = '2026-01-01' WHERE rule_version_id = ?",
            (decision.rule_version_id,),
        )


def test_needs_resolution_rules_never_execute_but_stay_visible(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="niejasna regula", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None,
        rule_content=_content(rule_kind=None, structured_parameters=None, resolution_status=RuleResolution.NEEDS_RESOLUTION),
    )
    resolved, unresolved = assemble_site_rules(conn, "S1", ["R1"], date(2026, 3, 5))
    assert resolved == ()
    assert len(unresolved) == 1
    assert unresolved[0].resolution_status == RuleResolution.NEEDS_RESOLUTION


def test_assemble_site_rules_splits_resolved_and_skips_no_active_rule(tmp_path: Path) -> None:
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="resolved rule", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    resolved, unresolved = assemble_site_rules(conn, "S1", ["R1", "R_NEVER_DECIDED"], date(2026, 3, 5))
    assert len(resolved) == 1
    assert unresolved == ()


def test_r1_1a_same_rule_id_under_two_sites_is_rejected(tmp_path: Path) -> None:
    """Audit round 1 FINDING R1-1 variant A: record_decision let a second,
    independent family reuse the same rule_id under a different site_id."""
    conn = _conn(tmp_path)
    record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    with pytest.raises(RuleFamilyIntegrityError):
        record_decision(
            conn, site_id="S2", rule_id="R1", statement="v1 on a different site", coordinator_id="C",
            recorded_at=datetime(2026, 3, 2), effective_from=date(2026, 3, 2), rel=None, rule_content=_content(),
        )


def test_r1_1b_cross_family_supersedes_link_is_rejected(tmp_path: Path) -> None:
    """Audit round 1 FINDING R1-1 variant B: insert_site_rule_version accepted
    a version whose supersedes_rule_version_id pointed at a different
    (site_id, rule_id) family -- only the foreign key existence was checked."""
    conn = _conn(tmp_path)
    original = record_decision(
        conn, site_id="S1", rule_id="R1", statement="v1", coordinator_id="C",
        recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1), rel=None, rule_content=_content(),
    )
    cross_family_version = SiteRuleVersion(
        rule_version_id="RV-cross-family", rule_id="R2", site_id="S2",
        category=RuleCategory.LOCAL_RULE, rule_kind=None, structured_parameters=None,
        enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
        effective_from=date(2026, 3, 1), effective_to=None,
        changed_at=datetime(2026, 3, 1), changed_by="C",
        supersedes_rule_version_id=original.rule_version_id,
        description=None, source=None, reason=None,
    )
    with pytest.raises(RuleFamilyIntegrityError):
        insert_site_rule_version(conn, cross_family_version)


def test_r1_2_json_boundary_rejects_lossy_or_non_standard_values(tmp_path: Path) -> None:
    """Audit round 1 FINDING R1-2: json.dumps defaults silently coerce
    non-string dict keys and tuples, and accept NaN/Infinity, which are not
    valid JSON -- all four must now be refused, not silently mutated."""
    conn = _conn(tmp_path)
    non_json_values = [
        {1: "x"},
        {"tuple": (1, 2)},
        float("nan"),
        float("inf"),
    ]
    for index, value in enumerate(non_json_values):
        with pytest.raises(TypeError):
            record_decision(
                conn, site_id="S1", rule_id=f"R-json-{index}", statement="v1", coordinator_id="C",
                recorded_at=datetime(2026, 3, 1), effective_from=date(2026, 3, 1),
                rel=None, rule_content=_content(structured_parameters=value),
            )


def test_planning_engine_has_no_site_memory_coupling() -> None:
    planning_dir = Path(__file__).resolve().parent.parent / "rota" / "planning"
    for path in planning_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "rota.persistence" not in source, f"{path} imports persistence"
        assert "rota.site_memory_types" not in source, f"{path} imports site_memory_types"
        assert "import sqlite3" not in source, f"{path} imports sqlite3 directly"
