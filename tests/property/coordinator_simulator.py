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
from math import ceil

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


# R6 fix (T43-R6-02): brief 2.4 freezes two hard bounds the old flat
# span=1..5-for-every-kind draw broke: LEAVE_GRANTED (urlop) is one range up
# to 14 calendar days, and at most one person may have it in a given
# scenario; SICK_LEAVE (L4) is 0-21 calendar days. DAY_SHIFT_OFF/
# UNAVAILABLE_24H/LEAVE_PLAN keep the old 1-5 day span -- the brief does not
# freeze their bounds the way it does urlop/L4, so this is a documented,
# not a mandated, choice.
_MAX_SPAN_DAYS = {
    AvailabilityKind.LEAVE_GRANTED.value: 14,
    AvailabilityKind.SICK_LEAVE.value: 21,
    AvailabilityKind.DAY_SHIFT_OFF.value: 5,
    AvailabilityKind.UNAVAILABLE_24H.value: 5,
    AvailabilityKind.LEAVE_PLAN.value: 5,
}


def random_absence_set(
    seed: int,
    spec: ObjectSpec,
    employee_count: int,
    *,
    allow_leave_granted: bool = True,
) -> list[AbsenceDraw]:
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
    The old allow_sick_leave=False pre-PLAN restriction is gone.

    R6 fix (T43-R6-02): brief 2.4 also freezes "w scenariuszu planowego
    urlopu nie ma albo ma go najwyżej jedna osoba" -- at most one
    LEAVE_GRANTED draw per scenario. The caller uses
    `allow_leave_granted=False` for a REPLAN draw when the initial PLAN draw
    already contained vacation. If another LEAVE_GRANTED would otherwise be
    drawn, resample from the other kinds instead of skipping the event, so
    `count` still reflects the number of absence events actually applied."""
    if seed == 0 or employee_count == 0:
        return []
    rng = random.Random(seed * 7919 + 1)  # distinct stream from the object generator's own rng
    count = rng.randint(0, 3)
    kinds = [k.value for k in AvailabilityKind]
    kinds_without_leave_granted = [k for k in kinds if k != AvailabilityKind.LEAVE_GRANTED.value]
    drawable_kinds = kinds if allow_leave_granted else kinds_without_leave_granted
    days = _month_dates(spec.month)
    draws = []
    leave_granted_drawn = False
    for _ in range(count):
        employee_index = rng.randrange(employee_count)
        kind = rng.choice(drawable_kinds)
        if kind == AvailabilityKind.LEAVE_GRANTED.value:
            if leave_granted_drawn:
                kind = rng.choice(kinds_without_leave_granted)
            else:
                leave_granted_drawn = True
        start_idx = rng.randrange(len(days))
        max_span = min(_MAX_SPAN_DAYS[kind], len(days) - start_idx)
        span = rng.randint(1, max_span)
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
            "display_name": f"SIM-{spec.seed}",
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
    browser calls (api/routers/durable_inputs.py::create_availability).

    availability_id includes employee_index (not just the in-call index i
    and start_date) so two SEPARATE apply_absences() calls on the same site
    (e.g. the initial draw and a later REPLAN-triggering draw, Checkpoint B)
    can never collide even when both happen to draw index 0 on the same
    start_date for a different employee -- confirmed as a real, reproduced
    collision for seed=8 (initial: EMP-1/2026-09-11, replan: EMP-4/
    2026-09-11) before this fix, a test-harness bug, not a product defect."""
    for i, draw in enumerate(draws):
        employee_id = local_employee_id(spec, draw.employee_index)
        resp = client.post(
            f"/api/workspace/employees/{employee_id}/availability",
            json={
                "site_id": site_id,
                "availability_id": f"SIM-{spec.seed}-AVAIL-{draw.employee_index}-{i}-{draw.start_date.isoformat()}",
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


def get_month_view(client: TestClient, site_id: str, month: date) -> dict:
    """R6 fix (T43-R6-04): the persisted MonthViewOut (assignments included)
    -- a different, genuinely independent data path from get_analytics()'s
    own planned_hours/month_balance/quarter_balance, used by
    compute_quarter_oracle() to sum actual PRIMARY hours itself rather than
    trusting the product's own analytics figure as the oracle's input."""
    resp = client.get(f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}")
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
    # Quarter analytics exposes the running quarter only when the
    # coordinator has already entered targets for all its months. Enter the
    # later targets before the first PLAN so missing quarter data cannot be
    # mistaken for a successful oracle comparison.
    for target_month in QUARTER_MONTHS[1:]:
        month_target = nominal_monthly_hours_kp(target_month, POLISH_2026_HOLIDAYS)
        for i in range(spec.employee_count):
            resp = client.post(
                f"/api/workspace/employees/{local_employee_id(spec, i)}/target-hours",
                json={"site_id": site_id, "month": target_month.isoformat(), "target_hours": month_target},
            )
            assert resp.status_code == 204, resp.text

    months_out = []
    for month in QUARTER_MONTHS:
        if month != QUARTER_MONTHS[0]:
            seed_calendar(client, site_id, month)

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
        month_view = get_month_view(client, site_id, month)
        months_out.append({
            "month": month.isoformat(), "first_plan_result": first_result, "external": external,
            "analytics": analytics, "assignments": month_view["assignments"],
        })

    return {"status": "QUARTER_OK", "seed": seed, "site_id": site_id, "months": months_out}


# --- Checkpoint B: evaluates the READY-MADE schedule the real solver ------
# --- returned. Never builds a second solver/validator; every fact below --
# --- is derived from real Assignments/demands/analytics already returned --
# --- by the production endpoints. -----------------------------------------

# T032 (add_dn_rhythm_reward)/T034 (add_third_consecutive_shift_penalty)
# only classify D/N atoms as 12h duties -- their window definitions assume a
# uniform daily atom, so a mixed-shape month like WEEKDAY_12H_WEEKEND_24H has
# no single well-defined "atom" and is intentionally excluded from the
# symmetric FAIRNESS_PASS/FAIL class (brief B3.1/B3.2): only UNPROVEN.
_SYMMETRIC_ATOM_HOURS: dict[str, int] = {"D_N_12H": 12, "SINGLE_24H": 24}


def _duration_hours(a: dict) -> float:
    start = datetime.fromisoformat(a["start_datetime"])
    end = datetime.fromisoformat(a["end_datetime"])
    return (end - start).total_seconds() / 3600.0


def _is_active_primary(a: dict) -> bool:
    return a["role"] == "PRIMARY" and a["state"] != "CANCELLED"


def demand_kind_by_id(demands: list[dict]) -> dict[str, str | None]:
    """The demand's own `shift_kind` field, as returned by the real
    GET .../schedule/{month} endpoint, IS the canonical classification
    (rota/planning/shift_catalog.py::classify_demand's own primary path:
    `if demand.shift_kind is not None: return demand.shift_kind`, and every
    T012-generated demand carries it) -- reading it here is reuse of that
    one classifier, not a second one."""
    return {d["demand_id"]: d.get("shift_kind") for d in demands}


def actual_hours_by_employee(assignments: list[dict], employees: list[str]) -> dict[str, float]:
    hours = {e: 0.0 for e in employees}
    for a in assignments:
        if _is_active_primary(a) and a["employee_id"] in hours:
            hours[a["employee_id"]] += _duration_hours(a)
    return hours


def weekend_hours_by_employee(assignments: list[dict], employees: list[str]) -> dict[str, float]:
    hours = {e: 0.0 for e in employees}
    for a in assignments:
        if not _is_active_primary(a) or a["employee_id"] not in hours:
            continue
        if datetime.fromisoformat(a["start_datetime"]).date().isoweekday() in WEEKEND:
            hours[a["employee_id"]] += _duration_hours(a)
    return hours


def holiday_hours_by_employee(assignments: list[dict], employees: list[str], holidays: frozenset[date]) -> dict[str, float]:
    hours = {e: 0.0 for e in employees}
    for a in assignments:
        if not _is_active_primary(a) or a["employee_id"] not in hours:
            continue
        if datetime.fromisoformat(a["start_datetime"]).date() in holidays:
            hours[a["employee_id"]] += _duration_hours(a)
    return hours


def _employee_day_kinds(assignments: list[dict], kind_by_demand: dict[str, str | None]) -> dict[tuple[str, date], str]:
    """One entry per (employee, calendar date of the shift's start) -- "MULTIPLE"
    if more than one active PRIMARY start lands on that date for that employee,
    exactly matching T032/T034's own "exactly one" per-day requirement."""
    day_kind: dict[tuple[str, date], str] = {}
    seen: set[tuple[str, date]] = set()
    for a in assignments:
        if not _is_active_primary(a):
            continue
        emp = a["employee_id"]
        d = datetime.fromisoformat(a["start_datetime"]).date()
        key = (emp, d)
        if key in seen:
            day_kind[key] = "MULTIPLE"
        else:
            seen.add(key)
            day_kind[key] = kind_by_demand.get(a.get("covers_demand_id")) or "MULTIPLE"
    return day_kind


def count_dn_rhythm_windows(day_kind: dict[tuple[str, date], str], employees: list[str], month: date) -> dict[str, int]:
    """T032 add_dn_rhythm_reward's own window: d=D exactly, d+1=N exactly,
    d+2 and d+3 have no start at all for that employee. Diagnostic count
    only -- never fed back into a threshold or PASS/FAIL by itself."""
    dates = _month_dates(month)
    counts = {e: 0 for e in employees}
    for e in employees:
        for i in range(len(dates) - 3):
            d0, d1, d2, d3 = dates[i], dates[i + 1], dates[i + 2], dates[i + 3]
            if (
                day_kind.get((e, d0)) == "D" and day_kind.get((e, d1)) == "N"
                and (e, d2) not in day_kind and (e, d3) not in day_kind
            ):
                counts[e] += 1
    return counts


_BAD_THIRD_WINDOW_PATTERNS = {("D", "D", "D"), ("D", "D", "N"), ("D", "N", "N")}


def count_bad_third_windows(day_kind: dict[tuple[str, date], str], employees: list[str], month: date) -> dict[str, int]:
    """T034 add_third_consecutive_shift_penalty's own bad windows -- one
    count per window even if it happened to match more than one pattern
    (structurally impossible here, kept for parity with the solver's own
    "at most one penalty per window" rule). N/N/N stays out of scope, exactly
    as the solver-side function documents (still HARD elsewhere)."""
    dates = _month_dates(month)
    counts = {e: 0 for e in employees}
    for e in employees:
        for i in range(len(dates) - 2):
            d0, d1, d2 = dates[i], dates[i + 1], dates[i + 2]
            window = (day_kind.get((e, d0)), day_kind.get((e, d1)), day_kind.get((e, d2)))
            if window in _BAD_THIRD_WINDOW_PATTERNS:
                counts[e] += 1
    return counts


def count_soft_absence_collisions(assignments: list[dict], absence_draws: list[AbsenceDraw], spec: ObjectSpec) -> int:
    """DAY_SHIFT_OFF/LEAVE_PLAN are SOFT preferences in the solver, not HARD
    -- a real Assignment can legally still land on one of those dates. This
    only counts how often that happened; it is not treated as a defect by
    itself (brief B3's own wording: "liczbę Assignmentów kolidujących")."""
    soft_kinds = {"DAY_SHIFT_OFF", "LEAVE_PLAN"}
    soft_ranges = [
        (local_employee_id(spec, d.employee_index), d.start_date, d.end_date)
        for d in absence_draws if d.kind in soft_kinds
    ]
    if not soft_ranges:
        return 0
    collisions = 0
    for a in assignments:
        if not _is_active_primary(a):
            continue
        emp = a["employee_id"]
        d = datetime.fromisoformat(a["start_datetime"]).date()
        for soft_emp, start, end in soft_ranges:
            if emp == soft_emp and start <= d <= end:
                collisions += 1
    return collisions


@dataclass(frozen=True)
class FairnessFacts:
    target_hours: dict[str, int]
    effective_target_hours: dict[str, int]
    actual_hours: dict[str, float]
    total_target_deviation: float
    completion_pct: dict[str, int]
    target_equity_spread: int
    weekend_hours: dict[str, float]
    weekend_spread: float
    holiday_hours: dict[str, float]
    holiday_spread: float
    dn_rhythm_windows: dict[str, int]
    bad_third_windows: dict[str, int]
    soft_absence_collisions: int


def compute_fairness_facts(
    *, assignments: list[dict], demands: list[dict], employees: list[str],
    analytics_rows: list[dict], absence_draws: list[AbsenceDraw], spec: ObjectSpec,
) -> FairnessFacts:
    """Pure function -- no HTTP, no CP-SAT, no DB. `analytics_rows` is the
    real GET .../analytics response's own `rows` (target_hours/
    effective_target_hours per employee already computed by the product)."""
    kind_by_demand = demand_kind_by_id(demands)
    day_kind = _employee_day_kinds(assignments, kind_by_demand)
    actual = actual_hours_by_employee(assignments, employees)
    weekend = weekend_hours_by_employee(assignments, employees)
    holiday = holiday_hours_by_employee(assignments, employees, POLISH_2026_HOLIDAYS)

    target_hours: dict[str, int] = {}
    effective_target_hours: dict[str, int] = {}
    for row in analytics_rows:
        if row["employee_id"] in actual and row.get("month_data"):
            target_hours[row["employee_id"]] = row["month_data"]["target_hours"]
            effective_target_hours[row["employee_id"]] = row["month_data"]["effective_target_hours"]

    total_target_deviation = sum(
        abs(actual[e] - effective_target_hours[e]) for e in effective_target_hours
    )
    # T032: floor(100 * actual / effective_target) for effective_target > 0 only.
    completion_pct = {
        e: int((100 * actual[e]) // effective_target_hours[e])
        for e in effective_target_hours if effective_target_hours[e] > 0
    }
    target_equity_spread = (max(completion_pct.values()) - min(completion_pct.values())) if completion_pct else 0

    weekend_spread = (max(weekend.values()) - min(weekend.values())) if weekend else 0.0
    holiday_spread = (max(holiday.values()) - min(holiday.values())) if holiday else 0.0

    return FairnessFacts(
        target_hours=target_hours, effective_target_hours=effective_target_hours, actual_hours=actual,
        total_target_deviation=total_target_deviation, completion_pct=completion_pct,
        target_equity_spread=target_equity_spread, weekend_hours=weekend, weekend_spread=weekend_spread,
        holiday_hours=holiday, holiday_spread=holiday_spread,
        dn_rhythm_windows=count_dn_rhythm_windows(day_kind, employees, spec.month),
        bad_third_windows=count_bad_third_windows(day_kind, employees, spec.month),
        soft_absence_collisions=count_soft_absence_collisions(assignments, absence_draws, spec),
    )


def is_symmetric_control_object(spec: ObjectSpec, absence_draws: list[AbsenceDraw]) -> bool:
    """R4/B3.1's REQUIRED control class: pure D/N 12h or pure H24, every
    LOCAL identical (no DAY_ONLY, no absence, no individual rule), no
    EXTERNAL_SUPPORT. WEEKDAY_12H_WEEKEND_24H has no single uniform atom
    across the month and is deliberately excluded -- it stays UNPROVEN."""
    return spec.shift_shape in _SYMMETRIC_ATOM_HOURS and not spec.day_only_indices and not absence_draws


def evaluate_fairness(
    *, spec: ObjectSpec, absence_draws: list[AbsenceDraw], has_external: bool,
    actual_hours: dict[str, float], primary_atom_count: int,
) -> tuple[str, dict]:
    """B3.1/B3.2: PASS only inside the frozen symmetric class, at the known
    minimal achievable spread. Never runs a second solver, never invents a
    threshold. Every other shape/scenario -- including any EXTERNAL
    reaction, absence, DAY_ONLY, or asymmetric shape -- is UNPROVEN, which
    must never be treated or rendered as green."""
    if has_external or not is_symmetric_control_object(spec, absence_draws):
        return "FAIRNESS_UNPROVEN", {"reason": "not the frozen symmetric control class (B3.1)"}
    atom_hours = _SYMMETRIC_ATOM_HOURS[spec.shift_shape]
    r = spec.employee_count
    n = primary_atom_count
    expected_min_spread = 0 if (r == 0 or n % r == 0) else atom_hours
    actual_spread = (max(actual_hours.values()) - min(actual_hours.values())) if actual_hours else 0
    detail = {"employee_count": r, "atom_count": n, "atom_hours": atom_hours, "expected_min_spread_hours": expected_min_spread, "actual_spread_hours": actual_spread}
    if actual_spread <= expected_min_spread:
        return "FAIRNESS_PASS", detail
    return "FAIRNESS_FAIL", detail


def select_first_candidate_reporting_validate(client: TestClient, site_id: str, month: date, result: dict) -> tuple[str, str | None, list[dict]]:
    """B2: 'did select-candidate return 204 vs an error' IS the real
    PRODUCT_VALIDATE_PASS/FAIL fact -- select_candidate()
    (rota/application/plan_ops.py:339-384) calls validate() and raises
    CandidateRejected on any HARD failure. Returns (status, violation_text,
    candidate) instead of raising, so a genuine product rejection is
    reported data, never a test crash."""
    candidate = result["candidates"][0]
    body = [{k: v for k, v in a.items() if k != "employee_display_name"} for a in candidate]
    resp = client.post(f"/api/workspace/sites/{site_id}/schedule/{month.isoformat()}/select-candidate", json={"candidate": body})
    if resp.status_code == 204:
        return "PRODUCT_VALIDATE_PASS", None, candidate
    return "PRODUCT_VALIDATE_FAIL", resp.text, candidate


def _actual_primary_hours_by_employee(assignments: list[dict], month: date) -> dict[str, int]:
    """R6 fix (T43-R6-04): the oracle's OWN summation over its OWN fetched
    Assignment data -- mirrors rota/balance.py:52-62's _hours_in_month
    arithmetic exactly (role==PRIMARY, state==PLANNED, whole-hour floor
    division of total_seconds by 3600, same-month filter) but never calls
    into rota.balance or reuses the analytics response's own planned_hours
    field as the "actual" input -- that would just be comparing the
    product's number against itself."""
    hours: dict[str, int] = {}
    for a in assignments:
        if a["role"] != "PRIMARY" or a["state"] != "PLANNED":
            continue
        start = datetime.fromisoformat(a["start_datetime"])
        end = datetime.fromisoformat(a["end_datetime"])
        if (start.year, start.month) != (month.year, month.month):
            continue
        emp = a["employee_id"]
        hours[emp] = hours.get(emp, 0) + int((end - start).total_seconds() // 3600)
    return hours


def compute_quarter_oracle(quarter_result: dict) -> dict:
    """B6: independent arithmetic only -- month_balance_expected = actual
    PRIMARY hours, computed by this function's own summation over the real
    persisted Assignments fetched for each month (see
    _actual_primary_hours_by_employee -- NOT read from analytics'
    planned_hours), minus target_hours; quarter_balance_expected
    accumulates month over month, carry-in 0 for the first month. Also
    cross-checks the product's OWN numbers for internal consistency
    (quarter_balance - month_balance == previous quarter_balance) for
    August/September, AND that the product's own unresolved_carryover
    equals its own quarter_balance every month (rota/balance.py:104-110
    defines unresolved_carryover as exactly running_quarter_balance -- a
    mismatch here would mean that identity broke, which is exactly the
    kind of drift an independent oracle exists to catch), per brief 4.3."""
    if quarter_result["status"] != "QUARTER_OK":
        return {"status": "QUARTER_BALANCE_NOT_APPLICABLE", "reason": quarter_result.get("reason", quarter_result["status"])}

    months = quarter_result["months"]
    running_expected: dict[str, float] = {}
    prev_product_quarter: dict[str, int | None] = {}
    per_month: list[dict] = []
    mismatches: list[dict] = []

    for idx, month_entry in enumerate(months):
        month_str = month_entry["month"]
        month = date.fromisoformat(month_str)
        rows = month_entry["analytics"]["rows"]
        actual_by_employee = _actual_primary_hours_by_employee(month_entry["assignments"], month)
        month_mismatches: list[dict] = []
        for row in rows:
            md = row.get("month_data")
            if md is None:
                continue
            emp = row["employee_id"]
            actual = actual_by_employee.get(emp, 0)
            target = md["target_hours"]
            expected_month_balance = actual - target
            expected_quarter_balance = running_expected.get(emp, 0) + expected_month_balance
            running_expected[emp] = expected_quarter_balance

            product_month_balance = md["month_balance"]
            product_quarter_balance = md["quarter_balance"]
            product_unresolved_carryover = md["unresolved_carryover"]
            if expected_month_balance != product_month_balance:
                month_mismatches.append({
                    "employee_id": emp, "kind": "month_balance",
                    "expected": expected_month_balance, "product": product_month_balance,
                })
            if product_quarter_balance is None:
                month_mismatches.append({
                    "employee_id": emp, "kind": "quarter_balance_missing",
                    "expected": expected_quarter_balance, "product": None,
                })
            elif expected_quarter_balance != product_quarter_balance:
                month_mismatches.append({
                    "employee_id": emp, "kind": "quarter_balance",
                    "expected": expected_quarter_balance, "product": product_quarter_balance,
                })
            if product_unresolved_carryover is None:
                month_mismatches.append({
                    "employee_id": emp, "kind": "unresolved_carryover_missing",
                    "expected": product_quarter_balance, "product": None,
                })
            elif product_quarter_balance is not None and product_unresolved_carryover != product_quarter_balance:
                month_mismatches.append({
                    "employee_id": emp, "kind": "unresolved_carryover",
                    "unresolved_carryover": product_unresolved_carryover, "quarter_balance": product_quarter_balance,
                })
            if idx > 0 and product_quarter_balance is not None:
                prev = prev_product_quarter.get(emp)
                if prev is not None and (product_quarter_balance - product_month_balance) != prev:
                    month_mismatches.append({
                        "employee_id": emp, "kind": "product_self_consistency",
                        "quarter_minus_month": product_quarter_balance - product_month_balance, "previous_quarter": prev,
                    })
            prev_product_quarter[emp] = product_quarter_balance

        per_month.append({"month": month_str, "mismatches": month_mismatches})
        mismatches.extend(month_mismatches)

    return {"status": "QUARTER_BALANCE_FAIL" if mismatches else "QUARTER_BALANCE_PASS", "per_month": per_month}


# ===========================================================================
# ROTA-T044 (tasks/ROTA-T044/brief.md R8 + TASK_CHATGPT.md + CORRECTION R1/R2
# + ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md): Symulator Koordynatora
# Wariant B -- prawdziwa zmienność zachowania.
#
# TEST-HARNESS BOUNDARY, identyczna jak w Wariancie A powyżej: Symulator
# automatyzuje wyłącznie decyzje koordynatora. Jego JEDYNA własna
# odpowiedzialność obliczeniowa to kalkulator liczby LOCAL, wykonywany raz,
# przed pierwszym PLAN. Nie ocenia fairness, bilansu ani jakości grafiku --
# zły/dziwny wynik produktu jest wynikiem badania, nigdy sygnałem do zmiany
# wejścia. Wariant A powyżej zostaje całkowicie nietknięty; wszystko poniżej
# jest addytywne, z osobnymi nazwami (sufiks _b / *B), nawet gdy loguje
# podobne czynności co Wariant A.
# ===========================================================================

WSZYSTKIE_MIESIACE_2026: tuple[date, ...] = tuple(date(2026, m, 1) for m in range(1, 13))
MAX_REQUIRED_PRIMARY_COUNT_B = 2  # zakres {1,2}, Codex R2-02/OWNER 2026-08-31


@dataclass(frozen=True)
class DemandAtomB:
    """One (shift kind, weekday) slice of a freely generated Wariant B
    object -- the smallest unit the generator draws independently (brief
    R8 section 1.2: 'losuje NIEZALEŻNIE ... każdego dnia tygodnia z osobna:
    czy ta zmiana występuje tego dnia, o jakich godzinach, i jaki jest
    required_primary_count'). Multiple atoms sharing the same
    (kind, start, end, required_primary_count) are grouped into one shift-
    catalog row before being sent to the real API -- grouping is an
    implementation detail (TASK_CHATGPT.md section 4), the per-weekday
    semantics and required_primary_count are never lost."""

    kind: str  # "D" or "N" (rota.domain.ShiftKind) -- H24 is kind="D" with start==end
    start: time
    end: time
    required_primary_count: int  # 1 or 2, independent per atom
    weekday: int  # ISO weekday, 1=Mon .. 7=Sun


def _weekday_occurrences_b(weekday: int, month: date) -> int:
    return sum(1 for d in _month_dates(month) if d.isoweekday() == weekday)


def layer_hours_b(atoms: tuple[DemandAtomB, ...], layer: int, month: date) -> float:
    """Total hours in `month` where AT LEAST `layer` people are required
    simultaneously -- an atom with required_primary_count >= layer
    contributes its full hours; a lower atom contributes 0 to this layer."""
    total = 0.0
    for atom in atoms:
        if atom.required_primary_count >= layer:
            total += _row_hours(atom.start, atom.end) * _weekday_occurrences_b(atom.weekday, month)
    return total


def layered_headcount_b(atoms: tuple[DemandAtomB, ...]) -> int:
    """ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md section 3.2, canonical
    formula after Codex R4-01/CC devil's-advocate finding 2 (own maxima per
    layer secretly combines peaks from DIFFERENT months -- caught with a
    constructed counterexample, fixed to sum layers WITHIN the same month
    first, THEN take the worst month):

        liczba_LOCAL = max_m( sum_k( ceil(layer_hours(k, m) / norm(m)) ) )

    No leave margin anywhere (OWNER R7: "jeśli sztucznie zawyzysz obsadę to
    dasz fory solverowi"). Pure sum/ceil/max arithmetic on the generated
    input -- never a second solver, never aware of PLAN/REPLAN results."""
    best = 0
    for m in WSZYSTKIE_MIESIACE_2026:
        norm = nominal_monthly_hours_kp(m, POLISH_2026_HOLIDAYS)
        total_this_month = sum(
            ceil(layer_hours_b(atoms, k, m) / norm)
            for k in range(1, MAX_REQUIRED_PRIMARY_COUNT_B + 1)
        )
        best = max(best, total_this_month)
    return best


def has_any_coverage_b(atoms: tuple[DemandAtomB, ...]) -> bool:
    """The ONLY rejection/reroll rule before building the Site (brief R8
    1.2): a demand pattern with zero coverage in every month is a useless
    test object, not a product defect."""
    return any(layer_hours_b(atoms, 1, m) > 0 for m in WSZYSTKIE_MIESIACE_2026)


# --- Control-case catalogs for T44-B-CALC-01/02/03 and the CC devil's-advocate
# --- counterexample (ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md section 3.2) --

def _dn_12h_atoms_b(required_primary_count_by_weekday: dict[int, int]) -> tuple[DemandAtomB, ...]:
    """D 05:00-17:00 + N 17:00-05:00 on every weekday present in the map,
    at that weekday's own required_primary_count -- the same D/N 12h shape
    as Wariant A's _CATALOG_ROWS['D_N_12H'], but with per-weekday counts."""
    atoms = []
    for wd, count in required_primary_count_by_weekday.items():
        atoms.append(DemandAtomB("D", time(5, 0), time(17, 0), count, wd))
        atoms.append(DemandAtomB("N", time(17, 0), time(5, 0), count, wd))
    return tuple(atoms)


CONTROL_ATOMS_UNIFORM_1_B = _dn_12h_atoms_b({wd: 1 for wd in ALL_WEEK})
CONTROL_ATOMS_UNIFORM_2_B = _dn_12h_atoms_b({wd: 2 for wd in ALL_WEEK})
CONTROL_ATOMS_MIXED_B = _dn_12h_atoms_b({**{wd: 2 for wd in WEEKDAYS}, **{wd: 1 for wd in WEEKEND}})
# CC devil's-advocate finding 2 counterexample: one 12h shift, Mon-Sat,
# required_primary_count=2 on Mon/Tue/Sat and =1 on Wed/Thu/Fri, Sunday
# closed -- the sum-of-per-layer-maxima formula gave 5, the corrected
# max-of-per-month-sums formula gives the true 4.
CONTROL_ATOMS_COUNTEREXAMPLE_B = tuple(
    DemandAtomB("D", time(8, 0), time(20, 0), (2 if wd in (1, 2, 6) else 1), wd)
    for wd in (1, 2, 3, 4, 5, 6)
)


@dataclass(frozen=True)
class ObjectSpecB:
    """One freely generated Wariant B object. Unlike Wariant A's ObjectSpec,
    employee_count is DERIVED from atoms via layered_headcount_b -- never a
    fixed function of a layer_count field, because required_primary_count
    can differ per (kind, weekday)."""

    seed: int
    month: date
    regime: str  # "ORDINARY" | "OCHRONA"
    rolling_7d_threshold_hours: int
    atoms: tuple[DemandAtomB, ...]
    employee_count: int
    target_hours_per_employee: int


_START_HOUR_CHOICES_B = (time(0, 0), time(5, 0), time(6, 0), time(7, 0), time(8, 0), time(14, 0), time(17, 0), time(20, 0))
_DURATION_HOURS_CHOICES_B = (8, 10, 12, 16, 24)


def _shift_end_b(start: time, duration_hours: int) -> time:
    """duration_hours=24 always yields end==start (the H24 wraparound
    encoding _row_hours/shift_duration_hours expect); any other duration
    may or may not cross midnight depending on `start`, both legal."""
    end_dt = datetime.combine(date(2000, 1, 1), start) + timedelta(hours=duration_hours)
    return end_dt.time()


def random_atoms_b(rng: random.Random) -> tuple[DemandAtomB, ...]:
    """Free, independent per-(kind, weekday) generation (brief R8 1.2; R10-01
    fix -- the first version only ever drew two fixed canonical D/N 12h
    windows, so H24 and varied hours were never reachable, contradicting
    TASK_CHATGPT.md section 4's explicit requirement). For each ISO weekday
    and each of D/N, draws 0, 1, or 2 INDEPENDENT entries (2 is a legal
    same-kind-same-day overlap, per rota/planning/shift_catalog.py's own
    documented rule), each with its own randomly drawn start hour, duration
    (including 24h, which naturally encodes H24 via start==end regardless
    of the drawn start hour) and required_primary_count in {1,2}. Rerolled
    by the caller until has_any_coverage_b is true."""
    atoms = []
    for wd in ALL_WEEK:
        for kind in ("D", "N"):
            entry_count = rng.choices([0, 1, 2], weights=[45, 45, 10])[0]
            for _ in range(entry_count):
                start = rng.choice(_START_HOUR_CHOICES_B)
                duration = rng.choice(_DURATION_HOURS_CHOICES_B)
                end = _shift_end_b(start, duration)
                required = rng.choice([1, 2])
                atoms.append(DemandAtomB(kind, start, end, required, wd))
    return tuple(atoms)


def random_object_spec_b(seed: int) -> ObjectSpecB:
    """Rerolls (same seed stream, distinct sub-draws) until a non-empty
    demand pattern is produced -- the only generator-side rejection rule."""
    rng = random.Random(seed)
    atoms = random_atoms_b(rng)
    while not has_any_coverage_b(atoms):
        atoms = random_atoms_b(rng)
    month = rng.choice(WSZYSTKIE_MIESIACE_2026)
    regime = rng.choice(["ORDINARY", "OCHRONA"])
    employee_count = layered_headcount_b(atoms)
    target_hours = nominal_monthly_hours_kp(month, POLISH_2026_HOLIDAYS)
    return ObjectSpecB(
        seed=seed, month=month, regime=regime,
        rolling_7d_threshold_hours=rng.choice([48, 56, 60]),
        atoms=atoms, employee_count=employee_count, target_hours_per_employee=target_hours,
    )


def catalog_rows_from_atoms_b(atoms: tuple[DemandAtomB, ...]) -> list[dict]:
    """Groups atoms sharing (kind, start, end, required_primary_count) into
    shift-catalog rows with a combined active_weekdays list -- an
    implementation detail (TASK_CHATGPT.md section 4), never losing the
    per-weekday required_primary_count semantics: two atoms with different
    required_primary_count on the same weekday never collapse into one row.

    Two atoms sharing (kind, start, end, required_primary_count) AND the
    same weekday (a legal same-day overlap, generate_catalog_demands's own
    "independent occurrences" rule) must become TWO SEPARATE rows, each
    carrying that weekday once -- merging them into one row with the
    weekday listed once would silently drop the second occurrence the
    calculator already counted (layer_hours_b sums every atom)."""
    buckets: dict[tuple[str, time, time, int], list[set[int]]] = {}
    for atom in atoms:
        key = (atom.kind, atom.start, atom.end, atom.required_primary_count)
        rows_for_key = buckets.setdefault(key, [])
        target = next((r for r in rows_for_key if atom.weekday not in r), None)
        if target is None:
            target = set()
            rows_for_key.append(target)
        target.add(atom.weekday)
    return [
        {
            "kind": kind, "start_time": start.strftime("%H:%M"), "end_time": end.strftime("%H:%M"),
            "required_primary_count": required, "active_weekdays": sorted(weekdays),
        }
        for (kind, start, end, required), rows_for_key in buckets.items()
        for weekdays in rows_for_key
    ]


def local_employee_id_b(spec: ObjectSpecB, index: int) -> str:
    return f"SIMB-{spec.seed}-EMP-{index}"


def declared_roster_b(spec: ObjectSpecB) -> list[str]:
    return [local_employee_id_b(spec, i) for i in range(spec.employee_count)]


def _create_site_b(client: TestClient, spec: ObjectSpecB) -> str:
    resp = client.post(
        "/api/workspace/sites",
        json={
            "display_name": f"SIMB-{spec.seed}",
            "rolling_7d_decision_threshold_hours": spec.rolling_7d_threshold_hours, "planning_regime": spec.regime,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["site_id"]


def _put_shift_catalog_b(client: TestClient, site_id: str, spec: ObjectSpecB) -> None:
    resp = client.put(
        f"/api/workspace/sites/{site_id}/shift-catalog",
        json={"shifts": catalog_rows_from_atoms_b(spec.atoms)},
    )
    assert resp.status_code == 204, resp.text


def add_local_employee_b(client: TestClient, site_id: str, spec: ObjectSpecB, index: int) -> str:
    employee_id = local_employee_id_b(spec, index)
    resp = client.post(
        "/api/workspace/employees",
        json={"employee_id": employee_id, "site_id": site_id, "display_name": employee_id, "day_only": False},
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


def build_object_b(client: TestClient, spec: ObjectSpecB) -> str:
    """Mirrors Wariant A's build_object() shape, addytywnie: real Site,
    real shift-catalog PUT from the generated atoms, real calendar seed,
    real roster/target_hours per LOCAL. HEADCOUNT invariant
    (declared_LOCAL_count == layered_headcount_b) holds by construction --
    spec.employee_count IS layered_headcount_b(spec.atoms)."""
    site_id = _create_site_b(client, spec)
    _put_shift_catalog_b(client, site_id, spec)
    seed_calendar(client, site_id, spec.month)
    for i in range(spec.employee_count):
        add_local_employee_b(client, site_id, spec, i)
    return site_id


# --- OWNER-03 / TASK_CHATGPT_CORRECTION_R1+R2: nieobecności to wejścia -----
# --- koordynatora, zapisywane RAZ, wyłącznie przy initial setup, przed ----
# --- pierwszym PLAN -- nigdy dodawane/rozszerzane później (CC devil's- -----
# --- advocate finding 1, zamknięte w CORRECTION_R2). -----------------------

def _is_workday_b(d: date) -> bool:
    """Mon-Fri and not a POLISH_2026_HOLIDAYS date -- R10-02 fix: a real
    urlop block must cover the STATED number of working days, and a
    holiday landing inside a fixed 14/7 calendar-day span used to silently
    shrink it (e.g. 9 working days instead of 10 in a month with a
    Mon-Fri holiday)."""
    return d.weekday() < 5 and d not in POLISH_2026_HOLIDAYS


def _end_after_n_workdays(start: date, n: int) -> date:
    """The calendar end-date of a block starting on `start` that covers
    EXACTLY n real working days -- weekends/holidays inside the span
    extend it (they don't count toward n) rather than shrinking it."""
    count = 0
    d = start
    while True:
        if _is_workday_b(d):
            count += 1
        if count == n:
            return d
        d += timedelta(days=1)


def urlop_blocks_b(spec: ObjectSpecB) -> list[AbsenceDraw]:
    """TASK_CHATGPT_CORRECTION_R1.md section 1, deterministic w.r.t.
    spec.seed/month:
    - employee_count == 1: the sole LOCAL gets ONE 10-workday block;
    - employee_count >= 2: exactly TWO different LOCAL (index 0 and 1, a
      deterministic pick, not cyclic over the whole roster) get one
      10-workday and one 5-workday block respectively, non-overlapping;
      every other LOCAL gets no planned leave block in this object.
    Never a per-roster cyclic 10/5/10/5/... schedule (T44-TASK-01, the
    infeasible math this correction replaced)."""
    if spec.employee_count == 0:
        return []
    days_in_month = _month_dates(spec.month)
    ten_day_start = days_in_month[0]
    ten_day_end = _end_after_n_workdays(ten_day_start, 10)
    if spec.employee_count == 1:
        return [AbsenceDraw(employee_index=0, kind=AvailabilityKind.LEAVE_GRANTED.value, start_date=ten_day_start, end_date=ten_day_end)]
    five_day_start = ten_day_end + timedelta(days=1)
    five_day_end = _end_after_n_workdays(five_day_start, 5)
    return [
        AbsenceDraw(employee_index=0, kind=AvailabilityKind.LEAVE_GRANTED.value, start_date=ten_day_start, end_date=ten_day_end),
        AbsenceDraw(employee_index=1, kind=AvailabilityKind.LEAVE_GRANTED.value, start_date=five_day_start, end_date=five_day_end),
    ]


def sick_leave_draw_b(spec: ObjectSpecB, rng: random.Random) -> AbsenceDraw | None:
    """OWNER-03 5.2 / CORRECTION history: exactly one probabilistic roll
    PER OBJECT (never per state-machine step -- that compounded to ~82%
    over 6 steps in an earlier, rejected draft), ~25% chance, one 5
    CALENDAR day block (no "roboczych" qualifier for L4, unlike urlop),
    LOCAL-only, works even for employee_count == 1."""
    if rng.random() >= 0.25:
        return None
    days_in_month = _month_dates(spec.month)
    employee_index = rng.randrange(spec.employee_count)
    start_idx = rng.randrange(max(1, len(days_in_month) - 4))
    start = days_in_month[start_idx]
    end = days_in_month[min(start_idx + 4, len(days_in_month) - 1)]
    return AbsenceDraw(employee_index=employee_index, kind=AvailabilityKind.SICK_LEAVE.value, start_date=start, end_date=end)


def initial_absences_b(spec: ObjectSpecB, rng: random.Random) -> list[AbsenceDraw]:
    """The complete initial-setup-only absence set for one object: the
    deterministic urlop block(s) plus at most one probabilistic L4 --
    computed once, before the first PLAN, and never revisited afterwards."""
    draws = urlop_blocks_b(spec)
    sick = sick_leave_draw_b(spec, rng)
    if sick is not None:
        draws.append(sick)
    return draws


def apply_absences_b(client: TestClient, site_id: str, spec: ObjectSpecB, draws: list[AbsenceDraw]) -> None:
    """Same real endpoint as Wariant A's apply_absences(), addytywny
    wrapper only because ObjectSpecB has its own local_employee_id_b."""
    for i, draw in enumerate(draws):
        employee_id = local_employee_id_b(spec, draw.employee_index)
        resp = client.post(
            f"/api/workspace/employees/{employee_id}/availability",
            json={
                "site_id": site_id,
                "availability_id": f"SIMB-{spec.seed}-AVAIL-{draw.employee_index}-{i}-{draw.start_date.isoformat()}",
                "kind": draw.kind, "start_date": draw.start_date.isoformat(), "end_date": draw.end_date.isoformat(),
            },
        )
        assert resp.status_code == 204, resp.text


# --- OWNER-06: EXTERNAL is a repeatable, decision-gated test reaction only -

def external_support_employee_id_b(spec: ObjectSpecB, attempt: int) -> str:
    return f"SIMB-EXTERNAL-{spec.seed}-{attempt}"


def external_support_reaction_b(client: TestClient, site_id: str, month: date, spec: ObjectSpecB, attempt: int) -> dict:
    """One EXTERNAL_SUPPORT creation + PLAN retry, mirroring Wariant A's
    external_support_reaction() exactly (same decision-link ordering: only
    the create-person write carries the real decision id, later writes
    pass null) but addytywnie named/looped for Wariant B's repeatable
    reaction (brief 1.4 / TASK_CHATGPT.md OWNER-06)."""
    readback = client.get(f"/api/workspace/sites/{site_id}/decisions/{month.isoformat()}")
    assert readback.status_code == 200, readback.text
    decision = readback.json()
    assert decision is not None, "external_support_reaction_b called with no persisted DECISION_REQUIRED"
    decision_required_id = decision["decision_required_id"]

    employee_id = external_support_employee_id_b(spec, attempt)
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

    retry_result = run_plan(client, site_id, month)
    return {"decision_required_id": decision_required_id, "external_employee_id": employee_id, "retry_result": retry_result}


def run_with_external_loop_b(client: TestClient, site_id: str, month: date, spec: ObjectSpecB, first_result: dict) -> dict:
    """OWNER-06 (TASK_CHATGPT.md section 8): first PLAN is preserved
    untouched; if it is a real, non-empty DECISION_REQUIRED, create
    EXTERNAL_SUPPORT and retry, up to `spec.employee_count` times (the
    limit frozen in the brief -- enough to replace the whole sick/absent
    LOCAL crew, never unbounded on a malformed test object). Returns every
    stage so the caller can build a full reproducer regardless of outcome."""
    externals: list[dict] = []
    current = first_result
    attempt = 0
    while (
        current["status"] == "DECISION_REQUIRED"
        and current.get("decision_payload")
        and attempt < spec.employee_count
    ):
        attempt += 1
        reaction = external_support_reaction_b(client, site_id, month, spec, attempt)
        externals.append(reaction)
        current = reaction["retry_result"]
    return {
        "first_result": first_result, "externals": externals, "final_result": current,
        "exhausted_limit": current["status"] == "DECISION_REQUIRED" and attempt >= spec.employee_count,
    }


# --- OWNER-07: the only two invariants the harness itself checks ----------

def assert_headcount_b(spec: ObjectSpecB) -> None:
    assert spec.employee_count == layered_headcount_b(spec.atoms), (
        f"declared LOCAL count {spec.employee_count} != calculator {layered_headcount_b(spec.atoms)}"
    )


def assert_closed_world_b(assignments: list[dict], declared_roster: list[str], external_ids: list[str]) -> None:
    known = set(declared_roster) | set(external_ids)
    for a in assignments:
        assert a["employee_id"] in known, f"Assignment {a.get('assignment_id')} belongs to unknown employee {a['employee_id']!r}"


def all_candidate_assignments_b(result: dict) -> list[dict]:
    """R10-03 fix: a FEASIBLE PlanningResult can return MULTIPLE candidates
    -- checking only candidates[0] silently ignores a foreign employee_id
    in any later candidate. Flattens every candidate's assignments into one
    list for a single assert_closed_world_b() call."""
    return [a for candidate in result.get("candidates", []) for a in candidate]


def run_full_scenario_b(client: TestClient, seed: int, num_replans: int = 0) -> dict:
    """One fully reproducible pass for a given seed -- builds the object,
    applies the deterministic initial absences, PLANs (+ EXTERNAL loop if a
    real DECISION_REQUIRED appears), selects the first candidate if
    FEASIBLE, then REPLANs `num_replans` times. Deterministic given
    (seed, num_replans) because random_object_spec_b/initial_absences_b are
    pure functions of `seed` and every subsequent step only depends on the
    real product's own response -- used both as the CoordinatorVariantBMachine's
    reproduction command (OWNER-08 "gotowa komenda") and for standalone
    debugging of one failing seed."""
    spec = random_object_spec_b(seed)
    assert_headcount_b(spec)
    site_id = build_object_b(client, spec)
    rng = random.Random(seed * 104729 + 1)
    absence_draws = initial_absences_b(spec, rng)
    apply_absences_b(client, site_id, spec, absence_draws)

    plan_result = run_plan(client, site_id, spec.month)
    final_result = plan_result
    externals: list[dict] = []
    if plan_result["status"] == "DECISION_REQUIRED" and plan_result.get("decision_payload"):
        loop = run_with_external_loop_b(client, site_id, spec.month, spec, plan_result)
        externals = loop["externals"]
        final_result = loop["final_result"]

    selected = False
    replan_results: list[dict] = []
    if final_result["status"] == "FEASIBLE":
        select_first_candidate(client, site_id, spec.month, final_result)
        selected = True
        for _ in range(num_replans):
            replan_results.append(run_replan(client, site_id, spec.month))

    return {
        "seed": seed, "site_id": site_id, "spec": spec, "absence_draws": absence_draws,
        "plan_result": plan_result, "externals": externals, "final_result": final_result,
        "selected": selected, "replan_results": replan_results,
    }


def reproduction_command_b(seed: int, num_replans: int) -> str:
    """An actually executable one-liner (Wariant A's own
    `_reproduction_command` pattern) rebuilding this exact seed's object and
    replaying the exact recorded action sequence through run_full_scenario_b."""
    return (
        "python -c \""
        "from api.deps import get_conn; from api.main import app; "
        "from fastapi.testclient import TestClient; from rota.persistence.db import connect; "
        "from tests.property.coordinator_simulator import run_full_scenario_b; "
        "conn = connect(':memory:'); app.dependency_overrides[get_conn] = lambda: (yield conn); "
        f"print(run_full_scenario_b(TestClient(app), {seed}, num_replans={num_replans}))\""
    )
