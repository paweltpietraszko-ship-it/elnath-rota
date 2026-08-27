# ROTA-T036 — REST/WEEKLY Deviation target bez cross-context Assignment lookup

Status: **READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS**

BASE_MAIN_SHA: `54acdf7cfebadefe1e3370bac0a62f963c72123e`
OWNER_INPUT: `arch/ARCHITECT_BRIEF_CROSS_CONTEXT_DEVIATION_TARGET_2026-08-27.md`
ARCHITECT_DECISION_DATE: 2026-08-27

## 1. Problem

`REST-01` może być wyprowadzony z pary, w której jeden Assignment należy do bieżącej ScheduleVersion, a drugi do canonical `boundary_assignments` lub `other_site_assignments`.

Obecny `deviation_mapping._affected_target()` bierze po prostu `ViolationDetail.assignment_ids[0]`. Jeżeli pierwszy element pochodzi z cross-context, `schedule_validation._validate_one_deviation()` odrzuca Deviation, ponieważ trwały target Assignment musi dziś rozwiązać się do Assignment bieżącej wersji.

Nie wolno naprawiać tego przez JOIN po samym `assignment_id` do wszystkich current ScheduleVersions. To byłoby szersze niż faktyczny kontekst walidacji, a T008 identity Assignment jest złożone: `(schedule_version_id, assignment_id)`.

## 2. Rozstrzygnięcie architektoniczne

**Nie rozszerzamy persistence o cross-context Assignment targety.**

Dla dokładnie dwóch built-in source references:

- `REST-01`;
- `WEEKLY-REST-01`;

persistent `Deviation.affected_assignment_or_employee` wskazuje **Employee**, którego dotyczy naruszenie, a nie jeden z Assignmentów składających się na naruszenie.

Uzasadnienie:

1. oba HARD-y są wyprowadzane per employee;
2. `Deviation` już od początku dopuszcza target Employee lub Assignment — nie powstaje nowy typ targetu;
3. `employee_id` jest jednoznaczny i już jest persistence-validated przez istniejącą regułę;
4. nie trzeba rozszerzać globalnej tożsamości Assignment ani udawać, że bare `assignment_id` jest globalnym kluczem;
5. dokładne Assignmenty nadal pozostają w `ViolationDetail.assignment_ids` dla diagnostyki, a manual REST override nadal zapisuje swoje istniejące szczegółowe pary/fakty;
6. nie powstaje SQL wyjątek dla `DeviationCategory.LAW`, więc przyszła reguła LAW nie dziedziczy automatycznie tej semantyki.

To jest zmiana sposobu materializacji targetu Deviation, nie zmiana HARD REST/WEEKLY.

## 3. ViolationDetail — minimalny jawny employee seam

W `rota/planning/validator.py` rozszerzyć `ViolationDetail` o jedno końcowe, compatibility-defaulted pole:

`affected_employee_id: str | None = None`

Nie parsować employee z `message` i nie odtwarzać go z Assignment IDs w application layer.

### 3.1 REST-01

Każdy `ViolationDetail("REST-01", ...)` utworzony w `_check_rest()` musi dostać dokładny `affected_employee_id=employee_id`, który jest już ownerem pętli wyprowadzającej to naruszenie.

Nie zmieniać:

- `assignment_ids`;
- sposobu grupowania WorkPeriod;
- boundary/other-site scope;
- REST gap/overlap/zero-gap semantyki;
- OCHRONA 24h floor.

### 3.2 WEEKLY-REST-01

Każdy `ViolationDetail("WEEKLY-REST-01", ...)` utworzony w `_check_weekly_rest()` dostaje `affected_employee_id=employee_id`.

Boundary nadal wpływa na obliczenie weekly rest dokładnie jak dziś. `assignment_ids` pozostają dotychczasowymi current-month IDs diagnostycznymi; persistent target Deviation jest Employee.

### 3.3 Inne reguły

Wszystkie pozostałe `ViolationDetail` zachowują `affected_employee_id=None` i dotychczasową semantykę.

W szczególności T036 NIE dotyka `WORK_PERIOD-01`. Jeżeli kiedyś jego materializacja ujawni osobny problem, to osobny task; nie dodawać go przy okazji.

## 4. deviation_mapping — source-specific, bez category-wide wyjątku

W `rota/application/deviation_mapping.py` `_affected_target(detail)` ma zachować istniejący porządek dla wszystkich źródeł poza dwoma wskazanymi niżej.

Dla `detail.rule in {"REST-01", "WEEKLY-REST-01"}`:

- wymagaj `detail.affected_employee_id`;
- zwróć dokładnie ten `employee_id`;
- brak pola = `UnknownDeviationSource` / fail closed;
- nie wybieraj Assignmentu z `assignment_ids`;
- nie parsuj `message`.

Dla wszystkich innych reguł pozostaje obecny mechanizm:

1. jeśli `demand_ids` — pierwszy demand;
2. w przeciwnym razie jeśli `assignment_ids` — pierwszy assignment;
3. brak targetu — fail closed.

`category_for_rule()` pozostaje bez zmian. `REST-01` i `WEEKLY-REST-01` nadal mapują się do `DeviationCategory.LAW`.

## 5. Persistence — bez zmian

Nie zmieniać `rota/persistence/schedule_validation.py`.

Nie dodawać:

- JOIN `assignments + current_schedule_versions`;
- listy dozwolonych cross-context targetów;
- `affected_schedule_version_id`;
- migracji DB;
- nowego target-kind pola;
- encoded composite IDs w istniejącym stringu.

Istniejący invariant persistence zostaje:

- Employee target musi istnieć w `employees`;
- Assignment target musi być same-version;
- COVERAGE może wskazać same-version ShiftDemand.

To jest celowe: T036 usuwa potrzebę cross-context Assignment persistence zamiast rozszerzać jego zasięg.

## 6. Dlaczego nie Opcja A z briefu wejściowego

Opcja A („bare assignment_id istnieje w dowolnej current ScheduleVersion”) jest odrzucona.

Powody:

- akceptuje assignment z niepowiązanego Site/month/Employee tylko dlatego, że lokalny ID się zgadza;
- nie odtwarza dokładnie assemblerowego boundary/other-site contextu;
- ignoruje złożoną identity `(schedule_version_id, assignment_id)`;
- po zapisie nadal nie wiadomo, który z kilku current Assignmentów o tym samym local ID był targetem;
- kategoriowy gate `LAW` byłby za szeroki.

T036 nie potrzebuje pełnej cross-context Assignment identity, ponieważ dla REST/WEEKLY prawdziwy trwały podmiot naruszenia jest już reprezentowalny przez istniejący Employee target.

## 7. TASK_SCOPE

Production — dokładnie:

- `rota/planning/validator.py`;
- `rota/application/deviation_mapping.py`.

Tests — jeden focused moduł, np.:

- `tests/test_t036_rest_deviation_target.py`.

Nie modyfikować:

- `rota/persistence/schedule_validation.py`;
- `rota/persistence/schedule_lifecycle.py`;
- `rota/persistence/db.py`;
- `rota/domain.py`;
- assembler;
- solver/fairness/constraints;
- manual REST override derivation;
- API/frontend;
- T034 ranking.

## 8. Minimalna macierz odbioru

T36-01 — pure mapping: `REST-01` z `affected_employee_id="E1"` materializuje Deviation target `E1`, nawet jeśli `assignment_ids[0]` jest bare ID cross-context Assignmentu.

T36-02 — analogicznie `WEEKLY-REST-01`.

T36-03 — REST/WEEKLY bez `affected_employee_id` fail closed; żadnego parsowania message.

T36-04 — validator `_check_rest` na cross-month REST pair zwraca detail z poprawnym employee ID oraz zachowuje oba assignment IDs diagnostycznie.

T36-05 — cross-site REST pair analogicznie wskazuje Employee i nie potrzebuje persistence lookup obcego Assignmentu.

T36-06 — WEEKLY-REST-01 zachowuje dotychczasowy boundary calculation i niesie jawny employee ID.

T36-07 — zwykła non-REST reguła z Assignment targetem zachowuje dotychczasowe same-version wymaganie persistence; ręcznie skonstruowany obcy Assignment target nadal jest odrzucany.

T36-08 — COVERAGE target ShiftDemand pozostaje bez zmian.

T36-09 — source_reference inny niż dokładnie `REST-01`/`WEEKLY-REST-01` nie dostaje employee-target semantyki tylko dlatego, że jego category byłaby LAW.

T36-10 — istniejący `tests/test_audit_t009_r6.py::test_r6_distinct_trainings_with_same_local_id_in_different_versions_both_count` przechodzi bez zmiany treści testu w scenariuszu, który ujawnił problem.

T36-11 — revalidate/finalize/manual-correction materializujące REST/WEEKLY przechodzą przez istniejący lifecycle bez zmian persistence.

## 9. Preimplementation reduction gate

Pozostają tylko dwa konieczne ruchy:

1. validator niesie jawnie employee, którego już zna podczas wyprowadzania REST/WEEKLY;
2. mapper wybiera Employee jako trwały target dokładnie dla tych dwóch source references.

Usunięte jako niepotrzebne:

- nowa cross-context identity w Deviation;
- migration/schema;
- persistence SQL exception;
- assembler whitelist;
- category-wide LAW gate;
- duplicate lookup logic;
- zmiany solvera/HARD.

## 10. Codex preimplementation audit

Audit exact contract HEAD i odpowiedz:

1. Czy Employee jest prawdziwym, jednoznacznym istniejącym targetem dla REST-01/WEEKLY-REST-01 bez zmiany ich HARD semantyki?
2. Czy `affected_employee_id` jest wyprowadzany w validatorze z już znanego employee, bez message parsing i bez drugiego ownera?
3. Czy mapper jest gated dokładnie po source_reference `REST-01`/`WEEKLY-REST-01`, nie po `DeviationCategory.LAW`?
4. Czy assignment_ids pozostają dostępne diagnostycznie, mimo że trwały target jest Employee?
5. Czy persistence pozostaje bez zmian i nadal odrzuca arbitrary cross-context Assignment targets?
6. Czy COVERAGE i wszystkie inne source mappings pozostają bez zmian?
7. Czy T009 reproducer z reused local assignment_id przechodzi bez wprowadzania bare-ID global lookup?
8. Czy production scope można zamknąć w `validator.py + deviation_mapping.py`?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.
