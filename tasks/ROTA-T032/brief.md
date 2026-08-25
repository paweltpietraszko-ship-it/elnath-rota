# ROTA-T032 — SOFT ranking: rytm D/N/wolne/wolne + naprawa równomierności godzin

Status: **DRAFT — do konsultacji Codex, potem decyzji architekta. Implementacja NIE rozpoczęta.**

Pochodzenie: live testing T031 przez Pawła, 2026-08-24/25 (obiekt "cacafdd",
OCHRONA). Nie dotyczy T031 (ekran/API) — czysto silnik planujący.

TASK_SCOPE:
- rota/planning/fairness.py
- rota/planning/solver.py
- tests/test_t032_soft_ranking.py

(`rota/planning/validator.py` CELOWO poza `TASK_SCOPE` — patrz §4, decyzja
otwarta, może wejść do zakresu dopiero po odpowiedzi architekta.)

## 1. Wynik dla właściciela

Solver premiuje grafiki, w których jak najwięcej pracowników ma jak
najwięcej wystąpień rytmu D→N→wolne→wolne (bez wymuszania wspólnej fazy
między ludźmi — to luźna preferencja, nie sztywny grafik brygadowy).
Solver przestaje przypadkowo skupiać niedobór godzin na jednej osobie,
kiedy inni mają wynik bliżej celu. Zero zmian UI/API — czysto wewnętrzna
poprawka funkcji celu CP-SAT.

## 2. Ustalone fakty (audyt live, cytaty z kodu)

### 2a. Brakujący czynnik SOFT "preferencje D/N" — spec.md:606-608

> Aktywne czynniki SOFT:
> - równomierność godzin względem target_hours
> - preferencje D/N; N,N i D,D dopuszczalne jeśli HARD zachowane

Sprawdzone: `rota/planning/fairness.py` implementuje wyłącznie
`add_weekend_fairness` i `add_holiday_fairness`. `rota/planning/solver.py`
implementuje `TARGET_DEVIATION_WEIGHT` (linia 40/319) oraz
`SOFT_PENALTY_WEIGHT` dla `DAY_SHIFT_OFF-01`/`LEAVE_PLAN-01` (linia
322-323). **Żaden fragment kodu nie realizuje "preferencje D/N"** — literę
kontraktu nigdy nie zaimplementowano.

**OWNER DECISION (Paweł, 2026-08-25):** to nie kara za serię tej samej
zmiany, tylko **nagroda za wystąpienie okna D→N→wolne→wolne**, liczona
niezależnie dla każdego pracownika. Solver NIE koordynuje faz między
pracownikami (odrzucony wariant: sztywny grafik brygadowy) — nawet
koordynator ręcznie nie byłby w stanie ułożyć grafiku wyłącznie z tym
wzorcem, więc to czysta preferencja rankingowa: więcej trafień u wszystkich
razem = lepszy kandydat.

### 2b. "Równomierność godzin względem target_hours" — zaimplementowana, ale matematycznie nieskuteczna

Potwierdzone live (odtworzone przez bezpośrednie wywołanie
`POST /schedule/{month}/plan` na obiekcie "cacafdd", wrzesień 2026,
`target_hours=160` identyczny dla wszystkich 5 zatrudnionych): wynikowy
rozkład godzin **192 / 180 / 180 / 120 / 48**.

Przyczyna (`solver.py:319`): `TARGET_DEVIATION_WEIGHT * (pos + neg)` sumuje
odchylenie `|target − actual|` przez wszystkich pracowników. Gdy suma
dostępnych godzin w miesiącu jest mniejsza niż suma wszystkich targetów
(zwykły przypadek), **ta suma jest matematycznie identyczna niezależnie od
tego, jak rozłożony jest niedobór** między zatrudnionymi poniżej celu — CP-SAT
nie ma żadnego bodźca do wyrównania, wybiera dowolne z wielu rozwiązań
o tej samej wartości funkcji celu. To nie literówka w wadze, tylko
strukturalna wada wzoru.

## 3. Poza zakresem

- REST-01 / WEEKLY-REST-01 / LOAD-01 (HARD) — bez zmian, żaden nowy SOFT
  term nie może ich naruszać (obowiązuje już `RULE-04`, spec.md:238).
- Sztywny, skoordynowany grafik brygadowy (rozważony i odrzucony przez
  Pawła — patrz §2a).
- UI/API (T031 i inne ekrany) — brak zmian.
- Zmiana istniejącej wagi `TARGET_DEVIATION_WEIGHT` samej w sobie — §2b
  proponuje DODATKOWY term, nie dotyka istniejącego.

## 4. Walidator — OTWARTA DECYZJA, nie ustalona

Paweł zwrócił uwagę, że walidator powinien mieć "te same zmiany co
solver". Sprawdzone w kodzie, dlaczego to nie jest proste 1:1:

`rota/planning/validator.py:1-2` (docstring): *"Independent HARD validator
(anti-drift rule 12, arch/spec.md SECTION 2/5). Re-derives every HARD
violation from PlanningState + a final Assignment list, from scratch,
without CP-SAT."* Funkcja `validate()` (linia 551) jest siatką
bezpieczeństwa wywoływaną po każdym solve/ręcznej poprawce/replanie —
zwraca `hard_pass` (bool) + listę naruszeń HARD. Jej pole `warnings`
zawiera dziś wyłącznie trzy wąskie, zdarzeniowe notatki
(`DAY_ONLY-N-FALLBACK-01 SOFT`, `DAY_SHIFT_OFF-01 SOFT`, `LEAVE_PLAN-01
SOFT`) — każda przypięta do konkretnego, już istniejącego wyjątku od
reguły HARD. **Walidator nie ma dziś żadnego odpowiednika wagi/funkcji
celu z CP-SAT** — nie liczy jakości SOFT dla żadnego istniejącego czynnika,
łącznie z już zaimplementowanym weekend/holiday fairness.

Literalne "to samo co w solverze" oznaczałoby dodanie do `validate()`
nowej kategorii wyniku (licznik jakości SOFT), której tam dotąd nie ma —
zmieniłoby to sens i kontrakt zwrotny funkcji używanej przez finalize/
replan/manual-correction, na której kontrakcie (dokładna zawartość
`warnings`) opierają się istniejące testy regresyjne (m.in. T023b i inne
rundy audytu).

**Pytanie do architekta:** czy produkt w ogóle potrzebuje widoczności tego
nowego SOFT po stronie walidatora (np. ostrzeżenie po ręcznej poprawce,
która wyraźnie psuje rytm u kogoś), a jeśli tak — w jakim wąskim,
zdarzeniowym kształcie, analogicznym do trzech istniejących ostrzeżeń, nie
jako ogólny re-scoring. Do czasu odpowiedzi `validator.py` zostaje POZA
`TASK_SCOPE`.

## 5. Propozycje techniczne (szkic do korekty przez architekta/Codex)

### 5a. Nagroda za rytm D/N/wolne/wolne — nowa funkcja w `fairness.py`

Dla każdego pracownika, dla każdego okna 4 kolejnych dni kalendarzowych
`(d, d+1, d+2, d+3)` w miesiącu: boolean `pattern_match[employee, d] = 1`
gdy dzień `d` = D, `d+1` = N, `d+2` i `d+3` = brak przypisania (wolne).
Dodać do listy `penalties` **ujemny** wkład (nagrodę) proporcjonalny do
sumy trafień — analogicznie do istniejącego wzorca
`add_weekend_fairness`/`add_holiday_fairness` (nowa funkcja
`add_dn_rhythm_reward(model, x, by_employee, penalties)`), ale z odwrotnym
znakiem: więcej trafień → niższa wartość funkcji celu.

Otwarte dla architekta: dokładna waga; czy okno liczone tylko wewnątrz
miesiąca, czy też na granicy miesięcy (wymagałoby danych z poprzedniego
miesiąca, podobnie jak `historical_holiday_hours`).

### 5b. Naprawa równomierności godzin — nowa funkcja w `fairness.py`

Nowy term min-max spread, ale liczony na **znormalizowanym** stosunku
`actual_hours / target_hours` (nie na surowych godzinach) — żeby nie
krzywdzić pracowników z różnymi etatami/targetami. Analogicznie do
`add_weekend_fairness`: policzyć `ratio_var` per pracownik, dodać
`max_ratio − min_ratio` do `penalties` z nową wagą.

Otwarte dla architekta: dokładna metryka przy `target_hours=0` (dzielenie
przez zero); czy to DODATKOWY term obok istniejącego
`TARGET_DEVIATION_WEIGHT`, czy zamiana; waga względem innych.

## 6. Otwarte pytania dla architekta (blokujące implementację)

1. Waga `add_dn_rhythm_reward` względem istniejących wag
   (`WEEKEND_FAIRNESS_WEIGHT=1`, `HOLIDAY_FAIRNESS_WEIGHT=1`,
   `TARGET_DEVIATION_WEIGHT=100`, `SOFT_PENALTY_WEIGHT`).
2. Dokładna metryka i waga dla §5b (equity godzin) + obsługa
   `target_hours=0`.
3. §4 — zakres i kształt zmian w `validator.py`, jeśli w ogóle potrzebne.
4. Czy §5a i §5b to jeden task (T032) wdrażany razem, czy dwa niezależne
   podzadania mogące iść do implementacji osobno (jedno może czekać na
   decyzję, drugie już nie).

## 7. Minimalna macierz odbioru (do uzupełnienia po odpowiedziach z §6)

Szkic, wymaga dopełnienia wagami/formułą po decyzji architekta:

T32-01 — nowy test jednostkowy odtwarzający potwierdzony bug §2b (te same
targety, niedobór godzin w puli) musi wykazać rozkład bliższy równości niż
dziś (nie musi być idealnie równy — HARD/coverage mają pierwszeństwo).

T32-02 — kandydat z większą liczbą okien D/N/wolne/wolne u tych samych
pracowników przy identycznym pokryciu HARD musi rankingować wyżej niż
kandydat z mniejszą liczbą takich okien, przy pozostałych czynnikach SOFT
równych.

T32-03 — żaden z dwóch nowych termów nie może zmienić wyniku FEASIBLE na
DECISION_REQUIRED ani odwrotnie na żadnym istniejącym scenariuszu
regresyjnym (pełna regresja Python musi przejść bez nowych FAIL).

T32-04 — (warunkowe, tylko jeśli §4 rozstrzygnięte na "tak") — nowy
scenariusz w `validator.py` zgodny z decyzją architekta.
