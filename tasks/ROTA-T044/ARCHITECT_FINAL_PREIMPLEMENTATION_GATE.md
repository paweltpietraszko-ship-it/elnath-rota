# ROTA-T044 — finalne zamknięcie preimplementation gate przez architekta

Status: **PASS — READY_FOR_IMPLEMENTATION**

Data: 2026-08-31
Branch: `task/ROTA-T044`
Audytowany exact HEAD przed tym wpisem: `b09b1146fc15e6ef89ff98ee725f087e786a3764`

## 1. Źródła wiążące

Finalny kontrakt implementacyjny T044 składa się z:

- `tasks/ROTA-T044/brief.md` @ `b8fccffa4591fe979fae09a6915a35f161566e12`;
- `tasks/ROTA-T044/TASK_CHATGPT.md` @ `bccdc5876df42e83781d735012d8d2dcb8242d83`;
- `tasks/ROTA-T044/TASK_CHATGPT_CORRECTION_R1.md` @ `6334c6425172e4985ce73957b5c5df929232228b`;
- `tasks/ROTA-T044/TASK_CHATGPT_CORRECTION_R2.md` @ `bb060e68b58a8300d1b6d8b42ede59d169b2b6a1`.

Ślad niezależnych gate'ów:

- `tests_r6.txt` — PASS R8 kalkulatora warstwowego 5/10/9;
- `tests_r7.txt` — FAIL niewykonalnej macierzy urlopów;
- `tests_r8.txt` — PASS korekty R1;
- `cc_devils_advocate_r1.txt` — jeden BLOCKER lifecycle absencji + jeden NON_BLOCKING kontrprzykład zawyżenia kalkulatora;
- `tests_r9.txt` @ `b09b1146fc15e6ef89ff98ee725f087e786a3764` — PASS obu korekt z rundy adwokata diabła.

## 2. Werdykt architekta

**PASS — READY_FOR_IMPLEMENTATION.**

Nie ma otwartej decyzji OWNERA ani nierozstrzygniętego blockera kontraktowego.

T044 może przejść do implementacji wyłącznie zgodnie z połączonym kontraktem powyżej. Ten werdykt nie jest zgodą na rozszerzenie produktu, zmianę Wariantu A ani zmianę TASK_SCOPE.

## 3. Zamrożone granice implementacji

### 3.1 Symulator B bada produkt, nie poprawia solvera

- Wariant B automatyzuje działania koordynatora przez istniejące API.
- Zły, dziwny albo niesprawiedliwy wynik solvera jest wynikiem badania/reproduktorem.
- Harness nie poprawia danych po PLAN/REPLAN, nie szuka lepszego grafiku i nie buduje drugiego solvera, validatora, fairness evaluatora ani kwartalnego oracle.
- Jedyna własna odpowiedzialność obliczeniowa Symulatora B to kalkulator liczby LOCAL przed pierwszym PLAN.

### 3.2 Kalkulator obsady

Kanoniczny wzór po korekcie R2:

```text
liczba_LOCAL = max_m(
    sum_k(
        ceil(layer_hours(k, m) / nominal_monthly_hours_kp(m, POLISH_2026_HOLIDAYS))
    )
)
```

Czyli:

1. dla każdego realnego miesiąca 2026 licz wszystkie warstwy dla tego samego miesiąca;
2. zsumuj headcount warstw tego miesiąca;
3. dopiero potem wybierz maksimum z 12 miesięcy.

Nie wolno wrócić do `sum_k(max_m(...))`, bo sztucznie łączy szczyty z różnych miesięcy.

Obowiązkowe oracle przed podłączeniem do Hypothesis:

- pełna warstwa req=1 → **5**;
- pełne req=2 → **10**;
- robocze=2/weekend=1 → **9**;
- kontrprzykład z `cc_devils_advocate_r1.txt` → **4**, nie 5.

Kalkulator pozostaje prostą arytmetyką `sum/ceil/max`; nie tworzy Assignmentów, nie wybiera ludzi i nie zna wyniku solvera.

### 3.3 Urlop i L4 — initial setup only

Absencje generowane przez Wariant B są zamrażane i zapisywane **dokładnie raz, przed pierwszym PLAN badanego obiektu**.

- `1 LOCAL` → jeden planowy urlop 10 dni roboczych;
- `>=2 LOCAL` → dokładnie dwa planowe bloki: 10 dni + 5 dni roboczych dla dwóch różnych LOCAL, bez nakładania;
- pozostali LOCAL nie dostają kolejnych planowych bloków urlopu w tym obiekcie;
- ewentualne L4: jeden blok 5 dni, losowanie ~25%, dokładnie raz na obiekt, LOCAL-only;
- po pierwszym PLAN nie istnieje transition tworzący, rozszerzający, przesuwający ani ponownie losujący urlop/L4;
- REPLAN ani przejście na kolejny miesiąc nie dopisują absencji.

Nie zmieniać `RetroactiveAbsenceRejected` ani `api/errors.py` w T044. Nieoczekiwany non-2xx przy prawidłowym initial setup trafia do istniejącego structured failure/reproducer path; harness nie zmienia danych, żeby ominąć błąd.

### 3.4 Generator i Hypothesis

- `required_primary_count` pozostaje per wiersz/dzień w `{1,2}`;
- legalne overlap'y katalogu pozostają legalne;
- odrzucany przed API jest wyłącznie wzór z zerowym pokryciem;
- Hypothesis stateful używa prawdziwego backendu, świeżej SQLite `:memory:` i nowego Site per przykład;
- `database=None`, `deadline=None`, `derandomize=False`;
- liczby profilu default/FULL wynikają z realnego pomiaru, nie są zgadywane;
- FULL jest opt-in przez `ROTA_SIM_VARIANT_B_FULL=1`;
- pierwszy PLAN ma wyłącznie LOCAL;
- EXTERNAL powstaje dopiero po realnym, niepustym `DECISION_REQUIRED`, według zamrożonego decision-link ordering i limitu z kontraktu;
- nie dodawać reaktywnie LOCAL.

## 4. TASK_SCOPE — bez rozszerzenia

Dozwolony zakres implementacji pozostaje:

- `tests/property/coordinator_simulator.py` — wyłącznie nowe addytywne helpery Wariantu B; istniejący Wariant A nietknięty;
- `tests/property/test_coordinator_simulator_variant_b.py`;
- `pyproject.toml` — wyłącznie zależność `hypothesis`;
- `tasks/ROTA-T044/round_01/tests/**` — testy, pomiary, reproduktory i raporty;
- dokumenty T044 wyłącznie jako ślad procesu, nie jako miejsce zmiany zachowania podczas implementacji.

Zabronione bez STOP i nowego gate'u:

- `rota/**`;
- `api/**`;
- `frontend/src/**`;
- `benchmarks/**`;
- zmiana istniejącego Wariantu A;
- nowy endpoint/model/response produktu;
- Cross-Site;
- UI/Playwright;
- zewnętrzny evaluator/model;
- drugi solver/validator/evaluator.

## 5. WHERE_MAP — obowiązkowy przed kodowaniem

Przed implementacją na exact HEAD implementer wykonuje:

```text
python where.py tests/property/coordinator_simulator.py
```

Po dodaniu faktycznie nowych/współdzielonych symboli Wariantu B wykonuje również `where.py ... --symbol <NAME>` dla tych ownerów/seamów zgodnie z `AGENTS.md`.

Raw output jest mapą tropów, nie werdyktem. Jeżeli pokaże konieczność zmiany produktu albo Wariantu A, implementer zatrzymuje się przed kodowaniem poza TASK_SCOPE.

## 6. Kolejność implementacji

Implementacja może rozpocząć się po tym gate'cie, ale zachowuje checkpointy z Tasku:

1. **A — kalkulator + generator:** oracle `5/10/9/4`, mixed `required_primary_count`, legal overlap, zero-coverage only.
2. **B — działania koordynatora:** initial setup absencji, prawdziwe API, PLAN, EXTERNAL po decyzji, select/REPLAN według preconditions, CLOSED WORLD, reproduktor.
3. **C — Hypothesis + koszt:** state machine, ustawienia Hypothesis, pomiar profilu, default/FULL, celowana regresja Wariantu A.

Nie uruchamiać pełnej regresji repo bez osobnej zgody OWNERA.

## 7. Gate po implementacji

Po implementacji nie ma automatycznego PASS tylko dlatego, że testy implementera są zielone.

Wymagany jest kolejny niezależny audyt implementacji na exact SHA, zgodnie z `AGENTS.md`:

- sprawdzenie `WHERE_MAP` dla faktycznie nowych ownerów;
- testy `5/10/9/4`;
- realny pion API Wariantu B;
- lifecycle absencji initial-setup-only;
- EXTERNAL/decision-link ordering;
- HEADCOUNT/CLOSED WORLD;
- reprodukcja realnej zmienności i zapisany pomiar profilu;
- regresja Wariantu A w zakresie wymaganym kontraktem;
- klasyfikacja wszystkich czerwonych wyników solvera jako wyników badania, a nie automatycznych błędów harnessu.

Dopiero po niezależnym audycie implementacji architekt wydaje finalną ocenę dostarczenia.

---

**ARCHITECT FINAL PREIMPLEMENTATION VERDICT: PASS — READY_FOR_IMPLEMENTATION.**
