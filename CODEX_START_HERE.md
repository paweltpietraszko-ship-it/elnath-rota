# Przekazanie dla nowej instancji Codexa

Aktualne na dzień 2026-09-04. Ten plik opisuje sposób współpracy oczekiwany
przez Pawła. Nie jest specyfikacją produktu i nie zastępuje kontraktu Tasku,
zamrożonej specyfikacji ani jawnych decyzji OWNERA.

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

Na początku zawsze:

1. przeczytaj `AGENTS.md` i ten plik;
2. przeczytaj aktualne `BOARD.md`;
3. pobierz aktualne referencje i potwierdź branch oraz exact SHA;
4. przeczytaj cały brief i wskazane decyzje OWNERA;
5. sprawdź `git status -sb` i nie dotykaj cudzych plików.

W audycie:

- Obejrzyj surowy diff exact SHA, ale nie żądaj od OWNERA czytania diffu.
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

## 7. Symulator Koordynatora — ważna granica

Symulator nie symuluje solvera i nie ma samemu rozstrzygać jego reguł. Ma
odtwarzać pracę prawdziwego koordynatora:

1. tworzy różne realistyczne obiekty i ich zapotrzebowania;
2. wpisuje rzeczywiste ustawienia przez produkcyjne operacje backendowe,
   tak jak koordynator zaznacza pola i przełączniki;
3. uruchamia produkcyjne PLAN/REPLAN;
4. odbiera to, co solver naprawdę zwrócił;
5. evaluator ocenia gotowy grafik według HARD, SOFT, Kodeksu pracy i
   sprawiedliwości; błędny albo brak grafiku jest wartościowym wynikiem i ma
   zostać zachowany z seedem oraz reproduktorem.

Nie wolno:

- dobierać dowolnie większej załogi tylko po to, aby solver stworzył ładny
  grafik;
- wpisywać z góry, że dany seed „wymaga wsparcia zewnętrznego”;
- ręcznie tworzyć wzorcowego grafiku, Assignmentów lub danych, które omijają
  pracę koordynatora;
- kalibrować całego narzędzia pod jeden miesiąc i kilka sztywnych seedów;
- badać pracownika między wieloma obiektami jak w systemie kadrowym — ta
  funkcja jest obecnie poza produktem.

Obsada ma wynikać z realnej możliwości cyklicznego pokrycia zmian, odpoczynków
i godzin, a nie z prostego dodawania maksimów z poszczególnych dni. Przykład
OWNER: dwie osoby w środę, te same dwie w sobotę i jedna osoba w niedzielę
mogą oznaczać trzy osoby załogi, nie pięć.

Nie zakładaj kanonicznego `target_hours=168`. Wejściowy target ma odpowiadać
rzeczywistemu miesiącowi i decyzji koordynatora. Ocena grafiku ma respektować
rozliczenie kwartalne; przy urlopie albo chorobie sprawiedliwość dotyczy łącznego
wyniku godzin nieobecności i pracy zgodnie z produkcyjną logiką Roty. Symulator
przekazuje dane wejściowe — nie powiela tych obliczeń i nie „pomaga” solverowi.

W narzędziu testowym można przyjąć domyślną zgodę koordynatora na dodanie
EXTERNAL_SUPPORT dopiero po rzeczywistej odpowiedzi produktu, że własna załoga
nie wystarcza. W prawdziwej aplikacji koordynator nadal podejmuje tę decyzję
ręcznie. LOCAL mają być oceniani sprawiedliwie przez produkcyjny solver;
symulator nie może sam liczyć lub poprawiać fairness.

## 8. Repozytorium i przekazania

- `BOARD.md` jest kolejką techniczną CC ↔ Codex, nie źródłem prawdy produktu.
- Po audycie zapisz nowy, nieistniejący wcześniej raport pod
  `tasks/<id>/round_01/tests/tests_r<n>.txt`, commitnij go na branchu Tasku,
  a status i odnośnik wpisz do `BOARD.md` na `main`.
- Nigdy nie nadpisuj starego raportu.
- Jeżeli branch przesunął się równolegle, pobierz zmianę i zachowaj cudzy commit;
  nie wykonuj force-push.
- Nie dodawaj do commita przypadkowych plików użytkownika, baz SQLite, PDF-ów,
  worktree ani lokalnych skryptów.

## 9. Stan przy tym przekazaniu

- Bazowy stan produktu przed commitem tego dokumentu:
  `main@8d07cf1498cb41a75818b65995a2569a47ea444f`.
- ROTA-T055 zostało scalone; bieżące `BOARD.md` nie zawiera nowego wpisu
  `READY_FOR_CODEX`.
- T055 dostarcza ostrzeżenia validatora do ekranu. Późniejsza poprawka
  architekta zachowała użyteczną datę DAY_ONLY przy ukrywaniu technicznych ID.
- Na początku następnej sesji nie zakładaj, że ten SHA nadal jest aktualny:
  wykonaj fetch i ponownie przeczytaj `BOARD.md`.

Najważniejsza zasada: audyt ma wykryć, czy realny człowiek dostaje poprawny
grafik i zrozumiały program. Liczba zielonych testów nie jest celem sama w sobie.
