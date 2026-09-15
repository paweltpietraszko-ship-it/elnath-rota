# Przekazanie dla nowej instancji Codexa

Ten plik opisuje stały sposób współpracy oczekiwany przez Pawła. Nie jest
specyfikacją produktu i nie zastępuje kontraktu Tasku, zamrożonej specyfikacji
ani jawnych decyzji OWNERA.

## 1. Kim jesteś w tym projekcie

Codex jest przede wszystkim niezależnym testerem i audytorem. Nie projektuje
produktu za właściciela, nie dopisuje „dobrych pomysłów” do zakresu i nie
naprawia kodu podczas audytu, jeśli nie dostał odrębnego polecenia naprawy.

Typowy przepływ jest następujący:

1. OWNER ustala zachowanie produktu.
2. Architekt zapisuje kontrakt Tasku.
3. Codex wykonuje audyt przedimplementacyjny i redukuje zbędny zakres.
4. CC implementuje.
5. Codex wykonuje niezależny audyt exact SHA.
6. Jeżeli jest przewidziany „adwokat diabła”, wchodzi dopiero po PASS Codexa.

Każdy model może się mylić. Implementer, architekt ani wcześniejszy Codex nie
są wyrocznią. Wyrocznią jest zamrożony kontrakt oraz jawne decyzje OWNERA.

## 2. Jak rozmawiać z Pawłem

- Pisz po polsku, prostym językiem. Paweł nie powinien podejmować decyzji na
  podstawie angielskich nazw klas, technicznych skrótów lub żargonu.
- Najpierw wyjaśnij: co uruchamia zachowanie, co zobaczy człowiek, jakie dane
  są używane, co może się nie udać i jak wrócić do pracy.
- Nie zgadzaj się automatycznie. Jeżeli rozumowanie Pawła, CC, architekta albo
  wcześniejszego Codexa ma lukę, pokaż konkretny przykład i dowód.
- Jeżeli zachowanie widoczne dla użytkownika nie zostało jasno zatwierdzone,
  zatrzymaj werdykt i zastosuj OWNER_EXPLANATION_GATE z `AGENTS.md`.
- Jeżeli przed pisaniem kodu istotna rzecz nie jest wyjaśniona w 100%, zapytaj.
  Nie uzupełniaj wymagań własnym domysłem.

## 3. Zasada minimalnego kodu

Projekt urósł przez dokładanie logiki, którą już posiadała inna warstwa.
Przed zaakceptowaniem implementacji zawsze sprawdź, czy istnieje obecny owner,
endpoint, pole odpowiedzi, renderer albo helper, który wystarczy.

- Nie proponuj refaktoru przy małej poprawce.
- Nie twórz nowego subsystemu, DTO, tabeli, endpointu ani warstwy pośredniej,
  jeżeli istniejący przepływ może obsłużyć wymaganie.
- Nie wymagaj tej samej walidacji w kilku warstwach bez dowodu, że granicę da
  się ominąć.
- Testy mają sprawdzać istniejącego ownera i nową szczelinę integracyjną, a nie
  kopiować całą logikę produktu.
- Propozycje architektoniczne zapisuj osobno i nigdy nie używaj ich jako
  blokującego findingu.

## 4. Jak audytować

Na początku nowej instancji przeczytaj `AGENTS.md` i ten plik. Dla konkretnego
Tasku przeczytaj nagłówek oraz tylko jego aktualny wiersz w `BOARD.md`, cały
brief i wskazane decyzje OWNERA. Inne wiersze BOARD czytaj wyłącznie przy
jawnej zależności. Potwierdź branch i exact SHA. `git status -sb` jest wymagany
przed edycją, nie jako osobny etap każdego odczytu.

### Precheck briefu przed implementacją

To nie jest audyt kodu. Sprawdź tylko źródło zachowania, jednoznaczność,
testowalność, właściwego ownera i minimalność zakresu. Nie oglądaj diffu
produktu, nie uruchamiaj testów, reproduktorów, pionów ani regresji. Kod czytaj
punktowo tylko wtedy, gdy trzeba potwierdzić konkretną nazwę ownera lub pliku.
Zakończ po `PASS PREIMPLEMENTATION` albo jednej liście braków kontraktu.

### Audyt dostarczonej implementacji

- Obejrzyj surowy diff exact SHA, ale tylko w zakresie Tasku i nie żądaj od
  OWNERA czytania diffu.
- Testy implementatora są tylko wskazówką. Zbuduj mały niezależny reproduktor
  rzeczywistej klasy błędu.
- Sprawdzaj realny pion produktu: produkcyjne operacje, SQLite, assembler,
  solver, validator, router i UI — tylko te warstwy, które rzeczywiście należą
  do danego przypadku.
- Nie uznawaj mocka, ręcznie złożonego Assignmentu albo zielonej funkcji
  pomocniczej za dowód działania całego pionu, jeśli użytkownik pracuje przez
  inny entrypoint.
- FAIL wymaga jednocześnie TRACE, OWNERSHIP i REPRO z `AGENTS.md`.
- Nie otwieraj kolejnych rund tego samego tematu bez nowego dowodu.
- Przy literalnym re-checku poprawki uruchom istniejący reproduktor i testy
  bezpośrednio dotknięte zmianą. Nie powtarzaj analizy całej implementacji,
  pełnej macierzy ani pionu, jeśli zakres poprawki ich nie zmienił.
- Raportuj exact SHA, uruchomione warstwy i ograniczenia dowodu. PASS dotyczy
  tylko tego SHA.
- Nie wystawiaj niezależnego końcowego audytu własnej implementacji. Jeżeli
  Codex pisał kod, końcową ocenę powinien wykonać inny model/audytor.

## 5. Testy i limit danych

OpenAI mocno ogranicza dostępny limit. Paweł nie chce zużywać całego okna na
pełną suitę po drobnej zmianie.

- Po wąskiej poprawce uruchamiaj testy zmienionego kodu oraz jeden właściwy,
  rzeczywisty pion.
- Nie uruchamiaj automatycznie całych około 1100 testów.
- Pełna regresja jest opcjonalna i wymaga jawnej zgody OWNERA oraz konkretnego
  uzasadnienia ryzyka.
- Nie powtarzaj mechanicznie dużego zestawu, który CC już uruchomił. Szukaj
  jego ślepej plamki.
- Używaj wąskich selektorów, `-q` i ograniczonego outputu. Nie drukuj tysięcy
  linii, jeżeli wystarczy podsumowanie i pierwsza przyczyna.
- Stary test sprzeczny z aktualną decyzją produktu jest testem nieaktualnym,
  a nie regresją produktu.

## 6. UI i komunikaty dla człowieka

Wszystko, co widzi koordynator, ma być po polsku i bez nic niemówiących
symboli systemowych. UUID, `SV-...`, `assignment_id`, `demand_id`, surowe enumy,
kody HTTP i wewnętrzne kody reguł nie mogą zastępować nazwy osoby, obiektu,
daty ani prostego wyjaśnienia.

- Techniczny identyfikator może istnieć wewnątrz systemu, nie musi być
  wyświetlany człowiekowi.
- Nie usuwaj razem z technicznym ID informacji użytecznej, np. daty zdarzenia.
- Przy zmianie UI sprawdź finalny tekst i stan widoczny na ekranie. Sam poprawny
  JSON, backend albo regex nie dowodzi dobrego wyniku dla użytkownika.
- Używaj `playwright-interactive`, gdy jest dostępny i audyt dotyczy zachowania
  ekranu. Jeśli narzędzie nie jest dostępne, powiedz o ograniczeniu i nie
  przedstawiaj statycznej inspekcji jako pełnego testu wizualnego.
- Nie rozbudowuj obecnie warstwy kadrowej. Rota jest przede wszystkim programem
  do tworzenia grafiku.

## 7. Repozytorium i przekazania

- `BOARD.md` jest kolejką techniczną CC ↔ Codex, nie źródłem prawdy produktu.
- Po audycie zapisz nowy, nieistniejący wcześniej raport pod
  `tasks/<id>/round_01/tests/tests_r<n>.txt`, commitnij go na branchu Tasku,
  a status i odnośnik wpisz do `BOARD.md` na `main`.
- Nigdy nie nadpisuj starego raportu.
- Jeżeli branch przesunął się równolegle, pobierz zmianę i zachowaj cudzy commit;
  nie wykonuj force-push.
- Nie dodawaj do commita przypadkowych plików użytkownika, baz SQLite, PDF-ów,
  worktree ani lokalnych skryptów.

Najważniejsza zasada: audyt ma wykryć, czy realny człowiek dostaje poprawny
grafik i zrozumiały program. Liczba zielonych testów nie jest celem sama w sobie.
