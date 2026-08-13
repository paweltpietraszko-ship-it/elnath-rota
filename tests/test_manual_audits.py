"""Regression wrapper for benchmarks/manual_audits.py (owner-directed,
2026-08-13): keeps the three hand-verified real-object solver passes from
silently rotting, without hiding their printed, human-readable evidence --
run `python -m benchmarks.manual_audits` directly to see the full schedules.
"""
from __future__ import annotations

from benchmarks.manual_audits import (
    _dense_overlap_2027_10,
    _feb_2028_leap_year,
    verify_decision_required_by_hand,
    verify_feasible_month,
)

EMPLOYEES = ("A", "B", "C", "D", "E")


def test_manual_audit_feb_2028_leap_year_feasible():
    assert verify_feasible_month(_feb_2028_leap_year(), EMPLOYEES) is True


def test_manual_audit_dense_overlap_oct_2027_feasible():
    assert verify_feasible_month(_dense_overlap_2027_10(), EMPLOYEES) is True


def test_manual_audit_decision_required_proven_by_hand():
    assert verify_decision_required_by_hand() is True
