# Symulator Koordynatora -- raport przebiegu (ROTA-T043 Checkpoint B)
Miesiące portfela: 2026-01-01, 2026-02-01, 2026-03-01, 2026-04-01, 2026-05-01, 2026-06-01, 2026-07-01, 2026-08-01, 2026-09-01, 2026-10-01, 2026-11-01, 2026-12-01 | obiekty: 20

## Pokrycie osi (brief 4.2)

- Miesiące: 2026-01-01, 2026-02-01, 2026-03-01, 2026-04-01, 2026-05-01, 2026-06-01, 2026-07-01, 2026-08-01, 2026-09-01, 2026-10-01, 2026-11-01, 2026-12-01
- Kształty katalogu: D_N_12H, SINGLE_24H, WEEKDAY_12H_WEEKEND_24H
- Liczba warstw: [1, 2]
- Statusy finalne: CRASH, DECISION_REQUIRED, FEASIBLE
- Wystąpiło EXTERNAL: True
- Wystąpił REPLAN: True
- Wystąpiły absencje: True

## Statusy

{'FEASIBLE': 17, 'DECISION_REQUIRED': 1, 'CRASH': 2}

## Seed 0
- Kształt: D_N_12H, warstwy: 1, regime ORDINARY, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_PASS** -- {'employee_count': 5, 'atom_count': 62, 'atom_hours': 12, 'expected_min_spread_hours': 12, 'actual_spread_hours': 12.0}

## Seed 1
- Kształt: D_N_12H, warstwy: 1, regime ORDINARY, obsada: 5
- Absencje: [{'employee_index': 1, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 2, 8), 'end_date': datetime.date(2026, 2, 19), 'employee_id': 'SIM-1-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 2
- Kształt: SINGLE_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 1, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 3, 20), 'end_date': datetime.date(2026, 3, 27), 'employee_id': 'SIM-2-EMP-1'}, {'employee_index': 2, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 3, 8), 'end_date': datetime.date(2026, 3, 9), 'employee_id': 'SIM-2-EMP-2'}, {'employee_index': 0, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 3, 3), 'end_date': datetime.date(2026, 3, 5), 'employee_id': 'SIM-2-EMP-0'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: NARROW_SEARCH_EXHAUSTED

## Seed 3
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: brak
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 4
- Kształt: D_N_12H, warstwy: 2, regime ORDINARY, obsada: 10
- Absencje: [{'employee_index': 5, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 5, 12), 'end_date': datetime.date(2026, 5, 19), 'employee_id': 'SIM-4-EMP-5'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 5
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 5, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 6, 13), 'end_date': datetime.date(2026, 6, 20), 'employee_id': 'SIM-5-EMP-5'}, {'employee_index': 0, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 6, 14), 'end_date': datetime.date(2026, 6, 18), 'employee_id': 'SIM-5-EMP-0'}, {'employee_index': 9, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 6, 21), 'end_date': datetime.date(2026, 6, 22), 'employee_id': 'SIM-5-EMP-9'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 6
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 3, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 7, 4), 'end_date': datetime.date(2026, 7, 4), 'employee_id': 'SIM-6-EMP-3'}, {'employee_index': 4, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 7, 10), 'end_date': datetime.date(2026, 7, 27), 'employee_id': 'SIM-6-EMP-4'}, {'employee_index': 3, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 7, 16), 'end_date': datetime.date(2026, 7, 24), 'employee_id': 'SIM-6-EMP-3'}]
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
- FAIRNESS: **FAIRNESS_PASS** -- {'employee_count': 5, 'atom_count': 62, 'atom_hours': 12, 'expected_min_spread_hours': 12, 'actual_spread_hours': 12.0}

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
- Absencje: [{'employee_index': 2, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 10, 10), 'end_date': datetime.date(2026, 10, 30), 'employee_id': 'SIM-9-EMP-2'}, {'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 10, 27), 'end_date': datetime.date(2026, 10, 28), 'employee_id': 'SIM-9-EMP-2'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 10
- Kształt: D_N_12H, warstwy: 2, regime ORDINARY, obsada: 10
- Absencje: [{'employee_index': 4, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 11, 25), 'end_date': datetime.date(2026, 11, 27), 'employee_id': 'SIM-10-EMP-4'}, {'employee_index': 5, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 11, 2), 'end_date': datetime.date(2026, 11, 13), 'employee_id': 'SIM-10-EMP-5'}, {'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 11, 3), 'end_date': datetime.date(2026, 11, 8), 'employee_id': 'SIM-10-EMP-2'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: FEASIBLE

## Seed 11
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 0, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 12, 19), 'end_date': datetime.date(2026, 12, 19), 'employee_id': 'SIM-11-EMP-0'}, {'employee_index': 5, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 12, 29), 'end_date': datetime.date(2026, 12, 29), 'employee_id': 'SIM-11-EMP-5'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 12
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 8, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 1, 11), 'end_date': datetime.date(2026, 1, 12), 'employee_id': 'SIM-12-EMP-8'}, {'employee_index': 6, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 1, 17), 'end_date': datetime.date(2026, 1, 29), 'employee_id': 'SIM-12-EMP-6'}]
- PLAN (pierwszy): **DECISION_REQUIRED**
- Reakcja EXTERNAL: SIM-EXTERNAL-12, drugi PLAN: DECISION_REQUIRED
- Wynik finalny: **DECISION_REQUIRED**

## Seed 13
- Kształt: D_N_12H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 2, 'kind': 'LEAVE_GRANTED', 'start_date': datetime.date(2026, 2, 20), 'end_date': datetime.date(2026, 2, 28), 'employee_id': 'SIM-13-EMP-2'}, {'employee_index': 4, 'kind': 'LEAVE_PLAN', 'start_date': datetime.date(2026, 2, 13), 'end_date': datetime.date(2026, 2, 14), 'employee_id': 'SIM-13-EMP-4'}, {'employee_index': 4, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 2, 13), 'end_date': datetime.date(2026, 2, 14), 'employee_id': 'SIM-13-EMP-4'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 14
- Kształt: SINGLE_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 2, 'kind': 'DAY_SHIFT_OFF', 'start_date': datetime.date(2026, 3, 6), 'end_date': datetime.date(2026, 3, 9), 'employee_id': 'SIM-14-EMP-2'}, {'employee_index': 1, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 3, 24), 'end_date': datetime.date(2026, 3, 25), 'employee_id': 'SIM-14-EMP-1'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}
- REPLAN: NARROW_SEARCH_EXHAUSTED

## Seed 15
- Kształt: WEEKDAY_12H_WEEKEND_24H, warstwy: 1, regime OCHRONA, obsada: 5
- Absencje: [{'employee_index': 4, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 4, 9), 'end_date': datetime.date(2026, 4, 10), 'employee_id': 'SIM-15-EMP-4'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 16
- **AWARIA (do przejrzenia)**: None

## Seed 17
- Kształt: SINGLE_24H, warstwy: 2, regime OCHRONA, obsada: 10
- Absencje: [{'employee_index': 7, 'kind': 'SICK_LEAVE', 'start_date': datetime.date(2026, 6, 3), 'end_date': datetime.date(2026, 6, 19), 'employee_id': 'SIM-17-EMP-7'}, {'employee_index': 7, 'kind': 'UNAVAILABLE_24H', 'start_date': datetime.date(2026, 6, 11), 'end_date': datetime.date(2026, 6, 14), 'employee_id': 'SIM-17-EMP-7'}]
- PLAN (pierwszy): **FEASIBLE**
- Wynik finalny: **FEASIBLE**
- PRODUCT_VALIDATE: **PRODUCT_VALIDATE_PASS**
- FAIRNESS: **FAIRNESS_UNPROVEN** -- {'reason': 'not the frozen symmetric control class (B3.1)'}

## Seed 18
- **AWARIA (do przejrzenia)**: None

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

### Klasyfikacja dowodu (brief 6.1/6.2)

| Obszar (brief 6.2) | Plik(i) | Klasa |
|---|---|---|
| PLAN / wybór kandydata | `tests/test_t009_plan_select_replan.py` | REAL_APPLICATION |
| | `tests/test_t031_schedule_api.py`, `tests/test_t042_audit4_repairs.py` | REAL_API |
| | `tests/property/test_coordinator_simulator.py` (T043) | REAL_API |
| Fairness i H24 | `tests/test_t041_checkpoint_a.py` (hand-built `PlanningState`) | UNIT_OR_ADAPTER |
| | `tests/test_t040_h24_rhythm_occupancy.py` (`plan_ops.plan_month`) | REAL_APPLICATION |
| | `tests/property/test_coordinator_simulator.py`'s symmetric fairness verdicts (T043 Checkpoint B) | REAL_API |
| Urlop/L4 przed PLAN i przed REPLAN | `tests/test_t041_checkpoint_b.py` | REAL_API |
| | `tests/property/test_coordinator_simulator.py` (T043) | REAL_API |
| Nakładające się demandy | `tests/test_t041_checkpoint_a.py` (a07-a13, hand-built `PlanningState`) | UNIT_OR_ADAPTER |
| | *(brak REAL_APPLICATION/REAL_API piona w granicach TASK_SCOPE T043 -- patrz uwaga niżej)* | -- |
| EXTERNAL_SUPPORT i okna | `tests/test_t041_checkpoint_a.py::test_t41_a05_external_support_excluded_from_available_local_ids` (hand-built state) | UNIT_OR_ADAPTER |
| | `tests/property/test_coordinator_simulator.py::test_decision_required_triggers_external_reaction_with_correct_decision_link_ordering` (T043) | REAL_API |
| Target, REPLAN i WorkBalance quarter carry-in | `tests/test_t011_d_quarter_balance.py` | REAL_APPLICATION |
| | `tests/property/test_coordinator_simulator.py`'s `run_quarter`/B6 oracle (T043) | REAL_API |
| Ostrzeżenia i wynik widoczny w UI | `frontend/e2e/t041-daily-workflow.spec.ts` | REAL_UI |
| | `frontend/e2e/t043-coordinator-confidence.spec.ts` (NOWY, Checkpoint C) | REAL_UI |

**OTWARTA FLAGA (R6 korekta):** Checkpoint C pierwotnie dopisał nowy test
`test_43c_two_legal_overlapping_demands_via_real_assembler_and_validator` do
`tests/test_t009_plan_select_replan.py`, żeby dać "Nakładającym się demandom"
realny REAL_APPLICATION pion. Ten plik NIE jest w TASK_SCOPE T043 (brief.md
sekcja 9) -- zmiana została cofnięta do stanu `main@c25c73e0`
(Codex R6 finding T43-R6-05). Realny REAL_APPLICATION/REAL_API pion dla tego
obszaru nadal nie istnieje w granicach TASK_SCOPE T043; dodanie go wymaga albo
zgody OWNERA na rozszerzenie zakresu, albo osobnego, małego follow-up Tasku.
To jest świadomie zostawione otwarte dla architekta/OWNERA, nie rozwiązane
tutaj (brief sekcja 12: potrzebna zmiana poza TASK_SCOPE = zatrzymać się i
zgłosić, nie obchodzić po cichu).

Uwaga o wspólnej zależności: `tests/support/t009_fixtures.py::seed_real_object` (użyty przez wiele powyższych REAL_APPLICATION/REAL_API testów, w tym `test_t009_plan_select_replan.py` i `test_t011_d_quarter_balance.py`) buduje swój obiekt przez `benchmarks/real_object_production.py`/`benchmarks/real_object_scenarios.py` -- moduły odrzucone przez OWNERA jako *oracle* (`feedback_no_benchmarks_generator_ever`). To nie czyni tych testów `BENCHMARK_ONLY`: ich własne asercje (FEASIBLE, atomowość wersji, poprawność coverage) są niezależne od jakiegokolwiek werdyktu benchmarku -- tylko KSZTAŁT obiektu (roster/katalog) pochodzi stamtąd. Warto to jednak wiedzieć: żaden REAL_APPLICATION test w tej tabeli nie jest w pełni niezależny od `benchmarks/**` jako generatora scenariusza.

Dwie ostatnie klasy (`UNIT_OR_ADAPTER`, `BENCHMARK_ONLY`) pozostają wartościowe dla precyzyjnych przypadków brzegowych (np. a08-a13's excess/gap/false-tag matrix), ale nigdie w tym raporcie nie są przedstawiane jako samodzielny dowód działania programu -- każdy obszar ma teraz co najmniej jeden REAL_API/REAL_APPLICATION/REAL_UI pion.

### Prawdziwy browser (brief 6.3)

`frontend/e2e/t043-coordinator-confidence.spec.ts` -- 1/1 PASS. Koordynator tworzy obiekt, dostaje 5 LOCAL, widzi "Obsada (5)", ustawia target godzin pierwszej osobie, klika PLAN, a ekran pokazuje dokładnie ten status ("Kandydaci" dla FEASIBLE albo baner decyzji dla DECISION_REQUIRED), jaki zwróciła realna odpowiedź API przechwycona w tym samym teście (nie sztywne oczekiwanie).

### Kalibracja na znanych błędach (brief 6.4)

Wszystkie trzy mutacje wykonane pojedynczo, bezpośrednio w tym worktree, i natychmiast cofnięte (`git checkout -- <plik>`) po każdym pomiarze. `git diff task/ROTA-T043 -- rota/ api/ frontend/src/ benchmarks/` jest puste (0 linii) na commit tego Checkpointu -- zero zmutowanego kodu produktu w wypchniętej gałęzi.

1. **H24 `occupancy=2*x` jako Boolean** (przywrócony pre-T040 `fairness.add_dn_rhythm_reward`, commit `fa70b1c` cofnięty tymczasowo): `tests/test_t040_h24_rhythm_occupancy.py` -- 3/6 CZERWONE pod mutacją (`test_t40_01...`, `test_t40_04...`, `test_t40_05...`, realny H24 obiekt zwraca DECISION_REQUIRED zamiast FEASIBLE), 6/6 ZIELONE po cofnięciu.
2. **Wyłączony fallback fairness dla brakującego targetu** (`add_equal_split_fairness` w `solver.py` zakomentowany): `tests/test_t041_checkpoint_a.py::test_t41_a01_one_missing_target_splits_equally_across_all_five` -- CZERWONY pod mutacją (godziny 132/156/144/168/120 zamiast równego 144/144/144/144/144), ZIELONY po cofnięciu.
3. **Stare geometryczne podwójne liczenie nakładających się demandów** (`validator._check_coverage`'s tag-disambiguation wyłączona): `tests/test_t041_checkpoint_a.py::test_t41_a07_two_legal_overlapping_demands_correctly_assigned_passes` (istniejący test, UNIT_OR_ADAPTER -- jedyny dostępny pion w granicach TASK_SCOPE po R6 cofnięciu) -- CZERWONY pod mutacją (fałszywy COVERAGE-01 excess na obu legalnych, nakładających się demandach), ZIELONY po cofnięciu. Ten pion jest UNIT_OR_ADAPTER, nie REAL_APPLICATION -- patrz otwarta flaga wyżej.

Wniosek: żadna z trzech klas błędów nie pozostała cicho zielona -- bramka zaufania działa.
