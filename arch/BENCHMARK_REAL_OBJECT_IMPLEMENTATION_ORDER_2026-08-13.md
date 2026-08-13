# ZLECENIE TESTOWE DLA CC — benchmark realnego pięcioosobowego obiektu

Status: OWNER-DIRECTED / READY FOR IMPLEMENTATION BY CC
Data: 2026-08-13
Właściciel decyzji produktowej: Paweł
Autor kryteriów testowych i późniejszy audytor: Codex
Dokument powiązany:
`arch/BENCHMARK_REAL_OBJECT_PROPOSAL_2026-08-13.md` (`17b1b67`)

## Rozstrzygnięcie właściciela

Nie ma otwartego pytania, czy benchmark ma odwzorowywać realny obiekt.
Właściciel rozstrzygnął cel wcześniej i potwierdził go 2026-08-13:

> Benchmark ma odtwarzać warunki mojego obiektu z 5 osobami, w tym jedną
> pracującą tylko na dniówki, a następnie tworzyć warunki brzegowe pokazujące,
> czy brak dopasowania wynika z rzeczywistego braku załogi, czy z błędu kodu.

Nie jest potrzebna decyzja architekta ani zmiana kontraktu produktu. To
naprawa infrastruktury testowej. CC implementuje, Codex wykonuje niezależny
audyt. Jeżeli podczas implementacji okaże się, że istniejący frozen contract
nie definiuje oczekiwanego statusu dla konkretnej, potrzebnej klasy wejścia,
CC nie zgaduje: zgłasza pojedynczy `CONTRACT_GAP` właścicielowi/architektowi.

## Korekta kwalifikacji istniejącego benchmarku

`benchmarks/rota_stress.py` jest benchmarkiem syntetycznych, z góry
wykonalnych przypadków. Może pozostać dodatkowym testem solvera, ale:

- nie jest benchmarkiem realnego obiektu;
- nie może być używany jako dowód wydolności pięcioosobowej obsady;
- jego `100/100 PASS` nie odpowiada na pytanie właściciela;
- nie wolno zastąpić nim benchmarku wymaganego w tym zleceniu.

W szczególności obecny generator tworzy 6 albo 10 pracowników i rozdziela ich
na sztuczne pule D/N. Dwie osoby nieużywane przez witness pozostają dostępne
solverowi jako rezerwa. To inny model obsady niż realny obiekt.

Wynik `57/72 FEASIBLE, 15/72 DECISION_REQUIRED` z dokumentu propozycji jest
wyłącznie obserwacją z doraźnego skryptu. Nie jest jeszcze dowodem regresyjnym:
generator, seedy i oracle dla `DECISION_REQUIRED` nie zostały utrwalone.
Dokument zawiera również omyłkę `30 miesięcy × 3 = 72`; rozkład wyników
`24 + 24 + 24` wskazuje na 24 miesiące. CC nie przenosi tych liczb jako
oczekiwań nowego benchmarku.

## Nienaruszalny model realnego obiektu

Każdy podstawowy przypadek benchmarku ma używać:

- dokładnie 5 pracowników: A, B, C, D, E;
- dokładnie jednej osoby `DAY_ONLY`: C;
- A, B, D i E zdolnych do pracy D/N;
- dokładnie jednej obsady PRIMARY na D i jednej na N każdego dnia;
- zmian D 05:00–17:00 oraz N 17:00–05:00 następnego dnia;
- minimum 11 godzin odpoczynku;
- granicy decyzji LOAD-01: ponad 60 godzin w dowolnym ruchomym oknie 7 dni;
- braku dostępnego X/Y w scenariuszach podstawowych;
- faktycznych przedziałów czasu, również dla N przechodzącej przez miesiąc;
- sześciu dni poprawnej historii przed pierwszym dniem badanego miesiąca.

Źródłem bazowych danych obiektu jest
`tests/fixtures/rota_reg_001.json` wraz z
`tests/regression/oracle_rota_reg_001.md`. Benchmark może parametryzować
miesiąc i perturbacje, ale nie może zwiększać zespołu, tworzyć ukrytej rezerwy
ani zmieniać C w pracownika nocnego.

## Cel techniczny

Benchmark ma dla każdego przypadku odpowiedzieć niezależnie na trzy pytania:

1. Czy istnieje legalny grafik przy wszystkich HARD constraints, w tym
   LOAD-01 <= 60 h?
2. Jeżeli nie, czy istnieje legalny grafik po zdjęciu wyłącznie granicy
   LOAD-01, z zachowaniem pozostałych HARD constraints?
3. Czy wynik produkcyjnego `rota.planning.engine.plan()` odpowiada tej
   niezależnej klasyfikacji i wskazuje właściwą przyczynę?

Sam brak `TECHNICAL_ERROR` nie jest PASS. Sam `DECISION_REQUIRED` również nie
jest PASS.

## Obowiązkowa niezależna klasyfikacja przypadków

Każdy przypadek przed uruchomieniem produkcyjnego engine musi zostać
sklasyfikowany przez reference oracle jako dokładnie jedna z klas:

### KNOWN_FEASIBLE

Istnieje pełny grafik spełniający wszystkie HARD constraints, łącznie z
REST-01 i LOAD-01.

Oczekiwanie od produkcji:

- `FEASIBLE` z kompletnym kandydatem;
- niezależny HARD PASS kandydata;
- `DECISION_REQUIRED`, `TECHNICAL_ERROR`, brak kandydata albo timeout jest
  FAIL-em kodu, nie „trudnym przypadkiem”.

### LOAD_DECISION_REQUIRED

Nie istnieje grafik z LOAD-01 <= 60 h, ale istnieje pełny grafik po zdjęciu
wyłącznie tego limitu.

Oczekiwanie od produkcji:

- status i payload zgodne z aktualnym frozen kontraktem dla LOAD-01;
- konkretny pracownik i okno wskazane przez blocker muszą rzeczywiście
  przekraczać próg w niezależnym rozwiązaniu/zaświadczeniu;
- `FEASIBLE` z przekroczeniem, inny zmyślony blocker albo `TECHNICAL_ERROR`
  jest FAIL-em.

### PROVEN_STAFFING_SHORTAGE

Nie istnieje pełny grafik nawet po zdjęciu wyłącznie LOAD-01, przy zachowaniu
coverage, eligibility, dostępności, REST-01, DAY_ONLY i pozostałych HARD.

Oczekiwanie od produkcji:

- brak fałszywego `FEASIBLE`;
- status i blocker zgodne z istniejącym frozen mappingiem dla rzeczywistego
  niedoboru;
- `TECHNICAL_ERROR` lub blocker niezgodny z niezależnym dowodem jest FAIL-em.

Jeśli reference oracle zwraca `UNKNOWN`, przypadek jest błędem/inconclusive
benchmarku. Nie wolno zaliczyć go ani jako PASS solvera, ani jako dowodu
niedoboru.

## Wymagania wobec reference oracle

Reference oracle nie może importować ani wywoływać:

- `rota.planning.engine.plan`;
- produkcyjnego adaptera solvera;
- produkcyjnych builderów constraints/eligibility;
- produkcyjnego validatora jako źródła oczekiwanej klasy.

Może użyć OR-Tools jako niezależnego mechanizmu obliczeniowego, ale musi
zbudować własny, minimalny model bez współdzielenia kodu modelu produkcyjnego.
Model referencyjny obejmuje co najmniej:

- pełne pokrycie D/N;
- DAY_ONLY i aktywność/uprawnienie pracownika;
- twarde nieobecności;
- fixed/REALIZED/frozen assignments użyte w danym przypadku;
- rzeczywiste przedziały REST-01, także przez granicę miesiąca;
- ruchome okna LOAD-01 z sześciodniową historią;
- wykonywalne HARD SiteRules, jeżeli scenariusz jawnie je zawiera.

Oracle uruchamia dwa rozstrzygające solve'y: capped i uncapped-LOAD. Do
klasyfikacji wolno użyć wyłącznie rozstrzygającego `FEASIBLE/OPTIMAL` albo
`INFEASIBLE`; `UNKNOWN` nie jest dowodem.

Niezależny checker ma ponownie sprawdzić każdy witness zwrócony przez oracle
oraz każdy kandydat produkcji bez wywoływania produkcyjnego validatora.
Produkcyjny validator może zostać uruchomiony dodatkowo, ale nie zastępuje
niezależnego checkera.

## Obowiązkowa drabina scenariuszy

Generator ma być deterministyczny i objąć co najmniej:

1. Bazowy ROTA-REG-001 bez zmiany oczekiwań oracle.
2. Miesiące długości 28, 29, 30 i 31 dni oraz różne dni tygodnia pierwszego
   dnia miesiąca.
3. Poprawną sześciodniową historię: D i N bez nakładania tego samego
   pracownika na dwie zmiany oraz N kończącą się w pierwszym dniu miesiąca.
4. PLAN bez istniejącego grafiku oraz REPLAN z REALIZED/frozen/baseline.
5. Narastające nieobecności: pojedyncze, nakładające się dla dwóch osób oraz
   spiętrzenia kolejnych dni.
6. Nieobecność C (DAY_ONLY) i oddzielnie nieobecności pracowników elastycznych.
7. Przypadek, w którym trudne przetasowanie nadal ma legalny grafik <=60 h.
8. Przypadek, w którym pełne pokrycie jest możliwe dopiero powyżej 60 h.
9. Przypadek z prostym, niezależnym dowodem braku eligible pracownika dla
   konkretnej zmiany.
10. Granice REST-01 dokładnie 11 h oraz poniżej 11 h.
11. Granice LOAD-01 dokładnie 60 h oraz powyżej 60 h w oknie przecinającym
    początek albo koniec miesiąca.
12. Noc kończąca miesiąc połączona z próbą przydzielenia D pierwszego dnia
    następnego miesiąca.

Perturbacje mają być dodawane stopniowo. Raport ma pokazywać pierwszy poziom,
na którym reference oracle zmienia klasę z `KNOWN_FEASIBLE` na
`LOAD_DECISION_REQUIRED` albo `PROVEN_STAFFING_SHORTAGE`.

## Reprodukowalność i raport

Każdy przypadek musi posiadać:

- stabilny `case_id`;
- seed;
- miesiąc;
- pełny opis perturbacji;
- pięcioosobowy roster i flagę C=DAY_ONLY;
- boundary assignments;
- oczekiwaną klasę reference oracle;
- wynik capped i uncapped reference solve;
- produkcyjny status, blocker i czas;
- błędy niezależnego checkera.

CLI ma umożliwiać:

- odtworzenie pojedynczego `case_id`/seedu;
- uruchomienie całej stałej macierzy;
- deterministyczny raport JSON nadający się do zachowania jako artefakt.

Generator przed wywołaniem produkcji musi sam zweryfikować boundary i
wszystkie fixed inputs. Przypadek z nielegalnym wejściem (np. D i N tego
samego pracownika bez odpoczynku już w historii) jest błędem generatora i nie
może zostać użyty do oceny solvera.

## Oddzielenie poprawności od wydajności

Raport zawiera dwie niezależne sekcje:

- `CORRECTNESS`: zgodność produkcji z reference oracle;
- `PERFORMANCE`: mean, p50, p95, max i liczba timeoutów per klasa.

Wolny, ale poprawny przypadek nie może być opisany jako błąd merytoryczny bez
wcześniej zatwierdzonego limitu SLA. Niepoprawny status nie może być ukryty
przez dobry czas wykonania.

## Zakres implementacji CC

Dozwolone:

- nowe/zmienione pliki w `benchmarks/`;
- testy generatora, reference oracle, klasyfikacji i CLI w `tests/`;
- mechaniczne doprecyzowanie nazwy/opisu istniejącego syntetycznego
  benchmarku, jeżeli jest potrzebne do uniknięcia mylących raportów.

Niedozwolone w tym zleceniu:

- zmiany w `rota/planning/`, `rota/domain.py` lub persistence;
- poprawianie PlanningEngine, aby dopasować go do wyniku benchmarku;
- zmiana frozen spec/addendów/oracle ROTA-REG-001;
- dodawanie szóstej osoby, X/Y albo automatyczne rozluźnianie HARD w celu
  uzyskania zielonego wyniku;
- uznanie istniejącego `100/100` za wykonanie tego zlecenia.

Jeżeli benchmark ujawni błąd PlanningEngine, CC kończy zlecenie benchmarkowe
z czerwonym, odtwarzalnym przypadkiem i przekazuje osobny finding do audytu.
Nie naprawia engine w tym samym commicie.

## Kryteria odbioru implementacji

Codex może zwrócić PASS dla benchmarku tylko wtedy, gdy:

1. Każdy przypadek podstawowy ma dokładnie A–E i tylko C=DAY_ONLY.
2. Nie istnieje ukryta pula ani dodatkowy eligible pracownik.
3. Każda oczekiwana klasa pochodzi z niezależnego capped/uncapped oracle.
4. `DECISION_REQUIRED` jest zaliczany wyłącznie w klasie i z przyczyną, które
   potwierdził oracle.
5. Wszystkie witnessy i kandydaci przechodzą niezależny checker.
6. Obowiązkowa drabina 1–12 jest pokryta testami klas, nie pojedynczymi
   literalnymi przykładami.
7. Generator wykrywa własne nielegalne boundary inputs przed `plan()`.
8. Ten sam seed/case_id odtwarza identyczne wejście i klasyfikację.
9. Raport rozdziela correctness od performance.
10. Testy istniejącego produktu pozostają zielone, ale ich liczba sama w sobie
    nie zastępuje powyższych dowodów.

Po implementacji CC przekazuje Codexowi dokładny SHA oraz polecenia do:

- pełnej macierzy benchmarku;
- pojedynczego case replay;
- testów reference oracle/generatora;
- raportu JSON.
