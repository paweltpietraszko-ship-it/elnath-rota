# FINDING 2026-09-05 — solver poświęca rytm D/N/W/W i unikanie 3 zmian pod
rząd dla precyzji "co do godziny" w rozliczeniu target_hours, nawet gdy
target_hours i tak nie da się zrealizować w całości

STATUS: finding + zweryfikowany mechanizm, NIE jest dokumentem
projektowym, NIE jest zamrożony. Materiał wejściowy dla architekta (ta
sama rola co inne `arch/FINDING_*`) — CC nie projektuje tutaj rozwiązania,
to zadanie architekta po przekazaniu przez Pawła. Dotyka solvera
(`rota/planning/solver.py`, `rota/planning/fairness.py`) — zgodnie z
własną zasadą CC ("dotyka solvera/kontraktu = pełny proces"), CC nie
wdraża tego sam.

## Origin (Paweł, 2026-09-05)

Obserwacja z realnej pracy: obiekty mają zwykle **nadwyżkę zatrudnienia**
(bufor na urlopy/L4), więc suma `target_hours` wszystkich pracowników
zwykle **przewyższa** realną liczbę godzin zapotrzebowania — struktury
nie da się w pełni obsłużyć (`target=168`, realne `worked≈144`, to
normalna sytuacja, nie błąd).

Paweł: *"rytm dobowy jest ważniejszy niż wtedy gdy target_houre jest 168 a
realane godziny to 144 (...) Solver nie ma z czego wyciągać założonych
godzin (...) Czyli nie mamy założonych godzin ani zachowanego rytmu."*

Dalej, po weryfikacji mechanizmu przez CC: koordynator w realnej pracy
**unika 3 zmian pod rząd bezwzględnie** (nigdy tego nie robi) — to nie
jest zwykła preferencja estetyczna, tylko coś bliższego twardej granicy,
którą koordynator łamie tylko w ostateczności, jeśli w ogóle. Paweł
wprost: to trzeba zrobić jako osobny Task.

## Verified findings (sprawdzone bezpośrednio w kodzie, nie zgadywane)

**1. Rytm D/N/W/W i kara za 3 zmiany pod rząd mają dokładnie tę samą,
najniższą możliwą wagę w solverze — i są matematycznie zdominowane przez
precyzję trafienia w `target_hours`.**

`rota/planning/fairness.py:14-19`:
```python
WEEKEND_FAIRNESS_WEIGHT = 1
HOLIDAY_FAIRNESS_WEIGHT = 1
TARGET_EQUITY_WEIGHT = 1
DN_RHYTHM_REWARD_WEIGHT = 1
THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT = 1
```

`rota/planning/solver.py:549-554` (`_add_combined_objective`):
```python
target_weight = (
    TARGET_DEVIATION_WEIGHT                               # = 100
    + TARGET_EQUITY_WEIGHT * MAX_COMPLETION_PCT
    + DN_RHYTHM_REWARD_WEIGHT * rhythm_match_count
    + THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT * third_shift_penalty_count
)
```

Komentarz w kodzie (`solver.py:493-505`, OWNER_CORRECTED 2026-08-25) mówi
to wprost: *"TARGET-01 has ABSOLUTE priority over equity/rhythm
specifically — not just a large weight ratio that happens to hold, a
mathematical guarantee (...) degrading total target deviation by even one
hour always costs more than the entire equity+rhythm swing could ever be
worth combined."* Ta sama gwarancja obejmuje `THIRD_CONSECUTIVE_SHIFT_PENALTY`
(ROTA-T034, `solver.py:509-514`) — dołączona jako "dokładnie jeden
kolejny term" do tej samej ochrony.

**2. Ta bezwzględna priorytetyzacja działa DWUWARSTWOWO — i druga warstwa
jest tym, co realnie łamie rytm nawet, gdy cel i tak jest nieosiągalny.**

- Warstwa 1 — `TARGET_DEVIATION_WEIGHT`: minimalizuje **sumę** niedoboru
  godzin wszystkich pracowników razem. Przy strukturalnej nadwyżce
  zatrudnienia to z góry przegrana bitwa — pewna część niedoboru jest
  nieunikniona.
- Warstwa 2 — `add_target_equity_fairness` (`fairness.py:139-168`):
  minimalizuje **rozpiętość procentu realizacji** (`worked/target*100`)
  między pracownikami — **nawet gdy suma niedoboru jest już z góry
  przesądzona**. Ta warstwa wymaga bardzo drobnej, godzinowej kontroli nad
  przydziałem (żeby wyrównać procenty między pracownikami o różnych
  `target_hours`) — a sztywny rytm D/N/W/W daje godziny tylko w grubych
  blokach (24h/48h na parę D/N). Żeby dobić kogoś do wyrównanego procentu,
  solver dorzuca/odejmuje pojedynczą zmianę w nieregularnym miejscu — i to
  jest moment, w którym rytm (i unikanie 3 zmian pod rząd) zostaje
  złamane, **mimo że cel `target_hours` i tak nie zostanie w pełni
  zrealizowany dla nikogo**.

**3. Program już ma gotowy, dojrzały mechanizm na "coś między HARD a
SOFT" — `DECISION_REQUIRED` — tylko nie jest do tego podłączony.**

`rota/planning/engine_types.py:48`: status wyniku planowania to jeden z
`"FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR", "NO_ALTERNATIVE"`.
`rota/planning/engine.py` używa dziś `DECISION_REQUIRED` dla prawdziwych
twardych konfliktów (REST-01, LOAD-01, MEMBERSHIP-01) — gdy solver nie
może zbudować grafiku bez złamania czegoś ważnego, **zatrzymuje się i
zwraca kompletny, czytelny dla koordynatora powód** (patrz
`rota/planning/decision_guidance.py`), zamiast po cichu to złamać.
"3 zmiany pod rząd" dziś nie korzysta z tego mechanizmu w ogóle — jest
zwykłym, najniżej ważonym SOFT, więc solver **nigdy nie zapyta
koordynatora**, po prostu cicho złamie wzorzec, kiedy uzna to za
korzystne dla precyzji `target_hours`.

## Czego NIE trzeba robić

- Nie trzeba zmieniać `TARGET_DEVIATION_WEIGHT` (warstwa 1) — minimalizacja
  sumarycznego niedoboru per obiekt zostaje jak jest, to nie jest
  przedmiotem tego findingu.
- Nie trzeba usuwać `add_target_equity_fairness` całkowicie — chodzi o to,
  żeby nie miała nieograniczonej, absolutnej priorytetyzacji kosztem
  rytmu/unikania 3 zmian pod rząd, a nie o wyłączenie jej.

## Otwarte pytania projektowe dla architekta (CC nie rozstrzyga)

1. ~~Czy "unikanie 3 zmian pod rząd" ma dostać realny, wysoki priorytet
   (bliski HARD) w samej funkcji celu, czy ma stać się osobnym,
   twardym ograniczeniem CP-SAT z ucieczką przez `DECISION_REQUIRED`,
   gdy solver naprawdę nie może go dochować?~~ **ROZSTRZYGNIĘTE (OWNER,
   2026-09-08, patrz niżej): drugie — osobne, twarde ograniczenie.**
2. Czy `add_target_equity_fairness` (wyrównywanie procentu realizacji)
   powinno dostać pasmo tolerancji (np. podobne rzędu wielkości do tego,
   które CC empirycznie zaobserwował dla samego trafienia w target —
   solver ląduje w granicach ok. jednego bloku zmianowego od celu), poza
   którym dalsze, drobniejsze wyrównywanie przestaje przebijać rytm/karę
   za 3 zmiany pod rząd? **NADAL OTWARTE.**
3. ~~Czy to dotyczy też rytmu D/N/W/W (`DN_RHYTHM_REWARD_WEIGHT`), czy tylko
   węższego "3 zmiany pod rząd" — Paweł mówił o obu, ale z różnym
   naciskiem (3 zmiany pod rząd = "coś między Hard a Soft"; ogólny rytm
   D/N/W/W = "ważniejszy niż" precyzja equity, ale niekoniecznie tej samej
   siły).~~ **ROZSTRZYGNIĘTE (OWNER, 2026-09-08): tylko węższe "3 zmiany
   pod rząd" dostaje HARD; ogólny rytm D/N/W/W zostaje SOFT i może zostać
   poświęcony na rzecz tego nowego twardego ograniczenia.**

## OWNER_CORRECTED 2026-09-08 — rozstrzygnięcie pytań 1 i 3

Paweł wprost: *"jak będziesz robić rytm to pamiętaj, że trzy zmiany pod
rząd musi być zabronione jako Hard nawet kosztem D/N/w/w."*

Rozstrzygnięcie: "3 zmiany pod rząd" (dziś `THIRD_CONSECUTIVE_SHIFT_PENALTY_WEIGHT`,
`add_third_consecutive_shift_penalty`, ROTA-T034) przestaje być SOFT w
funkcji celu i staje się osobnym, twardym ograniczeniem CP-SAT — z
ucieczką przez `DECISION_REQUIRED`, gdy solver naprawdę nie może go
dochować (ten sam, już istniejący, dojrzały mechanizm co REST-01/LOAD-01/
MEMBERSHIP-01, patrz punkt 3 wyżej). Ogólny rytm D/N/W/W
(`DN_RHYTHM_REWARD_WEIGHT`) pozostaje SOFT i może zostać jawnie poświęcony,
jeśli to jedyny sposób dochowania nowego twardego zakazu 3 zmian pod rząd
— czyli priorytet: HARD (3-zmiany-pod-rząd) > TARGET-01 > equity/D-N-W-W
rytm, w tej kolejności.

Jedyne, co zostaje otwarte, to pytanie 2 (pasmo tolerancji equity) — to
osobna, nierozstrzygnięta oś tego samego findingu i nie jest tym
rozstrzygnięciem objęte.

CC nadal nie projektuje implementacji (dotyka solvera, wymaga architekta)
— to rozstrzygnięcie tylko domyka jedną z trzech otwartych osi, żeby
architekt mógł napisać brief bez czekania na resztę, jeśli uzna to za
wystarczające, albo poczekać na rozstrzygnięcie pytania 2 też.

## Powiązane materiały

- [[project_quarter_closing_overtime_gap]] (pamięć CC) — ta sama
  dominacja `TARGET_DEVIATION_WEIGHT` została wcześniej empirycznie
  zweryfikowana jako *pożądana* dla końca kwartału (solver trafia w
  rozbieżne cele w granicach ok. jednego bloku zmianowego). Ten finding
  nie podważa tamtego ustalenia — dotyczy wyłącznie drugiej warstwy
  (equity/rytm/3-zmiany-pod-rząd), nie samego faktu, że TARGET-01 ma
  dominować.
- Materiał referencyjny (`Grafiki/7732.jpg`) był początkowo błędnie
  odczytany przez CC jako dowód wyjątku od reguły "nigdy 3 zmiany pod
  rząd" — to było pomyłką CC (zobaczone "D1 N1 N1" to w rzeczywistości 3
  dniówki z przerwami), skorygowaną przez Pawła. Podstawą tego findingu
  jest wyłącznie bezpośrednie stwierdzenie OWNERA, nie analiza obrazu.
