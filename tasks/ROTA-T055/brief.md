# ROTA-T055 — uruchomić istniejący kanał ostrzeżeń niezależnego walidatora

STATUS: READY FOR PREIMPLEMENTATION AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `e64ce8f236d7d0125207de62acf8b9bd3b6d9168`

Źródła:
- `arch/FINDING_2026-09-04_VALIDATOR_WARNINGS_NEVER_SURFACED.md`
- decyzja OWNERA 2026-09-04: „to jest sprawa do całościowego naprawienia taskiem. nie możemy mieć martwych ostrzeżeń.”
- stan scalonego T052: S1 nie blokuje HARD przez REST-01/WEEKLY-REST-01, ale realne naruszenie odpoczynku wokół S1 ma być widoczne jako SOFT warning

## 1. Cel

Doprowadzić istniejące `IndependentValidationReport.warnings` do koordynatora jednym, spójnym kanałem, bez tworzenia nowego systemu ostrzeżeń.

Task NIE dodaje nowych reguł SOFT. Naprawia transport już istniejących warningów z `rota/planning/validator.py`.

## 2. Potwierdzony obecny stan

W repo istnieją dwa kanały warningów:

1. `solver.py::_collect_warnings` — wąski kanał działający na etapie niezapisanego wyniku PLAN/REPLAN; jego warnings trafiają do `PlanningResultOut.warnings` i są widoczne w UI.
2. `validator.py::validate()` — szerszy kanał `IndependentValidationReport.warnings`, dziś obliczany przy `select_candidate` i `apply_manual_correction`, ale niewidoczny w API/UI.

`MonthlyPlanning.tsx` już renderuje `MonthViewOut.warnings` w istniejącym bannerze `Uwaga:`. Każdy write na tym ekranie i tak kończy się zwykłym reloadem miesiąca przez `GET /workspace/sites/{site_id}/schedule/{month}`.

`open_month()` już wywołuje `assemble_planning_state()` i posiada `state.existing_assignments`, czyli aktualny snapshot potrzebny do niezależnej walidacji.

## 3. Decyzje architektoniczne — zamrożone dla T055

1. **Jedyny docelowy kanał warningów aktualnego zapisanego grafiku to istniejące `MonthViewOut.warnings`.** Nie dodawać nowych pól warningów do odpowiedzi `select_candidate` ani `apply_manual_correction`.
2. **Warningi validatora mają przeżyć zwykły reload bez persistence.** Przy otwieraniu miesiąca należy ponownie uruchomić niezależny validator na aktualnym snapshotcie i dołączyć jego `report.warnings` do istniejących `OpenMonthView.warnings` / `MonthViewOut.warnings`.
3. **Nie persistować warningów.** Są pochodną aktualnego grafiku i aktualnych wejść/rules; nie są nowym durable business state.
4. **Nie dodawać tabeli, kolumny, statusu, markera, warning-history ani warning-ack subsystemu.**
5. **Nie zmieniać semantyki żadnej istniejącej reguły warningowej.** T055 nie modyfikuje warunków DAY_ONLY-N-FALLBACK-01, DAY_SHIFT_OFF-01, LEAVE_PLAN-01, REST-01 SOFT ani WEEKLY-REST-01 SOFT.
6. **Wszystkie istniejące warnings validatora wychodzą jednym taskiem.** Nie robić wariantu „najpierw tylko S1”. Powód: OWNER zlecił całościowe usunięcie martwego kanału.
7. **Nie usuwać solver-side `DAY_SHIFT_OFF-01 SOFT` w T055.** Ten warning działa na etapie jeszcze niezapisanego candidate preview, gdzie current snapshot nie zawiera kandydata. Usunięcie go pogorszyłoby zachowanie PLAN/REPLAN przed `select_candidate`.
8. Jeśli po zapisaniu grafiku ten sam warning pochodzi z validatora, to jest poprawny kanał current-state. Nie budować osobnej deduplikacji między transient `PlanningResult.warnings` i późniejszym `MonthViewOut.warnings`, bo nie są wyświetlane jako jeden równoczesny payload.
9. `open_month()` pozostaje read-only. Uruchomienie `validate()` w read path nie może niczego zapisywać ani materializować jako Deviation.
10. Jeśli dla miesiąca nie ma current ScheduleVersion, nie ma current snapshotu do walidacji; zwracane są wyłącznie istniejące assembler/open-month warnings.

## 4. Minimalna architektura

Najmniejszy flow:

`GET month -> open_month() -> assemble_planning_state() -> validate(state, current assignments) -> merge existing open_month warnings + report.warnings -> MonthViewOut.warnings -> istniejący banner "Uwaga"`

Preferowany owner to `rota/application/open_month.py`, ponieważ:
- to istniejący owner read-modelu miesiąca;
- już posiada złożony `PlanningState`;
- warningi mają być częścią readbacku current state, nie specjalną własnością HTTP routera;
- router ma pozostać warstwą marshalling.

Nie wywoływać ponownie assemblowania stanu w routerze tylko dla warningów.

## 5. Merge warningów

- Zachować istniejące assembler warnings.
- Dołączyć `IndependentValidationReport.warnings` z aktualnego snapshotu.
- Nie usuwać żadnej klasy warningów tylko dlatego, że podobna logika istnieje w solverze.
- Jeśli dokładnie identyczny string pojawi się dwukrotnie w tym samym `MonthViewOut.warnings`, można zastosować prostą stabilną deduplikację zachowującą pierwszą kolejność. Nie budować warning IDs ani nowego modelu danych.

## 6. Write flows

### SELECT CANDIDATE
`select_candidate()` nadal używa validatora do HARD validation i nie musi rozszerzać swojego response contractu o warnings. Po sukcesie istniejący frontend robi `load()`, a GET miesiąca ma pokazać warningi current snapshotu.

### MANUAL CORRECTION
`apply_manual_correction()` nadal materializuje istniejące HARD deviations według obecnego kontraktu. Nie persistować SOFT warnings jako Deviations. Po sukcesie istniejący reload miesiąca pokazuje warningi validatora.

### PLAN/REPLAN candidate preview
`PlanningResultOut.warnings` pozostaje istniejącym kanałem transient wyniku solvera. T055 nie przebudowuje PlanningResult i nie przenosi wszystkich warningów current-state do candidate preview.

## 7. TASK_SCOPE

Dozwolony kod produktu:
- `rota/application/open_month.py`
- `rota/planning/validator.py` wyłącznie jeśli potrzebny jest mały read-only helper/adaptor do bezpiecznego pobrania warnings; NIE zmieniać reguł warningowych
- `api/routers/schedule.py` tylko jeśli marshalling istniejącego pola `warnings` wymaga minimalnej korekty; preferowane zero zmian
- `frontend/src/screens/MonthlyPlanning.tsx` tylko jeśli istniejący banner nie wystarczy; preferowane zero zmian

Dozwolone testy/dokumenty:
- `tasks/ROTA-T055/brief.md`
- małe testy targetowane readbacku GET/open_month + jeden real-flow write->GET

Poza zakresem:
- nowe reguły warningowe
- nowe DB schema/persistence warningów
- warning history / acknowledgment / dismiss state
- zmiana Deviation modelu
- nowe pola odpowiedzi write endpointów
- refaktor solvera/validatora
- usuwanie solver-side warningów
- zmiana HARD/SOFT klasyfikacji jakiejkolwiek reguły
- deduplikacja semantyczna po kodach/ID lub nowy Warning DTO

## 8. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T055/brief.md
- rota/application/open_month.py
- rota/planning/validator.py
- api/routers/schedule.py
- frontend/src/screens/MonthlyPlanning.tsx

## 9. Acceptance

T55-01: current ScheduleVersion, dla którego `validate()` zwraca `DAY_ONLY-N-FALLBACK-01 SOFT`, po zwykłym `GET month` zwraca ten warning w istniejącym `MonthViewOut.warnings`.

T55-02: analogicznie `LEAVE_PLAN-01 SOFT` jest widoczne przez zwykły GET bez PLAN/REPLAN i bez nowego endpointu.

T55-03: S1 powodujące realny niedobór dobowego odpoczynku nadal NIE blokuje HARD, ale `REST-01 SOFT` pojawia się w `MonthViewOut.warnings` po zapisie i po reloadzie.

T55-04: S1 naruszające realne 35 h odpoczynku nadal NIE blokuje HARD, ale `WEEKLY-REST-01 SOFT` pojawia się w `MonthViewOut.warnings` po zapisie i po reloadzie.

T55-05: `select_candidate` z poprawnym HARD kandydatem zapisuje grafik jak dziś; następny istniejący `GET month` pokazuje warnings validatora. Response contract `select_candidate` pozostaje bez nowego warnings payload.

T55-06: `apply_manual_correction` zapisuje jak dziś; następny istniejący GET pokazuje warnings validatora. Warning SOFT nie jest materializowany jako Deviation.

T55-07: zwykły reload aplikacji odtwarza te same warnings z aktualnego stanu przez ponowne `validate()`. W DB nie ma nowego rekordu warninga.

T55-08: miesiąc bez current ScheduleVersion nie wywołuje sztucznego warning state i zachowuje dotychczasowe assembler warnings.

T55-09: transient warning solvera dla PLAN/REPLAN przed select pozostaje dostępny jak dziś; T055 go nie usuwa.

T55-10: istniejące HARD validation, finalization, deviations i schedule content pozostają bez zmian.

## 10. PREIMPLEMENTATION AUDIT

Audytor ma sprawdzić wyłącznie:
- czy `open_month()` ma komplet current state potrzebny do `validate()` bez drugiego assemblowania;
- czy `validate()` jest read-only i bezpieczny w GET path;
- czy `state.existing_assignments` jest właściwym current snapshotem dla tego readbacku;
- czy istniejący `MonthViewOut.warnings` + banner `MonthlyPlanning` wystarczają bez nowych response fields;
- czy solver-side warning musi zostać zachowany dla niezapisanego preview;
- czy scope jest wystarczający i nie wymaga DB/frontend redesignu.

Oczekiwany werdykt: `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL` z konkretnym trace do istniejącego kodu.

Test nie tworzy kontraktu.