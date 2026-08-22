"""Independent adversarial matrix for ROTA-T023 Checkpoint A @ f92c8b7."""
import json
from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.domain import AvailabilityKind, MembershipKind, ShiftCatalogKind, ShiftKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import absence_reference_repository as reference_repository
from rota.persistence.absence_reference_repository import get_absence_reference_snapshot
from rota.persistence.schedule_repository import InvalidScheduleVersionLineage
from rota.planning.absence import DailyAbsenceFact, canonical_hours_in_range
from tests.test_t023 import (
    _accept_one,
    _accept_two,
    _accept_version,
    _employee,
    _leave,
    _primary,
    _seed_full_month_calendar,
    _setup,
    _setup_two_sites,
)


def _canonical_total(snapshot, kind: AvailabilityKind) -> int:
    facts = [
        DailyAbsenceFact(day.the_date, kind, day.source_mode, day.status, day.hours)
        for day in snapshot.days
    ]
    return canonical_hours_in_range(facts, snapshot.days[0].the_date, snapshot.days[-1].the_date)


def test_a1_pre_plan_owner_example_is_really_40_hours(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, date(2027, 3, 8), date(2027, 3, 12))
    record = _leave(
        conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 12),
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert _canonical_total(snapshot, AvailabilityKind.LEAVE_GRANTED) == 40


def test_a2_same_chain_extension_keeps_predecessor_bound_day_after_current_mutation(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _accept_two(
        conn,
        ("D-8", "A-8", "A", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17)),
        ("D-9", "A-9", "A", datetime(2027, 3, 9, 5), datetime(2027, 3, 9, 17)),
    )
    first = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-CHAIN",
    )
    first_snapshot = get_absence_reference_snapshot(conn, first.availability_version_id)
    d8, b8 = _primary("D-8", "B-8", "B", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17), version_id="SV-1")
    d9, a9 = _primary("D-9", "A-9", "A", datetime(2027, 3, 9, 5), datetime(2027, 3, 9, 17), version_id="SV-1")
    lifecycle.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[],
        shift_demands=[d8, d9], assignments=[b8, a9], deviations=[],
    )
    extended = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 9), availability_id="AV-CHAIN",
    )
    extended_snapshot = get_absence_reference_snapshot(conn, extended.availability_version_id)
    assert extended_snapshot.days[0] == first_snapshot.days[0]


def test_a3_new_sick_chain_reuses_pre_replan_leave_reference(tmp_path) -> None:
    conn = _setup(tmp_path)
    _employee(conn, "B")
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17))
    _seed_full_month_calendar(conn, date(2027, 3, 8), date(2027, 3, 8))
    leave = _leave(
        conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-LEAVE",
    )
    original = get_absence_reference_snapshot(conn, leave.availability_version_id)
    demand, replacement = _primary(
        "D-8", "B-8", "B", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17), version_id="SV-1",
    )
    lifecycle.replace_working_snapshot(
        conn, version_id="SV-1", applied_rule_version_ids=[],
        shift_demands=[demand], assignments=[replacement], deviations=[],
    )
    sick = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-SICK",
    )
    later = get_absence_reference_snapshot(conn, sick.availability_version_id)
    assert later.days[0] == original.days[0]


def test_a4_broken_accepted_lineage_is_not_downgraded_to_pre_plan_leave(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, date(2027, 3, 8), date(2027, 3, 8))
    _accept_version(
        conn, version_id="SV-BROKEN", pairs=[], effective_from=None,
        accepted_at=datetime(2020, 3, 1, 8),
    )
    with pytest.raises(InvalidScheduleVersionLineage):
        _leave(
            conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2027, 3, 8), end_date=date(2027, 3, 8),
        )


def test_a5_missing_required_local_site_is_not_silently_ignored(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path)
    _accept_one(
        conn, "D-A", "A-A", "A", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17),
        version_id="SV-A", site_id="SITE-A",
    )
    _accept_version(
        conn, version_id="SV-B-TECHNICAL", pairs=[], effective_from=date(2027, 3, 1),
        accepted_at=datetime(2020, 3, 1, 8), site_id="SITE-B", record_action=False,
    )
    record = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A",
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_status == "MISSING"
    assert snapshot.days[0].status == "MISSING"


def test_a6_unrelated_old_external_work_does_not_expand_march_reference_scope(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.EXTERNAL_SUPPORT)
    _accept_one(
        conn, "D-A", "A-A", "A", datetime(2027, 3, 8, 5), datetime(2027, 3, 8, 17),
        version_id="SV-A", site_id="SITE-A",
    )
    _accept_one(
        conn, "D-OLD", "A-OLD", "A", datetime(2027, 1, 8, 5), datetime(2027, 1, 8, 17),
        version_id="SV-B-OLD", site_id="SITE-B", month=date(2027, 1, 1), effective_from=date(2027, 1, 1),
    )
    record = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A",
    )
    snapshot = get_absence_reference_snapshot(conn, record.availability_version_id)
    assert snapshot.reference_site_scope == ("SITE-A",)


def test_a7_snapshot_freezes_demand_and_work_period_component_provenance(tmp_path) -> None:
    conn = _setup(tmp_path)
    demand, assignment = _primary(
        "D-N", "A-N", "A", datetime(2027, 3, 8, 17), datetime(2027, 3, 9, 5),
        version_id="SV-1", work_period_id="WP-N", required_rest_after_hours=11,
    )
    demand = replace(
        demand, shift_kind=ShiftKind.N, catalog_kind=ShiftCatalogKind.H12,
        required_rest_hours=11, work_period_template_id="WPT-N", work_period_component=1,
    )
    _accept_version(
        conn, version_id="SV-1", pairs=[(demand, assignment)],
        effective_from=date(2027, 3, 1), accepted_at=datetime(2020, 3, 1, 8),
    )
    record = _leave(
        conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 8), end_date=date(2027, 3, 8),
    )
    raw = json.loads(conn.execute(
        "SELECT snapshot_json FROM absence_reference_snapshots WHERE availability_version_id = ?",
        (record.availability_version_id,),
    ).fetchone()[0])
    period = raw["days"][0]["periods"][0]
    assert period["shift_kind"] == "N"
    assert period["catalog_kind"] == "12h"
    assert period["required_rest_hours"] == 11
    assert period["work_period_template_id"] == "WPT-N"
    assert period["work_period_component"] == 1


def test_a8_real_snapshot_insert_failure_rolls_back_entire_command(tmp_path, monkeypatch) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, date(2027, 3, 8), date(2027, 3, 8))

    def fail_snapshot_insert(*_args, **_kwargs):
        raise RuntimeError("forced snapshot insert failure")

    monkeypatch.setattr(
        reference_repository, "save_absence_reference_snapshot_in_open_transaction", fail_snapshot_insert,
    )
    with pytest.raises(RuntimeError, match="forced snapshot insert failure"):
        _leave(
            conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-ATOMIC",
        )
    assert conn.execute(
        "SELECT COUNT(*) FROM availability_versions WHERE availability_id = 'AV-ATOMIC'",
    ).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM absence_reference_snapshots").fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM coordinator_action_records WHERE source_id LIKE 'AV-%'",
    ).fetchone()[0] == 0
