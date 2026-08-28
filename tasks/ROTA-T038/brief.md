# ROTA-T038 — Symulator Koordynatora (property-based test flow całego programu)

Status: **KOREKTA 4 ZAKOŃCZONA (autor: CC), do audytu Codex**

Base implementation SHA: `37e32da6244e4e43f504ef44b9b5a290f05a21b7` (`main`,
po zmergowaniu T037).

TASK_SCOPE:
- tests/property/__init__.py
- tests/property/coordinator_simulator.py
- tests/property/test_coordinator_simulator.py

Wszystkie trzy to nowe pliki (`tests/property/` nie istniał wcześniej) —
3 nowe pliki przekracza `MAX_NEW_FILES = 2` bramki `backend.py`.
**OWNER_ACCEPTED, Paweł, 2026-08-28** (patrz sekcja 5 — historia bramek).

## 1. Wynik dla właściciela (stan aktualny, KOREKTA 3)

Owner decision, Paweł, 2026-08-28 (rozmowa) — po trzech wcześniejszych,
niepełnych podejściach do testowania wertykalnego (R4 benchmark: zamrożony
5-osobowy model; `test_vertical_full_stack.py`: 4 ręczne scenariusze,
zatrzymuje się przed API; ręczne scenariusze Pawła: nie skalują się).

Cel: **nie** benchmark oceniający, czy solver ma rację (to rola
`benchmarks/REAL_OBJECT_BENCHMARK.md`, bez zmian) — tylko cienka warstwa,
która wymyśla RÓŻNE realistyczne obiekty i scenariusze absencji, klika
prawdziwe endpointy HTTP dokładnie tak jak przeglądarka koordynatora, i
**raportuje**, co się stało. Jedyna assercja w kodzie: brak wyjątku/5xx.

**Zamrożone zasady (owner ruling 2026-08-28, po dwóch rundach korekt):**

1. Obsada wymyślonego obiektu to DOKŁADNIE wyliczone minimum z jego
   własnego zapotrzebowania godzinowego (`ceil(godziny_miesięcznie / 160)`,
   **bez żadnego marginesu**) — koordynator nie prowizoruje obsady "na
   zapas". Potwierdzone matematycznie na przykładzie właściciela: 24h
   zmiana × 1 posterunek × 30 dni = 720h/mies.; 720/160 = 4.5 → 5 osób.
2. Każdy pracownik dostaje PRAWDZIWY `target_hours` na badany miesiąc
   (równy podział zapotrzebowania obiektu przez jego obsadę), ustawiony
   przez realny endpoint — nigdy `null`.
3. Wsparcie zewnętrzne NIE istnieje przed pierwszym PLAN. Powstaje
   wyłącznie jako reakcja na `DECISION_REQUIRED` — patrz punkt 4.
4. Gdy PLAN zwróci `DECISION_REQUIRED`, symulator reaguje jak prawdziwy
   koordynator: **musi kogoś znaleźć** (dopisuje jednego kolejnego
   lokalnego pracownika z tym samym `target_hours`) i uruchamia PLAN
   ponownie — nie REPLAN, bo nie ma jeszcze wybranego grafiku do ochrony.
   Powtarzane do `MAX_HIRES=4` prób.
5. Gdy PLAN od razu da `FEASIBLE`, **nie** uruchamiamy automatycznie
   REPLAN. REPLAN to osobny, jawnie zaraportowany scenariusz: symulacja
   zdarzenia W TRAKCIE miesiąca (nowa absencja po wybraniu kandydata) —
   deterministycznie tylko na parzystych seedach, żeby było to opisywalne
   bez dodatkowego ukrytego losowania.

Raport (`round_01/tests/simulator_report.md`) pokazuje na wpis: obiekt
startowy, absencje, ewentualne zatrudnienia w reakcji na DECISION_REQUIRED,
finalny status PLAN + powód + faktycznie użyte osoby (z jawną flagą
"ROZBIEŻNOŚĆ" gdyby ktoś spoza deklaracji trafił do grafiku), oraz osobno
scenariusz REPLAN (albo "nie dotyczy").

## 2. Historia korekt (dla kontekstu, nie jako aktualna specyfikacja)

- **v1** (`f6d1b85`): property-based benchmark oceniający niezmienniki
  solvera (niezależna re-walidacja, "musi być FEASIBLE"). Odrzucone:
  "nie projektuj warstwy zarządzającej solverem".
- **KOREKTA 1** (nigdy niewdrożona w kodzie, tylko plan): jeden sztywny
  obiekt. Odrzucone: właściciel chciał RÓŻNE wymyślone obiekty/scenariusze.
- **KOREKTA 2** (`74f901c`): różne obiekty, ale `employee_count` liczony
  z marginesem `+1` i z góry losowanym wsparciem zewnętrznym. Codex round-1
  audyt (`d153d05`, exact SHA `1e72cc9`): **FAIL**, trzy findings —
  margines dawał 6 zamiast 5 osób, `target_hours=null` dla wszystkich,
  wsparcie zewnętrzne istniało przed PLAN. Wszystkie trzy naprawione w
  KOREKCIE 3 (ten dokument, sekcja 1).

## 3. Świadome uproszczenia (aktualne, do wiadomości)

- **OCHRONA bez prawdziwego katalogu 24h** dla kształtu D/N — sam
  `Site.planning_regime=OCHRONA` już zmienia egzekwowanie REST/tygodniowego
  odpoczynku niezależnie od kształtu katalogu zmian.
- **Brak losowych świąt w kalendarzu** — każdy dzień `holiday=False`, jak
  we wszystkich istniejących fixture'ach w repo.
- **`posts` (liczba równoległych posterunków) na stałe 1** — przy 2 jeden
  seed (PLAN+REPLAN) mierzono na ~90s, przy 10 seedach to realne ryzyko
  kilkunastu minut. Zmienność zostaje w kształcie zmiany/regime/absencjach.
- **REPLAN nie sprawdza niezmiennika "frozen/REALIZED nietknięte"** — to
  pozostaje pokryte przez istniejący ręczny
  `test_12_freeze_affects_later_replan`, nie duplikowane tutaj.

## 4. Koszt

`DEFAULT_SEED_COUNT = 5`. Każdy seed: 1+ wywołań PLAN (więcej przy
zatrudnieniach reaktywnych, do `MAX_HIRES=4`), plus REPLAN na parzystych
seedach — kilka pełnych przebiegów CP-SAT na seed. `ROTA_SIM_SEEDS=<N>`
włącza głębszy przebieg do ręcznego uruchomienia — nie ma być odpalane
domyślnie przy każdej iteracji CC.

## 5. Historia bramek backend.py

- SHA `2d74efffee670a47f16ee7d3281e6ed7eb7f0b46` (przed KOREKTĄ 2): FAIL
  `NEW_FILES: 3` + WYMAGA_DECYZJI `TOTAL_LINES: 385`. OWNER_ACCEPTED.
- SHA `74f901c6378022c2e268ad49bf40f693b7593f25` (KOREKTA 2): FAIL
  `NEW_FILES: 3` (te same pliki) + WYMAGA_DECYZJI `TOTAL_LINES: 435`.
  OWNER_ACCEPTED.
- Bramka po KOREKCIE 3 do uruchomienia przed kolejnym audytem Codex.

## 5a. backend.py gate po KOREKCIE 3

SHA `73eb7cc9bc6319eb7893bf8dd782b092b522f84a`: FAIL `NEW_FILES: 3` (te same
pliki) + WYMAGA_DECYZJI `TOTAL_LINES: 481`. **OWNER_ACCEPTED, Paweł,
2026-08-28.**

## 6. Poza zakresem

- Warstwa przeglądarki/UI — osobna sprawa (Playwright), nie ten mechanizm.
- Dokończenie gałęzi R5 benchmarku (`benchmark/real-object-architect-2026-08-13`).
- Refaktor z audytu PR #9.
- Losowe święta, wariancja `posts`, sprawdzanie frozen/REALIZED w REPLAN —
  kandydaci na kolejną rundę tego samego mechanizmu.

## 7b. KOREKTA 4 (Codex round-2 FAIL)

`tests_r2.txt` (commit `81a4b44`, exact SHA `7e28f0d`): FAIL, dwa findings.

**T38-R2-01 — `target_hours` nie był rzeczywistym wymiarem czasu pracy.**
Poprzednio: podział zapotrzebowania obiektu przez liczbę osób (dawało 144h).
Naprawione: `nominal_monthly_hours_kp(month)` — realny wzór art. 130 KP
(40h za każdy pełny tydzień pon-nd w miesiącu + 8h za każdy pozostały dzień
pon-pt poza pełnymi tygodniami, minus 8h za święto poza niedzielą).
Zweryfikowane ręcznie i w kodzie: 176h dla września 2026 (3 pełne tygodnie
+ 4+3 dni robocze na brzegach = 120+56), zgodnie z wyliczeniem Codexa.
Wartość niezależna od liczebności obsady — realny wymiar pełnego etatu,
nie udział w zapotrzebowaniu obiektu.

**T38-R2-02 — reakcja na `DECISION_REQUIRED` zawsze dokłada LOCAL, nie
EXTERNAL_SUPPORT po "produkcyjnej propozycji wsparcia".** Zapytałem
właściciela wprost, czy to faktycznie wymagany mechanizm. Odpowiedź
(werbatim, 2026-08-28): *"Fakt jest taki, że na posterunku musi się ktoś
zjawić, choćby pani Prezes, jak to rozwiążesz w symulatorze technicznie
nie ma znaczenia... Byle nie był już domyślnie zapisany do obsady bo tak
się nie dzieje realnie."* Czyli jedyny realny wymóg to: reaktywna osoba
NIE może być w obsadzie startowej — co `hire_one_more_local()` już
spełnia (wywoływane wyłącznie po `DECISION_REQUIRED`, nigdy przy
budowaniu obiektu). **Konkretny mechanizm (LOCAL vs EXTERNAL_SUPPORT)
pozostaje bez zmian — wymóg "musi być EXTERNAL_SUPPORT" wykracza poza to,
co właściciel faktycznie polecił; flagowane, nie zaimplementowane.**

Przy okazji: zbadałem osobne pytanie właściciela o niejednorodne katalogi
zmian (różne wzorce tydzień/weekend, ta sama nazwa zmiany pokrywana przez
osoby o różnej długości dyżuru) — potwierdzone w kodzie
(`rota/planning/shift_catalog.py::generate_catalog_demands`, komentarz
"Multiple entries and overlaps are legal and generate independent
occurrences"): oba scenariusze są już natywnie wspierane przez wiele
wierszy katalogu z różnym `active_weekdays`/godzinami, zero zmian
produktowych potrzebnych. Nie wykorzystane jeszcze w generatorze
symulatora — kandydat na kolejną rundę.

Pełny formalny przebieg po tej korekcie (5 seedów): `1 passed in 226.22s
(0:03:46)`, zero awarii, `target_hours=176` potwierdzone dla wszystkich.

backend.py gate (od SHA `7e28f0d` do `a670af4`, ten konkretny fix):
WYMAGA_DECYZJI `RATIO: 7.0:1`. **OWNER_ACCEPTED, Paweł, 2026-08-28.**

## 7a. KOREKTA 3 (Codex round-1 FAIL naprawiony) + produktowe znalezisko

Naprawione dokładnie 3 findings z `tests_r1.txt` (commit `d153d05`, exact
SHA `1e72cc9`): usunięty margines `+1` (obsada teraz dokładnie `ceil(720/160)=5`),
usunięte z-góry-włączane wsparcie zewnętrzne (istnieje tylko jako reakcja
po `DECISION_REQUIRED` przez `hire_one_more_local()`), każdy pracownik
dostaje realny `target_hours` przez prawdziwy endpoint (nie `null`).

Przy okazji symulator złapał osobny, realny problem produktowy: `SICK_LEAVE`
zaznaczone PRZED istnieniem jakiegokolwiek planu kończy się nieobsłużonym
500 (`IncompleteAbsenceReferenceError`) — zgłoszone jako
`arch/ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md`, POZA zakresem
tego taska (dotyka zamrożonego dodatku T023, nie jest to zadanie CC do
samodzielnej naprawy). Symulator na razie **nie testuje** tej ścieżki
(`allow_sick_leave=False` w puli przed pierwszym PLAN), z jawną notatką w
`simulator_report.md` odsyłającą do briefu — nie omija problemu cicho.

Pełny formalny przebieg po tej korekcie (5 seedów): `1 passed in 271.19s
(0:04:31)`, zero awarii, obsada każdego obiektu = dokładnie 5, zero
rozbieżności deklaracja-vs-użycie.

## 7. Weryfikacja

- `ruff check tests/property/` — czyste.
- Reproduktor bez solvera (jak w audycie Codex round-1): dla 5 seedów
  potwierdzone `employee_count=5`, `kinds={'LOCAL'}` (brak
  EXTERNAL_SUPPORT przed PLAN), `target_hours=144` dla każdego (nie null).
- Pełny formalny przebieg (5 seedów) do uruchomienia i dołączenia jako
  dowód przed kolejnym audytem.
