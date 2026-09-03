# Próba czterech obiektów z `Ochrona.docx`

Data wykonania: 2026-09-03

Kod produktu: `main@6ff5b827ed1530bb3fc4370727fa1e3784269926`

Badany miesiąc: wrzesień 2026

Źródło: repozytoryjny plik `Ochrona.docx`

## Jak wykonano próbę

Każdy obiekt został utworzony w osobnej, syntetycznej bazie przez produkcyjne operacje backendu Roty: utworzenie obiektu, zapis katalogu zmian, kalendarza, pracowników, obsady i `target_hours`, następnie rzeczywisty `PLAN`, wybór pierwszego kandydata oraz produkcyjny eksport PDF. Nie tworzono ręcznie demandów ani Assignmentów. Nie użyto kalkulatora obsady. Liczbę LOCAL zachowano dokładnie z dokumentu: odpowiednio 4, 7, 17 i 3 osoby.

Każdy LOCAL dostał wejściowy `target_hours=176` dla września 2026. To 22 dni robocze po 8 godzin; tabelę 176 godzin dla września 2026 publikuje również [Sąd Apelacyjny w Katowicach](https://katowice.sa.gov.pl/print.php?id=734&p=new). Nieobecności nie zostały dodane, ponieważ dokument ich nie określa.

Jeżeli `PLAN` zwracał rzeczywisty `DECISION_REQUIRED`, dodawano jedną osobę `EXTERNAL_SUPPORT` przez normalne operacje Roty i ponawiano `PLAN`. Nie dodawano nikogo z góry.

Obrazy oznaczone na czerwono jako „WIZUALIZACJA KONTROLNA” nie są produkcyjnym wydrukiem. Powstały 1:1 z Assignmentów zapisanych przez Rotę, ponieważ produkt odmówił dla tych obiektów utworzenia PDF. Pełne dane źródłowe są w `wyniki_surowe.json`.

## Konieczne dostosowania czterech opisów do obecnych możliwości Roty

1. **Plac budowy / Magazyn** — dokumentowa zmiana 17:00–07:00 trwa 14 godzin, a obecny wydruk nie ma kodu 14 h. Użyto jednej ciągłej zmiany 15:00–07:00 (16 h, odpowiadającej istniejącemu N2). Weekend pozostał 07:00–19:00 i 19:00–07:00.
2. **Centrum Handlowe** — układ zachowano bez zmian: poniedziałek–sobota dwie osoby 08:00–20:00 i jedna 20:00–08:00; w niedzielę po jednej osobie na obu zmianach.
3. **Park Logistyczny** — bramę (2 osoby) i patrol (1 osoba) zagregowano do jednej zmiany 24 h z obsadą 3. Recepcję 07:00–17:00 wydłużono do drukowalnego przedziału 07:00–19:00. Obecna Rota nie rozróżnia stanowisk ani kwalifikacji „patrol”/„recepcja”.
4. **Urząd** — obecny katalog nie przyjmuje 06:30 ani 14:30. Odtworzono ten sam profil 16 roboczogodzin i podwójną obsadę w środku dnia jako 06:00–18:00 (12 h) oraz 10:00–14:00 (4 h), od poniedziałku do piątku.

## Wyniki widoczne na grafikach

### 1. Plac budowy / Magazyn

- Wynik `PLAN`: `FEASIBLE` za pierwszym razem.
- Obsada: 4 LOCAL, 0 EXTERNAL_SUPPORT.
- Zapisane godziny: Adam Nowak 144, Ewa Kowalska 128, Marta Wójcik 128, Piotr Zieliński 144. Łącznie 544 h.
- Rota zaakceptowała kandydata i nie zapisała odstępstw.
- Produkcyjny PDF: **nie powstał** — `UNSUPPORTED_SHIFT_KIND`, mimo że ustawienia wydruku mają zamrożony kod N2=16 h.
- Obraz: `01_plac_budowy_obraz_kontrolny.png`.

### 2. Centrum Handlowe

- Wynik `PLAN`: `FEASIBLE` za pierwszym razem.
- Obsada: 7 LOCAL, 0 EXTERNAL_SUPPORT.
- Zapisane godziny: 144 / 144 / 144 / 156 / 144 / 156 / 144. Łącznie 1032 h.
- Rota zaakceptowała kandydata i nie zapisała odstępstw.
- Produkcyjny PDF: **powstał poprawnie**.
- Pliki: `02_centrum_handlowe_grafik_rota.pdf`, jego obraz `02_centrum_handlowe_grafik_rota.png` oraz powiększony obraz kontrolny `02_centrum_handlowe_obraz_kontrolny.png`.

### 3. Park Logistyczny

- Pierwsze cztery wywołania `PLAN`: `DECISION_REQUIRED` z komunikatem o kolizji z tygodniowym czasem pracy (wskazane okna miały 77–84 h).
- Po każdej rzeczywistej decyzji dodano jedną osobę wsparcia. Piąte wywołanie zwróciło `FEASIBLE`.
- Obsada końcowa: 17 LOCAL oraz 4 EXTERNAL_SUPPORT. To ważny rzeczywisty wynik produktu, nie założenie wejściowe.
- LOCAL otrzymali od 108 do 144 h; każda z czterech osób EXTERNAL_SUPPORT otrzymała 96 h. Łącznie zapisano 2424 h.
- Rota zaakceptowała kandydata i nie zapisała odstępstw.
- Produkcyjny PDF: **nie powstał** — `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT` dla 21 widocznych osób.
- Obraz: `03_park_logistyczny_obraz_kontrolny.png`.

### 4. Urząd

- Wynik `PLAN`: `FEASIBLE` za pierwszym razem.
- Obsada: 3 LOCAL, 0 EXTERNAL_SUPPORT.
- Zapisane godziny: Adam 116, Ewa 120, Piotr 116. Łącznie 352 h.
- Rota zaakceptowała kandydata i nie zapisała odstępstw.
- Produkcyjny PDF: **nie powstał** — `UNSUPPORTED_SHIFT_KIND` dla warstwy 4 h, mimo że ustawienia wydruku mają zamrożony kod D2=4 h.
- Obraz: `04_urzad_obraz_kontrolny.png`.

## Co trzeba poprawić w wydruku i wejściu godzin

1. **Godziny co najmniej co 30 minut.** Obecny zapis katalogu przyjmuje wyłącznie pełną godzinę. Przez to poprawnego wejścia 06:30–14:30 z dokumentu nie da się wprowadzić. To ograniczenie wejścia, nie solvera.
2. **Zgodność eksportu z istniejącymi kodami.** Konfiguracja wydruku przyjmuje N2=16 h i D2=4 h, ale produkcyjny eksport odrzucił oba rzeczywiste grafiki jako `UNSUPPORTED_SHIFT_KIND`. Ustawienie, które UI pozwala zapisać, musi być możliwe do wydrukowania.
3. **Wydruk wielostronicowy dla dużej obsady.** Park Logistyczny ma 17 LOCAL, a po decyzjach solvera łącznie 21 osób. Rota nie powinna odmawiać całego wydruku tylko dlatego, że tabela nie mieści się na jednej stronie; potrzebny jest podział na strony z powtórzonym nagłówkiem.
4. **Czytelny podgląd przed pobraniem.** Przy błędzie PDF koordynator nadal powinien móc zobaczyć dokładnie ten sam grafik i przyczynę braku eksportu. W tej próbie konieczne były osobne obrazy kontrolne, bo sam produkt nie udostępnił dokumentu dla trzech z czterech obiektów.

## Ważne ograniczenia tej próby

- Jest to jeden rzeczywisty miesiąc czterech konkretnych obiektów, a nie dowód poprawności wszystkich grafików.
- Produkcyjny `select-candidate` przyjął wszystkie cztery wyniki, co oznacza przejście walidacji HARD należącej do Roty. Obrazy pozostają potrzebne do ludzkiej oceny rytmu i sprawiedliwości; same sumy godzin nie zastępują oględzin.
- Izolowana baza nie ma grafików z lipca i sierpnia. Rota zachowała ostrzeżenia o braku lipcowego `target_hours` i wyzerowaniu przeniesienia kwartalnego. Nie ukryto ich w `wyniki_surowe.json`; dlatego ta próba nie rozstrzyga rozliczenia całego kwartału.
- Brama/patrol/recepcja zostały zagregowane, bo obecny model nie przechowuje stanowiska ani wymaganej kwalifikacji. Nie wolno na podstawie tego grafiku twierdzić, że właściwa osoba trafiła na patrol.

## Pliki

- `wyniki_surowe.json` — pełne wejścia, historia odpowiedzi `PLAN`, demandy, Assignmenty, ostrzeżenia i problemy eksportu.
- `02_centrum_handlowe_grafik_rota.pdf` — jedyny produkcyjny PDF, który obecna Rota wygenerowała.
- `*_grafik_rota.png` — raster produkcyjnego PDF.
- `*_obraz_kontrolny.png` — czytelna macierz wykonana wyłącznie z zapisanych Assignmentów, jawnie oznaczona jako nieprodukcyjny wydruk.
