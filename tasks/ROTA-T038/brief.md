# ROTA-T038 — Symulator Koordynatora (property-based test flow całego programu)

Status: **KOREKTA 3 ZAKOŃCZONA (autor: CC), do audytu Codex**

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

## 6. Poza zakresem

- Warstwa przeglądarki/UI — osobna sprawa (Playwright), nie ten mechanizm.
- Dokończenie gałęzi R5 benchmarku (`benchmark/real-object-architect-2026-08-13`).
- Refaktor z audytu PR #9.
- Losowe święta, wariancja `posts`, sprawdzanie frozen/REALIZED w REPLAN —
  kandydaci na kolejną rundę tego samego mechanizmu.

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
