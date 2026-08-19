# BRIEF DLA ARCHITEKTA — DNI ROBOCZE ABSENCJI I AWARYJNA NOCKA `DAY_ONLY`

**Data decyzji właściciela:** 2026-08-19

**Baza do projektowania:** `main` po integracji ROTA-T012

**Rodzaj pracy:** dwa precyzyjne kontrakty produktu w jednym pakiecie architektonicznym

**Stan:** READY FOR ARCHITECT DESIGN — NIE READY FOR IMPLEMENTATION

## 1. Cel

Architekt ma przygotować zamrożony kontrakt oraz implementacyjny brief dla dwóch niezależnych, ale spotykających się w funkcji celu zachowań:

1. L4 i zatwierdzony urlop pomniejszają normę godzin wyłącznie za dni robocze.
2. Zgoda na N dla pracownika `day_only` jest awaryjnym fallbackiem SOFT, a nie zwykłym, aktywnym przez cały okres zdjęciem `DAY_ONLY-01`.

Oba zachowania ujawnił realny scenariusz właściciela dla marca 2027. Architekt nie ma ponownie otwierać decyzji produktu ani proponować ogólnego workflow/override engine.

## 2. Źródła dowodowe w repo

- `tasks/ROTA-T012/round_01/tests/tests_r23.txt` — finding `ABS-R23-1`;
- `tasks/ROTA-T012/round_01/tests/tests_r24.txt` — finding `DAY-R24-1`;
- `tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py` — trzy reproduktory arytmetyki;
- `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe.py` — pełny scenariusz 62 zmian;
- `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe_result.json` — wynik z wyjątkiem i bez wyjątku;
- `arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md` — obecny kontrakt wyjątku, który nowa decyzja zawęża;
- `rota/planning/absence.py`, `rota/planning/solver.py`, `rota/balance.py` — obecni konsumenci arytmetyki absencji.

## 3. Kontrakt A — L4 i urlop liczone tylko w dni robocze

### 3.1. Decyzja właściciela

L4 (`SICK_LEAVE`) i zatwierdzony urlop (`LEAVE_GRANTED`) pomniejszają normę o 8 h wyłącznie za dzień roboczy.

Na potrzeby Rota dzień roboczy spełnia oba warunki:

- przypada od poniedziałku do piątku;
- nie ma `CalendarDay.holiday=True`.

Soboty, niedziele i święta ustawowe nie pomniejszają normy, nawet jeśli leżą wewnątrz ciągłego zakresu L4/urlopu.

### 3.2. Przykład wiążący

Marzec 2027, target 168 h, L4 od 2 do 19 marca inclusive:

- zakres zawiera 18 dni kalendarzowych;
- zawiera 14 dni roboczych;
- pomniejszenie normy: `14 * 8 h = 112 h`;
- effective target: `168 - 112 = 56 h`;
- 36 h pracy oznacza niedobór 20 h, a nie nadwyżkę 12 h.

### 3.3. Zakres konsumentów — bez rozszerzania wcześniejszych decyzji

- live TARGET-01 solvera nadal uwzględnia `SICK_LEAVE` zgodnie z dzisiejszym ownership; ten kontrakt zmienia zbiór liczonych dni, nie dodaje samodzielnie `LEAVE_GRANTED` do celu solvera;
- miesięczny i kwartalny WorkBalance nadal uwzględniają `SICK_LEAVE` oraz `LEAVE_GRANTED`; dla obu używają nowej definicji dnia roboczego;
- union/dedup aktywnych zakresów pozostaje: jeden dzień jednego pracownika może pomniejszyć normę najwyżej raz, także przy nakładających się lub stykających rekordach i różnych rodzajach absencji;
- zakres jest inclusive i nadal przycinany do obliczanego miesiąca;
- effective target pozostaje clamped do zera.

### 3.4. Granica HARD, której nie wolno pomylić z księgowaniem godzin

Zmiana dotyczy wyłącznie arytmetyki targetu i WorkBalance.

`SICK_LEAVE-01` i `LEAVE_GRANTED-01` nadal blokują automatyczne Assignment przez każdy dzień kalendarzowy należący do zakresu absencji, włącznie z weekendami i świętami. Weekend nie pomniejsza normy, ale pracownik nadal pozostaje wtedy na L4/urlopie i nie może zostać automatycznie zaplanowany.

### 3.5. Obowiązki architekta dla kontraktu A

Architekt ma określić:

1. jedno kanoniczne ownership liczenia dni roboczych, współdzielone semantycznie przez solver i WorkBalance;
2. sposób dostarczenia `CalendarDay.holiday` do każdego konsumenta bez hardkodowania polskiego kalendarza w kodzie domenowym;
3. zachowanie publicznych/legacy wywołań `compute_month_balance()` i `compute_quarter_balance()`, które dziś nie przyjmują kalendarza;
4. fail-closed behavior przy brakującym lub niepełnym kalendarzu — bez zgadywania świąt;
5. minimalny TASK_SCOPE oraz migrację wywołań, bez nowego subsystemu kalendarzowego i bez SQL w warstwie aplikacji/planning.

Architekt nie może wrócić do wcześniejszego „per calendar day”; decyzja właściciela z 2026-08-19 ją zastępuje.

## 4. Kontrakt B — `day_only` N jako awaryjny fallback SOFT

### 4.1. Decyzja właściciela

Pracownik z `Employee.day_only=True` pozostaje domyślnie objęty `DAY_ONLY-01` jako HARD.

Datowana zgoda `EMPLOYEE_DAY_ONLY_N_EXCEPTION` oznacza:

> jeżeli bez tej osoby na N nie da się zbudować kompletnego poprawnego grafiku, solver może użyć jej na N wyjątkowo i ma użyć takich nocek możliwie najmniej.

Zgoda nie oznacza zwykłej kwalifikacji do N i nie może służyć do poprawiania TARGET-01, fairness ani kosmetyki grafiku, gdy istnieje kompletny grafik z zerem wyjątkowych nocek.

### 4.2. Wymagana gwarancja konstrukcyjna

Nie wystarczy dodać zwykłej kary SOFT o małej wadze. Dzisiejszy cel może poświęcić taką karę dla lepszego targetu, co reproduktor pokazał wynikiem ośmiu N dla pracownika `day_only`, mimo że grafik bez wyjątku był `FEASIBLE`.

Kontrakt ma gwarantować co najmniej:

1. normalny przebieg zachowuje `DAY_ONLY-01` jako HARD także wtedy, gdy istnieje datowana zgoda fallback;
2. jeśli ten przebieg daje kompletny, niezależnie zwalidowany grafik, wynik zostaje zwrócony z zerem wyjątkowych N;
3. fallback może zostać uruchomiony wyłącznie po wykazaniu, że normalny przebieg nie daje kompletnego grafiku; UNKNOWN, MODEL_INVALID i inne statusy techniczne nie są dowodem i nie mogą być maskowane retry;
4. fallback może otworzyć N wyłącznie pracownikom objętym obowiązującą w dacie `EMPLOYEE_DAY_ONLY_N_EXCEPTION`;
5. w fallbacku liczba Assignment N korzystających z wyjątku jest minimalizowana leksykograficznie przed TARGET-01, fairness i pozostałymi SOFT;
6. przy tym samym minimalnym użyciu wyjątku działają dotychczasowe cele/tie-breaki;
7. każde faktyczne użycie wyjątku jest jawne dla koordynatora jako SOFT warning/provenance, z employee, demand/date i `rule_version_id`; nigdy nie jest ciche;
8. brak zgody lub data poza `effective_from/effective_to` zachowuje dzisiejszy HARD `DAY_ONLY-01`;
9. zgoda uchyla wyłącznie `DAY_ONLY-01`: membership, availability, L4, urlop, REST, LOAD, SiteRules, kwalifikacja 24 h i wszystkie inne HARD nadal łączą się przez AND;
10. independent validator musi potwierdzać dokładnie tę samą datowaną legalność każdego wyjątkowego N.

### 4.3. Integracja z istniejącym T012 emergency 24 h

Owner decision 2026-08-19 ustala pierwszeństwo: wyjątkowa N pracownika `day_only` jest mniej ryzykownym fallbackiem niż utworzenie 24 h na obiekcie o normie 12 h. W takim obiekcie 24 h jest dalej idącym odstępstwem, w praktyce mogącym oznaczać naruszenie prawa pracy stosowane przez firmę dopiero przy braku innego wyjścia.

Architekt ma opisać deterministyczną sekwencję retry zgodną z tą kolejnością ryzyka:

1. normalny PLAN: bez emergency 24 h i bez `day_only` N fallback;
2. `day_only` N fallback bez emergency 24 h, z leksykograficzną minimalizacją liczby takich N;
3. dopiero jeśli również ten etap nie daje kompletnego grafiku, T012 emergency 24 h; w tym etapie zgoda `day_only` może pozostać dostępna, ale liczba wyjątkowych N nadal musi być minimalizowana przed zwykłymi celami, a architect ma jawnie opisać provenance obu rodzajów fallbacku;
4. dopiero po wyczerpaniu dozwolonych przebiegów zwykły DECISION_REQUIRED/LOAD diagnosis;
5. żaden retry nie może maskować statusu technicznego ani tworzyć nowego publicznego `ignore_hard` parametru.

Jeżeli istniejący engine ma wcześniejszą ścieżkę `NO_ELIGIBLE_EMPLOYEE`/unassignable, architekt musi objąć ją tym samym pojęciem „brak kompletnego grafiku”; nie wolno ograniczyć fallbacku wyłącznie do surowego CP-SAT `INFEASIBLE`, jeśli brak N dla `day_only` kończy się przed zbudowaniem modelu.

### 4.4. Wiążący oracle — marzec 2027

Profil:

- pięciu pracowników;
- pojedyncza obsada;
- D 05:00–17:00 i N 17:00–05:00 przez cały marzec 2027;
- A: `day_only`, posiada datowaną zgodę fallback N;
- B: L4 2–19 marca;
- C: 2 i 17 marca bez D, N dozwolona;
- D: LEAVE_GRANTED 17–21 marca;
- E: każdy piątek `UNAVAILABLE_24H`, także na nockach.

Obecny reproduktor:

- z aktywnym wyjątkiem: FEASIBLE, A dostaje 8 N;
- bez wyjątku: FEASIBLE, A dostaje 0 N.

Po nowym kontrakcie wiążący wynik brzmi:

- pierwszy przebieg bez wyjątkowej N jest FEASIBLE;
- solver nie uruchamia fallbacku;
- A dostaje dokładnie 0 N;
- wszystkie 62 demandy są pokryte i independent validator daje HARD PASS.

Kontrakt nie zamraża konkretnej dystrybucji pozostałych D/N między B–E, ponieważ korekta dni roboczych L4 zmienia TARGET-01. Zamrożone są kompletność, legalność oraz zero wyjątkowych N dla A w tym scenariuszu.

## 5. Minimalna macierz akceptacyjna dla architekta

### A. Dni robocze absencji

1. L4 wtorek–piątek przez zakres zawierający dwa weekendy — liczą się tylko weekdays.
2. LEAVE_GRANTED o tym samym zakresie — identyczny filtr w WorkBalance.
3. święto `CalendarDay.holiday=True` w poniedziałek–piątek — nie pomniejsza normy.
4. święto w weekend — nadal zero, bez podwójnego efektu.
5. nakładające się L4/urlop — union dat, bez podwójnego naliczenia.
6. zakres przez granicę miesiąca — przycięcie oraz filtr dni roboczych.
7. weekend/święto nadal blokują Assignment w aktywnym zakresie absencji.
8. niepełny kalendarz — jawny, zamrożony fail-closed rezultat.

### B. Awaryjna N dla `day_only`

1. normalny grafik FEASIBLE — zero N dla `day_only`, mimo aktywnej zgody.
2. tylko jedna wyjątkowa N odblokowuje pełny grafik — dokładnie jedna N i jawny warning.
3. dwie są konieczne — dokładnie dwie, nie więcej.
4. kilka osób ma zgodę — minimalna łączna liczba wyjątkowych N.
5. TARGET/fairness poprawiłby się przez dodatkową N — dodatkowa N zakazana przez leksykograficzne minimum.
6. wyjątek przed, na granicach i po zakresie dat.
7. równoczesne L4/urlop/UNAVAILABLE/REST/LOAD/inny SiteRule — brak bypassu.
8. normalny unassignable z powodu DAY_ONLY — fallback jest osiągalny.
9. UNKNOWN/MODEL_INVALID — brak retry i TECHNICAL_ERROR.
10. fallback nie pomaga — DECISION_REQUIRED/istniejąca diagnoza, nie fałszywe FEASIBLE.
11. integracja z T012 emergency 24 h w każdym dozwolonym etapie.
    Gdy zarówno jedna wyjątkowa N `day_only`, jak i emergency 24 h osobno
    dają kompletny grafik, wybrana musi zostać wyjątkowa N, bez emergency 24 h.
12. restart/select/finalize zachowują widoczną provenance faktycznie użytego SOFT.

## 6. Zakazy i granice architektoniczne

- bez ogólnego workflow engine;
- bez ogólnego `override HARD` lub `exception wins`;
- bez publicznej flagi pomijającej HARD;
- bez hardkodowanego kalendarza świąt w solverze;
- bez zmiany HARD blokowania L4/urlopu;
- bez uznania zwykłej wagi liczbowej za gwarancję „tylko wyjątkowo”;
- bez nowych statusów, jeśli istniejące FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR wystarczają;
- bez cichego używania `day_only` N;
- bez ponownego otwierania liczby 8 h za jeden kwalifikowany dzień roboczy;
- bez rozszerzania solvera o LEAVE_GRANTED TARGET adjustment, którego ten brief nie autoryzuje.

## 7. Oczekiwane deliverables architekta

1. Zamrożony addendum supersedujący wyłącznie „calendar day” w absence accounting.
2. Zamrożony addendum supersedujący aktywne znaczenie `EMPLOYEE_DAY_ONLY_N_EXCEPTION` na awaryjny fallback SOFT.
3. Jeden implementacyjny brief lub dwa jawnie zależne briefy z exact base SHA, TASK_SCOPE, limitami plików i checkpointami.
4. Literalna kolejność retry względem T012 emergency 24 h oraz LOAD diagnosis.
5. Jawny kontrakt warning/provenance dla użytej wyjątkowej N.
6. Macierz testów obejmująca klasy z sekcji 5 i wiążący marzec 2027.
7. Potwierdzenie, że wcześniejsze frozen decyzje pozostają bez zmian poza dwoma literalnie wskazanymi supersessions.

## 8. Warunek startu CC

CC nie zaczyna implementacji na podstawie samego tego dokumentu. Najpierw architekt zapisuje oba kontrakty i implementacyjny TASK_SCOPE, następnie Codex wykonuje preimplementation audit. Dopiero PASS tego audytu daje READY FOR IMPLEMENTATION.
