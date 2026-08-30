"""ROTA-T043 (tasks/ROTA-T043/brief.md, ARCHITECT_CORRECTED R4): Symulator
Koordynatora.

TEST-HARNESS BOUNDARY: ten moduł symuluje działania koordynatora, a nie
logikę solvera. Wszystkie parametry obiektu powstają przed pierwszym PLAN.
Symulator nie poprawia grafiku ani danych pod wynik solvera. Zły grafik jest
wynikiem badania i zostaje zachowany jako reproduktor. Pierwszy PLAN używa
tylko wygenerowanych LOCAL. Dopiero rzeczywisty DECISION_REQUIRED uruchamia
testową ścieżkę wsparcia EXTERNAL przez produkcyjny backend. Nie dodawaj
reaktywnie LOCAL, nie przewiduj z góry potrzeby wsparcia i nie kalibruj
wejść pod PASS.

Frozen owner rules (R4, replacing T038 KOREKTA 3's workload-derived
headcount, retired by OWNER 2026-08-30):
- staffing is NEVER derived from monthly workload. One full continuous
  24/7 layer of coverage is exactly 5 LOCAL; two full parallel layers are
  exactly 10 LOCAL. D_N_12H / SINGLE_24H (H24) / WEEKDAY_12H_WEEKEND_24H
  are three different SHAPES of the same one layer, not different
  headcounts;
- headcount never changes after the first PLAN. There is no reactive hire
  any more -- the old hire_one_more_local() is gone;
- every LOCAL employee gets a REAL target_hours for the studied month: the
  statutory full-time norm per Kodeks pracy art. 130 SS1, independent of
  headcount, computed against a FROZEN, hardcoded 2026 Polish public-holiday
  fixture (POLISH_2026_HOLIDAYS below) -- never an empty/self-checking
  holiday set;
- the calendar is seeded through the real production endpoint
  (POST /workspace/calendar/day), never a direct persistence write;
- external support does NOT exist before the first PLAN. It is created only
  as the TEST-HARNESS's own automatic reaction to a real, non-empty
  DECISION_REQUIRED -- see external_support_reaction() -- never a
  simulation of a coordinator manually adding a new LOCAL (that remains the
  real product's own manual flow, out of this harness's scope).

For each seed this invents an object (fixed 5/10 headcount, varying shift
shape/layer count/regime), ticks real availability/absence "checkboxes",
runs PLAN through the real backend, and -- only if PLAN returns a real
DECISION_REQUIRED -- runs the testowa ścieżka wsparcia EXTERNAL described
above. A bad or unfair result is a valid, reportable finding, never
something this module tries to fix. See test_coordinator_simulator.py for
the driver, the fairness/validate evaluator (Checkpoint B) and the report
writer.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from rota.domain import AvailabilityKind, ShiftKind, StandardShift
from rota.planning.shift_catalog import shift_duration_hours

WEEKDAYS = (1, 2, 3, 4, 5)  # ISO Mon-Fri
WEEKEND = (6, 7)  # ISO Sat-Sun
ALL_WEEK = (1, 2, 3, 4, 5, 6, 7)

# ROTA-T043 brief.md section 2.3: official Polish 2026 statutory
# public holidays (ustawowo wolne od pracy), frozen so the calendar input
# and the target-hours calculator cannot check themselves against each
# other. Fixed dates verified by hand; the two Easter-dependent dates
# computed from the Gregorian Easter algorithm for 2026 (Easter Sunday
# 2026-04-05) and cross-checked against the public sources the brief
# cites: Zielona Linia / Centrum Informacyjne Służb Zatrudnienia, "Święta
# wolne od pracy w 2026 roku", and the Powiatowy Urząd Pracy w Sosnowcu
# 2026 wymiar-czasu-pracy table (both already cited in the brief for the
# 160h/176h control values below).
POLISH_2026_HOLIDAYS: frozenset[date] = frozenset([
    date(2026, 1, 1),   # Nowy Rok
    date(2026, 1, 6),   # Trzech Króli
    date(2026, 4, 5),   # Wielkanoc (Niedziela Wielkanocna) -- falls on Sunday
    date(2026, 4, 6),   # Poniedziałek Wielkanocny
    date(2026, 5, 1),   # Święto Pracy
    date(2026, 5, 3),   # Święto Konstytucji 3 Maja -- falls on Sunday
    date(2026, 5, 24),  # Zielone Świątki (Zesłanie Ducha Świętego) -- falls on Sunday
    date(2026, 6, 4),   # Boże Ciało
    date(2026, 8, 15),  # Wniebowzięcie Najświętszej Maryi Panny
    date(2026, 11, 1),  # Wszystkich Świętych -- falls on Sunday
    date(2026, 11, 11), # Święto Niepodległości
    date(2026, 12, 25), # Boże Narodzenie (pierwszy dzień)
    date(2026, 12, 26), # Boże Narodzenie (drugi dzień)
])

# Owner request 2026-08-28: heterogeneous catalogs, not just one uniform
# shift shape per object. Each row is (kind, start, end, required_primary_count,
# active_weekdays) -- rota/planning/shift_catalog.py::generate_catalog_demands
# already documents "Multiple entries and overlaps are legal and generate
# independent occurrences", confirmed by reading the code, not assumed.
# required_primary_count of 1 is ONE full 24/7 layer's share of this row;
# _put_shift_catalog multiplies it by ObjectSpec.layer_count for a second
# parallel layer (R4: two full layers = 10 LOCAL, never a partial layer).
_CATALOG_ROWS: dict[str, list[tuple[str, time, time, int, tuple[int, ...]]]] = {
    "D_N_12H": [
        ("D", time(5, 0), time(17, 0), 1, ALL_WEEK),
        ("N", time(17, 0), time(5, 0), 1, ALL_WEEK),
    ],
    "SINGLE_24H": [
        ("D", time(8, 0), time(8, 0), 1, ALL_WEEK),
    ],
    # Weekday 12h D/N, weekend a single 24h shift -- same total daily hours
    # (24h either way) but a different catalog SHAPE by day of week.
    "WEEKDAY_12H_WEEKEND_24H": [
        ("D", time(6, 0), time(18, 0), 1, WEEKDAYS),
        ("N", time(18, 0), time(6, 0), 1, WEEKDAYS),
        ("D", time(6, 0), time(6, 0), 1, WEEKEND),
    ],
}
_SHAPES_WITH_NIGHT = ("D_N_12H", "WEEKDAY_12H_WEEKEND_24H")

# NOT IMPLEMENTED (owner ruling 2026-08-28, ROTA-T039 Codex round-1 FAIL,
# reconfirmed unaffected by T043): a night post covered by two people of
# different durations. See git history of this file (T038/T039) for the
# full structural reasoning -- out of scope here too; T043 does not add a
# partial second layer or SPLIT_NIGHT_12_8 (brief section 4.2/8).


def _row_hours(start: time, end: time) -> float:
    return shift_duration_hours(StandardShift(ShiftKind.D, start, end, end <= start, 1))


def monthly_hours_for_shape(shift_shape: str, month: date, layer_count: int = 1) -> int:
    """Sums the REAL implied workload from the catalog rows themselves --
    no separate hardcoded formula to drift out of sync with the catalog.
    Purely informational/reportable now (R4): never used to derive
    headcount."""
    rows = _CATALOG_ROWS[shift_shape]
    total = 0.0
    for day in _month_dates(month):
        for _kind, start, end, required, active_weekdays in rows:
            if day.isoweekday() in active_weekdays:
                total += _row_hours(start, end) * required * layer_count
    return round(total)


@dataclass(frozen=True)
class ObjectSpec:
    """One invented, internally-consistent Site. R4: headcount is a fixed
    function of layer_count alone (5 or 10), never derived from workload
    and never changed after the first PLAN."""

    seed: int
    month: date
    shift_shape: str  # one of _CATALOG_ROWS's keys
    regime: str  # "ORDINARY" | "OCHRONA"
    rolling_7d_threshold_hours: int
    layer_count: int  # 1 or 2 full parallel 24/7 layers
    monthly_hours_needed: int  # informational only -- report field, not a headcount input
    employee_count: int  # exactly 5 * layer_count -- R4 frozen rule
    target_hours_per_employee: int  # real statutory monthly norm (art. 130 KP), independent of headcount
    day_only_indices: tuple[int, ...]


def _days_in_month(month: date) -> int:
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return (next_month - month).days


def _month_dates(month: date) -> list[date]:
    count = _days_in_month(month)
    return [month + timedelta(days=i) for i in range(count)]


def nominal_monthly_hours_kp(month: date, holidays: frozenset[date] = frozenset()) -> int:
    """Codex round-2 FINDING T38-R2-01: target_hours must be the REAL
    statutory full-time monthly norm (Kodeks pracy art. 130 SS1), not a
    per-object workload share. 40h per full Mon-Sun week fully inside the
    month, + 8h per remaining Mon-Fri day outside those weeks, - 8h per
    holiday landing on a non-Sunday. Callers must pass POLISH_2026_HOLIDAYS
    (T43-PRE-03/brief 2.3) -- the empty default here exists only so this
    function stays independently testable against an explicit holiday set."""
    days = _month_dates(month)
    hours, i, n = 0, 0, len(days)
    while i < n:
        d = days[i]
        if d.weekday() == 0 and i + 6 < n:  # Monday with a full week still inside the month
            hours += 40
            i += 7
        else:
            if d.weekday() < 5:  # Mon-Fri
                hours += 8
            i += 1
    for h in holidays:
        if h.year == month.year and h.month == month.month and h.weekday() != 6:
            hours -= 8
    return hours


def random_object_spec(seed: int, month: date) -> ObjectSpec:
    """seed=0 is reserved for the simplest realistic object (plain D/N,
    ORDINARY, one layer) -- the "everyone available -> nice schedule"
    baseline from the owner's own description. Every other seed cycles
    DETERMINISTICALLY through _CATALOG_ROWS's shapes and then through
    layer_count (Codex round-1 FINDING T39-R1-02: a random.choice() left
    the default sweep never exercising every axis at all) -- guarantees
    every shape AND both layer counts appear within the default 20-seed
    portfolio instead of leaving it to chance."""
    rng = random.Random(seed)
    shapes = list(_CATALOG_ROWS)

    if seed == 0:
        shift_shape, regime, layer_count = "D_N_12H", "ORDINARY", 1
    else:
        shift_shape = shapes[(seed - 1) % len(shapes)]
        regime = "OCHRONA" if shift_shape in ("SINGLE_24H", "WEEKDAY_12H_WEEKEND_24H") else rng.choice(["ORDINARY", "OCHRONA"])
        # Deterministic on seed, not re-drawn from rng, so the default
        # portfolio (seeds 0..19) provably covers both layer counts
        # instead of leaving it to chance draws.
        layer_count = 2 if ((seed - 1) // len(shapes)) % 2 == 1 else 1

    monthly_hours_needed = monthly_hours_for_shape(shift_shape, month, layer_count)
    employee_count = 5 * layer_count  # R4 frozen rule -- never derived from workload
    # T38-R2-01/R4: the REAL statutory monthly norm for every full-time
    # employee (art. 130 KP), independent of headcount, checked against the
    # frozen 2026 holiday fixture -- never a share of this object's own
    # workload.
    target_hours_per_employee = nominal_monthly_hours_kp(month, POLISH_2026_HOLIDAYS)

    if shift_shape in _SHAPES_WITH_NIGHT:
        max_day_only = max(0, employee_count - 3)
        day_only_count = rng.randint(0, max_day_only) if seed != 0 else 0
        day_only_indices = tuple(sorted(rng.sample(range(employee_count), day_only_count)))
    else:
        # A single 24h shift catalog has no distinct night kind to block --
        # DAY_ONLY has nothing to mean here.
        day_only_indices = ()

    return ObjectSpec(
        seed=seed, month=month, shift_shape=shift_shape, regime=regime,
        rolling_7d_threshold_hours=rng.choice([48, 56, 60]) if seed != 0 else 60,
        layer_count=layer_count, monthly_hours_needed=monthly_hours_needed, employee_count=employee_count,
        target_hours_per_employee=target_hours_per_employee, day_only_indices=day_only_indices,
    )


@dataclass(frozen=True)
class AbsenceDraw:
    employee_index: int  # index into the LOCAL roster only (fixed at generation time)
    kind: str  # AvailabilityKind value
    start_date: date
    end_date: date


def random_absence_set(seed: int, spec: ObjectSpec, employee_count: int) -> list[AbsenceDraw]:
    """seed=0 draws zero absences -- the explicit "everyone available"
    baseline. employee_count is passed separately from spec.employee_count
    for callers building a mid-month (REPLAN) draw against the same fixed
    roster.

    R4/brief 2.4: SICK_LEAVE is drawable both before the first PLAN and
    before a REPLAN with no special-casing -- empirically confirmed against
    this exact worktree (2026-08-30): ROTA-T041 OWNER-T041-02 (AUDIT-1 C-02)
    already extended rota/persistence/absence_reference_repository.py's
    PRE_PLAN accounting to cover SICK_LEAVE the same as LEAVE_GRANTED (see
    _resolve_no_accepted_plan_day's docstring); a live POST .../availability
    with kind=SICK_LEAVE followed by a real PLAN on a freshly built site
    returns 200 FEASIBLE, not the old IncompleteAbsenceReferenceError 500.
    The old allow_sick_leave=False pre-PLAN restriction is gone."""
    if seed == 0 or employee_count == 0:
        return []
    rng = random.Random(seed * 7919 + 1)  # distinct stream from the object generator's own rng
    count = rng.randint(0, 3)
    kinds = [k.value for k in AvailabilityKind]
    days = _month_dates(spec.month)
    draws = []
    for _ in range(count):
        employee_index = rng.randrange(employee_count)
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


def seed_calendar(client: TestClient, site_id: str, month: date) -> None:
    """R4/T43-PRE-03: seeds every day of `month` through the real
    production endpoint (POST /workspace/calendar/day), using the frozen
    POLISH_2026_HOLIDAYS fixture for the holiday flag -- never a direct
    persistence write, never a self-checking empty holiday set."""
    for day in _month_dates(month):
        resp = client.post(
            "/api/workspace/calendar/day",
            json={"date": day.isoformat(), "holiday": day in POLISH_2026_HOLIDAYS, "site_id": site_id},
        )
        assert resp.status_code == 204, resp.text


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
    shifts = [
        {
            "kind": kind, "start_time": start.strftime("%H:%M"), "end_time": end.strftime("%H:%M"),
            "required_primary_count": required * spec.layer_count, "active_weekdays": list(active_weekdays),
        }
        for kind, start, end, required, active_weekdays in _CATALOG_ROWS[spec.shift_shape]
    ]
    resp = client.put(f"/api/workspace/sites/{site_id}/shift-catalog", json={"shifts": shifts})
    assert resp.status_code == 204, resp.text


def add_local_employee(client: TestClient, site_id: str, spec: ObjectSpec, index: int, day_only: bool) -> str:
    """One real coordinator action: create + attach roster + set a real
    target_hours for the studied month. R4: called only at object
    construction time -- there is no reactive post-PLAN hire any more."""
    employee_id = local_employee_id(spec, index)
    resp = client.post(
        "/api/workspace/employees",
        json={"employee_id": employee_id, "site_id": site_id, "display_name": employee_id, "day_only": day_only},
    )
    assert resp.status_code == 204, resp.text
    resp = client.post(f"/api/workspace/sites/{site_id}/roster", json={"employee_id": employee_id})
    assert resp.status_code == 204, resp.text
    resp = client.post(
        f"/api/workspace/employees/{employee_id}/target-hours",
        json={"site_id": site_id, "month": spec.month.isoformat(), "target_hours": spec.target_hours_per_employee},
    )
    assert resp.status_code == 204, resp.text
    return employee_id


def _add_local_roster(client: TestClient, site_id: str, spec: ObjectSpec) -> None:
    for i in range(spec.employee_count):
        add_local_employee(client, site_id, spec, i, day_only=i in spec.day_only_indices)


def declared_roster(spec: ObjectSpec) -> list[str]:
    """The full, fixed LOCAL headcount -- R4: never changes after
    construction, so no current_count parameter is needed any more."""
    return [local_employee_id(spec, i) for i in range(spec.employee_count)]


def build_object(client: TestClient, spec: ObjectSpec) -> str:
    """The complete object: exactly the R4-frozen 5/10 roster, real
    target_hours for everyone, real production calendar, no external
    support -- see module docstring."""
    site_id = _create_site(client, spec)
    _put_shift_catalog(client, site_id, spec)
    seed_calendar(client, site_id, spec.month)
    _add_local_roster(client, site_id, spec)
    return site_id


def apply_absences(client: TestClient, site_id: str, spec: ObjectSpec, draws: list[AbsenceDraw]) -> None:
    """The real 'ticking checkboxes' step -- same endpoint a coordinator's
    browser calls (api/routers/durable_inputs.py::create_availability)."""
    for i, draw in enumerate(draws):
        employee_id = local_employee_id(spec, draw.employee_index)
        resp = client.post(
            f"/api/workspace/employees/{employee_id}/availability",
            json={
                "site_id": site_id, "availability_id": f"SIM-{spec.seed}-AVAIL-{i}-{draw.start_date.isoformat()}",
                "kind": draw.kind, "start_date": draw.start_date.isoformat(), "end_date": draw.end_date.isoformat(),
            },
        )
        assert resp.status_code == 204, resp.text


def external_support_employee_id(spec: ObjectSpec) -> str:
    return f"SIM-EXTERNAL-{spec.seed}"


def external_support_reaction(client: TestClient, site_id: str, month: date, spec: ObjectSpec) -> dict:
    """R4/brief section 2.5: the TEST-HARNESS's own automatic reaction to a
    real, non-empty DECISION_REQUIRED from the caller's own first PLAN --
    NOT a simulation of a coordinator's manual "add a new LOCAL" action.
    Creates exactly ONE SIM-EXTERNAL-* person as EXTERNAL_SUPPORT (no
    target_hours -- brief 2.3), through the same three production writes
    the real ControlPanel.tsx roster-add flow makes, in the exact order
    frontend/src/screens/ControlPanel.tsx:292-304 requires: only the FIRST
    material write (create-person) carries the real decision id; every
    later write (attach-membership, support-window) passes null, or it
    hits an already-stale id and 500s.

    Caller must have already confirmed the first PLAN returned
    DECISION_REQUIRED with a non-empty payload before calling this -- it
    does not re-check that here, since the caller is responsible for
    preserving the first PLAN's own result untouched regardless of what
    this reaction returns."""
    readback = client.get(f"/api/workspace/sites/{site_id}/decisions/{month.isoformat()}")
    assert readback.status_code == 200, readback.text
    decision = readback.json()
    assert decision is not None, "external_support_reaction called with no persisted DECISION_REQUIRED"
    decision_required_id = decision["decision_required_id"]

    employee_id = external_support_employee_id(spec)
    resp = client.post(
        "/api/workspace/employees",
        json={
            "employee_id": employee_id, "site_id": site_id, "display_name": employee_id, "day_only": False,
            "responds_to_decision_required_id": decision_required_id,
        },
    )
    assert resp.status_code == 204, resp.text

    resp = client.post(
        f"/api/workspace/sites/{site_id}/roster",
        json={"employee_id": employee_id, "membership_kind": "EXTERNAL_SUPPORT", "responds_to_decision_required_id": None},
    )
    assert resp.status_code == 204, resp.text

    window_start = datetime(month.year, month.month, 1)
    next_month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    window_end = datetime(next_month.year, next_month.month, 1)
    resp = client.post(
        f"/api/workspace/employees/{employee_id}/support-window",
        json={
            "site_id": site_id, "start_datetime": window_start.isoformat(), "end_datetime": window_end.isoformat(),
            "allowed_shift_kind": None, "responds_to_decision_required_id": None,
        },
    )
    assert resp.status_code == 204, resp.text

    second_result = run_plan(client, site_id, month)
    return {"decision_required_id": decision_required_id, "external_employee_id": employee_id, "second_plan_result": second_result}


def run_plan(client: TestClient, site_id: str, month: date) -> dict:
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}/plan", json={"effective_from": month.isoformat()})
    resp.raise_for_status()
    return resp.json()


def run_replan(client: TestClient, site_id: str, month: date) -> dict:
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}/replan", json={"effective_from": month.isoformat()})
    resp.raise_for_status()
    return resp.json()


def select_first_candidate(client: TestClient, site_id: str, month: date, result: dict) -> None:
    """R4 4.1: 'wybór pierwszego zwróconego kandydata jako deterministycznej
    decyzji drivera' -- deterministic, not a fairness judgment."""
    candidate = result["candidates"][0]
    body = [{k: v for k, v in a.items() if k != "employee_display_name"} for a in candidate]
    resp = client.post(
        f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}/select-candidate", json={"candidate": body},
    )
    resp.raise_for_status()


def get_analytics(client: TestClient, site_id: str, month: date) -> dict:
    resp = client.get(f"/api/workspace/sites/{site_id}/analytics", params={"month": month.isoformat()})
    resp.raise_for_status()
    return resp.json()


# --- R4 section 4.3: obowiązkowy kontrolny przebieg kwartalny -------------

QUARTER_MONTHS = (date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1))


def quarter_object_spec(seed: int, month: date) -> ObjectSpec:
    """The one fixed quarterly-control object: D_N_12H, ORDINARY, one
    layer (5 LOCAL) -- brief 4.3 requires a simple, isolated shape so the
    quarter pion tests carry-in, not several problems at once."""
    target_hours = nominal_monthly_hours_kp(month, POLISH_2026_HOLIDAYS)
    return ObjectSpec(
        seed=seed, month=month, shift_shape="D_N_12H", regime="ORDINARY",
        rolling_7d_threshold_hours=60, layer_count=1,
        monthly_hours_needed=monthly_hours_for_shape("D_N_12H", month, 1),
        employee_count=5, target_hours_per_employee=target_hours, day_only_indices=(),
    )


def run_quarter(client: TestClient, seed: int) -> dict:
    """R4 section 4.3 mechanics only (the independent arithmetic
    cross-check is Checkpoint B's B6, not built here). One Site, one
    :memory: connection (the caller owns/passes the TestClient already
    bound to that connection), the same 5 LOCAL reused across
    July->August->September 2026. For each month: seed that month's
    calendar via the production endpoint, PLAN, react to a real
    DECISION_REQUIRED via external_support_reaction() if needed (without
    ever abandoning or overwriting the first PLAN's own result), pick the
    first candidate, select_candidate(), read analytics, then move on.

    Returns {"status": "QUARTER_OK", "months": [...]} with one entry per
    month (spec, first plan result, external reaction facts if any, the
    analytics snapshot right after select_candidate), or
    {"status": "QUARTER_BLOCKED", "failing_month": ..., "seed": seed,
    "first_plan_result": ..., "reason": ...} the first time a month cannot
    reach a FEASIBLE base schedule even after the external reaction --
    never hand-seeds Assignments to force continuation."""
    spec = quarter_object_spec(seed, QUARTER_MONTHS[0])
    site_id = build_object(client, spec)
    months_out = []
    for month in QUARTER_MONTHS:
        if month != QUARTER_MONTHS[0]:
            seed_calendar(client, site_id, month)
            month_target = nominal_monthly_hours_kp(month, POLISH_2026_HOLIDAYS)
            for i in range(spec.employee_count):
                resp = client.post(
                    f"/api/workspace/employees/{local_employee_id(spec, i)}/target-hours",
                    json={"site_id": site_id, "month": month.isoformat(), "target_hours": month_target},
                )
                assert resp.status_code == 204, resp.text

        first_result = run_plan(client, site_id, month)
        external = None
        base_for_candidate = first_result
        if first_result["status"] == "DECISION_REQUIRED":
            if not first_result.get("decision_payload"):
                return {
                    "status": "QUARTER_BLOCKED", "failing_month": month.isoformat(), "seed": seed,
                    "first_plan_result": first_result, "reason": "empty DECISION_REQUIRED payload -- tool/product defect, not a real block",
                }
            external = external_support_reaction(client, site_id, month, spec)
            base_for_candidate = external["second_plan_result"]

        if base_for_candidate["status"] != "FEASIBLE" or not base_for_candidate.get("candidates"):
            return {
                "status": "QUARTER_BLOCKED", "failing_month": month.isoformat(), "seed": seed,
                "first_plan_result": first_result, "external": external,
                "reason": f"no FEASIBLE base schedule for {month.isoformat()} even after external reaction",
            }

        select_first_candidate(client, site_id, month, base_for_candidate)
        analytics = get_analytics(client, site_id, month)
        months_out.append({
            "month": month.isoformat(), "first_plan_result": first_result, "external": external, "analytics": analytics,
        })

    return {"status": "QUARTER_OK", "seed": seed, "site_id": site_id, "months": months_out}
