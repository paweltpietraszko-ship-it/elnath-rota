# ROTA-REAL-OBJECT-01 — benchmark realnego obiektu przeciwko production code

Status: architect-authored test infrastructure — **R2 po audycie Codex R1, oczekuje na re-audyt**  
Production base used by the benchmark: `e010f004e90a1e4f426bb72298e7307045d32b56`

## Cel

Ten benchmark nie jest następcą w znaczeniu technicznym dla `rota_stress.py`.
`rota_stress.py` pozostaje syntetycznym generatorem z góry wykonalnych problemów.
ROTA-REAL-OBJECT-01 odpowiada na inne pytanie: co robi aktualny PlanningEngine,
gdy lokalny roster pozostaje realnym pięcioosobowym obiektem i dokładamy
kontrolowane warunki brzegowe.

## Nienaruszalny roster

Każdy przypadek operacyjny ma dokładnie pięciu LOCAL:

- A
- B
- C — `DAY_ONLY`
- D
- E

X i Y są odrębnymi `EXTERNAL_SUPPORT`. Nie są ukrytą szóstą/siódmą osobą.
Bez pasującego aktywnego `ExternalSupportWindow` nie mogą zostać użyci.

Podstawowa geometria obiektu:

- 1× PRIMARY D dziennie, 05:00–17:00;
- 1× PRIMARY N dziennie, 17:00–05:00;
- REST-01 = 11 h;
- LOAD-01 = maks. 60 h w dowolnym ruchomym 7-dniowym oknie przed
  `DECISION_REQUIRED`;
- sześć dni predecessor context przed miesiącem.

## Fail-closed benchmark input

`real_object_input.py` waliduje każdy fixture **przed** reference oracle i
przed wywołaniem production `plan()`.

Nielegalny fixture nie może być użyty do oceny solvera. Walidowane są m.in.:

- employee ids i rodzaje availability/rules;
- dodatnie przedziały;
- duplicate ids;
- DAY_ONLY w fixed/boundary facts;
- same-demand fixed conflicts;
- REST/overlap pomiędzy boundary i nienegocjowalnymi existing assignments;
- pełna sześciodniowa historia w przypadkach drabiny wymagających tego dowodu.

Semantycznie niepasujące okno X/Y (wrong Site, inactive, partial interval,
wrong shift kind, disabled profile) jest **legalnym wejściem testowym**, ale
nie może odblokować external eligibility.

## Niezależny oracle i checker witnessów

`real_object_oracle.py` buduje własny CP-SAT existence model. Nie importuje ani
nie wywołuje produkcyjnego PlanningEngine, solvera, eligibility builderów,
constraint builderów ani validatora.

Każdy FEASIBLE witness oracle jest następnie sprawdzany przez
`real_object_checker.py`. Witness z COVERAGE/REST/LOAD/eligibility błędem
zostaje `UNKNOWN/WITNESS_CHECK_FAILED` i nie może służyć jako dowód przeciwko
production.

Klasy reference:

- `KNOWN_FEASIBLE`
- `LOAD_DECISION_REQUIRED`
- `EXTERNAL_SUPPORT_DECISION_REQUIRED`
- `KNOWN_FEASIBLE_WITH_CONFIRMED_EXTERNAL_SUPPORT`
- `PROVEN_STAFFING_SHORTAGE`
- `INCONCLUSIVE`

`UNKNOWN` nigdy nie jest PASS-em.

## Certyfikaty DECISION_REQUIRED

Sam status `DECISION_REQUIRED` nie wystarcza.

Dla shortage/external runner niezależnie wyznacza demands, które mają zero
eligible employees, oraz przyczyny per employee. Payload production musi
wskazać prawdziwy demand i blocker zgodny z tym evidence.

Dla X/Y benchmark dodatkowo wyznacza parę `(demand, external employee)`, która
jest zablokowana w current state przez `EXTERNAL-01`, ale staje się eligible
po jawnie zadanym probe window.

Dla LOAD-01 runner nie ufa samemu `LoadBlocker`. Osobny niezależny solve
`verify_load_claim()` musi dowieść, że dokładnie zgłoszone
`employee/window/hours` da się uzyskać w legalnym uncapped grafiku, podczas gdy
reference capped pozostaje INFEASIBLE.

## Obowiązkowa drabina 1–14

Core matrix obejmuje wszystkie wymagane klasy:

1. literalny ROTA-REG-001;
2. miesiące 28/29/30/31 dni i różne weekday starts;
3. poprawną sześciodniową historię z N kończącą się w dniu 1;
4. PLAN i REPLAN z REALIZED/frozen/redistributable baseline;
5. narastające absencje;
6. osobno brak C oraz brak flexible worker;
7. trudne przetasowanie nadal możliwe <=60 h;
8. przypadek możliwy dopiero >60 h;
9. prosty brak eligible employee dla konkretnej zmiany;
10. REST dokładnie 11 h i poniżej 11 h;
11. LOAD dokładnie 60 h i >60 h na boundary;
12. month-end N kontra znany next-month D;
13. X/Y before/after coordinator window;
14. negative ExternalSupportWindow matrix: employee/Site/active/interval/kind/profile.

Absence ladder ma jawne `series_id/series_level`; raport wskazuje pierwszy poziom,
na którym reference przestaje być `KNOWN_FEASIBLE`.

## Reprodukcja

Każdy case zawiera w raporcie:

- `case_id`;
- stały `seed`;
- SHA-256 `input_fingerprint` pełnego wejścia;
- miesiąc;
- numery ladder steps;
- pełną listę perturbacji;
- A–E + C=DAY_ONLY;
- memberships X/Y oraz wszystkie current/probe windows;
- boundary/fixed assignments;
- reference class;
- capped/uncapped/probe solves z witnessami i checker errors;
- production status, blockers, load blocker, unblocking options i czas;
- independent candidate/certificate evidence.

Czasy nie są częścią deterministic correctness identity. Ten sam
`case_id + seed` musi jednak odtwarzać identyczny input fingerprint, reference
class i deterministic oracle witness przy jednym workerze CP-SAT.

## Correctness vs performance

Raport rozdziela:

- `correctness` — zgodność production z niezależnym oracle/checker;
- `performance` — mean/p50/p95/max oraz reference/production timeout counts
  osobno per reference class.

Brak SLA oznacza, że wolny poprawny wynik nie jest automatycznie błędem
merytorycznym.

## Uruchomienie

Core:

```bash
python -m benchmarks.real_object --suite core
```

Pełna macierz + 24-month calendar sweep:

```bash
python -m benchmarks.real_object --suite all
```

Exact replay:

```bash
python -m benchmarks.real_object --suite all \
  --case external-before-confirmation --seed 13001
```

Audit JSON:

```bash
python -m benchmarks.real_object --suite all --json real_object_all.json
```

Self-tests benchmarku:

```bash
pytest -q tests/test_real_object_benchmark.py
```

## Zasada audytu

Jeżeli R2 zwróci czerwony przypadek przeciwko PlanningEngine, nie wolno:

- zwiększyć lokalnego rosteru;
- dopisać ukrytej rezerwy;
- otworzyć X/Y bez jawnego window;
- zmienić oczekiwanej klasy po zobaczeniu production result;
- osłabić HARD tylko po to, aby odzyskać zielony raport.

Najpierw należy rozstrzygnąć, czy czerwony przypadek jest błędem benchmarku,
czy produkcyjnego PlanningEngine. Nie naprawiać obu w tym samym commicie.

## Status po audycie R1

SHA `54d3bb9` **nie jest zaakceptowany**. Codex R1 wykazał 7 klas błędów
benchmarku i nie wydał findingu przeciwko PlanningEngine.

R2 naprawia te klasy, ale sam dokument nie deklaruje PASS. Nowy exact SHA ma
zostać uruchomiony i ponownie zaatakowany przez Codexa.
