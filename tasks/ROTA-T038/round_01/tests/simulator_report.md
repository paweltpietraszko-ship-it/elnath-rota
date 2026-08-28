# Symulator Koordynatora -- raport przebiegu
Miesiąc: 2026-09-01 | seedy: 5

Znany, zgłoszony brak: SICK_LEAVE przed pierwszym PLAN nie jest tu testowane (patrz arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md) -- SICK_LEAVE po select-candidate/przed REPLAN jest w pełni testowane.

## Seed 0
- Zapotrzebowanie: D_N_12H, regime ORDINARY, 720h/mies.
- Obiekt startowy (5 osób): SIM-0-EMP-0, SIM-0-EMP-1, SIM-0-EMP-2, SIM-0-EMP-3, SIM-0-EMP-4
- Absencje (przed pierwszym PLAN): brak (wszyscy dostępni)
- PLAN (finalny): **FEASIBLE** -- -
  - Użyte osoby (5): SIM-0-EMP-0, SIM-0-EMP-1, SIM-0-EMP-2, SIM-0-EMP-3, SIM-0-EMP-4
- REPLAN: **nie dotyczy** -- wylosowano zero zdarzeń w trakcie miesiąca

## Seed 1
- Zapotrzebowanie: SINGLE_24H, regime OCHRONA, 720h/mies.
- Obiekt startowy (5 osób): SIM-1-EMP-0, SIM-1-EMP-1, SIM-1-EMP-2, SIM-1-EMP-3, SIM-1-EMP-4
- Absencje (przed pierwszym PLAN): SIM-1-EMP-1: LEAVE_GRANTED 2026-09-08..2026-09-08
- Koordynator dopisał w reakcji na DECISION_REQUIRED: SIM-1-EMP-5, SIM-1-EMP-6, SIM-1-EMP-7, SIM-1-EMP-8
- PLAN (finalny): **DECISION_REQUIRED** -- Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.
- REPLAN: **pominięto** -- brak grafiku bazowego po wyczerpaniu prób zatrudnienia

## Seed 2
- Zapotrzebowanie: D_N_12H, regime ORDINARY, 720h/mies.
- Obiekt startowy (5 osób): SIM-2-EMP-0, SIM-2-EMP-1, SIM-2-EMP-2, SIM-2-EMP-3, SIM-2-EMP-4
- Absencje (przed pierwszym PLAN): SIM-2-EMP-1: LEAVE_GRANTED 2026-09-20..2026-09-23; SIM-2-EMP-2: LEAVE_GRANTED 2026-09-18..2026-09-18; SIM-2-EMP-1: UNAVAILABLE_24H 2026-09-03..2026-09-03
- PLAN (finalny): **FEASIBLE** -- -
  - Użyte osoby (5): SIM-2-EMP-0, SIM-2-EMP-1, SIM-2-EMP-2, SIM-2-EMP-3, SIM-2-EMP-4
- Absencje (zdarzenie w trakcie miesiąca): SIM-2-EMP-1: SICK_LEAVE 2026-09-19..2026-09-23
- REPLAN: **FEASIBLE** -- -
  - Użyte osoby (5): SIM-2-EMP-0, SIM-2-EMP-1, SIM-2-EMP-2, SIM-2-EMP-3, SIM-2-EMP-4

## Seed 3
- Zapotrzebowanie: SINGLE_24H, regime OCHRONA, 720h/mies.
- Obiekt startowy (5 osób): SIM-3-EMP-0, SIM-3-EMP-1, SIM-3-EMP-2, SIM-3-EMP-3, SIM-3-EMP-4
- Absencje (przed pierwszym PLAN): brak (wszyscy dostępni)
- Koordynator dopisał w reakcji na DECISION_REQUIRED: SIM-3-EMP-5, SIM-3-EMP-6, SIM-3-EMP-7, SIM-3-EMP-8
- PLAN (finalny): **DECISION_REQUIRED** -- Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.
- REPLAN: **pominięto** -- brak grafiku bazowego po wyczerpaniu prób zatrudnienia

## Seed 4
- Zapotrzebowanie: SINGLE_24H, regime OCHRONA, 720h/mies.
- Obiekt startowy (5 osób): SIM-4-EMP-0, SIM-4-EMP-1, SIM-4-EMP-2, SIM-4-EMP-3, SIM-4-EMP-4
- Absencje (przed pierwszym PLAN): SIM-4-EMP-2: LEAVE_PLAN 2026-09-08..2026-09-10
- Koordynator dopisał w reakcji na DECISION_REQUIRED: SIM-4-EMP-5, SIM-4-EMP-6, SIM-4-EMP-7, SIM-4-EMP-8
- PLAN (finalny): **DECISION_REQUIRED** -- Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Koliduje z limitem dwóch nocek pod rząd | Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach.
- REPLAN: **pominięto** -- brak grafiku bazowego po wyczerpaniu prób zatrudnienia
