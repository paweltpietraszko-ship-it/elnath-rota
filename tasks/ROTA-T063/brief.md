# ROTA-T063 — Referencyjne testy biznesowego grafiku

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@af7d5c6f15dbc424a24b9647e725085afa662284`

SOURCE: `arch/PREBRIEF_AUDIT_2026-09-10_T063_ACTIVE_E2E_MATRIX.md` + OWNER rulings 2026-09-10.

## 1. Cel

T063 ma zbudować małą, wiarygodną warstwę testów akceptacyjnych, które dowodzą rzeczywistego wyniku biznesowego programu.

Zielony test nie wystarcza dlatego, że frontend kliknął PLAN, API odpowiedziało albo solver zwrócił dowolny status. Test ma dowodzić z góry określonego rezultatu biznesowego na z góry określonych danych.

T063 jest zadaniem testowym. Nie zmienia produktu, solvera, reguł planowania ani UI.

## 2. Zasada nadrzędna — test nie symuluje rzeczywistości, której nie zna

Dane kadrowe scenariusza są częścią kontraktu testu.

Fixture, helper, test, solver, fallback ani implementer nie mogą samodzielnie:
- zwiększyć liczby pracowników lokalnych,
- dodać wsparcia zewnętrznego,
- rozszerzyć okresu dostępności wsparcia,
- poluzować urlopu, chorobowego, DAY_ONLY, dostępności ani innych danych,
- zmienić zapotrzebowania obiektu,
- dobrać wygodniejszej obsady tylko po to, aby test przeszedł.

Jeżeli scenariusz mówi `5 LOCAL`, test ma dokładnie `5 LOCAL`.

T063 NIE buduje kolejnego Symulatora. Automat testowy nie ocenia, co jest rozsądne dla koordynatora i nie improwizuje jego decyzji. Jeżeli scenariusz zawiera decyzję człowieka, automat może wyłącznie odtworzyć literalną, wcześniej zamrożoną odpowiedź z `SCENARIO_PACK`.

## 3. External support — ostatnia droga ratunku, ale nie automatyczny fallback

W realnym procesie niedobór lokalnej obsady nie oznacza automatycznie końca planowania. Jeżeli bez wsparcia zewnętrznego nie da się zbudować grafiku, koordynator musi takie wsparcie znaleźć.

Jednocześnie external support nie jest równorzędnym pierwszym wyborem i nie może być użyty przedwcześnie, jeżeli istnieje inna dozwolona ścieżka rozwiązania rozpoznana przez produkt.

T063 nie próbuje jednak automatycznie dowodzić ogólnej „mądrości” tej hierarchii. Może sprawdzić kolejność tylko tam, gdzie `SCENARIO_PACK` jawnie zamraża oczekiwany krok dla konkretnego stanu.

W jednym wybranym scenariuszu wsparcia zewnętrznego sterownik testu może odgrywać koordynatora i przez zwykłe operacje produktu dodać syntetyczne osoby external. Ten scenariusz musi osobno sprawdzić:
- wariant z jedną osobą wsparcia,
- wariant z kilkoma osobami wsparcia.

To NIE jest ogólny mechanizm ratowania testów. Pozostałe scenariusze nie mogą automatycznie dopisywać ludzi.

Solver może użyć wyłącznie osób istniejących przed danym uruchomieniem PLAN/REPLAN. Nie dostaje helpera tworzenia pracowników. Każda osoba external podlega tym samym właściwym ograniczeniom co inni pracownicy, w tym odpoczynkowi i dostępności.

Nieznany employee albo ręcznie zbudowany Assignment spoza zwykłych operacji produktu oznacza FAIL testu.

## 4. SCENARIO_PACK jest normatywnym wejściem do implementacji

Przed rozpoczęciem implementacji T063 musi istnieć OWNER-zatwierdzony `SCENARIO_PACK` z konkretnymi danymi operacyjnymi.

CC nie projektuje scenariuszy. CC odwzorowuje je 1:1 w fixture/testach.

Każdy scenariusz musi określać co najmniej:
1. miesiąc i obiekt,
2. katalog wymaganych zmian/służb,
3. dokładną liczbę i role pracowników LOCAL,
4. indywidualne ograniczenia istotne dla scenariusza,
5. urlopy/chorobowe/dostępność lub ich brak,
6. external support: dokładny stan wejściowy i — jeżeli scenariusz przewiduje jego dodanie — dokładną liczbę/zakres po jawnej decyzji koordynatora,
7. kolejne operacje użytkownika,
8. każdą wymaganą decyzję koordynatora jako literalne `YES/NO` albo konkretną akcję,
9. oczekiwany wynik po każdym istotnym kroku,
10. oczekiwany wynik końcowy,
11. artefakty dowodowe.

Jeżeli czegoś o rzeczywistym scenariuszu nie wiadomo, implementacja tego scenariusza pozostaje HOLD i wraca do OWNERA. Nie uzupełniać braków „rozsądnymi założeniami”.

## 5. Co test może mierzyć wiarygodnie

T063 może automatycznie sprawdzać tylko rzeczy obserwowalne i wcześniej zamrożone:
- dokładny stan wejściowy,
- dokładny wynik PLAN/REPLAN,
- czy powstał lub nie powstał ScheduleVersion/current zgodnie ze scenariuszem,
- czy powstały konkretne służby i assignmenty,
- czy program wystawił określoną kategorię decyzji/działania, jeżeli scenariusz tego oczekuje,
- czy nie wystawił niedozwolonego/przedwczesnego działania, jeżeli scenariusz jawnie to zabrania,
- czy po literalnej decyzji koordynatora następny krok zachował oczekiwane zachowanie,
- czy użyto wyłącznie osób obecnych w danym stanie wejściowym,
- ile external support było dostępne i faktycznie użyte,
- czy końcowy grafik jest widoczny po reloadzie i eksportowalny do PDF.

T063 nie ma automatycznie oceniać:
- czy sugestia solvera jest „rozsądna” w sensie ogólnym,
- czy tekst komunikatu jest wystarczająco czytelny dla człowieka,
- czy grafik jest operacyjnie elegancki poza literalnymi asercjami scenariusza.

Te elementy pozostają do oceny człowieka przez screenshot, treść komunikatu i PDF.

## 6. Minimalna macierz referencyjna

### A. Realny dodatni D/N

Ścisły scenariusz obiektu całodobowego D/N z realną obsadą.

Acceptance:
- normalne operacje koordynatora,
- prawdziwy PLAN i prawdziwy solver,
- z góry oczekiwany `FEASIBLE`,
- niepusty pełny grafik,
- wymagane D/N faktycznie obsadzone,
- wynik zapisany zgodnie z lifecycle,
- reload zachowuje grafik,
- UI pokazuje rzeczywiste assignmenty,
- zapisany screenshot i PDF.

### B. Jeden kontrolowany scenariusz external support

Scenariusz musi zawierać dokładny stan bez wsparcia oraz oczekiwany wynik tego stanu. Jeżeli zamrożony scenariusz mówi, że program powinien najpierw zatrzymać się po konkretną decyzję koordynatora, test sprawdza właśnie to i nie dodaje jeszcze external.

Następnie sterownik testu może odtworzyć literalną decyzję koordynatora i dodać dokładnie zamrożoną liczbę osób przez normalne operacje produktu.

Wariant 1: dokładnie jedna osoba external.

Wariant 2: dokładnie kilka osób external.

Dla obu wariantów `SCENARIO_PACK` zamraża wynik. Jeżeli wpisany zestaw osób wystarcza, oczekiwaniem jest pełny grafik. Test nie może zwiększać wsparcia aż do uzyskania PASS.

### C. Realny ruch kadrowy / absencja

Co najmniej jeden przypadek obejmujący zwykłą rzeczywistość obiektu: urlop, chorobę albo nagłą absencję.

Scenariusz określa stan przed zmianą, samą zmianę i oczekiwany następny krok. Jeżeli program ma zatrzymać się po decyzję koordynatora, test sprawdza dokładnie tę decyzję jako poprawny wynik pośredni.

Dalsze przejście jest dozwolone tylko wtedy, gdy `SCENARIO_PACK` zawiera literalną odpowiedź koordynatora. Automat nie wybiera odpowiedzi sam.

## 7. Zakaz fałszywych pozytywów

Test T063 nie może uznać się za PASS, gdy:
- PLAN ma zerowe zapotrzebowanie,
- akceptowane są przeciwne wyniki typu `FEASIBLE lub DECISION_REQUIRED`,
- utworzono pusty ScheduleVersion,
- solver nie był uruchomiony,
- dane kadrowe zostały rozszerzone poza `SCENARIO_PACK`,
- external support został dodany automatycznie poza jednym zamrożonym scenariuszem,
- sterownik testu improwizował decyzję koordynatora,
- UI tylko powtórzył status API bez oczekiwanego rezultatu biznesowego,
- retry Playwright przykrył deterministycznie zły wynik produktu.

Jeżeli w scenariuszu istnieje oczekiwany etap `DECISION_REQUIRED`/guidance, PASS wymaga zgodności tego etapu z kontraktem scenariusza. Sam fakt, że końcowy PDF wygląda poprawnie, nie wystarcza, jeżeli program doszedł do niego przez jawnie niedozwolony krok.

## 8. Izolacja

Każdy referencyjny scenariusz zaczyna się od czystej dedykowanej bazy albo równoważnie pełnej izolacji.

Test nie może pozostawiać globalnych triggerów, nieskopowanych UPDATE ani danych wpływających na kolejny scenariusz. Retry infrastrukturalny nie zmienia oczekiwanego wyniku biznesowego i musi być odróżniony od PASS produktu.

## 9. Relacja do istniejących testów

Małe testy jednostkowe, integracyjne i UI pozostają potrzebne. T063 ich nie zastępuje.

Jednocześnie:
- test bez realnego zapotrzebowania nie jest dowodem ułożenia grafiku,
- test jednej kontrolnej zmiany może pozostać testem mechaniki, ale nie zastępuje referencyjnego D/N,
- T043 ma zostać poprawiony albo przeklasyfikowany,
- zamrożone Symulatory A/B i stare benchmarki pozostają poza zakresem i nie mogą wrócić jako generator „realistycznej” obsady.

## 10. Zależności

T062 dostarcza docelowe guidance dla kontrolowanego zatrzymania planowania. T063 może je sprawdzać tylko w zakresie literalnie wymaganym przez `SCENARIO_PACK`; nie projektuje tej logiki ponownie.

T064 dotyczy prawdziwego wyboru/generowania miesiąca. T063 nie może maskować jego braku przez podrobienie daty. Scenariusze wymagające T064 pozostają wykonawczo HOLD do T064; pozostałe nie są automatycznie blokowane.

## 11. Artefakty dowodowe

Każdy referencyjny przebieg zachowuje:
- nazwę scenariusza i wersję `SCENARIO_PACK`,
- wejściowe dane kadrowe,
- sekwencję rzeczywistych kroków i wyników programu,
- decyzje koordynatora odtworzone przez test, jeżeli występują,
- wynik PLAN/REPLAN,
- faktycznie wykorzystany external support,
- screenshot istotnego guidance, jeżeli scenariusz obejmuje decyzję,
- screenshot końcowego grafiku, jeżeli powstał,
- PDF końcowego grafiku, jeżeli powstał.

Artefakty służą do oceny przez człowieka. Automat nie udaje, że rozumie operacyjną jakość grafiku poza literalnymi asercjami.

## 12. Acceptance T063

T63-01 — Istnieje OWNER-zatwierdzony `SCENARIO_PACK`; implementer nie tworzy własnej rzeczywistości kadrowej.

T63-02 — Fixture/test nie zwiększa LOCAL ani external poza dokładny kontrakt scenariusza.

T63-03 — T063 nie tworzy uniwersalnego symulatora koordynatora ani fallbacku dobierającego ludzi do skutku.

T63-04 — Co najmniej jeden referencyjny dodatni scenariusz kończy się pełnym, niepustym D/N widocznym po reloadzie i w PDF.

T63-05 — Dokładnie jeden referencyjny scenariusz external support odgrywa koordynatora i osobno sprawdza wariant jednej oraz kilku osób external.

T63-06 — Co najmniej jeden scenariusz obejmuje realny ruch kadrowy/absencję.

T63-07 — Jeżeli scenariusz oczekuje decyzji koordynatora, automat może iść dalej tylko przez literalnie zamrożoną odpowiedź; nie interpretuje sytuacji sam.

T63-08 — Scenariusz może wymagać sprawdzenia, że konkretna akcja nie została zaproponowana przedwcześnie, ale tylko gdy ta kolejność jest jawnie wpisana w `SCENARIO_PACK`.

T63-09 — Żaden referencyjny acceptance nie akceptuje przeciwstawnych statusów jako równoważnego PASS.

T63-10 — Brak zapotrzebowania/pusty plan nie jest dowodem biznesowego grafiku.

T63-11 — Każdy scenariusz ma pełną izolację danych.

T63-12 — Dodatni scenariusz zapisuje screenshot i PDF; scenariusz decyzyjny zapisuje także dowód istotnego guidance.

T63-13 — T063 nie zmienia kodu produkcyjnego, solvera ani reguł biznesowych w celu dopasowania produktu do testu.

T63-14 — Odkryty błąd produktu powoduje FAIL/finding, a nie zmianę scenariusza, zwiększenie obsady lub poluzowanie oczekiwania.

## 13. Preimplementation audit Codexa

IMPLEMENTATION HOLD.

Codex ma sfalsyfikować wyłącznie kontrakt testowy i odpowiedzieć:
1. Czy obecna infrastruktura E2E pozwala wymusić literalne dane z `SCENARIO_PACK` bez ukrytych helperów dodających obsadę/external?
2. Jak zagwarantować, że tylko jeden wskazany scenariusz może jawnie tworzyć external przez normalne operacje produktu?
3. Jak najprościej zagwarantować czystą bazę/izolację dla każdego przebiegu?
4. Czy można obserwować i asertywnie sprawdzić oczekiwany krok decyzyjny bez budowania nowego symulatora logiki koordynatora?
5. Czy screenshot guidance oraz screenshot/PDF końcowego grafiku mogą być deterministycznie zachowane bez zmian produktu?
6. Czy którykolwiek punkt briefu wymaga zmiany produkcji zamiast samego test harnessu? Jeśli tak — FAIL zakresu i osobny finding.

Codex NIE projektuje konkretnych danych kadrowych scenariuszy. Brak konkretnego `SCENARIO_PACK` jest celowym IMPLEMENTATION HOLD, nie luką do wypełnienia przez model.
