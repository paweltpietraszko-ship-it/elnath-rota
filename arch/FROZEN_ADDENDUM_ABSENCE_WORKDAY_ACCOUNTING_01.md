# FROZEN PRODUCT CONTRACT ADDENDUM — ABSENCE-WORKDAY-ACCOUNTING-01

ADDENDUM_ID: ABSENCE-WORKDAY-ACCOUNTING-01
DATE: 2026-08-19
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_SHA: c55722dfa689baa2ae39ba51a0c290f35d7f2112
OWNER_DECISION_SOURCE: arch/ARCHITECT_BRIEF_WORKDAY_ABSENCE_AND_DAY_ONLY_FALLBACK_2026-08-19.md

## SUPERSESSION — EXACT SCOPE

Ta decyzja superseduje wyłącznie wcześniejsze znaczenie „8 h per calendar day” dla księgowania `SICK_LEAVE` / `LEAVE_GRANTED` przeciwko target_hours i WorkBalance.

NIE zmienia:
- wartości 8 h za jeden kwalifikowany dzień;
- rozdziału konsumentów: live TARGET-01 uwzględnia nadal tylko `SICK_LEAVE`, a WorkBalance nadal `SICK_LEAVE` + `LEAVE_GRANTED`;
- inclusive date ranges i przycinania do liczonego miesiąca;
- union/dedup dni jednego employee;
- clamp effective target do zera;
- HARD blokowania Assignment przez `SICK_LEAVE-01` i `LEAVE_GRANTED-01` na każdym dniu kalendarzowym należącym do aktywnego zakresu absencji.

## OWNER DECISION

L4 (`SICK_LEAVE`) i zatwierdzony urlop (`LEAVE_GRANTED`) pomniejszają normę o `8 h` wyłącznie za dni robocze.

Dzień roboczy dla tej reguły to dzień, który jednocześnie:
1. ma ISO weekday 1..5 (poniedziałek–piątek), oraz
2. ma persisted/provided `CalendarDay.holiday == False`.

Sobota, niedziela lub `CalendarDay.holiday=True` daje 0 h pomniejszenia normy.

Holiday nie jest zgadywane z kraju, nazwy święta ani biblioteki systemowej. Źródłem prawdy jest `CalendarDay` dostarczony przez istniejącą warstwę persistence/application.

## CANONICAL OWNERSHIP

`rota/planning/absence.py` pozostaje jednym pure ownership arytmetyki excused absence days.

Solver TARGET-01 oraz `rota.balance` NIE implementują własnego filtrowania weekendów/świąt. Oba konsumują ten sam wynik `excused_absence_days_in_month(...)`.

Dozwolone jest rozszerzenie istniejącej funkcji o dane `calendar_days`; nie tworzyć drugiego helpera z równoległą semantyką w solverze albo balance.

## COUNTING SEMANTICS

Dla employee i miesiąca:

1. wybierz aktywne AvailabilityRecord o dozwolonych `kinds`;
2. przytnij każdy inclusive range do granic miesiąca;
3. zbuduj unię dat per employee — jeden dzień może wejść najwyżej raz, także przy overlap/abut i różnych dozwolonych kinds;
4. z tej unii zachowaj wyłącznie daty Monday–Friday z `CalendarDay.holiday=False`;
5. wynik to liczba pozostałych dat.

`EXCUSED_ABSENCE_HOURS_PER_DAY` pozostaje `8`.

Przykład wiążący: marzec 2027, `SICK_LEAVE 2027-03-02..2027-03-19`, target 168 h -> 14 kwalifikowanych dni -> 112 h redukcji -> effective target 56 h.

## CALENDAR COMPLETENESS / FAIL CLOSED

Gdy w liczonym miesiącu istnieje co najmniej jeden aktywny, kwalifikowany AvailabilityRecord przecinający ten miesiąc, arytmetyka MUST mieć kompletny `CalendarDay` dla każdego dnia tego miesiąca.

Brak któregokolwiek dnia, brak całego kalendarza albo sprzeczne dane dla tej samej daty = jawny błąd `IncompleteAbsenceCalendarError` (lub równoważny, jednoznaczny typ), nigdy fallback do „weekday = workday” i nigdy założenie `holiday=False`.

Jeżeli w miesiącu nie ma żadnego aktywnego rekordu z konsumowanych `kinds`, kalendarz nie wpływa na wynik; legacy/public caller bez calendar_days może zachować wynik bez błędu, bo nic nie jest odejmowane.

PlanningState w normalnym PLAN/REPLAN już posiada kompletne `calendar_days`; solver przekazuje je do canonical absence helper. Brak/niepełność odkryta na publicznym `plan()` boundary ma zakończyć się `TECHNICAL_ERROR`, nie raw exception i nie DECISION_REQUIRED.

## PUBLIC / LEGACY BALANCE CALLS

`compute_month_balance()` i `compute_quarter_balance()` zachowują dotychczasowe argumenty i mogą dostać kompatybilnie dopisany na końcu opcjonalny `calendar_days`.

- caller z kwalifikowaną absencją i bez kompletnego kalendarza: fail closed przez `IncompleteAbsenceCalendarError`;
- caller bez kwalifikowanej absencji: dotychczasowy wynik pozostaje możliwy bez calendar_days;
- nie wolno syntetycznie tworzyć CalendarDay w `rota.balance`.

Persistence reconstruction (`reconstruct_month_balance`, `reconstruct_quarter_balance`) pobiera CalendarDay przez istniejący `rota.persistence.calendar_repository.list_calendar_days(...)` i przekazuje je do `rota.balance`. Bez SQL w `rota.balance`, solverze lub application.

Dla quarter można przekazać jeden zbiór CalendarDay obejmujący kwartał; kompletność jest oceniana niezależnie dla każdego miesiąca, w którym istnieje kwalifikowana absencja.

## CONSUMER BOUNDARY

Live solver TARGET-01:
- nadal `kinds=(SICK_LEAVE,)`;
- używa workday-filtered count;
- NIE dodaje LEAVE_GRANTED do live target adjustment.

WorkBalance month/quarter:
- nadal `SICK_LEAVE + LEAVE_GRANTED`;
- używa workday-filtered count dla obu.

## HARD AVAILABILITY REMAINS CALENDAR-RANGE BASED

Ta reguła NIE filtruje availability eligibility.

Jeżeli aktywny `SICK_LEAVE` / `LEAVE_GRANTED` obejmuje sobotę, niedzielę albo święto, Assignment kolidujący z tym realnym zakresem nadal jest HARD-blocked dokładnie jak przed tym addendum.

Weekend/holiday może więc jednocześnie:
- dawać 0 h redukcji targetu;
- nadal blokować Assignment przez availability.

## NON-GOALS

- brak polskiego kalendarza świąt w kodzie domenowym;
- brak nowej tabeli/calendar service;
- brak zmiany 8 h;
- brak zmiany HARD availability;
- brak zmiany solverowego ownership LEAVE_GRANTED;
- brak drugiego źródła prawdy dla absence day counting.

## REQUIRED ORACLES

1. zakres z dwoma weekendami: tylko weekdays;
2. LEAVE_GRANTED: identyczny filtr w WorkBalance;
3. weekday `holiday=True`: nie liczy się;
4. weekend `holiday=True`: nadal 0, bez podwójnego efektu;
5. overlap SICK_LEAVE/LEAVE_GRANTED: union dat;
6. cross-month range: clipping + workday filter;
7. weekend/holiday w aktywnej absencji nadal HARD-blockuje Assignment;
8. brak/niepełny calendar przy kwalifikowanej absencji: fail closed;
9. marzec 2027 B: effective target 56 h dla L4 2..19 marca przy target 168 h.
