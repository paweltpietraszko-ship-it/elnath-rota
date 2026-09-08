"""ROTA-T034's SOFT third-consecutive-day-shift-adjacent penalty (D/D/D,
D/D/N, D/N/N) is RETIRED, superseded by ROTA-T058 (OWNER_CORRECTED
2026-09-08): the same pattern -- generalized to any PRIMARY D/N combination,
not just day-shift-adjacent -- is now a genuine HARD CP-SAT constraint
(rota.planning.constraints.add_max_two_consecutive_primary_shift_constraint),
never traded away for target/equity precision, with no SOFT ranking and no
DECISION_REQUIRED escape for the automatic solver.

fairness.add_third_consecutive_shift_penalty and THIRD_CONSECUTIVE_SHIFT_
PENALTY_WEIGHT no longer exist -- this file's original T34-01..T34-12 SOFT-
ranking test matrix tested exactly that removed mechanism and would now only
duplicate, in a stale shape, what tests/test_t058.py covers for the real
(HARD) behavior. Kept as this short marker rather than deleted outright, so
the historical contract (contract SHA f4a1e0b) and its supersession stay
traceable from the test tree itself, not only from git history.

See tests/test_t058.py for the current, comprehensive behavioral coverage
(T58-01..T58-14)."""
from __future__ import annotations


def test_t034_soft_mechanism_is_fully_retired():
    """The exact symbols ROTA-T034 introduced must be gone, not merely
    unused -- a stray reimport of either would silently resurrect a second,
    competing ranking mechanism alongside ROTA-T058's HARD constraint."""
    import rota.planning.fairness as fairness

    assert not hasattr(fairness, "add_third_consecutive_shift_penalty")
    assert not hasattr(fairness, "THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT")
