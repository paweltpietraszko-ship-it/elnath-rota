# Przekazanie do architekta: backlog UX #6, #7 i #8

STATUS: INPUT FOR ARCHITECT — bez kodu produktu, bez gotowego kontraktu
implementacyjnego. Bazą jest `main@4b7618d7339ab64d78bf1ed99c0665e9c661bea4`.

Źródła:

- `arch/FINDING_2026-09-03_PERIODIC_TRAINING_S1.md` — pozycja #6;
- `arch/FINDING_2026-09-03_GLOBAL_WORKING_MONTH.md` — pozycja #7;
- `arch/FINDING_2026-09-03_UNACCEPTED_PLAN_PREVIEW.md` — pozycja #8.

Numery #6–#8 oznaczają pozycje backlogu projektu. Nie są numerami GitHub
Issues ani Pull Requests.

## Czego oczekujemy od architekta

1. Przeczytać każdy finding i sprawdzić opisany stan w aktualnym kodzie.
   Finding jest materiałem wejściowym, a nie zatwierdzonym projektem.
2. Traktować trzy sprawy osobno. Nie tworzyć jednego dużego tasku obejmującego
   szkolenie, wspólny miesiąc i trwałość wyniku PLAN.
3. Nie implementować i nie refaktoryzować przy okazji. Najpierw opisać po
   polsku najprostsze rozwiązanie korzystające z istniejących mechanizmów.
4. Wszystkie brakujące decyzje widoczne dla użytkownika przedstawić Pawłowi
   prostym językiem: kiedy sytuacja występuje, co zobaczy koordynator, co
   zostanie zapisane i co stanie się po błędzie lub ponowieniu operacji.
5. Dopiero po decyzjach OWNERA przygotować osobne, możliwie małe kontrakty
   wykonawcze. Każdy kontrakt ma wskazywać istniejącego właściciela logiki,
   minimalny `TASK_SCOPE` i mały pionowy test realnego przepływu. Nie powielać
   logiki produktu w testach.

## #6 — okresowe szkolenie S1

### Ustalenia OWNERA, których nie wolno rozszerzać

- S1 oznacza szkolenie okresowe i jest czymś innym niż istniejące szkolenie
  osoby wdrażanej do pracy.
- Koordynator ustawia przedział godzin S1 i może wpisać S1 pracownikowi w
  planowaniu miesiąca. Nie ma sztywnej długości szkolenia.
- S1 ma być widoczne na grafiku i wydruku, a jego godziny mają być policzone.
- Rota pozostaje programem do grafików. Nie ma sprawdzać, czy szkolenie się
  odbyło, prowadzić ewidencji szkoleń, dopuszczać pracownika do obsady na
  podstawie szkolenia ani budować modułu kadrowego.
- Nie wolno przy tej okazji zmieniać istniejącej obsługi osoby szkolonej
  (`TRAINEE`) ani procesu dodawania do obsady.

### Zadanie architekta

Wskazać najmniejszy istniejący mechanizm, w którym można zapisać i pokazać S1
bez udawania zwykłego zapotrzebowania D/N i bez rozbudowy kadrowej. Osobno
wyjaśnić Pawłowi tylko te kwestie, których powyższe decyzje nie rozstrzygają,
zwłaszcza wpływ godzin S1 na odpoczynek i pozostałe limity czasu pracy oraz
czy S1 wstawia wyłącznie koordynator, czy może je proponować solver. Nie
przyjmować odpowiedzi samodzielnie.

## #7 — jeden miesiąc roboczy programu

### Ustalenie OWNERA

Koordynator wybiera miesiąc raz, a ekrany dotyczące pracy nad grafikiem mają
używać tego samego miesiąca. Nie powinien ponownie wybierać października na
każdym ekranie. Lista rzeczywistych miesięcy oczekujących decyzji w ekranie
„Decyzje” nie jest takim selektorem i nie należy jej na siłę zmieniać.

### Zadanie architekta

Przed projektem podać dokładną listę ekranów i funkcji objętych wspólnym
miesiącem. Zaproponować najprostsze miejsce selektora, wykorzystując obecny
układ aplikacji, i prostym językiem wyjaśnić:

- czy wybór pamięta się tylko podczas przechodzenia między ekranami, czy także
  po odświeżeniu aplikacji;
- co dzieje się po zmianie obiektu;
- czy którykolwiek ekran ma uzasadniony wyjątek;
- czy opis okresu na wydruku wynika z miesiąca, czy pozostaje osobnym tekstem.

Nie łączyć tego automatycznie z większą przebudową lub konsolidacją ekranów.
To wymagałoby osobnej decyzji OWNERA.

## #8 — wynik PLAN przed zatwierdzeniem

### Ustalenie OWNERA

Po wykonaniu PLAN koordynator ma móc odejść z ekranu lub odświeżyć aplikację,
a następnie wrócić do dokładnie tego samego wyniku i zobaczyć, że grafik nie
został jeszcze zatwierdzony. Sam komunikat ostrzegawczy nie wystarcza.
Ponowne uruchomienie solvera nie jest odtworzeniem poprzedniego wyniku.

### Zadanie architekta

Najpierw prześledzić obecny cykl `PLAN -> kandydat -> zatwierdzenie -> wersja`
i wskazać, gdzie najmniejszym kosztem można trwale zachować dokładny wynik
PLAN. Nie zakładać z góry nowego `ScheduleStatus`, jeśli istniejący mechanizm
można bezpiecznie wykorzystać. Jednocześnie nie wolno mutować zatwierdzonego
grafiku ani historii.

Przed kontraktem wykonawczym architekt ma wyjaśnić Pawłowi i uzyskać decyzje
co najmniej o tym:

- czy zapamiętujemy jeden ostatni wynik, czy wszystkie pokazane warianty;
- co kolejny PLAN albo REPLAN robi z poprzednim niezatwierdzonym wynikiem;
- jak koordynator świadomie odrzuca taki wynik;
- gdzie wynik jest widoczny i jak odróżnia się go od zatwierdzonego grafiku;
- co się dzieje, gdy zapis lub odczyt nie powiedzie się.

## Oczekiwany rezultat

Najpierw trzy krótkie odpowiedzi architektoniczne — osobna dla #6, #7 i #8 —
z wyraźnym podziałem na zachowanie już zatwierdzone oraz decyzje, których
brakuje. Po odpowiedziach OWNERA: osobne taski/gałęzie, zaczynając od
najmniejszej zmiany. Każdy task przed implementacją trafia do niezależnego
audytu Codexa.
