"""ROTA-EXCEL-VBA-ENGINE-ADAPTER brief.md sections 4/6: a thin external
router for the Excel/VBA add-in -- orchestrates the SAME existing
write-owners (durable_inputs.set_target_hours/append_availability) and
the SAME existing PLAN/REPLAN/select_candidate lifecycle the React
frontend uses. No second solver/validator/persistence path; no new
ledger. Mounted only for IS_CENTRAL_SERVICE (api/main.py), authenticated
by API key (api/auth/api_key.py) rather than the browser cookie.

Section 6.1: candidate_id is a hash of the CURRENT server-side
PlanPreview's own Assignment lists -- never trusts an Assignment list
from the client. Section 3.4/3.5: the day-by-day grid shown to the
coordinator reuses the exact D/N/S1/DEL cell convention MonthlyPlanning.
tsx's own ScheduleGrid already renders for PLAN/REPLAN candidates --
not a second classification, just this router's own JSON shape for it.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import sqlite3
from collections.abc import Iterator
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.auth.api_key import get_authenticated_context_by_api_key
from api.auth.context import AuthenticatedContext
from api.errors import to_http_exception
from rota.application import schedule_projection
from rota.application.durable_inputs import append_availability, set_target_hours
from rota.application.errors import CandidateRejected, ReplanNotAvailableAfterAcceptance
from rota.application.plan_ops import TargetHoursRequired, plan_month, replan, select_candidate
from rota.domain import Assignment, AvailabilityKind, MembershipKind
from rota.persistence.availability_repository import _validate_delegation_hours, _validate_time_window, get_availability_history
from rota.persistence.coordinator_repository import CoordinatorNotFound, get_coordinator, save_coordinator
from rota.persistence.db import connect
from rota.persistence.employee_repository import list_employees_by_ids, list_memberships_for_site
from rota.persistence.plan_preview_repository import get_plan_preview
from rota.persistence.schedule_repository import get_current_schedule_snapshot
from rota.persistence.work_balance_repository import delegation_records_for_employees, get_work_balance_target
from rota.domain import Coordinator

router = APIRouter(prefix="/external/excel", tags=["excel"])


# --- auth-scoped conn/coordinator, mirroring api/deps.py's CENTRAL_SERVICE
# branch but keyed off the API-key context instead of the cookie one ------


def get_conn_excel(context: AuthenticatedContext = Depends(get_authenticated_context_by_api_key)) -> Iterator[sqlite3.Connection]:
    conn = connect(context.db_path)
    try:
        get_coordinator(conn, context.coordinator_id)
    except CoordinatorNotFound:
        save_coordinator(conn, Coordinator(coordinator_id=context.coordinator_id, display_name="Koordynator", active=True))
    try:
        yield conn
    finally:
        conn.close()


def get_coordinator_id_excel(context: AuthenticatedContext = Depends(get_authenticated_context_by_api_key)) -> str:
    return context.coordinator_id


# --- request/response DTOs (brief.md section 3/4) -------------------------


class TargetHoursInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: str
    target_hours: int = Field(ge=0)


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    availability_id: str
    employee_id: str
    kind: str
    start_date: str
    end_date: str
    start_time: str | None = None
    end_time: str | None = None
    delegation_hours: int | None = None
    active: bool


class ExcelMonthlyInputRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    month: str
    target_hours: list[TargetHoursInput] = []
    availability: list[AvailabilityInput] = []


class ExcelScheduleRowOut(BaseModel):
    employee_id: str
    pseudonym: str
    days: list[str]
    total_hours: int


class ExcelCandidateOut(BaseModel):
    candidate_id: str
    candidate_no: int
    rows: list[ExcelScheduleRowOut]


class ExcelBlockerOut(BaseModel):
    # brief.md section 9: co blokuje / kogo dotyczy / co dalej, w jednym
    # gotowym polskim zdaniu -- nigdy sam kod/status jako jedyna treść.
    message: str
    employee_ids: list[str] = []


class ExcelPlanResultOut(BaseModel):
    status: str
    candidates: list[ExcelCandidateOut] = []
    blocker: ExcelBlockerOut | None = None


class ExcelSelectCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    month: str
    candidate_id: str


class ExcelScheduleOut(BaseModel):
    rows: list[ExcelScheduleRowOut]


def _parse_month(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Nieprawidłowy miesiąc: {value!r}") from exc
    if parsed.day != 1:
        raise HTTPException(status_code=400, detail="Miesiąc musi być podany jako pierwszy dzień (RRRR-MM-01).")
    return parsed


def _month_end(month: date) -> date:
    return date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])


# --- section 4.2: roster gate, whole payload validated before any write --


def _active_local_employee_ids(conn: sqlite3.Connection, site_id: str) -> set[str]:
    return {
        m.employee_id for m in list_memberships_for_site(conn, site_id)
        if m.enabled and m.membership_kind == MembershipKind.LOCAL
    }


def _validate_roster_gate(conn: sqlite3.Connection, site_id: str, payload: ExcelMonthlyInputRequest) -> None:
    local_ids = _active_local_employee_ids(conn, site_id)
    foreign = {t.employee_id for t in payload.target_hours if t.employee_id not in local_ids}
    foreign |= {a.employee_id for a in payload.availability if a.employee_id not in local_ids}
    if foreign:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pracownik spoza aktywnej obsady tego obiektu: "
                f"{', '.join(sorted(foreign))}. Żadne dane nie zostały zapisane."
            ),
        )


def _validate_payload_shape(payload: ExcelMonthlyInputRequest) -> None:
    """brief.md section 4.2/XL-18/XL-19: the WHOLE payload -- every enum,
    date, and time -- is validated before the first write, not discovered
    mid-reconciliation. Codex R5-02/R6-02: parsability alone is not enough
    -- an inverted date range (end before start) or a kind/field
    combination the write owner would reject (e.g. UNAVAILABLE_TIME_
    WINDOW without both times, DELEGACJA without a positive
    delegation_hours) must also fail before the first write, not after an
    earlier row already committed. Reuses the EXACT semantic checks the
    real write owner (append_availability_version_in_open_transaction)
    runs, never a second, looser copy of them."""
    for item in payload.availability:
        try:
            kind = AvailabilityKind(item.kind)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Nieprawidłowy rodzaj nieobecności {item.kind!r} w rekordzie {item.availability_id!r}. Żadne dane nie zostały zapisane.",
            ) from exc
        try:
            start_date = date.fromisoformat(item.start_date)
            end_date = date.fromisoformat(item.end_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Nieprawidłowa data w rekordzie {item.availability_id!r}. Żadne dane nie zostały zapisane.",
            ) from exc
        try:
            start_time = _parse_hh_mm(item.start_time)
            end_time = _parse_hh_mm(item.end_time)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Nieprawidłowa godzina w rekordzie {item.availability_id!r}. Żadne dane nie zostały zapisane.",
            ) from exc
        try:
            if end_date < start_date:
                raise ValueError("end_date must be >= start_date")
            _validate_time_window(kind, start_time, end_time)
            _validate_delegation_hours(kind, item.delegation_hours)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"Nieprawidłowy zakres w rekordzie {item.availability_id!r}: {exc}. Żadne dane nie zostały zapisane.",
            ) from exc


# --- section 4.3: idempotent reconciler, no new ledger ---------------------


def _availability_semantic_state(record) -> tuple:
    return (
        record.employee_id, record.kind.value, record.start_date.isoformat(), record.end_date.isoformat(),
        record.start_time.isoformat() if record.start_time else None,
        record.end_time.isoformat() if record.end_time else None,
        record.delegation_hours, record.active,
    )


def _availability_input_state(item: AvailabilityInput) -> tuple:
    return (
        item.employee_id, item.kind, item.start_date, item.end_date,
        item.start_time, item.end_time, item.delegation_hours, item.active,
    )


def _apply_monthly_inputs(conn: sqlite3.Connection, *, coordinator_id: str, site_id: str, month: date, payload: ExcelMonthlyInputRequest) -> None:
    for item in payload.target_hours:
        current = get_work_balance_target(conn, item.employee_id, month)
        if current == item.target_hours:
            continue
        set_target_hours(conn, coordinator_id=coordinator_id, site_id=site_id, employee_id=item.employee_id, month=month, target_hours=item.target_hours)
    for item in payload.availability:
        history = get_availability_history(conn, item.availability_id)
        latest = history[-1] if history else None
        if latest is not None and _availability_semantic_state(latest) == _availability_input_state(item):
            continue
        append_availability(
            conn, coordinator_id=coordinator_id, site_id=site_id, availability_id=item.availability_id,
            employee_id=item.employee_id, kind=AvailabilityKind(item.kind),
            start_date=date.fromisoformat(item.start_date), end_date=date.fromisoformat(item.end_date),
            active=item.active,
            start_time=_parse_hh_mm(item.start_time), end_time=_parse_hh_mm(item.end_time),
            delegation_hours=item.delegation_hours,
        )


def _parse_hh_mm(value: str | None):
    if value is None:
        return None
    from datetime import time as _time

    hour, _, minute = value.partition(":")
    return _time(int(hour), int(minute or 0))


# --- section 3.4/3.5/8/XL-12: day-grid for PLAN/REPLAN candidates and the
# accepted schedule, delegated entirely to the shared projection owner
# (rota.application.schedule_projection) -- Codex R5-01: an earlier,
# router-local implementation kept only the LAST same-day Assignment per
# employee, silently discarding real worked hours whenever an employee had
# more than one legal, non-overlapping Assignment on the same day. This
# thin wrapper exists only so callers keep this module's own name.


def _candidate_day_grid(
    candidate: list[Assignment], demands_by_id: dict, days: list[date],
    delegation_by_employee: dict[str, list],
) -> dict[str, tuple[list[str], int]]:
    # Kept for direct callers with only a bare Assignment list and no
    # database (e.g. a unit-level check of the same-day merge behavior) --
    # real endpoint code below calls build_ad_hoc_day_grid directly with
    # conn/site_id/local_ids so absence also projects correctly (Codex
    # R6-01).
    return schedule_projection.build_ad_hoc_day_grid(candidate, demands_by_id, days, delegation_by_employee)


def _candidate_id(candidate: list[Assignment]) -> str:
    facts = sorted(
        [
            a.employee_id, a.start_datetime.isoformat(), a.end_datetime.isoformat(), a.role.value, a.state.value,
            a.covers_demand_id, a.operational_code, a.work_period_id, a.required_rest_after_hours,
            a.manual_work_role_id, a.manual_work_role_name, a.frozen,
        ]
        for a in candidate
    )
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pseudonyms(conn: sqlite3.Connection, employee_ids: set[str]) -> dict[str, str]:
    employees = list_employees_by_ids(conn, list(employee_ids))
    return {eid: (employees[eid].display_name if eid in employees else eid) for eid in employee_ids}


def _candidates_out(conn: sqlite3.Connection, site_id: str, month: date, candidates: list[list[Assignment]], demands_by_id: dict) -> list[ExcelCandidateOut]:
    days = [date(month.year, month.month, d) for d in range(1, calendar.monthrange(month.year, month.month)[1] + 1)]
    local_ids = _active_local_employee_ids(conn, site_id)
    delegation_by_employee = delegation_records_for_employees(conn, list(local_ids), days[0], days[-1]) if local_ids else {}
    delegation_by_employee = {eid: [r for r in recs if r.kind == AvailabilityKind.DELEGACJA] for eid, recs in delegation_by_employee.items()}
    out = []
    for i, candidate in enumerate(candidates, start=1):
        grid = schedule_projection.build_ad_hoc_day_grid(
            candidate, demands_by_id, days, delegation_by_employee,
            conn=conn, site_id=site_id, local_ids=local_ids,
        )
        all_ids = local_ids | set(grid)
        pseudonyms = _pseudonyms(conn, all_ids)
        rows = []
        for employee_id in sorted(all_ids, key=lambda eid: (pseudonyms[eid].casefold(), eid)):
            cells, total_hours = grid.get(employee_id, ([""] * len(days), 0))
            rows.append(ExcelScheduleRowOut(employee_id=employee_id, pseudonym=pseudonyms[employee_id], days=cells, total_hours=total_hours))
        out.append(ExcelCandidateOut(candidate_id=_candidate_id(candidate), candidate_no=i, rows=rows))
    return out


def _target_hours_required_blocker(conn: sqlite3.Connection, exc: TargetHoursRequired) -> ExcelPlanResultOut:
    names = _pseudonyms(conn, set(exc.employee_ids))
    listed = ", ".join(names[eid] for eid in exc.employee_ids)
    return ExcelPlanResultOut(
        status="TARGET_HOURS_REQUIRED",
        blocker=ExcelBlockerOut(
            message=f"Brakuje celu godzinowego dla: {listed}. Wpisz cel w kolumnie Godziny i wybierz Przelicz.",
            employee_ids=list(exc.employee_ids),
        ),
    )


def _result_out(conn: sqlite3.Connection, site_id: str, month: date, result) -> ExcelPlanResultOut:
    if result.status == "FEASIBLE":
        demands_by_id: dict = {}
        preview = get_plan_preview(conn, site_id, month)
        if preview is not None:
            demands_by_id = {d.demand_id: d for d in preview.shift_demands}
        return ExcelPlanResultOut(status=result.status, candidates=_candidates_out(conn, site_id, month, result.candidates, demands_by_id))
    if result.status == "DECISION_REQUIRED" and result.decision_payload is not None and result.decision_payload.unblocking_options:
        # brief.md section 9: reuse the existing plain-language guidance
        # text (rota.planning.decision_guidance) -- never a second wording.
        text = result.decision_payload.unblocking_options[0].text
        return ExcelPlanResultOut(status=result.status, blocker=ExcelBlockerOut(message=text))
    if result.status == "TECHNICAL_ERROR":
        return ExcelPlanResultOut(
            status=result.status,
            blocker=ExcelBlockerOut(message="Wystąpiła awaria techniczna. Spróbuj ponownie za chwilę."),
        )
    return ExcelPlanResultOut(
        status=result.status,
        blocker=ExcelBlockerOut(message="Brak grafiku do zaproponowania. Spróbuj ponownie za chwilę."),
    )


# --- endpoints (brief.md section 6) -----------------------------------------


@router.post("/plan", response_model=ExcelPlanResultOut)
def post_excel_plan(
    payload: ExcelMonthlyInputRequest, conn: sqlite3.Connection = Depends(get_conn_excel),
    coordinator_id: str = Depends(get_coordinator_id_excel),
) -> ExcelPlanResultOut:
    try:
        month = _parse_month(payload.month)
        _validate_roster_gate(conn, payload.site_id, payload)
        _validate_payload_shape(payload)
        _apply_monthly_inputs(conn, coordinator_id=coordinator_id, site_id=payload.site_id, month=month, payload=payload)
        # Excel never exposes the lifecycle "effective_from" concept
        # (brief.md section 1/2) -- today() is the sane hidden default,
        # ignored entirely by plan_month() once a current version already
        # exists (recompute branch).
        result = plan_month(conn, site_id=payload.site_id, month=month, coordinator_id=coordinator_id, effective_from=date.today())
        return _result_out(conn, payload.site_id, month, result)
    except TargetHoursRequired as exc:
        return _target_hours_required_blocker(conn, exc)
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/replan", response_model=ExcelPlanResultOut)
def post_excel_replan(
    payload: ExcelMonthlyInputRequest, conn: sqlite3.Connection = Depends(get_conn_excel),
    coordinator_id: str = Depends(get_coordinator_id_excel),
) -> ExcelPlanResultOut:
    try:
        month = _parse_month(payload.month)
        _validate_roster_gate(conn, payload.site_id, payload)
        _validate_payload_shape(payload)
        _apply_monthly_inputs(conn, coordinator_id=coordinator_id, site_id=payload.site_id, month=month, payload=payload)
        result = replan(conn, site_id=payload.site_id, month=month, coordinator_id=coordinator_id, effective_from=date.today())
        return _result_out(conn, payload.site_id, month, result)
    except TargetHoursRequired as exc:
        return _target_hours_required_blocker(conn, exc)
    except ReplanNotAvailableAfterAcceptance:
        return ExcelPlanResultOut(
            status="REPLAN_NOT_AVAILABLE",
            blocker=ExcelBlockerOut(message="Ten miesiąc ma już zaakceptowany grafik. Wybierz Przelicz zamiast Pokaż inny wariant."),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/select-candidate", status_code=204)
def post_excel_select_candidate(
    payload: ExcelSelectCandidateRequest, conn: sqlite3.Connection = Depends(get_conn_excel),
    coordinator_id: str = Depends(get_coordinator_id_excel),
) -> None:
    month = _parse_month(payload.month)
    preview = get_plan_preview(conn, payload.site_id, month)
    if preview is None:
        raise HTTPException(status_code=409, detail="Brak aktualnego wyniku PLAN/REPLAN do wyboru. Wybierz Przelicz ponownie.")
    matching = next((c for c in preview.candidates if _candidate_id(c) == payload.candidate_id), None)
    if matching is None:
        # brief.md section 6.1: stale/foreign candidate_id is a controlled
        # blocker, never a lookup into a different preview/site/month.
        raise HTTPException(status_code=409, detail="Ten kandydat jest nieaktualny. Wybierz Przelicz lub Pokaż inny wariant ponownie.")
    try:
        select_candidate(conn, site_id=payload.site_id, month=month, candidate=matching, coordinator_id=coordinator_id)
    except CandidateRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/schedule/{site_id}/{month}", response_model=ExcelScheduleOut)
def get_excel_schedule(
    site_id: str, month: str, conn: sqlite3.Connection = Depends(get_conn_excel),
) -> ExcelScheduleOut:
    parsed_month = _parse_month(month)
    try:
        current = get_current_schedule_snapshot(conn, site_id, parsed_month)
    except Exception as exc:
        raise to_http_exception(exc) from exc
    if current is None:
        return ExcelScheduleOut(rows=[])
    _header, snapshot = current
    demands_by_id = {d.demand_id: d for d in snapshot.shift_demands}
    candidates_out = _candidates_out(conn, site_id, parsed_month, [snapshot.assignments], demands_by_id)
    return ExcelScheduleOut(rows=candidates_out[0].rows if candidates_out else [])
