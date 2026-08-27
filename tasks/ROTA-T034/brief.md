# ROTA-T034 — SOFT: trzecia zmiana z rzędu

Status: **READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS**

BASE_MAIN_SHA: `05514c26b9e29e8ff11a03d422c4c8f15f7a2442`
ARCHITECT_VERIFIED_MAIN_SHA: `05514c26b9e29e8ff11a03d422c4c8f15f7a2442`
OWNER_RULING_DATE: 2026-08-26
SOURCE: `ARCHITECT_BRIEF_DAY_SHIFT_STREAK_LIMIT_2026-08-26.md`

T034 dodaje wyłącznie jeden rankingowy SOFT dla trzeciej kolejnej zmiany. Nie zmienia HARD, validatora, czasu planowania, REPLAN, DTO ani persistence.

## 1. Zamrożony wynik produktu

Dla jednego pracownika solver ma preferować brak dokładnie tych trzech sekwencji zmian rozpoczynających się w trzech kolejnych datach kalendarzowych:

- `D / D / D`;
- `D / D / N`;
- `D / N / N`.

Każde 3-dniowe okno zawierające co najmniej jedną z powyższych sekwencji wnosi **jedną** karę SOFT. Jedno okno nigdy nie jest karane podwójnie tylko dlatego, że nietypowy dzień technicznie zawiera więcej niż jeden komponent D/N.

Reguła pozostaje wyłącznie SOFT:

- kandydat z taką sekwencją nadal może być `FEASIBLE`;
- nie powstaje `DECISION_REQUIRED`;
- independent validator nie odrzuca kandydata z tego powodu;
- ręczna korekta nie jest odrzucana wyłącznie przez T034;
- solver nie musi udowodnić, że lepszego wariantu bez tej sekwencji nie ma.

`N / N / N` nie należy do T034. Nadal jest wyłącznie istniejącym HARD `NIGHT-STREAK-01`.

## 2. Potwierdzeni ownerzy na exact main

Na `05514c26b9e29e8ff11a03d422c4c8f15f7a2442` istnieją i są jedynymi ownerami potrzebnymi T034:

- `rota/planning/solver.py::_build_day_kind_terms` — jedno źródło per-employee/start-date dla D, N i occupied; składa nowe `x`, fixed target-Site oraz `boundary_assignments`, a D/N klasyfikuje przez canonical `classify_demand`;
- `rota/planning/fairness.py::add_dn_rhythm_reward` — istniejący precedent czystego SOFT opartego na `day_kind_terms`;
- `rota/planning/constraints.py::add_max_two_consecutive_night_constraints` — istniejący HARD `NIGHT-STREAK-01`, którego T034 nie zmienia;
- `rota/planning/solver.py::_add_combined_objective` — jedyny owner połączenia TARGET-01, equity, rhythm i pozostałych SOFT;
- istniejący `optimization_complete`, `search_attempt` i budżety planowania/REPLAN pozostają bez zmian.

T034 nie czyta poprzedniego miesiąca drugi raz i nie tworzy drugiej klasyfikacji D/N.

## 3. Jedyny nowy helper SOFT

W `rota/planning/fairness.py` dodać:

`THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT = 1`

oraz jeden helper, nazwa kanoniczna:

`add_third_consecutive_shift_penalty(model, month, day_kind_terms, penalties) -> int`

### 3.1 Wejście

Helper dostaje wyłącznie:

- istniejący `CpModel`;
- `state.month`;
- już zbudowane `day_kind_terms`;
- istniejącą listę `penalties`.

Nie dostaje `PlanningState`, Assignments, repozytorium ani profilu i niczego sam nie klasyfikuje.

`day_kind_terms[employee_id][date]` pozostaje istniejącym tuple `(d_term, n_term, any_term, n_demand_id)`. T034 używa tylko `d_term` i `n_term`.

### 3.2 Okna czasowe i boundary

Rozpatruj wszystkie trójki kolejnych dat `(d, d+1, d+2)`, które **przecinają planowany miesiąc**:

- pierwszy możliwy start: `month_start - 2 dni`;
- ostatni możliwy start: `month_end`.

Dzięki temu bez nowego inputu działają zarówno okna wchodzące z poprzedniego miesiąca, jak i wychodzące do następnego miesiąca, jeżeli odpowiedni persisted target-Site boundary fact już istnieje w `day_kind_terms`.

Brak wpisu dla daty oznacza brak znanego D/N na tej dacie. Nie zgadywać brakującej historii ani przyszłości.

Okno złożone wyłącznie z niezmiennych fixed/boundary constants nie trafia do objective, bo nie może zmienić rankingu bieżącego solve.

### 3.3 Dokładne dopasowanie

Dla jednego dnia `D` oznacza istniejący `d_term == 1`, a `N` oznacza istniejący `n_term == 1`. Jeżeli term jest expression, helper może reużyć istniejący prywatny `_exactly_one(...)`; nie tworzyć nowego sposobu klasyfikowania zmiany.

Dla każdego okna kara jest aktywna wtedy i tylko wtedy, gdy spełnione jest co najmniej jedno:

- `D0 ∧ D1 ∧ D2`;
- `D0 ∧ D1 ∧ N2`;
- `D0 ∧ N1 ∧ N2`.

Jedno okno = maksymalnie jeden bool `bad_window`, niezależnie od liczby spełnionych wariantów.

To nie obejmuje `D/N/D`, `N/D/D`, `N/D/N`, `N/N/D` ani żadnej innej sekwencji. T034 nie rozszerza owner ruling.

### 3.4 Minimalne kodowanie CP-SAT

Nie budować osobnego automatu/stanu sekwencji.

Wystarczy jeden `bad_window` BoolVar dla okna, które może zależeć od bieżących decyzji, i dolne ograniczenie dla każdego możliwego wzorca, np. logiczny odpowiednik:

`bad_window >= literal_1 + literal_2 + literal_3 - 2`.

Ponieważ objective minimalizuje `bad_window`, nie jest potrzebny drugi scorer ani rozbudowana reifikacja całego automatu. Literały D/N normalizować leniwie i lokalnie; wolno użyć małego cache `(employee_id, date, kind)`, aby nie tworzyć tej samej reifikacji wielokrotnie w nakładających się oknach.

Helper dopisuje:

`THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT * sum(bad_windows)`

do `penalties` i zwraca liczbę **zmiennych** `bad_window`. Jest to ścisły górny bound maksymalnego rankingowego swing tej kary w tym solve.

Jeżeli nie powstał żaden zmienny `bad_window`, helper niczego nie dopisuje i zwraca `0`.

## 4. Wiring i pierwszeństwo TARGET-01

W `solver.py::_add_combined_objective` wywołać nowy helper na tym samym `day_kind_terms`, którego używa rhythm.

Nie dodawać nowej fazy leksykograficznej.

Istniejąca matematyczna ochrona TARGET-01 przed T032 equity/rhythm ma zostać rozszerzona dokładnie o maksymalny wpływ T034:

`target_weight = TARGET_DEVIATION_WEIGHT`
`    + TARGET_EQUITY_WEIGHT * MAX_COMPLETION_PCT`
`    + DN_RHYTHM_REWARD_WEIGHT * rhythm_match_count`
`    + THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT * third_shift_penalty_count`

Wynik: poprawa nowego SOFT nigdy nie może kupić nawet 1h gorszego łącznego TARGET-01 względem zestawu SOFT objętego już tą matematyczną ochroną.

T034 nie zmienia istniejącej relacji TARGET-01 do starszych weekend/holiday/LEAVE_PLAN/DAY_SHIFT_OFF terms; to nie jest zadanie do globalnego przeprojektowania objective.

## 5. Budżet, optimization_complete i search_attempt

Bez zmian.

- T034 korzysta z tego samego modelu i jednego istniejącego solve;
- nie dodaje osobnego solve ani proof phase;
- nie zmienia `PLANNING_OPERATION_BUDGET_SECONDS` ani `REPLAN_SEARCH_BUDGET_SECONDS`;
- `optimization_complete` zachowuje obecne znaczenie;
- `search_attempt` zachowuje obecne znaczenie i może znaleźć inny/lepszy wariant, ale niczego nie gwarantuje.

## 6. TASK_SCOPE

Production — dokładnie:

- `rota/planning/fairness.py`;
- `rota/planning/solver.py`.

Tests:

- `tests/test_t034_third_consecutive_shift_soft.py`.

Nie modyfikować:

- `rota/planning/constraints.py`;
- `rota/planning/validator.py`;
- `rota/planning/engine.py` / `engine_types.py`;
- `rota/application/**`;
- `api/**`, `frontend/**`;
- persistence/domain/assembler;
- REST/WEEKLY-REST/LOAD/eligibility;
- `NIGHT-STREAK-01`;
- target/absence accounting;
- REPLAN-T033 mechanics.

Jeżeli implementator uważa, że potrzebuje pliku spoza tego scope, zgłasza konkretny blocker zamiast budować równoległy mechanizm.

## 7. Minimalna macierz odbioru

T34-01 — kontrolowany ranking `D/D/D`: przy identycznej wcześniejszej jakości wariant bez tej trójki ma niższy objective.

T34-02 — analogicznie `D/D/N`.

T34-03 — analogicznie `D/N/N`.

T34-04 — jedno 3-dniowe okno wnosi maksymalnie jedną karę, nawet jeśli technicznie więcej niż jeden wzorzec byłby jednocześnie rozpoznawalny.

T34-05 — boundary `30.08 / 31.08 / 01.09`: persisted D/D + bieżący D lub N jest oceniany z tych samych `day_kind_terms`; brak drugiego history read.

T34-06 — boundary `31.08 / 01.09 / 02.09`: persisted D + bieżące D/D, D/N albo N/N działa odpowiednio.

T34-07 — brak persisted boundary fact nie jest zastępowany domysłem i sam nie tworzy kary.

T34-08 — tylko dwie kolejne zmiany nie tworzą kary.

T34-09 — `N/N/N` nie tworzy nowego T034 SOFT; nadal jest odrzucane przez istniejący `NIGHT-STREAK-01` HARD.

T34-10 — realny `solve()` ma przynajmniej jeden kontrolowany przypadek z dwoma HARD-poprawnymi możliwościami o tej samej wcześniejszej jakości, w którym wynik wybiera wariant bez jednej z trzech karanych trójek. To jest pionowy wiring test, nie drugi solver.

T34-11 — matematyczna ochrona TARGET-01 uwzględnia realny `third_shift_penalty_count`; wariant z lepszym T034 SOFT nie może wygrać kosztem gorszego łącznego TARGET-01.

T34-12 — istniejące T032/T033 regressions dla rhythm, NIGHT-STREAK-01, `optimization_complete` i `search_attempt` pozostają zielone. Nie kopiować ich pełnych macierzy do nowego pliku.

Ręczna korekta nie potrzebuje nowego testu validatora: scope gwarantuje brak zmian validatora, a T034 jest objective-only.

## 8. PREIMPLEMENTATION REDUCTION GATE

Po redukcji pozostają tylko elementy konieczne:

- jeden helper SOFT — owner-visible ranking;
- jedno wywołanie helpera w istniejącym combined objective;
- jeden dodatkowy składnik górnego boundu chroniącego TARGET-01;
- jeden nowy plik testów dla nowego seam.

Usunięte jako niepotrzebne:

- HARD/validator/decision guidance;
- drugi day-kind builder albo boundary reader;
- nowa faza solvera;
- DTO/status/API/UI;
- osobny state machine sekwencji;
- persistence/job/session;
- zmiany REPLAN/search_attempt/budżetu.

## 9. PREIMPLEMENTATION AUDIT

Independent Codex audituje exact contract HEAD i odpowiada wyłącznie:

1. Czy helper reuse istniejące `day_kind_terms` i nie tworzy drugiej klasyfikacji D/N/boundary read?
2. Czy dokładnie `D/D/D`, `D/D/N`, `D/N/N` dają po jednej karze na okno, bez innych sekwencji?
3. Czy zakres okien prawidłowo wykorzystuje znane boundary facts z obu stron miesiąca i nie zgaduje brakujących faktów?
4. Czy helper jest wyłącznie SOFT i nie zmienia `NIGHT-STREAK-01`, validatora ani PlanningResult?
5. Czy returned `third_shift_penalty_count` jest poprawnym górnym boundem wpływu kary i został dodany do istniejącej matematycznej ochrony TARGET-01?
6. Czy T034 nie dodaje drugiego solve/fazy i zachowuje istniejący budget/optimization_complete/search_attempt?
7. Czy macierz testów dowodzi rankingu, boundary i vertical wiring bez kopiowania T032/T033?
8. Czy production scope można zamknąć dokładnie w `fairness.py + solver.py`?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.
