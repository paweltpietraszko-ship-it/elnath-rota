# ROTA-THIRD-CONSECUTIVE-SHIFT-ORDINARY-SCOPE — THIRD-CONSECUTIVE-SHIFT-01 tylko dla OCHRONA

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

BASE_MAIN_SHA: `91907bc39c0b6f8d83b5e05b724e8eac36e24067`
SOURCE_FINDING: `BOARD.md` / `ROTA-THIRD-CONSECUTIVE-SHIFT-ORDINARY-SCOPE`
PARENT_CONTRACT: `tasks/ROTA-T058/brief.md`
OWNER_RULING: dla ORDINARY jedynymi HARD ograniczeniami rytmu pracy mają być obowiązujące limity prawne, w szczególności REST-01/WEEKLY-REST-01; system nie ma nakładać ochroniarskiego zakazu trzeciego dnia pracy z rzędu.

## 1. Cel

Zawęzić istniejącą regułę `THIRD-CONSECUTIVE-SHIFT-01` z T058 do `SitePlanningRegime.OCHRONA`.

Nie zmieniamy samej semantyki T058 dla OCHRONA. Zmieniamy wyłącznie jej zakres reżimowy.

## 2. PRODUCT_TRUTH

### 2.1 OCHRONA

Dla OCHRONA pozostaje dokładnie dotychczasowy kontrakt T058:
- automat nie może dołożyć nowej trzeciej kolejnej PRIMARY służby na trzech kolejnych datach rozpoczęcia;
- boundary/fixed/historyczne fakty uczestniczą zgodnie z T058;
- ręczna korekta może świadomie zapisać naruszenie przez istniejący Deviation/action trail;
- `THIRD_CONSECUTIVE_SHIFT_BLOCKED` pozostaje prawidłowym publicznym wynikiem automatycznego planowania.

### 2.2 ORDINARY

Dla ORDINARY `THIRD-CONSECUTIVE-SHIFT-01` NIE obowiązuje.

To oznacza:
- solver może legalnie zaplanować trzy lub więcej kolejnych dni PRIMARY, jeżeli wszystkie inne HARD są spełnione;
- validator nie zgłasza `THIRD-CONSECUTIVE-SHIFT-01` dla ORDINARY;
- brak `THIRD_CONSECUTIVE_SHIFT_BLOCKED` jako wyniku wynikającego wyłącznie z tej reguły;
- nie powstaje Deviation tej reguły dla ręcznej korekty ORDINARY;
- REST-01, WEEKLY-REST-01, LOAD-01, availability, membership, role gates i inne niezależne HARD pozostają bez zmian.

Nie interpretować tego jako „ORDINARY nie ma ograniczeń”. Znika tylko biznesowa reguła T058.

## 3. Architektura

Reżim Site jest jedynym gate'em zakresu tej reguły.

Wzorzec ma być analogiczny do już istniejących reguł ograniczonych do OCHRONA, np. `SHIFT-24-01`/kwalifikacji 24h: jedna domena planowania, jeden solver i jeden validator, lecz dana reguła wykonuje się tylko dla właściwego reżimu.

Zakazane:
- drugi solver dla ORDINARY;
- globalne wyłączenie T058;
- heurystyczne rozpoznawanie handlu po godzinach zmian;
- wyjątek per employee/SiteRule;
- nowy toggle konfiguracyjny w UI;
- osłabianie REST/WEEKLY-REST/LOAD.

## 4. Miejsca wymagające spójnej zmiany

Aktualny trace wskazuje dwa niezależne enforcement points bez regime gate:

1. CP-SAT: `rota/planning/constraints.py::add_max_two_consecutive_primary_shift_constraint`, wywoływany z `rota/planning/solver.py`;
2. validator: `rota/planning/validator_checks_patterns.py::_check_third_consecutive_shift`.

Oba muszą używać tej samej jawnej przesłanki `planning_regime == OCHRONA` przekazanej istniejącym state/contextem. Nie wolno naprawić tylko solvera albo tylko validatora.

Jeżeli aktualny kształt funkcji nie ma regime w argumentach, wolno wykonać najmniejszą zmianę sygnatury/state potrzebną do przekazania już istniejącej informacji o Site. Nie tworzyć nowego globalnego lookupu DB wewnątrz constraints/validatora.

## 5. Relacja do T058

Ten Task superseduje T058 wyłącznie w jednym punkcie: zakres reżimowy `THIRD-CONSECUTIVE-SHIFT-01`.

Wszystkie pozostałe ustalenia T058 dla OCHRONA zostają zachowane, w tym:
- definicja kolejnych dat rozpoczęcia;
- PRIMARY-only;
- TRAINEE/S1 exclusion;
- boundary/fixed behavior;
- ręczna korekta i freeze decyzji;
- brak coordinator override automatu;
- brak nowej blokady PDF;
- brak zmian objective/fairness.

## 6. Acceptance

TCSO-01 — OCHRONA: istniejący reprezentatywny scenariusz trzeciej kolejnej służby nadal jest blokowany przez solver.

TCSO-02 — OCHRONA: validator nadal zgłasza `THIRD-CONSECUTIVE-SHIFT-01` dla tego samego naruszenia.

TCSO-03 — ORDINARY: trzy kolejne PRIMARY dni nie są blokowane ani przez solver, ani przez validator wyłącznie z powodu T058.

TCSO-04 — ORDINARY: jeżeli ten sam scenariusz łamie niezależny REST/WEEKLY-REST/LOAD/availability, odpowiednia niezależna reguła nadal działa; test nie może dowodzić PASS przez przypadkowe usunięcie innych HARD.

TCSO-05 — ORDINARY: ręczna korekta trzech kolejnych dni nie materializuje Deviation `THIRD-CONSECUTIVE-SHIFT-01`.

TCSO-06 — OCHRONA: istniejące boundary/fixed i ręczne-deviation zachowanie T058 bez regresji.

TCSO-07 — żadnego nowego ustawienia/toggle/UI dla tej reguły.

TCSO-08 — status `THIRD_CONSECUTIVE_SHIFT_BLOCKED` nie pojawia się w ORDINARY, jeżeli jedynym potencjalnym blockerem byłby T058.

## 7. Minimalne testy

Backend:
- solver OCHRONA — istniejący blocker nadal aktywny;
- validator OCHRONA — istniejący finding nadal aktywny;
- solver ORDINARY — 3 consecutive feasible przy spełnieniu innych HARD;
- validator ORDINARY — brak T058 finding dla identycznego układu;
- regresja ręcznej korekty/freeze dla OCHRONA;
- izolacja od REST/WEEKLY-REST/LOAD.

Nie wymaga nowego E2E frontendu, jeżeli publiczny status/API nie zmienia kształtu.

## 8. WHERE_MAP

WHERE_MAP: REQUIRED
- `tasks/ROTA-T058/brief.md` — read-only parent contract.
- `rota/planning/constraints.py` :: `add_max_two_consecutive_primary_shift_constraint`.
- `rota/planning/solver.py` :: call site / dostęp do `SitePlanningRegime`.
- `rota/planning/validator_checks_patterns.py` :: `_check_third_consecutive_shift`.
- `rota/planning/validator.py` lub istniejący validator context — wyłącznie jeśli potrzebne do przekazania regime.
- `rota/planning/state.py` / `engine_types.py` — tylko jeśli regime nie jest już dostępny w istniejącym context; nie tworzyć drugiego state.
- `tests/test_t058.py` i właściwe istniejące testy T058.
- nowy `tests/test_third_consecutive_shift_regime_scope.py` lub równoważny wąski plik.

## 9. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-THIRD-CONSECUTIVE-SHIFT-ORDINARY-SCOPE/**`
- `rota/planning/constraints.py`
- `rota/planning/solver.py`
- `rota/planning/validator_checks_patterns.py`
- `rota/planning/validator.py`
- `rota/planning/state.py`
- `rota/planning/engine_types.py`
- `tests/test_t058.py`
- `tests/test_third_consecutive_shift_regime_scope.py`

Jeśli implementer potrzebuje innej ścieżki produkcyjnej, STOP i pytanie do architekta przed zmianą.

## 10. Preimplementation audit Codexa

Codex ma sfalsyfikować przede wszystkim:
1. czy regime gate jest potrzebny w obu niezależnych enforcement points;
2. czy istniejący context już niesie `planning_regime`, bez rozszerzania architektury;
3. czy wyłączenie w ORDINARY nie osłabia żadnego prawnego HARD;
4. czy acceptance izoluje T058 od REST/WEEKLY-REST/LOAD;
5. czy TASK_SCOPE wystarcza bez zmian API/UI/persistence.

IMPLEMENTATION HOLD do PASS preimplementation na dokładnym SHA tego briefu.
