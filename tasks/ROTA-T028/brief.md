# ROTA-T028 — automatyczny poligon scenariuszy solvera

Status: **READY FOR IMPLEMENTATION BY A NEW CODEX INSTANCE**

Owner intent: Paweł, 2026-08-24.

Base SHA: `37973b5b054ce43e33ca475151f0424d97bd875c` (`main`, po ROTA-T027).

## 0. Wynik dla właściciela

Powstaje mały lokalny skrypt, który:

1. wymyśla syntetyczny obiekt, obsadę i warunki miesiąca;
2. zna co najmniej jeden poprawny grafik dla przypadków wykonalnych;
3. przekazuje wejście do produkcyjnego `plan()`;
4. sprawdza każdy zwrócony grafik przez produkcyjny `validator.validate()`;
5. przy błędzie zapisuje seed i fakty potrzebne Codexowi do odtworzenia.

To NIE jest benchmark: brak pomiarów czasu, punktów, rankingów i porównań
wersji. Skrypt nie czyta bazy użytkownika, nie używa UI, sieci ani AI.

## 1. Cel i granica

Łańcuch T028:

```text
deterministyczny generator → PlanningState → plan() → validate() → PASS/błąd
```

T028 sprawdza rdzeń solvera. Nie sprawdza SQLite, assemblera, API ani frontu —
te warstwy mają osobne testy pionowe. Nie wolno rozszerzyć T028 o ich obsługę.

T028 nie zmienia `rota/**`, `api/**`, `frontend/**`, `benchmarks/**`, frozen
specs ani istniejących testów. Jeśli implementacja wymaga takiej zmiany,
wykonawca zgłasza blocker zamiast tworzyć connector lub nową warstwę.

## 2. CLI

```text
python -m tools.solver_scenario_lab --cases 25 --seed 20260824
python -m tools.solver_scenario_lab --family <name> --case-seed <seed>
```

Argumenty:

- `--cases`: dodatnia liczba, domyślnie `25`;
- `--seed`: root seed, domyślnie `20260824`;
- `--family` i `--case-seed`: muszą wystąpić razem; uruchamiają dokładnie
  jeden przypadek i służą do replay;
- `--output-dir`: domyślnie `artifacts/solver-scenario-lab`.

Stdout:

- jedna krótka linia dla każdego błędu wraz z komendą replay;
- na końcu dokładnie:
  `CASES=<n> PASS=<n> FAIL=<n> SEED=<seed>`;
- exit `0` dla pełnego PASS, `1` gdy choć jeden przypadek zawiódł;
- błędne argumenty pozostają standardowym błędem argparse.

Zakazane: czasy, percentyle, throughput, score, ranking i słowo „benchmark” w
nazwie wyniku.

## 3. Model przypadku

Wewnętrzny, typowany `GeneratedScenario` zawiera:

- `family`;
- `case_seed`;
- gotowy `PlanningState`;
- `witness` dla przypadku wykonalnego albo `None` dla shortage;
- `expected_status`: tylko `FEASIBLE` albo `DECISION_REQUIRED`;
- `expected_blocking_demand_id`: tylko dla shortage;
- bezpieczne `summary` z syntetycznymi faktami.

Generator:

- używa wyłącznie lokalnego `random.Random(case_seed)`;
- nie używa solvera do budowania witness ani oczekiwania;
- używa wyłącznie aktualnych obiektów domenowych i wspieranych reguł;
- nadaje wszystkim identyfikatorom/nazwom prefiks `LAB-`;
- nie odczytuje plików, bazy, zegara, UUID, sieci ani zmiennych użytkownika.

Ten sam kod, family i case seed muszą tworzyć identyczne `summary`, wejście i
witness. Różny seed musi zmienić realny warunek, nie tylko identyfikator.

## 4. Zamknięte rodziny v1

Generator cyklicznie wybiera pięć rodzin. Pierwsze pięć przypadków obejmuje
każdą dokładnie raz.

### F1 `ordinary_12h_feasible`

- `ORDINARY`, pełny miesiąc zmian D/N 12h;
- 5–9 lokalnych pracowników, obsada 1 albo 2 PRIMARY;
- przy obsadzie 2 generator wybiera co najmniej 7 pracowników, aby sam nie
  tworzył niedoboru godzin;
- co najmniej jedna osoba `day_only`;
- jedna nieobecność przecina pierwotne przypisanie i rzeczywiście wymusza
  legalnego zastępcę;
- rodzaj nieobecności rotuje między `UNAVAILABLE_24H`, `LEAVE_GRANTED` i
  `SICK_LEAVE`.

### F2 `ochrona_12h_boundary_feasible`

- `OCHRONA`, D/N 12h;
- co najmniej jeden REALIZED/frozen Assignment z poprzedniego miesiąca;
- boundary wyklucza pierwotną osobę z pierwszej zmiany;
- witness respektuje odpoczynek dobowy i 35h tygodniowy.

### F3 `ochrona_24h_feasible`

- `OCHRONA`, mieszany profil 12h/24h z wystąpieniami 24h utworzonymi przez
  istniejący katalog; nie używać profilu wyłącznie 24h, w którym obecny kontrakt
  świadomie nie stosuje flagi `can_work_24h`;
- co najmniej jedna osoba ma `can_work_24h=False`;
- istnieje wystarczająca pula osób uprawnionych;
- witness nie używa osoby nieuprawnionej do żadnego wystąpienia 24h.

### F4 `hard_rule_reassignment_feasible`

- jedna aktywna, RESOLVED+HARD reguła faktycznie przecina pierwotne
  przypisanie i wymusza legalnego zastępcę;
- rodzaj rotuje między obecnymi:
  `EMPLOYEE_ALLOWED_SHIFT_KINDS`, `EMPLOYEE_ALLOWED_WEEKDAYS`,
  `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`.

### F5 `night_shortage_decision_required`

- na jednym wskazanym dniu wszyscy pracownicy zdolni do N mają aktywne
  `UNAVAILABLE_24H`;
- jedyna pozostała osoba jest `day_only`;
- zbiór osób uprawnionych do wskazanej N jest konstrukcyjnie pusty;
- pozostałe demands zachowują obsadę;
- oczekiwanie: `DECISION_REQUIRED`, brak kandydatów i wskazany demand w
  `blocking_shift_demands`.

Miesiące rotują przez kształty 28, 29, 30 i 31 dni; 29 oznacza luty
przestępny. Nie dodawać TRAINING/TRAINEE, CLEANING, EXTERNAL_SUPPORT,
wielo-Site ani innych rodzin w T028.

## 5. Oracle i klasyfikacja

### Przypadek wykonalny

Przed `plan()` runner wywołuje `validate(state, witness)`:

- jeżeli witness nie ma `hard_pass=True`: `GENERATOR_ERROR`;
- solver musi zwrócić `FEASIBLE` i 1–3 kandydatów;
- KAŻDY kandydat musi mieć `validate(...).hard_pass=True`;
- kandydat nie musi być identyczny z witness;
- nie wolno wymagać konkretnej osoby ani kolejności, jeśli istnieje wiele
  legalnych rozwiązań.

### Shortage

Runner niezależnie sprawdza zapisany lokalny dowód: dla wskazanego N zbiór
uprawnionych pracowników jest pusty na podstawie membership, day_only i
nieobecności. Jeśli nie jest pusty: `GENERATOR_ERROR`.

Solver musi zwrócić `DECISION_REQUIRED`, zero kandydatów, niepusty payload i
oczekiwany demand w `blocking_shift_demands`.

### Wyniki błędne

- `GENERATOR_ERROR`: generator nie spełnia własnego założenia;
- `SOLVER_MISMATCH`: status/payload nie zgadza się z konstrukcyjnym
  oczekiwaniem albo pojawia się `TECHNICAL_ERROR`;
- `CANDIDATE_INVALID`: liczba kandydatów jest zła lub którykolwiek kandydat
  nie przechodzi walidatora.

Nie tworzyć drugiego solvera ani kopiować całej logiki walidatora. Istniejący
`validator.validate()` jest właścicielem kontroli HARD; lokalny dowód shortage
jest jedynym dodatkowym oraclem v1.

## 6. Failure record i replay

PASS nie zapisuje żadnego pliku.

Każdy błąd zapisuje nowy, nieistniejący wcześniej plik:

```text
<output-dir>/run-<root-seed>/case-<index>-<case-seed>.json
```

Plik zawiera:

- `schema_version=1`;
- build/base SHA;
- root seed, case index/seed i family;
- `summary` syntetycznego scenariusza;
- oczekiwany i rzeczywisty status;
- violations/warnings i bezpieczny opis kandydatów;
- gotową komendę replay.

Nie zapisuje nazwisk, notatek ani danych spoza scenariusza. Istniejącego pliku
nie wolno nadpisać ani usunąć. `artifacts/solver-scenario-lab/` trafia do
`.gitignore`.

Replay regeneruje przypadek z `family + case_seed`. Jest gwarantowany dla tego
samego SHA kodu zapisanego w failure record; przy innym SHA narzędzie pokazuje
ostrzeżenie, ale może uruchomić przypadek ponownie.

## 7. Dozwolone pliki i limit

Nowe:

- `tools/__init__.py`;
- `tools/solver_scenario_lab.py`;
- `tests/test_solver_scenario_lab.py`;
- standardowe delivery pod `tasks/ROTA-T028/round_01/implementation/`.

Modyfikowane:

- `.gitignore` — tylko domyślny katalog artefaktów.

Zakazane: wszystkie inne pliki produktu/testów/benchmarków/specyfikacji.

`tools/solver_scenario_lab.py` maksymalnie 500 linii, test maksymalnie 400.
Brak nowych zależności. Jeżeli zakres nie mieści się w tych granicach,
implementator zgłasza blocker zamiast dodawać moduły i abstrakcje.

## 8. Minimalna macierz T028

T28-01 — CLI odrzuca `cases <= 0` i niepełną parę family/case-seed.

T28-02 — ten sam seed daje identyczne summary/witness; inny zmienia warunek.

T28-03 — pierwsze pięć przypadków obejmuje dokładnie F1–F5.

T28-04 — kształty 28/29/30/31, w tym luty przestępny.

T28-05 — witness każdej rodziny wykonalnej przechodzi walidator przed PLAN.

T28-06 — F1: trzy rodzaje nieobecności rzeczywiście przecinają pierwotne
przypisanie i końcowy kandydat ich nie narusza.

T28-07 — F2: boundary zmienia pierwszą dopuszczalną osobę; kandydaci przechodzą
reguły ochrony.

T28-08 — F3: osoba `can_work_24h=False` nie obsadza 24h.

T28-09 — F4: każda z trzech reguł jest aktywna i wymusza zmianę przypisania.

T28-10 — F5: lokalny proof ma pusty eligible set, a solver zwraca oczekiwany
blocking demand.

T28-11 — podstawiony kandydat bez jednego PRIMARY daje `CANDIDATE_INVALID`;
runner nie ufa samemu statusowi `FEASIBLE`.

T28-12 — podstawiony zły status daje `SOLVER_MISMATCH`.

T28-13 — błąd zapisuje JSON i komendę replay; PASS nie zapisuje pliku;
istniejący plik nie jest nadpisywany.

T28-14 — replay odtwarza family/case seed; ten sam SHA daje to samo summary.

T28-15 — test zakresu: brak importu `benchmarks`, brak metryk czasu i brak
zmian poza §7.

T28-16 — pełna regresja repozytorium. Znany stary test source-diff T023 nie
należy do T028 i nie może być „naprawiany” w tym Tasku.

## 9. Warunki odbioru

PASS wymaga:

- T28-01…T28-16;
- realnego CLI `--cases 5` obejmującego F1–F5;
- co najmniej jednego niezależnego mutanta invalid-candidate odrzuconego przez
  poligon;
- braku zmian poza §7;
- braku benchmarkowych metryk i importów;
- exact SHA, raw `backend.py` stdout i diff względem base SHA w DELIVERY.

## 10. Polecenie dla nowej instancji Codexa

Przeczytaj `AGENTS.md` i cały brief. W tym Tasku jesteś implementatorem.
Zaimplementuj dokładnie F1–F5 i T28-01…T28-16. Nie dodawaj rodzin, bazy, UI,
API, benchmarku ani poprawki solvera.

Jeśli poligon znajdzie błąd solvera, zachowaj failure JSON i zgłoś go — nie
naprawiaj go w T028. Jeśli brakuje wspieranego publicznego modelu potrzebnego
do F1–F5, wskaż dokładny blocker zamiast zmieniać `rota/**`.
