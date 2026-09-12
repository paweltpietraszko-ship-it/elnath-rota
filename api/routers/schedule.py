"""ROTA-T031 (tasks/ROTA-T031/brief.md): thin wrap of open_month/plan_ops/
lifecycle_ops/precheck/deviation_mapping for the Planowanie miesiaca
screen. Marshalling and a Polish deviation-label lookup only -- no new
persistence, versioning, or solver logic; every write still goes through
the existing plan_month/select_candidate/replan/revalidate/finalize/
restore application functions.
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.config import DEV_COORDINATOR_ID
from api.decision_payload import DecisionRequiredPayloadOut, decision_payload_out
from api.deps import get_conn
from api.errors import to_http_exception
from api.runtime_log import log_runtime_error
from rota.application.assembler import assemble_planning_state
from rota.application.lifecycle_ops import delete_current_version, exclude_from_history, finalize, restore, revalidate
from rota.application.memory_read import current_decision_required
from rota.application.open_month import months_with_schedule, open_month
from rota.application.plan_ops import (
    plan_month,
    reject_plan_preview,
    replan,
    replan_retry_narrow,
    replan_wider_search,
    select_candidate,
)
from rota.application.precheck import precheck
from rota.domain import Assignment, AssignmentRole, AssignmentState
from rota.persistence.employee_repository import list_employees_by_ids
from rota.persistence.plan_preview_repository import get_plan_preview
from rota.persistence.schedule_repository import (
    get_current_schedule_snapshot,
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
    is_schedule_version_live,
)

router = APIRouter(prefix="/workspace/sites", tags=["schedule"])

# brief.md section 4 point 8 / audit finding A-2: WEEKLY-REST-01 and REST-01
# had no Polish label anywhere in the T021 UI documents. Unknown codes fall
# back to the raw source_reference instead of a fabricated label.
_DEVIATION_LABELS = {
    "REST-01": "odpoczynek dobowy",
    "WEEKLY-REST-01": "odpoczynek tygodniowy (35h, OCHRONA)",
    "LOAD-01": "obciążenie godzinowe",
    "COVERAGE-01": "brak pokrycia zmiany",
    "DAY_SHIFT_OFF-01": "dzień wolny",
    "LEAVE_GRANTED-01": "urlop",
    "UNAVAILABLE-01": "niedostępność",
    "SICK_LEAVE-01": "zwolnienie lekarskie",
    "DAY_ONLY-01": "tylko dniówka",
    "MEMBERSHIP-01": "brak przypisania do obiektu",
    "EXTERNAL-01": "wsparcie zewnętrzne poza oknem",
    "SHIFT-24-01": "niedostępność 24h",
    "SHIFT-24-PAIR-01": "niekompletna para 24h",
    # ROTA-T058 (brief section 2.2, "wąski limit jednej polskiej etykiety").
    "THIRD-CONSECUTIVE-SHIFT-01": "trzecia służba pod rząd",
}


def _deviation_label(source_reference: str) -> str:
    return _DEVIATION_LABELS.get(source_reference, source_reference)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid date: {value!r}") from exc


class MonthsOut(BaseModel):
    months: list[str]


class ScheduleVersionOut(BaseModel):
    version_id: str
    status: str
    effective_from: str | None
    created_at: str
    created_by: str
    parent_version_id: str | None
    # ROTA-T057 follow-up (2026-09-07): whether this version's own first
    # shift has actually started (see schedule_repository.
    # is_schedule_version_live) -- the frontend needs this to show/hide
    # Przelicz Plan / Usuń correctly, since those now branch on live vs.
    # accepted-but-not-yet-live rather than on WORKING/FINAL status.
    is_live: bool


class ShiftDemandOut(BaseModel):
    demand_id: str
    start_datetime: str
    end_datetime: str
    required_primary_count: int
    shift_kind: str | None


class AssignmentOut(BaseModel):
    assignment_id: str
    schedule_version_id: str
    employee_id: str
    employee_display_name: str
    start_datetime: str
    end_datetime: str
    role: str
    state: str
    frozen: bool
    covers_demand_id: str | None
    mentor_primary_assignment_id: str | None
    operational_code: str | None
    work_period_id: str | None
    required_rest_after_hours: int | None


class DeviationOut(BaseModel):
    deviation_id: str
    category: str
    source_reference: str
    label: str
    affected_assignment_or_employee: str
    acknowledged: bool


class PlanPreviewOut(BaseModel):
    # ROTA-T057: None before the very first ScheduleVersion for this
    # (site_id, month) has ever been created (T57-01).
    schedule_version_id: str | None
    candidates: list[list[AssignmentOut]]
    warnings: list[str]
    optimization_complete: bool
    # R2-03 audit fix: "plan" or "replan" -- so the frontend can dispatch a
    # further "Szukaj dalej" to the correct continuation after a reload.
    operation_kind: str


class MonthViewOut(BaseModel):
    current_version: ScheduleVersionOut | None
    version_history: list[ScheduleVersionOut]
    demands: list[ShiftDemandOut]
    assignments: list[AssignmentOut]
    deviations: list[DeviationOut]
    # R1-2 (round-1 audit): DECISION_REQUIRED is a persistent hard stop, not
    # a transient PlanningResult held only in the browser's memory -- this
    # is the existing site_memory readback (current_decision_required),
    # surfaced here so it survives a reload.
    decision_required: DecisionRequiredPayloadOut | None
    warnings: list[str]
    # ROTA-T054: the persisted, unaccepted PLAN/REPLAN preview for this
    # (site_id, month), if one exists and still matches current_version --
    # a preview tied to an older version is stale and never surfaced here
    # (brief section 5, "GET MONTH / reload"). plan_preview_error (T54-07)
    # is set only when reading the preview itself failed; the rest of this
    # response (current schedule) stays untouched either way.
    plan_preview: PlanPreviewOut | None = None
    plan_preview_error: str | None = None


class PlanningResultOut(BaseModel):
    status: str
    candidates: list[list[AssignmentOut]]
    decision_payload: DecisionRequiredPayloadOut | None
    error_message: str | None
    warnings: list[str]
    optimization_complete: bool


class PrecheckOut(BaseModel):
    status: str
    under_covered_demand_ids: list[str]


def _version_out(conn, v) -> ScheduleVersionOut:
    return ScheduleVersionOut(
        version_id=v.version_id, status=v.status.value,
        effective_from=v.effective_from.isoformat() if v.effective_from else None,
        created_at=v.created_at.isoformat(), created_by=v.created_by, parent_version_id=v.parent_version_id,
        is_live=is_schedule_version_live(conn, v.version_id, now=datetime.now()),
    )


def _demand_out(d) -> ShiftDemandOut:
    return ShiftDemandOut(
        demand_id=d.demand_id, start_datetime=d.start_datetime.isoformat(), end_datetime=d.end_datetime.isoformat(),
        required_primary_count=d.required_primary_count, shift_kind=d.shift_kind.value if d.shift_kind else None,
    )


def _assignment_out(a, employees_by_id: dict) -> AssignmentOut:
    employee = employees_by_id.get(a.employee_id)
    return AssignmentOut(
        assignment_id=a.assignment_id, schedule_version_id=a.schedule_version_id, employee_id=a.employee_id,
        employee_display_name=employee.display_name if employee else a.employee_id,
        start_datetime=a.start_datetime.isoformat(), end_datetime=a.end_datetime.isoformat(),
        role=a.role.value, state=a.state.value, frozen=a.frozen, covers_demand_id=a.covers_demand_id,
        mentor_primary_assignment_id=a.mentor_primary_assignment_id, operational_code=a.operational_code,
        work_period_id=a.work_period_id, required_rest_after_hours=a.required_rest_after_hours,
    )


def _deviation_out(d) -> DeviationOut:
    return DeviationOut(
        deviation_id=d.deviation_id, category=d.category.value, source_reference=d.source_reference,
        label=_deviation_label(d.source_reference), affected_assignment_or_employee=d.affected_assignment_or_employee,
        acknowledged=d.acknowledged,
    )


def _plan_preview_out(conn, preview) -> PlanPreviewOut:
    all_employee_ids = {a.employee_id for candidate in preview.candidates for a in candidate}
    employees_by_id = list_employees_by_ids(conn, list(all_employee_ids))
    candidates = [[_assignment_out(a, employees_by_id) for a in candidate] for candidate in preview.candidates]
    return PlanPreviewOut(
        schedule_version_id=preview.schedule_version_id, candidates=candidates,
        warnings=list(preview.warnings), optimization_complete=preview.optimization_complete,
        operation_kind=preview.operation_kind,
    )


def _planning_result_out(conn, result, *, operation: str) -> PlanningResultOut:
    """ROTA-TECHNICAL-ERROR-RECOVERY-UX (brief.md section 3/A2/A15): the
    ONE shared boundary for every PLAN/REPLAN/wider-search/retry result --
    a structured TECHNICAL_ERROR (no exception context; the solver simply
    returned that status) gets exactly one sanitized runtime log entry
    here, category STRUCTURED_PLANNING_FAILURE, never the raw
    `result.error_message`. `operation` is "PLAN" or "REPLAN" (wider-
    search/retry keep the REPLAN category they already continue -- brief
    section 3: "wider-search/retry zachowują swoją rzeczywistą operację")."""
    all_employee_ids = {a.employee_id for candidate in result.candidates for a in candidate}
    employees_by_id = list_employees_by_ids(conn, list(all_employee_ids))
    candidates = [[_assignment_out(a, employees_by_id) for a in candidate] for candidate in result.candidates]
    decision_payload = decision_payload_out(result.decision_payload) if result.decision_payload is not None else None
    if result.status == "TECHNICAL_ERROR":
        log_runtime_error(
            component=operation, exception_type="STRUCTURED_PLANNING_FAILURE",
            safe_message="Solver zwrócił TECHNICAL_ERROR bez kontekstu wyjątku.",
        )
    return PlanningResultOut(
        status=result.status, candidates=candidates, decision_payload=decision_payload,
        error_message=result.error_message, warnings=list(result.warnings),
        optimization_complete=result.optimization_complete,
    )


@router.get("/{site_id}/schedule/months", response_model=MonthsOut)
def get_months(site_id: str, conn=Depends(get_conn)) -> MonthsOut:
    try:
        months = months_with_schedule(conn, site_id=site_id)
        return MonthsOut(months=[m.isoformat() for m in months])
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/{site_id}/schedule/{month}", response_model=MonthViewOut)
def get_month(site_id: str, month: date, conn=Depends(get_conn)) -> MonthViewOut:
    try:
        view = open_month(conn, site_id=site_id, month=month)
        current = get_current_schedule_snapshot(conn, site_id=site_id, month=month)
        demands: list = []
        assignments: list = []
        deviations: list = []
        if current is not None:
            _, snapshot = current
            employee_ids = list({a.employee_id for a in snapshot.assignments})
            employees_by_id = list_employees_by_ids(conn, employee_ids)
            demands = [_demand_out(d) for d in snapshot.shift_demands]
            assignments = [_assignment_out(a, employees_by_id) for a in snapshot.assignments]
            deviations = [_deviation_out(d) for d in snapshot.deviations]
        readback = current_decision_required(conn, site_id=site_id, month=month)
        decision_required = decision_payload_out(readback.payload) if readback is not None else None
        # ROTA-T054 (brief section 5, "GET MONTH / reload", T54-07/T54-08):
        # a preview read failure is isolated here -- it must never fail the
        # whole month view or hide the current schedule already assembled
        # above. A preview whose schedule_version_id no longer matches the
        # CURRENT version is stale (e.g. a REPLAN created a new WORKING
        # child but its own solve never came back FEASIBLE, so no fresh
        # preview replaced the old one) and is never surfaced as current.
        plan_preview_out = None
        plan_preview_error = None
        try:
            preview = get_plan_preview(conn, site_id, month)
            # R2-01 audit fix: a preview is only "current" while its exact
            # WORKING version is still the current version AND that version
            # has not since moved to FINAL -- once finalized, an unselected
            # preview computed against the pre-final state is stale, even
            # though the version_id itself did not change (finalize() is a
            # status transition, not a new version).
            # R4-01 (architect audit fix): a persistent current_decision_
            # required readback (`readback`, above) is written before this
            # function's own delete-old-preview cleanup ever runs, so its
            # mere presence already proves a later non-FEASIBLE result
            # superseded whatever preview this exact WORKING version still
            # points at -- hide it even if that cleanup's own DELETE failed,
            # without needing a new marker for the same fact.
            # ROTA-T057 (T57-01): a preview can now legitimately exist BEFORE
            # any ScheduleVersion does -- current() and stored
            # schedule_version_id both None is the "no version yet" match,
            # not a stale leftover.
            preview_matches_current = preview is not None and (
                (view.current_version is None and preview.schedule_version_id is None)
                or (
                    view.current_version is not None
                    and preview.schedule_version_id == view.current_version.version_id
                    and not view.current_version.status.value.startswith("FINAL")
                )
            )
            if preview_matches_current and readback is None:
                plan_preview_out = _plan_preview_out(conn, preview)
                if view.current_version is None:
                    # No ScheduleVersion exists to source demands from yet --
                    # show the preview's own (the candidates were solved
                    # against these), so the grid can label D/N instead of
                    # falling back to "?" (found via a real manual test,
                    # 2026-09-06).
                    demands = [_demand_out(d) for d in preview.shift_demands]
        except Exception as exc:  # isolated, never propagated as the whole request's error (T54-07)
            plan_preview_error = str(exc)
        return MonthViewOut(
            current_version=_version_out(conn, view.current_version) if view.current_version else None,
            version_history=[_version_out(conn, v) for v in view.version_history],
            demands=demands, assignments=assignments, deviations=deviations,
            decision_required=decision_required, warnings=list(view.warnings),
            plan_preview=plan_preview_out, plan_preview_error=plan_preview_error,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.get("/{site_id}/schedule/{month}/precheck", response_model=PrecheckOut)
def get_precheck(site_id: str, month: date, conn=Depends(get_conn)) -> PrecheckOut:
    try:
        state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
        result = precheck(state)
        return PrecheckOut(status=result.status, under_covered_demand_ids=list(result.under_covered_demand_ids))
    except Exception as exc:
        raise to_http_exception(exc) from exc


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: str | None = None
    # Integration audit (2026-08-26): lets the coordinator ask for a
    # different CP-SAT seed/order ("Szukaj dalej") after a FEASIBLE but
    # optimization_complete=False result, without persisting anything --
    # mirrors plan_month's own existing search_attempt parameter.
    search_attempt: int = Field(default=0, ge=0)


@router.post("/{site_id}/schedule/{month}/plan", response_model=PlanningResultOut)
def post_plan(site_id: str, month: date, payload: PlanRequest, conn=Depends(get_conn)) -> PlanningResultOut:
    try:
        effective_from = _parse_date(payload.effective_from) if payload.effective_from else None
        # R1-5 (round-1 audit): raised here as ValueError (caller-input class,
        # -> 400) instead of letting plan_month's own require_real_date(None)
        # raise TypeError -- api/errors.py no longer maps TypeError to 400,
        # so an unmapped TypeError correctly still means "500, a real bug".
        if effective_from is None and get_current_version_id(conn, site_id=site_id, month=month) is None:
            raise ValueError("effective_from is required to create the first schedule version")
        result = plan_month(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID, effective_from=effective_from,
            search_attempt=payload.search_attempt,
        )
        return _planning_result_out(conn, result, operation="PLAN")
    except Exception as exc:
        raise to_http_exception(exc) from exc


class AssignmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignment_id: str
    schedule_version_id: str
    employee_id: str
    start_datetime: str
    end_datetime: str
    role: str
    state: str
    frozen: bool
    covers_demand_id: str | None = None
    mentor_primary_assignment_id: str | None = None
    operational_code: str | None = None
    work_period_id: str | None = None
    required_rest_after_hours: int | None = None


def _assignment_from_in(a: AssignmentIn) -> Assignment:
    return Assignment(
        assignment_id=a.assignment_id, schedule_version_id=a.schedule_version_id, employee_id=a.employee_id,
        start_datetime=datetime.fromisoformat(a.start_datetime), end_datetime=datetime.fromisoformat(a.end_datetime),
        role=AssignmentRole(a.role), state=AssignmentState(a.state), frozen=a.frozen,
        covers_demand_id=a.covers_demand_id, mentor_primary_assignment_id=a.mentor_primary_assignment_id,
        operational_code=a.operational_code, work_period_id=a.work_period_id,
        required_rest_after_hours=a.required_rest_after_hours,
    )


class SelectCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate: list[AssignmentIn]
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post("/{site_id}/schedule/{month}/select-candidate", status_code=204)
def post_select_candidate(site_id: str, month: date, payload: SelectCandidateRequest, conn=Depends(get_conn)) -> None:
    try:
        candidate = [_assignment_from_in(a) for a in payload.candidate]
        select_candidate(
            conn, site_id=site_id, month=month, candidate=candidate, coordinator_id=DEV_COORDINATOR_ID,
            note=payload.note, responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/{site_id}/schedule/{month}/plan-preview/reject", status_code=204)
def post_reject_plan_preview(site_id: str, month: date, conn=Depends(get_conn)) -> None:
    """ROTA-T054 (brief section 5, "ODRZUĆ WYNIK"): explicit coordinator
    rejection of the current unaccepted PLAN/REPLAN preview."""
    try:
        reject_plan_preview(conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ReplanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: str
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post("/{site_id}/schedule/{month}/replan", response_model=PlanningResultOut)
def post_replan(site_id: str, month: date, payload: ReplanRequest, conn=Depends(get_conn)) -> PlanningResultOut:
    try:
        effective_from = _parse_date(payload.effective_from)
        result = replan(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID, effective_from=effective_from,
            note=payload.note, responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
        return _planning_result_out(conn, result, operation="REPLAN")
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ReplanRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search_attempt: int = Field(default=0, ge=0)


@router.post("/{site_id}/schedule/{month}/replan/wider-search", response_model=PlanningResultOut)
def post_replan_wider_search(
    site_id: str, month: date, payload: ReplanRetryRequest = ReplanRetryRequest(), conn=Depends(get_conn),
) -> PlanningResultOut:
    """Step 2 ("Szukaj szerzej") of the agreed two-step REPLAN flow -- only
    meaningful after a NARROW_SEARCH_EXHAUSTED result from /replan, and only
    on the coordinator's explicit choice. Creates no new ScheduleVersion."""
    try:
        result = replan_wider_search(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            search_attempt=payload.search_attempt,
        )
        return _planning_result_out(conn, result, operation="REPLAN")
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/{site_id}/schedule/{month}/replan/retry", response_model=PlanningResultOut)
def post_replan_retry(
    site_id: str, month: date, payload: ReplanRetryRequest = ReplanRetryRequest(), conn=Depends(get_conn),
) -> PlanningResultOut:
    """Integration audit (2026-08-26), point 6: retries the narrow (step 1)
    stage on the SAME CURRENT WORKING child replan() already created, after
    a SEARCH_INCOMPLETE result -- never calls replan() again, which would
    create another child version."""
    try:
        result = replan_retry_narrow(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            search_attempt=payload.search_attempt,
        )
        return _planning_result_out(conn, result, operation="REPLAN")
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/{site_id}/schedule/{month}/revalidate", status_code=204)
def post_revalidate(site_id: str, month: date, conn=Depends(get_conn)) -> None:
    try:
        revalidate(conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID)
    except Exception as exc:
        raise to_http_exception(exc) from exc


class FinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acknowledged_deviation_ids: list[str]
    reason: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post("/{site_id}/schedule/{month}/finalize", status_code=204)
def post_finalize(site_id: str, month: date, payload: FinalizeRequest, conn=Depends(get_conn)) -> None:
    try:
        finalize(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID,
            acknowledged_deviation_ids=set(payload.acknowledged_deviation_ids), reason=payload.reason,
            responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: str
    note: str | None = None
    responds_to_decision_required_id: str | None = None


@router.post("/{site_id}/schedule/{month}/restore", status_code=204)
def post_restore(site_id: str, month: date, payload: RestoreRequest, conn=Depends(get_conn)) -> None:
    try:
        restore(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID, version_id=payload.version_id,
            note=payload.note, responds_to_decision_required_id=payload.responds_to_decision_required_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class VersionSnapshotOut(BaseModel):
    version_id: str
    demands: list[ShiftDemandOut]
    assignments: list[AssignmentOut]


@router.get("/{site_id}/schedule/{month}/versions/{version_id}", response_model=VersionSnapshotOut)
def get_version_snapshot(site_id: str, month: date, version_id: str, conn=Depends(get_conn)) -> VersionSnapshotOut:
    """ROTA-T057 follow-up (owner finding 2026-09-07): read-only view of an
    older, non-current version's content -- "Podglad" for a live month,
    where restore is refused (see restore_schedule_version). Never touches
    current/history/lifecycle state; a plain read."""
    try:
        header = get_schedule_version_header(conn, version_id)
        if header.site_id != site_id or header.month != month:
            raise ValueError(f"{version_id} does not belong to ({site_id}, {month})")
        snapshot = get_schedule_snapshot(conn, version_id)
        employee_ids = list({a.employee_id for a in snapshot.assignments})
        employees_by_id = list_employees_by_ids(conn, employee_ids)
        return VersionSnapshotOut(
            version_id=version_id,
            demands=[_demand_out(d) for d in snapshot.shift_demands],
            assignments=[_assignment_out(a, employees_by_id) for a in snapshot.assignments],
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


class ExcludeFromHistoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version_id: str


@router.post("/{site_id}/schedule/{month}/exclude-from-history", status_code=204)
def post_exclude_from_history(site_id: str, month: date, payload: ExcludeFromHistoryRequest, conn=Depends(get_conn)) -> None:
    try:
        exclude_from_history(
            conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID, version_id=payload.version_id,
        )
    except Exception as exc:
        raise to_http_exception(exc) from exc


@router.post("/{site_id}/schedule/{month}/delete-current", status_code=204)
def post_delete_current_version(site_id: str, month: date, conn=Depends(get_conn)) -> None:
    try:
        delete_current_version(conn, site_id=site_id, month=month, coordinator_id=DEV_COORDINATOR_ID)
    except Exception as exc:
        raise to_http_exception(exc) from exc
