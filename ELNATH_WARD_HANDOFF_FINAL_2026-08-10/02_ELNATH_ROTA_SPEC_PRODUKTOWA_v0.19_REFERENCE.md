# ELNATH ROTA — SPECYFIKACJA PRODUKTOWA v0.17 CANDIDATE

STATUS: KANDYDAT / NIEZAMROŻONA  
JĘZYK: polski  
CEL: opisać wyłącznie produkt Elnath Rota dla pierwszego pilota  
UWAGA: ten dokument NIE opisuje procesu Elnath Ward

---

## 1. Cel pierwszej wersji

Elnath Rota ma przygotować miesięczny grafik pracy dla jednej rzeczywistej placówki.

Program nie ma być tylko tabelą do ręcznego wpisywania zmian.

Ma:
- zebrać ograniczenia pracowników;
- przygotować konkretny grafik;
- wykrywać problemy;
- pozwalać na ręczne poprawki;
- ponownie sprawdzać grafik po poprawkach;
- zapisać i odtworzyć wcześniejsze wersje;
- przygotować czytelny wydruk;
- uczciwie zgłosić brak rozwiązania, jeżeli poprawnego grafiku nie da się ułożyć.

---

## 2. Zakres pierwszego pilota

Pierwszy pilot obejmuje:
- jeden obiekt;
- pracę 24/7;
- zmianę dzienną `D`: 05:00–17:00;
- zmianę nocną `N`: 17:00–05:00 następnego dnia;
- jedną osobę odpowiedzialną za obsadę każdej wymaganej zmiany;
- możliwość dodatkowej obecności pracownika szkolonego `S`.

Planowanie następnego miesiąca używa wyłącznie stałych zmian `D` i `N`.

Solver nie tworzy innych godzin zmian.

Wyjątkowo, już podczas trwającego miesiąca, koordynator może ręcznie zmienić godziny konkretnej pracy, np.:
- pierwszy pracownik 05:00–13:00;
- następca od 13:00.

Jest to awaryjna korekta rzeczywistego miesiąca, a nie wariant, który solver ma proponować przy planowaniu.

Model danych nie może jednak zakładać, że historyczna / ręcznie poprawiona zmiana zawsze ma dokładnie 12 godzin, ponieważ takie wyjątkowe korekty muszą dać się zapisać i prawidłowo policzyć.

---

## 3. Czego pierwsza wersja nie zawiera

Poza zakresem są:
- sklepy;
- produkcja;
- piekarnia;
- wiele placówek;
- delegowanie między punktami;
- PWA w pierwszym pilocie;
- Railway;
- chmura;
- aplikacja mobilna;
- AI;
- LynxMask;
- rozbudowana analityka;
- system kadrowo-płacowy;
- samodzielne składanie wniosków przez pracowników.


Pełna wersja produktu ma jednak zapewniać PWA dla koordynatora, ponieważ typowym powodem REPLAN jest nagła choroba pracownika, a koordynator może być poza biurem. PWA ma co najmniej umożliwiać wprowadzenie nagłej niedostępności, uruchomienie REPLAN, zobaczenie propozycji albo `DECISION_REQUIRED` oraz zatwierdzenie decyzji / wybranego wariantu.

Program nie pokazuje pustych modułów ani zapowiedzi tych funkcji.

---

## 4. Pracownicy

W danych projektowych i testowych pierwszego pilota używamy wyłącznie anonimowych oznaczeń:
- `Pracownik A`;
- `Pracownik B`;
- `Pracownik C`;
- `Pracownik D`;
- `Pracownik E`.

W fazie projektowania i budowy nie używamy prawdziwych danych osobowych.

Tester powinien mieć możliwość samodzielnego zastąpienia oznaczeń A–E prawdziwymi nazwiskami na swoim lokalnym urządzeniu, bez zmiany logiki programu.

W testowej piątce występuje co najmniej jedno rzeczywiste ograniczenie pracownika:

`TYLKO_DNIÓWKI`

Jeden z pięciu pracowników może być przypisywany przez solver wyłącznie do zmian dziennych.

To ograniczenie jest ukłonem wobec pracownika, a nie absolutnym zakazem. Koordynator może je wyłączyć lub świadomie zrobić odstępstwo.

Dla wszystkich pracowników solver nie planuje automatycznie 24 godzin pracy bez przerwy.

Program przechowuje co najmniej:
- identyfikator pracownika;
- nazwę wyświetlaną;
- aktywność w danym okresie;
- stałe ograniczenia planistyczne możliwe do włączenia/wyłączenia;
- nieobecności potrzebne do grafiku;
- potrzeby wolnego;
- docelową liczbę godzin dla danego miesiąca;
- liczbę faktycznie zaplanowanych godzin;
- narastający bilans godzin w bieżącym kwartale;
- nierozliczony bilans przeniesiony z poprzedniego okresu, jeżeli występuje.

### Szkolenie nowego pracownika

Gdy pojawia się nowy pracownik, koordynator może przydzielić go na szkolenie razem z doświadczonym pracownikiem.

Szkolenie jest krótszą obecnością w ramach zmiany, a nie pełną dodatkową zmianą.

Typowy przypadek pilota:
- dwa szkolenia po około 4 godziny;
- każde szkolenie jest wliczane do czasu pracy pracownika szkolonego;
- szkolenia odbywają się od poniedziałku do piątku.

Koordynator nie wybiera niezależnie terminu i mentora szkolenia. Najpierw patrzy, kiedy doświadczony pracownik pełni już zmianę PRIMARY, a następnie dopisuje `S` do tej konkretnej zmiany.

Koordynator ręcznie określa:
- istniejącą zmianę PRIMARY mentora, do której dopisuje szkolenie;
- konkretne godziny obecności szkolonego w ramach tej zmiany.

Dzień, typ `D`/`N` i mentor wynikają z wybranej istniejącej zmiany PRIMARY.

Wtedy na jednej zmianie celowo występują dwie osoby:
- pracownik podstawowy, który zapewnia wymaganą obsadę i pełni rolę osoby szkolącej;
- pracownik szkolony oznaczony symbolem `S`.

Pracownik szkolony:
- jest osobnym rekordem pracownika;
- jest widoczny w grafiku;
- nie zastępuje pracownika podstawowego jako wymaganej obsady;
- może wystąpić jako dodatkowa osoba na zmianie bez generowania błędu „podwójna obsada”;
- ma godziny szkolenia doliczane do własnego czasu pracy.

Symbol `S` oznacza szkolenie, a nie trzeci typ normalnej zmiany.

### Gotowość po szkoleniu

W praktyce koordynator zakłada, że po dwóch szkoleniach pracownik jest gotowy do samodzielnej pracy.

Rota przyjmuje więc domyślnie:
`2 zakończone szkolenia S -> GOTOWY_DO_SAMODZIELNEJ_PRACY`

Koordynator zachowuje pełną kontrolę i może zmienić ten stan ręcznie.

Program nie ocenia jakości szkolenia i nie podejmuje decyzji personalnej za koordynatora. Automatyczny stan jest jedynie odwzorowaniem typowej praktyki.

### Nowy pracownik w trakcie miesiąca

Jeżeli nowy pracownik dochodzi już po rozpoczęciu miesiąca:
- wcześniejsza wersja grafiku pozostaje w historii;
- szkolenia `S` są dodawane do bieżącego stanu;
- po uzyskaniu gotowości pracownik staje się kandydatem do samodzielnej obsady od wskazanego momentu;
- solver może ponownie ułożyć pozostałą część miesiąca.

Podstawowym źródłem zapotrzebowania jest stała pula zmian / godzin wymaganych przez obiekt.

Wejście nowego pracownika zmienia natomiast pulę dostępnych zasobów.

Dlatego przy ponownym generowaniu solver nie musi tylko wstawić nowego pracownika w pojedyncze „brakujące miejsce”.

Może ponownie rozdzielić wszystkie jeszcze niezrealizowane zmiany pomiędzy całą aktualnie dostępną załogę.

W konsekwencji po przebudowie:
- nowy pracownik może dostać część pozostałych zmian;
- dotychczasowi pracownicy mogą dostać inną liczbę godzin niż w poprzedniej wersji grafiku;
- ich konkretne przyszłe D/N mogą się zmienić;
- godziny już przepracowane pozostają faktem i nie podlegają przebudowie.

### Cel godzin a godziny zaplanowane

Rota rozróżnia:
- `CEL_GODZIN` — wartość planistyczną wynikającą z normy, bilansu i decyzji koordynatora;
- `GODZINY_ZAPLANOWANE` — wynik konkretnej wersji grafiku;
- `GODZINY_ZREALIZOWANE` — czas już rzeczywiście przepracowany.

Po wejściu nowego pracownika `GODZINY_ZAPLANOWANE` mogą zmienić się dla wszystkich pracowników w części miesiąca, która jeszcze nie została przepracowana.

Solver powinien nadal dążyć do rozsądnego zbliżenia pracowników do ich celów godzinowych, ale nie może traktować starej wersji zaplanowanych godzin jako zobowiązania, którego nie wolno zmienić.

Nowy pracownik nie otrzymuje mechanicznie „reszty godzin po osobie X”. Jego wejście może uzasadniać nowy podział całej pozostałej puli pracy.

### Wsparcie z innego obiektu

Do demonstracji mechanizmu braku obsady istnieją również dwa anonimowe wpisy:
- `Pracownik X — inny obiekt`;
- `Pracownik Y — inny obiekt`.

Nie oznacza to pełnej obsługi wielu obiektów.

X/Y po uzyskaniu zgody koordynatora są po prostu dostępni dla grafiku w określonym zakresie. Ich rozliczenia kadrowe i godzinowe poza tym obiektem nie należą do pilota.

---

## 5. Roczny plan urlopów

Na początku roku może istnieć plan urlopów.

W pierwszym pilocie plan urlopów jest informacją planistyczną i ostrzeżeniem, a nie bezwzględną blokadą solvera.

Program powinien:
- przechować planowany okres urlopu;
- pokazać go podczas przygotowywania miesiąca;
- ostrzec, jeżeli grafik przypisuje pracownika w okresie planowanego urlopu;
- zachować historię zmian planu.

Program nie może zakładać, że sam zapis w rocznym planie oznacza faktycznie udzielony urlop.

Rzeczywiście udzielony / zatwierdzony urlop miesięczny jest osobnym stanem i jego dokładne zachowanie pozostaje do doprecyzowania z testerem.

---

## 6. Dni wolne zgłaszane przed nowym miesiącem

Do 20. dnia bieżącego miesiąca zbierane są potrzeby pracowników dotyczące wolnego w miesiącu następnym.

W praktyce koordynator po otrzymaniu takiej potrzeby od razu traktuje wskazany czas jako niedostępny przy układaniu grafiku.

Program nie może jednak zakładać, że każde zgłoszone „wolne” oznacza automatycznie 24 godziny niedostępności.

W pierwszym pilocie wystarczą dwa proste rodzaje:

- `WOLNE_OD_DNIÓWKI` — pracownik nie powinien być zaplanowany na dniówkę, ale nocka może pozostać możliwa;
- `NIEDOSTĘPNOŚĆ_24H` — solver nie może automatycznie zaplanować żadnej kolidującej zmiany.

Nie wprowadzamy w pilocie dowolnych przedziałów godzinowych dla potrzeb wolnego.

Zgłoszenie pozostaje przypisane do konkretnej osoby i powinno mieć stan pozwalający odróżnić co najmniej:
- aktywne;
- zmienione;
- wycofane.

Koordynator może świadomie odstąpić od zgłoszonego wolnego, ale program musi wtedy pokazać konflikt i zapisać go jako odstępstwo.

---

## 7. Wolne związane z lekarzem

W praktyce pierwszej firmy takie wolne jest honorowane.

Program powinien zapisać jedynie informację potrzebną do planowania.

Nie powinien wymagać:
- diagnozy;
- opisu choroby;
- szczegółów medycznych.

Po przyjęciu takiej niedostępności pracownik nie może zostać zaplanowany na kolidującą zmianę.

---

## 8. Zwykły wolny dzień — praktyka firmy

W pierwszym pilocie zwykłe wolne ma dwa znaczenia:

**WOLNE_OD_DNIÓWKI**
- solver nie planuje dniówki;
- nocka może być użyta, jeśli nie narusza innych reguł.

**NIEDOSTĘPNOŚĆ_24H**
- solver nie planuje żadnej kolidującej zmiany.

Koordynator może ręcznie zrobić odstępstwo od obu reguł.

Program nie blokuje tej decyzji, ale:
- pokazuje konflikt;
- wskazuje, której reguły dotyczy odstępstwo;
- wymaga świadomego potwierdzenia przy zapisie wersji finalnej.

---

## 9. Pełna niedostępność

Pełna niedostępność oznacza coś innego niż zwykły wolny dzień.

Blokuje każdą zmianę nachodzącą na wskazany przedział.

Dotyczy to między innymi:
- urlopu;
- chorobowego;
- innej całodobowej niedostępności.

Jeżeli pełna niedostępność obejmuje wtorek, może blokować także nockę rozpoczętą w poniedziałek, jeżeli ta nocka wchodzi we wtorek.

---

## 10. Wymagania Zleceniodawcy

Przed przygotowaniem pierwszego grafiku koordynator powinien mieć możliwość wypełnienia dla placówki pliku lub formularza:

`Wymagania Zleceniodawcy`

Jest to osobne źródło ograniczeń planistycznych.

Nie należy mieszać go z:
- przepisami prawa;
- regulaminem pracodawcy;
- urlopami i nieobecnościami;
- preferencjami pracowników;
- ręcznymi decyzjami koordynatora.

### 10.1. Przykłady rzeczywistych wymagań

Znane przykłady:

- zleceniodawca wymaga wyłącznie zmian 12-godzinnych;
- zleceniodawca nie chce konkretnego pracownika na zmianach dziennych w dniach pracy zakładu;
- ograniczenie może dotyczyć tylko określonych dni tygodnia;
- ograniczenie może obowiązywać tylko w określonych godzinach;
- ograniczenie może dotyczyć konkretnego pracownika, rodzaju zmiany albo okresu.

W przyszłości mogą pojawić się inne wymagania tego samego rodzaju.

Dla pierwszego pilota:
- `dni pracy zakładu` oznaczają poniedziałek–piątek z wyłączeniem dni ustawowo wolnych od pracy;
- Wymagania Zleceniodawcy traktujemy jako `TWARDE`, ponieważ wynikają z umowy albo utrwalonej praktyki pracy;
- nie są one zwykłą preferencją solvera.


### 10.2. Wymaganie musi być strukturalne

Solver nie powinien podejmować decyzji na podstawie samego swobodnego tekstu.

Każde wymaganie używane do automatycznego planowania powinno mieć co najmniej:

- identyfikator wymagania;
- placówkę;
- opis dla człowieka;
- typ wymagania;
- zakres obowiązywania;
- datę początku;
- opcjonalną datę końca;
- informację, kogo lub czego dotyczy;
- skutek dla planowania;
- status aktywności;
- źródło lub notatkę koordynatora.

### 10.3. Minimalne typy wymagań

Pierwszy model powinien umieć wyrazić co najmniej:

**Wymagany typ zmiany**
- np. wyłącznie zmiany 12-godzinne.

**Zakaz przypisania pracownika**
- np. pracownik X nie może być na dniówce w określonych dniach.

**Dozwolone przypisanie tylko w określonym czasie**
- np. pracownik może być używany tylko na nockach albo tylko w weekendy.

**Wymaganie dotyczące dnia**
- np. ograniczenie obowiązuje tylko w dni pracy zakładu.

**Wymaganie czasowe**
- obowiązuje od daty A do daty B.

Nie budujemy na tym etapie uniwersalnego języka reguł dla wszystkich możliwych klientów.

### 10.4. Twarde i miękkie wymagania

Każde wymaganie musi być sklasyfikowane jako:

- `TWARDE` — nie wolno go naruszyć przy tworzeniu zatwierdzonego grafiku;
- `MIĘKKIE` — program powinien je preferować, ale może pokazać wariant naruszający je, jeśli bez tego nie da się uzyskać lepszego rozwiązania.

Domyślnie ograniczenie opisane przez koordynatora jako warunek umowy ze zleceniodawcą powinno być traktowane jako kandydat do reguły `TWARDEJ`, ale jego status musi być świadomie zatwierdzony.

### 10.5. Kolejność ważności źródeł

Wymagania Zleceniodawcy nie mogą automatycznie przebić:

1. twardych przepisów prawa;
2. zatwierdzonych twardych nieobecności;
3. innych twardych ograniczeń pracownika.

Jeżeli wymaganie zleceniodawcy jest sprzeczne z wyższą regułą, program nie może „rozwiązać” konfliktu przez jej złamanie.

Powinien zgłosić konflikt przed lub podczas generowania grafiku.

### 10.6. Konflikt wymagań

Przykład:

- zleceniodawca nie chce pracownika A na dniówkach;
- pozostali pracownicy są niedostępni;
- dniówka musi być obsadzona.

Jeżeli nie istnieje legalny i zgodny z pozostałymi twardymi regułami wariant, wynik powinien być:

`Brak rozwiązania przy aktualnych wymaganiach Zleceniodawcy i dostępnej obsadzie.`

Program powinien wskazać, które wymaganie uczestniczy w konflikcie.

Nie wolno po cichu ignorować wymagania tylko po to, aby domknąć grafik.

### 10.7. Wymagania nierozpoznane

Koordynator może wpisać nowe wymaganie, którego program jeszcze nie potrafi odwzorować w strukturze.

Takie wymaganie:
- zostaje zapisane jako opis;
- otrzymuje status `WYMAGA_ROZSTRZYGNIĘCIA`;
- nie jest automatycznie interpretowane przez solver;
- musi zostać przełożone na znany typ reguły albo świadomie dodane jako nowy rodzaj ograniczenia.

To chroni przed sytuacją, w której program zgaduje znaczenie zdania z umowy lub ustnej instrukcji.

### 10.8. Wersjonowanie

Wymagania Zleceniodawcy są wersjonowane.

Program powinien przechowywać:
- wersję obowiązującą dla danego okresu;
- datę zmiany;
- poprzednią wartość;
- osobę wprowadzającą zmianę;
- opcjonalne uzasadnienie lub źródło.

Grafik powinien dać się powiązać z wersją wymagań, na podstawie której został przygotowany.

### 10.9. Miejsce w miesięcznym procesie

Kolejność wejść do planowania powinna być następująca:

1. wymagania placówki i Zleceniodawcy;
2. roczny plan urlopów;
3. inne zatwierdzone urlopy i twarde nieobecności;
4. zaakceptowane dni wolne;
5. pozostałe twarde ograniczenia pracowników;
6. reguły miękkie;
7. przygotowanie grafiku.

Wymagania Zleceniodawcy są więc częścią danych wejściowych grafiku, a nie korektą nakładaną dopiero na gotowy wynik.

---

## 11. Pamięć zasad obiektu — element pierwszego pilota

Warstwa pamięci jest częścią pierwszego pilota.

Jej celem nie jest prowadzenie kadr ani zastępowanie solvera.

Jej celem jest zwolnienie koordynatora z konieczności pamiętania wszystkich lokalnych zasad obowiązujących na obiekcie.

Przy wielu obiektach koordynator może znać dziesiątki wyjątków, ograniczeń i ustaleń. Program powinien je zachować i automatycznie przywołać przy przygotowaniu kolejnego grafiku.

### 11.1. Co pamięć ma przechowywać

W pierwszym pilocie pamięć powinna obejmować co najmniej:

- wymagania Zleceniodawcy;
- lokalne zasady obiektu;
- potwierdzone wyjątki;
- zmiany zasad w czasie;
- źródło zasady albo krótką notatkę, skąd ona pochodzi;
- status zasady;
- okres obowiązywania;
- informację, czy zasada jest twarda, miękka czy tylko informacyjna.

Przykłady:

- `Na tym obiekcie obowiązują wyłącznie zmiany 12-godzinne.`
- `Pracownik A nie może być na dniówkach od poniedziałku do piątku.`
- `Od 1 października wymaganie dotyczące pracownika A przestaje obowiązywać.`
- `Na obiekcie wymagane jest określone uprawnienie.`

### 11.2. Zasady są przypisane do obiektu

Każda reguła pamięci musi być przypisana do konkretnego obiektu.

W pierwszym pilocie istnieje tylko jeden obiekt, ale model nie może zakładać, że zasada jest globalna dla całej firmy.

To przygotowuje produkt do rzeczywistej pracy koordynatora obsługującego wiele obiektów bez budowania jeszcze wielopunktowego grafiku.

### 11.3. Pamięć nie jest swobodną notatką solvera

Pamięć może przechowywać tekst źródłowy lub opis dla człowieka, ale solver nie powinien sam interpretować dowolnego tekstu.

Reguła wpływająca na grafik musi mieć postać strukturalną, którą program potrafi jednoznacznie zastosować.

Jeżeli koordynator zapisze nową zasadę, której program jeszcze nie rozumie, pozostaje ona:

`WYMAGA_ROZSTRZYGNIĘCIA`

i nie jest automatycznie używana przez solver.

### 11.4. Aktywne zasady są przywoływane automatycznie

Przy rozpoczęciu grafiku dla danego miesiąca program powinien automatycznie zebrać aktywne zasady obiektu obowiązujące w tym okresie.

Koordynator nie powinien co miesiąc wpisywać ich ponownie ani pamiętać, że musi je ręcznie odszukać.

Przed generowaniem grafiku program pokazuje krótkie podsumowanie:

`Aktywne zasady obiektu`

z możliwością sprawdzenia szczegółów.

### 11.5. Pamięć i solver mają różne role

Warstwa pamięci odpowiada za:
- zachowanie zasady;
- jej historię;
- źródło;
- okres obowiązywania;
- status;
- przypomnienie jej we właściwym momencie.

Solver odpowiada za:
- zastosowanie aktywnej, strukturalnej reguły;
- wykrycie konfliktu;
- ocenę wykonalności grafiku.

Pamięć nie układa grafiku.

Solver nie jest magazynem wiedzy o obiekcie.

### 11.6. Zmiana zasady nie usuwa historii

Jeżeli wymaganie lub lokalna zasada zmieni się:

- stara wersja pozostaje w historii;
- nowa wersja otrzymuje własny okres obowiązywania;
- grafik powinien dać się powiązać z zestawem zasad obowiązujących w chwili jego przygotowania.

Nie wolno po cichu nadpisywać wcześniejszej reguły tak, jakby nigdy nie istniała.

### 11.7. Wyjaśnienie „dlaczego”

Dla ograniczenia wpływającego na grafik koordynator powinien móc sprawdzić:

`Dlaczego program tego nie pozwala?`

Program powinien wskazać konkretną aktywną zasadę, np.:

`Pracownik A nie może zostać przypisany do dniówki 12 września, ponieważ na tym obiekcie obowiązuje wymaganie Zleceniodawcy WZ-03.`

To ma ograniczać sytuacje, w których koordynator pamięta, że „chyba była taka zasada”, ale nie jest pewien jej treści.

### 11.8. Minimalny zakres pilota

Warstwa pamięci w pierwszym pilocie nie musi zawierać:

- modeli językowych;
- automatycznego wnioskowania z dokumentów;
- wyszukiwania semantycznego;
- automatycznej interpretacji umów;
- wspólnej pamięci wielu firm;
- synchronizacji chmurowej.

Wystarczy lokalna, trwała, wersjonowana pamięć zasad obiektu, powiązana z regułami używanymi przez solver.

### 11.9. Wykorzystanie istniejącego Elnath Memory Engine

Istniejący `elnath-memory-engine` może być kandydatem na techniczną bazę tej warstwy, ponieważ przechowuje wersjonowane rekordy, relacje, źródła i historię zmian.

Decyzja o jego użyciu nie jest jeszcze zamrożona.

Przed wykorzystaniem należy sprawdzić, czy:
- można użyć tylko potrzebnego podzbioru;
- nie wymusza zbędnej złożoności;
- pamięć obiektu da się odseparować od operacyjnej bazy grafiku;
- adaptacja będzie prostsza niż napisanie minimalnej warstwy pamięci od zera.

Do pilota obowiązkowa jest funkcja pamięci, a nie konkretny istniejący silnik.

### Zasada nadrzędna: bez biurokracji

Rota pyta wyłącznie o dane konieczne do:
- utworzenia grafiku;
- zastosowania reguły;
- policzenia godzin;
- wyjaśnienia konfliktu na poziomie wystarczającym do decyzji.

Wszelkie opisy, uzasadnienia, źródła i komentarze są fakultatywne, chyba że bez konkretnej informacji program nie potrafi jednoznacznie zastosować reguły.

Program może zapytać:
`Czy chcesz dodać powód / notatkę?`

Odpowiedź `nie` nie blokuje dalszej pracy.

Jeżeli program może sam wygenerować czytelny opis z danych strukturalnych, nie powinien wymagać od koordynatora ponownego wpisywania tego samego tekstem.

---

## 12. Tworzenie grafiku

Koordynator wybiera miesiąc i przygotowuje dane wejściowe.

### Zapotrzebowanie obiektu

Zapotrzebowanie na pracę wynika z obsady obiektu.

Dla pilota:
- każdego dnia potrzebna jest jedna obsada `D 05:00–17:00`;
- każdego dnia potrzebna jest jedna obsada `N 17:00–05:00`;
- suma tych zmian tworzy stałą pulę godzin do obsadzenia w danym miesiącu.

Solver nie tworzy godzin po to, aby „dobić” pracownikom normę.

Najpierw istnieje realne zapotrzebowanie obiektu, a następnie solver rozdziela tę pracę pomiędzy dostępnych pracowników.

Każde ponowne generowanie może zmienić rozkład przyszłych godzin całej załogi, jeżeli zmieniły się dane wejściowe, np. doszedł nowy pracownik, ktoś zachorował albo zmieniła się dostępność.

Program przed generowaniem pokazuje:
- wymaganą pulę zmian / godzin obiektu;
- aktywną lokalną pulę pracowników;
- aktywne zasady obiektu;
- urlopy i potrzeby wolnego;
- miesięczne cele godzin;
- bilans godzin do uwzględnienia;
- oczywiste braki obsady wykryte we wstępnej kontroli.

Solver układa wyłącznie standardowe zmiany:
- `D 05:00–17:00`;
- `N 17:00–05:00`.

Każda normalna zmiana wymaga jednego pracownika podstawowego.

### Zamrożone przypisania koordynatora

Koordynator może wskazać konkretne przyszłe przypisanie, którego solver nie może zmienić przy ponownym generowaniu grafiku.

Przykład:
`22 sierpnia, D — Pracownik A — ZAMROŻONE`

Dla solvera takie przypisanie jest twardym ograniczeniem wejściowym.

Solver:
- zachowuje wskazanego pracownika na wskazanej zmianie;
- układa pozostałą część grafiku wokół tego przypisania;
- jeżeli zamrożenie powoduje konflikt z inną regułą albo uniemożliwia pełny grafik, informuje o tym koordynatora;
- nie zdejmuje zamrożenia samodzielnie.

Koordynator może:
- zamrozić pojedynczą zmianę;
- zamrozić wiele przyszłych zmian;
- zdjąć zamrożenie i ponownie uruchomić solver.

Zamrożenie jest decyzją planistyczną koordynatora, a nie trwałą cechą pracownika ani obiektu.

Zmiany już zrealizowane nie wymagają zamrożenia — są historią i z definicji nie podlegają ponownemu planowaniu.

Jeżeli zaplanowano szkolenie, do tej samej zmiany można dodać drugiego pracownika oznaczonego `S`.

`S` nie wypełnia wymogu obsady samodzielnie.

Wyjątkowe, skrócone lub przesunięte godziny są ręczną korektą koordynatora podczas trwającego miesiąca, nie wynikiem solvera.

---

## 13. Twarde reguły grafiku

W Rota pojęcie `TWARDA REGUŁA` oznacza regułę twardą dla automatycznego działania solvera, a nie bezwzględną blokadę koordynatora.

Solver:
- nie może samodzielnie naruszyć twardej reguły, chyba że dana reguła została wprost sklasyfikowana jako dopuszczalna do automatycznego nagięcia;
- nie może ukryć naruszenia;
- jeżeli bez naruszenia nie istnieje rozwiązanie, ma zgłosić konflikt i przedstawić możliwe działania.

Koordynator:
- może ręcznie zrobić odstępstwo od reguły;
- musi zobaczyć jednoznaczne ostrzeżenie;
- odstępstwo jest jawnie zapisane w wersji grafiku;
- przy finalizacji musi świadomie potwierdzić listę odstępstw.

Do reguł chronionych przez solver w pilocie należą co najmniej:
- dokładnie jeden pracownik podstawowy na wymaganej zmianie; dodatkowy pracownik `S` jest dozwolony wyłącznie jako szkolony i nie zastępuje obsady podstawowej;
- profil `TYLKO_DNIÓWKI`;
- brak 24 godzin pracy bez przerwy;
- urlop;
- `NIEDOSTĘPNOŚĆ_24H`;
- twarde Wymagania Zleceniodawcy;
- wymagane kwalifikacje, jeżeli okażą się potrzebne;
- poprawne traktowanie zmian przechodzących przez północ;
- reguły czasu pracy potwierdzone w audycie prawnym.

### Polityka kompromisów i decyzji HARD

Solver nie używa jednej wspólnej hierarchii, która pozwalałaby automatycznie „kupić” naruszenie reguły HARD większym kosztem.

Automatyczna funkcja jakości może porównywać wyłącznie rozwiązania dopuszczalne bez odblokowania HARD. Do miękkich kryteriów należą w szczególności:
- unikanie `N,N`, jeżeli istnieje równie dobre rozwiązanie bez takiego układu;
- unikanie `D,D`, jeżeli istnieje równie dobre rozwiązanie bez takiego układu;
- unikanie nocki przed zgłoszonym `DAY_SHIFT_OFF`, jeżeli inne rozwiązanie jest dostępne;
- możliwie dobre dopasowanie do celu godzin;
- możliwie równy podział pracy weekendowej;
- unikanie kolizji z `LEAVE_PLAN`, który jest ostrzeżeniem planistycznym, a nie blokadą.

`N,N` i `D,D` są dozwolonymi układami pracy. `N,N` jest obecnie łatwiejszym kompromisem niż `D,D`, ale oba pozostają kryteriami SOFT, nie naruszeniem prawa ani automatycznym powodem odrzucenia grafiku.

Reguł chronionych / HARD solver sam nie odblokowuje. Dotyczy to między innymi:
- pracy 24 godzin bez przerwy;
- nocki dla aktywnego `DAY_ONLY`;
- `LEAVE_GRANTED`;
- `UNAVAILABLE_24H`;
- twardych Wymagań Zleceniodawcy;
- użycia X/Y bez aktywnego, potwierdzonego zakresu;
- innych aktywnych reguł HARD.

Jeżeli pełne pokrycie grafiku wymagałoby takiego ruchu, solver przechodzi do stanu wymagającego decyzji koordynatora. Może wskazać możliwe odblokowania HARD, ale nie wykonuje ich sam.

### Krytyczne obciążenie 60 h / 7 kolejnych dni

Rota kontroluje każde ruchome okno siedmiu następujących po sobie dni, a nie tydzień kalendarzowy.

Jeżeli proponowany pełny grafik powoduje u któregokolwiek pracownika więcej niż `60 h` pracy w dowolnych siedmiu kolejnych dniach:
- solver nie przedstawia takiego wyniku jako zwykłego zakończonego `FEASIBLE`;
- wskazuje pracownika, zakres siedmiu dni i sumę godzin;
- informuje, że pełne pokrycie przy aktualnej obsadzie wymaga ekstremalnego obciążenia;
- przechodzi do decyzji koordynatora.

Koordynator może świadomie zaakceptować takie obciążenie albo zmienić dostępne zasoby, np. udostępnić X/Y lub świadomie przywrócić pracownika z wolnego/urlopu. Dopiero po tej decyzji solver ponownie przelicza grafik.

Kontrola używa rzeczywistych godzin Assignment, nie samej liczby symboli D/N.

---

## 14. Granica miesiąca

Miesiąc jest widokiem użytkownika, ale nie może być granicą poprawności.

Program musi uwzględniać:
- końcówkę poprzedniego miesiąca;
- początek następnego miesiąca,

jeżeli wpływa to na możliwość zaplanowania zmian lub odpoczynku.

Przykład:
- nocka 31 sierpnia kończy się 1 września;
- nie wolno analizować jej tak, jakby kończyła się wraz z sierpniem.

---

## 15. Wynik pracy programu

Automatyczne planowanie ma trzy stany operacyjne:

### A. FEASIBLE — istnieją poprawne propozycje
Solver przygotował co najmniej jeden pełny grafik spełniający wszystkie aktywne HARD oraz nieprzekraczający niezaakceptowanego progu krytycznego obciążenia.

Solver nie musi wybierać jednego „ostatecznego” grafiku. Może zwrócić do `3` kompletnych, dobrych propozycji spełniających HARD i uszeregowanych według kryteriów SOFT.

UI pokazuje propozycje koordynatorowi. Koordynator wybiera i zatwierdza jedną z nich.

Wszystkie propozycje muszą być pełnymi grafikami, a nie częściowymi szkicami. Różnice jakości powinny być widoczne, np. bilans godzin, rozkład weekendów, N,N / D,D i inne ostrzeżenia SOFT.

### B. DECISION_REQUIRED — bez odblokowania HARD / decyzji krytycznej nie ma akceptowalnego grafiku
Solver nie znalazł pełnego akceptowalnego grafiku przy aktualnie dostępnej obsadzie i aktywnych ograniczeniach albo znalazł wyłącznie pełne grafiki przekraczające próg `60 h` w ruchomym oknie 7 dni.

To nie jest awaria ani terminalny FAIL. Solver powinien wtedy wskazać:
- które zmiany / okresy są problemem;
- którzy pracownicy lub reguły blokują obsadę;
- czy problemem jest krytyczne obciążenie i w jakim ruchomym oknie 7 dni;
- jakie jawne decyzje koordynatora mogą odblokować dalsze planowanie.

Przykładowe opcje odblokowania:
- potwierdzić i dodać zakres dostępności X/Y;
- świadomie przywrócić pracownika z wolnego lub urlopu;
- świadomie wyłączyć / nadpisać ograniczenie takie jak `DAY_ONLY`;
- świadomie zaakceptować krytyczne obciążenie ponad `60 h` w siedmiu kolejnych dniach;
- wykonać inną ręczną korektę dopuszczoną przez koordynatora.

Solver nie wybiera żadnej z tych opcji sam. Po decyzji koordynatora wejście PlanningState zostaje zmienione i solver uruchamia się ponownie.

### C. TECHNICAL_ERROR
Program sam uległ błędowi. Błąd techniczny nie może być przedstawiony jako brak obsady, decyzja wymagana ani poprawny grafik.

### Wstępna kontrola obsady przed pełnym liczeniem

Przed uruchomieniem pełnego układania Rota wykonuje prostą kontrolę, czy z danych wejściowych wynika oczywisty strukturalny brak ludzi.

Przykład:
- dwie osoby wypadają na cały miesiąc;
- pozostała lokalna pula nie jest w stanie pokryć wszystkich wymaganych zmian.

W takim przypadku program powinien ostrzec przed pełnym liczeniem:

`Przy obecnej obsadzie prawdopodobnie potrzebne jest wsparcie zewnętrzne na cały miesiąc.`

Wstępna kontrola nie zastępuje właściwego solvera i nie może fałszywie deklarować poprawnego grafiku. Ma jedynie wcześnie wykrywać oczywiste braki strukturalne.

### Wsparcie zewnętrzne

Pracownik zewnętrzny jest rozwiązaniem ostatecznym.

Wsparcie zewnętrzne może dotyczyć:
- jednej konkretnej zmiany;
- kilku dni;
- tygodnia;
- całego miesiąca.

Rota powinien wskazać potrzebny zakres wsparcia, jeżeli można go wiarygodnie ustalić.

Przykłady:
- `Potrzebny pracownik zewnętrzny na nockę 14 sierpnia.`
- `Potrzebne wsparcie zewnętrzne od 12 do 18 sierpnia.`
- `Przy obecnej obsadzie potrzebne jest wsparcie zewnętrzne przez cały miesiąc.`

Solver nie przypisuje X/Y automatycznie.

Koordynator najpierw uzyskuje zgodę / potwierdzenie dostępności.

Po potwierdzeniu wybiera:
`Dodaj wsparcie zewnętrzne`

i określa zakres dostępności X/Y.

Od tego momentu X lub Y staje się normalnym kandydatem solvera wyłącznie w potwierdzonym zakresie, bez modelowania jego macierzystego obiektu.

Program może także wskazać, że jedyną drogą do zamknięcia grafiku jest świadome odstępstwo od konkretnej reguły. Decyzję podejmuje wyłącznie koordynator.

### C. Błąd techniczny
Program sam uległ błędowi.

Błąd techniczny nie może być przedstawiony jako brak rozwiązania ani jako poprawny grafik.

---

## 16. Ręczne poprawki

Koordynator może ręcznie zmienić przypisanie pracownika także wtedy, gdy zmiana narusza regułę, której solver sam nie mógłby naruszyć.

Po każdej materialnej zmianie program ponownie sprawdza grafik.

Jeżeli powstaje odstępstwo:
- program pokazuje je natychmiast;
- wskazuje pracownika, dzień/zmianę i naruszoną regułę;
- nie cofa automatycznie decyzji koordynatora;
- oznacza wersję jako `ROBOCZA_Z_ODSTĘPSTWAMI`.

Przykładowe odstępstwa:
- `Pracownik A pracuje mimo wcześniej zgłoszonego wolnego`;
- `Pracownik B ma dwie nocki pod rząd`;
- `Pracownik C ma ciąg pracy 24h`;
- `Pracownik D został zaplanowany w okresie zatwierdzonego urlopu`;
- `Przekroczono miesięczny cel godzin`.

Program jest narzędziem decyzyjnym, nie nadrzędnym decydentem.


### Zamrożenie ręcznej decyzji

Po ręcznym przypisaniu pracownika koordynator może wybrać:
`Zamroź przypisanie`

Od tej chwili kolejne uruchomienie solvera traktuje tę decyzję jako twarde ograniczenie.

Samo ręczne przypisanie nie musi automatycznie oznaczać zamrożenia. Koordynator decyduje, czy chce zachować je przy następnym przeliczeniu.

---

## 17. Zatwierdzenie grafiku

Program rozróżnia co najmniej cztery stany:

- `ROBOCZY`;
- `ROBOCZY_Z_ODSTĘPSTWAMI`;
- `FINALNY_BEZ_ODSTĘPSTW`;
- `FINALNY_Z_ODSTĘPSTWAMI`.

Domyślnie wersja z wykrytym konfliktem pozostaje robocza.

Koordynator może oznaczyć ją jako finalną, ale przed zapisem program musi wyświetlić pełną listę odstępstw od aktywnych reguł i wymagać świadomego potwierdzenia.

Odstępstwa powinny być kategoryzowane co najmniej jako:
- `PRAWO`;
- `WYMAGANIE_ZLECENIODAWCY`;
- `URLOP_LUB_WOLNE`;
- `GODZINY`;
- `PREFERENCJA`.

Nie wszystkie kategorie mają tę samą wagę.

Program nie może przedstawiać preferencji typu `N,N` jako równoważnej konfliktowi z prawem.

Koordynator może opcjonalnie podać krótki powód odstępstwa.

Program może zapytać:
`Czy chcesz podać powód?`

Podanie powodu nie jest wymagane do zapisu.

Po potwierdzeniu wersja otrzymuje status:
`FINALNY_Z_ODSTĘPSTWAMI`

Historia zachowuje:
- listę odstępstw;
- ich kategorie;
- opcjonalny powód;
- kto je zaakceptował;
- kiedy je zaakceptowano;
- do której wersji grafiku należały.

### Wydruk

Na samym wydruku grafiku nie pokazujemy:
- listy odstępstw;
- powodów;
- kategorii konfliktów;
- historii decyzji.

Wydruk zawiera grafik i potrzebną legendę.

Informacje o odstępstwach pozostają w programie.

---

## 18. Godziny pracy

Pierwsza firma pracuje operacyjnie na kwartale kalendarzowym:
- styczeń–marzec;
- kwiecień–czerwiec;
- lipiec–wrzesień;
- październik–grudzień.

Przy układaniu konkretnego miesiąca koordynator pracuje na miesięcznej docelowej liczbie godzin dla każdego pracownika.

Docelowa liczba godzin jest parametrem planistycznym, a nie zamrożoną liczbą godzin przypisaną w konkretnej wersji grafiku.

Program oddzielnie przechowuje:
- cel godzin;
- godziny zaplanowane w aktualnej wersji;
- godziny już zrealizowane.

Punktem wyjścia jest miesięczna norma czasu pracy obowiązująca dla danego miesiąca.

Ponieważ zmiany w pilocie mają 12 godzin, miesięczna norma nie musi być podzielna przez 12.

Przykład:
- norma: `176h`;
- 14 zmian = `168h`;
- 15 zmian = `180h`.

Różnica względem miesięcznego celu jest zapamiętywana w bilansie.

Miesięczny cel godzin nie jest bezwzględnym limitem.

Jeżeli pełny grafik wymaga przekroczenia celu:
- solver może użyć nadgodzin jako rozwiązania o niższej jakości;
- program pokazuje przekroczenie;
- koordynator świadomie je akceptuje przy finalizacji.

### Narastający bilans

Rota prowadzi dla każdego pracownika:
- bilans miesiąca;
- narastający bilans bieżącego kwartału;
- nierozliczony bilans pozostający po zakończeniu kwartału, jeżeli taki istnieje w praktyce firmy.

Po zakończeniu marca Rota nie kasuje automatycznie informacji o pozostałych godzinach.

Przed kwietniowym grafikiem może pokazać np.:

`Pracownik A: nierozliczone +12h z poprzedniego kwartału. Ustal cel godzin na nowy miesiąc.`

Program nie ustala sam, w jaki sposób te godziny mają zostać prawnie rozliczone. Koordynator ustala nowy cel.

### Uwaga prawna do zweryfikowania w audycie

Nie zapisujemy jako uniwersalnej reguły prawnej, że każda nadgodzina może być automatycznie „oddana” w następnym kwartale.

Aktualny Kodeks pracy rozróżnia co najmniej:
- czas wolny udzielany na wniosek pracownika;
- czas wolny udzielany z inicjatywy pracodawcy.

Dla czasu wolnego udzielanego bez wniosku pracownika Kodeks wskazuje termin najpóźniej do końca okresu rozliczeniowego.

Dlatego Rota ma pamiętać nierozliczone godziny i przypominać o nich, ale przed zamrożeniem reguły prawnej trzeba potwierdzić dokładny sposób stosowany przez firmę.

To nadal jest pamięć operacyjna potrzebna do grafiku, a nie pełny system kadrowo-płacowy.

---

## 19. Zapis i wersje

Dane są przechowywane lokalnie.

Program zapisuje wersje grafiku i nie nadpisuje po cichu poprzedniej wersji finalnej.

Jeżeli w trakcie miesiąca pojawia się choroba, awaria obsady, wyjątkowe skrócenie zmiany albo inna materialna zmiana:
- dotychczasowy grafik pozostaje w historii;
- koordynator tworzy nową wersję;
- nowa wersja zawiera stan po korekcie;
- program ponownie sprawdza reguły i odstępstwa.

Wyjątkowa ręczna zmiana godzin konkretnej pracy, np. 05:00–13:00, jest zapisywana w tej nowej wersji wraz z rzeczywistymi godzinami.

Program powinien umożliwiać:
- odtworzenie wcześniejszej wersji;
- rozpoznanie, która wersja jest aktualnie obowiązująca;
- backup lokalnych danych.

Zatwierdzony wcześniej grafik nie może zniknąć po późniejszej korekcie miesiąca.

---

## 20. Wydruk

Program ma przygotować czytelny miesięczny grafik i pozwalać koordynatorowi poprawiać go bezpośrednio w programie.

Na pierwszy pilot nie wymagamy warstwy Excel/XLSX.

Minimalny rezultat:
- czytelny widok miesięczny;
- możliwość ręcznej korekty w programie;
- możliwość wydruku lub utworzenia prostego dokumentu do wydruku.

Dokładny format techniczny wydruku pozostaje do zamknięcia.

Legenda zawiera wyłącznie oznaczenia rzeczywiście użyte w danym grafiku.

---

## 21. Logi diagnostyczne

Pierwszy tester może zgodzić się na lokalne logowanie diagnostyczne.

Program niczego nie wysyła automatycznie.

Po wybraniu:
`Przygotuj paczkę diagnostyczną`

program tworzy plik ZIP do ręcznego wysłania.

Logi mogą zawierać:
- wersję programu;
- wersję systemu;
- czas zdarzenia;
- nazwę operacji;
- wynik operacji;
- kody błędów;
- techniczne informacje o awarii;
- wyniki walidacji.

Domyślnie nie powinny zawierać:
- imion i nazwisk;
- szczegółów medycznych;
- treści całego grafiku;
- haseł;
- tokenów;
- pełnej bazy danych.

---

## 22. Obserwacja pracy w święta — opcja pilota

Ta funkcja nie jest kryterium ukończenia pierwszego pilota, ale jest pożądaną opcją, jeżeli można ją dodać bez komplikowania rdzenia.

### Weekendy — miękka sprawiedliwość operacyjna

W obrębie miesiąca solver powinien próbować rozdzielać pracę weekendową możliwie proporcjonalnie między pracowników.

To nie jest reguła prawa pracy. Jest to polityka operacyjna firmy, która ma ograniczać sytuacje budzące niesnaski, np.:
- jeden pracownik ma 8 zmian weekendowych;
- inny ma 2.

Jako kryterium SOFT solver porównuje rozkład pracy weekendowej z idealnie równym podziałem możliwym dla danej puli pracowników. Im bliżej idealnej równowagi, tym wyżej oceniany jest wariant. Wariant wyraźnie bliższy równowadze nie może otrzymać gorszej oceny weekendowej od wariantu bardziej nierównego. Nie jest wymagane osiągnięcie matematycznej identyczności, jeżeli uniemożliwiają ją inne ograniczenia.

Pracownik z profilem `TYLKO_DNIÓWKI` również uczestniczy w weekendowej sprawiedliwości poprzez dniówki weekendowe.

Solver nie powinien próbować wyrównywać mu nocek, których profil domyślnie nie przewiduje.

Szkolenia `S` odbywają się wyłącznie od poniedziałku do piątku, więc nie wchodzą do statystyki sprawiedliwości weekendowej.

### Klasyfikacja weekendowej nocki

Dla statystyki weekendowej nocka jest liczona jako weekendowa, jeżeli jakakolwiek część jej czasu przypada na sobotę lub niedzielę.

W szczególności:
- piątek 17:00 → sobota 05:00 = zmiana weekendowa;
- sobota 17:00 → niedziela 05:00 = zmiana weekendowa;
- niedziela 17:00 → poniedziałek 05:00 = zmiana weekendowa.

Ta klasyfikacja służy wyłącznie miękkiej ocenie sprawiedliwości weekendów.

### Święta — miękka sprawiedliwość historyczna

Program powinien obserwować i pamiętać, kto pracował w dniach świątecznych.

Cel nie jest prawny ani kadrowy. Jest to polityka operacyjna firmy wynikająca z tego, że nierównomierne obciążenie pracą w święta jest szczególnie odczuwalne przez pracowników.

Dla każdego Assignment przypadającego na dzień oznaczony `holiday=true` program przypisuje tę pracę do historii obciążenia świątecznego pracownika.

Przy układaniu kolejnych grafików solver:
- automatycznie otrzymuje kalendarz świąt oraz historię wcześniejszych Assignmentów świątecznych w `PlanningState`;
- traktuje równomierność pracy w święta jako kryterium `SOFT`;
- preferuje warianty, które zmniejszają różnicę historycznego obciążenia świątecznego pomiędzy pracownikami mogącymi legalnie i operacyjnie obsadzić daną zmianę;
- nigdy nie narusza `HARD`, aby poprawić sprawiedliwość świąteczną;
- nie wymaga od koordynatora ręcznego prowadzenia osobnego rejestru tego, kto pracował w święta.

Historia świąteczna wynika z trwałych danych programu: `Assignment + Employee + CalendarDay(holiday=true)`.

Źródło informacji o tym, które dni są świętami, jest technicznym elementem kalendarza programu. Solver nie odczytuje bezpośrednio pliku CSV/JSON; dostaje gotowe dane kalendarza w `PlanningState`.

Na wydruku grafiku nie pokazujemy historii świąt ani analizy sprawiedliwości.

---

## 23. Test przeciwniczy

Tester zostanie poproszony o celowe utrudnianie pracy programu.

Przykładowo może:
- dać wielu osobom wolne tego samego dnia;
- nałożyć urlopy;
- usunąć dostępnego pracownika;
- próbować przypisać osobę podczas chorobowego;
- próbować ustawić sprzeczne zmiany;
- zmieniać dane po utworzeniu grafiku;
- próbować zatwierdzić grafik z brakiem;
- zamknąć program podczas zapisu;
- wprowadzać błędne dane.

Celem nie jest udowodnienie, że program zawsze zrobi grafik.

Celem jest udowodnienie, że:
- gdy poprawny grafik istnieje, program potrafi go utworzyć;
- gdy nie istnieje, program to uczciwie zgłasza;
- gdy sam się zepsuje, nie udaje sukcesu;
- nigdy nie przedstawia błędnego grafiku jako poprawnego.

---

## 24. Kryterium wersji „prostej, ale nie prostackiej”

Program jest wystarczająco dobry, jeżeli po jego użyciu koordynator otrzymuje gotowy, sprawdzony grafik.

Program jest zbyt prostacki, jeżeli koordynator nadal musi sam:
- pamiętać urlopy;
- szukać konfliktów;
- liczyć godziny;
- sprawdzać braki;
- pilnować granic miesięcy;
- tworzyć własne kopie bezpieczeństwa;
- poprawiać wynik w Excelu.

---

## 25. Pierwszy tester

Pierwszym testerem jest osoba, która zna rzeczywistą pracę i czasami przygotowuje grafiki także dla wielu punktów.

W pierwszym pilocie testuje jednak tylko tę jedną placówkę.

Jego uwagi służą do:
- znalezienia błędów;
- wykrycia rozjazdu z realną praktyką;
- oceny wygody;
- przygotowania programu do późniejszej prezentacji osobie decyzyjnej.

Pozytywna opinia testera nie oznacza automatycznie zgody firmy na wdrożenie.

---

## 26. Otwarte punkty przed zamrożeniem

Do rozstrzygnięcia pozostają:

1. dokładne pozostałe reguły czasu pracy wynikające z audytu prawnego, ale tylko te, które materialnie zmieniają możliwość przypisania pracownika do zmiany; operacyjny kontrakt pilota przyjmuje już minimum 11 h odpoczynku między zmianami oraz dopuszcza N,N;
2. dokładny status prawny i sposób rozliczania godzin pozostających po końcu okresu rozliczeniowego w tej konkretnej firmie;
3. dokładny format wydruku;
4. dane jednego lub dwóch zanonimizowanych historycznych miesięcy od testera;
5. technologia programu — do decyzji osobno, po analizie technicznej.

Rozstrzygnięte:
- zapotrzebowanie pochodzi ze stałej puli godzin / zmian wymaganych przez obiekt;
- solver rozdziela tę pulę pomiędzy dostępnych pracowników;
- wejście nowego pracownika może spowodować ponowny podział całej jeszcze niezrealizowanej puli zmian pomiędzy wszystkich dostępnych pracowników;
- zaplanowane godziny wszystkich pracowników mogą się wtedy zmienić;
- godziny już zrealizowane pozostają niezmienne;
- Rota rozróżnia cel godzin, godziny zaplanowane i godziny zrealizowane;
- koordynator może zamrażać konkretne przyszłe przypisania; solver traktuje je jako twarde ograniczenie do czasu ręcznego odblokowania;
- solver może po wejściu nowego pracownika przebudować pozostały grafik;
- solver planuje tylko standardowe D 05–17 i N 17–05;
- wyjątkowe inne godziny są ręczną korektą w trwającym miesiącu;
- późniejsza korekta tworzy nową wersję i nie usuwa poprzedniego grafiku;
- szkolenie `S` jest krótką obecnością szkoleniową, typowo 4h × 2;
- szkolenia S odbywają się od poniedziałku do piątku;
- szkolenie jest wliczane do czasu pracy szkolonego;
- koordynator dopisuje `S` do istniejącej zmiany PRIMARY mentora i określa konkretne godziny szkolenia; dzień i D/N wynikają z wybranej zmiany;
- po dwóch zakończonych szkoleniach Rota domyślnie oznacza pracownika jako gotowego do samodzielnej pracy, z możliwością ręcznej zmiany przez koordynatora;
- `S` nie zastępuje wymaganej obsady;
- weekendowa nocka liczy się jako weekendowa, jeżeli zahacza o sobotę lub niedzielę;
- szkolenia S nie wchodzą do sprawiedliwości weekendowej;
- X/Y nie wymagają rozbudowanego modelu kadrowego;
- `TYLKO_DNIÓWKI` jest stałą cechą możliwą do wyłączenia;
- solver może zwrócić do 3 pełnych propozycji spełniających HARD; koordynator wybiera ostateczny wariant;
- weekend fairness jest kryterium SOFT nagradzającym bliskość idealnie równego podziału;
- każde ruchome okno 7 kolejnych dni jest kontrolowane pod kątem obciążenia; ponad 60 h wymaga decyzji koordynatora;
- brak normalnego rozwiązania prowadzi do `DECISION_REQUIRED`, nie do terminalnego FAIL;
- solver wskazuje możliwe odblokowania HARD, ale sam nie używa X/Y, nie ściąga z wolnego/urlopu, nie wyłącza chronionych ograniczeń i nie akceptuje krytycznego obciążenia;
- opisy, uzasadnienia, źródła i komentarze są fakultatywne;
- Rota ma nadrzędną zasadę minimalizacji biurokracji.

---

## 27. Audyt wpływu prawa na sam grafik

Celem audytu prawnego nie jest budowanie w Elnath Rota warstwy kadrowej, płacowej ani systemu obsługi prawa pracy.

Celem jest odpowiedź na węższe pytanie:

> **Które przepisy rzeczywiście zmieniają możliwość przypisania konkretnego pracownika do konkretnej zmiany?**

Jeżeli przepis nie wpływa na układanie grafiku, nie powinien powodować rozbudowy rdzenia programu.

### 27.1. Klasyfikacja każdego przepisu

Każdy istotny przepis klasyfikujemy do jednej z trzech grup:

**A — wpływa bezpośrednio na grafik**

Przykładowo:
- minimalny odpoczynek;
- maksymalny dopuszczalny czas pracy w stosowanym systemie;
- zakaz lub ograniczenie konkretnego przypisania;
- kwalifikacja wymagana do obsady konkretnego stanowiska.

Taka reguła może wejść do walidatora lub solvera.

**B — wpływa na proces firmy, ale nie na układ zmian**

Przykładowo:
- część obowiązków dokumentacyjnych;
- obowiązki kadrowe;
- rozliczenia niewpływające na możliwość wykonania konkretnej zmiany.

Takiej reguły nie implementujemy w rdzeniu grafiku tylko dlatego, że istnieje w prawie.

**C — nie ma materialnego wpływu na pierwszy pilot**

Regułę dokumentujemy jako sprawdzoną, ale nie tworzymy dla niej funkcji programu.

### 27.2. Zasada minimalnego modelu

Elnath Rota przechowuje wyłącznie te cechy pracownika lub placówki, które są potrzebne do:

- ustalenia dostępności;
- sprawdzenia legalności przypisania;
- wyboru pomiędzy kandydatami;
- policzenia godzin potrzebnych do oceny grafiku.

Nie tworzymy pełnego profilu kadrowego pracownika.

Jeżeli dla konkretnej placówki potrzebna jest kwalifikacja, wystarczy minimalna informacja typu:
`posiada_wymaganą_kwalifikację = tak/nie`
albo równoważna cecha domenowa.

Nie kopiujemy do Rota całej dokumentacji potwierdzającej tę kwalifikację.

### 27.3. Najważniejszy test: czy legalny grafik był wykonalny

Przed zamrożeniem architektury należy przeprowadzić próbę na kilku rzeczywistych, zanonimizowanych miesiącach.

Dla każdego miesiąca potrzebujemy w miarę możliwości:
- listy pracowników dostępnych do tej placówki;
- znanych urlopów i nieobecności;
- zgłoszonych i zaakceptowanych wolnych;
- rzeczywistego grafiku;
- zasad czasu pracy obowiązujących tę grupę.

Następnie sprawdzamy, czy przy tych samych danych można było utworzyć grafik spełniający twarde przepisy.

Możliwe wyniki:

**Wynik 1 — istniał poprawny wariant, ale rzeczywisty grafik łamał regułę**

To wskazuje przede wszystkim na:
- niewiedzę;
- przyzwyczajenie;
- ręczny błąd;
- wygodę;
- niewystarczającą kontrolę przy układaniu.

W takim przypadku Rota może realnie usunąć problem przez walidację i lepszą propozycję.

**Wynik 2 — przy tej samej liczbie ludzi nie istniał żaden poprawny grafik**

To wskazuje na problem strukturalny:
- za mała obsada;
- zbyt wiele twardych nieobecności;
- sprzeczne ograniczenia;
- niewystarczająca pula osób do zapewnienia ciągłej obsady.

Wtedy problemu nie wolno „naprawiać” przez łamanie prawa w solverze.

Program powinien powiedzieć:
`Nie da się ułożyć poprawnego grafiku przy obecnej obsadzie i ograniczeniach.`

To jest wartościowy wynik biznesowy, a nie awaria programu.

**Wynik 3 — pozorne naruszenie jest legalne dzięki rzeczywiście stosowanemu wyjątkowi lub systemowi czasu pracy**

Wtedy należy:
- potwierdzić, że wyjątek rzeczywiście dotyczy tej grupy;
- zapisać tylko minimalną regułę potrzebną solverowi;
- nie przedstawiać legalnej praktyki jako naruszenia.

### 27.4. Szczególne znaczenie ochrony

Pierwszy audyt ma sprawdzić między innymi, jaki system czasu pracy jest rzeczywiście stosowany wobec pracowników tej placówki.

Kodeks pracy przewiduje szczególne rozwiązania dla pracowników zatrudnionych przy pilnowaniu mienia lub ochronie osób.

Samo występowanie zmian 12-godzinnych nie może więc zostać uznane przez program za naruszenie bez ustalenia stosowanego systemu czasu pracy.

Jednocześnie szczególny system nie oznacza braku ograniczeń dotyczących odpoczynku.

Dlatego przed implementacją należy ustalić:
- jaki system czasu pracy obowiązuje pierwszą grupę;
- jaki okres rozliczeniowy jest stosowany;
- jakie minimalne odpoczynki wynikają z tego systemu;
- czy istnieją firmowe wyjątki lub profile mające realny wpływ na przypisanie.

### 27.5. ZPChr bez automatycznej warstwy kadrowej

Sam fakt działania firmy jako zakładu pracy chronionej nie oznacza, że Rota ma stać się systemem obsługi niepełnosprawności.

Audyt ma sprawdzić tylko, czy status lub konkretny przepis zmienia możliwość zaplanowania pracy.

W szczególności trzeba uwzględnić, że przepisy o czasie pracy osób z niepełnosprawnościami zawierają wyjątek dla osób zatrudnionych przy pilnowaniu.

Dopiero po ustaleniu rzeczywistej sytuacji pracowników pierwszej placówki zdecydujemy, czy jakakolwiek cecha związana z tym statusem jest w ogóle potrzebna solverowi.

### 27.6. Ochrona osób i mienia

Ustawa o ochronie osób i mienia jest istotna dla grafiku tylko w takim zakresie, w jakim konkretne zadanie lub placówka wymaga określonych kwalifikacji pracownika ochrony.

Jeżeli pierwsza placówka nie wymaga rozróżnienia kwalifikacyjnego do obsadzenia jej zwykłej zmiany, nie tworzymy rozbudowanego modułu kwalifikacji.

Jeżeli wymaga — kwalifikacja staje się prostym twardym warunkiem obsady.

### 27.7. Pytanie badawcze dla konsultanta

Przed kodowaniem chcemy wraz z konsultantem odpowiedzieć na pytanie:

> **Gdy koordynator nagina regułę, czy robi to dlatego, że jej nie zna lub przeoczył lepsze rozwiązanie, czy dlatego, że przy dostępnej liczbie pracowników poprawny grafik nie istnieje?**

Nie zakładamy odpowiedzi z góry.

Odpowiedź ma wynikać z:
- realnych historycznych grafików;
- realnej dostępności;
- rzeczywistych zasad;
- próby znalezienia poprawnego wariantu.

### 27.8. Warunek przed zamrożeniem architektury

Przed zamrożeniem architektury musimy znać:

1. przepisy, które materialnie wpływają na przypisanie do zmiany;
2. rzeczywiście stosowany system czasu pracy pierwszej grupy;
3. minimalny zestaw danych potrzebnych do egzekwowania tych reguł;
4. wynik przynajmniej kilku historycznych prób wykonalności;
5. listę kwestii, które są wyłącznie kadrowe i świadomie pozostają poza Rota.

Architektura robocza może powstać wcześniej.

Architektura zamrożona nie powinna powstać, dopóki nie wiemy, czy prawo zmienia rdzeń samego problemu układania grafiku.

---

## 28. Status dokumentu

To jest pierwszy polski kandydat specyfikacji produktu.

Nie opisuje Elnath Ward.

Proces tworzenia programu, role modeli, bramki, audyty, format zadań i sposób prowadzenia pipeline zostaną opisane dopiero na podstawie aktualnej dokumentacji Elnath Ward.

