# Znalezisko — SHIFT-24-PAIR-01 w 67% przebiegów Wariantu B

Status: **ZNALEZISKO DO DYSKUSJI — nie brief, nie kontrakt, zero zmian kodu**

Data: 2026-08-31
Kontekst: kontrolowany przebieg 30 obiektów Wariantu B (seedy 0-29, mirror
20-obiektowego portfela Wariantu A), zrobiony jako "dry run" evaluatora
ręcznie, bez żadnej nowej infrastruktury.

## 1. Skala

**20 z 30 wygenerowanych obiektów (67%) kończy się `TECHNICAL_ERROR`**,
wszystkie z tym samym typem naruszenia:

```
independent validator found HARD violations that cannot be attributed to
a known autonomy boundary: SHIFT-24-PAIR-01: template <id> mismatch
[lista pracowników A] vs [lista pracowników B]
```

## 2. Co dokładnie sprawdza SHIFT-24-PAIR-01

`rota/planning/validator.py::_check_24h_same_person` (linie ok. 450-478):
zmiana katalogowa sklasyfikowana jako `ShiftCatalogKind.H24` (dokładnie 24h
czasu trwania) jest wewnętrznie dzielona na dwie 12-godzinne połówki
dzielące jeden `work_period_template_id` (`shift_catalog.py::_components_for_shift`,
linie 151-164) — to modeluje jedną, ciągłą służbę 24h. Reguła wymaga, żeby
**ten sam zestaw pracowników** pokrywał obie połówki. Jeśli solver przypisze
różnych ludzi do pierwszej i drugiej połówki, niezależny walidator łapie to
jako twarde naruszenie i produkt zwraca `TECHNICAL_ERROR`.

## 3. Konkretny reproduktor — seed 0

Wygenerowany katalog (miesiąc 2026-12, obsada wg kalkulatora: 8):

| kind | start | end | required | dzień tyg. |
|---|---|---|---|---|
| D | 17:00 | 01:00 | 2 | 1 (Pon) |
| N | 20:00 | 12:00 | 2 | 1 (Pon) |
| N | 20:00 | 08:00 | 1 | 1 (Pon) |
| **D** | **08:00** | **18:00** | **1** | **2 (Wt)** |
| **N** | **08:00** | **08:00** | **1** | **2 (Wt)** |
| N | 14:00 | 06:00 | 1 | 3 (Śr) |
| D | 07:00 | 07:00 | 2 | 5 (Pt) |
| D | 00:00 | 00:00 | 1 | 6 (Sob) |
| D | 00:00 | 00:00 | 2 | 7 (Nd) |
| N | 14:00 | 00:00 | 2 | 7 (Nd) |

Pogrubiony wiersz dla wtorku: `N 08:00-08:00` to zmiana 24h (start==end),
a **w tym samym dniu, o tej samej godzinie startu**, jest DODATKOWO osobna,
niezależna zmiana `D 08:00-18:00`. Solver ma dwie konkurujące o tych samych
ludzi definicje pokrycia w tym samym oknie czasowym — i w efekcie inna osoba
pokrywa pierwszą połówkę 24h (zbieżną czasowo z tą osobną zmianą D) niż
drugą.

**Reprodukcja:**
```
python -c "from api.deps import get_conn; from api.main import app; from fastapi.testclient import TestClient; from rota.persistence.db import connect; from tests.property.coordinator_simulator import run_full_scenario_b; conn = connect(':memory:'); app.dependency_overrides[get_conn] = lambda: (yield conn); print(run_full_scenario_b(TestClient(app), 0, num_replans=0))"
```

Pełne surowe dane (10 seedów z tym błędem, katalog + pełny komunikat
walidatora): `tasks/ROTA-T044/round_01/tests/reports/batch1/seed{0,1,3,5,6,7,8,9,...}.json`
w tej gałęzi.

## 4. Sprawdzone bezpośrednio: czy to podwójna rezerwacja jednej osoby?

OWNER zapytał wprost, czy problem to solver pozwalający jednej osobie na
dwie nachodzące się zmiany. Sprawdziłem to bezpośrednio na 8 przebiegach
FEASIBLE (z realnymi `candidates`): **zero przypadków, gdzie jedna osoba ma
dwa nachodzące się w czasie Assignmenty.** To nie jest ten problem — solver
nigdzie nie double-bookuje jednej osoby. Problem to wyłącznie "różne osoby
na dwóch połówkach tej samej logicznej służby 24h", nie "jedna osoba na
dwóch zmianach naraz".

## 5. Dwie hipotezy o winie — świadomie nierozstrzygnięte

### Hipoteza A — generator Wariantu B tworzy nierealistyczne katalogi

Poprawka R10-01 (losowanie 0/1/2 niezależnych wpisów per (rodzaj, dzień),
szeroki wybór godzin startu i czasu trwania w tym 24h) nie ma **żadnego**
ograniczenia sensowności poza "odrzuć zero pokrycia w całym miesiącu".
W efekcie generator może (i regularnie tworzy) katalogi, których żaden
realny koordynator by nie skonfigurował: zmianę 24h nakładającą się w
czasie z osobną, krótszą zmianą tego samego dnia, albo — jak w wierszach dla
poniedziałku/niedzieli powyżej — trzy niezależne, mocno nachodzące się na
siebie zmiany naraz. To jest dokładnie ten sam rodzaj problemu, co "8 osób
na obiekcie 5-osobowym" z wcześniejszych ustaleń OWNERA — tylko teraz
dotyczy KATALOGU, nie obsady.

**Jeśli to jest główna przyczyna:** generator potrzebuje dodatkowej reguły
sensowności (analogicznej do "zero pokrycia = odrzuć") — np. zakaz
generowania zmiany 24h w tym samym dniu, w którym istnieje już inna,
niezależna zmiana nachodząca się czasowo z którąkolwiek z jej dwóch połówek.

### Hipoteza B — produkt powinien wymuszać spójność 24h PODCZAS liczenia, nie dopiero sprawdzać po fakcie

Nawet jeśli katalog jest "dziwny", produkt dostał go jako w pełni legalne
dane wejściowe (żaden z wierszy katalogu sam w sobie nie łamie żadnej reguły
zapisu — `rota/planning/shift_catalog.py:250` wprost mówi, że nakładające
się zmiany są legalne). Można argumentować, że skoro `SHIFT-24-PAIR-01` jest
twardą regułą, CP-SAT **powinien** ją wymuszać jako ograniczenie podczas
samego rozwiązywania (nigdy nie rozważać kandydata łamiącego tę regułę),
zamiast dopuszczać taki wynik i dopiero łapać go osobnym, niezależnym
walidatorem po fakcie — kończąc się nieczytelnym `TECHNICAL_ERROR` zamiast
np. próbą znalezienia grafiku, który tej reguły przestrzega, albo czytelnym
`DECISION_REQUIRED`.

**Nie rozstrzygam, która hipoteza (albo obie naraz) jest prawdziwa — to
pytanie do Codexa i architekta.**

## 6. Trzeci, osobny problem: brak diagnostyki przy TECHNICAL_ERROR

Niezależnie od pytania "kto zawinił" (sekcja 5), sam sposób, w jaki produkt
zgłasza `TECHNICAL_ERROR`, utrudnia diagnozę — sprawdzone bezpośrednio na
`seed0` z tej samej paczki batch1.

Gdy `PlanningResult.status == "TECHNICAL_ERROR"`, pole `candidates` w
odpowiedzi API jest zawsze `[]` (potwierdzone na `seed0`: `plan_result.candidates
== []`). Sam wygenerowany — ale odrzucony przez niezależny walidator —
kandydat grafiku (te konkretne przypisania, które doprowadziły do
naruszenia SHIFT-24-PAIR-01) nigdzie nie trafia do odpowiedzi. Zostaje
wyłącznie tekstowy `error_message`, np.:

```
independent validator found HARD violations that cannot be attributed to
a known autonomy boundary: SHIFT-24-PAIR-01: template <id> mismatch
[empA,...] vs [empB,...]
```

Ten komunikat wprawdzie nazywa konkretne `employee_id` i `template_id`, ale
to nie to samo, co móc zobaczyć realny, wygenerowany harmonogram i jego
przypisania. Żeby zrekonstruować mechanizm tego zgłoszenia (tak jak zrobiłem
to w sekcji 3), musiałem czytać kod (`validator.py`, `shift_catalog.py`) i
odtwarzać go pośrednio z samego katalogu zmian wejściowych — nie mogłem po
prostu zajrzeć w to, co solver faktycznie złożył.

Innymi słowy: produkt WIE, że coś poszło nie tak (stąd `TECHNICAL_ERROR` i
nazwane ID w komunikacie), ale wyrzuca dokładnie te dane (kandydata, który
do naruszenia doprowadził), które pozwoliłyby to zdiagnozować bez odtwarzania
mechanizmu z kodu.

Nie oceniam, czy to jest błąd, czy świadomy wybór projektowy (np. "nie
pokazujemy niepoprawnego kandydata, bo mógłby wprowadzić w błąd") — to
pytanie do Codexa/architekta, analogicznie do hipotez w sekcji 5.

## 7. Pytania do Codexa i architekta

1. Czy `SHIFT-24-PAIR-01` powinien być twardym ograniczeniem CP-SAT
   podczas solvingu, czy pozostać niezależnym post-hoc walidatorem (i wtedy
   `TECHNICAL_ERROR` jest tu poprawnym, oczekiwanym zachowaniem produktu na
   nierealistyczne dane wejściowe)?
2. Czy generator Wariantu B potrzebuje nowej reguły sensowności (poza "zero
   pokrycia"), zakazującej generowania zmiany 24h nachodzącej się czasowo z
   inną, niezależną zmianą tego samego obiektu? Jeśli tak — czy to Task na
   Symulator, czy to zmienia też coś w kontrakcie T044?
3. Czy 67% jest reprezentatywne, czy akurat ten mały (30-obiektowy) przebieg
   trafił nieproporcjonalnie dużo takich kolizji? (generator losuje niezależnie
   per obiekt, więc to możliwe, ale warto to nazwać wprost).
4. Czy to się nadaje na jeden mały Task (np. dodanie reguły do generatora +
   ewentualna poprawka produktu, jeśli hipoteza B się potwierdzi), czy trzeba
   to rozdzielić na dwa niezależne Taski (Symulator osobno, produkt osobno)?
5. Czy brak diagnostyki opisany w sekcji 6 (odrzucany kandydat przy
   TECHNICAL_ERROR) to osobny Task, czy naturalnie wchodzi w zakres tego
   samego Tasku co punkty 1-4 (bo dotyczy tej samej ścieżki kodu)?
