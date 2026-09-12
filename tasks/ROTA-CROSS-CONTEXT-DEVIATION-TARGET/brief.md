# ROTA-CROSS-CONTEXT-DEVIATION-TARGET — legalny target LAW z bieżącego cross-context

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@1198071074b3548727731d78c2f6df48e49f203c`

SOURCE: `arch/ARCHITECT_BRIEF_CROSS_CONTEXT_DEVIATION_TARGET_2026-08-27.md` + BOARD scope review `ROTA-CROSS-CONTEXT-vs-CORRECTION-EFFECTIVE-SCOPE`.

## 1. Cel

Naprawić wyłącznie crash `MalformedScheduleSnapshot` przy zapisie legalnego `Deviation` kategorii `LAW`, gdy jego targetem jest Assignment z kontekstu granicznego używanego przez walidację odpoczynku, ale nie należący do właśnie zapisywanej wersji.

To nie jest zmiana zasad Korekty ręcznej, solvera ani REST-01. Nie łączyć tego zadania z `ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT`.

## 2. Zamrożony fakt

`REST-01` i `WEEKLY-REST-01` celowo walidują także `boundary_assignments` i `other_site_assignments`. Legalne naruszenie może więc wskazywać Assignment z:
- bieżącej wersji sąsiedniego miesiąca tego samego obiektu;
- bieżącej wersji innego obiektu.

`_validate_one_deviation()` uznaje dziś jedynie Employee, Assignment tej samej wersji albo — wyłącznie dla `COVERAGE` — ShiftDemand tej samej wersji. Legalny cross-context target LAW jest więc odrzucany.

## 3. Zamrożone rozwiązanie

W `rota/persistence/schedule_validation.py::_validate_one_deviation` rozszerzyć wyłącznie regułę legalności targetu:

- dotychczasowe Employee / same-version Assignment / COVERAGE ShiftDemand pozostają bez zmian;
- dla `deviation.category == DeviationCategory.LAW` legalny jest dodatkowo Assignment należący do dowolnej **aktualnie bieżącej** ScheduleVersion;
- sprawdzenie ma użyć istniejących tabel `assignments` + `current_schedule_versions`;
- Assignment z wersji niebędącej już current pozostaje niedozwolony;
- żadna inna kategoria nie dostaje nowej furtki.

Minimalny sens zapytania:

```sql
SELECT 1
FROM assignments a
JOIN current_schedule_versions c ON c.version_id = a.schedule_version_id
WHERE a.assignment_id = ?
```

Nie tworzyć nowej tabeli, pola, repozytorium ani cross-context registry.

## 4. Czego nie zmieniać

Poza scope:
- `rota/application/manual_edit.py`;
- `rota/planning/validator.py`;
- `rota/planning/solver.py`;
- `rota/planning/fairness.py`;
- `rota/application/deviation_mapping.py`;
- `rota/application/assembler.py`;
- semantyka `REST-01` / `WEEKLY-REST-01`;
- zasady historycznej Korekty ręcznej.

## 5. Acceptance

A1. LAW/REST-01 targetujący Assignment z current sąsiedniego miesiąca jest legalny.

A2. LAW/REST-01 targetujący Assignment z current innego obiektu jest legalny.

A3. LAW targetujący Assignment z wersji historycznej, która nie jest current, jest odrzucony.

A4. Target spoza LAW nie uzyskuje prawa do cross-context Assignmentu.

A5. Istniejący wyjątek COVERAGE dla same-version ShiftDemand działa bez zmian.

A6. Reproduktor historycznego crasha przechodzi bez zmian w `manual_edit.py`, solverze i validatorze planowania.

## 6. Literalny TASK_SCOPE

Production:
- `rota/persistence/schedule_validation.py` — tylko rozszerzenie legalności targetu LAW jak wyżej.

Tests:
- nowy `tests/test_cross_context_deviation_target.py` albo najbliższy istniejący test validation, jeśli Codex wskaże już właściwego właściciela;
- istniejący reproduktor/test, który wcześniej wpadał w `MalformedScheduleSnapshot`, może zostać użyty jako regresja bez zmiany jego sensu.

Jeśli poprawka wymaga innego production path, CC zatrzymuje pracę i wraca do architekta.

## 7. Preimplementation check Codexa

Tylko trzy pytania:
1. Czy JOIN `assignments` + `current_schedule_versions` odpowiada dokładnie legalnemu current cross-context potrzebnemu przez REST/WEEKLY-REST?
2. Czy gate `category == LAW` nie otwiera innych kategorii?
3. Czy jeden production file wystarcza?

Jeśli 3x TAK: PASS exact SHA i zwolnienie HOLD. Bez ponownego audytu solvera.