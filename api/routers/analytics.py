"""Read-only wrap of rota.application.analytics_read -- ROTA-T021 §Analityka
i bilanse (arch/T021_spec.md). One application-level entry point already
exists (analytics_for_site_month); this router only marshals its dataclasses
to JSON, no new logic."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import get_conn
from api.errors import to_http_exception
from rota.application.analytics_read import analytics_for_site_month

router = APIRouter(prefix="/workspace", tags=["analytics"])


class AnalyticsMonthDataOut(BaseModel):
    month: str
    target_hours: int
    effective_target_hours: int
    planned_hours: int
    realized_hours: int
    month_balance: int
    quarter_balance: int | None
    unresolved_carryover: int | None


class EmployeeAnalyticsRowOut(BaseModel):
    employee_id: str
    display_name: str
    status: str
    month_data: AnalyticsMonthDataOut | None
    quarter_months: list[AnalyticsMonthDataOut]
    warnings: list[str]


class CoordinatorAnalyticsViewOut(BaseModel):
    site_id: str
    month: str
    quarter_first_month: str
    hours_scope: str
    rows: list[EmployeeAnalyticsRowOut]


def _month_data_out(md) -> AnalyticsMonthDataOut | None:
    if md is None:
        return None
    return AnalyticsMonthDataOut(
        month=md.month.isoformat(), target_hours=md.target_hours, effective_target_hours=md.effective_target_hours,
        planned_hours=md.planned_hours, realized_hours=md.realized_hours, month_balance=md.month_balance,
        quarter_balance=md.quarter_balance, unresolved_carryover=md.unresolved_carryover,
    )


@router.get("/sites/{site_id}/analytics", response_model=CoordinatorAnalyticsViewOut)
def get_analytics(site_id: str, month: str, conn=Depends(get_conn)) -> CoordinatorAnalyticsViewOut:
    try:
        view = analytics_for_site_month(conn, site_id=site_id, month=date.fromisoformat(month))
    except Exception as exc:
        raise to_http_exception(exc) from exc
    return CoordinatorAnalyticsViewOut(
        site_id=view.site_id, month=view.month.isoformat(), quarter_first_month=view.quarter_first_month.isoformat(),
        hours_scope=view.hours_scope.value,
        rows=[
            EmployeeAnalyticsRowOut(
                employee_id=row.employee_id, display_name=row.display_name, status=row.status.value,
                month_data=_month_data_out(row.month_data),
                quarter_months=[_month_data_out(m) for m in row.quarter_months],
                warnings=list(row.warnings),
            )
            for row in view.rows
        ],
    )


if __name__ == "__main__":
    print("api.routers.analytics module OK")
