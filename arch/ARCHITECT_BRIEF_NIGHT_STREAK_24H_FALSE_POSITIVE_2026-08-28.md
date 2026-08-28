# BRIEF DLA ARCHITEKTA — PLAN FAŁSZYWIE UZNAJE ZWYKŁY OBIEKT H24 ZA NIEWYKONALNY

**Stan:** ZGŁOSZENIE ZNALEZISKA — CC READ-ONLY, NIE READY FOR IMPLEMENTATION.
**Źródło:** dwa NIEZALEŻNE potwierdzenia w tej samej sesji — (1) Symulator
Koordynatora (ROTA-T038/T039, dane syntetyczne), (2) realny obiekt testowy
Pawła w `rota_dev.db` (dane ręcznie wprowadzone przez UI, bez mojego
udziału w konfiguracji) — plus dowód wykonalności opisany w sekcji 3.
**BASE_MAIN_SHA:** `d445ee6` (po zmergowaniu T039). Zero zmian w `rota/`
w tej sesji przed tym znaleziskiem — potwierdzone `git diff` od `aa6330c`.

## 1. Obserwowane zachowanie

Obiekt: jedna zmiana 24h (06:00-06:00 następnego dnia), regime OCHRONA,
5 pracowników LOCAL, `target_hours` poprawnie ustawione, katalog zmian
poprawnie zapisany. PLAN dla całego miesiąca (wrzesień 2026, 30 dni) zwraca
`DECISION_REQUIRED`:

- 30 zablokowanych zapotrzebowań — **KAŻDA** nocna połówka 24h zmiany w
  całym miesiącu;
- wszystkich 5 pracowników z powodem `NIGHT-STREAK-01`
  ("Koliduje z limitem dwóch nocek pod rząd");
- `unblocking_options`: "Brak automatycznego rozwiązania przy obecnej
  obsadzie i zapisanych ograniczeniach."

**Dodatkowy eksperyment (Paweł, po pierwszej wersji tego briefu):**
wyłączenie NIGHT-STREAK-01 wyłącznie w pamięci procesu (bez zmiany plików)
nie naprawia problemu — PLAN nadal zwraca `DECISION_REQUIRED`, tym razem z
powodem `REST-01`. To pokazuje, że problem NIE jest zlokalizowany
wyłącznie w NIGHT-STREAK-01 — coś w modelu solvera lub w diagnostyce
konfliktu dla katalogu H24 jest szersze niż jedna reguła. Traktować jako
dowód, że usterka dotyczy obsługi H24 ogólnie, nie jako potwierdzenie
konkretnego mechanizmu.

## 2. Dowód wykonalności — ręczna rotacja przechodzi produkcyjny `validate()`

Zbudowany ręcznie, poza solverem: prosta rotacja round-robin 5 pracowników
(A,B,C,D,E,A,B,C,D,E,...), jedna 24h-zmiana dziennie, na TYCH SAMYCH
zapotrzebowaniach co realny obiekt Pawła (`assemble_planning_state` na
`rota_dev.db`, wrzesień 2026, 60 zapotrzebowań = 30 dni × D/N-połówki).
Każdemu `Assignment` ustawione `work_period_id`/`required_rest_after_hours`
dokładnie tak, jak robi to `solver.py::_extract_assignments`
(`work_period_id = f"{site_id}:{work_period_template_id}"`,
`resolve_required_rest(demand.required_rest_hours)`).

Wynik niezależnego `rota.planning.validator.validate(state, assignments)`:

```
hard_pass: True
violations: []
```

**Legalne, w pełni zgodne z HARD rozwiązanie na te same dane istnieje** —
solver go nie znajduje i zwraca `DECISION_REQUIRED`. To jest twardy dowód,
że problem leży w SOLVERZE (nie znajduje istniejącego rozwiązania) i/lub w
DIAGNOSTYCE KONFLIKTU (błędnie twierdzi, że żadne rozwiązanie nie istnieje)
— nie w rzeczywistym braku obsady. Ten dowód **nie lokalizuje** która
konkretna reguła/mechanizm jest winna — patrz zastrzeżenie w sekcji 4.

## 3. Tropy do zbadania przez architekta (żaden niepotwierdzony jako jedyna przyczyna)

- `rota/planning/solver.py::_build_day_kind_terms` (linia ~329) klasyfikuje
  slot pracownik×zapotrzebowanie pod kluczem
  `d = slot.demand.start_datetime.date()`, osobno dla `d_term` i `n_term`.
  Dla zmiany 24h obie połówki (komponent D i komponent N) DZIELĄ tę samą
  datę rozpoczęcia (sprawdzone na realnych danych: `2026-09-01-D` i
  odpowiadający komponent N obie mają `start_datetime.date() ==
  2026-09-01`). Możliwy skutek: pracownik pracujący 24h-zmianę w dniu X
  dostaje jednocześnie `d_term=1` i `n_term=1` na tej samej dacie.
- Eksperyment z sekcji 1 (wyłączenie NIGHT-STREAK-01 → REST-01 przejmuje
  blokadę) sugeruje, że także logika REST-01/asumpcji dla par H24
  (`work_period_component`, `constraints.py:388-390` i okolice) może być
  zaangażowana, nie tylko NIGHT-STREAK-01.
- Diagnostyka konfliktu (`_conflicting_night_streak`, `solver.py:638-665`)
  może wyciągać niepełny/mylący rdzeń UNSAT z asumpcji CP-SAT, niezależnie
  od tego, która reguła jest ostatecznie winna.

**Żaden z powyższych nie jest potwierdzoną przyczyną** — to lista tropów do
debugowania modelu CP-SAT przez architekta, nie diagnoza.

## 4. Argument właściciela (2026-08-28, werbatim) — co dowodzi, a czego nie dowodzi

"Jak przy 24 godzinnych zmianach może być konflikt nocek, skoro po 24
godzinach pracy należy się 24 godziny odpoczynku". Po przepracowaniu zmiany
24h obowiązuje osobna reguła odpoczynku, która fizycznie uniemożliwia tej
samej osobie przepracowanie kolejnej 24h-zmiany następnego dnia — a tym
bardziej trzech pod rząd przy prostej rotacji 5 osób.

**Co ten argument dowodzi**: że przy 5 osobach rotujących pojedynczo
istnieje legalny grafik (zgodne z dowodem w sekcji 2) — PLAN jest
niewykonalny fałszywie.
**Czego NIE dowodzi**: który konkretny mechanizm (NIGHT-STREAK-01, REST-01,
diagnostyka konfliktu, coś innego w modelu H24) jest za to odpowiedzialny.
Eksperyment z sekcji 1 pokazuje, że to nie jest tak proste jak "wyłącz
NIGHT-STREAK-01 dla H24".

## 5. Dowody z niezależnych reprodukcji

**Symulator** (`tests/property/coordinator_simulator.py`, seed=2,
`SINGLE_24H`, 2026-09): identyczny komunikat, identyczne dni blokujące
(2026-09-01/02/03-N jako pierwsze trzy), niezmienny po 4 kolejnych
dosłaniach pracownika (5→9 osób).

**Realny obiekt Pawła** (`rota_dev.db`, site `SITE-af2c7186...`, "Test1"):
identyczny komunikat, 30 zablokowanych demandów (cały miesiąc), 5
pracowników z tym samym powodem. Zweryfikowane bezpośrednio przez
`curl POST .../schedule/2026-09-01/plan` na żywo działającym serwerze
deweloperskim — nie przez odczyt kodu.

## 6. Poza zakresem tego zgłoszenia

- CC nie proponuje konkretnej poprawki — wymaga zrozumienia całego modelu
  CP-SAT (solver + diagnostyka konfliktu), nie punktowej zmiany.
- Nie sprawdzone: czy błąd dotyczy WYŁĄCZNIE katalogu `SINGLE_24H`/H24, czy
  też np. `WEEKDAY_12H_WEEKEND_24H` (który w symulatorze dał identyczny
  wynik dla swojej weekendowej 24h-części — patrz `simulator_report.md`
  seed=3).
- Obserwacja o katalogu zmian zmienianym po utworzeniu wersji `WORKING`
  (niezwiązana z fałszywą niewykonalnością H24) zgłoszona OSOBNO — patrz
  `arch/ARCHITECT_BRIEF_SHIFT_CATALOG_STALE_WORKING_VERSION_2026-08-28.md`.
  Nie rozszerza zakresu tego zgłoszenia ani przyszłego tasku solvera.

## 7. Warunek przekazania

Zgłoszenie faktów, dowodu wykonalności i dwóch niezależnych reprodukcji —
nie gotowy TASK_SCOPE i nie diagnoza. Wymaga: (1) architekt/Codex
debuguje model CP-SAT (solver.py + constraints.py + diagnostyka konfliktu)
i lokalizuje faktyczny mechanizm usterki spośród tropów z sekcji 3,
(2) Paweł decyduje o priorytecie (realny obiekt ochrony z jedną zmianą 24h
to prawdopodobnie najczęstszy rzeczywisty przypadek użycia programu —
problem jest realny i ma mocny reproduktor, więc prawdopodobnie wysoki
priorytet).
