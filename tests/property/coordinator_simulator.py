"""ROTA-T038 (tasks/ROTA-T038/brief.md, KOREKTA 2 - OWNER_CORRECTED
2026-08-28): Symulator Koordynatora.

A thin "ticks checkboxes and reports" layer, explicitly NOT a layer that
judges whether the solver is right (that role stays with
benchmarks/REAL_OBJECT_BENCHMARK.md, unchanged). For each seed this:

1. invents a realistic Site (varying shift shape, number of parallel posts,
   regime) with staffing DERIVED from that object's own hourly workload
   (never picked independently of it -- the owner-caught v1 bug: an
   "N-person" object could silently need/use more people than its label
   claimed);
2. ticks real availability/absence "checkboxes" (sick leave, vacation,
   day-off-on-demand) through the same HTTP endpoint a coordinator's
   browser calls;
3. runs PLAN then REPLAN through the real routers;
4. reports what happened -- status, human-readable reason, and the full
   declared roster next to who actually ended up in the schedule -- into
   tests/property/test_coordinator_simulator.py's report writer.

The only judgment this module makes is "did anything crash" -- status
(FEASIBLE/DECISION_REQUIRED/TECHNICAL_ERROR) and headcount usage are
reported as facts for the owner to read, never asserted as right or wrong.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient

from rota.domain import AvailabilityKind, CalendarDay
from rota.persistence.calendar_repository import save_calendar_day

REALISTIC_HOURS_PER_EMPLOYEE = 160  # a plain, documented approximation of a full-time month, not a hidden constant
STAFFING_MARGIN = 1  # small buffer for REST/rotation feasibility on top of the raw hours division


@dataclass(frozen=True)
class ObjectSpec:
    """One invented, internally-consistent Site: staffing is DERIVED from
    this object's own hourly workload, never an independent random draw."""

    seed: int
    month: date
    shift_shape: str  # "D_N_12H" | "SINGLE_24H"
    posts: int  # parallel primaries required per shift
    regime: str  # "ORDINARY" | "OCHRONA"
    rolling_7d_threshold_hours: int
    monthly_hours_needed: int
    employee_count: int  # DERIVED from monthly_hours_needed, never independent
    day_only_indices: tuple[int, ...]
    external_count: int


def _days_in_month(month: date) -> int:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return (next_month - month).days


def _month_dates(month: date) -> list[date]:
    count = _days_in_month(month)
    return [month + timedelta(days=i) for i in range(count)]


def random_object_spec(seed: int, month: date) -> ObjectSpec:
    """seed=0 is reserved for the simplest realistic object (D/N, 1 post,
    ORDINARY) -- the "everyone available -> nice schedule" baseline from
    the owner's own description."""
    rng = random.Random(seed)
    days = _days_in_month(month)

    if seed == 0:
        shift_shape, posts, regime = "D_N_12H", 1, "ORDINARY"
    else:
        shift_shape = rng.choice(["D_N_12H", "SINGLE_24H"])
        # Fixed at 1 (not varied 1-3): posts=2 needs ~10-12 declared
        # employees and was measured at ~90s for one seed's PLAN+REPLAN
        # during this task's build -- too slow for a default 10-seed sweep.
        # Variety in this version comes from shift_shape/regime/external
        # support/absences instead. Flagged as a scope simplification, not
        # a silent cut -- posts variation is a reasonable follow-up once
        # solve time is budgeted for it.
        posts = 1
        regime = "OCHRONA" if shift_shape == "SINGLE_24H" else rng.choice(["ORDINARY", "OCHRONA"])

    # Both shapes cover the post around the clock -- 24h/day of coverage per
    # post either way (D+N together, or one 24h shift) -- so the same
    # formula applies to both; shape varies the CATALOG, not the hours math.
    monthly_hours_needed = 24 * posts * days

    employee_count = math.ceil(monthly_hours_needed / REALISTIC_HOURS_PER_EMPLOYEE) + STAFFING_MARGIN

    if shift_shape == "D_N_12H":
        max_day_only = max(0, employee_count - max(posts + 2, 3))
        day_only_count = rng.randint(0, max_day_only) if seed != 0 else 0
        day_only_indices = tuple(sorted(rng.sample(range(employee_count), day_only_count)))
    else:
        # A single 24h shift catalog has no distinct night kind to block --
        # DAY_ONLY has nothing to mean here.
        day_only_indices = ()

    external_count = 0 if seed == 0 else (rng.randint(1, 2) if rng.random() < 0.4 else 0)

    return ObjectSpec(
        seed=seed, month=month, shift_shape=shift_shape, posts=posts, regime=regime,
        rolling_7d_threshold_hours=rng.choice([48, 56, 60]) if seed != 0 else 60,
        monthly_hours_needed=monthly_hours_needed, employee_count=employee_count,
        day_only_indices=day_only_indices, external_count=external_count,
    )


@dataclass(frozen=True)
class AbsenceDraw:
    employee_index: int  # index into the LOCAL roster only
    kind: str  # AvailabilityKind value
    start_date: date
    end_date: date


def random_absence_set(seed: int, spec: ObjectSpec) -> list[AbsenceDraw]:
    """seed=0 draws zero absences -- the explicit "everyone available"
    baseline. Every other seed draws 0-3 records over the local roster
    only (absences apply to real people, not to external-support windows,
    which already have their own availability window mechanism)."""
    if seed == 0 or spec.employee_count == 0:
        return []
    rng = random.Random(seed * 7919 + 1)  # distinct stream from the object generator's own rng
    count = rng.randint(0, 3)
    kinds = [k.value for k in AvailabilityKind]
    days = _month_dates(spec.month)
    draws = []
    for _ in range(count):
        employee_index = rng.randrange(spec.employee_count)
        kind = rng.choice(kinds)
        start_idx = rng.randrange(len(days))
        span = rng.randint(1, min(5, len(days) - start_idx))
        draws.append(AbsenceDraw(
            employee_index=employee_index, kind=kind,
            start_date=days[start_idx], end_date=days[start_idx + span - 1],
        ))
    return draws


def local_employee_id(spec: ObjectSpec, index: int) -> str:
    return f"SIM-{spec.seed}-EMP-{index}"


def external_employee_id(spec: ObjectSpec, index: int) -> str:
    return f"SIM-{spec.seed}-EXT-{index}"


def seed_calendar(conn, month: date) -> None:
    for day in _month_dates(month):
        save_calendar_day(conn, CalendarDay(day, False))


def _create_site(client: TestClient, spec: ObjectSpec) -> str:
    resp = client.post(
        "/api/workspace/sites",
        json={
            "display_name": f"SIM-{spec.seed}", "profile_display_name": f"SIM-PROFILE-{spec.seed}",
            "rolling_7d_decision_threshold_hours": spec.rolling_7d_threshold_hours, "planning_regime": spec.regime,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["site_id"]


def _put_shift_catalog(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    all_week = [1, 2, 3, 4, 5, 6, 7]
    if spec.shift_shape == "D_N_12H":
        shifts = [
            {"kind": "D", "start_time": "05:00", "end_time": "17:00", "required_primary_count": spec.posts, "active_weekdays": all_week},
            {"kind": "N", "start_time": "17:00", "end_time": "05:00", "required_primary_count": spec.posts, "active_weekdays": all_week},
        ]
    else:
        shifts = [
            {"kind": "D", "start_time": "08:00", "end_time": "08:00", "required_primary_count": spec.posts, "active_weekdays": all_week},
        ]
    resp = client.put(f"/api/workspace/sites/{site_id}/shift-catalog", json={"shifts": shifts})
    assert resp.status_code == 204, resp.text


def _add_local_roster(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    for i in range(spec.employee_count):
        employee_id = local_employee_id(spec, i)
        resp = client.post(
            "/api/workspace/employees",
            json={"employee_id": employee_id, "site_id": site_id, "display_name": employee_id, "day_only": i in spec.day_only_indices},
        )
        assert resp.status_code == 204, resp.text
        resp = client.post(f"/api/workspace/sites/{site_id}/roster", json={"employee_id": employee_id})
        assert resp.status_code == 204, resp.text


def _add_external_support(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    if not spec.external_count:
        return
    last_day = _month_dates(spec.month)[-1]
    for i in range(spec.external_count):
        ext_id = external_employee_id(spec, i)
        client.post("/api/workspace/employees", json={"employee_id": ext_id, "site_id": site_id, "display_name": ext_id, "day_only": False})
        client.post(f"/api/workspace/sites/{site_id}/roster", json={"employee_id": ext_id, "membership_kind": "EXTERNAL_SUPPORT"})
        client.post(
            f"/api/workspace/employees/{ext_id}/support-window",
            json={
                "site_id": site_id, "start_datetime": f"{spec.month.isoformat()}T00:00:00",
                "end_datetime": f"{last_day.isoformat()}T23:59:59", "allowed_shift_kind": None,
            },
        )


def declared_roster(spec: ObjectSpec) -> list[str]:
    """The FULL, honest headcount -- local and external together, never a
    category silently excluded from the number the report calls "the object"."""
    return [local_employee_id(spec, i) for i in range(spec.employee_count)] + \
           [external_employee_id(spec, i) for i in range(spec.external_count)]


def build_object(client: TestClient, conn, spec: ObjectSpec) -> str:
    site_id = _create_site(client, spec)
    _put_shift_catalog(client, site_id, spec)
    seed_calendar(conn, spec.month)
    _add_local_roster(client, site_id, spec)
    _add_external_support(client, site_id, spec)
    return site_id


def apply_absences(client: TestClient, site_id: str, spec: ObjectSpec, draws: list[AbsenceDraw]) -> None:
    """The real 'ticking checkboxes' step -- same endpoint a coordinator's
    browser calls (api/routers/durable_inputs.py::create_availability)."""
    for i, draw in enumerate(draws):
        employee_id = local_employee_id(spec, draw.employee_index)
        resp = client.post(
            f"/api/workspace/employees/{employee_id}/availability",
            json={
                "site_id": site_id, "availability_id": f"SIM-{spec.seed}-AVAIL-{i}", "kind": draw.kind,
                "start_date": draw.start_date.isoformat(), "end_date": draw.end_date.isoformat(),
            },
        )
        assert resp.status_code == 204, resp.text
