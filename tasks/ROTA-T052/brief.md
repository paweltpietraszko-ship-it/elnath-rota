# ROTA-T052 — S1 okresowe szkolenie jako ręczny czas pracy w grafiku

STATUS: READY FOR PREIMPLEMENTATION AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `7cd5fde8446bd08a02c647d4eabaab9db200acba`

Źródła:
- `arch/FINDING_2026-09-03_PERIODIC_TRAINING_S1.md`
- `arch/ARCHITECT_HANDOFF_UX_BACKLOG_06_08_2026-09-03.md`
- decyzje OWNERA 2026-09-03

## 1. Cel

Dodać kod `S1` oznaczający szkolenie okresowe pracownika. Koordynator ręcznie ustawia dzień oraz przedział godzin. S1 jest widoczne na grafiku i wydruku oraz liczy się jako czas pracy.

S1 NIE jest onboardingowym `TRAINEE`, NIE jest demandem D/N i NIE jest funkcją kadrową.

## 2. Decyzje OWNERA — zamrożone

1. S1 dysponuje wyłącznie koordynator. Solver nigdy sam nie proponuje ani nie generuje S1.
2. Koordynator ustala start/end S1; brak sztywnej długości, minimum lub maksimum specyficznego dla S1.
3. Godziny S1 są godzinami pracy.
4. S1 uczestniczy w istniejących ograniczeniach czasu pracy, w szczególności:
   - nie może być traktowane jako „pusty czas” przy nakładaniu pracy;
   - wpływa na REST-01 zgodnie z istniejącą semantyką okresów pracy;
   - wpływa na rolling-7d `LOAD-01` / próg profilu;
   - wpływa na bilans planned/realized hours w taki sam sposób jak inny rzeczywisty czas pracy odpowiedniego state.
5. S1 nie pokrywa PRIMARY demand i nie zmienia coverage.
6. S1 nie wpływa na `READY_FOR_PRIMARY`, threshold szkolenia wdrożeniowego ani istniejące `TRAINEE`.
7. Rota nie ewidencjonuje wykonania szkolenia jako moduł HR, ważności certyfikatów, terminów kolejnych szkoleń ani dopuszczeń do pracy.

## 3. Proponowana minimalna architektura do audytu

Najmniejszym istniejącym agregatem zawierającym pracownika, przedział czasu, state, ScheduleVersion i historię jest `Assignment`.

Na BASE_MAIN_SHA tabela `assignments.role` jest `TEXT NOT NULL` bez SQL CHECK ograniczającego ją do dwóch wartości. Obecny model domenowy ma jednak wyłącznie role `PRIMARY` i `TRAINEE` oraz wiele jawnych reguł tych dwóch ról.

Propozycja architekta: rozszerzyć `AssignmentRole` o trzecią semantycznie jednoznaczną rolę, np. `PERIODIC_TRAINING`, której widocznym kodem operacyjnym jest `S1`.

To NIE jest zgoda na „przerobienie TRAINEE”. Nowa rola ma własne invarianty:
- `covers_demand_id = None`;
- `mentor_primary_assignment_id = None`;
- nie bierze udziału w coverage/mentor/readiness;
- jest fixed/manual-only dla solvera;
- jest normalnym przedziałem pracy dla overlap/rest/load/balance;
- należy do complete ScheduleVersion snapshot i historii tak jak pozostałe wpisy grafiku.

Jeżeli preimplementation audit wykaże, że rozszerzenie AssignmentRole łamie fundamentalny invariant albo wymaga większej zmiany niż osobny lekki byt czasu pracy, audyt ma zwrócić FAIL z konkretnym trace. Nie wolno samodzielnie przeprojektować tasku na moduł HR lub nowy subsystem.

## 4. Konfiguracja kodu S1

W `Kody zmian` S1 ma własny start/end ustawiany przez koordynatora, bez fixed-duration validation D1-D5/N1-N5.

Nie wciskać S1 do `WORK_CODE_KEYS` jako D/N z fałszywą frozen duration i nie reużywać N5/reserve slotu.

Najmniejsza reprezentacja ustawienia ma przechować tylko przedział S1 potrzebny jako wartość domyślna/konfiguracyjna UI. Nie budować katalogu wielu typów szkoleń.

Koordynator przy wpisaniu S1 na konkretny dzień może użyć skonfigurowanego przedziału; task nie dodaje automatycznego cyklu/recurrence generatora.

## 5. Planowanie i walidacja

Solver:
- nigdy nie tworzy S1;
- istniejące S1 w ScheduleVersion traktuje jako ręcznie ustalony/fixed czas pracownika przy ocenie dostępności i HARD czasu pracy;
- nie używa S1 do pokrycia demandu.

Independent validator:
- nie wymaga `covers_demand_id` dla PERIODIC_TRAINING;
- nie stosuje mentor/readiness reguł TRAINEE;
- stosuje właściwe reguły overlap/rest/load do przedziału S1;
- coverage liczy wyłącznie PRIMARY jak dziś.

REPLAN:
- S1 jest ręcznym faktem grafiku i nie może zostać samodzielnie usunięte/przesunięte przez solver. Koordynator zmienia/usuwa je jawnie.

## 6. Godziny

`rota/balance.py` obecnie liczy tylko `AssignmentRole.PRIMARY`; po T052 S1 ma być uwzględnione w planned/realized hours, bez podwójnego liczenia i bez wliczania onboarding `TRAINEE`, jeśli ten dziś nie jest liczony.

Nie zmieniać definicji target hours ani absence hours.

## 7. UI

`MonthlyPlanning`:
- możliwość ręcznego wpisania S1 pracownikowi na konkretny dzień;
- start/end zgodne z ustawieniem S1, z możliwością świadomego ustawienia przedziału według istniejącego uzgodnionego UX;
- S1 wyraźnie widoczne w siatce jako `S1`;
- usunięcie/zmiana S1 jest jawna operacja koordynatora.

`PrintSettings`/Kody zmian:
- S1 jako oddzielny wiersz z start/end;
- brak wymuszania długości właściwej dla D/N.

Wydruk:
- komórka S1 renderuje symbol `S1`;
- legenda zawiera S1 jako szkolenie okresowe;
- nie nazywać go onboarding/TRAINEE.

## 8. Właściciele logiki

- domain role/invariants: `rota/domain.py`
- schedule persistence/lifecycle: istniejący `assignments` + `schedule_repository`/`schedule_lifecycle`; nowa tabela tylko jeśli audit udowodni, że AssignmentRole nie jest bezpieczne
- manual coordinator write: istniejący owner ręcznych korekt (`rota/application/manual_edit.py`) lub najmniejsza istniejąca operacja wskazana przez audit
- planning fixed/time constraints: istniejący solver/validator/work-period owners
- hours: `rota/balance.py`
- API: istniejący schedule/manual-correction router
- UI: `MonthlyPlanning` + `PrintSettings`
- PDF: `schedule_export.py`

## 9. TASK_SCOPE

Dozwolony kod produktu, jeśli preimplementation audit potwierdzi AssignmentRole approach:
- `rota/domain.py`
- `rota/application/manual_edit.py`
- `rota/balance.py`
- `rota/planning/solver.py`
- `rota/planning/validator.py`
- `rota/planning/work_periods.py` tylko jeśli istniejący shared oracle wymaga jawnego uwzględnienia nowej roli
- `rota/persistence/site_repository.py` dla ustawienia przedziału S1
- `rota/persistence/schedule_repository.py` / `schedule_lifecycle.py` tylko tam, gdzie rola jest serializowana/walidowana
- `api/routers/schedule.py` lub istniejący router manual correction wskazany przez audit
- `frontend/src/api/client.ts`
- `frontend/src/screens/MonthlyPlanning.tsx`
- `frontend/src/screens/PrintSettings.tsx`
- `rota/application/schedule_export.py`

Schema migration `rota/persistence/db.py` jest dozwolona WYŁĄCZNIE, jeśli potrzebuje jej konfiguracja przedziału S1; nie zmieniać assignments table tylko po to, by dodać wartość role, bo role jest już TEXT.

Dozwolone testy/dokumenty:
- `tasks/ROTA-T052/brief.md`
- małe testy targetowane + jeden pionowy real-flow test

Poza zakresem:
- istniejący onboarding `TRAINEE` i readiness workflow poza zapewnieniem braku regresji
- HR/training registry/certyfikaty/terminy ważności
- solver-generated S1
- recurrence scheduler
- nowy ShiftKind D/N/S
- kodowanie S1 jako N/D/ShiftDemand/reserve
- refaktoryzacja ogólna Assignment/validator

## 10. Acceptance

T52-01: koordynator ustawia kod S1 z przedziałem np. 10:00-14:30; konfiguracja akceptuje 4,5h bez fixed-duration błędu.

T52-02: koordynator wpisuje S1 pracownikowi w `MonthlyPlanning`; po reloadzie wpis jest częścią bieżącego ScheduleVersion i nadal widnieje jako S1.

T52-03: S1 nie pokrywa żadnego ShiftDemand, nie zmienia coverage i solver nigdy sam nie tworzy S1.

T52-04: S1 nie zmienia TRAINEE readiness i nie jest liczone jako onboarding training occurrence.

T52-05: przypadek D 05:00-17:00 + S1 18:00-22:00 + próba kolejnej pracy naruszającej wymagany rest nie przechodzi automatycznie; validator/solver uwzględniają S1 w time-work semantics.

T52-06: rolling 7d zawiera godziny S1; przekroczenie skonfigurowanego LOAD-01 przez dodanie S1 jest wykrywane zgodnie z istniejącym kontraktem decyzji.

T52-07: WorkBalance planned/realized hours zawiera S1 dokładnie raz; target/absence semantics bez zmian.

T52-08: REPLAN nie usuwa ani nie przesuwa istniejącego S1; tylko jawna akcja koordynatora może je zmienić/usunąć.

T52-09: PDF i ekran grafiku pokazują S1; TRAINEE print behavior pozostaje niezmienione.

T52-10: brak regresji PRIMARY/TRAINEE — istniejące coverage, mentor i readiness tests przechodzą bez zmiany kontraktu.

## 11. PREIMPLEMENTATION AUDIT

Przed kodem niezależny audytor ma szczególnie sprawdzić:
- wszystkie miejsca branching on `AssignmentRole.PRIMARY/TRAINEE`;
- czy `AssignmentRole.PERIODIC_TRAINING` jest rzeczywiście mniejszą zmianą niż osobny byt;
- jak existing solver tworzy/fiksuje existing assignments i gdzie S1 musi być fixed;
- jak validator liczy REST/LOAD/overlap i czy shared work-period oracle może bezpiecznie objąć S1;
- wszystkie liczniki godzin filtrujące `role == PRIMARY`;
- persistence/load/save Assignment role oraz FINAL immutability;
- manual correction atomicity i wersjonowanie;
- print renderer assumptions o PRIMARY/TRAINEE;
- dokładny minimalny sposób persistence S1 interval config.

Audit ma wydać `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL — ARCHITECT_CORRECTION_REQUIRED` z konkretnym trace. Audit nie może sam dopisywać funkcji HR ani rozszerzać S1.

Test nie tworzy kontraktu.
