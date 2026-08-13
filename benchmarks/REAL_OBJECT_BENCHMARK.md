# ROTA-REAL-OBJECT-01 — benchmark realnego obiektu przeciwko production code

Status: architect-authored test infrastructure — **R3 candidate after Codex R2 FAIL**
Production base used by the benchmark: `e010f004e90a1e4f426bb72298e7307045d32b56`

## Cel

ROTA-REAL-OBJECT-01 nie zastępuje technicznie `rota_stress.py`. Tamten plik
pozostaje syntetycznym generatorem z góry wykonalnych problemów. Ten benchmark
sprawdza aktualny PlanningEngine na realnym pięcioosobowym rdzeniu obiektu oraz
kontrolowanych warunkach brzegowych.

## Nienaruszalny model

Lokalny roster to zawsze dokładnie A–E, przy czym C jest `DAY_ONLY`.
X i Y są wyłącznie `EXTERNAL_SUPPORT`; nie są ukrytą szóstą i siódmą osobą.

Target Site używa:

- D 05:00–17:00;
- N 17:00–05:00;
- jednej PRIMARY D i jednej PRIMARY N dziennie;
- REST-01 = 11 h;
- LOAD-01 = 60 h / ruchome 7 dni przed `DECISION_REQUIRED`.

Target-site boundary/fixed facts muszą mieć legalną geometrię D/N. Kontekst
`other_site_assignments` jest jawnie odrębny: reprezentuje pracę pracownika na
innym obiekcie i może mieć inną geometrię zmian, ale nadal podlega REST/LOAD.
To pozwala uczciwie testować granicę dokładnie 11 h bez wymyślania lokalnej
zmiany 06:00–18:00.

## Fail-closed wejścia

`real_object_input.py` uruchamia się przed oracle i przed production `plan()`.
Nielegalny fixture nie może służyć do oceny solvera.

Walidowane są m.in.:

- employee ids, availability, SiteRules i ExternalSupportWindow;
- dodatnie przedziały;
- globalna unikalność assignment_id między boundary/fixed/cross-site context;
- legalna geometria lokalnych target-site facts;
- operatywny stan fixed facts — `CANCELLED` nie udaje historii pracy;
- DAY_ONLY dla target Site;
- same-version fixed demand references;
- REST/overlap między wszystkimi fixed/context facts;
- dokładnie jedna REALIZED D i N na każdym z sześciu predecessor days,
  gdy scenariusz wymaga ladder step 3.

## Niezależny oracle i checker

`real_object_oracle.py` buduje własny CP-SAT existence model i nie importuje
produkcyjnego solvera/eligibility/validatora. Uwzględnia target-site boundary
oraz jawny cross-site context dla REST i LOAD.

Każdy FEASIBLE witness oracle jest ponownie sprawdzany przez
`real_object_checker.py`. Witness z błędem COVERAGE, eligibility, REST lub LOAD
staje się `UNKNOWN/WITNESS_CHECK_FAILED` i nie jest dowodem przeciw produkcji.

Reference classes:

- `KNOWN_FEASIBLE`;
- `LOAD_DECISION_REQUIRED`;
- `EXTERNAL_SUPPORT_DECISION_REQUIRED`;
- `KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT`;
- `PROVEN_STAFFING_SHORTAGE`;
- `INCONCLUSIVE`.

`UNKNOWN` nigdy nie jest PASS-em.

## DECISION_REQUIRED — pełny certyfikat

R3 nie stosuje zasady „wystarczy jeden poprawny element”.
`real_object_decisions.py` sprawdza każdy zgłoszony element payloadu:

- każdy `blocking_shift_demand` musi istnieć i mieć dokładny przedział;
- każdy blocker employee/condition musi mieć niezależne evidence;
- dodatkowy fikcyjny blocker jest FAIL-em nawet obok poprawnego;
- wymagana klasa unblocking option musi istnieć;
- niepowiązana opcja jest FAIL-em;
- nie-LOAD decision nie może przemycić `load_blocker`.

Dla LOAD dokładny `employee/window/hours` jest ponownie dowodzony przez osobny
uncapped solve `verify_load_claim()`.

Dla prostego shortage checker używa dowodu zero individually eligible.
Dla konfliktów zbiorowych buduje osobny uncapped CP-SAT dla zgłoszonego zbioru
blocking demands i potwierdza coverage + eligibility + REST. Dzięki temu para
zmian, które osobno może wykonać A, lecz razem łamie REST, może zostać
pozytywnie certyfikowana bez udawania indywidualnego shortage.

## External support condition

Publicznym condition dla niemożności użycia X/Y jest `EXTERNAL-01`, również
gdy wewnętrzną przyczyną jest `SiteProfile.external_support_enabled=false`.
Szczegół `EXTERNAL_SUPPORT_DISABLED` może pozostać diagnostyką wewnętrzną, ale
nie stanowi drugiej publicznej taksonomii blockera. Rozstrzygnięcie zapisano w:

`arch/BENCHMARK_REAL_OBJECT_R3_CONDITION_CLARIFICATION_2026-08-13.md`.

Wyłączony profil nie staje się przez to odblokowywalny oknem X/Y. Taki case
pozostaje shortage; zmienia się wyłącznie kanoniczny kod provenance.

## Drabina 1–14

Core matrix obejmuje:

1. literalny ROTA-REG-001;
2. miesiące 28/29/30/31 dni;
3. poprawną sześciodniową historię;
4. PLAN i REPLAN z REALIZED/frozen/redistributable baseline;
5. monotonicznie narastające absencje;
6. osobno brak C i brak flexible worker;
7. trudne przetasowanie nadal <=60 h;
8. coverage możliwe dopiero >60 h;
9. prosty brak eligible employee;
10. REST dokładnie 11 h i poniżej 11 h przez cross-site context;
11. LOAD dokładnie 60 h i >60 h na boundary;
12. month-end N kontra znany next-month D;
13. X/Y before/after jawnego window;
14. negatywną macierz employee/Site/active/interval/kind/profile.

Absence ladder jest inkluzywna: fakty poziomu N są podzbiorem poziomu N+1.
Runner sam sprawdza tę własność i ustawia `benchmark_errors`, więc sama zgodna
metadata `series_level` nie wystarcza.

## Reprodukcja i raport

Każdy case zapisuje m.in.:

- `case_id` i stały `seed`;
- SHA-256 `input_fingerprint`;
- pełny scenario z perturbacjami, windows i context assignments;
- reference capped/uncapped/probe solves oraz witness checker evidence;
- production status, każdy blocker, load blocker, unblocking options i czas;
- independent candidate/decision certificate evidence.

JSON jest serializowalny bez utraty dat/enums. Exact replay wymaga zgodnego
`case_id + seed`. Czasy nie należą do deterministic correctness identity.

## Correctness i performance

Raport rozdziela:

- `correctness` — oracle/checker kontra production;
- `performance` — mean/p50/p95/max i timeout counts per reference class.

Brak zatwierdzonego SLA oznacza, że wolny poprawny wynik nie jest automatycznie
błędem merytorycznym.

## Uruchomienie

```bash
pytest -q tests/test_real_object_benchmark.py tests/test_real_object_benchmark_r3.py
python -m benchmarks.real_object --suite core --json real_object_core_r3.json
python -m benchmarks.real_object --suite calendar --json real_object_calendar_r3.json
python -m benchmarks.real_object --suite all --json real_object_all_r3.json
python -m benchmarks.real_object --suite all --case external-before-confirmation --seed 13001
```

## Zasada audytu

R3 nadal nie deklaruje własnego PASS. Codex ma najpierw zaatakować benchmark.
Jeżeli infrastruktura przejdzie audyt, a prawidłowo certyfikowany case pozostaje
czerwony, dopiero wtedy wolno utworzyć osobny finding przeciw PlanningEngine.
Benchmark branch nie zmienia `rota/`.
