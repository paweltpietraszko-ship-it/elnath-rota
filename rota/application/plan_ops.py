"""Operations 3 (PLAN), 4 (select candidate), 5 (REPLAN)
(tasks/ROTA-T009/brief.md).
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import replace
from datetime import date, datetime

from rota.application.assembler import assemble_planning_state, resolved_rule_version_ids
from rota.application.context import require_active_coordinator_context
from rota.application.errors import (
    CandidateRejected,
    NoCurrentScheduleVersion,
    ScheduleVersionNotWorking,
    require_real_date,
)
from rota.domain import Assignment, AssignmentRole, AssignmentState, ScheduleVersion
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence import site_memory
from rota.persistence.schedule_repository import (
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
    set_schedule_version_planning_regime_in_open_transaction,
)
from rota.planning.engine import plan
from rota.planning.engine_types import PlanningResult
from rota.planning.validator import validate
from rota.site_memory_types import ActionSourceKind, AffectedEntity, CoordinatorActionKind


class MissingCoordinatorActor(Exception):
    """ROTA-T019b section 14: select_candidate must be told explicitly who
    is selecting -- the previous fallback to the ScheduleVersion's own
    created_by is removed. No other T017 candidate semantics change."""


def _persist_decision_readback(
    conn, *, site_id: str, month: date, coordinator_id: str, schedule_version_id: str, result: PlanningResult,
) -> PlanningResult:
    """ROTA-T019b section 11: after plan()'s FINAL public result, persist or
    clear the current DECISION_REQUIRED readback. Fails closed: a
    persistence failure here becomes TECHNICAL_ERROR, never an unpersisted
    DECISION_REQUIRED or a FEASIBLE with a stale pointer left behind."""
    if result.status == "DECISION_REQUIRED":
        try:
            with conn:
                site_memory.reuse_or_insert_decision_required_snapshot_no_commit(
                    conn, site_id=site_id, month=month, schedule_version_id=schedule_version_id,
                    requested_by=coordinator_id, recorded_at=datetime.now(), payload=result.decision_payload,
                )
        except sqlite3.Error:
            return PlanningResult(
                status="TECHNICAL_ERROR", candidates=[], decision_payload=None,
                error_message="failed to persist DECISION_REQUIRED readback", warnings=list(result.warnings),
            )
        return result
    if result.status == "FEASIBLE":
        try:
            with conn:
                site_memory.clear_current_decision_required_no_commit(conn, site_id=site_id, month=month)
        except sqlite3.Error:
            return PlanningResult(
                status="TECHNICAL_ERROR", candidates=[], decision_payload=None,
                error_message="failed to clear stale DECISION_REQUIRED readback pointer", warnings=list(result.warnings),
            )
        return result
    return result  # TECHNICAL_ERROR: previous current pointer is preserved untouched


def _require_working_or_absent(conn, site_id: str, month: date) -> str | None:
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        return None
    header = get_schedule_version_header(conn, current_id)
    if header.status.value.startswith("FINAL"):
        raise ScheduleVersionNotWorking(f"{current_id} is FINAL; use REPLAN to create a new WORKING child")
    return current_id


def _create_first_version(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    version_id: str, demands: list,
) -> None:
    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=None,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=demands, assignments=[], deviations=[], effective_from=effective_from,
    )


def plan_month(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date | None = None,
    search_attempt: int = 0,
) -> PlanningResult:
    """Operation 3 (PLAN). Creates the first WORKING version when none
    exists yet (requires effective_from); otherwise plans fresh against the
    existing current WORKING version. A FINAL current version is never
    reopened -- callers must REPLAN.

    ROTA-T032 section 7.2: search_attempt is an optional, non-persisted
    passthrough to the existing solver -- "Szukaj dalej" reuses this same
    operation on the same CURRENT WORKING version with attempt > 0, never a
    new application operation. It is never stored on ScheduleVersion.

    R4-1/R5-1: schedule_versions rows can never be physically deleted (DB
    trigger), so a version created and only later found broken by a
    downstream read cannot be undone -- every assemble_planning_state read
    this function needs, including the one that produces the state handed
    to plan(), must happen BEFORE create_schedule_version. The version is
    only created once every read that could fail already has.

    R6-1: assemble_planning_state, run before any version exists, stamps
    schedule_version_id="" on its ephemeral ShiftDemands (T008 identity:
    Assignment/ShiftDemand are scoped by schedule_version_id) -- the state
    handed to plan() must instead already carry the REAL id the version is
    about to be created with, or a REPLAN'd/selected candidate later fails
    ASSIGN-03/04 as "modified" purely because its scope doesn't match."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    current_id = _require_working_or_absent(conn, site_id, month)
    if current_id is None:
        require_real_date(effective_from)
        assemble_planning_state(conn, site_id=site_id, month=month)  # dry-run; writes nothing
        state, _ = assemble_planning_state(conn, site_id=site_id, month=month)  # still pre-write
        version_id = f"SV-{uuid.uuid4().hex}"
        demands = tuple(replace(d, schedule_version_id=version_id) for d in state.shift_demands)
        state = replace(state, schedule_version_id=version_id, shift_demands=demands)
        _create_first_version(
            conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
            version_id=version_id, demands=list(demands),
        )
        result = plan(state, search_attempt=search_attempt)
        return _persist_decision_readback(
            conn, site_id=site_id, month=month, coordinator_id=coordinator_id,
            schedule_version_id=version_id, result=result,
        )
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    result = plan(state, search_attempt=search_attempt)
    return _persist_decision_readback(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, schedule_version_id=current_id, result=result,
    )


def _coerce_unproven_realized_to_planned(candidate: list[Assignment], prior_existing: tuple) -> list[Assignment]:
    """R4-12: only an Assignment that was ALREADY REALIZED in the version's
    prior persisted content is trusted, preserved historical fact -- the
    validator's REALIZED exemption (retroactive availability changes must
    not invalidate real history) is not a shape a caller may fabricate on a
    brand-new candidate to dodge fresh eligibility checking. Anything newly
    claimed REALIZED is validated as if it were PLANNED instead."""
    prior_realized_ids = {a.assignment_id for a in prior_existing if a.state == AssignmentState.REALIZED}
    return [
        replace(a, state=AssignmentState.PLANNED)
        if a.state == AssignmentState.REALIZED and a.assignment_id not in prior_realized_ids
        else a
        for a in candidate
    ]


def _assignment_fact(a: Assignment) -> dict:
    return {
        "schedule_version_id": a.schedule_version_id, "assignment_id": a.assignment_id, "employee_id": a.employee_id,
        "start_datetime": a.start_datetime, "end_datetime": a.end_datetime, "role": a.role.value,
        "state": a.state.value, "frozen": a.frozen, "covers_demand_id": a.covers_demand_id,
        "mentor_primary_assignment_id": a.mentor_primary_assignment_id, "operational_code": a.operational_code,
        "work_period_id": a.work_period_id, "required_rest_after_hours": a.required_rest_after_hours,
    }


def _candidate_delta(prior: tuple, candidate: list[Assignment]) -> tuple[dict, dict]:
    """ROTA-T019b section 19: only the changed/added/removed selected
    Assignment facts -- never the unselected T017 candidates, never the
    whole snapshot."""
    prior_by_id = {a.assignment_id: a for a in prior}
    candidate_by_id = {a.assignment_id: a for a in candidate}
    removed_ids = prior_by_id.keys() - candidate_by_id.keys()
    added_ids = candidate_by_id.keys() - prior_by_id.keys()
    changed_ids = {
        aid for aid in (prior_by_id.keys() & candidate_by_id.keys())
        if _assignment_fact(prior_by_id[aid]) != _assignment_fact(candidate_by_id[aid])
    }
    before_state = {
        "removed": [_assignment_fact(prior_by_id[aid]) for aid in sorted(removed_ids)],
        "changed": [_assignment_fact(prior_by_id[aid]) for aid in sorted(changed_ids)],
    }
    after_state = {
        "added": [_assignment_fact(candidate_by_id[aid]) for aid in sorted(added_ids)],
        "changed": [_assignment_fact(candidate_by_id[aid]) for aid in sorted(changed_ids)],
    }
    return before_state, after_state


def _replan_cutover_violations(
    prior: tuple[Assignment, ...], candidate: list[Assignment], cutover_at: datetime,
) -> list[str]:
    """ROTA-T023 R5-3/brief.md section 10.2: on a REPLAN child, every
    non-CANCELLED PRIMARY Assignment that started before cutover_at is
    frozen for this selection -- no removal, no field mutation, and no new
    replacement PRIMARY may start before cutover_at either. `prior` is the
    REPLAN child's own current snapshot (cloned from the parent by
    replan()), so this compares within one schedule_version_id, no
    cross-version identity model needed."""
    prior_by_id = {a.assignment_id: a for a in prior}
    candidate_by_id = {a.assignment_id: a for a in candidate}
    pre_cutover_prior = {
        aid: a for aid, a in prior_by_id.items()
        if a.role == AssignmentRole.PRIMARY and a.state != AssignmentState.CANCELLED and a.start_datetime < cutover_at
    }
    violations = []
    for aid, prior_a in pre_cutover_prior.items():
        cand_a = candidate_by_id.get(aid)
        if cand_a is None:
            violations.append(f"REPLAN cutover: pre-cutover PRIMARY {aid} removed")
        elif _assignment_fact(prior_a) != _assignment_fact(cand_a):
            violations.append(f"REPLAN cutover: pre-cutover PRIMARY {aid} mutated")
    for aid, cand_a in candidate_by_id.items():
        if aid in prior_by_id:
            continue
        if cand_a.role == AssignmentRole.PRIMARY and cand_a.state != AssignmentState.CANCELLED and cand_a.start_datetime < cutover_at:
            violations.append(f"REPLAN cutover: new pre-cutover PRIMARY {aid} added")
    return violations


def _enforce_replan_cutover(header: ScheduleVersion, prior: tuple, candidate: list[Assignment], cutover_at: datetime) -> None:
    if header.parent_version_id is None:
        return
    cutover_violations = _replan_cutover_violations(prior, candidate, cutover_at)
    if cutover_violations:
        raise CandidateRejected("; ".join(cutover_violations))


def _replan_cutover_pre_check(
    *, current_id, header, candidate, cutover_at, site_id, responds_to_decision_required_id,
):
    """B-R12-2: the cutover comparison must run against the child snapshot
    CURRENT inside the same atomic replace_working_snapshot transaction it
    guards, not against a `state.existing_assignments` read taken earlier --
    otherwise a concurrent write between that read and this transaction can
    make the checked snapshot stale."""
    def _check(open_conn) -> None:
        site_memory.validate_decision_required_link_no_commit(
            open_conn, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
        )
        current_snapshot = get_schedule_snapshot(open_conn, current_id)
        _enforce_replan_cutover(header, tuple(current_snapshot.assignments), candidate, cutover_at)

    return _check


def _select_candidate_hook(
    *, site_id, month, coordinator_id, header, current_id, before_state, after_state, note,
    responds_to_decision_required_id, recorded_at, planning_regime,
):
    def _hook(open_conn) -> None:
        # ROTA-T023b (frozen addendum section 4, 'provenance adoption on
        # selected candidate'): this fresh, freshly-validated candidate
        # write is the ONLY normal automatic path that may promote an
        # old-regime WORKING plan -- revalidate/finalize/restore/manual
        # child creation must never call this primitive.
        set_schedule_version_planning_regime_in_open_transaction(
            open_conn, version_id=current_id, planning_regime=planning_regime,
        )
        site_memory.record_coordinator_action_no_commit(
            open_conn, action_kind=CoordinatorActionKind.SCHEDULE_CANDIDATE_SELECTED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=header.effective_from, month=month, schedule_version_id=current_id,
            affected_entities=[AffectedEntity("SCHEDULE_VERSION", current_id)],
            before_state=before_state, after_state=after_state, note=note,
            source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=current_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        site_memory.invalidate_current_decision_required_no_commit(open_conn, site_ids=[site_id], months=[month])

    return _hook


def select_candidate(
    conn, *, site_id: str, month: date, candidate: list[Assignment], coordinator_id: str,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> ScheduleVersion:
    """Operation 4. Persists a coordinator-chosen FEASIBLE candidate onto
    the current WORKING version in place -- this fills in a version that
    was already created empty/ephemeral by PLAN and has not yet been shown
    as a real schedule, so it is not the "material correction" the owner
    versioning rule (review_01) targets; that rule governs operation 8.

    ROTA-T019b section 14: coordinator_id is now required -- the previous
    fallback to the ScheduleVersion's own created_by is removed. No other
    T017 candidate semantics change."""
    if coordinator_id is None:
        raise MissingCoordinatorActor("select_candidate requires an explicit acting coordinator_id")
    current_id = _require_working_or_absent(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    header = get_schedule_version_header(conn, current_id)
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    for_validation = _coerce_unproven_realized_to_planned(candidate, state.existing_assignments)
    report = validate(state, for_validation)
    if not report.hard_pass:
        raise CandidateRejected("; ".join(report.violations))
    before_state, after_state = _candidate_delta(state.existing_assignments, candidate)
    # R5-3/section 10.1: cutover_at is captured once, immediately before the
    # cutover-preservation check and the snapshot replacement it guards, and
    # the same value becomes SCHEDULE_CANDIDATE_SELECTED.recorded_at below.
    # B-R12-2: the actual comparison runs inside pre_check, against the
    # snapshot current in that same atomic transaction -- not here.
    cutover_at = datetime.now()
    recorded_at = cutover_at
    hook = _select_candidate_hook(
        site_id=site_id, month=month, coordinator_id=coordinator_id, header=header, current_id=current_id,
        before_state=before_state, after_state=after_state, note=note,
        responds_to_decision_required_id=responds_to_decision_required_id, recorded_at=recorded_at,
        planning_regime=state.site.planning_regime,
    )
    pre_check = _replan_cutover_pre_check(
        current_id=current_id, header=header, candidate=candidate, cutover_at=cutover_at,
        site_id=site_id, responds_to_decision_required_id=responds_to_decision_required_id,
    )
    return lifecycle.replace_working_snapshot(
        conn, version_id=current_id, applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=state.shift_demands, assignments=candidate, deviations=[], on_success=hook,
        pre_check=pre_check,
    )


def _replan_action_hook(*, site_id, month, coordinator_id, effective_from, current_id, child_id, note, responds_to_decision_required_id, recorded_at):
    def _hook(open_conn) -> None:
        site_memory.record_coordinator_action_no_commit(
            open_conn, action_kind=CoordinatorActionKind.SCHEDULE_REPLAN_CREATED, origin_site_id=site_id,
            affected_site_ids=[site_id], coordinator_id=coordinator_id, recorded_at=recorded_at,
            effective_from=effective_from, month=month, schedule_version_id=child_id,
            affected_entities=[AffectedEntity("SCHEDULE_VERSION", child_id)],
            before_state={"current_version_id": current_id}, after_state={"current_version_id": child_id},
            note=note, source_kind=ActionSourceKind.SCHEDULE_VERSION, source_id=child_id,
            responds_to_decision_required_id=responds_to_decision_required_id,
        )
        site_memory.invalidate_current_decision_required_no_commit(open_conn, site_ids=[site_id], months=[month])

    return _hook


def replan(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
    note: str | None = None, responds_to_decision_required_id: str | None = None,
) -> PlanningResult:
    """Operation 5. Always creates a new WORKING child cloned from the
    current version's complete content before calling plan(); T008/T006
    invariants are then enforced by create_schedule_version()/plan()
    themselves. Never auto-saves the returned candidate.

    R4-1/R6-1: every assemble_planning_state read must happen BEFORE
    create_schedule_version writes the child (rows can never be physically
    deleted), and its shift_demands/existing_assignments/deviations are
    re-stamped in memory to the child's real id first, so a later
    ASSIGN-03/04 check does not see every fixed fact as "modified" purely
    by scope."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    require_real_date(effective_from)
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month}) to REPLAN from")
    assemble_planning_state(conn, site_id=site_id, month=month)  # dry-run; writes nothing
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)  # still pre-write; scoped to parent
    child_id = f"SV-{uuid.uuid4().hex}"
    demands = tuple(replace(d, schedule_version_id=child_id) for d in state.shift_demands)
    existing = tuple(replace(a, schedule_version_id=child_id) for a in state.existing_assignments)
    deviations = tuple(replace(d, schedule_version_id=child_id) for d in state.deviations)
    state = replace(
        state, schedule_version_id=child_id, shift_demands=demands,
        existing_assignments=existing, deviations=deviations,
    )
    hook = _replan_action_hook(
        site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from,
        current_id=current_id, child_id=child_id, note=note,
        responds_to_decision_required_id=responds_to_decision_required_id, recorded_at=datetime.now(),
    )
    lifecycle.create_schedule_version(
        conn, version_id=child_id, site_id=site_id, month=month, parent_version_id=current_id,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=list(demands), assignments=list(existing),
        deviations=list(deviations), effective_from=effective_from, on_success=hook,
        pre_check=lambda c: site_memory.validate_decision_required_link_no_commit(
            c, responds_to_decision_required_id=responds_to_decision_required_id, origin_site_id=site_id,
        ),
    )
    result = plan(state)
    return _persist_decision_readback(
        conn, site_id=site_id, month=month, coordinator_id=coordinator_id, schedule_version_id=child_id, result=result,
    )
