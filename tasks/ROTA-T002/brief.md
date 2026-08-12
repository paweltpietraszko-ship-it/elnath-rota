TASK_CONTRACT
CONTRACT_VERSION: v0.4 + decyzje wlasciciela 2026-08-10
TASK_ID: ROTA-T002
FROZEN_SOURCE: arch/spec.md SECTION 1 (PlanningState)
  @ 7e34c251280a8054307e9f4b2f69d9f239604ac9

OBJECTIVE:
  Zaimplementowac PlanningState -- niemutowalna
  struktura danych przekazywana do PlanningEngine.
  Bez logiki planowania, bez solvera.

TASK_SCOPE:
  - rota/planning/state.py

IMPLEMENTATION:
  PlanningState jest dataclass (NIE persystowana), pola:
  site, profile, month, calendar_days, boundary_assignments,
  memberships, employees, external_windows,
  availability_records, site_rules, existing_assignments,
  work_balances, holiday_history, schedule_version_id.

  Bez metod biznesowych. Bez logiki walidacji w __init__.
  arch/spec.md SECTION 9 obowiazuje.
  Nie tworzyc rota/planning/__init__.py.

ACCEPTANCE_CHECKS:
  1. import rota.planning.state.PlanningState -> pola obecne
  2. import chain rota.domain + rota.planning.state -> OK
  3. ruff check rota/ -> 0 bledow
  4. rota/planning/state.py ponizej 600 linii
  5. brak rota/planning/__init__.py

FORBIDDEN:
  - logika planowania, solver, CP-SAT
  - PlanningEngine, PlanningResult
  - metody biznesowe w PlanningState
  - rota/planning/__init__.py
  - >1 nowy plik
  - merge do main

DELIVERY:
  STATUS: DONE|CONTRACT_GAP|WYMAGA_DECYZJI
  HEAD_SHA: <git rev-parse HEAD>
  BRANCH: task/ROTA-T002
  BACKEND_OUTPUT: <verbatim output_backend.txt>
