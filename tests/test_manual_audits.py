"""Regression wrapper for tests/support/manual_audits.py (owner-directed,
2026-08-13): keeps the three hand-verified real-object solver passes from
silently rotting, without hiding their printed, human-readable evidence --
run `python -m tests.support.manual_audits` directly to see the full
schedules. ROTA-CLEANUP-FROZEN-BENCHMARKS (2026-09-15): moved out of
benchmarks/ -- this is a live, owner-kept regression guard, never part of
the frozen/broken benchmark evaluator chain that was deleted alongside it.
"""
from __future__ import annotations

from dataclasses import replace

from rota.domain import SitePlanningRegime
from tests.support.manual_audits import (
    _dense_overlap_2027_10,
    _feb_2028_leap_year,
    verify_decision_required_by_hand,
    verify_feasible_month,
)

EMPLOYEES = ("A", "B", "C", "D", "E")


def _ochrona(state):
    """ROTA-CLOUD-REVIEW-FIXES T: these hand-verified real-object passes check
    OCHRONA DAY_ONLY; the shared builder's default site is ORDINARY, where
    D/N has no legal meaning since T065."""
    return replace(state, site=replace(state.site, planning_regime=SitePlanningRegime.OCHRONA))


def test_manual_audit_feb_2028_leap_year_feasible():
    assert verify_feasible_month(_ochrona(_feb_2028_leap_year()), EMPLOYEES) is True


def test_manual_audit_dense_overlap_oct_2027_feasible():
    assert verify_feasible_month(_ochrona(_dense_overlap_2027_10()), EMPLOYEES) is True


def test_manual_audit_decision_required_proven_by_hand():
    assert verify_decision_required_by_hand() is True
