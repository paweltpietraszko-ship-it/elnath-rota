# BRIEF DLA ARCHITEKTA — NIGHT-STREAK-01 BLOKUJE CAŁY MIESIĄC DLA ZWYKŁEGO OBIEKTU 24H

**Stan:** ZGŁOSZENIE ZNALEZISKA — CC READ-ONLY, NIE READY FOR IMPLEMENTATION.
**Źródło:** dwa NIEZALEŻNE potwierdzenia w tej samej sesji — (1) Symulator
Koordynatora (ROTA-T038/T039, dane syntetyczne), (2) realny obiekt testowy
Pawła w `rota_dev.db` (dane ręcznie wprowadzone przez UI, bez mojego
udziału w konfiguracji).
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

## 2. Dlaczego to wygląda na fałszywy alarm

NIGHT-STREAK-01 (`rota/planning/constraints.py:557`) zabrania **trzech**
kolejnych nocy pod rząd dla TEGO SAMEGO pracownika
(`add_max_two_consecutive_night_constraints` — nazwa funkcji: max DWIE z
rzędu są legalne, TRZECIA jest zabroniona).

Przy prostej rotacji 5 osób (A,B,C,D,E,A,B,C,D,E,...) po jednej 24h
zmianie dziennie, ŻADNA osoba nigdy nie pracuje więcej niż 1 dzień z 5 —
nigdy nawet 2 dni pod rząd, a limit dotyczy dopiero 3. To powinno być
trywialnie spełnialne nawet przy 2-3 osobach, a tym bardziej przy 5.
Dosłuchane w tej samej sesji dosłanie kolejnych 4 osób (do 9) NIE zmieniło
wyniku ani treści blokad — identyczne w każdym szczególe (patrz sekcja 4),
co dodatkowo wskazuje na błąd diagnostyki, nie na realny brak obsady.

## 3. Prawdopodobna przyczyna — współdzielony klucz dnia dla połówek D/N zmiany 24h

`rota/planning/solver.py::_build_day_kind_terms` (linia ~329) klasyfikuje
każdy slot pracownik×zapotrzebowanie pod kluczem
`d = slot.demand.start_datetime.date()` — DATA ROZPOCZĘCIA zapotrzebowania,
osobno dla `d_term` (D) i `n_term` (N).

Dla zmiany 24h (`generate_catalog_demands`, T012 expansion) obie połówki
JEDNEJ 24h-zmiany danego dnia — komponent D (np. 06:00-18:00) i komponent N
(18:00-06:00 następnego dnia) — mają **tę samą datę rozpoczęcia** (dzień X).
Sprawdzone wprost na realnych danych: `2026-09-01-D` start 2026-09-01
06:00; odpowiadający komponent N ma `work_period_component=2` i również
`start_datetime.date() == 2026-09-01`.

Skutek: pracownik pracujący 24h-zmianę w dniu X dostaje jednocześnie
`d_term=1` I `n_term=1` na TEJ SAMEJ dacie X — traktowany jak ktoś, kto ma
"noc" w dniu X. Jeśli licznik nocy w NIGHT-STREAK-01 sumuje to poprawnie
per pracownik per data, i każdy pracownik pracuje tylko co 5. dzień, to
NIE powinno dawać konfliktu. **Nie zdążyłem jednoznacznie potwierdzić
mechanizmu awarii do końca** (wymagałoby to debugowania samego modelu
CP-SAT/wyciągania asumpcji z `solver.py:638-665`,
`_conflicting_night_streak`) — zgłaszam to jako najbardziej prawdopodobny
trop, nie jako potwierdzoną przyczynę.

## 4. Dowody z obu niezależnych reprodukcji

**Symulator** (`tests/property/coordinator_simulator.py`, seed=2,
`SINGLE_24H`, 2026-09): identyczny komunikat, identyczne dni blokujące
(2026-09-01/02/03-N jako pierwsze trzy), niezmienny po 4 kolejnych
dosłaniach pracownika (5→9 osób).

**Realny obiekt Pawła** (`rota_dev.db`, site `SITE-af2c7186...`, "Test1"):
identyczny komunikat, 30 zablokowanych demandów (cały miesiąc), 5
pracowników z tym samym powodem. Zweryfikowane bezpośrednio przez
`curl POST .../schedule/2026-09-01/plan` na żywo działającym serwerze
deweloperskim — nie przez odczyt kodu.

## 5. Poza zakresem tego zgłoszenia

- CC nie proponuje konkretnej poprawki w `_build_day_kind_terms`/
  `add_max_two_consecutive_night_constraints`/ekstrakcji asumpcji — to
  wymaga zrozumienia całego modelu CP-SAT, nie punktowej zmiany.
- Nie sprawdzone: czy błąd dotyczy WYŁĄCZNIE katalogu `SINGLE_24H`/H24, czy
  też np. `WEEKDAY_12H_WEEKEND_24H` (który w symulatorze dał identyczny
  wynik dla swojej weekendowej 24h-części — patrz `simulator_report.md`
  seed=3).
- Naprawa dev-bazy Pawła (usunięcie osieroconego wskaźnika current-version
  dla września, żeby PLAN w ogóle wygenerował świeże zapotrzebowania z
  zapisanego katalogu) wykonana ręcznie, poza tym zgłoszeniem — osobny,
  mniejszy problem (patrz sekcja 6), niezwiązany z solverem.

## 6. Dodatkowa, osobna obserwacja (nie NIGHT-STREAK-01) — katalog zmian zmieniony po utworzeniu wersji roboczej

Niezależnie od powyższego: jeśli koordynator zapisze katalog zmian PO TYM,
jak dla danego miesiąca istnieje już wersja `WORKING` (utworzona np. z
pustym katalogem), `PLAN` nie odświeża zapotrzebowań tej wersji — ponowne
"Przelicz" liczy świeżo W PAMIĘCI, ale nic nie trafia do siatki, dopóki
nie powstanie NOWA wersja. U Pawła to wymagało ręcznego usunięcia wpisu w
`current_schedule_versions` dla (site, miesiąc), żeby kolejny PLAN
utworzył wersję od zera. To osobny, prawdopodobnie warty osobnego
zgłoszenia UX/kontraktowego temat (czy edycja katalogu zmian powinna
wymuszać/oferować odświeżenie bieżącej roboczej wersji) — nie rozstrzygane
tutaj.

## 7. Warunek przekazania

Zgłoszenie faktów i dwóch niezależnych reprodukcji, nie gotowy TASK_SCOPE.
Wymaga: (1) architekt/Codex potwierdza lub odrzuca hipotezę z sekcji 3
przez debug modelu CP-SAT, (2) Paweł decyduje o priorytecie (realny
obiekt ochrony z jedną zmianą 24h to prawdopodobnie najczęstszy
rzeczywisty przypadek użycia programu — jeśli to potwierdzony błąd, ma
wysoki priorytet).
