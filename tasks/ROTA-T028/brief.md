# ROTA-T028 — poligon scenariuszy koordynatora i solvera

Status: **READY FOR IMPLEMENTATION BY A NEW CODEX INSTANCE**

Owner intent: Paweł, 2026-08-24.

Base SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5` (`main`, po T029/T030).

Korekta granicy 2026-08-24: poprzedni brief błędnie zabraniał SQLite i
assemblera. Zmuszało to generator do ręcznego budowania `PlanningState` oraz
kopiowania skutków decyzji koordynatora. Ten kontrakt zastępuje tamten model.
Zatwierdzona granica: tymczasowa baza + produkcyjne operacje backendowe, bez
przeglądarki, sieci i danych użytkownika.

TASK_SCOPE:
- tasks/ROTA-T028/brief.md
- tools/solver_scenario_lab.py
- tests/test_solver_scenario_lab.py
- .gitignore

Owner amendment `OWNER_ACCEPTED`, 2026-08-24:

- warianty Obiektu to: 12h `1x5`, 12h `2x10`, 24h `1x4`, 24h `1x5`,
  24h `2x8` i 24h `2x10`; liczba LOCAL nie zmienia się z długością miesiąca;
- każdy przypadek od początku deklaruje dokładnie jedną syntetyczną osobę
  `LAB-EXTERNAL-*`, bez target hours i bez okna wsparcia;
- najpierw planuje wyłącznie własna załoga. Okno wsparcia wolno zapisać przez
  `add_external_support_window()` tylko po rzeczywistej produkcyjnej propozycji
  wsparcia, po czym runner ponawia planowanie;
- urlop: zero albo jedna osoba LOCAL, 14 dni kalendarzowych; chorobowe: 0-21
  dni, pracownik i ewentualne nałożenie z urlopem wynikają z seeda;
- generator zapisuje tylko decyzje i daty. Backend pozostaje jedynym
  właścicielem wyliczenia godzin i skutków nieobecności;
- `target_hours=168` jest jawną decyzją wejściową koordynatora dla każdego
  LOCAL, a nie wartością wyliczaną przez generator;
- po zmianie wejść dotyczących wybranego grafiku runner używa produkcyjnego
  `replan()`;
- zarówno `FEASIBLE`, jak i kompletne `DECISION_REQUIRED` są wartościowym
  wynikiem poligonu. Błędem są `TECHNICAL_ERROR`, niepoprawny kandydat,
  niespójny payload albo naruszenie świata zamkniętego.

## 1. Wynik dla właściciela

Powstaje lokalny skrypt, który dla każdego syntetycznego przypadku:

1. otwiera nową, pustą bazę SQLite `:memory:`;
2. zakłada syntetyczny obiekt i wyliczoną obsadę;
3. zapisuje konfigurację, checkboxy, kalendarz, godziny docelowe oraz
   nieobecności przez istniejące operacje backendu;
4. uruchamia produkcyjne `plan_month()` albo, po zmianie wybranego grafiku,
   `replan()`;
5. sprawdza każdego kandydata produkcyjnym `validate()`;
6. wybiera pierwszego poprawnego kandydata przez produkcyjne
   `select_candidate()` i odczytuje zapisany snapshot;
7. po `DECISION_REQUIRED` dodaje okno dla wcześniej zadeklarowanego wsparcia
   wyłącznie wtedy, gdy payload rzeczywiście proponuje tę operację, i ponawia
   planowanie;
8. przy błędzie zapisuje seed, decyzje wejściowe i wynik potrzebny do replay.

To NIE jest benchmark. Nie mierzy czasu, nie przyznaje punktów i nie porównuje
wersji. Nie używa przeglądarki, FastAPI/TestClient, sieci, AI ani danych
użytkownika.

## 2. Jedyna dozwolona architektura

```text
seed
  → typowany ScenarioSpec (decyzje koordynatora, bez PlanningState)
  → nowa syntetyczna baza :memory:
  → produkcyjne komendy zapisu
  → assemble_planning_state / plan_month
  → produkcyjny validate
  → select_candidate / zapisany snapshot
  → PASS albo failure JSON
```

Generator NIE tworzy bezpośrednio:

- `PlanningState`;
- `ShiftDemand`;
- `Assignment` ani witness-grafiku;
- `Deviation`;
- wierszy SQL.

Nie wylicza sam odpoczynku, godzin, kwalifikacji, skutków urlopu/chorobowego,
precedencji reguł ani dopuszczalności pracownika. Właścicielami pozostają
assembler, solver i validator.

Każdy przypadek używa osobnego połączenia `connect(":memory:")`, zamykanego w
`finally`. Zakazane jest czytanie `ROTA_DB_PATH`, `rota_dev.db`, backupu,
jakiejkolwiek ścieżki przekazanej przez użytkownika albo ponowne używanie bazy
między przypadkami. Do failure JSON nie trafia dump bazy.

## 3. Produkcyjne seamy

Scenario runner może wywoływać bezpośrednio tylko istniejące operacje używane
przez obecny backend:

- `bootstrap_or_resume_coordinator_context` — koordynator, Site i SiteProfile;
- `update_employee`, `update_membership`, `update_site_profile` — obsada,
  `day_only`, `can_work_24h` i katalog zmian;
- `set_calendar_day`, `set_target_hours`, `append_availability` — kalendarz,
  godziny docelowe, urlop, chorobowe i niedostępność;
- `add_external_support_window` — wyłącznie po rzeczywistej propozycji
  wsparcia w produkcyjnym payloadzie;
- `create_employee_shift_unavailability`,
  `create_employee_weekday_unavailability`, `create_day_only_n_exception` —
  istniejące checkboxy/reguły macierzy;
- `validate_standard_shift` — ta sama produkcyjna walidacja katalogu, której
  używa ekran Obiekt przed `update_site_profile`;
- `assemble_planning_state`, `plan_month`, `replan`, `validate`,
  `select_candidate`;
- `get_current_schedule_snapshot` wyłącznie do potwierdzenia zapisu po wyborze.

Można konstruować obiekty wejściowe tych komend (`Site`, `SiteProfile`,
`Employee`, `SiteMembership`, `CalendarDay`, `StandardShift`). Nie wolno
importować routerów `api/**`, wywoływać repozytoriów zapisu ani tworzyć nowego
connectora. Jeżeli potrzebnego działania nie ma na powyższej liście,
implementator zgłasza blocker zamiast pisać jego lokalny odpowiednik.

T028 nie zmienia żadnego z tych seamów.

## 4. Model przypadku i deterministyczność

Typowany `ScenarioSpec` zawiera wyłącznie jawne decyzje wejściowe:

- `family`, `case_seed`, miesiąc;
- syntetyczny Site/SiteProfile i katalog zmian;
- dokładną liczbę pracowników LOCAL wynikającą z wariantu Obiektu oraz jedną
  wcześniej zadeklarowaną osobę EXTERNAL_SUPPORT bez okna;
- wartości checkboxów i okresy reguł;
- CalendarDay dla każdego dnia miesiąca;
- target hours równe jawnie `168` dla każdego LOCAL; bez targetu dla
  EXTERNAL_SUPPORT;
- okresy `UNAVAILABLE_24H`, `LEAVE_GRANTED` lub `SICK_LEAVE`;
- kolejne wyniki produkcyjne przed i ewentualnie po wsparciu;
- bezpieczne `summary` tych samych faktów.

Wszystkie identyfikatory i nazwy wejściowe mają prefiks `LAB-`. Generator używa
wyłącznie `random.Random(case_seed)`. Ten sam seed tworzy identyczny
`ScenarioSpec` i identyczną kolejność komend.

Produkcyjne UUID, timestamps, action IDs, version IDs i demand IDs nie są
częścią gwarancji deterministyczności i są normalizowane lub pomijane w
porównaniu/replay. Generator nie może omijać produkcyjnych komend tylko po to,
aby uzyskać identyczne techniczne ID.

## 5. Macierz scenariuszy v1

Wariant Obiektu jest jawnym wymiarem, nigdy liczbą losowaną z zakresu:

- `ordinary_12h_single_5`: D/N 12h, jedna osoba na zmianie, 5 LOCAL;
- `ordinary_12h_double_10`: D/N 12h, dwie osoby na zmianie, 10 LOCAL;
- `ochrona_24h_single_4`: zmiana 24h, jedna osoba, 4 LOCAL;
- `ochrona_24h_single_5`: zmiana 24h, jedna osoba, 5 LOCAL;
- `ochrona_24h_double_8`: zmiana 24h, dwie osoby, 8 LOCAL;
- `ochrona_24h_double_10`: zmiana 24h, dwie osoby, 10 LOCAL.

Przypadki cyklicznie obejmują sześć wariantów. Seed wybiera jeden z jawnych
wariantów pracy koordynatora: baza bez nieobecności, 14-dniowy
`LEAVE_GRANTED`, `SICK_LEAVE` długości 0-21 dni, pojedyncza decyzja checkboxa
(D, N albo dzień tygodnia) albo jednodniowy brak N. Urlop dotyczy najwyżej
jednego LOCAL; chorobowe może dotyczyć tej samej albo innej osoby. Wszystkie
zapisy przechodzą przez produkcyjne komendy, a ich godziny i skutki pozostają
własnością backendu.

Każdy przypadek ma jedną osobę EXTERNAL_SUPPORT bez okna. Pierwszy przebieg
jest próbą własną załogą. Jeżeli wynik `DECISION_REQUIRED` zawiera
produkcyjną opcję skonfigurowania tej osoby, runner zapisuje okno dokładnie na
wskazane blocking demands i ponawia planowanie. Bez takiej opcji okno nie
powstaje. Wynik przed i po decyzji pozostaje w raporcie.

Nie dodawać TRAINING/TRAINEE, CLEANING, wielu Site ani innych wariantów.
Miesiące rotują przez 28, 29, 30 i 31 dni, w tym luty przestępny.

## 6. Oracle bez drugiego solvera

### FEASIBLE

Runner:

1. wymaga `status == FEASIBLE` i 1–3 kandydatów;
2. pobiera kanoniczny `PlanningState` przez assembler;
3. wywołuje `validate(state, candidate)` dla KAŻDEGO kandydata;
4. wymaga `hard_pass=True` dla każdego;
5. przeprowadza kontrolę świata zamkniętego z §7;
6. wybiera pierwszego kandydata przez `select_candidate`;
7. odczytuje snapshot i potwierdza, że zapisano dokładnie wybraną listę
   Assignment (po tożsamości i pełnych polach, bez dopowiadania zmian).

Runner nie wymaga konkretnej osoby ani kolejności, jeśli validator dopuszcza
kilka rozwiązań. Nie istnieje witness tworzony przez generator.

### DECISION_REQUIRED

Runner wymaga statusu `DECISION_REQUIRED`, zera kandydatów i niepustego
payloadu. Dla jawnego jednodniowego braku N wymaga także wskazanego demandu N
w `blocking_shift_demands`. Nie wylicza odpoczynku ani eligibility.

`TECHNICAL_ERROR`, błędny status, brak payloadu lub kandydat odrzucony przez
validator oznacza błąd przypadku.

## 7. Kontrola świata zamkniętego

To jedyna niezależna kontrola poza produkcyjnym validatorem. Dla każdego
kandydata i zapisanego snapshotu runner sprawdza:

- `employee_id` należy do dokładnego zbioru zapisanych pracowników: LOCAL albo
  jednej wcześniej zadeklarowanej osoby EXTERNAL_SUPPORT. Osoba zewnętrzna
  może wystąpić dopiero po zapisaniu dozwolonego okna;
- każdy PRIMARY ma `covers_demand_id` należący do demandów z assemblera oraz
  dokładnie ten sam przedział czasu;
- kandydat nie zawiera dodatkowego Assignment ani odcinka pracy poza demandami;
- profil i kanoniczne demands nie zawierają `ShiftCatalogKind.OTHER` (`INNY`);
- `other_site_assignments` jest puste; `external_windows` jest puste przed
  propozycją, a po niej zawiera wyłącznie okna wcześniej zadeklarowanej osoby
  i dokładnych blocking demands.

Kontrola nie próbuje wyjaśniać, dlaczego pracownik jest legalny. To zadanie
validatora. Odrzuca jednak wspólne przeoczenie solvera i validatora, które
dodałoby pracownika, demand albo godziny nieistniejące w świecie koordynatora.

Testy podstawiają mutanty wyniku: obcy pracownik, obcy demand, Assignment bez
demandu i dodatkowy przedział czasu. Każdy musi zostać odrzucony przez kontrolę
świata zamkniętego, nawet gdy podstawiony validator zwróci `hard_pass=True`.

## 8. CLI, failure record i replay

```text
python -m tools.solver_scenario_lab --cases 25 --seed 20260824
python -m tools.solver_scenario_lab --family <name> --case-seed <seed>
```

- `--cases`: dodatnia liczba, domyślnie 25;
- `--seed`: root seed, domyślnie 20260824;
- `--family` i `--case-seed` występują razem i odtwarzają jeden przypadek;
- `--output-dir`: domyślnie `artifacts/solver-scenario-lab`.

Stdout: jedna krótka linia na błąd z komendą replay, a na końcu dokładnie
`CASES=<n> PASS=<n> FAIL=<n> SEED=<seed>`. Exit 0 dla pełnego PASS, 1 dla co
najmniej jednego błędu.

PASS nie zapisuje pliku. Błąd zapisuje nowy, nigdy nienadpisywany:

```text
<output-dir>/run-<root-seed>/case-<index>-<case-seed>.json
```

JSON zawiera schema_version, SHA kodu, seed/family, `ScenarioSpec.summary`,
uporządkowaną listę wykonanych komend, oczekiwany/rzeczywisty status,
violations/warnings, semantyczny opis kandydatów i komendę replay. Nie zawiera
dumpu SQLite, ścieżek użytkownika, nazwisk ani danych spoza `LAB-*`.

Replay odtwarza decyzje z `family + case_seed`. Przy innym SHA ostrzega, lecz
może wykonać przypadek; nie wymaga identycznych UUID/timestamps.

## 9. Pliki i limit

Nowe:

- `tools/solver_scenario_lab.py` — maksymalnie 600 linii;
- `tests/test_solver_scenario_lab.py` — maksymalnie 600 linii.

Modyfikowane:

- `tasks/ROTA-T028/brief.md` — wyłącznie mechaniczne włączenie
  `OWNER_ACCEPTED` z 2026-08-24;
- `.gitignore` — wyłącznie `artifacts/solver-scenario-lab/`.

Brak `tools/__init__.py`: Python uruchamia `tools` jako namespace package, więc
trzeci pusty plik nie jest potrzebny. Brak nowych zależności.

Zakazane są zmiany w `rota/**`, `api/**`, `frontend/**`, `benchmarks/**`,
frozen specs i istniejących testach. Jeżeli implementacja nie mieści się w
dwóch nowych plikach, zgłasza blocker zamiast tworzyć framework.

## 10. Minimalna macierz odbioru

T28-01 — CLI: argumenty, exit codes i dokładna linia podsumowania.

T28-02 — ten sam seed daje identyczny ScenarioSpec/komendy; inny seed zmienia
realny fakt. Techniczne ID i timestamps są ignorowane.

T28-03 — pierwsze sześć przypadków pokrywa dokładnie sześć wariantów Obiektu,
a test seeda pokrywa pięć wariantów decyzji oraz miesiące 28/29/30/31.

T28-04 — każda komenda scenariusza przechodzi przez seam z §3; test blokuje
bezpośredni zapis SQL i import `api`.

T28-05 — jawny dowód, że każda sprawa używa nowej bazy `:memory:` i nie czyta
`ROTA_DB_PATH` ani pliku użytkownika.

T28-06 — FEASIBLE: każdy kandydat przechodzi produkcyjny validator i kontrolę
świata zamkniętego; pierwszy przeżywa select + readback. DECISION_REQUIRED:
zero kandydatów i kompletny payload.

T28-07 — urlop i chorobowe są zapisane przez append_availability zgodnie z §5;
kandydat nie przydziela pracy w aktywnym okresie, a generator nie liczy godzin.

T28-08 — sześć wariantów ma dokładnie liczebności 5/10/4/5/8/10 i katalog
12h/24h zapisany przez update_site_profile.

T28-09 — wariant checkboxa rotuje trzy istniejące decyzje macierzy i nie konstruuje
SiteRuleVersion ręcznie.

T28-10 — jawny brak N zwraca DECISION_REQUIRED przed wsparciem. Okno powstaje
tylko po produkcyjnej propozycji, a raport zachowuje wynik przed/po i użycie
LAB-EXTERNAL.

T28-11 — mutanty obcego pracownika/demandu, braku demandu i dodatkowych godzin
są odrzucane niezależnie od podstawionego PASS validatora.

T28-12 — profil/demands `INNY`, niezadeklarowany EXTERNAL_SUPPORT lub
other-Site powodują GENERATOR_ERROR przed uznaniem wyniku.

T28-13 — failure JSON/replay, brak pliku dla PASS, brak nadpisania.

T28-14 — realne CLI `--cases 6` wykonuje sześć wariantów Obiektu na
produkcyjnych seamach.

T28-15 — diff-scope z §9, build/import i pełna regresja. Znany stary test
source-diff T023 nie należy do T028.

## 11. Polecenie dla implementatora

Przeczytaj `AGENTS.md` i cały brief. Implementujesz poligon, nie nowy backend.
Najpierw zapisz `ScenarioSpec`, potem odtwórz jego decyzje na osobnej bazie
`:memory:` wyłącznie operacjami z §3. Nie buduj `PlanningState`, witness,
Assignment ani ShiftDemand ręcznie.

Jeżeli poligon znajdzie błąd produkcyjnego solvera lub validatora, zapisz
failure JSON i zgłoś go. Nie naprawiaj `rota/**` w T028.
