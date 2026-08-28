"""ROTA-T038 (tasks/ROTA-T038/brief.md): Symulator Koordynatora.

Generates a random-but-realistic Site (varying employee count, DAY_ONLY
mix, ORDINARY/OCHRONA regime, external support, rolling-7d threshold) from
one integer seed, then drives it through the SAME HTTP endpoints a real
coordinator's browser calls (api/routers/*.py via FastAPI TestClient) --
create site, configure shift catalog, add employees, attach roster, plan,
resolve or accept DECISION_REQUIRED, select a candidate, sometimes a manual
correction, then finalize. REPLAN is deliberately out of v1 (see
brief.md "Poza zakresem") -- flagged as a follow-up, not silently dropped.

This is deliberately NOT a second scheduling system and does not decide
whether a schedule is "the right one" -- see benchmarks/REAL_OBJECT_BENCHMARK.md
for that role, unchanged and untouched by this module. The oracle here is
Rota's own already-published contract promises (see COORDINATOR SIMULATOR
INVARIANTS in test_coordinator_simulator.py), checked with the same
independent rota.planning.validator.validate() production already uses --
zero reimplemented solver logic.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient

from rota.application.assembler import assemble_planning_state
from rota.domain import Assignment, CalendarDay
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.planning.validator import validate


@dataclass(frozen=True)
class ObjectSpec:
    """One randomly-drawn, internally-consistent Site configuration."""

    seed: int
    month: date
    employee_count: int
    day_only_indices: tuple[int, ...]
    regime: str  # "ORDINARY" | "OCHRONA"
    external_support: bool
    rolling_7d_threshold_hours: int
    sufficient_staffing: bool


def random_object_spec(seed: int, month: date) -> ObjectSpec:
    """The generator. `sufficient_staffing=False` on ~1-in-5 seeds
    deliberately under-staffs (1-2 employees) to also exercise
    DECISION_REQUIRED as a checked, not just tolerated, outcome. Everything
    else varies every seed: regime, DAY_ONLY mix, external support,
    rolling-7d threshold.

    Deliberately NOT varied (simplifications, flagged in brief.md): no
    calendar holidays (every day holiday=False, matching every existing
    fixture in this repo); required_primary_count fixed at 1 for both D and
    N (varying it would need real coverage math, not just headcount, to
    keep the "sufficient" guarantee honest); OCHRONA uses the same D/N
    12h catalog as ORDINARY, not a genuine 24h shift pair -- it only
    exercises the REST/weekly-rest rule differences OCHRONA triggers
    (SitePlanningRegime), not a distinct shift catalog shape.
    """
    rng = random.Random(seed)
    sufficient_staffing = rng.randint(1, 5) != 1

    if sufficient_staffing:
        employee_count = rng.randint(4, 8)
        # Keep at least 3 employees able to work N (day_only blocks N).
        max_day_only = max(0, employee_count - 3)
        day_only_count = rng.randint(0, max_day_only)
    else:
        employee_count = rng.randint(1, 2)
        day_only_count = 0

    day_only_indices = tuple(sorted(rng.sample(range(employee_count), day_only_count)))

    return ObjectSpec(
        seed=seed,
        month=month,
        employee_count=employee_count,
        day_only_indices=day_only_indices,
        regime=rng.choice(["ORDINARY", "OCHRONA"]),
        external_support=sufficient_staffing and rng.random() < 0.5,
        rolling_7d_threshold_hours=rng.choice([40, 48, 56, 60]),
        sufficient_staffing=sufficient_staffing,
    )


def _days_in_month(month: date) -> list[date]:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    days, day = [], month
    while day < next_month:
        days.append(day)
        day = day + timedelta(days=1)
    return days


def seed_calendar(conn, month: date) -> None:
    """Calendar days are setup data, not a coordinator action -- every
    existing fixture in this repo (tests/support/t009_fixtures.py,
    tests/test_t021_external_support_roster.py) writes them directly
    through persistence, not through the /calendar HTTP endpoint. Matched
    here for consistency, not as a new convention."""
    for day in _days_in_month(month):
        save_calendar_day(conn, CalendarDay(day, False))


def build_object(client: TestClient, conn, spec: ObjectSpec) -> str:
    """Real coordinator setup journey, through the real HTTP endpoints.
    Returns the created site_id."""
    create_resp = client.post(
        "/api/workspace/sites",
        json={
            "display_name": f"SIM-{spec.seed}",
            "profile_display_name": f"SIM-PROFILE-{spec.seed}",
            "rolling_7d_decision_threshold_hours": spec.rolling_7d_threshold_hours,
            "planning_regime": spec.regime,
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    site_id = create_resp.json()["site_id"]

    catalog_resp = client.put(
        f"/api/workspace/sites/{site_id}/shift-catalog",
        json={
            "shifts": [
                {"kind": "D", "start_time": "05:00", "end_time": "17:00", "required_primary_count": 1, "active_weekdays": [1, 2, 3, 4, 5, 6, 7]},
                {"kind": "N", "start_time": "17:00", "end_time": "05:00", "required_primary_count": 1, "active_weekdays": [1, 2, 3, 4, 5, 6, 7]},
            ],
        },
    )
    assert catalog_resp.status_code == 204, catalog_resp.text

    seed_calendar(conn, spec.month)

    for i in range(spec.employee_count):
        employee_id = f"SIM-{spec.seed}-EMP-{i}"
        create_emp_resp = client.post(
            "/api/workspace/employees",
            json={
                "employee_id": employee_id, "site_id": site_id, "display_name": employee_id,
                "day_only": i in spec.day_only_indices,
            },
        )
        assert create_emp_resp.status_code == 204, create_emp_resp.text
        attach_resp = client.post(f"/api/workspace/sites/{site_id}/roster", json={"employee_id": employee_id})
        assert attach_resp.status_code == 204, attach_resp.text

    if spec.external_support:
        ext_id = f"SIM-{spec.seed}-EXT-1"
        client.post("/api/workspace/employees", json={"employee_id": ext_id, "site_id": site_id, "display_name": ext_id, "day_only": False})
        client.post(
            f"/api/workspace/sites/{site_id}/roster",
            json={"employee_id": ext_id, "membership_kind": "EXTERNAL_SUPPORT"},
        )
        client.post(
            f"/api/workspace/employees/{ext_id}/support-window",
            json={
                "site_id": site_id, "start_datetime": f"{spec.month.isoformat()}T00:00:00",
                "end_datetime": f"{_days_in_month(spec.month)[-1].isoformat()}T23:59:59", "allowed_shift_kind": None,
            },
        )

    return site_id


def independently_revalidate(conn, site_id: str, month: date, version_id: str) -> bool:
    """The oracle: reconstruct PlanningState the same way
    rota.application.manual_edit.apply_manual_correction already does, and
    re-run the SAME independent validator production uses. Returns
    hard_pass. Zero reimplemented solver/validator logic."""
    snapshot = get_schedule_snapshot(conn, version_id)
    state, _ = assemble_planning_state(
        conn, site_id=site_id, month=month, schedule_version_id=version_id,
        shift_demands=list(snapshot.shift_demands), assignments=list(snapshot.assignments), deviations=[],
    )
    report = validate(state, list(snapshot.assignments))
    return report.hard_pass


def find_planned_primary(conn, version_id: str) -> Assignment | None:
    snapshot = get_schedule_snapshot(conn, version_id)
    return next(
        (a for a in snapshot.assignments if a.role.value == "PRIMARY" and a.state.value == "PLANNED"), None,
    )
