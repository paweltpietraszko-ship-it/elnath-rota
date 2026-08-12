TASK_CONTRACT
CONTRACT_VERSION: v0.4 + decyzje właściciela 2026-08-10
TASK_ID: ROTA-T001a
FROZEN_SOURCE: arch/spec.md SECTION 1
  @ 7e34c251280a8054307e9f4b2f69d9f239604ac9

OBJECTIVE:
  Stałe + wszystkie enumy + StandardShift.
  Baza dla T001b-e.

TASK_SCOPE:
  - pyproject.toml
  - rota/constants.py
  - rota/domain.py

RESOLVED_GAPS: brak w tym sub-tasku

IMPLEMENTATION:
  pyproject.toml:
    Dodac do [tool.pytest.ini_options]:
      pythonpath = ["."]

  rota/constants.py:
    REST_MIN_HOURS: int = 11
    # aktualne przepisy prawa pracy (art. 132 KP)

  rota/domain.py:
    Czytaj arch/spec.md SECTION 1.
    Tylko enumy i StandardShift -- nic wiecej.

    ShiftKind(str, Enum): D | N
    AssignmentRole(str, Enum): PRIMARY | TRAINEE
    AssignmentState(str, Enum):
      PLANNED | REALIZED | CANCELLED
    AvailabilityKind(str, Enum):
      DAY_SHIFT_OFF | UNAVAILABLE_24H |
      LEAVE_PLAN | LEAVE_GRANTED
    MembershipKind(str, Enum):
      LOCAL | EXTERNAL_SUPPORT
    ReadinessState(str, Enum):
      NOT_READY | READY_FOR_PRIMARY
    ReadinessSource(str, Enum):
      DEFAULT | COORDINATOR_OVERRIDE
    RuleCategory(str, Enum):
      CLIENT_REQUIREMENT | LOCAL_RULE |
      CONFIRMED_EXCEPTION
    RuleEnforcement(str, Enum):
      HARD | SOFT | INFORMATIONAL
    RuleResolution(str, Enum):
      RESOLVED | NEEDS_RESOLUTION
    DeviationCategory(str, Enum):
      LAW | CLIENT_REQUIREMENT | LEAVE_OR_TIME_OFF |
      HOURS | PREFERENCE | COVERAGE
    ScheduleStatus(str, Enum):
      WORKING | WORKING_WITH_DEVIATIONS |
      FINAL_NO_DEVIATIONS | FINAL_WITH_DEVIATIONS

    @dataclass(frozen=True)
    StandardShift:
      kind: ShiftKind
      start_time: time
      end_time: time
      end_next_day: bool
      required_primary_count: int

  Nie tworzyc rota/__init__.py.
  arch/spec.md SECTION 9 obowiazuje w calosci.

ACCEPTANCE_CHECKS:
  1. python -c "
     from rota.constants import REST_MIN_HOURS
     assert REST_MIN_HOURS == 11
     from rota.domain import (
       ShiftKind, AssignmentRole, AssignmentState,
       AvailabilityKind, MembershipKind,
       ReadinessState, ReadinessSource,
       RuleCategory, RuleEnforcement, RuleResolution,
       DeviationCategory, ScheduleStatus, StandardShift,
     )
     assert ShiftKind.D and ShiftKind.N
     assert AssignmentRole.PRIMARY and AssignmentRole.TRAINEE
     print('OK')
     " -> sukces
  2. Brak rota/__init__.py
  3. ruff check rota/ -> 0 bledow
  4. Zaden plik nie przekracza 600 linii

FORBIDDEN:
  - jakiekolwiek @dataclass poza StandardShift
  - PlanningState, PlanningEngine, solver, CP-SAT
  - pliki testowe
  - rota/__init__.py
  - >2 nowe pliki
  - merge do main

CONTRACT_GAP_CONDITIONS:
  - enum wymaga wartosci spoza spec.md -> STOP

DELIVERY:
  STATUS: DONE|CONTRACT_GAP|WYMAGA_DECYZJI
  HEAD_SHA: <git rev-parse HEAD>
  BRANCH: task/ROTA-T001
  BACKEND_OUTPUT: <verbatim stdout backend.py>
