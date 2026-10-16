# ROTA-CLOUD-REVIEW-FIXES — poprawki po przeglądzie chmurowym

STATUS: READY FOR INDEPENDENT PREIMPLEMENTATION CHECK; IMPLEMENTATION HOLD.
DATA: 2026-10-16.
BASE_SHA: 1fcc8f86d1030534e6dd81a96f91607aa2eb21bf (main).
BRANCH: codex/rota-cloud-review-fixes.

## 1. Cel i źródła

Jeden zatwierdzony blok: F1–F7, przygotowanie migracji konfiguracji Railway
oraz naprawa odłożonych, nieaktualnych testów. Bez implementacji w tym briefie.

Źródła PRODUCT_TRUTH:
- `arch/spec.md`, obowiązujące kontrakty T009, T010 część D (NN), T024,
  T032, T058, ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT oraz
  ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS; nowe decyzje poniżej mają pierwszeństwo
  wyłącznie w opisanym zakresie.
- OWNER_ACCEPTED 2026-10-16: jeden blok poprawek wskazany w przekazaniu
  ROTA-CLOUD-REVIEW-FIXES; przeniesione tu decyzje właściciela z tego przekazania
  i doprecyzowania z rozmowy przygotowującej ten brief.

Dowody problemów, nie źródło nowych wymagań:
- `arch/FINDING_2026-10_CLOUD_CODE_REVIEW.md` na
  `review/cloud-2026-10@14aa586156b7c5068435717f1436bac8c9fcf411`;
  przegląd dotyczył `4f0ed0d7862f718ae15ecb6fca784364c083f7a3`.
- `ODLOZONE.md`, wyłącznie sekcja z 2026-09-24 o 34 stabilnych porażkach;
  `arch/FINDING_2026-09-24_TEST_SUITE_34_STABLE_FAILURES.md` jako historyczny pomiar.
- Railway: https://docs.railway.com/infrastructure-as-code — sprawdzone
  2026-10-16: wycofanie CaC 2026-12-01, zastępuje je IaC zarządzane przez CLI.

## 2. Zamrożone decyzje OWNERA

O1. Noc przy zmianie czasu pozostaje w grafiku 12-godzinna. Dosłownie:
„W grafiku wstawiamy normalnie 12h, do wynagrodzenia jest liczone 13 h, ale my
nie mamy programu kadrowego tylko grafik, więc ustalamy 12h.” Nie zmieniać
arytmetyki długości służby, godzin salda ani odpoczynku na czas upływający UTC.

O2. Pierwszy grafik od daty w środku miesiąca nie planuje wcześniejszych dni.
Dosłownie: „Jeśli ustalam grafik od 10 października to nie ustalam zmian na dni
do 10 bo to bez sensu.” Granica w kontrakcie: 10 października włącznie;
wykluczone są dni 1–9. Dotyczy pierwszego PLAN i pierwszej akceptacji, nie
kasowania historii rodzica późniejszych wersji.

O3. „Hasło min 8 znaków. Inne wymagania wprowadź jeśli uważasz to za konieczne,
bo aplikacja będzie docelowo chmurowa.” W tym bloku: minimum 8 znaków,
obecne hasło wymagane przy samodzielnej zmianie, wspólna walidacja długości
przy tworzeniu/resetowaniu/zmianie hasła przez obecny UserManager.
Nie dokładamy wymogu cyfr, wielkich liter ani znaków specjalnych.

O4. „Wg mnie wszystkie naruszenia trzeba komunikować koordynatorowi lepiej za
dużo niz za mało.” Dotyczy wszystkich naruszeń zwracanych przez obecną
walidację aktualnego grafiku, niezależnie od kategorii i przyczyny, a nie
wyłącznie L4/urlopu/niedostępności. Zachować również istniejące ostrzeżenia.

O5. Po przedstawieniu opcji ręcznego zapisu trzeciej nocki z naruszeniem,
potwierdzeniem przed finalizacją i wydrukiem OWNER wybrał TAK:
„Tak, koordynator ma wszelkie prawa łamać zasady bo to jego odpowiedzialność,
Rota sama zasad nie łamie zasady przestrzega a decyzje Koordynatora zapisuje
w pamięci.” Automat przestrzega reguł; świadoma ręczna korekta może je
naruszać, zapisując Deviation i istniejący ślad CoordinatorAction.
W zakresie F1 NIGHT-STREAK-01 otrzymuje istniejącą kategorię LAW i polską
etykietę; podlega istniejącym potwierdzeniom LAW. To jawne doprecyzowanie
T032 dla ręcznej korekty, bez osłabienia reguły automatycznego planowania.
„Pamięć” oznacza istniejącą pamięć decyzji obiektu, bez nowego magazynu.

## 3. Kontrakt zmian i istniejący owner

### F6 — komunikacja bieżących naruszeń (priorytet)

Wyzwalacz: otwarcie/odświeżenie miesiąca z bieżącą wersją grafiku, również
FINAL. Używane dane: aktualny snapshot i bieżące dane wejściowe, z których
`open_month.open_month` już składa stan i wywołuje `validate`.

Nie wyrzucać `report.violation_details`. Przenieść pełną listę jako wynik
odczytu `OpenMonthView` do obecnego routera miesiąca. Wąski formatter
`api/schedule_validation_messages.py` zamienia strukturalne referencje
naruszenia na polski opis i trafia do istniejącego `MonthViewOut.warnings`.
Obecny banner `month-warnings` w MonthlyPlanning jest powierzchnią prezentacji;
bez nowego panelu, endpointu, trwałych odchyleń tworzonych przez GET ani
drugiego wywołania walidatora dla tej samej prezentacji.

Każdy wykryty fakt musi być widoczny: nazwa reguły/przyczyna po polsku,
osoba/osoby i daty lub okres, jeżeli naruszenie je wskazuje; dla braku obsady
data/godziny nieobsadzonej zmiany. Dane prezentacyjne pobierać ze wskazanych
Assignment/Demand/Employee i istniejących reguł obiektu. Nie parsować
angielskiego `message` jako źródła relacji. Nie pokazywać surowych UUID,
DEV/SV, kodów reguł ani angielskiego komunikatu jako wyjaśnienia.
Formatter obsługuje wszystkie obecne źródła violation, w tym reguły obiektu;
nie może pomijać nieznanego przypadku ani przedstawiać błędu odczytu jako
braku naruszeń. Przy niepełnej referencji pokazuje czytelną informację
o wykrytym problemie i braku części szczegółów, bez wymyślania osoby/daty.

Przykład: po zapisaniu L4 dla osoby ze zmianą 28.10, ponowne otwarcie grafiku
pokazuje jej nazwę, 28.10 i konflikt ze zwolnieniem lekarskim. Nie dopiero
przy PDF. Po usunięciu konfliktu i odświeżeniu aktualny komunikat znika.
To samo dla innych wykrytych naruszeń; nie rozszerzamy reguł walidatora ani
nie znosimy jego dotychczasowych wyłączeń, np. faktów REALIZED.

Odczyt niczego nie zapisuje, nie uznaje naruszenia za potwierdzone i nie
przelicza grafiku. Istniejące ręczne poprawki, Przelicz, finalizacja i eksport
zachowują własne bramki i ślad decyzji. Błąd walidacji/odczytu jest jawny
w istniejącej obsłudze błędów; odświeżenie ponawia odczyt.

### F5 — polska strefa zegara serwera

Owner: konfiguracja procesu w runtime `Dockerfile`, dokumentacja wdrożenia.
Zainstalować dane stref i ustawić `TZ=Europe/Warsaw`, aby obecne naiwne
`datetime.now()`/`date.today()` oznaczały polski czas ścienny. Udokumentować
sprawdzenie ewentualnej nadpisującej zmiennej na Railway. Bez masowej
konwersji datetime, migracji istniejących zapisów i nowego subsystemu zegara.

O 06:30 w Polsce służba od 06:00 jest rozpoczęta; istniejące zabezpieczenia
ręcznej korekty/Przelicz traktują ją tak samo jak na lokalnym polskim zegarze.
O 00:30 domyślne „Obowiązuje od” wskazuje bieżącą polską datę. Sprawdzić
zimę i lato. O1 obowiązuje także po ustawieniu strefy.
Nie wysyła nowych danych; awaria konfiguracji wymaga poprawy konfiguracji
i ponownego uruchomienia procesu, bez poprawiania zapisanych grafików.

### F3 — historyczne NN w PDF i Excelu

Owner: `manual_edit.mark_not_worked`, obecny zapis wersji potomnej.
Przy NN domyślne `effective_from` wyznaczać z daty rozpoczęcia wskazanej
służby w snapshotcie rodzica, zamiast dzisiejszej daty. Router nadal nie
wymaga od człowieka ani klienta samodzielnego podawania tej granicy.
Jawna data przekazywana przez istniejący wewnętrzny interfejs nie może
przesunąć skutku NN za datę oznaczanej służby.

Pozostają: CANCELLED + NN w dziecku, oryginalny zapis w rodzicu, dotychczasowy
ślad decyzji i brak automatycznego REPLAN. Istniejące projekcje PDF/Excel
mają po ponownym eksporcie pokazać NN i prawidłowe WYK dla tamtego dnia,
zgodne z ekranem/saldem. Nie naprawiać tego drugim filtrem w eksporterze.
Odmowa nielegalnego NN i atomowość zapisu zachowują obecne zachowanie.
Nie wykonywać zbiorczej migracji dawnych korekt w bazach.

### F1 — świadoma trzecia nocka, bez błędu 500

Owner: `deviation_mapping._BUILTIN_RULE_CATEGORY` i etykieta w routerze
schedule. Dodać NIGHT-STREAK-01 → LAW oraz polską etykietę „trzecia nocka
pod rząd”. Istniejące `apply_manual_correction -> validate ->
materialize_deviations -> zapis wersji i CoordinatorAction` zapisuje ręczny
wyjątek wraz z faktami decyzji; nie przechwytujemy UnknownDeviationSource
ogólnym fallbackiem i nie usuwamy naruszenia z walidatora.

Przy N/N/N koordynator widzi naruszenie po zapisie, może je potwierdzić
w istniejącym lifecycle i przy wydruku. Zasady potwierdzania LAW pozostają
w obecnych ownerach, bez nowego mechanizmu zgody. Współistnienie z
THIRD-CONSECUTIVE-SHIFT-01 nie znosi żadnej z reguł ani ochrony zapisanej
ręcznej decyzji, którą już zapewnia T058. Automat nie dostaje prawa
samodzielnego utworzenia trzeciej nocki. Błąd zapisu nie pozostawia częściowej
wersji ani częściowego śladu decyzji.

### F2 — właściwe okno historii NIGHT-STREAK-01

Owner: `validator_checks_patterns._check_night_streak`; granica odniesienia
to produkcyjne `constraints.add_max_two_consecutive_night_constraints`.
Ograniczyć sprawdzane trzydniowe okna i boundary facts do okien tej reguły
dla badanego miesiąca, zgodnie z istniejącym solverem. Stara trójka nocek
całkowicie poza tym zakresem nie powoduje naruszenia ani TECHNICAL_ERROR
w badanym miesiącu. Prawdziwa trójka obejmująca jego początek nadal jest
wykrywana. Nie obcinać wspólnego `assembler._context_window`, bo historia
służy również innym regułom; bez zmiany solvera i pozostałych checków.

Dowód używa historii tego samego obiektu utworzonej legalną ręczną decyzją
po F1; nie zakłada przenikania niezależnych danych syntetycznych.

### F4 — pierwszy PLAN od wybranego dnia

Owner: `plan_ops.plan_month` (brak current) i `select_candidate` (pierwsza
akceptacja), reuse istniejącego preview z `effective_from` i `shift_demands`.
Przy pierwszym PLAN od 10.10 automat planuje wyłącznie służby rozpoczynające
się 10.10 lub później. Przed solverem ograniczyć zapotrzebowanie tego pierwszego
planu; ten sam zakres musi przejść przez preview, walidację akceptacji
i pierwszy trwały snapshot. Nie wystarczy schować dni na ekranie/wydruku.
Akceptacja nie odtwarza ponownie pełnomiesięcznych demands pomijających tę
granicę. Web i Excel korzystają z tej samej ścieżki application.

W dniach 1–9 nie ma assignments, nie nalicza się ich godzin i nie zgłasza
braków obsady za nieplanowany okres. Od 10.10 zapotrzebowanie, UI, saldo
i PDF/Excel są zgodne. Dzień 1 zachowuje pełny miesiąc, ostatni dzień tylko
ten dzień. Granicą jest data startu służby, także dla nocki kończącej się
następnego dnia. Nie usuwać potrzebnego kontekstu odpoczynku innych wersji
i obiektów. Nie skalować automatycznie miesięcznych target_hours ani
absencji/delegacji; nie zmieniać wag solvera. To ograniczenie zakresu pierwszego
grafiku, bez nowej polityki godzin docelowych.

Pierwszy PLAN nadal tworzy wyłącznie preview, wersja powstaje po „Użyj tego
grafiku”. Błąd nie tworzy pół-wersji. Dotychczasowa ochrona started services
i historia rodziców w kolejnych wersjach pozostają w obecnej ścieżce.

### F7 — bezpieczna zmiana hasła przez obecny komponent auth

Owner: `UserManager` z fastapi-users i cienki endpoint `/api/auth/me/password`.
Request: `current_password` oraz dotychczasowe `password` (nowe hasło), inne
pola nadal odrzucane. Weryfikacja obecnego hasła przez wspierany password helper
biblioteki; zapis/hash przez obecny UserManager. Walidację minimum 8 znaków
umieścić w jego hooku `validate_password`, współdzielonym przez zmianę,
provisioning i reset operatora. Bez drugiej walidacji biznesowej w routerach.
Nie blokować logowania na istniejące krótsze hasła: reguła dotyczy ustawiania
nowego hasła, nie retroaktywnego odbierania dostępu.

Obecny formularz „Konto” dostaje „Obecne hasło” i informację „Nowe hasło musi
mieć co najmniej 8 znaków”. Brak/błędne obecne hasło oraz za krótkie nowe
odmawiają zmiany czytelnym polskim komunikatem; konto i stare hasło pozostają
sprawne. Sukces pokazuje „Hasło zmienione.”, czyści pola haseł. Anulowanie
również je czyści. Pola maskowane; nie zapisywać haseł w logach, pamięci
obiektu ani web storage. Transport pozostaje istniejącym HTTPS i HttpOnly
cookie; bez zmiany mapowania konta, bazy i uprawnień.
Reset operatora nadal nie wymaga starego hasła. Zgubione hasło obsługuje
obecny operator, bez publicznego resetowania/SMTP/rejestracji.

### R — przygotowanie migracji Railway bez zmiany zasobów

Potwierdzony odczytem CLI 2026-10-16: projekt `truthful-freedom`, środowisko
`production`, serwis `elnath-rota`, źródło tego repo/main, builder Dockerfile,
dysk `elnath-rota-volume` pod `/data`. To stan infrastruktury do ponownego
sprawdzenia przed migracją, nie dane do odtwarzania projektu od zera.

Owner: `.railway/railway.ts` (stabilny TypeScript IaC), instrukcja
`deploy/RAILWAY.md`. Zastąpić stare ustawienia buildera równoważną konfiguracją
istniejącego serwisu. Wykorzystać aktualne CLI `railway config migrate`
w trybie podglądu i dane odczytane z istniejącego projektu; lokalna wersja
5.57.8 nie jest dowodem obsługi nowych komend. Wspierany SDK i lockfile
izolować w `.railway/package.json`/`package-lock.json`, bez zależności runtime
aplikacji i bez nowego pipeline automatycznych wdrożeń.

Konfiguracja ma zachować istniejący serwis, dysk, źródło, region, zmienne,
domeny i liczbę replik. Reuse named partial wygenerowanego dla pojedynczego
serwisu; bez przejmowania niepowiązanych zasobów. Sekrety pozostają na Railway
(`preserve()` tam, gdzie wymagane), nigdy w pliku ani w dowodzie. Nie używać
`--include-variables` ani zapisu odszyfrowanych wartości do repo.

Dostarczyć plik i instrukcję migracji, również kolejność usunięcia `railway.json`
i wyłączenia starego pola konfiguracji na serwisie. Nowy plik nie jest
automatycznie stosowany przez push aplikacji: działa przez CLI. Przed
zastosowaniem przedstawić plan zmian; blokada planu z powodu nadal aktywnego
CaC jest ograniczeniem etapu, nie dowodem poprawnej migracji.

Ten Task przygotowuje migrację do zatwierdzenia. Nie uruchamiać
`migrate --apply`, `config apply`, redeploy ani usuwania starej konfiguracji
na żywym serwisie bez jawnej zgody OWNERA na konkretny plan. W gałęzi można
przygotować usunięcie starego pliku; przed merge OWNER musi otrzymać kolejność
przejścia zapewniającą ciągłość ustawienia Dockerfile i dostępności `/data`.
Wycofanie: zachować dotychczasowe działające ustawienia do czasu zatwierdzonego
przejścia; nie odtwarzać/usuwać baz ani dysku. Brak dostępu lub rozbieżność
zasobów oznacza jawny HOLD migracji, bez zgadywania konfiguracji.

### T — odłożone nieaktualne testy

Tylko klasy z sekcji ODLOZONE 2026-09-24, nie inne odłożone tematy:
- testy oczekujące reguł ochrony przypiąć lokalnie do OCHRONA; test bramki
  target_hours do ORDINARY, zgodnie z zamrożonymi decyzjami;
- trzy testy „no persistence coupling” mają rozpoznawać importy, nie tekst
  w komentarzu; bez przeredagowywania poprawnej produkcji dla regexa;
- źródłowe kontrole po przeniesieniu absencji wskazują rzeczywisty obecny
  owner; najlepiej zachować istniejący sens kontroli zachowania;
- usunąć wyłącznie jednorazowy, zużyty dowód git-diff T23-54;
- wynik auth 404/405 uniezależnić od przypadkowego lokalnego frontend/dist.

Preferować ustawienie reżimu w danym teście zamiast globalnej zmiany
`tests/support/minimal_state.py`, `state_builder.py` lub buildera scenariuszy.
Nie osłabiać asercji produktowych ani zmieniać solvera, by „zazielenić” testy.
Liczba 34 to historyczny wynik, nie nakaz usunięcia dokładnie 34 testów.
CC zestawia zmieniony test → aktualny kontrakt → powód aktualizacji.
Nowa niezależna przyczyna poza tym zakresem wymaga zgłoszenia, nie rozszerzenia
naprawy przy okazji. Nie odtwarzać usuniętych benchmarków/symulatorów.

## 4. Redukcja zakresu — jedno przejście przed implementacją

SOURCE/NECESSITY: F6/O4 wymaga tylko przeniesienia już obliczonego wyniku
i prezentacji; F5/O1 tylko konfiguracji zegara; F3 potrzebuje daty w obecnym
ownerze NN; F1/O5 mapowania/etykiety i istniejącego action trail; F2 właściwego
zakresu jednego checka; F4/O2 ograniczenia pierwszego planu i akceptacji;
F7/O3 hooka UserManager i pola starego hasła; R migracji konfiguracji;
T mechanicznej zgodności testów z obowiązującym produktem.

Usunięto z proponowanego rozwiązania potrzebę nowych tabel, silnika reguł,
automatycznych korekt przy GET, drugiej walidacji, filtrowania NN w eksporterze,
przebudowy dat na aware datetime, osobnego auth i globalnej zmiany fixture.
Formatter prezentacji F6 jest małym adapterem, nie ownerem reguł. Nie zmieniamy
istniejącego `fresh_validation` używanego przez lifecycle/eksport; sam fakt,
że odczyt miesiąca również waliduje, nie uzasadnia refaktoru całego przepływu.
To decyzja zakresu autora briefu, nie niezależny PASS własnego kontraktu.

## 5. Minimalne dowody i kryteria akceptacji

CC: celowane testy zmienionych ownerów, build frontendu, mechaniczny backend
gate i ultrareview zgodnie z przekazaniem. Codex niezależnie sprawdza exact SHA,
surowy diff i najmniejszy reproduktor każdej poprawianej klasy, bez powtarzania
pełnej macierzy niższych warstw. Raporty kolejno `round_01/tests/tests_r<n>.txt`;
nie nadpisywać wcześniejszych.

A1/F6: przez produkcyjny zapis dostępności → GET miesiąca → rzeczywisty UI
pokazać nowy konflikt L4 z osobą/datą i jego zniknięcie po naprawie danych.
Mała parametryzacja pozostałych klas dostępności oraz przykład naruszenia
spoza dostępności i reguły obiektu dowodzi braku filtra kategorii. Sprawdzić
równoczesne naruszenia, ostrzeżenia SOFT i FINAL; GET bez zapisów/auto-ack.
Nie pisać od nowa kompletnego zestawu testów wszystkich reguł.

A2/F5: w zbudowanym kontenerze runtime sprawdzić Europe/Warsaw zimą/latem,
polską datę o 00:30 i istniejącą granicę służby dokładnie o starcie oraz po
starcie przez manual correction/PLAN. Dowód z hosta Windows nie dowodzi
konfiguracji kontenera. Zachować 12h przy jesiennej i wiosennej zmianie czasu.

A3/F3: produkcyjne NN za wczoraj i za poprzedni miesiąc → zapis dziecka
z datą służby → projekcja PDF i Excel; WYK bez godzin nieodbytej służby,
rodzic bez zmian, action trail obecny. Sprawdzić dobę nocną według daty startu.

A4/F1: rzeczywista ręczna korekta N/N/N zapisuje wersję, LAW i CoordinatorAction,
UI polska etykieta; istniejąca finalizacja/eksport wymaga właściwego
potwierdzenia. Kontrola negatywna: automat nie zwraca nowego N/N/N jako FEASIBLE.

A5/F2: zachować reproduktor odległej historycznej trójki i uogólnić na
początek miesiąca; historia poza oknem nie blokuje innego miesiąca,
trójka w zakresie nadal wykrywana. Dotyczy tego samego obiektu, z legalnie
zapisanym wyjątkiem ręcznym, bez mieszania niezależnych seedów.

A6/F4: PLAN → reload preview → „Użyj tego grafiku” → odczyt/saldo/projekcja
PDF i Excel dla daty 10.10; brak demands/assignments/godzin/braków pokrycia
za 1–9, planowanie od 10 włącznie. Granice 1 i ostatni dzień, jedna nocka;
kontrola istniejącej wersji z rodzicem bez kasowania wcześniejszych faktów.
Sprawdzić akceptację przez obecną ścieżkę Excel, nie tylko web wrapper.

A7/F7: w CENTRAL_SERVICE prawdziwy endpoint: brak/błędne obecne hasło,
nowe 7/8 znaków, poprawna zmiana i logowanie nowym hasłem; stare przestaje
działać. Create/reset operatora respektuje ten sam limit. Konto i mapowanie
bez zmian; starsze krótkie hasło nadal pozwala się zalogować i zmienić na nowe.
UI: polskie komunikaty, pola maskowane i czyszczone. Direct API nie omija reguł.

A8/R: konfiguracja i instrukcja obejmują wyłącznie istniejący serwis;
walidacja oficjalnym CLI/SDK, podgląd migracji, brak sekretów/destrukcyjnych
zmian. Gotowość plików odróżnić od wykonania migracji. Żywe zastosowanie
i powdrożeniowy odczyt grafiku/logowanie/eksport to osobny etap po zgodzie.

A9/T: celowane testy starych klas przechodzą z oczekiwaniem wynikającym
z aktualnych kontraktów, nie ze zmienionej produkcji. Pełna suita
`.venv\Scripts\python.exe -m pytest tests -q` jest wymagana raz przez CC
na końcowym SHA tego bloku: zgodę na ten zakres i ryzyko wspólnych fixture
utrwala przywołana decyzja OWNERA w ODLOZONE z 2026-09-24 i jej uruchomienie
w przekazaniu 2026-10-16. Codex nie powtarza jej automatycznie; dodatkowy pełny
przebieg wymaga osobnej zgody zgodnie z AGENTS. Przed implementacją nie
uruchamiać pełnej suity „dla ponownego odkrycia” opisanych porażek.

Brak środowiska/narzędzia → NOT_CHECKED/PARTIAL z przyczyną, nie deklaracja
wykonanej weryfikacji. FAIL wymaga TRACE + OWNERSHIP + niezależnego REPRO
na dokładnym SHA. Sam brief nie jest dowodem naprawy ani zgodą na merge.

## 6. Zakres plików i wyłączenia

Produkcja: dozwolone wyłącznie zmiany opisane w §3 w wymienionych niżej
ownerach. `api/routers/schedule.py` obejmuje transport F6 i etykietę F1;
`api/schedule_validation_messages.py` wyłącznie czystą prezentację F6;
`open_month.py` wyłącznie zachowanie już policzonych violation_details;
`plan_ops.py` wyłącznie F4; `manual_edit.py` wyłącznie F3;
`Workspace.tsx`, `client.ts`, auth manager/backend/schemas wyłącznie F7.
MonthlyPlanning nie wymaga nowego kodu produkcyjnego dla istniejącego bannera.

Testy: dwa nowe wąskie pliki backendowe dla poprawek grafiku/auth oraz jeden
scenariusz UI. Wskazane stare pliki wolno zmieniać tylko dla klas T opisanych
wyżej i koniecznego dostosowania kontraktu żądania zmiany hasła. Wspólnych
fixture nie zmieniać w tym Tasku. Nowe dowody/raporty pozostają w katalogu Tasku.

OUT_OF_SCOPE: ogólne uprawnienia edycji historii, nowe ścieżki wyjątków,
automatyczne uznawanie odstępstw, nowe reguły/wagi/fairness solvera, naliczanie
płac 11/13h, retroaktywna migracja danych NN, globalny refaktor, nowy magazyn
pamięci, zmiany RODO/tenancy, unieważnianie wszystkich JWT/API keys,
rate-limit/MFA/SSO, samorejestracja i reset przez e-mail, automatyczne wdrożenia,
inne pozycje ODLOZONE, zmiana AGENTS i propozycja poziomów audytu z BOARD.
Te wyłączenia nie są deklaracją kompletnego bezpieczeństwa wdrożenia chmurowego.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: rota/application/open_month.py --symbol open_month; rota/application/manual_edit.py --symbol mark_not_worked; rota/application/plan_ops.py --symbol plan_month; rota/application/plan_ops.py --symbol select_candidate; rota/application/deviation_mapping.py --symbol category_for_rule; rota/planning/validator_checks_patterns.py --symbol _check_night_streak; api/auth/manager.py --symbol UserManager; api/auth/backend.py --symbol change_own_password
- REASON: potwierdzić wspólnych ownerów, granice pierwszej akceptacji i alternatywne wejścia bez dublowania walidacji.

Po zamrożeniu zakresu implementer, a następnie audytor implementacji uruchamia
`python where.py <file>` dla wymienionych plików oraz wariant `--symbol` dla
tych konkretnych symboli. Nie rozszerzać mapy na całe repo; czytać wskazane
fragmenty przed wnioskami. Nie uruchamiać jej w samym prechecku briefu.

TASK_SCOPE:
- tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md
- tasks/ROTA-CLOUD-REVIEW-FIXES/repo_before.hash
- tasks/ROTA-CLOUD-REVIEW-FIXES/round_01/
- rota/application/open_month.py
- rota/application/manual_edit.py
- rota/application/plan_ops.py
- rota/application/deviation_mapping.py
- rota/planning/validator_checks_patterns.py
- api/routers/schedule.py
- api/schedule_validation_messages.py
- api/auth/backend.py
- api/auth/schemas.py
- api/auth/manager.py
- frontend/src/api/client.ts
- frontend/src/screens/Workspace.tsx
- Dockerfile
- railway.json
- .railway/railway.ts
- .railway/README.md
- .railway/package.json
- .railway/package-lock.json
- deploy/RAILWAY.md
- tests/test_cloud_review_schedule_fixes.py
- tests/test_cloud_review_password_change.py
- frontend/e2e/cloud-review-fixes.spec.ts
- tests/test_audit_r25_findings.py
- tests/test_audit_t010_r5_b.py
- tests/test_audit_t010_r3.py
- tests/test_audit_t009_r4.py
- tests/test_excel_external_api.py
- tests/test_rota_generic_month.py
- tests/test_replan_minimal_reshuffle.py
- tests/test_manual_audits.py
- tests/test_site_rules_execution.py
- tests/test_site_profile_persistence.py
- tests/test_site_memory_decision_ledger.py
- tests/test_t009_plan_select_replan.py
- tests/test_t010_day_only_n_exception.py
- tests/test_t017.py
- tests/test_t013.py
- tests/test_t012.py
- tests/test_t024_auth_isolation.py
- tests/test_t023_checkpoint_b.py
- tests/test_t022_planning_integrity.py
- tests/test_t021_screen2_r13_audit.py
- tests/test_t021_screen2_r12_audit.py
- tests/test_t026.py

KONIEC TASK_SCOPE.

## 7. Przekazanie i bramki

Najpierw niezależny precheck Codexa: źródła/decyzje, jednoznaczność,
testowalność i minimalni ownerzy, bez audytu produktu/testów/regresji.
Następnie niezależna ocena merytoryczna CC; dopiero obie bramy zwalniają
IMPLEMENTATION HOLD. Autor tego briefu nie wystawia mu niezależnego PASS.
Przed merge wymagane ultrareview i niezależny audyt implementacji Codexa
na exact SHA, z zakresem dowodu zgodnym z aktualnym AGENTS, nie z nieprzyjętą
propozycją poziomów audytu. Merge i zastosowanie zmian Railway zarządza OWNER.
