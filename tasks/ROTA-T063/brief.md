# ROTA-T063 — Referencyjne testy biznesowego grafiku

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@af7d5c6f15dbc424a24b9647e725085afa662284`

SOURCE: `arch/PREBRIEF_AUDIT_2026-09-10_T063_ACTIVE_E2E_MATRIX.md` + OWNER rulings 2026-09-10.

## 1. Cel

T063 ma zbudować małą, wiarygodną warstwę testów akceptacyjnych, które dowodzą rzeczywistego wyniku biznesowego programu.

Zielony test nie wystarcza dlatego, że:
- frontend kliknął PLAN,
- API odpowiedziało,
- solver zwrócił dowolny status,
- test użył sztucznie wygodnej obsady.

Dodatni test T063 ma kończyć się rzeczywistym, niepustym grafikiem D/N widocznym dla koordynatora. Test scenariusza wymagającego dalszej decyzji ma kończyć się dokładnie tym zachowaniem, które wynika z zamrożonego scenariusza operacyjnego — nie z dowolnej odpowiedzi programu.

T063 jest zadaniem testowym. Nie zmienia produktu, solvera, reguł planowania ani UI.

## 2. Najważniejsza zasada OWNERA — rzeczywistość nie może być wymyślona przez test

Dane kadrowe scenariusza są częścią kontraktu testu.

Fixture, helper, test, solver, fallback ani implementer nie mogą samodzielnie:
- zwiększyć liczby pracowników lokalnych,
- dodać wsparcia zewnętrznego,
- rozszerzyć okresu dostępności wsparcia,
- poluzować urlopu, chorobowego, DAY_ONLY, dostępności ani innych danych,
- zmienić zapotrzebowania obiektu,
- dobrać "wygodniejszej" obsady tylko po to, aby test przeszedł.

Jeżeli scenariusz mówi „5 LOCAL”, test ma dokładnie 5 LOCAL. Jeżeli scenariusz dopuszcza 1 osobę wsparcia zewnętrznego w konkretnym zakresie, test może użyć tylko tego zakresu. Żadna zgoda na wsparcie zewnętrzne nie oznacza zgody na dowolną liczbę osób lub dowolny czas.

## 3. External support — jawnie ograniczony zasób, nie nieskończony fallback

Niedobór lokalnej obsady nie oznacza z definicji, że poprawnym wynikiem jest zatrzymanie planowania. W rzeczywistym procesie koordynator może być zobowiązany do znalezienia wsparcia zewnętrznego.

Dlatego każdy scenariusz, w którym external support może wystąpić, musi jawnie określić jego granice. Co najmniej:
- czy wsparcie jest dostępne,
- maksymalną liczbę dostępnych osób zewnętrznych,
- okres/datę lub zakres służb, dla których wsparcie jest dopuszczone,
- inne istotne ograniczenia, jeżeli występują w realnym przypadku.

Brak któregoś z tych ustaleń nie daje implementerowi prawa do ich wymyślenia.

Jeżeli zamrożony limit wsparcia wystarcza, oczekiwaniem scenariusza może być pełny grafik. Jeżeli nie wystarcza, oczekiwane zachowanie musi wynikać z osobnej jawnej decyzji OWNERA dla tego scenariusza. Nie wolno z góry przyjmować „za mało LOCAL = PLAN musi stanąć”.

## 4. SCENARIO_PACK jest normatywnym wejściem do implementacji

Przed rozpoczęciem implementacji T063 musi istnieć OWNER-zatwierdzony `SCENARIO_PACK` z konkretnymi danymi operacyjnymi.

CC nie projektuje scenariuszy. CC odwzorowuje je 1:1 w fixture/testach.

`SCENARIO_PACK` dla każdego przypadku musi określać co najmniej:
1. miesiąc i obiekt,
2. katalog wymaganych zmian/służb,
3. dokładną liczbę i role pracowników LOCAL,
4. indywidualne ograniczenia istotne dla scenariusza (np. DAY_ONLY),
5. urlopy/chorobowe/dostępność, jeśli występują,
6. external support: dokładny limit i zakres albo jawne `NONE`,
7. operację użytkownika: PLAN / późniejszy REPLAN / inna już istniejąca operacja,
8. oczekiwany wynik biznesowy,
9. artefakty dowodowe, które mają zostać zachowane.

Jeżeli czegoś o rzeczywistym scenariuszu nie wiadomo, implementacja tego scenariusza pozostaje HOLD i wraca do OWNERA z jednym precyzyjnym pytaniem. Nie uzupełniać braków „rozsądnymi założeniami”.

## 5. Minimalna macierz T063

T063 nie ma generować dziesiątek losowych przypadków. Pierwsza wersja ma zawierać mały zestaw referencyjnych scenariuszy o wysokiej wartości dowodowej.

### A. Realny dodatni D/N

OWNER dostarcza ścisły scenariusz realnego obiektu całodobowego D/N z realną obsadą i, jeżeli potrzebne, jawnie ograniczonym external support.

Acceptance:
- test przechodzi przez normalne operacje koordynatora,
- uruchamia prawdziwy PLAN i prawdziwy solver,
- wynik jest z góry określony jako biznesowo dodatni,
- powstaje niepusty grafik,
- wymagane D/N są faktycznie obsadzone zgodnie z kontraktem scenariusza,
- grafik zostaje wybrany/zapisany zgodnie z aktualnym lifecycle,
- po odświeżeniu nadal jest widoczny,
- koordynator widzi realne assignmenty, nie tylko status API,
- zapisany zostaje screenshot grafiku i PDF do oceny optycznej.

### B. Realny scenariusz z ograniczonym wsparciem zewnętrznym

OWNER dostarcza przypadek, w którym lokalna obsada sama nie wystarcza lub jest na granicy, a realny proces dopuszcza określone wsparcie zewnętrzne.

Acceptance:
- fixture nie tworzy żadnego external support poza limitem scenariusza,
- solver nie może traktować zgody jako otwartego poolu,
- test sprawdza dokładnie oczekiwany wynik biznesowy dla podanego limitu,
- raport testu pokazuje, ile wsparcia było dostępne i ile faktycznie wykorzystano.

### C. Co najmniej jeden realny ruch kadrowy

Po bazowym grafiku OWNER dostarcza realny przypadek zmiany: np. urlop, choroba, zmiana dostępności albo inny rzeczywiście występujący ruch kadrowy.

Acceptance:
- stan przed zmianą jest rzeczywistym zapisanym grafikiem z wcześniejszego scenariusza albo jawnie zdefiniowanym stanem wejściowym,
- zmiana danych jest dokładnie taka, jak w `SCENARIO_PACK`,
- nie wolno ratować scenariusza dodatkową obsadą poza kontraktem,
- wynik końcowy musi być biznesowo jednoznaczny: nowy prawidłowy grafik albo dokładnie ustalona potrzeba dalszej decyzji.

Dalsze scenariusze mogą być dopisywane tylko po zatwierdzeniu danych przez OWNERA. Liczba testów nie jest celem samym w sobie; celem jest wiarygodność rzeczywistości, którą reprezentują.

## 6. Zakaz fałszywych pozytywów

Test T063 nie może uznać się za PASS, gdy:
- PLAN ma zerowe zapotrzebowanie,
- oczekiwane są alternatywne przeciwne wyniki typu `FEASIBLE lub DECISION_REQUIRED`,
- utworzono pusty ScheduleVersion,
- solver nie był uruchomiony,
- dane kadrowe zostały rozszerzone poza `SCENARIO_PACK`,
- test użył dodatkowego external support bez jawnego limitu OWNERA,
- UI tylko powtórzył odpowiedź API, ale nie powstał biznesowy rezultat scenariusza,
- retry Playwright przykrył deterministycznie zły wynik produktu.

## 7. Izolacja

Każdy referencyjny scenariusz zaczyna się od czystej dedykowanej bazy albo równoważnie pełnej izolacji.

Test nie może pozostawiać globalnych triggerów, nieskopowanych UPDATE ani danych wpływających na kolejny scenariusz. Retry infrastrukturalny nie zmienia oczekiwanego wyniku biznesowego i musi być odróżniony od PASS produktu.

## 8. Relacja do istniejących testów

Małe testy jednostkowe, integracyjne i UI pozostają potrzebne. T063 nie zastępuje ich i nie wymaga ich usuwania.

Jednocześnie:
- test bez realnego zapotrzebowania nie jest dowodem ułożenia grafiku,
- test jednej kontrolnej zmiany może pozostać testem mechaniki, ale nie zastępuje referencyjnego D/N,
- T043 ma zostać poprawiony albo przeklasyfikowany tak, aby nie udawał dowodu biznesowego, jeśli nim nie jest.

Zamrożone Symulatory A/B i stare benchmarki pozostają poza zakresem i nie mogą wrócić tylnymi drzwiami jako generator „realistycznej” obsady.

## 9. Zależności

T062 dostarcza docelowe zachowanie/guidance dla kontrolowanego zatrzymania planowania; T063 nie projektuje go ponownie.

T064 dotyczy prawdziwego wyboru/generowania miesiąca. T063 nie może maskować jego braku przez podrobienie daty. Scenariusze, których nie da się uczciwie wykonać przed T064, pozostają wykonawczo HOLD do T064. Scenariusze niewymagające tej naprawy nie są blokowane tylko dlatego, że T064 istnieje.

## 10. Artefakty dowodowe

Każdy referencyjny scenariusz kończący się grafikiem ma zachować co najmniej:
- identyfikator/nazwę scenariusza i wersję `SCENARIO_PACK`,
- użyte dane kadrowe w formie możliwej do audytu,
- wynik PLAN/REPLAN,
- screenshot widocznego grafiku,
- PDF wygenerowanego grafiku,
- informację o faktycznie wykorzystanym external support.

Artefakty służą do oceny przez człowieka. Automat nie ma udawać, że rozumie operacyjną jakość grafiku poza asercjami literalnie zamrożonymi w scenariuszu.

## 11. Acceptance T063

T63-01 — Istnieje jawny OWNER-zatwierdzony `SCENARIO_PACK`; implementer nie tworzy własnej obsady.

T63-02 — Fixture/test nie może zwiększyć LOCAL ani external support ponad kontrakt scenariusza.

T63-03 — External support ma jawny limit i zakres; nigdy nie jest nieograniczonym fallbackiem.

T63-04 — Co najmniej jeden referencyjny dodatni scenariusz kończy się realnym, niepustym D/N widocznym w UI po reloadzie.

T63-05 — Co najmniej jeden referencyjny scenariusz sprawdza realne użycie ograniczonego external support.

T63-06 — Co najmniej jeden referencyjny scenariusz obejmuje realny ruch kadrowy po/bądź podczas planowania, z jednoznacznym oczekiwaniem biznesowym.

T63-07 — Żaden referencyjny acceptance nie akceptuje przeciwstawnych statusów jako równoważnego PASS.

T63-08 — Brak zapotrzebowania/pusty plan nie może być klasyfikowany jako dowód biznesowego grafiku.

T63-09 — Każdy scenariusz ma pełną izolację danych.

T63-10 — Dodatni scenariusz zapisuje screenshot i PDF do oceny człowieka.

T63-11 — T063 nie zmienia kodu produkcyjnego, solvera ani reguł biznesowych w celu dopasowania produktu do testu.

T63-12 — Odkryty błąd produktu powoduje FAIL/finding, a nie zmianę scenariusza, zwiększenie obsady lub poluzowanie oczekiwania.

## 12. Preimplementation audit Codexa

IMPLEMENTATION HOLD.

Codex ma sfalsyfikować wyłącznie kontrakt testowy i odpowiedzieć:
1. Czy obecna infrastruktura E2E pozwala wymusić literalne dane z `SCENARIO_PACK` bez ukrytych helperów dodających obsadę lub external support?
2. Gdzie obecnie istnieją helpery/fixture, które mogą cicho rozszerzać staffing albo zmieniać dane między uruchomieniami?
3. Jak najprościej zagwarantować czystą bazę/izolację dla każdego referencyjnego scenariusza?
4. Jakie istniejące testy należy przeklasyfikować jako mechaniczne zamiast acceptance, bez ich zbędnego przepisywania?
5. Czy artefakty screenshot/PDF mogą być deterministycznie zapisane dla każdego dodatniego scenariusza bez zmian produktu?
6. Czy którykolwiek punkt briefu wymaga zmiany produkcji zamiast samego test harnessu? Jeśli tak — FAIL zakresu i osobny finding.

Codex NIE ma projektować konkretnych danych kadrowych scenariuszy. Brak konkretnego `SCENARIO_PACK` jest celowym IMPLEMENTATION HOLD, nie luką do wypełnienia przez model.
