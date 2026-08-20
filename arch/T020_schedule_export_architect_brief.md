# Handoff brief for architect: wydruk grafiku (proponowane ROTA-T020)

## Status dokumentu

To jest handoff faktów i jawnych decyzji właściciela z 2026-08-20. Ma
posłużyć architektowi do napisania właściwego, testowalnego kontraktu T020.
Nie jest jeszcze kontraktem implementacyjnym ani zgodą na rozpoczęcie kodu.

T020 dotyczy wyłącznie przygotowania przejrzystego, statycznego wydruku
grafiku. Nie zmienia solvera, WorkBalance, zasad absencji, cyklu
ScheduleVersion ani pamięci decyzji.

## Cel produktu

Koordynator ma móc wygenerować z Roty czytelny grafik jednego obiektu i
jednego miesiąca, gotowy do wydrukowania i przekazania pracownikom.

Właściciel: po tym dokumencie potencjalny klient będzie oceniał program.
Wydruk musi być prosty, logiczny i czytelny także w czerni i bieli.

Układ branżowy pozostaje punktem odniesienia:

- miesiąc w kolumnach;
- pracownicy w wierszach;
- osobny wiersz PLAN i WYK dla pracownika;
- podsumowania godzin;
- legenda symboli na wydruku.

Realny, lecz nieczytelny wzór firmowy znajduje się w `Grafiki/7442.jpg`.
Nie kopiować go 1:1. Ma on wyjaśniać konwencję branżową i znaczenie
legendy, a nie narzucać finalny wygląd.

## Twarda granica: zmiany wyłącznie w Rocie

Wynikiem T020 ma być statyczny, gotowy do druku PDF.

Nie dostarczamy edytowalnego XLSX. Nie budujemy importu arkusza ani
dwukierunkowej synchronizacji PDF/XLSX z Rotą.

Jeżeli koordynator zauważy błąd lub potrzebę korekty:

1. poprawia grafik w Rocie przez właściwą istniejącą operację;
2. Rota zapisuje zmianę w swoim normalnym modelu i cyklu ScheduleVersion;
3. koordynator generuje nowy PDF z aktualnego stanu.

PDF nigdy nie jest źródłem danych programu. Ręczna zmiana zewnętrznego
pliku nie może zostać uznana za zmianę grafiku w Rocie.

Każdy PDF musi pozwalać rozpoznać, z jakiego stanu powstał. Musi zawierać
co najmniej:

- identyfikację obiektu i miesiąca;
- rzeczywisty zakres dat, niezależny od edytowalnej etykiety miesiąca;
- identyfikator current ScheduleVersion albo równoważną, jednoznaczną
  proweniencję zestawu wersji użytych do złożenia dokumentu;
- osobny identyfikator/numer rewizji dokumentu;
- czas wygenerowania.

Papierowego wydruku nie da się fizycznie unieważnić po zmianie grafiku.
Identyfikator rewizji ma jednak pozwolić koordynatorowi jednoznacznie
rozpoznać starszy dokument jako nieaktualny.

## PLAN i WYK — decyzja właściciela

Rota nie jest programem kadrowym ani rejestrem przewinień pracowników.
Wydruk ma pokazywać prawidłowy, aktualny grafik, a nie wskazywać, kto
wcześniej nie przyszedł do pracy.

PLAN może zmienić się w trakcie miesiąca:

- nowa wersja obowiązuje od jawnego `ScheduleVersion.effective_from`;
- dni wcześniejsze zachowują plan, który wtedy obowiązywał;
- dzień rozpoczęcia obowiązywania i przyszłość pokazują nowy plan;
- WYK zmienia się razem z właściwą korektą planu;
- ręczna korekta jednej dzisiejszej zmiany nie uruchamia REPLAN całego
  miesiąca.

Przykład wiążący: A miał dziś dniówkę, nie przyszedł, a zmianę przejął B.
Po ręcznej korekcie wydruk pokazuje B jako prawidłową obsadę tej zmiany w
aktualnym PLAN/WYK. Poprzednie przypisanie A pozostaje w historii Roty, ale
wydruk nie prezentuje go jako informacji o „bumelce”.

Nie wolno przyjąć uproszczenia `parent ScheduleVersion = PLAN`, `child
ScheduleVersion = WYK`. Dziecko może powstać także przez REPLAN, freeze,
szkolenie, zmianę `effective_from` albo kolejną korektę. Architekt ma
zaprojektować minimalny read model, który odtworzy właściwy stan dla
każdego dnia zgodnie z obowiązującymi wersjami, bez tworzenia drugiego
systemu historii grafiku.

Fakt istniejącego kodu: `rota/application/manual_edit.py` tworzy pełne
dziecko bieżącej ScheduleVersion dla materialnej korekty, zachowuje rodzica
i nie uruchamia automatycznie REPLAN. T020 ma ten mechanizm odczytać, a nie
zastąpić.

## Nagłówek i ustawienia wydruku

Koordynator ustawia te wartości w Rocie, nie w PDF:

- nazwę firmy widoczną na wydruku;
- nazwę obiektu widoczną na wydruku;
- nazwę miesiąca/tytuł okresu.

Nazwa firmy i nazwa obiektu mają być trwałymi wartościami domyślnymi dla
danego Site, ale koordynator może je później zmienić. Zmiana wpływa na nowe
wydruki i nie modyfikuje wcześniej wygenerowanych dokumentów.

Edytowalna etykieta miesiąca nie może zmienić rzeczywistego miesiąca ani
zakresu danych. PDF musi nadal jawnie zawierać prawdziwy zakres dat.

Zmiana samego nagłówka nie jest zmianą grafiku i nie wymaga nowej
ScheduleVersion, ale tworzy nową rewizję dokumentu.

## Zakres godzin i obiektów

Wydruk dotyczy dokładnie jednego Site i jednego miesiąca.

Podsumowania PLAN, WYK, urlopu i chorobowego na wydruku obejmują wyłącznie
godziny pracownika na tym Site. Praca tego samego Employee na innych
obiektach nie może zostać doliczona do wydruku obiektu.

Rota może nadal pokazywać koordynatorowi informację o godzinach pracownika
na innych Site w innych ekranach/read modelach. Jest to sygnał informacyjny.
Nie zmienia wydruku i nie blokuje jego wygenerowania. Koordynator odpowiada
za decyzję, czy dopuścić przekroczenie obserwowanego limitu; T020 nie staje
się systemem kadrowym ani płacowym.

Układ musi pozostać czytelny przynajmniej dla około 10 pracowników i
podwójnej obsady. W kodzie nie istnieje twardy limit liczby pracowników na
Site, dlatego implementacja nie może zakładać dokładnie siedmiu wierszy z
obecnego mockupu.

## Obsługiwane reżimy zmian

Pierwsza wersja T020 ma obsługiwać:

- obiekty działające w podstawowym reżimie 12h;
- obiekty działające w podstawowym reżimie 24h.

`INNY` jest jawnie poza pierwszym zakresem T020. Jeżeli bieżący dokument
wymaga przedstawienia zmiany `INNY`, generator nie może jej po cichu
pominąć ani wyprodukować nieprawdziwego PDF. Kontrakt implementacyjny ma
ustalić jawny, bezpieczny komunikat „ten typ wydruku nie jest jeszcze
obsługiwany”.

Reżim godzin Site jest regułą wyższego rzędu dla prezentacji absencji:

- na obiekcie 12h używa się denominacji właściwych dla reżimu 12h;
- zaznaczenie pracownikowi `can_work_24h` tego nie zmienia;
- obiekt 12h z awaryjną możliwością 24h nadal rozpisuje urlop i chorobowe
  według reżimu 12h;
- denominacji 24h wolno użyć dopiero na obiekcie działającym zasadniczo w
  reżimie 24h.

Nie wolno dobierać kodów absencji na podstawie samego `can_work_24h` ani
wyłącznie dlatego, że kod 24h daje krótszy zapis.

## Legenda — wiążące wartości właściciela

Kody legendy są konwencją prezentacyjną. Solver nie przypisuje kodów
`D1..D5`, `N1..N5`, `U1..U5` ani `C1..C5` i T020 nie może przenosić tej
logiki do solvera.

Każdy pełny kod ma własną wartość. Numer nie oznacza wspólnej wartości dla
wszystkich liter. Tabela jest niesymetryczna i na tym etapie celowo jej nie
„naprawiamy”:

| Kod | Wartość | Kod | Wartość | Kod | Wartość | Kod | Wartość |
|---|---:|---|---:|---|---:|---|---:|
| D1 | 12h | N1 | 12h | U1 | 12h | C1 | 12h |
| D2 | 4h  | N2 | 16h | U2 | 16h | C2 | 16h |
| D3 | 24h | N3 | 24h | U3 | rezerwa | C3 | rezerwa |
| D4 | 2h  | N4 | 24h | U4 | rezerwa | C4 | rezerwa |
| D5 | 24h | N5 | 24h | U5 | rezerwa | C5 | rezerwa |

Rezerwa oznacza zdefiniowany slot bez przypisanej wartości, a nie usunięty
kod. Koordynator może w Rocie przypisać wartość wolnemu slotowi. Taka
konfiguracja musi być trwała i używana deterministycznie przez następne
wydruki danego Site/reżimu.

Zdjęcie źródłowe zawiera przy kodach D/N także godziny rozpoczęcia i
zakończenia. Kontrakt architektoniczny ma jawnie ustalić mapowanie realnego
interwału Assignment na kod legendy. Nie wolno klasyfikować dowolnego
czterogodzinnego interwału jako `D2` wyłącznie na podstawie długości, jeżeli
konfiguracja legendy wiąże kod z innymi godzinami rozpoczęcia/zakończenia.

## Urlop i chorobowe na wydruku

T020 nie zmienia T018 ani `arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md`.
WorkBalance nadal otrzymuje poprawnie policzone godziny urlopu i L4 według
obowiązującej zasady 8h za kwalifikowany dzień roboczy. T020 jedynie
przedstawia wynik w papierowej konwencji symboli.

Automatyczny wybór symboli:

1. korzysta wyłącznie z niezerowych denominacji dozwolonych przez
   podstawowy reżim godzin danego Site;
2. szuka dokładnej sumy godzin;
3. wybiera kombinację z najmniejszą liczbą symboli;
4. przy wielu równie krótkich kombinacjach używa jednej jawnej,
   deterministycznej kolejności;
5. rozmieszcza symbole deterministycznie w pierwszych kwalifikujących się
   dniach nieobecności.

Przykład wiążący właściciela dla 40h urlopu:

- PLAN: `D1 / D1 / N2` = `12 + 12 + 16 = 40h`;
- WYK pod tymi samymi pozycjami: `U1 / U1 / U2` = `12 + 12 + 16 = 40h`.

Jeżeli dokładna dekompozycja nie istnieje, program nie może zaokrąglić,
zgadnąć ani użyć niedozwolonego kodu 24h. Przygotowanie wydruku ma zwrócić
koordynatorowi jawny problem do rozstrzygnięcia. Koordynator może w Rocie
wskazać sposób prezentacji, w szczególności przypisać potrzebną wartość do
wolnego slotu legendy. Rozstrzygnięcie ma zostać zapisane w konfiguracji
wydruku, aby ponowne wygenerowanie było deterministyczne. Nie zmienia ono
WorkBalance, Assignment ani ScheduleVersion.

## Układ i druk czarno-biały

Firmy często drukują grafiki czarno-biało. Znaczenie komórki nie może
zależeć wyłącznie od koloru. Kolor może pomagać na ekranie, ale wydruk ma
zachować rozróżnienie przez tekst, obramowanie, wypełnienie lub inny sygnał
widoczny w skali szarości.

Ostateczny rozmiar papieru, paginacja, marginesy i szczegóły typografii nie
są jeszcze decyzją właściciela. Mają zostać ocenione na prawdziwym PDF w
Checkpoint A, zamiast być zgadywane w kodzie produkcyjnym.

Istniejący mockup HTML:

`https://claude.ai/code/artifact/7e68a361-05f1-4c06-9920-710bf2ca3fc2`

jest wyłącznie materiałem pomocniczym. Link zewnętrzny nie jest trwałym
źródłem kontraktu i może być niedostępny dla audytora lub architekta. Przed
zamrożeniem właściwego zadania należy umieścić w repo trwały obraz/PDF
zaakceptowanego mockupu.

## Wymagane dwa checkpointy

### Checkpoint A — prawdziwy szablon PDF, bez integracji produkcyjnej

Przed rozpoczęciem generatora opartego na danych Roty wykonawca dostarcza
do akceptacji właściciela rzeczywiste, możliwe do otwarcia i wydrukowania
próbki PDF:

- reprezentatywny miesiąc obiektu 12h;
- reprezentatywny miesiąc obiektu 24h;
- około 10 pracowników oraz przykład podwójnej obsady;
- PLAN/WYK;
- urlop i chorobowe, w tym wiążące 40h;
- podsumowania i legendę;
- wersję czytelną w czerni i bieli.

Próbki używają kontrolowanych danych demonstracyjnych. Nie wymagają jeszcze
produkcyjnego read modelu ani podłączenia do bazy.

Checkpoint A kończy się jawną akceptacją właściciela. Bez niej nie wolno
rozpoczynać Checkpoint B.

### Checkpoint B — integracja z rzeczywistymi danymi Roty

Dopiero po akceptacji wyglądu:

- powstaje aplikacyjny read model eksportu;
- generator pobiera rzeczywisty Site/miesiąc/wersje/Assignment/absencje;
- konfiguracja nagłówka i legendy jest trwała;
- generowany PDF odpowiada dokładnie aktualnemu stanowi Roty;
- żadne SQL nie trafia do warstwy aplikacyjnej;
- nie powstaje drugi solver, workflow engine, system kadrowy ani import
  dokumentów.

## Minimalna macierz dowodowa dla właściwego kontraktu

Architekt ma przełożyć poniższe przypadki na testowalne acceptance, bez
zmiany ich znaczenia:

1. PDF jednego Site/miesiąca zawiera jednoznaczną proweniencję i rewizję.
2. Zmiana nagłówka w Rocie tworzy nowy dokument, lecz nie ScheduleVersion.
3. Korekta grafiku w Rocie tworzy właściwy aktualny stan; stary PDF pozostaje
   rozpoznawalny jako wcześniejszy.
4. Nowy PLAN od `effective_from` nie zmienia dni wcześniejszych.
5. Jednodniowa ręczna korekta nie uruchamia REPLAN całego miesiąca i wydruk
   pokazuje aktualną prawidłową obsadę, nie historię nieobecnego pracownika.
6. Obiekt 12h generuje czytelny dokument i nie używa kodu 24h tylko dla
   skrócenia zapisu absencji.
7. `can_work_24h=True` na obiekcie o podstawowym reżimie 12h nie zmienia
   denominacji absencji.
8. Obiekt 24h generuje czytelny dokument z właściwą prezentacją okresu 24h.
9. `INNY` kończy się jawnym unsupported, nigdy cichym pominięciem danych.
10. 40h urlopu daje dokładnie PLAN `D1/D1/N2` oraz WYK `U1/U1/U2`.
11. Automatyczna dekompozycja jest minimalna i deterministyczna.
12. Brak dokładnej dekompozycji wymaga decyzji koordynatora; brak
    zaokrąglenia i brak zmiany WorkBalance.
13. Po zapisie konfiguracji wolnego slotu restart programu daje identyczny
    wynik eksportu.
14. Podsumowania nie doliczają godzin tego Employee z innego Site.
15. Wielu pracowników, podwójna obsada i miesiąc 31-dniowy pozostają
    czytelne w czerni i bieli.
16. PDF nie zawiera wspieranego mechanizmu edycji/importu danych grafiku.
17. T020 nie zmienia wyników solvera, T018 ani WorkBalance.

## Otwarte decyzje techniczne dla architekta

Architekt może zdecydować o bibliotece PDF, podziale modułów i szczegółach
read modelu, ale nie może zmienić powyższych decyzji produktu.

Do rozstrzygnięcia technicznego pozostają:

- minimalny trwały model ustawień nagłówka i legendy;
- sposób jednoznacznej identyfikacji rewizji dokumentu;
- odtworzenie dziennego stanu z lineage/effective_from bez fałszywego
  `parent=PLAN / child=WYK`;
- jawna kolejność rozstrzygania remisów dekompozycji;
- mapowanie skonfigurowanych interwałów D/N na symbole;
- sposób renderowania i weryfikacji PDF;
- TASK_SCOPE, migracja, limity plików oraz pełna macierz regresji.

Żadna z tych decyzji technicznych nie może wprowadzić edytowalnego arkusza,
importu PDF/XLSX, logiki kadrowej, nowego naliczania godzin ani alternatywnej
historii grafiku.
