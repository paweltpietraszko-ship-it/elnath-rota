"""AvailabilityRecord persistence -- append-only history
(tasks/ROTA-T008/brief.md AVAILABILITYRECORD -- APPEND-ONLY HISTORY).

Mirrors the linear-chain pattern already audited in
rota/persistence/decision_ledger.py: availability_id names one logical
family, chain_seq is MAX+1 within that family, and a single entry point
determines first-vs-superseding from whether a chain end already exists,
so branching/skipping the end is structurally impossible rather than
merely validated.
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, time
from typing import Optional

from rota.domain import AvailabilityKind, AvailabilityRecord


class InvalidAvailabilityChain(Exception):
    """Raised when an appended version would branch, skip the chain end, or
    reference a predecessor outside its own (availability_id, employee_id)."""


class UnknownEmployeeForAvailability(Exception):
    """Raised when employee_id does not identify an existing Employee."""


def _current_chain_end(conn: sqlite3.Connection, availability_id: str) -> Optional[tuple]:
    return conn.execute(
        "SELECT availability_version_id, chain_seq, employee_id FROM availability_versions "
        "WHERE availability_id = ? ORDER BY chain_seq DESC LIMIT 1",
        (availability_id,),
    ).fetchone()


def _validate_time_window(kind: AvailabilityKind, start_time: Optional[time], end_time: Optional[time]) -> None:
    """ROTA-T065-ORDINARY-TIME-AVAILABILITY brief.md section 3/10: the
    write boundary, not the solver, rejects a malformed or overnight
    window -- and a kind other than UNAVAILABLE_TIME_WINDOW can never
    accidentally inherit hourly semantics."""
    if kind == AvailabilityKind.UNAVAILABLE_TIME_WINDOW:
        if start_time is None or end_time is None:
            raise ValueError("UNAVAILABLE_TIME_WINDOW requires both start_time and end_time")
        # Audit R4-01: the API's own full-hour parser is not this data
        # owner's only caller -- the write boundary itself must reject
        # sub-hour precision, matching the product's existing time-of-day
        # precision (brief.md section 10) without this implementation
        # extending it.
        for value in (start_time, end_time):
            if value.minute != 0 or value.second != 0 or value.microsecond != 0:
                raise ValueError(f"UNAVAILABLE_TIME_WINDOW requires a full hour 00:00-23:00, got {value}")
        if start_time >= end_time:
            raise ValueError(
                f"UNAVAILABLE_TIME_WINDOW requires start_time < end_time within the same day "
                f"(overnight windows are out of scope), got {start_time}-{end_time}"
            )
    elif start_time is not None or end_time is not None:
        raise ValueError(f"{kind.value} must not carry start_time/end_time")


def append_availability_version_in_open_transaction(
    conn: sqlite3.Connection, *, availability_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, active: bool, note: Optional[str] = None,
    start_time: Optional[time] = None, end_time: Optional[time] = None,
) -> AvailabilityRecord:
    """Same write as append_availability_version, without its own
    `with conn:` (ROTA-T019b atomicity)."""
    if end_date < start_date:
        raise ValueError("AvailabilityRecord.end_date must be >= start_date")
    _validate_time_window(kind, start_time, end_time)
    employee_row = conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    if employee_row is None:
        raise UnknownEmployeeForAvailability(employee_id)

    end_row = _current_chain_end(conn, availability_id)
    if end_row is None:
        predecessor_id, chain_seq = None, 0
    else:
        predecessor_id, predecessor_chain_seq, predecessor_employee_id = end_row
        if predecessor_employee_id != employee_id:
            raise InvalidAvailabilityChain(
                f"availability_id {availability_id!r} belongs to employee "
                f"{predecessor_employee_id!r}, not {employee_id!r}"
            )
        chain_seq = predecessor_chain_seq + 1

    availability_version_id = f"AV-{uuid.uuid4().hex}"
    conn.execute(
        """INSERT INTO availability_versions
           (availability_version_id, availability_id, employee_id, chain_seq, kind,
            start_date, end_date, active, supersedes_availability_version_id, note,
            start_time, end_time)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            availability_version_id, availability_id, employee_id, chain_seq, kind.value,
            start_date.isoformat(), end_date.isoformat(), int(active), predecessor_id, note,
            start_time.isoformat() if start_time is not None else None,
            end_time.isoformat() if end_time is not None else None,
        ),
    )

    return AvailabilityRecord(
        availability_id=availability_id, availability_version_id=availability_version_id,
        employee_id=employee_id, kind=kind, start_date=start_date, end_date=end_date,
        active=active, supersedes_availability_version_id=predecessor_id, note=note,
        start_time=start_time, end_time=end_time,
    )


def append_availability_version(
    conn: sqlite3.Connection, *, availability_id: str, employee_id: str, kind: AvailabilityKind,
    start_date: date, end_date: date, active: bool, note: Optional[str] = None,
    start_time: Optional[time] = None, end_time: Optional[time] = None,
) -> AvailabilityRecord:
    with conn:
        return append_availability_version_in_open_transaction(
            conn, availability_id=availability_id, employee_id=employee_id, kind=kind,
            start_date=start_date, end_date=end_date, active=active, note=note,
            start_time=start_time, end_time=end_time,
        )


def _row_to_record(row: tuple) -> AvailabilityRecord:
    (availability_id, availability_version_id, employee_id, kind, start_date,
     end_date, active, supersedes, note, start_time, end_time) = row
    return AvailabilityRecord(
        availability_id=availability_id, availability_version_id=availability_version_id,
        employee_id=employee_id, kind=AvailabilityKind(kind),
        start_date=date.fromisoformat(start_date), end_date=date.fromisoformat(end_date),
        active=bool(active), supersedes_availability_version_id=supersedes, note=note,
        start_time=time.fromisoformat(start_time) if start_time is not None else None,
        end_time=time.fromisoformat(end_time) if end_time is not None else None,
    )


_COLUMNS = (
    "availability_id, availability_version_id, employee_id, kind, start_date, "
    "end_date, active, supersedes_availability_version_id, note, start_time, end_time"
)


def get_availability_history(conn: sqlite3.Connection, availability_id: str) -> list[AvailabilityRecord]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM availability_versions WHERE availability_id = ? ORDER BY chain_seq ASC",
        (availability_id,),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def get_current_availability_for_employee(conn: sqlite3.Connection, employee_id: str) -> list[AvailabilityRecord]:
    """One row per availability_id family belonging to employee_id: the
    current chain end (regardless of active/inactive)."""
    rows = conn.execute(
        f"""SELECT {_COLUMNS} FROM availability_versions v
            WHERE employee_id = ? AND chain_seq = (
                SELECT MAX(chain_seq) FROM availability_versions
                WHERE availability_id = v.availability_id
            )
            ORDER BY availability_id""",
        (employee_id,),
    ).fetchall()
    return [_row_to_record(row) for row in rows]


def list_active_overlapping(
    conn: sqlite3.Connection, employee_id: str, range_start: date, range_end: date
) -> list[AvailabilityRecord]:
    """Current chain-end records for employee_id that are active and whose
    [start_date, end_date] overlaps the inclusive [range_start, range_end]."""
    current = get_current_availability_for_employee(conn, employee_id)
    return [
        record for record in current
        if record.active and record.start_date <= range_end and record.end_date >= range_start
    ]


def list_active_overlapping_for_employees(
    conn: sqlite3.Connection, employee_ids: list[str], range_start: date, range_end: date
) -> list[AvailabilityRecord]:
    """ROTA-T019: current chain-end records, active and overlapping
    [range_start, range_end], for a whole roster in one SELECT instead of
    one list_active_overlapping() call per employee."""
    if not employee_ids:
        return []
    placeholders = ",".join("?" for _ in employee_ids)
    rows = conn.execute(
        f"""SELECT {_COLUMNS} FROM availability_versions v
            WHERE employee_id IN ({placeholders}) AND chain_seq = (
                SELECT MAX(chain_seq) FROM availability_versions
                WHERE availability_id = v.availability_id
            )
            ORDER BY employee_id, availability_id""",
        (*employee_ids,),
    ).fetchall()
    current = [_row_to_record(row) for row in rows]
    return [
        record for record in current
        if record.active and record.start_date <= range_end and record.end_date >= range_start
    ]


if __name__ == "__main__":
    print("persistence.availability_repository module OK")
