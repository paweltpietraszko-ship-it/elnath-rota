"""ROTA-T056 -- monthly additional D6+/N6+ work codes (definable durations
for quarter-closing manual corrections). Brief: tasks/ROTA-T056/brief.md.

Covers: persistence/collision invariant on both write boundaries (T56-01/02/03),
unified action history (T56-04), the narrow _validate_item provenance
exception and its fail-closed negatives (T56-06/07/08), and export
mapping/sums/legend/revision (T56-09/12). Frontend (T56-05) and the two
REAL PDF GATE human-review artifacts (T56-13/14) are covered separately,
not by this file.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

import pytest

from rota.application import schedule_export as SE
from rota.application.durable_inputs import save_monthly_extra_work_codes
from rota.domain import ShiftKind
from rota.persistence.db import connect
from rota.persistence.site_repository import (
    InvalidSitePrintSettings,
    MonthlyExtraWorkCodes,
    WorkCodeInterval,
    get_site_monthly_extra_work_codes,
    save_site_monthly_extra_work_codes,
    save_site_print_settings,
)

import tests.test_t020 as T020

SEPT = date(2026, 9, 1)
OCT = date(2026, 10, 1)


def _conn_with_settings():
    conn = connect(":memory:")
    T020._seed(conn)
    save_site_print_settings(conn, T020._settings())
    return conn


# --- T56-01/02: per (site_id, month) persistence, independent months ---


def test_t56_01_definitions_persist_and_reload():
    conn = _conn_with_settings()
    codes = {"D6": WorkCodeInterval("06:00", "20:00", False), "N6": WorkCodeInterval("20:00", "06:00", True)}
    save_site_monthly_extra_work_codes(conn, MonthlyExtraWorkCodes("SITE-1", SEPT, codes))
    assert get_site_monthly_extra_work_codes(conn, "SITE-1", SEPT) == codes


def test_t56_02_months_are_independent():
    conn = _conn_with_settings()
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", SEPT, {"D6": WorkCodeInterval("06:00", "20:00", False)})
    )
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", OCT, {"D7": WorkCodeInterval("05:00", "22:00", False)})
    )
    assert get_site_monthly_extra_work_codes(conn, "SITE-1", SEPT) == {"D6": WorkCodeInterval("06:00", "20:00", False)}
    assert get_site_monthly_extra_work_codes(conn, "SITE-1", OCT) == {"D7": WorkCodeInterval("05:00", "22:00", False)}


# --- T56-03: shared signature-collision invariant, both write boundaries ---


def test_t56_03a_extra_code_colliding_with_standard_is_rejected():
    conn = _conn_with_settings()  # standard D1 = 06:00-18:00 (12h)
    with pytest.raises(InvalidSitePrintSettings):
        save_site_monthly_extra_work_codes(
            conn, MonthlyExtraWorkCodes("SITE-1", SEPT, {"D7": WorkCodeInterval("06:00", "18:00", False)})
        )
    assert get_site_monthly_extra_work_codes(conn, "SITE-1", SEPT) == {}


def test_t56_03b_standard_edit_colliding_with_saved_extra_is_rejected():
    conn = _conn_with_settings()
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", SEPT, {"D7": WorkCodeInterval("07:00", "19:00", False)})
    )
    colliding = replace(T020._settings(), work_code_intervals={
        **T020._default_intervals(), "D1": WorkCodeInterval("07:00", "19:00", False),
    })
    with pytest.raises(InvalidSitePrintSettings):
        save_site_print_settings(conn, colliding)
    # rejected write preserves the previous D1 interval
    from rota.persistence.site_repository import get_site_print_settings
    assert get_site_print_settings(conn, "SITE-1").work_code_intervals["D1"] == WorkCodeInterval("06:00", "18:00", False)


def test_t56_03c_bad_code_shape_and_duration_rejected():
    conn = _conn_with_settings()
    for bad_codes in (
        {"D1": WorkCodeInterval("07:00", "19:00", False)},  # not an extra slot
        {"N5": WorkCodeInterval("07:00", "19:00", False)},  # not an extra slot
        {"X6": WorkCodeInterval("07:00", "19:00", False)},  # bad family
        {"D6": WorkCodeInterval("07:00", "19:30", False)},  # non-integer hours
    ):
        with pytest.raises(InvalidSitePrintSettings):
            save_site_monthly_extra_work_codes(conn, MonthlyExtraWorkCodes("SITE-1", SEPT, bad_codes))


def test_t56_03d_two_extra_codes_same_month_colliding_signature_rejected():
    conn = _conn_with_settings()
    with pytest.raises(InvalidSitePrintSettings):
        save_site_monthly_extra_work_codes(conn, MonthlyExtraWorkCodes("SITE-1", SEPT, {
            "D7": WorkCodeInterval("07:00", "19:00", False),
            "D8": WorkCodeInterval("07:00", "19:00", False),
        }))


# --- T56-04: unified action history ---


def test_t56_04_save_records_context_configuration_saved_action():
    conn = _conn_with_settings()
    from rota.persistence.coordinator_repository import save_coordinator_site_association
    from rota.domain import CoordinatorSiteAssociation
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    save_monthly_extra_work_codes(
        conn, coordinator_id="COORD-1", site_id="SITE-1", month=SEPT,
        codes={"D6": WorkCodeInterval("06:00", "20:00", False)},
    )
    rows = conn.execute(
        "SELECT action_kind, month FROM coordinator_action_records WHERE origin_site_id = 'SITE-1'"
    ).fetchall()
    assert ("CONTEXT_CONFIGURATION_SAVED", "2026-09-01") in rows
    assert conn.execute("SELECT COUNT(*) FROM schedule_versions").fetchone()[0] == 0


# --- T56-06/07/08: the narrow _validate_item exception + fail-closed negatives ---


def _custom_duration_setup(conn, *, end_hour=23):
    demand, assignment = T020._work_item(1, 6, 18, kind=ShiftKind.D)  # 06:00-18:00, 12h
    custom = replace(assignment, end_datetime=datetime(2026, 8, 1, end_hour, 0))
    T020._create_version(conn, [demand], [custom])
    return demand, custom


def test_t56_07_exact_monthly_extra_match_is_accepted():
    conn = connect(":memory:")
    T020._seed(conn)
    save_site_print_settings(conn, T020._settings())
    _custom_duration_setup(conn)  # 06:00-23:00, 17h, same covers_demand_id as the 12h demand
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, {"D7": WorkCodeInterval("06:00", "23:00", False)})
    )
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="sierpien 2026")
    assert isinstance(result, SE.ExportReady)
    model = SE._assemble_export_model(conn, site_id="SITE-1", month=T020.MONTH, period_label="x")
    row = model.rows[0]
    assert row.plan[0] == "D7" and row.wyk[0] == "D7"
    assert row.wyk_hours == 17 and row.plan_hours == 17  # T56-09: never silently 0


@pytest.mark.parametrize(
    "mutate_extra",
    [
        lambda codes: {},  # no extra code defined at all
        lambda codes: {"N7": codes["D7"]},  # wrong family
        lambda codes: {"D7": WorkCodeInterval("07:00", "23:00", False)},  # start_time off by 1h
        lambda codes: {"D7": WorkCodeInterval("06:00", "22:00", False)},  # same start, different end (16h not 17h)
    ],
)
def test_t56_08_fail_closed_negatives(mutate_extra):
    conn = connect(":memory:")
    T020._seed(conn)
    save_site_print_settings(conn, T020._settings())
    _custom_duration_setup(conn)
    base = {"D7": WorkCodeInterval("06:00", "23:00", False)}
    extra = mutate_extra(base)
    if extra:
        save_site_monthly_extra_work_codes(conn, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, extra))
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="sierpien 2026")
    assert isinstance(result, SE.ExportProblem)
    assert result.problem_code == "WORK_PROVENANCE_INCOMPLETE"


def test_t56_08_same_duration_different_clock_still_rejected():
    # T56-08: a same-DURATION (17h) but different-clock-time extra code must
    # not match -- the exception is exact-interval, never duration-only.
    conn = connect(":memory:")
    T020._seed(conn)
    save_site_print_settings(conn, T020._settings())
    _custom_duration_setup(conn)  # real interval 06:00-23:00
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, {"D7": WorkCodeInterval("05:00", "22:00", False)})  # also 17h, different clock
    )
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="sierpien 2026")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "WORK_PROVENANCE_INCOMPLETE"


# --- T56-12: solver/catalog/WorkBalance/analytics untouched (no such imports here) ---


# --- R8 audit fixes (2026-09-05): atomicity, exact end_next_day, oversized legend ---


def test_t56_r8_01_atomic_write_rolls_back_config_on_action_failure():
    from rota.domain import CoordinatorSiteAssociation
    from rota.persistence.coordinator_repository import save_coordinator_site_association

    conn = _conn_with_settings()
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    conn.execute(
        "CREATE TRIGGER inject_action_failure BEFORE INSERT ON coordinator_action_records "
        "BEGIN SELECT RAISE(ABORT, 'injected action failure'); END"
    )
    conn.commit()
    with pytest.raises(Exception):
        save_monthly_extra_work_codes(
            conn, coordinator_id="COORD-1", site_id="SITE-1", month=SEPT,
            codes={"D6": WorkCodeInterval("06:00", "20:00", False)},
        )
    assert get_site_monthly_extra_work_codes(conn, "SITE-1", SEPT) == {}
    assert conn.execute("SELECT COUNT(*) FROM coordinator_action_records").fetchone()[0] == 0


def test_t56_r8_02_end_next_day_requires_exactly_one_day_not_any_later_day():
    # A 65h Assignment must NOT match a 41h (end_next_day=True) definition --
    # both merely "cross midnight", but end_next_day means exactly one day.
    conn = connect(":memory:")
    T020._seed(conn)
    save_site_print_settings(conn, T020._settings())
    demand, assignment = T020._work_item(1, 6, 18, kind=ShiftKind.D)
    too_long = replace(assignment, end_datetime=datetime(2026, 8, 3, 23, 0))  # 65h
    T020._create_version(conn, [demand], [too_long])
    save_site_monthly_extra_work_codes(
        conn, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, {"D7": WorkCodeInterval("06:00", "23:00", True)})  # 41h
    )
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="x")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "WORK_PROVENANCE_INCOMPLETE"

    # the genuine, exactly-one-day-later match must still be accepted
    conn2 = connect(":memory:")
    T020._seed(conn2)
    save_site_print_settings(conn2, T020._settings())
    demand2, assignment2 = T020._work_item(1, 6, 18, kind=ShiftKind.D)
    exact = replace(assignment2, end_datetime=datetime(2026, 8, 2, 23, 0))  # exactly next day, 41h
    T020._create_version(conn2, [demand2], [exact])
    save_site_monthly_extra_work_codes(
        conn2, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, {"D7": WorkCodeInterval("06:00", "23:00", True)})
    )
    result2 = SE.generate_schedule_pdf(conn2, site_id="SITE-1", month=T020.MONTH, period_label="x")
    assert isinstance(result2, SE.ExportReady)
    model2 = SE._assemble_export_model(conn2, site_id="SITE-1", month=T020.MONTH, period_label="x")
    assert model2.rows[0].wyk_hours == 41 and model2.rows[0].wyk[0] == "D7"


def test_t56_r8_04_oversized_legend_fails_closed_instead_of_truncating():
    from datetime import timedelta

    from rota.domain import Assignment, AssignmentRole, AssignmentState, ShiftCatalogKind, ShiftDemand

    n = 130
    conn = connect(":memory:")
    T020._seed(conn, employees=tuple(f"EMP-{i}" for i in range(1, n + 1)))
    save_site_print_settings(conn, T020._settings())
    combos = [(h, d) for h in range(0, 24) for d in range(1, 24)][:n]
    demands, assignments, extras = [], [], {}
    for i, (start_h, dur) in enumerate(combos, start=1):
        day = (i % 28) + 1
        demand_start = datetime(2026, 8, day, 6, 0)
        start = datetime(2026, 8, day, start_h, 0)
        end = start + timedelta(hours=dur)
        sig = (start.strftime("%H:%M"), end.strftime("%H:%M"), end.date() > start.date())
        demands.append(ShiftDemand(f"DEM-{i}", "", demand_start, demand_start + timedelta(hours=12), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12))
        assignments.append(Assignment(f"ASG-{i}", "", f"EMP-{i}", start, end, AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, f"DEM-{i}", None))
        extras[f"D{i + 5}"] = WorkCodeInterval(*sig)
    T020._create_version(conn, demands, assignments)
    save_site_monthly_extra_work_codes(conn, MonthlyExtraWorkCodes("SITE-1", T020.MONTH, extras))
    result = SE.generate_schedule_pdf(conn, site_id="SITE-1", month=T020.MONTH, period_label="x")
    assert isinstance(result, SE.ExportProblem) and result.problem_code == "ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT"


def test_t56_12_schedule_export_never_imports_solver_or_shift_catalog():
    import ast
    source = open("rota/application/schedule_export.py", encoding="utf-8").read()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "rota.planning.solver" not in imported
    assert "rota.planning.shift_catalog" not in imported
