# ROTA-T044 — TASK ChatGPT — korekta R2 po rundzie „adwokata diabła” CC

Status: **READY_FOR_CODEX_NARROW_REAUDIT — CC READ-ONLY — NIE IMPLEMENTOWAĆ**

## 0. Źródła i zakres

Ta korekta zamyka wyłącznie dwa findingi z:

- `tasks/ROTA-T044/round_01/tests/cc_devils_advocate_r1.txt` @ `5808fbc1c0b5030d8346bc67fe0e6447667485ea`;
- oceniany kontrakt wykonawczy:
  - `tasks/ROTA-T044/TASK_CHATGPT.md` @ `bccdc5876df42e83781d735012d8d2dcb8242d83`;
  - `tasks/ROTA-T044/TASK_CHATGPT_CORRECTION_R1.md` @ `6334c6425172e4985ce73957b5c5df929232228b`;
- źródłowy brief R8: `tasks/ROTA-T044/brief.md` @ `b8fccffa4591fe979fae09a6915a35f161566e12`;
- PASS korekty R1: `tasks/ROTA-T044/round_01/tests/tests_r8.txt`.

Runda CC znalazła:

1. **BLOCKER:** brak jawnego lifecycle urlopu/L4 względem pierwszego PLAN;
2. **NON_BLOCKING, ale sprzeczny z wcześniejszą decyzją OWNERA:** suma niezależnych maksimów per warstwa może sztucznie zawyżyć roster, łącząc szczyty z dwóch różnych miesięcy.

Ta korekta nie otwiera ponownie żadnego innego elementu T044. Kalkulator pozostaje prostą arytmetyką przed PLAN; Symulator pozostaje obserwatorem produktu, nie drugim solverem/evaluatorem.

## 1. PRECEDENCJA

W połączonym kontrakcie T044 ta korekta ma pierwszeństwo **wyłącznie** dla:

- lifecycle zapisu urlopu/L4 w `TASK_CHATGPT.md` §5/§6/Checkpoint B;
- wzoru kalkulatora obsady w `brief.md` §1.1 i `TASK_CHATGPT.md` §3.2;
- testów odbioru bezpośrednio dotyczących tych dwóch punktów;
- następnego gate'u.

`TASK_CHATGPT_CORRECTION_R1.md` nadal obowiązuje w całości dla liczby bloków urlopu:

- `1 LOCAL` → jeden blok 10 dni roboczych;
- `>=2 LOCAL` → dokładnie dwa bloki dla dwóch różnych LOCAL: 10 dni + 5 dni roboczych, bez nakładania;
- pozostali LOCAL nie dostają kolejnych planowych bloków urlopu.

Reszta R8 / TASK_CHATGPT pozostaje zamknięta.

---

## 2. KOREKTA A — absencje są wejściem początkowym, nie akcją po PLAN

### 2.1 Jeden moment zapisu

Wariant B generuje i zapisuje wszystkie swoje planowe absencje dla badanego obiektu **dokładnie raz, podczas initial setup obiektu, przed jego pierwszym PLAN**.

Dotyczy to:

- planowego urlopu z `TASK_CHATGPT_CORRECTION_R1.md`;
- ewentualnego jednego L4 losowanego ~25% raz na obiekt.

Po wykonaniu pierwszego PLAN tego obiektu state machine T044 **nie ma żadnej reguły**, która:

- tworzy nowy `LEAVE_GRANTED` lub `SICK_LEAVE`;
- rozszerza istniejący zakres `LEAVE_GRANTED` lub `SICK_LEAVE`;
- przenosi istniejącą absencję na inne daty;
- losuje drugie L4;
- dodaje kolejny planowy urlop.

REPLAN w T044 bada wynik produktu po innych dozwolonych, wcześniej zamrożonych działaniach; **nie jest poprzedzany nowym zapisem urlopu/L4**.

### 2.2 Wielomiesięczna sekwencja

Jeżeli state machine kontynuuje ten sam Site/roster w kolejnym miesiącu, T044 nie używa tego jako pretekstu do ponownego losowania i dopisywania nowych urlopów/L4. Wielomiesięczny przebieg nadal służy wyłącznie obserwowaniu kolejnych działań produktu i odczytów — bez nowej maszynerii absencji.

T044 nie rozszerza w ten sposób zakresu absencji poza dane zamrożone przy initial setup.

### 2.3 Znany `RetroactiveAbsenceRejected`

Ta korekta **nie zmienia produktu** i nie dodaje mapowania `RetroactiveAbsenceRejected` w `api/errors.py`.

Kontrakt harnessu ma po prostu nie generować retroaktywnego zapisu po PLAN. To precondition generatora/state machine, nie nowa reguła produktu.

Jeżeli mimo poprawnego initial setup istniejące API zwróci non-2xx/5xx podczas zapisu absencji przed pierwszym PLAN:

- harness nie zmienia danych i nie próbuje „naprawić” przypadku;
- używa istniejącego OWNER-08 failure/reproducer path;
- zapisuje pełny ustrukturyzowany artefakt wejścia i odpowiedzi;
- kończy ten przykład jako finding/awarię narzędzia lub produktu zgodnie z faktem, który wystąpił.

Nie budować osobnego catchera biznesowego tylko dla `RetroactiveAbsenceRejected` w T044 i nie ruszać `rota/**`/`api/**`.

### 2.4 Odbiór korekty absencji

Dodać/zmienić minimalny test kontraktowy Wariantu B tak, aby dowodził:

- urlop i ewentualne L4 są materializowane przed pierwszym PLAN;
- liczba zapisów planowych absencji po pierwszym PLAN = **0**;
- REPLAN nie uruchamia nowego draw/write urlopu ani L4;
- state machine nie ma legalnego transition „dodaj/rozszerz urlop albo L4 po PLAN”;
- nie trzeba zmieniać produktu, aby ten warunek spełnić.

`T44-B-08` z korekty R1 pozostaje testem skali urlopu. `T44-B-09` nadal sprawdza jedno L4 ~25% raz na obiekt, a dodatkowo musi potwierdzić, że to losowanie i zapis są częścią initial setup przed pierwszym PLAN.

---

## 3. KOREKTA B — kalkulator bierze maksimum z REALNEGO miesiąca, nie z syntetycznej sumy szczytów

### 3.1 Dlaczego to nie jest nowa decyzja produktowa

Wcześniejsze jawne decyzje OWNERA pozostają bez zmian:

- kalkulator ma dawać **ciasną** obsadę; za mało daje ciągłe wsparcie, za dużo daje solverowi „fory”;
- nie ma marginesu urlopowego/L4;
- kiedy ten sam kształt wymaga różnej liczby osób w różnych realnych miesiącach 2026, kalkulator wybiera **wyższą rzeczywiście występującą wartość**;
- `required_primary_count` pozostaje per wiersz/dzień i może wynosić `{1,2}`;
- warstwy nadal są potrzebne, aby reprezentować mieszaną obsadę, np. robocze=2/weekend=1.

R8 poprawnie wprowadziło warstwy, ale kolejność `max` i `sum` była zbyt szeroka: `sum(max każdej warstwy)` może połączyć szczyt warstwy 1 ze stycznia i szczyt warstwy 2 z sierpnia, mimo że taki miesiąc nie istnieje. To jest sztuczny zapas, którego OWNER już zakazał.

### 3.2 Nowy, kanoniczny wzór

Dla każdego **konkretnego** miesiąca `m` z 12 miesięcy 2026:

1. policz godziny każdej warstwy `k` dokładnie jak w R8;
2. dla każdej warstwy policz:

`layer_headcount(k, m) = ceil(layer_hours(k, m) / nominal_monthly_hours_kp(m, POLISH_2026_HOLIDAYS))`

3. zsumuj warstwy dla **tego samego miesiąca**:

`monthly_headcount(m) = sum(layer_headcount(k, m) for k in 1..MAX_REQUIRED_PRIMARY_COUNT)`

4. dopiero na końcu wybierz najgorszy realny miesiąc:

`liczba_LOCAL = max(monthly_headcount(m) for m in WSZYSTKIE_MIESIACE_2026)`

Czyli:

```text
DOBRZE:  max_m( sum_k( ceil(layer_hours(k,m) / norm(m)) ) )
ŹLE:     sum_k( max_m( ceil(layer_hours(k,m) / norm(m)) ) )
```

Nie wolno dodawać maksimów pochodzących z różnych miesięcy.

### 3.3 Granica: nadal prosty kalkulator, nie mini-solver

Ta korekta nie dodaje żadnego planowania:

- brak Assignmentów;
- brak wyboru pracownika;
- brak odpoczynku/HARD/fairness;
- brak CP-SAT;
- brak analizy wyniku PLAN/REPLAN;
- tylko `sum`, `ceil`, pętla po 12 miesiącach i jedno `max`.

Kalkulator nadal działa raz przed pierwszym PLAN.

### 3.4 Zamrożone kontrolne wyniki

Dotychczasowe trzy przypadki pozostają bez zmiany:

- `T44-B-CALC-01`: D/N 12h, req=1 cały tydzień → **5 LOCAL**;
- `T44-B-CALC-02`: D/N 12h, req=2 cały tydzień → **10 LOCAL**;
- `T44-B-CALC-03`: D/N 12h, robocze=2/weekend=1 → **9 LOCAL**.

Dodać czwarty test regresyjny z dokładnego kontrprzykładu CC:

- zmiana 12h;
- warstwa 1 aktywna poniedziałek–sobota;
- warstwa 2 aktywna tylko poniedziałek/wtorek/sobota;
- `required_primary_count` odpowiednio 1/2;
- stary `sum(max warstw)` dawał 5;
- poprawny `max(sum warstw w tym samym miesiącu)` daje **4 LOCAL**;
- test ma zamrozić wynik **4**, aby nie wróciło syntetyczne łączenie różnych miesięcy.

Nazwa: `T44-B-CALC-04`.

### 3.5 HEADCOUNT invariant

`HEADCOUNT` z `TASK_CHATGPT.md` §9.1 oznacza od teraz zgodność z powyższym, poprawionym kalkulatorem. Nie powstaje drugi headcount checker.

---

## 4. PRE_IMPLEMENTATION_REDUCTION_GATE po korekcie R2

Po obu korektach nadal pozostają tylko istniejące odpowiedzialności T044:

- jeden kalkulator obsady w testowym helperze B;
- jeden swobodny generator obiektu;
- jeden stateful driver Hypothesis;
- istniejące produkcyjne API;
- HEADCOUNT + CLOSED WORLD jako jedyne własne invariants harnessu;
- jeden wspólny failure/reproducer path.

Nie powstają:

- nowy endpoint;
- nowe zachowanie produktu;
- obsługa `RetroactiveAbsenceRejected` w produkcie;
- drugi solver/validator/evaluator;
- nowy system absencji;
- nowy model kadrowy;
- zmiana Wariantu A.

TASK_SCOPE pozostaje bez zmian.

WHERE_MAP pozostaje REQUIRED i przed implementacją musi być ponowiony na exact HEAD dla `tests/property/coordinator_simulator.py`, a po dodaniu nowych symboli — tylko dla faktycznie nowych/współdzielonych ownerów.

---

## 5. Następny gate

CC zakończył już rundę „adwokata diabła”. **Nie powtarza jej automatycznie po tej korekcie.**

Następny krok:

1. Codex wykonuje **wąski niezależny reaudyt** exact HEAD z tą korektą R2.
2. Reaudyt sprawdza wyłącznie:
   - czy urlop/L4 są teraz jednoznacznie initial-setup-only, przed pierwszym PLAN i bez późniejszych writes;
   - czy nie dodano zmiany produktu dla `RetroactiveAbsenceRejected`;
   - czy kalkulator używa `max_m(sum_k(... dla tego samego m))`, a nie `sum_k(max_m(...))`;
   - czy 5/10/9 pozostają bez zmian;
   - czy kontrprzykład CC daje 4;
   - czy kalkulator nadal jest prostą arytmetyką, nie drugim solverem;
   - czy reszta Tasku/Correction R1 pozostała zamknięta.
3. Raport zapisać jako kolejny nieistniejący `tests_rN.txt`; nie nadpisywać wcześniejszych raportów.
4. Do PASS Codexa: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.
5. Po PASS Task wraca do architekta do finalnego zamknięcia preimplementation gate; dopiero wtedy może dostać `READY_FOR_IMPLEMENTATION`.

## 6. Zakazy

Ta korekta nie upoważnia do:

- zmian `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`;
- modyfikacji Wariantu A;
- zmian EXTERNAL;
- zmian celu Hypothesis poza precondition absencji;
- dodania fairness/quarter/legal evaluatora;
- zmiany `required_primary_count` poza `{1,2}`;
- rozszerzania generatora o nowe klasy obiektów;
- uruchamiania pełnej regresji repo bez osobnej zgody OWNERA.

Do następnego PASS: **bez implementacji**.
