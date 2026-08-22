"""Independent implementation audit probes for ROTA-T023 Checkpoint B."""
from dataclasses import replace
from datetime import date

import pytest

from rota.application import plan_ops
from rota.application.errors import CandidateRejected
from rota.application.store import open_store
from rota.domain import AssignmentState, AvailabilityKind
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.work_balance_repository import (
    absence_facts_for_employee,
    absence_facts_for_employees,
)
from rota.planning.absence import IncompleteAbsenceReferenceError
from tests.test_t023 import COORDINATOR, SITE, _employee, _setup
from tests.test_t023_checkpoint_b import PAST, PAST_END, PAST_MONTH, _seed_parent_and_child


@pytest.mark.parametrize("batch", [False, True])
def test_b_audit_legacy_active_absence_without_snapshot_fails_closed(tmp_path, batch) -> None:
    conn = _setup(tmp_path)
    append_availability_version(
        conn,
        availability_id="AV-LEGACY",
        employee_id="A",
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2020, 1, 6),
        end_date=date(2020, 1, 6),
        active=True,
    )

    with pytest.raises(IncompleteAbsenceReferenceError):
        if batch:
            absence_facts_for_employees(conn, ["A"], date(2020, 1, 1), date(2020, 1, 31))
        else:
            absence_facts_for_employee(conn, "A", date(2020, 1, 1), date(2020, 1, 31))


def test_b_audit_cutover_check_uses_snapshot_inside_atomic_write(tmp_path, monkeypatch) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _, prior = _seed_parent_and_child(
        conn,
        prior_facts=[
            ("D-PAST", "A-PAST", "A", PAST, PAST_END, AssignmentState.PLANNED),
        ],
        month=PAST_MONTH,
    )
    candidate = list(prior)
    original_replace = plan_ops.lifecycle.replace_working_snapshot

    def interleaved_replace(open_conn, **kwargs):
        original_replace(
            open_conn,
            version_id=kwargs["version_id"],
            applied_rule_version_ids=kwargs["applied_rule_version_ids"],
            shift_demands=kwargs["shift_demands"],
            assignments=[replace(prior[0], employee_id="B")],
            deviations=[],
        )
        return original_replace(open_conn, **kwargs)

    monkeypatch.setattr(plan_ops.lifecycle, "replace_working_snapshot", interleaved_replace)
    with pytest.raises(CandidateRejected, match="pre-cutover PRIMARY"):
        plan_ops.select_candidate(
            conn,
            site_id=SITE,
            month=PAST_MONTH,
            candidate=candidate,
            coordinator_id=COORDINATOR,
        )


def test_b_audit_cutover_read_cannot_go_stale_before_first_write(tmp_path, monkeypatch) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _, prior = _seed_parent_and_child(
        conn,
        prior_facts=[
            ("D-PAST", "A-PAST", "A", PAST, PAST_END, AssignmentState.PLANNED),
        ],
        month=PAST_MONTH,
    )
    candidate = list(prior)
    original_get = plan_ops.get_schedule_snapshot
    original_replace = plan_ops.lifecycle.replace_working_snapshot
    database_path = conn.execute("PRAGMA database_list").fetchone()[2]
    concurrent_conn = open_store(database_path)

    def interleaved_get(open_conn, version_id):
        stale_snapshot = original_get(open_conn, version_id)
        original_replace(
            concurrent_conn,
            version_id=version_id,
            applied_rule_version_ids=[],
            shift_demands=stale_snapshot.shift_demands,
            assignments=[replace(prior[0], employee_id="B")],
            deviations=[],
        )
        return stale_snapshot

    monkeypatch.setattr(plan_ops, "get_schedule_snapshot", interleaved_get)
    try:
        with pytest.raises(CandidateRejected, match="pre-cutover PRIMARY"):
            plan_ops.select_candidate(
                conn,
                site_id=SITE,
                month=PAST_MONTH,
                candidate=candidate,
                coordinator_id=COORDINATOR,
            )
    finally:
        concurrent_conn.close()
