# Prośba do Codexa: niezależny brief dla Symulatora Koordynatora Wariant B

Status: **PROŚBA O NIEZALEŻNY BRIEF, NIE BRIEF SAM W SOBIE — CC celowo nie
projektuje tego rozwiązania, patrz "Dlaczego Codex, nie CC" niżej.**

## Kontekst

ROTA-T043 (`main`, exact SHA `6ea0e09` w ramach merge `1b6bfbf`) dało Symulator
Koordynatora, który OWNER po przejrzeniu wyników nazwał **Wariantem A**:
deterministyczny, stały zestaw 20 obiektów (seedy 0-19, zawsze te same przy
każdym uruchomieniu). Sam Wariant A jest wartościowy i zostaje — dobry jako
**czujnik regresji**: jeśli po zmianie kodu ten sam, zawsze identyczny zestaw
20 przypadków nagle daje inny wynik, to jest realny sygnał, że coś się
zepsuło.

Ale to nie jest to, czego OWNER potrzebuje do testowania programu w szerszym
sensie. Potrzebny jest **Wariant B**: generator, który przy KAŻDYM uruchomieniu
losuje NOWE, różne obiekty/scenariusze — nie odgrywa zamkniętej listy.

## Rozmowa z OWNER, która do tego doprowadziła (2026-08-30, dosłownie)

> "Widzę nadal problemy. To nadal odtwarzanie 20 scenariuszy? Jak włączysz
> ponownie symulator to przetworzy te same 20 obiektów?"

Po potwierdzeniu przez CC, że tak, zakres jest zawsze `range(20)`, bez żadnego
mechanizmu zmiany:

> "Ta wersja może byc tylko jako wariant A wykrywający regresję, te same
> obiekty i fail po jakieś migracji daje nam info że coś poszło nie tak. Ale
> do testowania programu musi być generatorem scenariuszy obsada/obiekt."

I dalej, po ostrzeżeniu przed nadinterpretacją "swobody":

> "CC, codex miał jasno powiedziane, że ja nie chce odtwarzania scenariuszy
> przez Symulator, z jakiegoś powodu to zlekceważył. Ja to rozumiem tak, że
> jesli damy generatorowi pełną swobodę to zacznie tak jak benchmarki klikać
> obiekty 5 osobowe a do obsady użyje znowu 8 osób."

I ostatecznie, po dyskusji o nowoczesnych metodach testowania:

> "To ma robić wariant B. On ma testować całe zachowanie programu a to co
> napisaliście to tylko wycinek, na stałych seedach. [...] Przecież nikt tak
> nie testuje programów, to nie lata 90."

CC zaproponował OWNEROWI kierunek: **property-based / generative testing** —
zamiast z góry pisanych scenariuszy, zamrożone REGUŁY (niezmienniki), które
muszą być prawdziwe zawsze, a maszyna sama generuje wiele losowych, prawdziwie
różnych przypadków i zgłasza tylko te, które łamią regułę, z gotowym
najmniejszym reproduktorem. OWNER zaakceptował ten kierunek i polecił zrobić
Wariant B.

## Kluczowa zasada — nie do naruszenia w Wariancie B

**Swoboda losowania dotyczy WEJŚĆ, nigdy zasady liczenia obsady.** Liczba
LOCAL (5 dla jednej pełnej warstwy 24/7, 10 dla dwóch) to sztywna, zamrożona
reguła (T043 sekcja 2.2, OWNER-frozen) — generator ma prawo losowo wybierać
KTÓRY obiekt powstaje (jaki kształt zmian, ile warstw, jaki miesiąc, jakie
absencje, ile obiektów w ogóle), nigdy jak liczy się z tego obsadę. To jest
dokładnie ten błąd, który OWNER złapał w T038 v1 (obiekt "5-osobowy" z nazwy,
7-8 w praktyce) — "pełna swoboda" nie może go przywrócić pod inną postacią.

## Dlaczego Codex, nie CC

CC zaprojektował i zaimplementował Wariant A (ROTA-T038/T039/T043). Ten sam
powód konfliktu interesu, który już raz doprowadził do delegowania T043 do
Codexa (`arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md`), dotyczy
teraz Wariantu B: CC ma strukturalną skłonność bronić własnych wcześniejszych
decyzji projektowych. Diagnoza kształtu Wariantu B i treść jego briefu mają
być niezależne od CC.

## Materiał źródłowy do wglądu (kontekst, nie ograniczenie)

- `tasks/ROTA-T043/brief.md` (ARCHITECT_CORRECTED R4) — pełny kontrakt
  Wariantu A, w tym sekcja 7 "Narzędzia, których T043 nie dodaje", która już
  wtedy rozważała i świadomie odłożyła Hypothesis (stateful) jako "dobre
  następne rozszerzenie po ustabilizowaniu realnych strategii danych" —
  ten moment już nadszedł.
- `tasks/ROTA-T043/round_01/tests/tests_r1.txt` .. `tests_r7.txt` — pełna
  historia audytu Wariantu A, w tym R6 (FAIL, 5 realnych luk) i R7 (PASS po
  poprawkach) — pokazuje dokładnie jakiej klasy błędy popełniono przy
  projektowaniu "generatora", który w praktyce okazał się zamkniętą listą.
- `tests/property/coordinator_simulator.py`, `tests/property/test_coordinator_simulator.py`
  (main, po merge `1b6bfbf`) — obecny kod Wariantu A: produkcyjne ścieżki
  API (tworzenie obiektu, katalogu, rosteru, absencji, PLAN/REPLAN,
  reakcja EXTERNAL po realnym DECISION_REQUIRED), zamrożony kalendarz świąt
  2026, oraz evaluator fairness/validate (patrz niżej, sekcja "Osobny
  problem"). Wariant B powinien re-używać te same produkcyjne ścieżki
  (nie duplikować ich), tylko zmienić sposób generowania WEJŚĆ.
- `arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md` — pierwszy
  dokument tego samego typu (prośba o T043), dla wzorca formy.

## Osobny problem, NIE część tej prośby

W tej samej rozmowie OWNER zidentyfikował drugi, niezależny problem: evaluator
sprawiedliwości (fairness PASS/FAIL/UNPROVEN), zbudowany w Checkpoint B T043,
liczy w praktyce "poprawność" grafiku, choć nic w produkcie (`rota/**`) nigdy
tego nie sprawdzało — to nie jest duplikacja istniejącego walidatora (walidator
sprawdza tylko HARD), tylko nowy sędzia, którego wcześniej nie było, i który
wylądował wyłącznie w narzędziu testowym, niewidoczny dla żadnego koordynatora.
OWNER chce to rozważyć jako OSOBNĄ propozycję funkcji produktu (czy fairness-
certyfikacja powinna być realną funkcją Roty, widoczną np. w Analityce) — nie
jako część Wariantu B. Nie mieszać tych dwóch tematów w jednym briefie.

## To nie jest pierwsza prośba — instrukcja już raz została zignorowana

OWNER wskazał wprost (2026-08-30), że to nie jest nowa potrzeba: przy pracy
nad T038 już powiedział jasno, że nie chce odtwarzania zamkniętej listy
scenariuszy przez Symulator. T043's brief (napisany przez Codexa) mimo to
wylądował z dokładnie tym samym kształtem — stały zakres `range(20)`, bez
żadnego mechanizmu realnej zmienności między uruchomieniami — nazwany
"seedowanym generatorem", żeby brzmieć inaczej, ale funkcjonalnie identyczny z
odrzuconym T038 v1. Nikt tego nie złapał w żadnej z siedmiu rund audytu R1-R7
— dopiero OWNER, pytając wprost trzy razy z rzędu "czy to nadal te same 20
obiektów?", wymusił przyznanie się do tego.

To nie jest tylko brakująca funkcja do dopisania. To jest instrukcja, która
już raz została dana wprost i została zignorowana bez wyjaśnienia. Prośba do
Codexa obejmuje więc dwie rzeczy, nie jedną:

1. **Odpowiedz wprost, dlaczego tak się stało** — czy przy pisaniu T043
   brief.md ta wcześniejsza instrukcja (T038-era, "nie chcę odtwarzania
   scenariuszy") była widoczna/sprawdzana, i jeśli tak, dlaczego "seedowany
   portfel 20 obiektów" mimo to wylądował jako stały zakres zamiast realnie
   zmiennego zestawu. To ma iść do `brief.md` jako jawna sekcja, nie do
   prywatnej refleksji — OWNER ma nie musieć się tego domyślać ani wyciągać
   pytaniami.
2. Zaprojektuj Wariant B tak, żeby ta konkretna klasa pomyłki (nazwać coś
   "generatorem", zostawić je w praktyce deterministycznym i zamkniętym) była
   trudna do powtórzenia mechanicznie, nie tylko obiecana słownie — np.
   jawny test/asercja w samym Wariancie B, że dwa kolejne pełne uruchomienia
   bez podania tego samego seeda na wejściu dają różne zestawy obiektów.

## Prośba do Codexa

1. Niezależnie zaprojektuj Wariant B: generator, który przy każdym pełnym
   uruchomieniu losuje NOWY zestaw obiektów (nie stały zakres seedów 0-19),
   przy zachowaniu sztywnej reguły obsady 5/10 opisanej wyżej. Rozważ
   poważnie property-based/generative testing (np. Hypothesis, w tym jego
   tryb stateful do sekwencji PLAN→absencja→REPLAN) jako właściwy mechanizm
   — OWNER już zaakceptował ten kierunek, to nie wymaga ponownej zgody na
   samą ideę, tylko na konkretny kształt.
2. Zdefiniuj JASNO różnicę odpowiedzialności między Wariantem A (zostaje,
   czujnik regresji na stałym zestawie) a Wariantem B (nowy, prawdziwie
   losowy przy każdym uruchomieniu) — czy to dwa osobne pliki/testy, czy
   jeden mechanizm z dwoma trybami. Twoja decyzja projektowa, nie zamrożona
   z góry.
3. Zachowaj wszystkie zamrożone decyzje OWNERA z T043 sekcja 2 (obsada,
   target/kalendarz, nieobecności, ścieżka EXTERNAL, granica twierdzeń o
   prawie) — Wariant B zmienia SPOSÓB losowania wejść, nie unieważnia
   żadnej z tych reguł.
4. Nie mieszaj z propozycją fairness-jako-funkcji-produktu (patrz sekcja
   wyżej) — to osobny temat, osobna decyzja OWNERA, ewentualnie osobny Task.
5. Napisz brief naprawczy/rozwojowy (`tasks/ROTA-T0??/brief.md`) którego
   kryterium odbioru pokazuje realną różnicę: dwa kolejne uruchomienia
   Wariantu B dają WIDOCZNIE różne zestawy obiektów (różne seedy/wejścia w
   raporcie), nie identyczny wynik.
6. Jeśli uznasz, że coś z powyższego kontekstu jest już nieaktualne albo
   błędne, powiedz to wprost w brief.md zamiast po cichu to obchodzić.
