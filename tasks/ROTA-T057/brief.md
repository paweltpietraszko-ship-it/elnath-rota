# ROTA-T057 — lifecycle PLAN / REPLAN / Przelicz Plan

STATUS: READY FOR PREIMPLEMENTATION AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `dfeec962fd90d249f83606b414801ff67d305d7c`

Źródła:
- `BOARD.md` — OWNER_RULING 2026-09-06 dla `ROTA-PLAN-VS-REPLAN-LIFECYCLE`
- `arch/FINDING_2026-09-05_PLAN_VS_REPLAN_LIFECYCLE.md` — materiał dowodowy o obecnym kodzie, NIE źródło zakresu produktu
- `arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md` — istniejący próg 15% różnicy wariantów

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

### 2.2 REPLAN przed pierwszą akceptacją

- REPLAN służy wyłącznie do pokazania kolejnego wariantu w ramach tego samego podejścia przed pierwszą akceptacją grafiku dla miesiąca.
- Każdy kolejny wariant musi różnić się o co najmniej 15% obsady od KAŻDEGO wcześniej pokazanego wariantu w tym podejściu, nie tylko od ostatniego.
- Próg 15% reużywa istniejącą semantykę T017; nie tworzyć nowej miary podobieństwa.
- REPLAN przed akceptacją nie tworzy ScheduleVersion i nie zmienia `current`.
- `Użyj tego grafiku` jest pierwszym momentem trwałego zapisu zaakceptowanego grafiku.

### 2.3 Zaakceptowany, ale jeszcze nieżywy grafik

- Grafik jest `nieżywy`, dopóki faktycznie nie rozpoczęła się jego pierwsza służba.
- Granica jest czasem startu pierwszej rzeczywistej służby, nie samą datą kalendarzową.
- Jeśli zaakceptowany grafik jest jeszcze nieżywy i koordynator uznaje go za błędny, może:
  - skasować go i uruchomić PLAN od nowa; albo
  - poprawić punktowo Korektą ręczną.
- `Przelicz Plan` nie służy do tego przypadku.
- Skasowanie nieżywego grafiku nie ma tworzyć sztucznej historii biznesowej po grafiku, który jeszcze nie zaczął obowiązywać.

### 2.4 Żywy grafik i Przelicz Plan

- Grafik staje się `żywy` w chwili rozpoczęcia jego pierwszej służby.
- Od tej chwili każda automatyczna zmiana solverem odbywa się wyłącznie przez `Przelicz Plan`.
- `Przelicz Plan`:
  - twardo chroni wszystkie służby, których start już nastąpił;
  - nie może ich zmienić nawet wtedy, gdy bieżące reguły/validator uznałyby je dziś za niepożądane;
  - dla przyszłej części minimalizuje liczbę zmian względem aktualnego obowiązującego grafiku;
  - po akceptacji tworzy dokładnie jedną nową ScheduleVersion;
  - poprzednia obowiązująca wersja pozostaje w historii na zawsze.
- Nieudany, przerwany, `SEARCH_INCOMPLETE` albo odrzucony wynik `Przelicz Plan` pozostawia `current`, historię i liczbę ScheduleVersion bez zmian.

### 2.5 Korekta ręczna

- Korekta ręczna pozostaje dostępna przed i po ożywieniu grafiku.
- To jedyny mechanizm, w którym koordynator może świadomie zmienić konkretną służbę poza solverem.
- T057 nie rozszerza kontraktu Korekty ręcznej o inne decyzje produktowe.

## 3. Wspólna zasada preview / akceptacji

Dla PLAN, REPLAN i Przelicz Plan kandydat solvera jest technicznym preview, nie biznesową wersją grafiku.

Przed `Użyj tego grafiku` preview:
- nie jest `current`;
- nie jest widoczne w historii;
- nie może być `restore` targetem;
- nie może być drukowane jako obowiązujący grafik;
- nie może wpływać na bilanse/rozliczenia jako zaakceptowany grafik.

`Użyj tego grafiku` jest jedyną granicą trwałego zaakceptowania wyniku solvera.

Nie tworzyć nowego trzeciego subsystemu preview, jeśli istniejący `plan_preview` może być użyty bez zmiany jego semantyki.

## 4. Wymagane zachowanie UI

UI ma jasno rozdzielać dostępność operacji:

- brak zaakceptowanego grafiku -> PLAN + REPLAN wariantów przed akceptacją;
- zaakceptowany, ale nieżywy -> możliwość usunięcia i PLAN od nowa oraz Korekta ręczna; brak `Przelicz Plan`;
- żywy grafik -> `Przelicz Plan` + Korekta ręczna; zwykły pre-acceptance REPLAN nie jest używany.

Nazwy i przyciski nie mogą prowadzić do innej semantyki backendu niż opis powyżej.

## 5. FIRST EXECUTION GATE — obowiązek CC przed ciężkimi testami i handoffem

Ten gate jest obowiązkowy dla implementera i ma być wykonany na najwyższym dostępnym realnym poziomie produktu. Jeśli frontend dla danej ścieżki działa, użyć realnego UI + API + persistence. Nie zastępować gate samym pytestem ani analizą kodu.

CC ma przejść co najmniej poniższe scenariusze na osobnej bazie testowej i zapisać obserwowane `current`, liczbę ScheduleVersion, preview i wynik grafiku przed/po:

E1 — pierwszy PLAN od zera:
- brak zaakceptowanego grafiku;
- PLAN -> FEASIBLE preview;
- przed `Użyj tego grafiku`: 0 zaakceptowanych wersji biznesowych;
- odrzuć preview -> nadal 0;
- PLAN ponownie -> zaakceptuj -> dokładnie 1 zaakceptowana wersja i ona jest `current`.

E2 — REPLAN przed pierwszą akceptacją:
- wygeneruj co najmniej 3 kolejne warianty;
- przed akceptacją żadna ScheduleVersion nie jest tworzona;
- każdy nowy wariant różni się >=15% od KAŻDEGO wcześniej pokazanego wariantu tego podejścia;
- odrzucenie/restart nie zmienia `current` ani historii;
- akceptacja jednego wariantu tworzy dokładnie 1 wersję.

E3 — zaakceptowany, ale nieżywy:
- zaakceptuj grafik, którego pierwsza służba jeszcze się nie zaczęła;
- usuń grafik;
- potwierdź brak biznesowej historii po nim;
- uruchom PLAN od nowa i zaakceptuj nowy wariant.

E4 — żywy grafik / Przelicz Plan:
- przygotuj zaakceptowany grafik, którego pierwsza służba już się rozpoczęła;
- wykonaj `Przelicz Plan` z realną przyczyną zmiany w przyszłości;
- przed akceptacją preview stary grafik nadal jest `current`;
- po akceptacji powstaje dokładnie jedna nowa wersja;
- wszystkie rozpoczęte służby są bit-for-bit zachowane w zakresie pól solverowo modyfikowalnych;
- przyszłość zmienia się minimalnie względem poprzedniej wersji;
- poprzednia wersja pozostaje w historii.

E5 — nieudane/odrzucone Przelicz Plan:
- `SEARCH_INCOMPLETE` albo kontrolowany brak zaakceptowanego wyniku;
- odrzucenie preview;
- `current`, liczba ScheduleVersion i historia bez zmian.

Jeżeli którykolwiek E1–E5 nie przechodzi, CC NIE uruchamia kosztownego finalnego pakietu audytowego i NIE przekazuje tasku do Codexa jako gotowego. Najpierw naprawia zachowanie albo wraca do architekta, jeśli kontrakt jest sprzeczny.

## 6. Testy automatyczne po przejściu execution gate

Dopiero po E1–E5:

- targetowane testy lifecycle PLAN/REPLAN/Przelicz Plan;
- regresje 15% diversity T017;
- regresja cutover na dokładnie przed/równo/po starcie pierwszej służby;
- atomowość `Użyj tego grafiku`;
- preview niewidoczne dla current/history/restore/export;
- failure/abort nie zmienia wersji biznesowych;
- historia żywego grafiku zachowana po Przelicz Plan;
- minimal-change objective dla przyszłości nadal działa;
- solver HARD/validator bez nieuzasadnionej zmiany semantyki.

Zielony pytest/build/backend bez dowodu E1–E5 NIE jest wystarczającym dowodem wykonania T057.

## 7. PREIMPLEMENTATION AUDIT — Codex przed kodem produktu

Przed implementacją Codex ma sfalsyfikować brief względem obecnego kodu i istniejących kontraktów, szczególnie:

- czy cztery operacje są jednoznaczne i nie nakładają się;
- czy `grafik żywy` ma deterministyczną granicę opartą na starcie pierwszej służby;
- czy 15% reużywa dokładnie mechanizm T017;
- czy preview może pozostać jednym istniejącym seamem;
- czy usunięcie nieżywego grafiku nie koliduje z history/audit semantics;
- czy Przelicz Plan może chronić rozpoczęte służby bez zmiany solvera w obszarach poza T057;
- czy TASK_SCOPE obejmuje wszystkie konieczne ścieżki przed pierwszą zmianą kodu.

Codex nie ma projektować nowych stanów/history subsystemów bez wykazanej konieczności.

## 8. Acceptance

T57-01: pierwszy PLAN nie tworzy biznesowej ScheduleVersion przed akceptacją.

T57-02: odrzucony/niepełny/nieudany PLAN nie zmienia current/history/version count.

T57-03: REPLAN przed pierwszą akceptacją tworzy kolejne preview, nie ScheduleVersion.

T57-04: każdy kolejny pre-acceptance REPLAN różni się >=15% od wszystkich wcześniejszych wariantów tego podejścia.

T57-05: `Użyj tego grafiku` po PLAN/REPLAN atomowo tworzy dokładnie jedną zaakceptowaną wersję i ustawia ją jako current.

T57-06: zaakceptowany, ale nieżywy grafik można usunąć bez pozostawiania go jako trwałej historii obowiązującego grafiku; po usunięciu PLAN działa od zera.

T57-07: granica live/non-live jest wyznaczona przez faktyczny start pierwszej służby.

T57-08: dla żywego grafiku `Przelicz Plan` jest solverową ścieżką zmiany; zwykły pre-acceptance REPLAN nią nie jest.

T57-09: `Przelicz Plan` twardo zachowuje wszystkie rozpoczęte służby.

T57-10: `Przelicz Plan` minimalizuje zmiany w przyszłości względem current.

T57-11: zaakceptowany `Przelicz Plan` tworzy dokładnie jedno dziecko, ustawia je jako current i zachowuje rodzica w historii.

T57-12: odrzucony/SEARCH_INCOMPLETE/nieudany `Przelicz Plan` nie zmienia current/history/version count.

T57-13: preview żadnej operacji nie jest dostępne przez history/restore/export jako zaakceptowany grafik.

T57-14: Korekta ręczna pozostaje dostępna przed i po ożywieniu i nie jest zastępowana solverowym lifecycle.

T57-15: FIRST EXECUTION GATE E1–E5 jest wykonany i raportowany przed finalnym pakietem testów CC.

## 9. Zakaz rozszerzania zakresu

Poza T057:
- nowe reguły jakości samego grafiku niezwiązane z lifecycle;
- zmiana HARD/SOFT poza tym, co konieczne dla twardej ochrony rozpoczętych służb i istniejącego minimal-change/15%;
- temat target_hours vs rytm D/N/W/W;
- blokada PDF dla niepotwierdzonych LAW;
- porządkowanie identyfikatorów technicznych w UI;
- historyczna korekta faktycznie wykonanej służby i REALIZED — osobny finding;
- refaktoryzacje „przy okazji”.

Jeżeli implementation wymaga któregoś z tych tematów, STOP i powrót do architekta.

## 10. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - plan/preview application flow: PLAN, REPLAN, candidate acceptance/rejection
  - ScheduleVersion persistence/current/history/restore
  - solver entry points dla minimal-change i variant diversity 15%
  - cutover/live boundary używany przez Przelicz Plan
  - frontend `MonthlyPlanning.tsx` — widoczność i znaczenie PLAN/REPLAN/Przelicz Plan/Korekta ręczna
  - API routers/DTO dla powyższych operacji
  - istniejące testy T017/T023/T033/T041 dotyczące variant/cutover/version lifecycle
- REASON: znaleźć dokładne seams przed zamrożeniem literalnego TASK_SCOPE. `where.py`/search są dowodem lokalizacji, nie źródłem nowych wymagań.

## 11. TASK_SCOPE — do zamrożenia po PREIMPLEMENTATION AUDIT

Na tym etapie nie wpisywać zgadywanej szerokiej listy plików. Codex ma w preimplementation audit wskazać minimalny rzeczywisty zestaw plików wynikający z WHERE_MAP. Architekt po audycie zamraża literalny `TASK_SCOPE:` przed pierwszą zmianą kodu produktu.

Implementacja pozostaje HOLD do czasu PASS preimplementation audit i zamrożenia TASK_SCOPE.
