# ROTA-T058 — HARD zakaz trzeciej kolejnej służby + 24h pasmo equity

STATUS: READY FOR FINAL NARROW RECHECK — IMPLEMENTATION HOLD

BASE_MAIN_SHA: `298ddb9557455a574959876c38be1ebd7493319a`
SOURCE_FINDING: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` @ `c174c2e`
OWNER_CORRECTION: main@`500b337dd86f43c7d978c9afc2b4a7ccabd13249`
PREIMPLEMENTATION_AUDIT_R1: `tasks/ROTA-T058/round_01/tests/tests_r1.txt` @ `c21e80f`
PREIMPLEMENTATION_AUDIT_R2: `tasks/ROTA-T058/round_01/tests/tests_r2.txt` @ `3e49b1a`

## 1. Cel

Naprawić priorytety automatycznego solvera bez odebrania koordynatorowi istniejącej władzy ręcznej korekty i bez zmiany znaczenia TARGET-01:

1. automatyczny PLAN/REPLAN/Przelicz Plan nigdy sam nie tworzy trzeciej kolejnej służby tego samego pracownika na trzech kolejnych datach rozpoczęcia;
2. ręczna korekta koordynatora może świadomie utworzyć taki układ, ale program musi go oflagować jako odchylenie i zapisać ślad decyzji człowieka;
3. ogólny rytm D/N/W/W pozostaje SOFT;
4. equity dostaje dopuszczalne pasmo 24h, wewnątrz którego solver nie psuje rytmu tylko dla dalszego wyrównania;
5. TARGET-01 pozostaje bez zmian.

## 2. Zamrożony kontrakt OWNERA

### 2.1 HARD wiąże automat

Dla jednego pracownika każda nowa automatyczna sekwencja służb rozpoczynających się na trzech kolejnych datach kalendarzowych jest zabroniona.

Zakaz dotyczy PRIMARY realnej służby pracownika niezależnie od kombinacji D/N. Nie budować go z surowego `any_term`, bo ten obejmuje również TRAINEE i PERIODIC_TRAINING. Jedna data rozpoczęcia liczy się raz także dla pracy 24h D+N.

PLAN/REPLAN/Przelicz Plan nie dostaje wyjątku przez `DECISION_REQUIRED`. Jeśli solver musiałby dołożyć nową trzecią kolejną służbę, nie może zwrócić takiego kandydata jako FEASIBLE. Użytkownik dostaje czytelny komunikat i recovery przez zmianę obsady/dostępności oraz ponowienie planowania.

Istniejący `NIGHT-STREAK-01` pozostaje własnym, węższym HARD i zachowuje swój dotychczasowy lifecycle. T058 nie rozszerza jego ścieżki wyjątku na ogólny zakaz trzech kolejnych służb.

### 2.2 HARD nie odbiera władzy koordynatorowi

Ręczna korekta pozostaje istniejącą ścieżką świadomej decyzji człowieka. Koordynator może utworzyć układ naruszający nowy HARD.

W takim przypadku:
- validator wykrywa nazwane naruszenie;
- istniejący mechanizm `validate -> materialize_deviations -> coordinator action` zapisuje odchylenie i ślad decyzji;
- `rota/application/deviation_mapping.py` mapuje nowy built-in rule do istniejącej kategorii Deviation;
- `api/routers/schedule.py` wystawia dla niego czytelną polską etykietę, bez surowego technicznego kodu w UI;
- program nie przedstawia tego wyniku jako automatycznie zgodnego z HARD;
- nie tworzyć drugiego systemu wyjątków, nowej tabeli, nowego DTO ręcznej korekty ani osobnego subsystemu decyzji.

T058 nie wprowadza własnej blokady wydruku. Wydruk grafiku z odchyleniami należy do osobnego kontraktu jednorazowego potwierdzenia przed każdym wydrukiem.

### 2.3 Fixed facts, przeszłość i granice miesiąca

Służby już rozpoczęte/odbyte oraz inne jawnie zapisane fakty pozostają faktami. Późniejszy automat nie może ich cicho cofnąć ani przepisać tylko dlatego, że dzisiejszy validator wykrywa w ich oknie nowy HARD.

W pełni istniejące/odbyte okno trzech kolejnych służb nie może samo w sobie zatruć całego planowania przyszłości.

Jednocześnie fixed/boundary facts uczestniczą w decyzji, czy solver może dołożyć NOWĄ służbę. Jeśli dwa wcześniejsze dni są już faktami, a kandydat trzeciego dnia tworzyłby nowe zabronione okno, solver musi go zablokować.

Zakaz działa przez granicę miesiąca.

### 2.4 Rytm D/N/W/W

Ogólny rytm D/N/W/W pozostaje SOFT. Nowy automatyczny HARD ma przed nim pierwszeństwo.

### 2.5 TARGET-01

Nie zmieniać semantyki TARGET-01 ani jego danych wejściowych. Minimalizacja sumarycznej odchyłki od target_hours pozostaje obowiązująca.

### 2.6 Equity z pasmem 24h

24h jest martwą strefą rankingu SOFT, nie HARD.

- różnica godzin <=24h nie daje dodatkowej korzyści za dalsze wyrównywanie;
- różnica >24h może nadal wpływać na ranking;
- wynik >24h pozostaje legalny;
- deadband ma działać na istniejących canonical worked-hours expressions;
- analogiczna tolerancja musi objąć fallback `add_equal_split_fairness`, gdy brakuje targetów, inaczej ta ścieżka nadal może psuć rytm dla sub-24h wyrównania.

Nie tworzyć drugiego równoległego liczenia godzin.

## 3. Wymagane zachowanie użytkowe

Scenariusz A — automat, rozwiązanie możliwe:
- solver zwraca legalny wynik;
- nie dokłada pracownikowi nowej trzeciej kolejnej służby.

Scenariusz B — automat, rozwiązanie niemożliwe:
- pełne pokrycie wymagałoby dołożenia nowej trzeciej kolejnej służby;
- solver nie zwraca takiego kandydata;
- brak automatycznego `DECISION_REQUIRED` override;
- UI/API pokazuje czytelny komunikat.

Scenariusz C — ręczna korekta:
- koordynator świadomie tworzy trzecią kolejną służbę;
- zapis nie jest blokowany przez T058;
- validator materializuje nazwane odchylenie;
- coordinator action zachowuje ślad decyzji;
- API/UI pokazuje czytelną polską etykietę tego odchylenia, nie surowy kod reguły.

Scenariusz D — equity <=24h:
- przy równej jakości TARGET-01 solver nie psuje lepszego rytmu tylko po to, by dalej zmniejszyć różnicę mieszczącą się w 24h.

Scenariusz E — equity >24h:
- equity może preferować zmniejszenie różnicy, ale pozostaje SOFT.

Scenariusz F — boundary/fixed:
- dwa istniejące dni + nowa służba trzeciego dnia: nowa służba zablokowana;
- w pełni istniejące/odbyte trzydniowe okno: zachowane jako fakt i nie blokuje niezwiązanej przyszłości.

## 4. Zakaz rozszerzania zakresu

Poza T058:
- zmiana REST-01, LOAD-01, MEMBERSHIP-01;
- zmiana NIGHT-STREAK-01 poza współistnieniem z nowym HARD;
- zmiana TARGET-01 lub jego danych wejściowych;
- nowe ustawienie w Control Panel;
- nowy system wyjątków lub nowy `DECISION_REQUIRED` dla tego HARD;
- nowa blokada eksportu/PDF;
- przebudowa całej funkcji celu;
- rozszerzanie historycznej Korekty ręcznej/REALIZED poza istniejący kontrakt;
- refaktoryzacje „przy okazji”.

## 5. PREIMPLEMENTATION WHERE_MAP — wykonany w R1

WHERE_MAP:
- MODE: REQUIRED
- EXECUTION_STATUS: SATISFIED_BY_R1
- REPORT: `tasks/ROTA-T058/round_01/tests/tests_r1.txt`
- IMPLEMENTATION: HOLD until final narrow re-check PASS

Zamrożone techniczne redukcje z R1/R2:
- reuse istniejącego ownera klasyfikacji/dzień z `solver._build_day_kind_terms`, ale dla nowego HARD użyć PRIMARY occupancy per employee/date, nie surowego `any_term`;
- CP-SAT HARD umieścić z constraints, wpiąć raz w solverze i usunąć stary third-shift SOFT oraz jego objective-bound bookkeeping;
- validator ma niezależnie sprawdzać PRIMARY start-date occupancy bez tworzenia drugiego D/N classifiera;
- nowy rodzaj infeasible diagnozować osobno od NIGHT-STREAK-01 i REST-01, bez coordinator override;
- reuse istniejącego preview cleanup, Deviation persistence i coordinator action log;
- `deviation_mapping.py` dostaje tylko mapowanie nowego built-in rule do istniejącej kategorii;
- `api/routers/schedule.py` dostaje tylko czytelną polską etykietę nowego Deviation;
- 24h deadband objąć target equity oraz missing-target equal-split fallback.

## 6. Acceptance

T58-01: automatyczny PLAN/REPLAN/Przelicz Plan nie proponuje nowej trzeciej kolejnej służby tego samego pracownika na trzech kolejnych datach rozpoczęcia.

T58-02: nowy HARD dotyczy PRIMARY realnej służby i jednej okupacji daty, nie TRAINEE/S1 ani podwójnego liczenia D+N 24h.

T58-03: zakaz działa przez granicę miesiąca i wobec fixed/boundary facts przy dokładaniu nowej służby.

T58-04: brak legalnej automatycznej obsady nie prowadzi do coordinator override; użytkownik dostaje czytelny komunikat i brak FEASIBLE kandydata łamiącego HARD.

T58-05: ręczna korekta może świadomie zapisać naruszenie; validator materializuje nazwane Deviation, istniejący coordinator action trail zapisuje decyzję, a API/UI pokazuje czytelną polską etykietę zamiast surowego kodu reguły.

T58-06: późniejszy automat nie cofa po cichu ręcznie zaakceptowanej/odbytej decyzji i w pełni fixed historyczne okno nie blokuje niezwiązanej przyszłości.

T58-07: NIGHT-STREAK-01 pozostaje poprawne i nie jest osłabione.

T58-08: D/N/W/W pozostaje SOFT.

T58-09: TARGET-01 zachowuje dotychczasową semantykę i priorytet.

T58-10: target equity nie daje dodatkowej korzyści za zmniejszanie różnicy <=24h.

T58-11: missing-target equal-split fairness również respektuje deadband 24h.

T58-12: różnica >24h pozostaje legalna i equity może ją zmniejszać tylko jako SOFT.

T58-13: solver i validator zgadzają się co do reprezentatywnych scenariuszy nowego HARD, przy zachowaniu niezależności walidacji.

T58-14: T058 nie dodaje własnej blokady PDF/eksportu ani nowego subsystemu wyjątków.

## 7. EXACT TASK_SCOPE — FROZEN

READ_ONLY_EVIDENCE:
- arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md
- BOARD.md
- tasks/ROTA-T058/round_01/tests/tests_r1.txt
- tasks/ROTA-T058/round_01/tests/tests_r2.txt
- rota/application/manual_edit.py

TASK_SCOPE:
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/fairness.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/engine_types.py
- rota/application/plan_ops.py
- rota/application/deviation_mapping.py
- api/routers/schedule.py
- frontend/src/api/client.ts
- frontend/src/screens/MonthlyPlanning.tsx
- tests/test_t034_third_consecutive_shift_soft.py
- tests/test_t058.py

`engine_types.py`, `plan_ops.py`, `frontend/src/api/client.ts` i `MonthlyPlanning.tsx` wolno zmieniać wyłącznie, jeśli rzeczywiście potrzebny jest truthful non-decision result/status i jego czytelna prezentacja. `deviation_mapping.py` wolno zmienić wyłącznie o mapowanie nowego built-in rule do istniejącej kategorii, a `api/routers/schedule.py` wyłącznie o czytelną polską etykietę nowego Deviation. Nie tworzyć nowego payloadu/subsystemu.

Jeżeli implementacja wymaga innego istniejącego pliku, STOP i powrót do Architekta przed edycją.
