"""Final narrow R10-1 sibling check for ROTA-T020 product 6872f6e."""
from datetime import datetime, timedelta

import pytest

from rota.application import schedule_export as export
from rota.domain import ShiftCatalogKind, ShiftDemand, ShiftKind


@pytest.mark.parametrize("first_hours,second_hours", [(6, 18), (18, 6)])
def test_round11_normal_h24_requires_two_exact_12h_components(
    first_hours: int,
    second_hours: int,
) -> None:
    start = datetime(2026, 8, 5, 6)
    middle = start + timedelta(hours=first_hours)
    end = middle + timedelta(hours=second_hours)
    first = ShiftDemand(
        "D",
        "",
        start,
        middle,
        1,
        shift_kind=ShiftKind.D,
        catalog_kind=ShiftCatalogKind.H24,
        work_period_template_id="TPL",
        work_period_component=1,
    )
    second = ShiftDemand(
        "N",
        "",
        middle,
        end,
        1,
        shift_kind=ShiftKind.N,
        catalog_kind=ShiftCatalogKind.H24,
        work_period_template_id="TPL",
        work_period_component=2,
    )

    assert export._is_legitimate_normal_24h(first, second, 24) is False
