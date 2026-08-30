# Symulator Koordynatora -- raport przebiegu (ROTA-T043 Checkpoint B)
Miesiąc portfela: 2026-09-01 | obiekty: 20

## Pokrycie osi (brief 4.2)

- Kształty katalogu: D_N_12H, SINGLE_24H, WEEKDAY_12H_WEEKEND_24H
- Liczba warstw: [1, 2]
- Statusy finalne: DECISION_REQUIRED, FEASIBLE
- Wystąpiło EXTERNAL: True
- Wystąpił REPLAN: True
- Wystąpiły absencje: True

## Statusy

{'FEASIBLE': 19, 'DECISION_REQUIRED': 1}

## Seed 0
- Kształt: D_N_12H, warstwy: 1, regime ORDINARY, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_PASS** -- {'employee_count': 5, 'atom_count': 60, 'atom_hours': 12, 'expected_min_spread_hours': 0, 'actual_spread_hours': 0.0}

## Seed 1
- Kształt: D_N_12H, warstwy: 1, regime ORDINARY, obsada: 5
- Absencje: [{'employee_index': 1, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 8), 'end_date': datetime.date(2026, 9, 8), 'employee_id': 'SIM-1-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 2
- Kształt: SINGLE_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 1, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 20), 'end_date': datetime.date(2026, 9, 23), 'employee_id': 'SIM-2-EMP-1'}, {'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 18), 'end_date': datetime.date(2026, 9, 18), 'employee_id': 'SIM-2-EMP-2'}, {'employee_index': 1, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 3), 'end_date': datetime.date(2026, 9, 3), 'employee_id': 'SIM-2-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 3
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 4
- Kształt: D_N_12H, warstwy: 2, regime ORDINARY, obsada: 10
- Absencje: [{'employee_index': 5, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 12), 'end_date': datetime.date(2026, 9, 13), 'employee_id': 'SIM-4-EMP-5'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 5
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 5, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 13), 'end_date': datetime.date(2026, 9, 16), 'employee_id': 'SIM-5-EMP-5'}, {'employee_index': 0, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 14), 'end_date': datetime.date(2026, 9, 18), 'employee_id': 'SIM-5-EMP-0'}, {'employee_index': 2, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 9), 'end_date': datetime.date(2026, 9, 10), 'employee_id': 'SIM-5-EMP-2'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 6
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 3, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 9, 4), 'end_date': datetime.date(2026, 9, 4), 'employee_id': 'SIM-6-EMP-3'}, {'employee_index': 4, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 10), 'end_date': datetime.date(2026, 9, 14), 'employee_id': 'SIM-6-EMP-4'}, {'employee_index': 3, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 16), 'end_date': datetime.date(2026, 9, 18), 'employee_id': 'SIM-6-EMP-3'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 7
- Kształt: D_N_12H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_PASS** -- {'employee_count': 5, 'atom_count': 60, 'atom_hours': 12, 'expected_min_spread_hours': 0, 'actual_spread_hours': 0.0}

## Seed 8
- Kształt: SINGLE_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 1, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 9, 11), 'end_date': datetime.date(2026, 9, 11), 'employee_id': 'SIM-8-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 9
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 2, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 10), 'end_date': datetime.date(2026, 9, 12), 'employee_id': 'SIM-9-EMP-2'}, {'employee_index': 3, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 7), 'end_date': datetime.date(2026, 9, 11), 'employee_id': 'SIM-9-EMP-3'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 10
- Kształt: D_N_12H, warstwy: 2, regime ORDINARY, obsada: 10
- Absencje: [{'employee_index': 4, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 9, 25), 'end_date': datetime.date(2026, 9, 27), 'employee_id': 'SIM-10-EMP-4'}, {'employee_index': 5, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 2), 'end_date': datetime.date(2026, 9, 4), 'employee_id': 'SIM-10-EMP-5'}, {'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 3), 'end_date': datetime.date(2026, 9, 5), 'employee_id': 'SIM-10-EMP-2'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 11
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 0, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 19), 'end_date': datetime.date(2026, 9, 19), 'employee_id': 'SIM-11-EMP-0'}, {'employee_index': 5, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 29), 'end_date': datetime.date(2026, 9, 29), 'employee_id': 'SIM-11-EMP-5'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 12
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 8, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 9, 11), 'end_date': datetime.date(2026, 9, 12), 'employee_id': 'SIM-12-EMP-8'}, {'employee_index': 6, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 17), 'end_date': datetime.date(2026, 9, 19), 'employee_id': 'SIM-12-EMP-6'}]
- PLAN (pierwszy): **DECISION_REQUIRED**
- Reakcja EXTERNAL: SIM-EXTERNAL-12, drugi PLAN: DECISION_REQUIRED
- Wynik finalny: **DECISION_REQUIRED**

## Seed 13
- Kształt: D_N_12H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 20), 'end_date': datetime.date(2026, 9, 24), 'employee_id': 'SIM-13-EMP-2'}, {'employee_index': 4, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 9, 13), 'end_date': datetime.date(2026, 9, 14), 'employee_id': 'SIM-13-EMP-4'}, {'employee_index': 4, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 9, 3), 'end_date': datetime.date(2026, 9, 6), 'employee_id': 'SIM-13-EMP-4'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 14
- Kształt: SINGLE_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 2, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 9, 6), 'end_date': datetime.date(2026, 9, 9), 'employee_id': 'SIM-14-EMP-2'}, {'employee_index': 1, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 24), 'end_date': datetime.date(2026, 9, 25), 'employee_id': 'SIM-14-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 15
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 4, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 9), 'end_date': datetime.date(2026, 9, 10), 'employee_id': 'SIM-15-EMP-4'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 16
- Kształt: D_N_12H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 0, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 9, 2), 'end_date': datetime.date(2026, 9, 6), 'employee_id': 'SIM-16-EMP-0'}, {'employee_index': 4, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 11), 'end_date': datetime.date(2026, 9, 14), 'employee_id': 'SIM-16-EMP-4'}, {'employee_index': 2, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 9, 20), 'end_date': datetime.date(2026, 9, 20), 'employee_id': 'SIM-16-EMP-2'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 17
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 7, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 9, 3), 'end_date': datetime.date(2026, 9, 7), 'employee_id': 'SIM-17-EMP-7'}, {'employee_index': 7, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 11), 'end_date': datetime.date(2026, 9, 14), 'employee_id': 'SIM-17-EMP-7'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 18
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 4, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 9, 8), 'end_date': datetime.date(2026, 9, 9), 'employee_id': 'SIM-18-EMP-4'}, {'employee_index': 9, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 9, 17), 'end_date': datetime.date(2026, 9, 21), 'employee_id': 'SIM-18-EMP-9'}, {'employee_index': 0, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 9, 17), 'end_date': datetime.date(2026, 9, 21), 'employee_id': 'SIM-18-EMP-0'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 19
- Kształt: D_N_12H, warstwy: 1, regime ORDINARY, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Przebieg kwartalny Q3 2026 (obowiązkowy)

- Status: **QUARTER_OK**
- Oracle: **QUARTER_BALANCE_PASS**

## Bramka zaufania do testów (Checkpoint C)

Klasyfikacja istniejących testów (REAL_UI/REAL_API/REAL_APPLICATION/UNIT_OR_ADAPTER/BENCHMARK_ONLY) i kalibracja na znanych błędach nie są jeszcze wykonane -- to zakres Checkpointu C, osobnego kroku.
