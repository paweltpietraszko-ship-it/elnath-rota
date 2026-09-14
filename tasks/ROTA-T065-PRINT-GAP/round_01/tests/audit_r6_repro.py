"""Independent R6 reproducer for PRINT-GAP on exact implementation 3fa2941.

The frozen role contract says a new ScheduleVersion snapshots positions for
people belonging to the Site. PRINT-GAP then promises one historical position
under every ORDINARY employee name. This exercises the ordinary case where a
current local employee has a valid position but no assignment in this version.
"""

import calendar
from datetime import date, datetime, timedelta

from rota.application import schedule_export
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    CoordinatorSiteAssociation,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    SiteMembership,
    SiteRoleDefinition,
)
from rota.persistence import schedule_lifecycle
from rota.persistence.coordinator_repository import save_coordinator_site_association
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_site_membership
from rota.persistence.site_repository import SitePrintSettings, save_site_print_settings
from rota.persistence.site_role_repository import save_site_role
from tests.support.t008_fixtures import seed_base_entities


MONTH = date(2026, 8, 1)


def test_zero_assignment_local_employee_keeps_historical_position_on_print() -> None:
    conn = connect(":memory:")
    seed_base_entities(conn, site_id="SITE-1", employee_id="EMP-WORKS")
    save_coordinator_site_association(conn, CoordinatorSiteAssociation("COORD-1", "SITE-1", True))
    save_site_role(conn, SiteRoleDefinition("ROLE-KIER", "SITE-1", "Kierownik", True))

    # Both people are ordinary local employees with one valid position. Only
    # the first gets work in this ScheduleVersion; the second is still printed
    # as a roster row and must retain the historical position under the name.
    from rota.domain import Employee
    from rota.persistence.employee_repository import save_employee

    save_employee(conn, Employee("EMP-NO-WORK", "Anna Bez Zmiany", date(2026, 1, 1), None, False))
    for employee_id in ("EMP-WORKS", "EMP-NO-WORK"):
        save_site_membership(
            conn,
            SiteMembership(
                employee_id,
                "SITE-1",
                MembershipKind.LOCAL,
                True,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
                True,
                position_role_id="ROLE-KIER",
            ),
        )
    for offset in range(calendar.monthrange(MONTH.year, MONTH.month)[1]):
        save_calendar_day(conn, CalendarDay(MONTH + timedelta(days=offset), False))

    save_site_print_settings(
        conn,
        SitePrintSettings(
            site_id="SITE-1",
            company_print_name="Firma",
            site_print_name="Sklep",
            base_regime="12h",
            work_code_intervals={},
            reserve_hours={},
        ),
    )

    start = datetime(2026, 8, 3, 5)
    end = datetime(2026, 8, 3, 12)
    demand = ShiftDemand(
        "DEM-1",
        "",
        start,
        end,
        1,
        required_role_id="ROLE-KIER",
        required_role_name="Kierownik",
    )
    assignment = Assignment(
        "ASG-1",
        "",
        "EMP-WORKS",
        start,
        end,
        AssignmentRole.PRIMARY,
        AssignmentState.REALIZED,
        False,
        "DEM-1",
        None,
    )
    schedule_lifecycle.create_schedule_version(
        conn,
        version_id="SV-1",
        site_id="SITE-1",
        month=MONTH,
        parent_version_id=None,
        created_at=datetime(2026, 7, 31, 8),
        created_by="COORD-1",
        applied_rule_version_ids=[],
        shift_demands=[demand],
        assignments=[assignment],
        deviations=[],
        effective_from=MONTH,
    )

    model = schedule_export._assemble_export_model(
        conn, site_id="SITE-1", month=MONTH, period_label="Sierpień 2026"
    )
    row = next(row for row in model.ordinary_rows if row.employee_id == "EMP-NO-WORK")
    result = schedule_export.generate_schedule_pdf(
        conn, site_id="SITE-1", month=MONTH, period_label="Sierpień 2026"
    )
    assert isinstance(result, schedule_export.ExportReady)
    assert result.pdf_bytes.startswith(b"%PDF")  # the public pipeline reaches the real renderer
    assert row.position_label == "Kierownik"
