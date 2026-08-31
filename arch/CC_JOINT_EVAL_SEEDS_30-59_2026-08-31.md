# CC — ręczna ocena, seedy 30-59 (Wariant B, batch2, post-T045)

Status: **RĘCZNY PRZEGLĄD, dyscyplina identyczna jak przy dry-runie Wariantu A**
— `BRAK_UWAG` / `DO_SPRAWDZENIA` / `BRAK_DOWODU`, zero przeliczania faktów
już policzonych przez `validate()`/`rota/balance.py`, zero wymyślania nowych
progów, zero automatycznego Tasku z samego faktu znaleziska.

Zakres: `tasks/ROTA-T044/round_01/tests/reports/batch2/seed30.json` ..
`seed59.json` (30 obiektów).

## Wynik ogólny

- Zero crashy / `HARNESS_EXCEPTION`.
- Wszystkie 30: `final_result.status = FEASIBLE`.
- Rozwiązane wcześniejsze pytanie z batcha 1 (seed16/21 "brak kandydatów mimo
  FEASIBLE"): to nie był bug, tylko sprawdzanie złego pola. `plan_result` to
  PIERWSZA próba PLAN (przed pętlą EXTERNAL) — gdy jego status to
  `DECISION_REQUIRED`, `candidates` jest puste z definicji. Właściwy,
  ostateczny wynik z kandydatami jest w `final_result` (potwierdzone wprost
  na 10 seedach z tej partii: 31, 37, 39, 40, 41, 42, 45, 46, 52, 56 — każdy
  miał `plan_result.status=DECISION_REQUIRED` + puste `candidates`, ale
  `final_result.candidates` niepuste i `selected=True` po jednym/dwóch
  EXTERNAL). **BRAK_UWAG dla tej klasy obserwacji.**

## KOREKTA (2026-08-31, po odpowiedzi Codexa i weryfikacji z OWNEREM)

Poniższe DO_SPRAWDZENIA-01 **wycofuję jako nowe znalezisko**. Codex słusznie
wskazał, że `tasks/ROTA-T044/brief.md:96-102` zawiera dosłowny cytat OWNERA
sprzed T044, dotyczący dokładnie tej samej klasy zjawiska w surowych danych
Wariantu A: *"Nie, bo to sprawa kadrowa nie nasza, koordynator musi pamiętać
o urlopach nie Rota, Rota mu podaje narastająco bilans poprawnie."*
Sprawdziłem to bezpośrednio z OWNEREM i policzyłem arytmetykę dla seed 47:
całkowite zapotrzebowanie miesięczne to 472h, przy 5 osobach to 94.4h/osobę —
daleko poniżej targetu 168h. To dokładnie ten sam mechanizm
("zapotrzebowanie/osobę < norma pełnoetatowa"), nie osobne zjawisko
"skupienia zapotrzebowania w tygodniu", jak błędnie założyłem niżej. Moja
hipoteza mechanizmu (sekcja poniżej, zachowana dla przejrzystości procesu)
była nietrafiona.

**Jedno węższe, nierozstrzygnięte pytanie zostaje otwarte** (nowe, różne od
pierwotnego zarzutu): czy `calculator_result=5` dla seed 47 to faktycznie
minimalna obsada wymagana dla wykonalności (np. przez wymogi odpoczynku po
H24, szczytowe obciążenie w piątek/sobotę), czy nadmiarowe zawyżenie wobec
472h realnego zapotrzebowania (472h/168h ≈ 2.8, czyli objętościowo ~3 osoby
by wystarczyły)? Niesprawdzone — jeśli warto to zbadać, to osobny,
świadomie nowy wątek, nie kontynuacja tego znaleziska.

## DO_SPRAWDZENIA-01 (WYCOFANE — zobacz KOREKTĘ powyżej): systematyczny niedobór godzin bez absencji

**19/30 (63%)** obiektów ma co najmniej jednego pracownika z
`effective_target_hours == target_hours_per_employee` (czyli **bez żadnej
korekty za absencję**) i mimo to `month_balance <= -20h` w finalnym,
zaakceptowanym grafiku. Seedy: 31, 33, 34, 35, 36, 40, 41, 43, 44, 45, 46,
47, 48, 50, 54, 55, 56, 58, 59. Niedotknięte: 30, 32, 37, 38, 39, 42, 49, 51,
52, 53, 57.

Konkretny przykład — **seed 47** (reproduktor:
`python -c "from api.deps import get_conn; from api.main import app; from fastapi.testclient import TestClient; from rota.persistence.db import connect; from tests.property.coordinator_simulator import run_full_scenario_b; conn = connect(':memory:'); app.dependency_overrides[get_conn] = lambda: (yield conn); print(run_full_scenario_b(TestClient(app), 47, num_replans=1))"`):

- `target_hours_per_employee = 168`, 5 zadeklarowanych pracowników,
  `calculator_result = 5` (zgodne z deklaracją — kalkulator obsady nie jest
  tu winny).
- Tylko 2 z 5 pracowników mają wylosowaną absencję (`LEAVE_GRANTED`).
- Pozostali trzej (EMP-2, EMP-3, EMP-4) mają **pełny, nieskorygowany**
  `effective_target_hours = 168`, a mimo to `planned_hours` = 108/112/108,
  czyli `month_balance` = **-60h / -56h / -60h**.
- Katalog zmian (`atoms`) generuje zapotrzebowanie tylko na 3 z 7 dni
  tygodnia (weekday 2, 5, 6) — reszta tygodnia ma zero zmian.

**Hipoteza mechanizmu (nierozstrzygnięta):** kalkulator obsady liczy
potrzebną liczbę osób z SUMY godzin zapotrzebowania w miesiącu podzielonej
przez `target_hours_per_employee`, ale nie sprawdza, czy to zapotrzebowanie
jest równomiernie rozłożone w tygodniu. Gdy zapotrzebowanie jest skupione na
kilku dniach tygodnia, nawet poprawnie wyliczona liczba osób nie może w
praktyce "wypełnić" każdemu pełnego miesięcznego celu — dokładnie ten sam
rodzaj rozjazdu ("obsada z nazwy" vs "obsada w praktyce"), który był
fundamentem projektowym Symulatora od T038.

**Silny kontrargument, dlaczego to może być artefakt narzędzia, nie
produktu:** sam produkt ostrzega w `final_result.warnings` na każdym z tych
19 obiektów: `"missing target_hours for employee '...', month <M>: quarter
carry-in reset to 0"`. System ma mechanizm wyrównywania `month_balance`
przez `quarter_balance`/`unresolved_carryover` między miesiącami tego samego
kwartału — ale Wariant B buduje **izolowane, pojedyncze miesiące** bez
kontekstu kwartału, więc ten mechanizm nigdy nie ma szans zadziałać w tych
danych. Możliwe, że to, co wygląda jak "niedobór", w realnym, wielomiesięcznym
użyciu byłoby normalnie wyrównane w następnym miesiącu kwartału.

**Jawne niewiadome (dlatego `DO_SPRAWDZENIA`, nie stwierdzony defekt):**
1. Czy kalkulator obsady Wariantu B faktycznie ignoruje rozkład
   zapotrzebowania po dniach tygodnia, czy to zamierzone uproszczenie
   (`arch/` dokumentuje to jako "uproszczoną, ale przejrzystą heurystykę")?
2. Czy sam produkt (nie Symulator) miałby ten sam wzorzec przy prawdziwym,
   wielomiesięcznym kontekście kwartału, czy `quarter_balance` rzeczywiście
   by to wyrównał?
3. Nie sprawdzałem, czy to WYŁĄCZNIE artefakt izolowanego jednomiesięcznego
   testu Wariantu B, czy realny sygnał dla koordynatorów.

Nie stwierdzam, które wyjaśnienie jest prawdziwe — to pytanie do Codexa i
architekta, tak jak przy SHIFT-24-PAIR-01.

## BRAK_DOWODU

Brak przypadków w tej partii.
