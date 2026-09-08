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
   (bliski HARD), czy stać się osobnym ograniczeniem HARD?~~
   **ROZSTRZYGNIĘTE OSTATECZNIE (OWNER, 2026-09-08, patrz niżej): osobne,
   bezwzględne HARD; bez wyjątku przez `DECISION_REQUIRED`.**
2. ~~Czy `add_target_equity_fairness` (wyrównywanie procentu realizacji)
   powinno dostać pasmo tolerancji (np. podobne rzędu wielkości do tego,
   które CC empirycznie zaobserwował dla samego trafienia w target —
   solver ląduje w granicach ok. jednego bloku zmianowego od celu), poza
   którym dalsze, drobniejsze wyrównywanie przestaje przebijać rytm/karę
   za 3 zmiany pod rząd?~~ **ROZSTRZYGNIĘTE OSTATECZNIE (OWNER,
   2026-09-08): tak, dopuszczone pasmo różnicy wynosi 24h między
   pracownikami. To tolerancja SOFT, nie twardy limit obsady.**
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
funkcji celu i staje się osobnym, twardym ograniczeniem CP-SAT. Późniejsze
ostateczne doprecyzowanie OWNERA wykluczyło proponowaną tu wcześniej
ucieczkę przez `DECISION_REQUIRED`; obowiązuje bezwzględny zakaz opisany
niżej. Ogólny rytm D/N/W/W
(`DN_RHYTHM_REWARD_WEIGHT`) pozostaje SOFT i może zostać jawnie poświęcony,
jeśli to jedyny sposób dochowania nowego twardego zakazu 3 zmian pod rząd
— czyli priorytet: HARD (3-zmiany-pod-rząd) > TARGET-01 > equity/D-N-W-W
rytm, w tej kolejności.

Pytanie 2 zostało później rozstrzygnięte przez OWNERA — patrz ostateczne
doprecyzowanie poniżej.

## Dodatkowy argument ownera (2026-09-08) dla pytania 2 (pasmo tolerancji equity)

Paweł: *"Czasami koordynator jest zmuszony dać komuś 180 godzin a innym
156, czyli solver może mieć luz."* Potwierdzone przez CC jako argument do
wykorzystania tam, gdzie potrzebny (nie ograniczony do jednego miejsca w
tym dokumencie).

Odczytanie: różnica rzędu 180h vs 156h (~24h, jeden pełny blok D/N) między
pracownikami jest w realnej pracy **normalna i akceptowalna**, nie błędem
do skorygowania — koordynator i tak często jest zmuszony dać komuś wyraźnie
więcej/mniej z powodów niezwiązanych z precyzją algorytmu. To dodatkowe,
jakościowe wsparcie dla hipotezy CC z pytania 2 (pasmo tolerancji rzędu
jednego bloku zmianowego), tym razem wprost od ownera, nie tylko z
empirycznej obserwacji CC. Późniejsze doprecyzowanie poniżej zamraża 24h
jako ostateczną wartość tego pasma.

## OWNER_FINAL 2026-09-08 — oba pozostałe rozstrzygnięcia

Paweł wprost: *"Wszystkie 3 zmiany pod rząd mają być zakazane, tolerancja
godzin jest dopuszczona, i może wynosić 24h między pracownikami."*

Zamrożone zachowanie dla briefu:

1. Każda trzecia kolejna służba tego samego pracownika na trzech kolejnych
   datach rozpoczęcia jest bezwzględnie zabroniona jako HARD. Nie ma ścieżki
   zatwierdzenia wyjątku przez koordynatora. Jeżeli bez naruszenia zakazu nie
   da się pokryć grafiku, PLAN nie powstaje; użytkownik dostaje czytelny
   komunikat i może zmienić obsadę lub dostępność, a następnie spróbować
   ponownie. Nie zapisuje się ani nie eksportuje grafiku łamiącego zakaz.
2. Equity dostaje pasmo tolerancji 24h między pracownikami. Różnica mieszcząca
   się w tym paśmie jest dopuszczalna i solver nie ma psuć rytmu D/N/W/W tylko
   po to, aby ją dalej zmniejszać. To tolerancja dla rankingu SOFT, a nie nowe
   ograniczenie HARD zabraniające różnic większych niż 24h; poza pasmem equity
   może nadal wpływać na wybór rozwiązania zgodnie z architekturą celu.
3. Ogólny rytm D/N/W/W pozostaje SOFT. Priorytet jest więc: bezwzględne HARD
   trzech kolejnych służb, następnie istniejące TARGET-01, a niżej equity z
   pasmem 24h i rytm D/N/W/W.

Finding jest gotowy do przekazania architektowi. Architekt ma opisać
implementację, wykorzystując istniejącego właściciela klasyfikacji służb i
nie rozszerzając wyjątku `DECISION_REQUIRED` z `NIGHT-STREAK-01` na ten nowy
bezwzględny zakaz.

## OWNER_CORRECTED 2026-09-08 — HARD ogranicza automat, nie władzę człowieka

Paweł wprost: *"program nie może negować decyzji koordynatora, on może tylko
oflagować odchylenie. Nigdy automatycznie nie blokujemy władzy człowieka,
program nie łamie Hard ale człowiek na własną odpowiedzialność może, dlatego
odnotowujemy decyzje koordynatora."*

To doprecyzowanie zastępuje wcześniejsze zbyt szerokie zdania o całkowitym
zakazie zapisu/akceptacji/eksportu:

1. HARD pozostaje bezwzględny dla automatycznego PLAN/REPLAN/Przelicz Plan:
   solver nie może sam zaproponować trzeciej kolejnej służby i nie dostaje
   automatycznej ścieżki wyjątku przez `DECISION_REQUIRED`.
2. Koordynator zachowuje istniejącą władzę ręcznej korekty. Może świadomie
   wpisać układ naruszający ten HARD; program ma go oznaczyć jako odchylenie,
   zapisać decyzję koordynatora i nie przedstawiać wyniku jako automatycznie
   zgodnego z regułą.
3. Późniejsza automatyczna operacja nie może cicho negować zaakceptowanej
   decyzji człowieka ani traktować w pełni istniejącego/odbytego okna jako
   nierozwiązywalnego błędu blokującego całą przyszłość. Nadal musi jednak
   uniemożliwić solverowi dołożenie nowej trzeciej kolejnej służby tam, gdzie
   nie ma zapisanej decyzji człowieka.
4. T058 nie wprowadza bezwzględnej blokady wydruku. Obsługa wydruku grafiku z
   odchyleniami podlega osobnemu, zaakceptowanemu kontraktowi jednorazowego
   potwierdzenia przed każdym wydrukiem.

Architekt ma rozdzielić w briefie dwa istniejące wejścia: automatyczny wynik
solvera (HARD, bez wyjątku) oraz ręczną korektę koordynatora (dozwolona z
odchyleniem i śladem decyzji). Nie tworzyć drugiego systemu wyjątków, jeżeli
istniejące `validate -> materialize_deviations -> coordinator action` wystarcza.

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
