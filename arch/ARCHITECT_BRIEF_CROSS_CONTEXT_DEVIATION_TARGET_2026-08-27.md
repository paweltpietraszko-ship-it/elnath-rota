# Brief dla architekta — Deviation target musi dopuszczać cross-context REST-01/WEEKLY-REST-01

Status: FAKTOGRAFICZNY, NIE ROZSTRZYGA PROJEKTU — do przekazania architektowi/Codexowi.

BASE_MAIN_SHA: `54acdf7cfebadefe1e3370bac0a62f963c72123e`
ŹRÓDŁO: znalezisko z niezależnego audytu ROTA-T034 (round 2/3, exact SHA `f7563c7`/`020603a`), klasyfikacja `WYMAGA_DECYZJI`, poza zakresem T034.

## 1. Zamrożony fakt: problem jest realny i odtwarzalny, niezależny od T034

`tests/test_audit_t009_r6.py::test_r6_distinct_trainings_with_same_local_id_in_different_versions_both_count` failuje deterministycznie na T034 (`f7563c7`/`020603a`), a przechodzi na bazowym `05514c26...` (main sprzed T034). T034 samo w sobie NIE dotyka żadnego z plików w tym traceback — to nie regresja logiki, tylko nowy, poprawny ranking T034 po raz pierwszy trafia w realny, przedtem nieteoretyzowany scenariusz.

Dokładny traceback (odtworzony lokalnie):

```
rota/application/training.py:147: in mark_training_realized
    return manual_edit.apply_manual_correction(...)
rota/application/manual_edit.py:325: in apply_manual_correction
    return lifecycle.create_schedule_version(...)
rota/persistence/schedule_lifecycle.py:168: in create_schedule_version
    status = _validate_content(...)
rota/persistence/schedule_lifecycle.py:115: in _validate_content
    validation.validate_deviations(conn, deviations, assignments_by_id, demands_by_id)
rota/persistence/schedule_validation.py:309: in validate_deviations
    _validate_one_deviation(conn, deviation, assignments_by_id, demands_by_id or {})
rota/persistence/schedule_validation.py:325: MalformedScheduleSnapshot:
    deviation 'DEV-0-REST-01': affected_assignment_or_employee must resolve to an
    Employee, a same-version Assignment, or (for COVERAGE) a same-version ShiftDemand
```

Konkretnie: wrześniowy plan tworzy Deviation `REST-01` (kategoria `LAW`), którego `affected_assignment_or_employee` wskazuje na przypisanie z **sierpnia** (`solved-2026-08-31-N-A`) — bo naruszenie odpoczynku dobowego faktycznie łączy ostatnią nockę sierpnia z pierwszą zmianą września. Walidator we wrześniu widzi tylko przypisania własnej (nowo tworzonej) wersji, więc cel Deviation nie rozwiązuje się do niczego legalnego i rzuca `MalformedScheduleSnapshot`.

## 2. Potwierdzeni właściciele kodu na exact main (`54acdf7`)

- `rota/planning/validator.py::_check_rest` (linia ~456-505) — **jedyne** miejsce budujące `ViolationDetail("REST-01", ids, ...)`. Linia 464: `all_assignments = list(assignments) + other_site_list + _not_cancelled(state.boundary_assignments)` — REST-01 (i WEEKLY-REST-01, analogicznie) **z założenia i od dawna** porównuje pary przypisań, gdzie jedno może być z `state.boundary_assignments` (sąsiedni miesiąc, ten sam obiekt) albo z `state.other_site_assignments` (inny obiekt, nakładający się okres). To nie jest przypadek ani błąd — `boundary_assignments`/`other_site_assignments` istnieją dokładnie po to.
- `rota/application/assembler.py::_assemble_cross_context` (linia ~172-181) — źródło `boundary_assignments`/`other_site_assignments`: `get_current_assignments_in_interval` / `get_current_assignments_for_employees` — to zawsze **aktualna (current) ScheduleVersion** sąsiedniego miesiąca (ten sam obiekt) lub aktualna wersja nakładającego się okresu na innym obiekcie. Nigdy stara/nadpisana wersja.
- `rota/application/deviation_mapping.py::_affected_target` (linia 51-56) — bierze `detail.assignment_ids[0]` bez rozróżniania, czy id pochodzi z bieżącej, granicznej czy innej-obiektowej wersji. `category_for_rule` (linia 40-48) mapuje `REST-01`/`WEEKLY-REST-01` → `DeviationCategory.LAW` (linia 20-23, ROTA-T023b).
- `rota/persistence/schedule_validation.py::_validate_one_deviation` (linia 312-328) — jedyne miejsce z regułą legalności celu. Ma już analogiczny, kategoriowy wyjątek dla `COVERAGE` (linia 319-323, `tasks/ROTA-T009/review_01_architect_clarification.md`): cel może być ShiftDemand **tej samej wersji**, ale tylko dla `category=COVERAGE`. Brak jakiegokolwiek odpowiednika dla `LAW`/cross-context.
- Schemat (`rota/persistence/db.py`): `assignments(schedule_version_id, assignment_id, ...)` PK złożony; `current_schedule_versions(site_id, month, version_id)` PK `(site_id, month)`, FK na `schedule_versions(version_id, site_id, month)`. Jeden JOIN wystarcza, by sprawdzić "czy ten assignment_id należy do JAKIEJKOLWIEK aktualnie-bieżącej wersji":
  ```sql
  SELECT 1 FROM assignments a
  JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
  WHERE a.assignment_id = ?
  ```
  Ten JOIN naturalnie obejmuje zarówno przypadek cross-month (ten sam obiekt, sąsiedni miesiąc), jak i cross-site (inny obiekt) — dokładnie te same dwa źródła, z których `_check_rest` buduje `all_assignments`. Nie wymaga wcześniejszej wiedzy o site_id/month danego assignment_id.

## 3. Czego NIE dotyka ten problem

- Żaden plik produkcyjny T034 (`rota/planning/fairness.py`, `rota/planning/solver.py`) — potwierdzone `git diff` bajt-w-bajt bez zmian względem `f7563c7`.
- Sam mechanizm wykrywania REST-01/cross-month — działa poprawnie i od dawna (to nie jest nowa funkcja).
- Manualna korekta (`rota/application/manual_edit.py`, linie ~66-181, `_rederive_rest01_deviations`-podobne funkcje) niezależnie odtwarza pary REST-01/WEEKLY-REST-01 — może więc produkować dokładnie ten sam kształt Deviation z tego samego powodu, niezależnie od tego, czy trafienie przyszło przez solver czy przez ręczną korektę. To sugeruje, że poprawka powinna żyć w jednym wspólnym punkcie (`_validate_one_deviation`), a nie osobno w każdym wywołującym.

## 4. Opcje nazwane przez audyt (Codex, round 3), do rozstrzygnięcia

**Opcja A (rekomendowana przeze mnie, patrz niżej):** autoryzować wąskie zadanie rozszerzające regułę legalności celu Deviation w `_validate_one_deviation`, analogicznie do już istniejącego wyjątku dla `COVERAGE`: dla `category == DeviationCategory.LAW` cel może dodatkowo rozwiązać się do Assignment należącego do **jakiejkolwiek aktualnie-bieżącej (current) ScheduleVersion** (nie tylko wersji właśnie walidowanej) — patrz zapytanie SQL w sekcji 2. Nie zmienia znaczenia REST-01/WEEKLY-REST-01, nie zmienia solvera, nie zmienia rankingu T034.

**Opcja B (Codex: „nie rekomendowana bez uzasadnienia produktowego"):** uznać oczekiwanie testu T009 za nieaktualne wobec nowego, poprawnego rankingu T034 i zmienić/usunąć asercję w `test_audit_t009_r6.py`. Problem: to nie naprawia luki — każdy przyszły plan, który trafi w analogiczny cross-month REST-01 z późniejszą korektą (nie tylko trening), rzuci ten sam `MalformedScheduleSnapshot`. Ukrywa realne naruszenie odpoczynku zamiast pozwolić je zapisać.

## 5. Moja rekomendacja (do potwierdzenia/odrzucenia przez architekta)

Opcja A, dokładnie w kształcie z sekcji 2 punkt ostatni — jeden dodatkowy warunek w `_validate_one_deviation`, gated `category == DeviationCategory.LAW`, sprawdzający istnienie assignment_id w JOIN `assignments`+`current_schedule_versions`. Zero zmian w solverze, walidatorze planowania, ani w mapowaniu kategorii. Nie wymaga nowej tabeli, nowego pola, nowej migracji.

## 6. TASK_SCOPE (proponowany, do zamrożenia przez architekta)

Production — prawdopodobnie wyłącznie:
- `rota/persistence/schedule_validation.py`

Tests:
- rozszerzenie/nowy plik pokrywający: cross-month REST-01 target legalny; cross-site REST-01 target legalny; target z NIE-bieżącej (nadpisanej) wersji nadal odrzucony; target spoza LAW nadal odrzucony na starych zasadach; `test_audit_t009_r6.py`'s `test_r6_distinct_trainings_with_same_local_id_in_different_versions_both_count` przechodzi bez zmiany swojej treści.

Nie modyfikować (do potwierdzenia przez architekta, ale nic w faktach powyżej tego nie wymaga):
- `rota/planning/validator.py`, `rota/planning/solver.py`, `rota/planning/fairness.py`, `rota/application/deviation_mapping.py`, `rota/application/assembler.py`, `rota/application/manual_edit.py`.

## 7. Pytania preimplementacyjne dla Codexa (do potwierdzenia przed implementacją)

1. Czy JOIN `assignments`+`current_schedule_versions` poprawnie i wyłącznie odtwarza dokładnie ten sam zbiór "legalnych cross-context assignmentów", z którego `_check_rest` faktycznie buduje pary (boundary + other-site), bez fałszywych pozytywów?
2. Czy ograniczenie wyjątku do `category == DeviationCategory.LAW` jest wystarczające i nie zostawia otwartej furtki dla innych kategorii?
3. Czy istnieje scenariusz, w którym `WORK_PERIOD-01` (linia 467 validator.py, osobny kod reguły, nieobecny w `_BUILTIN_RULE_CATEGORY`) mógłby też trafić do `materialize_deviations` z cross-context targetem? Jeśli tak — to osobny, nieopisany tu problem (`UnknownDeviationSource`), do zgłoszenia, nie do cichego naprawienia przy okazji.
4. Czy pełna regresja (w tym `test_audit_t009_r6.py` i cały `tests/test_t023_checkpoint_b.py`/`tests/test_sick_leave.py`/`tests/test_t017.py`, które audyt T034 osobno sklasyfikował jako niezwiązane) pozostaje zielona po tej zmianie.
