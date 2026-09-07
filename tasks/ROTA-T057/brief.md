# ROTA-T057 — lifecycle PLAN / REPLAN / Przelicz Plan

STATUS: READY FOR IMPLEMENTATION — PREIMPLEMENTATION PASS, TASK_SCOPE FROZEN

BASE_MAIN_SHA: `dfeec962fd90d249f83606b414801ff67d305d7c`
PREIMPLEMENTATION_PASS: `tasks/ROTA-T057/round_01/tests/tests_r3.txt` @ `64dc390`

Źródła:
- `BOARD.md` — OWNER_RULING 2026-09-06 dla `ROTA-PLAN-VS-REPLAN-LIFECYCLE`
- `arch/FINDING_2026-09-05_PLAN_VS_REPLAN_LIFECYCLE.md` — materiał dowodowy o obecnym kodzie, NIE źródło zakresu produktu
- `arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md` — istniejący próg 15% różnicy wariantów
- `tasks/ROTA-T057/round_01/tests/tests_r3.txt` — PASS preimplementation i minimalne seamy
- `tasks/ROTA-T057/round_01/tests/tests_r4.txt` — wąski reaudyt scope; trzy korekty mechaniczne, bez nowej decyzji produktowej

## 1. Cel

Rozdzielić i naprawić cztery różne operacje koordynatora, które obecny kod częściowo miesza:

1. `PLAN` — pierwszy wariant miesiąca albo ponowne liczenie po skasowaniu zaakceptowanego, ale jeszcze nieżywego grafiku.
2. `REPLAN` — kolejne alternatywne propozycje przed pierwszą akceptacją grafiku dla miesiąca.
3. Usunięcie zaakceptowanego, ale jeszcze nieżywego grafiku + ponowny `PLAN`.
4. `Przelicz Plan` — solverowa zmiana grafiku, który już żyje i obowiązuje.

`Korekta ręczna` pozostaje osobnym, istniejącym mechanizmem ręcznej zmiany i nie jest zastępowana przez żadną z powyższych operacji.

## 2. Zamrożony kontrakt OWNERA

### 2.1 PLAN

- PLAN służy do policzenia propozycji od nowa, gdy dla `(site_id, month)` nie ma jeszcze zaakceptowanego grafiku.
- PLAN jest również używany po świadomym skasowaniu przez koordynatora zaakceptowanego, ale jeszcze nieżywego grafiku.
- Kandydat PLAN jest tylko preview do momentu `Użyj tego grafiku`.
- Odrzucenie, nieukończenie albo błąd PLAN nie tworzy biznesowej ScheduleVersion, nie zmienia `current` i nie trafia do historii/restore/export.
- Pierwszy nieudany PLAN dla pustego miesiąca pozostawia **0 ScheduleVersion**.

### 2.2 REPLAN przed pierwszą akceptacją

- REPLAN służy wyłącznie do pokazania kolejnego wariantu w ramach tego samego podejścia przed pierwszą akceptacją grafiku dla miesiąca.
- Każdy kolejny wariant musi różnić się o co najmniej 15% obsady od KAŻDEGO wcześniej pokazanego wariantu w tym podejściu, nie tylko od ostatniego.
- Próg 15% reużywa istniejącą semantykę T017; nie tworzyć nowej miary podobieństwa.
- REPLAN przed akceptacją nie tworzy ScheduleVersion i nie zmienia `current`.
- `Użyj tego grafiku` jest pierwszym momentem trwałego zapisu zaakceptowanego grafiku.
- Pamięć aktywnego podejścia i sygnatur wariantów musi przeżyć reload.
- `Odrzuć wynik` kończy aktywne podejście; kolejny PLAN zaczyna nowe podejście.

### 2.3 Zaakceptowany, ale jeszcze nieżywy grafik

- Grafik jest `nieżywy`, dopóki faktycznie nie rozpoczęła się jego pierwsza rzeczywista służba.
- Granica jest dokładnym czasem startu pierwszej rzeczywistej służby, nie północą ani samą datą kalendarzową.
- Przykład zamrożony przez OWNERA: 1 września o 10:00 grafik z pierwszą służbą o 18:00 nadal jest nieżywy; dokładnie o 18:00 staje się żywy.
- Jeśli zaakceptowany grafik jest jeszcze nieżywy i koordynator uznaje go za błędny, może:
  - skasować go i uruchomić PLAN od nowa; albo
  - poprawić punktowo Korektą ręczną.
- Dotyczy to również grafiku FINAL, jeśli pierwsza rzeczywista służba jeszcze się nie rozpoczęła.
- `Przelicz Plan` nie służy do tego przypadku.
- Skasowanie nieżywego grafiku usuwa go z `current`, biznesowej Historii, restore, eksportu i rozliczeń. Niewidoczny techniczny ślad audytu może pozostać.
- Nie osłabiać fizycznej niezmienności FINAL z T008: użyć istniejącego lifecycle/current/history i dziennika akcji, bez drugiego systemu historii.

### 2.4 Żywy grafik i Przelicz Plan

- Grafik staje się `żywy` dokładnie w chwili rozpoczęcia jego pierwszej rzeczywistej służby.
- Od tej chwili każda automatyczna zmiana solverem odbywa się wyłącznie przez `Przelicz Plan`.
- `Przelicz Plan`:
  - twardo chroni wszystkie służby, których start już nastąpił;
  - nie może ich zmienić nawet wtedy, gdy bieżące reguły/validator uznałyby je dziś za niepożądane;
  - dla przyszłej części minimalizuje liczbę zmian względem aktualnego obowiązującego grafiku;
  - po akceptacji tworzy dokładnie jedną nową ScheduleVersion;
  - poprzednia obowiązująca wersja pozostaje w historii na zawsze.
- Nieudany, przerwany, `SEARCH_INCOMPLETE` albo odrzucony wynik `Przelicz Plan` pozostawia `current`, historię i liczbę ScheduleVersion bez zmian.
- T057 nie obejmuje planowania przyszłego L4.

### 2.5 Korekta ręczna

- Korekta ręczna pozostaje dostępna przed i po ożywieniu grafiku.
- To jedyny mechanizm, w którym koordynator może świadomie zmienić konkretną służbę poza solverem.
- T057 zmienia tylko skutek wersjonowania korekty przed/po granicy live, jeśli jest to konieczne do zachowania jednego lifecycle.
- T057 nie rozszerza uprawnień do edycji rozpoczętych/odbytych służb i nie rozstrzyga osobnego findingu REALIZED/historycznej korekty faktycznie wykonanej służby.

## 3. Wspólna zasada preview / akceptacji

Dla PLAN, REPLAN i Przelicz Plan kandydat solvera jest technicznym preview, nie biznesową wersją grafiku.

Przed `Użyj tego grafiku` preview:
- nie jest `current`;
- nie jest widoczne w historii;
- nie może być `restore` targetem;
- nie może być drukowane jako obowiązujący grafik;
- nie może wpływać na bilanse/rozliczenia jako zaakceptowany grafik.

`Użyj tego grafiku` jest jedyną granicą trwałego zaakceptowania wyniku solvera.

Rozszerzyć istniejący `PlanPreview` jako jedyny owner pamięci aktywnego podejścia i sygnatur wariantów. Nie tworzyć nowego subsystemu preview ani biznesowej ScheduleVersion przed akceptacją.

Akceptacja zachowuje istniejący `SCHEDULE_CANDIDATE_SELECTED` i istniejący atomowy owner tworzenia ScheduleVersion/current. Nie tworzyć nowego statusu akceptacji.

## 4. Właściciele techniczni — reduction gate R3

- **15% diversity:** jeden owner w solverze, zgodny z T017. UI i application nie liczą własnej kopii miary.
- **Granica live:** jeden helper application i jeden backendowy czas operacji. Backend autoryzuje fazę; UI tylko prezentuje wynik i nie może obejść reguły.
- **Usunięcie przed live:** istniejący lifecycle/current/history + istniejący dziennik akcji; bez drugiego systemu historii.
- **Przelicz Plan:** przenieść istniejącą ochronę cutover/minimal-change ze starego znaczenia REPLAN. Nie zmieniać pozostałych reguł solvera.
- **Routery eksportu/Historii i księgowość:** poza zmianą; nie dodawać tam drugiej walidacji lifecycle. Targetowany pion ma potwierdzić, że po usunięciu nie widzą grafiku przez istniejący owner current/history.

## 5. Wymagane zachowanie UI

UI ma jasno rozdzielać dostępność operacji:

- brak zaakceptowanego grafiku -> PLAN + REPLAN wariantów przed akceptacją;
- zaakceptowany, ale nieżywy -> możliwość usunięcia i PLAN od nowa oraz Korekta ręczna; brak `Przelicz Plan`;
- żywy grafik -> `Przelicz Plan` + Korekta ręczna; zwykły pre-acceptance REPLAN nie jest używany.

Nazwy i przyciski nie mogą prowadzić do innej semantyki backendu niż opis powyżej. Bezpośrednie endpointy muszą egzekwować te same fazy co UI.

## 6. FIRST EXECUTION GATE — obowiązek CC przed ciężkimi testami i handoffem

Ten gate jest obowiązkowy dla implementera i ma być wykonany na najwyższym dostępnym realnym poziomie produktu. Jeśli frontend dla danej ścieżki działa, użyć realnego UI + API + persistence. Nie zastępować gate samym pytestem ani analizą kodu.

CC wykonuje E1–E5 na osobnej bazie i zapisuje obserwowane `current`, liczbę ScheduleVersion, preview, historię i wynik grafiku przed/po w artefaktach `execution_e1.md` ... `execution_e5.md`.

### E1 — pierwszy PLAN od zera
- brak zaakceptowanego grafiku;
- PLAN -> FEASIBLE preview;
- przed `Użyj tego grafiku`: 0 ScheduleVersion;
- odrzuć preview -> nadal 0;
- nieudany PLAN -> nadal 0;
- PLAN ponownie -> zaakceptuj -> dokładnie 1 zaakceptowana wersja i ona jest `current`.

### E2 — REPLAN przed pierwszą akceptacją
- wygeneruj co najmniej 3 kolejne warianty;
- przed akceptacją żadna ScheduleVersion nie jest tworzona;
- każdy nowy wariant różni się >=15% od KAŻDEGO wcześniej pokazanego wariantu tego podejścia;
- przeładuj aplikację między wariantami i potwierdź zachowanie aktywnego podejścia/sygnatur;
- `Odrzuć wynik` kończy podejście;
- akceptacja jednego wariantu tworzy dokładnie 1 wersję.

### E3 — zaakceptowany, ale nieżywy
- zaakceptuj grafik z pierwszą służbą o znanej godzinie;
- chwilę przed startem pierwszej służby: także FINAL można usunąć;
- po usunięciu brak grafiku w current, biznesowej Historii, restore i eksporcie;
- uruchom PLAN od nowa i zaakceptuj nowy wariant;
- dokładnie w chwili startu pierwszej służby i później operacja usunięcia jest odrzucona przez backend, również przy bezpośrednim endpointzie.

### E4 — żywy grafik / Przelicz Plan
- przygotuj zaakceptowany grafik, którego pierwsza służba już się rozpoczęła;
- wykonaj `Przelicz Plan` z realną zmianą dotyczącą przyszłości, ale bez scenariusza przyszłego L4;
- przed akceptacją preview stary grafik nadal jest `current`;
- po akceptacji powstaje dokładnie jedna nowa wersja;
- wszystkie rozpoczęte służby są bit-for-bit zachowane w zakresie pól solverowo modyfikowalnych;
- przyszłość zmienia się minimalnie względem poprzedniej wersji;
- poprzednia wersja pozostaje w historii;
- stary i nowy grafik mają zostać pokazane/drukowane obok siebie i ocenione optycznie; same zielone testy i zgodność liczbowa nie wystarczają.

### E5 — nieudane/odrzucone Przelicz Plan
- `SEARCH_INCOMPLETE` albo kontrolowany brak zaakceptowanego wyniku;
- odrzucenie preview;
- `current`, liczba ScheduleVersion i historia bez zmian;
- bezpośredni endpoint nie może ominąć phase/lifecycle guard.

Jeżeli którykolwiek E1–E5 nie przechodzi, CC NIE uruchamia kosztownego finalnego pakietu audytowego i NIE przekazuje tasku do Codexa jako gotowego. Najpierw naprawia zachowanie albo wraca do architekta, jeśli kontrakt jest sprzeczny.

## 7. Testy automatyczne po przejściu execution gate

Dopiero po E1–E5:

- targetowane testy lifecycle PLAN/REPLAN/Przelicz Plan w `tests/test_t057.py`;
- regresje 15% diversity T017 tylko tam, gdzie T057 literalnie zastępuje oczekiwania;
- granica live dokładnie przed/równo/po starcie pierwszej służby;
- atomowość `Użyj tego grafiku`;
- preview niewidoczne dla current/history/restore/export;
- failure/abort nie zmienia wersji biznesowych;
- historia żywego grafiku zachowana po Przelicz Plan;
- minimal-change objective dla przyszłości nadal działa;
- bezpośrednie API nie omija faz lifecycle;
- solver HARD/validator bez nieuzasadnionej zmiany semantyki.

Nie kopiować pełnych kontraktów solvera z T017. Nie dodawać testu przyszłego L4.

Zielony pytest/build/backend bez dowodu E1–E5 NIE jest wystarczającym dowodem wykonania T057.

## 8. Acceptance

T57-01: pierwszy PLAN nie tworzy biznesowej ScheduleVersion przed akceptacją; nieudany pierwszy PLAN pozostawia 0 ScheduleVersion.

T57-02: odrzucony/niepełny/nieudany PLAN nie zmienia current/history/version count.

T57-03: REPLAN przed pierwszą akceptacją tworzy kolejne preview, nie ScheduleVersion; aktywne podejście i sygnatury wariantów przeżywają reload.

T57-04: każdy kolejny pre-acceptance REPLAN różni się >=15% od wszystkich wcześniejszych wariantów tego podejścia; miara ma jednego ownera zgodnego z T017.

T57-05: `Odrzuć wynik` kończy aktywne pre-acceptance podejście; `Użyj tego grafiku` po PLAN/REPLAN atomowo tworzy dokładnie jedną zaakceptowaną wersję i ustawia ją jako current.

T57-06: zaakceptowany, także FINAL, ale nieżywy grafik można usunąć przed startem pierwszej rzeczywistej służby; po usunięciu nie jest widoczny w current, biznesowej Historii, restore, eksporcie ani rozliczeniach; PLAN działa od zera.

T57-07: granica live/non-live jest wyznaczona przez faktyczny start pierwszej rzeczywistej służby: chwilę przed można usunąć, dokładnie od startu nie można.

T57-08: dla żywego grafiku `Przelicz Plan` jest solverową ścieżką zmiany; zwykły pre-acceptance REPLAN nią nie jest.

T57-09: `Przelicz Plan` twardo zachowuje wszystkie rozpoczęte służby.

T57-10: `Przelicz Plan` minimalizuje zmiany w przyszłości względem current.

T57-11: zaakceptowany `Przelicz Plan` tworzy dokładnie jedno dziecko, ustawia je jako current i zachowuje rodzica w historii.

T57-12: odrzucony/SEARCH_INCOMPLETE/nieudany `Przelicz Plan` nie zmienia current/history/version count.

T57-13: preview żadnej operacji nie jest dostępne przez history/restore/export jako zaakceptowany grafik.

T57-14: Korekta ręczna pozostaje dostępna przed i po ożywieniu i nie jest zastępowana solverowym lifecycle; T057 nie rozszerza uprawnień do historycznej edycji służb.

T57-15: bezpośrednie endpointy nie omijają backendowego ownera faz lifecycle.

T57-16: FIRST EXECUTION GATE E1–E5 jest wykonany i raportowany przed finalnym pakietem testów CC; E4 zawiera optyczne porównanie starego i nowego grafiku.

## 9. Zakaz rozszerzania zakresu

Poza T057:
- nowe reguły jakości samego grafiku niezwiązane z lifecycle;
- zmiana HARD/SOFT poza tym, co konieczne dla twardej ochrony rozpoczętych służb i istniejącego minimal-change/15%;
- temat target_hours vs rytm D/N/W/W;
- blokada PDF dla niepotwierdzonych LAW;
- porządkowanie identyfikatorów technicznych w UI;
- historyczna korekta faktycznie wykonanej służby i REALIZED — osobny finding;
- planowanie przyszłego L4;
- nowy subsystem preview, nowy status akceptacji albo drugi system historii;
- refaktoryzacje „przy okazji”.

Jeżeli implementacja wymaga któregoś z tych tematów lub pliku poza TASK_SCOPE, STOP i powrót do architekta przed zmianą.

## 10. WHERE_MAP — wykonany w preimplementation audit

WHERE_MAP:
- MODE: REQUIRED
- EXECUTION_STATUS: SATISFIED_BY_R3
- TARGETS:
  - `rota/application/plan_ops.py`: PLAN/REPLAN/accept/reject flow
  - `rota/application/planning_lifecycle.py`: nowy mały owner faz i aktywnego podejścia
  - `rota/application/lifecycle_ops.py`: current/version lifecycle i usunięcie przed live
  - `rota/application/manual_edit.py`: wersjonowanie Korekty ręcznej względem live boundary, bez rozszerzenia uprawnień
  - `rota/application/open_month.py`: odczyt fazy/current dla UI/API
  - `rota/persistence/plan_preview_repository.py`: rozszerzony PlanPreview i pamięć podejścia/sygnatur
  - `rota/persistence/schedule_lifecycle.py`, `schedule_repository.py`: current/history/version owner
  - `rota/planning/engine.py`, `solver.py`, `replan_reshuffle.py`: reuse T017 15%, cutover/minimal-change
  - `api/routers/schedule.py`, `api/errors.py`: backend phase guard i DTO/errors
  - `frontend/src/screens/MonthlyPlanning.tsx`, `frontend/src/api/client.ts`: prezentacja faz bez lokalnego autoryzowania
- REASON: dokładne seamy wskazane przez niezależny preimplementation audit R3.

## 11. EXACT TASK_SCOPE — FROZEN

READ_ONLY_EVIDENCE:
- tasks/ROTA-T057/brief.md
- tasks/ROTA-T057/round_01/tests/tests_r1.txt
- tasks/ROTA-T057/round_01/tests/tests_r2.txt
- tasks/ROTA-T057/round_01/tests/tests_r3.txt
- tasks/ROTA-T057/round_01/tests/tests_r4.txt

TASK_SCOPE:
- rota/application/plan_ops.py
- rota/application/planning_lifecycle.py
- rota/application/lifecycle_ops.py
- rota/application/manual_edit.py
- rota/application/open_month.py
- rota/application/errors.py
- rota/persistence/plan_preview_repository.py
- rota/persistence/db.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_errors.py
- rota/site_memory_types.py
- rota/planning/state.py
- rota/planning/engine.py
- rota/planning/solver.py
- rota/planning/replan_reshuffle.py
- api/routers/schedule.py
- api/errors.py
- frontend/src/api/client.ts
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/screens/History.tsx
- tests/test_t057.py
- tests/test_t017.py
- tests/test_t020.py
- tests/test_t023.py
- tests/test_t023b.py
- tests/test_t033_replan_must_differ.py
- tests/test_t041_checkpoint_a.py
- tests/test_t041_checkpoint_b.py
- tests/test_t009_plan_select_replan.py
- tests/test_t031_schedule_api.py
- tests/test_audit_t009_r6.py
- tests/test_t019b.py
- tests/test_t023_checkpoint_b.py
- frontend/e2e/monthly-planning.spec.ts
- tasks/ROTA-T057/round_01/execution_e1.md
- tasks/ROTA-T057/round_01/execution_e2.md
- tasks/ROTA-T057/round_01/execution_e3.md
- tasks/ROTA-T057/round_01/execution_e4.md
- tasks/ROTA-T057/round_01/execution_e5.md

Nie edytować innych istniejących testów „na wszelki wypadek”. Pięć testów dodanych po R4 wolno zmienić wyłącznie tam, gdzie ich istniejące oczekiwania zostały literalnie zastąpione przez T057 albo bezpośrednio testują przenoszony cutover. Jeśli implementacja naprawdę wymaga pliku spoza tej listy, architekt aktualizuje TASK_SCOPE przed pierwszą zmianą tego pliku.
