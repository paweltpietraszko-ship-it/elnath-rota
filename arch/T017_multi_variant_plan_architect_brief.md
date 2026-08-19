# Handoff brief for architect: solver returns multiple schedule variants (proponowane T017)

## Status

Czysto faktograficzny brief, bez proponowanego rozwiązania. Nazwa "T017" to
robocza etykieta, nie zamrożony identyfikator.

## Skąd to zadanie

Właściciel (Paweł), przy okazji pytania "co się dzieje, jeśli koordynatorowi
nie spodoba się wynik PLAN" (2026-08-16): pamięta, że przy projektowaniu
architektury solver miał przedstawiać **kilka wariantów** poprawnego
grafiku do wyboru, nie jeden. Zapytał, czy dziś koordynator musi po prostu
wcisnąć PLAN ponownie, i czy dostanie ten sam wynik.

## Fakt: to nie jest błędna pamięć — było to w referencyjnej architekturze, ale nie weszło do zamrożonego kontraktu

`ELNATH_WARD_HANDOFF_FINAL_2026-08-10/02_ELNATH_ROTA_SPEC_PRODUKTOWA_v0.19_REFERENCE.md:1195`
(referencyjny, nie zamrożony): *"solver może zwrócić do 3 pełnych propozycji
spełniających HARD; koordynator wybiera ostateczny wariant."*

Sprawdzone: ani zamrożony `ELNATH_WARD_HANDOFF_FINAL_2026-08-10/01_
ELNATH_WARD_FROZEN_EXECUTION_CONTRACT_v0.4_CURRENT.md`, ani dzisiejszy
`arch/spec.md` nie zawierają tego zdania ani żadnego odpowiednika. Oba
mówią wyłącznie o solverze **preferującym** lepszy wariant SOFT wewnętrznie
(np. `arch/spec.md`: "holiday fairness... solver preferuje warianty
zmniejszające nierówność") — czyli o wyborze **wewnątrz** solvera, nie o
prezentowaniu kilku gotowych opcji koordynatorowi. To ten sam wzorzec co
24h zmiana (`T012_24h_shift_architect_brief.md`): realna cecha z
referencyjnej architektury, która nie przetrwała przejścia do zamrożonego
kontraktu pilota v0.4.

## Fakt: struktura danych już dziś zakłada listę wariantów, ale implementacja zawsze wypełnia ją jednym elementem

`rota/planning/engine_types.py:46-51`:
```python
class PlanningResult:
    status: Literal["FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR"]
    candidates: list[list[Assignment]]
    ...
```
`candidates` jest typu **lista list** `Assignment` — strukturalnie gotowa
na kilka pełnych grafików naraz. Ale `rota/planning/engine.py:121`:
```python
return PlanningResult("FEASIBLE", [full], None, None, outcome.warnings + report.warnings)
```
zawsze wkłada dokładnie **jeden** kompletny grafik (`full`), opakowany w
listę jednoelementową. Nigdzie w kodzie nie ma ścieżki produkującej więcej
niż jeden element tej listy.

## Fakt: warstwa aplikacyjna już ma funkcję wyboru spośród kandydatów

`rota/application/plan_ops.py:103-108`, `select_candidate(...)`:
*"Operation 4. Persists a coordinator-chosen FEASIBLE candidate onto the
current WORKING version..."* — przyjmuje **konkretny** kandydat (`candidate:
list[Assignment]`) do zapisania, co zakłada, że coś wcześniej pokazało
koordynatorowi więcej niż jedną opcję do wyboru. Dziś, skoro `plan_month`
zawsze zwraca dokładnie jednego kandydata, ta funkcja w praktyce zawsze
dostaje tylko jedną możliwość — ale jej sygnatura/przeznaczenie nie
zakładają wyłącznie tego przypadku.

## Fakt: solver jest dziś deterministyczny

`rota/planning/solver.py:454-455`:
```python
solver.parameters.num_search_workers = 1
solver.parameters.random_seed = 0
```
Przy niezmienionych danych wejściowych (ta sama obsada, ten sam miesiąc,
te same reguły) ponowne wciśnięcie PLAN zwraca dziś **ten sam** grafik —
nie ma mechanizmu "pokaż mi coś innego". Jedyny sposób na inny wynik dziś
to zmiana danych wejściowych (np. ręczna korekta) przed ponownym
przeliczeniem.

## DECYZJA WŁAŚCICIELA — minimalna różnica wariantów (2026-08-16)

Każdy kolejny grafik przedstawiany jako odrębny wariant musi różnić się od
poprzedniego o **co najmniej 15%**. Jest to minimalny próg rzeczywistej
różnicy w obsadzie grafiku, nie cel optymalizacyjny.

Różnicy nie wolno uzyskiwać przez zmianę technicznych identyfikatorów
`Assignment`, kolejności elementów listy ani innych danych, które nie
zmieniają faktycznej obsady widzianej przez koordynatora. Architekt ma
zdefiniować mechaniczną metrykę porównania, jej mianownik i zasadę
zaokrąglania tak, aby próg 15% był jednoznaczny i testowalny. Mechanizm musi
też wykluczać ponowne zwrócenie wariantu identycznego z którymkolwiek
wcześniej przedstawionym w tej samej liście kandydatów.

## Otwarte pytania NIE rozstrzygane w tym briefie (należą do właściciela/architekta)

- Ile wariantów ma zwracać solver? (v0.19 referencyjnie mówi "do 3" — czy
  to nadal aktualna liczba, czy właściciel chce inną?)
- Jak dokładnie liczyć ustalone **15% rzeczywistej różnicy w obsadzie**:
  jaka jest jednostka i mianownik porównania oraz jak zaokrąglać próg dla
  małych grafików? To techniczne doprecyzowanie metryki nie może zmieniać
  minimalnego progu ani opierać różnicy na technicznych identyfikatorach.
- Co się dzieje, gdy solver znajdzie tylko 1 lub 2 warianty zamiast pełnych
  3 (bo więcej po prostu nie istnieje przy danym roster)?
- Jak to się ma do kosztu obliczeniowego — szukanie kilku odrębnych pełnych
  rozwiązań CP-SAT zamiast jednego wymaga dodatkowej logiki (np. wykluczenie
  poprzedniego rozwiązania i ponowne rozwiązanie), nie jest "za darmo".
- To pytanie techniczne dotyczy wyłącznie `rota/planning/solver.py`/
  `engine.py` — warstwa aplikacyjna (`select_candidate`) i typ danych
  (`PlanningResult.candidates`) już dziś strukturalnie to udźwigną bez
  zmian.

Dokument nie proponuje sposobu generowania wariantów ani ich liczby — to
świadomie pozostawione architektowi po decyzji właściciela co do powyższych
pytań.
