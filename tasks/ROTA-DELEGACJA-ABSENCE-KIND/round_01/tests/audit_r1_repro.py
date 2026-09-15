from datetime import date, datetime

from rota.application.schedule_export import _build_ordinary_rows
from rota.domain import AvailabilityKind, AvailabilityRecord, Employee


def test_print_does_not_block_a_recorded_manual_assignment_on_delegation_day():
    day = date(2026, 10, 5)
    employee = Employee("E1", "Jan", date(2020, 1, 1), None, False)
    delegation = AvailabilityRecord(
        "DEL-1", "DEL-V1", "E1", AvailabilityKind.DELEGACJA,
        day, day, True, None, None, delegation_hours=7,
    )

    rows = _build_ordinary_rows(
        {"E1"}, {"E1": employee}, [day],
        {"E1": {day: [(datetime(2026, 10, 5, 12), datetime(2026, 10, 5, 19), "A1")]}},
        {}, {"E1": [delegation]}, {},
    )

    assert rows
