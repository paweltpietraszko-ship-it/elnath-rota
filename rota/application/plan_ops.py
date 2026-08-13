"""Operations 3 (PLAN), 4 (select candidate), 5 (REPLAN)
(tasks/ROTA-T009/brief.md).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from rota.application.assembler import assemble_planning_state, generate_profile_demands, resolved_rule_version_ids
from rota.application.context import require_active_coordinator_context
from rota.application.errors import CandidateRejected, NoCurrentScheduleVersion, ScheduleVersionNotWorking
from rota.domain import Assignment, ScheduleVersion
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.schedule_repository import (
    get_current_version_id,
    get_schedule_snapshot,
    get_schedule_version_header,
)
from rota.persistence.site_profile_repository import get_site_profile
from rota.persistence.site_repository import get_site
from rota.planning.engine import plan
from rota.planning.engine_types import PlanningResult
from rota.planning.validator import validate


def _require_working_or_absent(conn, site_id: str, month: date) -> str | None:
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        return None
    header = get_schedule_version_header(conn, current_id)
    if header.status.value.startswith("FINAL"):
        raise ScheduleVersionNotWorking(f"{current_id} is FINAL; use REPLAN to create a new WORKING child")
    return current_id


def _create_first_version(conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date) -> None:
    profile = get_site_profile(conn, get_site(conn, site_id).profile_id)
    demands = generate_profile_demands(profile, month)
    version_id = f"SV-{uuid.uuid4().hex}"
    lifecycle.create_schedule_version(
        conn, version_id=version_id, site_id=site_id, month=month, parent_version_id=None,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=demands, assignments=[], deviations=[], effective_from=effective_from,
    )


def plan_month(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date | None = None,
) -> PlanningResult:
    """Operation 3 (PLAN). Creates the first WORKING version when none
    exists yet (requires effective_from); otherwise plans fresh against the
    existing current WORKING version. A FINAL current version is never
    reopened -- callers must REPLAN."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    current_id = _require_working_or_absent(conn, site_id, month)
    if current_id is None:
        if effective_from is None:
            raise ValueError("effective_from is required to create the first ScheduleVersion")
        _create_first_version(conn, site_id=site_id, month=month, coordinator_id=coordinator_id, effective_from=effective_from)
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    return plan(state)


def select_candidate(
    conn, *, site_id: str, month: date, candidate: list[Assignment],
) -> ScheduleVersion:
    """Operation 4. Persists a coordinator-chosen FEASIBLE candidate onto
    the current WORKING version in place -- this fills in a version that
    was already created empty/ephemeral by PLAN and has not yet been shown
    as a real schedule, so it is not the "material correction" the owner
    versioning rule (review_01) targets; that rule governs operation 8."""
    current_id = _require_working_or_absent(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month})")
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    report = validate(state, candidate)
    if not report.hard_pass:
        raise CandidateRejected("; ".join(report.violations))
    return lifecycle.replace_working_snapshot(
        conn, version_id=current_id, applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=state.shift_demands, assignments=candidate, deviations=[],
    )


def replan(
    conn, *, site_id: str, month: date, coordinator_id: str, effective_from: date,
) -> PlanningResult:
    """Operation 5. Always creates a new WORKING child cloned from the
    current version's complete content before calling plan() -- T008/T006
    invariants (REALIZED preserved, frozen preserved, TRAINEE preserved,
    FINAL parent immutable, minimum-reshuffle ranking) are then enforced by
    create_schedule_version()/plan() themselves. Never auto-saves the
    returned candidate."""
    require_active_coordinator_context(conn, coordinator_id=coordinator_id, site_id=site_id)
    current_id = get_current_version_id(conn, site_id, month)
    if current_id is None:
        raise NoCurrentScheduleVersion(f"no current ScheduleVersion for ({site_id}, {month}) to REPLAN from")
    parent_snapshot = get_schedule_snapshot(conn, current_id)
    child_id = f"SV-{uuid.uuid4().hex}"
    lifecycle.create_schedule_version(
        conn, version_id=child_id, site_id=site_id, month=month, parent_version_id=current_id,
        created_at=datetime.now(), created_by=coordinator_id,
        applied_rule_version_ids=resolved_rule_version_ids(conn, site_id, month),
        shift_demands=parent_snapshot.shift_demands, assignments=parent_snapshot.assignments,
        deviations=parent_snapshot.deviations, effective_from=effective_from,
    )
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    return plan(state)
