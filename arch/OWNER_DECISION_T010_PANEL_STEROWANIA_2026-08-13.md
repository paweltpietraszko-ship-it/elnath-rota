# ROTA — decyzja właściciela: T010 / Panel Sterowania

DATA: 2026-08-13
STATUS: OWNER DECISION / aneks produktu przed briefem ROTA-T010
BAZA: main `51b71725186fa30be23219e94aa135bb69bc5bce`

## 1. Zmiana kierunku T010

ROTA-T010 nie jest już zadaniem dotyczącym parsera języka naturalnego.

Parser i sterowanie Rotą żywym językiem są usunięte z zakresu produktu. Koordynator nie ma przekazywać reguł przez swobodny tekst, a program nie ma zgadywać jego intencji.

Konfigurowalne decyzje koordynatora mają być przekazywane jawnie przez UI.

## 2. Nazwa i rola miejsca konfiguracji

W UI miejsce skupiające konfigurowalne zasady programu nazywa się **Panel Sterowania**.

Panel Sterowania jest jednym, rozpoznawalnym miejscem, w którym koordynator szuka ustawień wpływających na działanie Roty.

Panel Sterowania NIE jest drugim źródłem logiki biznesowej i NIE przechowuje równoległej kopii prawdy. Jeżeli dana funkcja już istnieje w domenie, warstwie aplikacyjnej lub persistence, panel ma ją tylko udostępnić przez prostą bramkę/podpięcie do istniejącej operacji.

Duplikowanie istniejącego stanu albo logiki tylko dlatego, że funkcja pojawia się w Panelu Sterowania, jest błędem architektonicznym.

## 3. Bieżąca lista pracowników obiektu

Panel Sterowania musi pozwalać koordynatorowi:

- dodać pracownika do bieżącej listy pracowników obiektu;
- usunąć pracownika z bieżącej listy pracowników obiektu.

"Usunięcie pracownika" w tym miejscu NIE oznacza fizycznego kasowania Employee ani historycznych danych.

Po usunięciu z bieżącej listy:

- nazwisko nie ma pojawiać się w nowych/bieżących grafikach tego obiektu tylko dlatego, że rekord historycznie istnieje;
- wcześniejsze ScheduleVersion, Assignment, rozliczenia i inne dane historyczne pozostają niezmienione i odtwarzalne;
- historia musi nadal jednoznacznie wskazywać pracownika, który wcześniej pracował na obiekcie.

Gdy pracownik odchodzi, koordynator może najpierw wyłączyć jego ogólną dostępność, a następnie usunąć go z bieżącej listy. Program nie usuwa historii.

## 4. Sterowanie dostępnością pracownika

Dla pracownika przypisanego do obiektu Panel Sterowania udostępnia pięć jawnych pozycji:

1. **Ogólna dostępność** — domyślnie włączona.
2. **Dniówka** — domyślnie włączona.
3. **Nocka** — domyślnie włączona.
4. **Dzień tygodnia** — wybór dnia/dni z listy oraz okres obowiązywania.
5. **Szkolenie** — domyślnie wyłączone.

Nie dodaje się osobnej pozycji **Święta**.

## 5. Znaczenie decyzji koordynatora dla solvera

Powyższe ustawienia są bieżącą komunikacją koordynatora z solverem i mają charakter bezwzględny.

Jeżeli obowiązujące ustawienie mówi, że pracownik nie jest dostępny dla danego użycia, solver NIE może tego ustawienia samodzielnie naruszyć w celu ułożenia grafiku.

W szczególności:

- brak Ogólnej dostępności blokuje użycie pracownika w danym okresie;
- wyłączona Dniówka blokuje D;
- wyłączona Nocka blokuje N;
- wyłączony wybrany dzień tygodnia blokuje planowanie w tym dniu w zadanym okresie;
- wyłączone Szkolenie oznacza, że solver nie może sam użyć pracownika jako szkolonego;
- włączone Szkolenie oznacza wyłącznie, że koordynator dopuścił możliwość szkolenia — nie nakazuje solverowi zaplanowania szkolenia.

Jeżeli przy tych decyzjach nie da się stworzyć kompletnego grafiku, solver ma zwrócić brak rozwiązania wymagający działania koordynatora. Nie może sam odblokować pracownika ani zignorować ustawienia.

## 6. Zmiany stałe i okresowe

Ustawienie może wyrażać stan stały albo czasową zmianę z zakresem **od–do**.

Przykład rzeczywisty:

- pracownica normalnie pracuje tylko na dniówkach: D włączone, N wyłączone;
- w sytuacji kryzysowej koordynator włącza N na okres 20–29;
- solver może uwzględnić ją na N wyłącznie w tym okresie;
- po zakończeniu okresowej zmiany wraca wcześniejszy stan, czyli N wyłączone.

Program nie wyprowadza takich decyzji z historii, zachowania pracownika, liczby szkoleń ani własnej oceny sytuacji.

## 7. Ogólna niedostępność i rodzaj nieobecności

Po wyłączeniu Ogólnej dostępności na okres koordynator może wskazać jeden z trzech powodów potrzebnych Rotcie do grafiku i godzin:

- **choroba**;
- **urlop**;
- **nieobecność nieusprawiedliwiona**.

Rota wykorzystuje ten wybór wyłącznie do prawidłowego oznaczenia grafiku i obliczenia godzin.

Dla nieobecności nieusprawiedliwionej solver wpisuje `0` godzin. Konsekwencje kadrowe pozostają całkowicie poza zakresem Roty.

Rota nie ocenia pracownika i nie wykonuje działań kadrowych.

## 8. Program nie decyduje o pracowniku

Koordynator ustanawia reguły dotyczące pracownika. Program je wykonuje i może pokazywać fakty lub ostrzeżenia, ale nie może samodzielnie:

- dopuścić pracownika do samodzielnej pracy;
- odsunąć go od pracy;
- podnieść lub obniżyć jego statusu;
- wyprowadzić uprawnienia z liczby zrealizowanych szkoleń;
- tworzyć nowej reguły o pracowniku na podstawie analizy jego historii.

W szczególności dotychczasowe założenie, że osiągnięcie progu liczby REALIZED TRAINEE automatycznie zmienia pracownika na READY_FOR_PRIMARY, jest uchylone decyzją właściciela. Liczbę szkoleń można policzyć i pokazać koordynatorowi, ale decyzja o dopuszczeniu należy do koordynatora.

## 9. Granica HARD / SOFT / informacja

Ustawienia dostępności opisane w tym aneksie są decyzjami bezwzględnymi dla solvera.

Oddzielnie w produkcie istnieją zasady miękkie: solver powinien ich przestrzegać, ale może je naruszyć, jeżeli inaczej nie stworzy grafiku; takie naruszenie ma być widoczne dla koordynatora.

Informacje nie ograniczają planowania.

Nie wolno mieszać tych trzech znaczeń w Panelu Sterowania.

## 10. Zakres następnego briefu ROTA-T010

Brief ROTA-T010 ma być mały. Nie tworzy uniwersalnego edytora reguł, parsera, DSL, silnika workflow ani nowej warstwy przechowującej kopię danych.

Pierwszy zakres T010 powinien objąć tylko brakujące podpięcia potrzebne do:

- bieżącej listy pracowników obiektu (dodanie / usunięcie bez kasowania historii);
- pięciu ustawień pracownika z sekcji 4;
- okresów od–do i powrotu do wcześniejszego stanu;
- bezwzględnego respektowania tych decyzji przez solver.

Jeżeli istniejący kod już zapewnia część powyższego zachowania, T010 ma go wykorzystać zamiast implementować drugi mechanizm.
