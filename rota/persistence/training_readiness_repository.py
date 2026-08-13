"""ROTA-T009 R5-3: training readiness credit ledger.

mark_training_realized's readiness threshold must count only unique,
qualifying training events -- not every current REALIZED TRAINEE
Assignment re-evaluated against today's SiteProfile config. A credit row
is written (inside the same open transaction as the schedule child) only
when an event qualifies at the moment it is recorded; the row's presence,
not a re-derived judgement about the Assignment, is what later counts.
"""
from __future__ import annotations

import sqlite3


def write_training_readiness_credit_in_open_transaction(
    conn: sqlite3.Connection, *, site_id: str, employee_id: str, assignment_id: str,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO training_readiness_credits (site_id, employee_id, assignment_id) VALUES (?, ?, ?)",
        (site_id, employee_id, assignment_id),
    )


def count_training_readiness_credits(conn: sqlite3.Connection, *, site_id: str, employee_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM training_readiness_credits WHERE site_id = ? AND employee_id = ?",
        (site_id, employee_id),
    ).fetchone()
    return row[0]
