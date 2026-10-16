# ROTA-LARGE-FILES-REFACTOR — plan ostrożnego porządkowania plików

STATUS: PLAN DO NIEZALEŻNEGO PRECHECKU; brak zbiorczej zgody na implementację.
DATA: 2026-10-16.
BASE_SHA: 923bd54917a0f9e8512d759611796e9c159fa70a.

## 1. Cel i decyzje OWNERA

Źródło: BOARD ROTA-LARGE-FILES-REFACTOR oraz `ODLOZONE.md`, wyłącznie wpis
2026-10-16 „Refaktor dużych plików”; dokument ten jest źródłem kolejności
prac, nie nowego zachowania produktu. Kontrakty funkcji pozostają w aktualnej
zamrożonej specyfikacji i istniejących briefach poszczególnych funkcji.

OWNER: „Refaktor ok, ale nie bezmyslny. Jeśli logiczniejszy będzie plik na
660 linii niż sztuczne dzielenie go na kawałki to to przekroczenie jest ok.”
Najnowsza decyzja w rozmowie: „jest bardzo ryzykowne więc planuj tak by było
bezpieczne, jeśli jakis podział jest groźny dla programu to go nie robimy.”

Obowiązuje: wyłącznie przenoszenie bez zmiany zachowania, jeden obszar na Task,
pełna suita, niezależny audyt Codexa i ultrareview po refaktorze. Implementer:
sesja Claude Code w chmurze. Termin kredytu nie uzasadnia pomijania dowodów.
Brak podziału jest poprawnym wynikiem. Nie obiecujemy plików poniżej 600 linii.

## 2. Decyzja startowa: jeden zamknięty fragment ekranu

Pierwszy i jedyny obecnie rozpisany Task implementacyjny:
`tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/brief.md`.
Przenosi już istniejący komponent ScheduleGrid z jego zależnościami lokalnymi;
nie rozcina głównego komponentu MonthlyPlanning, jego stanu, efektów ani akcji.
W wyniku MonthlyPlanning nadal przekracza limit — świadomie, zgodnie z decyzją
OWNERA. Nie wycinać kolejnych fragmentów, żeby osiągnąć wynik liczbowy.

Punktowo przeczytano ScheduleGrid i jego helpery, trzy miejsca użycia, listy
symboli pozostałych nazwanych plików, zależności etapów solvera i transakcje
migracji bazy. To przygotowanie granic, nie pełny audyt bezpieczeństwa całego
repo. Kandydat poniżej oznacza możliwość przyszłego briefu, nie potwierdzoną
bezpieczną implementację.

## 3. Kolejność i decyzja dla każdego wskazanego pliku

| Plik na BASE | Decyzja teraz | Granica i powód |
|---|---|---|
| `frontend/src/screens/MonthlyPlanning.tsx` | ETAP 1, tylko ScheduleGrid | Komponent jest już osobną funkcją; props i własne useMemo stanowią istniejącą granicę. Reszta ekranu pozostaje razem. |
| `rota/planning/solver.py` | NIE DZIELIĆ w tym planie | Solve, fazy celu, wyszukiwanie wariantów i finalizacja współdzielą model oraz jeden deadline. Oddzielenie nazw funkcji nie dowodzi niezależności czasu, kolejności i rezultatów. Brak dostatecznie izolowanej granicy uzasadniającej dziś ryzyko. |
| `frontend/src/screens/Workspace.tsx` | KANDYDAT po zamknięciu etapu 1 | Już osobny InstallGuideModal wraz z renderInstallGuide; ewentualny przyszły Task po potwierdzeniu jego importów i stanu. Pozostały Workspace zostaje. |
| `frontend/src/screens/EmployeeDetail.tsx` | KANDYDAT później | Już osobny RoleCoverageAuthorizationsPanel; wymaga osobnego briefu i sprawdzenia odświeżania danych po zapisie. Nie dzielić hooków głównego ekranu. |
| `frontend/src/api/client.ts` | KANDYDAT później, tylko typy | Oddzielenie deklaracji typów z zachowaniem publicznych importów może być naturalne. Transport, timeouty, diagnostyka, auth i obsługa błędów pozostają razem; nie rozdzielać obiektu api na system rejestrów. |
| `api/routers/schedule.py` | ZOSTAWIĆ na tym etapie | Ewentualne wydzielenie DTO/presenterów wymaga sprawdzenia OpenAPI, importów, zależności FastAPI i testów patchujących moduł; samo skrócenie routera nie daje tej gwarancji. |
| `rota/application/durable_inputs.py` | ZOSTAWIĆ na tym etapie | Naturalne grupy operacji istnieją, lecz dzielą atomowy zapis i unieważnianie pamięci/decyzji. Nie rozcinać transakcji; przyszły Task tylko po wykazaniu kompletnej granicy jednej grupy. |
| `rota/application/schedule_projection.py` | NIE DZIELIĆ w tym planie | Lineage, dobór wersji na dzień, absencje, NN, delegacje i okresy pracy wpływają na wspólny wynik PDF/Excel. Przesunięcie przypadkowych helperów łatwo ukryje zmianę historycznej projekcji. |
| `rota/application/plan_ops.py` | NIE DZIELIĆ w tym planie | Pierwszy plan, preview, akceptacja i cutover współdzielą warunki ochrony historii oraz zapis pamięci. Nie rozcinać kroków operacji ani hooków transakcyjnych. |
| `rota/planning/engine.py` | NIE DZIELIĆ w tym planie | Wspólna orkiestracja etapów, różnicowania, błędów i budżetu solvera. Nie wydzielać retry/decision jako osobnych silników. |
| `rota/planning/constraints.py` | NIE DZIELIĆ w tym planie | Kolejność budowy modelu i wspólne literały reguł; podział wymagałby osobnego mocnego dowodu równoważności. Żadnego przepisywania ograniczeń. |
| `rota/persistence/db.py` | NIE DZIELIĆ w tym planie | Historyczne SQL, migracja szyfrowania, kolejność user_version i jawne BEGIN/ROLLBACK/COMMIT. Nie dotykać schematu/migracji dla długości pliku. Nie scalać starego brancha L1-DB przez analogię do dawnego PASS. |

Decyzje NIE DZIELIĆ to zastosowanie zasady bezpieczeństwa OWNERA, nie finding
w produkcie. Nowa propozycja dla tych obszarów wymaga osobnego kontraktu
i dowodu wyraźnej korzyści oraz izolacji; nie jest zobowiązaniem kontynuowania.
Kandydatów nie wpisywać automatycznie do kolejki implementacyjnej.

## 4. Bramki i zatrzymanie po każdym obszarze

1. Zamrozić exact base i literalny zakres pojedynczego Tasku. Zmiany równoległe
   dotyczące tych samych symboli wymagają uzgodnienia nowej bazy, nie cichego
   cherry-picku/refaktoru starej wersji. Nie pracować w głównym checkout CC.
2. Niezależny precheck briefu i ocena merytoryczna CC. Autor nie daje własnemu
   planowi PASS. W tym kroku nie uruchamiać produktu/testów/suity.
3. Implementer przenosi tylko wymienione deklaracje; pokazuje stary→nowy symbol,
   zachowane ciało i minimalne zmiany importu. Bez poprawiania znalezionych
   usterek, czyszczenia algorytmu, rename, optymalizacji i zmiany formatów.
4. Dowód zachowania stosowny do obszaru; pełna suita raz na końcowym SHA
   izolowanego refaktoru jest jawnie wymagana decyzją OWNERA. Dla frontendu
   również build i rzeczywiste celowane scenariusze UI; zielony backend nie
   dowodzi równoważności ekranu. Nie wymagać identycznego losowego grafiku
   solvera jako nowej definicji zgodności produktu.
5. Niezależny audyt exact SHA, potem ultrareview przed rekomendacją merge.
   Nie ogłaszać zaliczenia nieuruchomionego narzędzia. Kolejny Task dopiero
   po zamknięciu tego obszaru; merge/wdrożenie nadal wyłącznie OWNER.

STOP/NO_SPLIT: zmiana wymaga nowego cyklu importów, ukrytego rejestru,
przekazywania dziesiątek pól stanu zamiast istniejących props, zmiany hooków,
kolejności obliczeń/operacji/zapisów, terminów timeout, modelu solvera,
formatu danych, schematu lub publicznego API. Także gdy zgodności nie można
sprawdzić w dostępnym środowisku, a ryzyko dotyczy istotnej ścieżki.
Nie obchodzić STOP nowym adapterem lub poprawką testu. Zgłosić ograniczenie;
pozostawić oryginalny kod. To nie FAIL produktu ani zaproszenie do redesignu.

Wycofanie przed merge: odrzucić jeden branch; po zatwierdzonym merge
revert jednego izolowanego refaktoru do poprzedniej wersji aplikacji.
Żaden etap nie wykonuje migracji danych, więc nie tworzy zależności od nowego
schematu. Nie edytować danych użytkownika, nie używać produkcyjnej bazy
do eksperymentów, nie wdrażać automatycznie po zielonych testach.

## 5. Limit pliku i wyłączenia

Zgoda na uzasadnione przekroczenie rozmiaru nie pozwala wyłączać ruff,
zmieniać backend.py, ukrywać jego wyniku ani usuwać testów. Jeśli mechaniczny
gate zgłasza SIZE_FILE już dużego pliku, podać dosłowny wynik, rozmiar przed/po
i źródło zaakceptowanego wyjątku OWNERA; nie nazywać tego zielonym gate.
Pozostałe błędy klasyfikować osobno, nie podciągać pod wyjątek rozmiaru.

Poza zakresem: implementacja zbiorcza 12 plików, zmiana zachowania i wyglądu,
porządkowanie przy okazji, nowe architektury, nowe reguły, zmiana istniejących
testowych oczekiwań biznesowych, sztuczny wymóg 600 linii, automatyczna
kontynuacja kolejnych kandydatów i odświeżanie historycznych benchmarków.

TASK_SCOPE:
- tasks/ROTA-LARGE-FILES-REFACTOR/brief.md

KONIEC TASK_SCOPE.

Ten scope dotyczy wyłącznie dokumentu planu. Implementację etapu 1 określa
oddzielny brief poniżej; żaden inny plik z tabeli nie jest dopuszczony do zmian.
