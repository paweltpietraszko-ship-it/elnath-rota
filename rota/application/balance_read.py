"""ROTA-T011-D (A-5): explicit quarter-balance read, thin and unguarded --
same shape as rota.application.memory_read (delegates without repacking,
no coordinator-context guard, since this is a read). Closes Z-6 alongside
assembler._assemble_work_balances's real carry-in (B-5/W2).
"""
from __future__ import annotations

from datetime import date

from rota.balance import MissingTargetHoursError
from rota.domain import WorkBalance
from rota.persistence.work_balance_repository import reconstruct_quarter_balance
from rota.planning.absence import IncompleteAbsenceReferenceError


def quarter_balance(conn, *, employee_id: str, quarter_first_month: date) -> tuple[list[WorkBalance], list[str]]:
    """ROZSTRZYGNIĘCIE WŁAŚCICIELA (2026-08-14): degrades to a warning, never
    raises MissingTargetHoursError, and never returns a partially-computed
    result -- if any month of the quarter (including a future one) lacks
    target_hours, the result is an empty list plus one warning naming the
    gap. Delegates to reconstruct_quarter_balance unchanged; no per-month
    loop is reimplemented here. ROTA-T023 Checkpoint B: the same degrade-
    to-warning treatment now also applies when a required absence reference
    is MISSING/AMBIGUOUS (IncompleteAbsenceReferenceError) -- never guessed,
    never a partial result."""
    try:
        return reconstruct_quarter_balance(conn, employee_id=employee_id, quarter_first_month=quarter_first_month), []
    except MissingTargetHoursError as exc:
        return [], [f"quarter balance unavailable for employee {employee_id!r}: {exc}"]
    except IncompleteAbsenceReferenceError as exc:
        return [], [f"quarter balance unavailable for employee {employee_id!r}: {exc}"]
