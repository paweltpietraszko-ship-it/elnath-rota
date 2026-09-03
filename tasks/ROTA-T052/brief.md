# ROTA-T052 — S1 okresowe szkolenie jako ręczny czas pracy w grafiku

STATUS: READY FOR PREIMPLEMENTATION RE-AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `7cd5fde8446bd08a02c647d4eabaab9db200acba`

Źródła:
- `arch/FINDING_2026-09-03_PERIODIC_TRAINING_S1.md`
- `arch/ARCHITECT_HANDOFF_UX_BACKLOG_06_08_2026-09-03.md`
- decyzje OWNERA 2026-09-03
- PREIMPLEMENTATION AUDIT round_01 — FAIL; korekta OWNERA/architekta: S1 liczy godziny pracy, ale NIE uczestniczy w dobowym `REST-01`; nocka -> poranne S1 jest dozwolone

## 1. Cel

Dodać kod `S1` oznaczający szkolenie okresowe pracownika. Koordynator ręcznie ustawia dzień oraz przedział godzin. S1 jest widoczne na grafiku i wydruku oraz liczy się jako czas pracy.

S1 NIE jest onboardingowym `TRAINEE`, NIE jest demandem D/N i NIE jest funkcją kadrową.

## 2. Decyzje OWNERA — zamrożone

1. S1 dysponuje wyłącznie koordynator. Solver nigdy sam nie proponuje ani nie generuje S1.
2. Koordynator ustala start/end S1; brak sztywnej długości, minimum lub maksimum specyficznego dla S1.
3. Godziny S1 są godzinami pracy.
4. S1 uczestniczy w istniejących ograniczeniach czasu pracy WYŁĄCZNIE tam, gdzie wskazano poniżej:
   - nie może nakładać się czasowo z inną pracą tego samego pracownika;
   - wpływa na rolling-7d `LOAD-01` / próg profilu;
   - wpływa na bilans planned/realized hours w taki sam sposób jak inny rzeczywisty czas pracy odpowiedniego state;
   - **S1 NIE uczestniczy w dobowym `REST-01`**: wcześniejsza nocka nie blokuje porannego S1 z powodu 11h odpoczynku, a samo S1 nie uruchamia nowego 11-godzinnego odpoczynku przed kolejną zmianą.
5. S1 nie pokrywa PRIMARY demand i nie zmienia coverage.
6. S1 nie wpływa na `READY_FOR_PRIMARY`, threshold szkolenia wdrożeniowego ani istniejące `TRAINEE`.
7. Rota nie ewidencjonuje wykonania szkolenia jako moduł HR, ważności certyfikatów, terminów kolejnych szkoleń ani dopuszczeń do pracy.

Korekta round_01 jest wąska: usuwa S1 z `REST-01`. Nie usuwa S1 z overlap, `LOAD-01` ani bilansów i nie ustanawia żadnych nowych wyjątków dla zwykłych D/N/24h.

## 3. Proponowana minimalna architektura do audytu

Najmniejszym istniejącym agregatem zawierającym pracownika, przedział czasu, state, ScheduleVersion i historię jest `Assignment`.

Na BASE_MAIN_SHA tabela `assignments.role` jest `TEXT NOT NULL` bez SQL CHECK ograniczającego ją do dwóch wartości. Obecny model domenowy ma jednak wyłącznie role `PRIMARY` i `TRAINEE` oraz wiele jawnych reguł tych dwóch ról.

Propozycja architekta: rozszerzyć `AssignmentRole` o trzecią semantycznie jednoznaczną rolę, np. `PERIODIC_TRAINING`, której widocznym kodem operacyjnym jest `S1`.

To NIE jest zgoda na „przerobienie TRAINEE”. Nowa rola ma własne invarianty:
- `covers_demand_id = None`;
- `mentor_primary_assignment_id = None`;
- nie bierze udziału w coverage/mentor/readiness;
- jest fixed/manual-only dla solvera;
- jest normalnym zajętym przedziałem czasu dla overlap oraz liczy się do `LOAD-01` i bilansów;
- **nie jest work period dla dobowego `REST-01` i nie może być użyte do wyliczania ściany 11h ani przed S1, ani po S1**;
- należy do complete ScheduleVersion snapshot i historii tak jak pozostałe wpisy grafiku.

Jeżeli preimplementation re-audit wykaże, że rozszerzenie AssignmentRole łamie fundamentalny invariant albo wymaga większej zmiany niż osobny lekki byt czasu pracy, audyt ma zwrócić FAIL z konkretnym trace. Nie wolno samodzielnie przeprojektować tasku na moduł HR lub nowy subsystem.

## 4. Konfiguracja kodu S1

W `Kody zmian` S1 ma własny start/end ustawiany przez koordynatora, bez fixed-duration validation D1-D5/N1-N5.

Nie wciskać S1 do `WORK_CODE_KEYS` jako D/N z fałszywą frozen duration i nie reużywać N5/reserve slotu.

Najmniejsza reprezentacja ustawienia ma przechować tylko przedział S1 potrzebny jako wartość domyślna/konfiguracyjna UI. Nie budować katalogu wielu typów szkoleń.

Koordynator przy wpisaniu S1 na konkretny dzień może użyć skonfigurowanego przedziału; task nie dodaje automatycznego cyklu/recurrence generatora.

## 5. Planowanie i walidacja

Solver:
- nigdy nie tworzy S1;
- istniejące S1 w ScheduleVersion traktuje jako ręcznie ustalony/fixed zajęty czas pracownika dla overlap i obciążenia;
- NIE stosuje do S1 dobowego `REST-01`: nocka -> poranne S1 jest legalne, a S1 -> kolejna zmiana nie wymaga 11h tylko z powodu S1;
- nie używa S1 do pokrycia demandu.

Independent validator:
- nie wymaga `covers_demand_id` dla PERIODIC_TRAINING;
- nie stosuje mentor/readiness reguł TRAINEE;
- wykrywa rzeczywisty overlap S1 z inną pracą;
- uwzględnia S1 w `LOAD-01`;
- pomija S1 w dobowym `REST-01` po obu stronach relacji odpoczynku;
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
- planning fixed/time constraints: istniejący solver/validator; shared `work_periods` nie może automatycznie wciągnąć S1 do `REST-01`
- hours: `rota/balance.py`
- API: istniejący schedule/manual-correction router
- UI: `MonthlyPlanning` + `PrintSettings`
- PDF: `schedule_export.py`

## 9. TASK_SCOPE

Dozwolony kod produktu, jeśli preimplementation re-audit potwierdzi AssignmentRole approach:
- `rota/domain.py`
- `rota/application/manual_edit.py`
- `rota/balance.py`
- `rota/planning/solver.py`
- `rota/planning/validator.py`
- `rota/planning/work_periods.py` tylko jeśli istniejący shared oracle wymaga jawnego WYŁĄCZENIA nowej roli z dobowego REST-01; nie zmieniać semantyki REST zwykłych okresów pracy
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
- jakakolwiek zmiana `REST-01` dla PRIMARY/TRAINEE lub zwykłych D/N/24h poza koniecznym pominięciem S1

## 10. Acceptance

T52-01: koordynator ustawia kod S1 z przedziałem np. 10:00-14:30; konfiguracja akceptuje 4,5h bez fixed-duration błędu.

T52-02: koordynator wpisuje S1 pracownikowi w `MonthlyPlanning`; po reloadzie wpis jest częścią bieżącego ScheduleVersion i nadal widnieje jako S1.

T52-03: S1 nie pokrywa żadnego ShiftDemand, nie zmienia coverage i solver nigdy sam nie tworzy S1.

T52-04: S1 nie zmienia TRAINEE readiness i nie jest liczone jako onboarding training occurrence.

T52-05: pracownik kończy N o 05:00 i ma S1 np. 08:00-12:00 tego samego dnia; system NIE zgłasza `REST-01` i nie blokuje S1 z powodu braku 11h odpoczynku.

T52-06: S1 08:00-12:00 nie tworzy własnej 11-godzinnej ściany odpoczynku; kolejna niekolidująca zmiana nie jest blokowana wyłącznie dlatego, że S1 zakończyło się o 12:00.

T52-07: rzeczywisty overlap, np. S1 10:00-14:00 i inna praca 12:00-17:00, jest niedozwolony/wykrywany zgodnie z istniejącą ochroną przed nakładaniem pracy.

T52-08: rolling 7d zawiera godziny S1; przekroczenie skonfigurowanego LOAD-01 przez dodanie S1 jest wykrywane zgodnie z istniejącym kontraktem decyzji.

T52-09: WorkBalance planned/realized hours zawiera S1 dokładnie raz; target/absence semantics bez zmian.

T52-10: REPLAN nie usuwa ani nie przesuwa istniejącego S1; tylko jawna akcja koordynatora może je zmienić/usunąć.

T52-11: PDF i ekran grafiku pokazują S1; TRAINEE print behavior pozostaje niezmienione.

T52-12: brak regresji PRIMARY/TRAINEE — istniejące coverage, mentor, readiness i REST tests dla zwykłej pracy przechodzą bez zmiany kontraktu.

## 11. PREIMPLEMENTATION RE-AUDIT

Po korekcie round_01 niezależny audytor ma szczególnie sprawdzić:
- wszystkie miejsca branching on `AssignmentRole.PRIMARY/TRAINEE`;
- czy `AssignmentRole.PERIODIC_TRAINING` jest rzeczywiście mniejszą zmianą niż osobny byt;
- jak existing solver tworzy/fiksuje existing assignments i gdzie S1 musi być fixed;
- jak validator/work-period oracle może objąć overlap/LOAD bez przypadkowego objęcia S1 dobowym `REST-01`;
- że oba kierunki korekty są spełnione: `N -> S1` bez 11h i `S1 -> praca` bez nowej 11h ściany po S1;
- wszystkie liczniki godzin filtrujące `role == PRIMARY`;
- persistence/load/save Assignment role oraz FINAL immutability;
- manual correction atomicity i wersjonowanie;
- print renderer assumptions o PRIMARY/TRAINEE;
- dokładny minimalny sposób persistence S1 interval config.

Audit ma wydać `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL — ARCHITECT_CORRECTION_REQUIRED` z konkretnym trace. Audit nie może sam dopisywać funkcji HR ani rozszerzać S1.

Test nie tworzy kontraktu.
