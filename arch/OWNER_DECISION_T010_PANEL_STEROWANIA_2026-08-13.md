# ROTA — decyzja właściciela: T010 / konfiguracja i Panel Sterowania

DATA: 2026-08-13
STATUS: OWNER DECISION / skonsolidowany aneks produktu przed briefem ROTA-T010
BAZA: main `51b71725186fa30be23219e94aa135bb69bc5bce`
ZASTĘPUJE: wcześniejszą treść tego dokumentu z commita
`4925be4ba755755373200b7ffc0581882a31c5ce`

## 1. Zmiana kierunku T010

ROTA-T010 nie jest zadaniem dotyczącym parsera języka naturalnego.

Parser i sterowanie Rotą swobodnym tekstem są usunięte z zakresu produktu.
Koordynator przekazuje konfigurowalne decyzje jawnie. Program nie zgaduje
jego intencji i nie tworzy reguł na podstawie analizy zachowania pracownika.

T010 ma przygotować trwałe operacje aplikacyjne oraz odczyty konfiguracji.
Nie implementuje jeszcze Reacta, Tauri ani żadnego tymczasowego UI.

## 2. Panel Sterowania

**Panel Sterowania** jest nazwą docelowego okna przyszłego desktopowego UI.
Nazwa nie jest poleceniem zaprojektowania tego okna w T010.

Panel będzie jednym, rozpoznawalnym miejscem, w którym koordynator:

- przeprowadzi pierwszą konfigurację obiektu;
- później zmieni te same ustawienia obiektu i pracowników.

Panel nie jest drugim źródłem logiki ani danych. Jeżeli stan lub operacja już
istnieją w domenie, application layer albo persistence, Panel ma użyć ich
przez właściwą operację aplikacyjną. Nie wolno tworzyć równoległej kopii
konfiguracji tylko dlatego, że dana funkcja jest widoczna w Panelu.

Docelowy Panel powstanie w T012. T010 przygotowuje wspólny mechanizm
konfiguracji, z którego T012 skorzysta bez bezpośrednich zapisów do repository.

## 3. Jedna konfiguracja: pierwsze uruchomienie i późniejsza edycja

Pierwsza konfiguracja i późniejsza edycja są jednym mechanizmem konfiguracji.

T010 zapewnia operacje aplikacyjne zapisujące te same istniejące encje zarówno
przy pierwszym uruchomieniu, jak i później. Nie tworzy:

- osobnych par „create dla onboardingu / update dla Panelu”, jeżeli jedna
  operacja może bezpiecznie obsłużyć oba stany;
- tabel onboardingowych;
- kopii danych konfiguracyjnych;
- szkicu konfiguracji;
- numeru kroku ani flagi `onboarding_in_progress`.

Pierwszy kontekst obejmuje:

`Coordinator → SiteProfile → Site → CoordinatorSiteAssociation`

a następnie konfigurację zmian i bieżącej listy pracowników obiektu. Po
utworzeniu kontekstu te same źródła prawdy służą do dalszej edycji.

Pierwsza konfiguracja ma doprowadzić do zwykłego, operacyjnego stanu programu,
wystarczającego do ułożenia grafiku. Nie powstaje osobny „wynik onboardingu”.

### 3.1 Minimalna kompletność do pierwszego PLAN

Odczyt konfiguracji nie może uznać obiektu za gotowy do pierwszego PLAN, jeżeli
brakuje danych wymaganych przez istniejący application layer. Minimalny
operacyjny zestaw obejmuje:

- aktywnego Coordinator;
- aktywny Site;
- aktywne CoordinatorSiteAssociation dla tego Coordinator i Site;
- SiteProfile przypisany do Site;
- co najmniej jedną zdefiniowaną zmianę standardową z godziną początku,
  godziną końca, informacją o końcu następnego dnia oraz wymaganą obsadą
  PRIMARY;
- próg ruchomego okna godzin używany przez istniejącą kontrolę LOAD-01;
- pełne CalendarDay dla planowanego miesiąca;
- bieżącą listę pracowników obiektu wraz z Employee i aktywnymi
  SiteMembership;
- stałe ustawienia pracowników potrzebne solverowi, w tym `day_only`;
- miesięczne `target_hours`, jeżeli koordynator chce użyć istniejącego
  rankingu TARGET-01 i obserwacji bilansu.

Brak `target_hours` nie blokuje utworzenia demandów ani pierwszego PLAN —
zgodnie z T009 pozostaje brakującą daną i wyłącza tylko target-based SOFT dla
danego pracownika. Brak pełnego kalendarza miesiąca nadal blokuje planowanie;
program nie zgaduje świąt ani dni roboczych.

Pracownicy zewnętrzni X/Y, ExternalSupportWindow, nieobecności i dodatkowe
SiteRules są konfigurowane wtedy, gdy występują. Ich brak nie oznacza sam w
sobie niedokończonego onboardingu podstawowego obiektu.

## 4. Przerwanie i wznowienie konfiguracji

Konfiguracja może zostać przerwana.

To, co zostało poprawnie zapisane, pozostaje w normalnych danych programu. Po
ponownym uruchomieniu T010 odczytuje istniejący stan i pozwala kontynuować od
brakujących danych. Nie cofa poprawnych wcześniejszych zapisów tylko dlatego,
że koordynator nie zakończył całej konfiguracji w jednej sesji.

T010 dostarcza mały odczyt bieżącej konfiguracji, wyliczany z istniejących
danych. Ma on pozwolić T012 rozpoznać:

- brak pierwszego kontekstu;
- konfigurację częściową;
- istniejący, skonfigurowany obiekt.

Odczyt nie jest nowym trwałym stanem onboardingu. Jest projekcją istniejących
danych i wskazuje konkretnie, czego brakuje.

Przy pustej konfiguracji T012 otworzy Panel Sterowania w trybie pierwszej
konfiguracji. Ten sam Panel później służy do edycji. T010 nie projektuje
ekranów, kolejności pól ani kreatora.

## 5. Ograniczone odstępstwo dla bootstrapu

Utworzenie pierwszego kontekstu jest jedynym przypadkiem, w którym nie istnieje
jeszcze pełna relacja koordynator–obiekt możliwa do sprawdzenia zwykłą bramką
application layer.

Specjalne odstępstwo może istnieć wyłącznie w najmniejszej operacji potrzebnej
do utworzenia pierwszego kontekstu. Po jego powstaniu normalne operacje znów
podlegają istniejącej kontroli aktywnego Coordinator, Site oraz
CoordinatorSiteAssociation.

Nie wolno pod pretekstem bootstrapu:

- osłabić kontroli wszystkich operacji aplikacyjnych;
- pozwolić istniejącemu koordynatorowi konfigurować dowolny obiekt;
- dopuścić UI do bezpośrednich zapisów w repository;
- stworzyć drugiej, słabiej chronionej ścieżki późniejszej edycji.

## 6. Bieżąca lista pracowników obiektu

Mechanizm konfiguracji pozwala koordynatorowi:

- dodać pracownika do bieżącej listy pracowników obiektu;
- usunąć pracownika z bieżącej listy pracowników obiektu.

„Usunięcie pracownika” nie oznacza fizycznego kasowania Employee ani historii.

Po usunięciu z bieżącej listy:

- pracownik nie uczestniczy w nowych planowaniach tego obiektu tylko dlatego,
  że jego rekord historycznie istnieje;
- wcześniejsze ScheduleVersion, Assignment, bilanse i inne dane historyczne
  pozostają niezmienione i odtwarzalne;
- historia nadal jednoznacznie wskazuje pracownika, który wcześniej pracował
  na obiekcie.

Jeżeli aktywny Employee znajduje się na bieżącej, włączonej liście pracowników
obiektu, oznacza to, że koordynator dopuścił go do układania grafiku. Rota nie
prowadzi kadr i nie ustanawia dodatkowej oceny dopuszczenia pracownika.

## 7. Ustawienia pracownika udostępniane przez konfigurację

Dla pracownika przypisanego do obiektu konfiguracja udostępnia jedną spójną
matrycę dostępności:

1. **Ogólna dostępność**.
2. **Dniówka**.
3. **Nocka**.
4. **Dni tygodnia** — rozwijana lista: Pon, Wt, Śr, Czw, Pt, Sob, Nd.

Dla nowego pracownika domyślnie wszystkie pozycje są zaznaczone:

- Ogólna dostępność ✓;
- Dniówka ✓;
- Nocka ✓;
- Pon ✓, Wt ✓, Śr ✓, Czw ✓, Pt ✓, Sob ✓, Nd ✓.

Nie ma osobnego ustawienia **Święta**.

Nie ma przełącznika **Szkolenie**. Szkolenie `S` koordynator wstawia ręcznie
do grafiku, jeżeli uzna je za potrzebne. Solver nie rozstrzyga, czy pracownik
potrzebuje szkolenia.

## 8. Jedno znaczenie wszystkich kontrolek dostępności

Ustawienia dostępności są bieżącą, jawną komunikacją koordynatora z solverem i
mają charakter HARD.

Każdy ptaszek w tej matrycy ma dokładnie to samo znaczenie:

- `✓` = solver może korzystać z pracownika w tym wymiarze;
- `☐` = solver nie może korzystać z pracownika w tym wymiarze.

Nie istnieje kontrolka, w której zaznaczenie oznacza zakaz. Dotyczy to również
listy dni tygodnia.

Odznaczenie pozycji wraz z zakresem od–do tworzy czasowe ograniczenie HARD.
Obowiązuje wyłącznie w podanym zakresie, a po dacie `do` automatycznie wygasa
i wraca wcześniejszy stan. Stan bazowy nie jest nadpisywany zmianą okresową.
Obie granice są włączne: ograniczenie obowiązuje przez cały dzień `od` i cały
dzień `do`; stan bazowy wraca następnego dnia po `do`.

Dla konkretnego ShiftDemand solver może użyć pracownika tylko wtedy, gdy
jednocześnie obowiązują:

- Ogólna dostępność ✓;
- właściwy rodzaj zmiany: Dniówka ✓ dla D albo Nocka ✓ dla N;
- dzień tygodnia, w którym zaczyna się ShiftDemand, ma ✓.

Jest to jedna logika koniunkcji dostępności, a nie osobne mechanizmy o różnych
znaczeniach.

| Obowiązujące stany | Skutek dla solvera |
|---|---|
| wszystkie właściwe pozycje ✓ | pracownik jest dostępny dla danego demandu |
| Ogólna dostępność ☐ | D i N są zablokowane przez cały obowiązujący okres |
| Dniówka ☐ | D jest zablokowana; samo to ustawienie nie blokuje N |
| Nocka ☐ | N jest zablokowana; samo to ustawienie nie blokuje D |
| Dniówka ☐ i Nocka ☐ | D i N są zablokowane |
| Piątek ☐ | D i N zaczynające się w piątek są zablokowane |

Jeżeli kilka ograniczeń nakłada się w czasie, nie konkurują ze sobą i nie są
uszeregowane priorytetem. Jedno obowiązujące `☐` we właściwym wymiarze
wystarcza do zablokowania przydziału. Solver niczego nie „odblokowuje” na
podstawie innego zaznaczonego pola.

Jeżeli obowiązujące ustawienie mówi, że pracownik nie jest dostępny dla danego
użycia, solver nie może go samodzielnie naruszyć, aby ułożyć grafik.

W szczególności:

- Ogólna dostępność ☐ blokuje użycie pracownika w obowiązującym
  okresie;
- Dniówka ☐ blokuje automatyczny przydział D;
- Nocka ☐ blokuje automatyczny przydział N;
- dzień tygodnia z ☐ blokuje D i N rozpoczynające się w każdym takim dniu
  mieszczącym się w zadanym zakresie od–do.

Dla ograniczeń dnia tygodnia obowiązuje istniejąca konwencja Rota: dniem
zmiany, także nocnej, jest data rozpoczęcia ShiftDemand.

Jeżeli przy tych decyzjach nie da się stworzyć kompletnego grafiku, program ma
zwrócić brak rozwiązania wymagający działania koordynatora. Nie może sam
odblokować pracownika ani zignorować ustawienia.

## 9. Lista dni tygodnia

Koordynator rozwija listę dni tygodnia. Wszystkie dni są domyślnie zaznaczone,
czyli dozwolone dla solvera. Aby zapisać ograniczenie, odznacza wybrany dzień
i podaje daty od–do.

Przykład:

- `Piątek ☐ | od 2026-09-01 | do 2026-10-31`;
- pracownik jest niedostępny w każdy piątek mieszczący się w tym okresie;
- pozostałe dni nie zmieniają się;
- po 2026-10-31 ograniczenie wygasa automatycznie.

Oznacza to, że piątek 2026-10-30 jest jeszcze objęty ograniczeniem, a stan
bazowy wraca 2026-11-01.

To obejmuje praktyczne sytuacje okresowe, np. leczenie powodujące brak
dostępności w piątki przez dwa miesiące.

## 10. `day_only` w tej samej logice Nocki

`Employee.day_only` pozostaje istniejącym źródłem bazowego stanu Nocki, ale
nie jest osobną kontrolką o innym znaczeniu:

- dla zwykłego nowego pracownika bazowo Nocka ✓;
- gdy `Employee.day_only=true`, bazowo Nocka ☐.

Panel nie pokazuje jednocześnie osobnego przełącznika `day_only` i konkurującej
z nim Nocki. Widoczny stan Nocki jest projekcją obowiązującej decyzji.

Koordynator może czasowo zawiesić bazowy zakaz `day_only`, zapisując
`Nocka ✓` z zakresem od–do. Znaczenie ptaszka się nie odwraca: ✓ zawsze znaczy
„solver może”. Po dacie końcowej wraca bazowe Nocka ☐.

Analogicznie dla pracownika z bazowym Nocka ✓ koordynator może zapisać:

`Nocka ☐ | od 2026-09-20 | do 2026-09-29`

W tym okresie solver nie może przydzielać N; po 2026-09-29 wraca bazowe
Nocka ✓.

Przykład:

- pracownica zwykle pracuje tylko na D;
- w sytuacji kryzysowej koordynator dopuszcza N od 20 do 29 dnia miesiąca;
- solver może użyć jej na N wyłącznie w tym okresie;
- od 30 dnia ponownie obowiązuje `day_only`.

Brief T010 ma wskazać najmniejszy mechanizm wykorzystujący istniejące źródła
prawdy. Nie wolno pozostawić dwóch konkurencyjnych logik ani nadać ptaszkowi
Nocki innego znaczenia niż pozostałym kontrolkom.

## 11. Nieobecności

### 11.1 Niedostępność znana przed planowaniem

Koordynator może wcześniej zapisać niedostępność ciągłą albo powtarzalną w
wybrane dni tygodnia. Solver omija te terminy i może rozłożyć pracę na inne
dni, nadal respektując pozostałe HARD.

Przy ogólnej niedostępności koordynator może wskazać powód potrzebny Rotcie do
grafiku i godzin:

- choroba;
- urlop;
- nieobecność nieusprawiedliwiona (`NN`).

Rota wykorzystuje powód wyłącznie do oznaczenia grafiku i prawidłowego
policzenia godzin. Konsekwencje kadrowe są poza zakresem.

### 11.2 NN po niewykonaniu zaplanowanej zmiany

`NN` jest faktem operacyjnym: pracownik nie wykonał zaplanowanej zmiany.

Po korekcie bieżącego grafiku zmiana jest widoczna jako `NN`, a efektywne
godziny pracy za nią wynoszą `0`. Program nie udaje, że zmiana została
przepracowana i nie tworzy sztucznego przepracowanego Assignment.

Przykład:

- ułożony grafik dawał pracownikowi 168 godzin;
- pracownik nie wykonał jednej zmiany 12-godzinnej;
- bieżący grafik oznacza tę zmianę jako `NN`;
- efektywne godziny pracy wynoszą 156.

`168` w tym przykładzie jest wynikiem wcześniej ułożonego grafiku, a nie
indywidualnym nakazem wypracowania dokładnie 168 godzin.

## 12. Rota nie decyduje o pracowniku

Rota jest kalkulatorem grafików pilnującym jawnych założeń obiektu i norm
pracy. Koordynator decyduje o pracowniku. Program wykonuje jego ustawienia,
liczy godziny i pokazuje fakty, ostrzeżenia oraz brak możliwości ułożenia
grafiku.

Program nie może samodzielnie:

- dopuścić ani odsunąć pracownika od pracy;
- tworzyć decyzji kadrowych;
- wyprowadzać uprawnień z historii lub liczby szkoleń;
- zmieniać eligibility na podstawie etykiety `readiness_state`.

`READY_FOR_PRIMARY` / `NOT_READY` mogą pozostać informacyjną etykietą programu,
np. pomocną przy nowym pracowniku. Etykieta nie blokuje ani nie dopuszcza do
grafiku. Istniejące automatyczne przestawienie tej etykiety po policzeniu
szkoleń może pozostać, dopóki pozostaje wyłącznie informacyjne; T010 nie ma
rozbudowywać tego mechanizmu.

## 13. TARGET-01 i obserwacja godzin

Zapotrzebowanie obiektu określa liczbę potrzebnych zmian. Solver nie tworzy
dodatkowej pracy po to, aby pracownik osiągnął określoną liczbę godzin.

`target_hours` pozostaje istniejącym parametrem SOFT. Pomaga rozsądnie
rozdzielić wymagane zmiany i obserwować miesięczne oraz kwartalne saldo, ale:

- nie może naruszyć HARD;
- nie może utworzyć dodatkowej zmiany;
- nie jest decyzją kadrową;
- liczby `planned_hours` i `realized_hours` nadal wynikają z grafiku.

T010 nie zmienia istniejącej semantyki TARGET-01.

## 14. HARD, SOFT i informacja

W konfiguracji nie wolno mieszać trzech znaczeń:

- ustawienia dostępności z tego aneksu są HARD;
- istniejące zasady SOFT mogą wpływać na ranking, lecz nie na poprawność HARD;
- informacje i etykiety nie ograniczają planowania.

Wygląd przyszłego Panelu ma komunikować tę różnicę, ale szczegóły UI należą
do T012.

## 15. Granica briefu ROTA-T010

Brief T010 ma być mały i ma najpierw zinwentaryzować istniejące możliwości:

- SiteProfile i jego repository;
- Employee, SiteMembership, AvailabilityRecord i ich application commands;
- SiteRuleVersion / SiteMemory oraz wykonywalny katalog T007;
- Site, Coordinator i CoordinatorSiteAssociation;
- istniejącą warstwę application z T009.

T010 implementuje wyłącznie brakujące podpięcia potrzebne do:

- bootstrapu pierwszego kontekstu;
- odczytu kompletności konfiguracji;
- pierwszej konfiguracji i późniejszej edycji tych samych danych;
- bieżącej listy pracowników bez kasowania historii;
- jednej matrycy dostępności z identycznym znaczeniem wszystkich ptaszków;
- stałych i okresowych ustawień ogólnych, D/N oraz dni tygodnia;
- powtarzalnej niedostępności w dniach tygodnia;
- projekcji `day_only` jako bazowego Nocka ☐ oraz jego czasowego zawieszenia
  przez Nocka ✓ od–do;
- zapisu i rozliczenia `NN` zgodnie z tym aneksem;
- bezwzględnego respektowania tych decyzji przez solver.

T010 nie tworzy:

- UI, kreatora ani tymczasowego ekranu;
- parsera języka naturalnego;
- uniwersalnego edytora reguł ani DSL;
- nowej warstwy workflow;
- drugiego źródła prawdy;
- osobnego systemu kadrowego;
- osobnego systemu onboardingu.

Jeżeli istniejący kod zapewnia część zachowania, T010 ma go wykorzystać.
Jeżeli implementacja wymaga nowej decyzji produktowej, brief ma zwrócić ją
właścicielowi przed kodowaniem zamiast zakodować założenie.

## 16. Obowiązkowe przypadki do zamrożenia w briefie

Brief T010 ma uczynić testowalnymi co najmniej następujące klasy:

1. pusta baza → utworzenie pierwszego kontekstu;
2. przerwanie po części poprawnych zapisów → restart → rozpoznanie braków i
   kontynuacja bez osobnego stanu onboardingu;
3. istniejący obiekt → edycja przez te same operacje i źródła prawdy;
4. próba użycia bootstrapu do obejścia kontroli istniejącego obiektu → odmowa;
5. usunięcie pracownika z bieżącej listy → brak w nowym planowaniu i pełna
   historyczna odtwarzalność;
6. wszystkie pozycje domyślnie ✓ → brak dodatkowego ograniczenia;
7. Nocka ☐ od–do → brak N tylko w tym okresie i automatyczny powrót bazowego
   stanu;
8. `day_only=true` → bazowe Nocka ☐; czasowe Nocka ✓ od–do → N tylko w tym
   okresie i automatyczny powrót zakazu;
9. Piątek ☐ od–do → brak automatycznego przydziału D i N rozpoczynających się
   w każdy piątek tego okresu, bez wpływu na inne dni;
10. ustawienie HARD uniemożliwiające pokrycie → jawny brak rozwiązania, bez
   samodzielnego odblokowania pracownika;
11. `NOT_READY` i `READY_FOR_PRIMARY` → identyczna eligibility przy tych samych
   rzeczywistych danych pracownika;
12. NN na zaplanowanej zmianie → oznaczenie NN, 0 godzin efektywnych za tę
    zmianę i zachowana historia wcześniejszej wersji grafiku;
13. target_hours → wpływ wyłącznie SOFT na rozdział istniejącego demandu,
    nigdy tworzenie dodatkowej pracy ani naruszenie HARD.

Ten aneks jest podstawą do napisania briefu T010, nie zgodą na implementację.
