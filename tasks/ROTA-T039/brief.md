# ROTA-T039 — Symulator Koordynatora: niejednorodne katalogi zmian

Status: **IMPLEMENTACJA ZAKOŃCZONA (autor: CC), do audytu**

Base implementation SHA: `67a245539400795bcf86234efad1f808a9f11013` (`main`,
po zmergowaniu T038).

Owner decision: Paweł, 2026-08-28 (rozmowa) — T038 (Symulator Koordynatora,
zmergowany) budował tylko jednorodne obiekty (ta sama zmiana/liczba osób
każdego dnia). Realne obiekty bywają bardziej złożone: inny wzorzec
tydzień/weekend, ta sama nocka pokrywana przez dwie osoby o różnej
długości dyżuru. Zadanie: rozbudować generator symulatora o te wzorce.

TASK_SCOPE:
- tests/property/coordinator_simulator.py
- tasks/ROTA-T039/brief.md

## 1. Wynik dla właściciela

Generator (`random_object_spec`) losuje teraz jeden z 4 kształtów katalogu
zmian (`_CATALOG_ROWS`), nie tylko poprzednie 2:

- `D_N_12H` (bez zmian) — D+N po 12h, codziennie.
- `SINGLE_24H` (bez zmian) — jedna zmiana 24h, codziennie.
- `WEEKDAY_12H_WEEKEND_24H` (nowy) — D+N 12h w dni robocze (pon-pt), jedna
  zmiana 24h w weekend (sob-nd). Ta sama łączna liczba godzin/dobę (24h),
  inny kształt katalogu zależny od dnia tygodnia.
- `SPLIT_NIGHT_12_8` (nowy) — nocka pokrywana przez dwie osoby o różnej
  długości dyżuru: jedna 18:00-06:00 (12h), druga tylko 22:00-06:00 (8h) —
  dokładnie przykład z realnego grafiku podany przez właściciela.

`monthly_hours_needed` (a więc i wyliczana obsada) jest teraz sumowane
wprost z rzeczywistych wierszy katalogu (`monthly_hours_for_shape`), nie z
osobnej, sztywnej formuły `24*posts*dni` — eliminuje ryzyko rozjazdu między
katalogiem a matematyką obsady przy przyszłych kształtach.

## 2. Realne znalezisko po drodze — nakładające się zapotrzebowania są dziś błędnie liczone

Pierwsza próba modelowania `SPLIT_NIGHT_12_8` (dwa NAKŁADAJĄCE się wiersze
"N": 18:00-06:00 wymaga 1 i 18:00-02:00 wymaga 1) dawała **`TECHNICAL_ERROR`**
na każdym dniu miesiąca (`COVERAGE-01 coverage excess 2/1 PRIMARY`).

Przyczyna, potwierdzona w kodzie: `rota/planning/validator.py::_check_coverage`
liczy pokrycie zapotrzebowania na podstawie **geometrycznego nakładania się**
wszystkich przypisań PRIMARY, nie przez przypisanie do konkretnego
zapotrzebowania (`covers_demand_id` jest jawnie ignorowane — cytat z kodu:
"not covers_demand_id tagging"). Dwa NAPRAWDĘ nakładające się zapotrzebowania,
każde wymagające 1 osoby, wzajemnie liczą się nawzajem jako "nadmiar
pokrycia" — mimo że `shift_catalog.py::generate_catalog_demands` wprost
deklaruje "overlaps are legal and generate independent occurrences".

To jest rozbieżność między udokumentowaną możliwością (overlaps są legalne
na poziomie generowania zapotrzebowań) a rzeczywistym zachowaniem walidatora
pokrycia (nie obsługuje poprawnie nakładających się zapotrzebowań z osobnymi
wymaganiami). CC to obszedł, nie naprawił: `SPLIT_NIGHT_12_8` przeprojektowany
na dwa SĄSIADUJĄCE (nienakładające się) zapotrzebowania (18:00-22:00 wymaga
1, 22:00-06:00 wymaga 2) — zweryfikowane, działa poprawnie (brak
`TECHNICAL_ERROR`, tylko realny `DECISION_REQUIRED` przy minimalnej obsadzie).

**Nie zgłoszone jako osobny brief architekta w tej rundzie** — jeśli
właściciel uzna to za wart uwagi problem (nakładające się zapotrzebowania są
udokumentowane jako legalne, ale walidator ich nie obsługuje), potrzebny
osobny brief, analogiczny do `ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md`.

## 3. Dodatkowe znalezisko z pełnego przebiegu — SINGLE_24H przy minimalnej obsadzie utyka na NIGHT-STREAK-01

Pełny przebieg (5 seedów) pokazał: obiekty `SINGLE_24H` przy dokładnie
wyliczonej minimalnej obsadzie (5 osób) regularnie kończą jako
`DECISION_REQUIRED` — powód: "Koliduje z limitem dwóch nocek pod rząd"
(NIGHT-STREAK-01, T032). Reaktywne zatrudnianie (`hire_one_more_local`,
do `MAX_HIRES=4`) **nie rozwiązuje tego** — nawet przy 9 osobach dalej
`DECISION_REQUIRED` z tym samym powodem.

To sugeruje, że heurystyka `ceil(godziny/160)` jest zbyt optymistyczna dla
obiektów z codzienną zmianą 24h — sam wymiar godzinowy nie uwzględnia
ograniczeń rotacji/odpoczynku między kolejnymi 24h dyżurami. Zgłaszane jako
obserwacja z raportu, nie jako błąd do naprawy w tym tasku — symulator
zrobił dokładnie to, do czego służy (ujawnił fakt), nie ocenia go.

## 4. Poza zakresem

- Naprawa walidatora dla nakładających się zapotrzebowań (punkt 2) —
  wymagałby briefu architekta, nie zrobione tutaj.
- Poprawa heurystyki obsady dla `SINGLE_24H` (punkt 3) — obserwacja do
  przemyślenia, nie zaimplementowana zmiana.
- `posts` nadal na stałe 1 (bez zmian z T038).

## 5. Weryfikacja

- `ruff check tests/property/` — czyste.
- Zweryfikowane osobno (bez pełnego przebiegu): `monthly_hours_for_shape`
  dla wszystkich 4 kształtów (720h dla trzech jednorodnych co do sumy,
  960h dla `SPLIT_NIGHT_12_8`), zgodne z ręcznym wyliczeniem.
- Pojedyncze seedy z nowymi kształtami (5, 9) sprawdzone osobno przed
  pełnym przebiegiem — złapały i pozwoliły naprawić `TECHNICAL_ERROR`
  wcześniej niż pełny, kosztowny przebieg by to zrobił.
- Pełny formalny przebieg (5 seedów): `1 passed in 104.39s (0:01:44)`,
  zero awarii, `simulator_report.md` dołączony do commita jako dowód.
