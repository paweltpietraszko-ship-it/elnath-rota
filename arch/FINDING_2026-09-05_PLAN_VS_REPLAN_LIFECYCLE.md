# PRE-BRIEF AUDIT — „Przelicz (PLAN)” a „REPLAN”

AUDITED_SHA: `8dacf9da87e1ff6a3885bd1df37add84b9e91716`

Zakres: sprawdzenie, czy obecna implementacja realizuje jawne rozróżnienie
OWNERA:

- **Przelicz (PLAN)** — po nowym fakcie, np. L4, zachować rozpoczęte służby i
  zmienić przyszłą część obowiązującego grafiku w najmniejszym koniecznym
  stopniu;
- **REPLAN** — na żądanie koordynatora, któremu nie podoba się układ, ułożyć
  na nowo przyszłą część bez priorytetu minimalnego podobieństwa;
- wynik żadnej operacji nie staje się obowiązującą wersją ani historią przed
  wyborem przez koordynatora.

To audyt definicji problemu przed briefem. Kod produktu nie został zmieniony.

## Wynik

Rozróżnienie matematyczne solvera w większości istnieje. Cykl życia wersji i
dostępność przycisków nie realizują jednak zamierzonego procesu. Potrzebny jest
osobny brief; nie należy przemycać tej zmiany do zadania blokady wydruku.

## 1. Co robi dziś „Przelicz (PLAN)”

### Zgodne z zamiarem

`planning.engine.plan()` wywołuje solver bez flagi „wynik musi być inny”. Dla
istniejących, planowanych i niezablokowanych przypisań solver najpierw
minimalizuje liczbę zmienionych par pracownik–zapotrzebowanie, a dopiero potem
rozstrzyga zwykłymi kryteriami SOFT. Wąskie testy potwierdziły:

- jedna konieczna zmiana wygrywa z wariantem dwóch zmian o lepszym SOFT;
- solver przechodzi do dwóch zmian dopiero wtedy, gdy jedna zmiana nie daje
  rozwiązania zgodnego z HARD.

### Niezgodne z zamiarem

1. PLAN działa tylko na bieżącej wersji `WORKING`. Jeżeli obowiązujący grafik
   jest `FINAL`, backend odrzuca PLAN komunikatem „use REPLAN”, a frontend
   całkowicie ukrywa przycisk „Przelicz (PLAN)”. Istniejący test
   `test_t41_b13_final_current_still_rejects_plan` utrwala właśnie to
   zachowanie; niezależne uruchomienie: `1 passed`.
2. Ochrona rozpoczętych służb nie jest twardą regułą zwykłego PLAN. Są one
   częścią tej samej minimalizacji przetasowań co przyszłość. Jeżeli nowy fakt
   sprawi, że zachowanie przeszłej pary jest niemożliwe według bieżącego
   validatora, solver może ją zmienić. Cutover jest wymuszany dopiero dla
   wersji posiadającej rodzica; wersja bazowa jest jawnie wyłączona. Istniejący
   test `test_t23_r5_3f_initial_plan_not_subject_to_cutover_guard` potwierdza,
   że historyczne przypisanie wersji bazowej można zmienić przy wyborze
   kandydata; niezależne uruchomienie: `1 passed`.
3. Jeżeli bieżący grafik jest `WORKING`, zaakceptowanie wyniku PLAN zastępuje
   zawartość tej samej wersji w miejscu. Poprzedni obowiązujący układ nie staje
   się osobną wersją historyczną.
4. Przy pierwszym PLAN, jeszcze przed wynikiem solvera, tworzona jest pusta
   bieżąca ScheduleVersion z zapotrzebowaniami. Kandydat nie jest w niej
   zapisany przed wyborem, lecz techniczny pusty kontener już występuje jako
   wersja bieżąca.

## 2. Co robi dziś REPLAN

### Zgodne z zamiarem

1. Solver dostaje twardy warunek, że wynik ma różnić się od obecnego grafiku
   co najmniej jedną parą pracownik–zapotrzebowanie.
2. Nie dostaje fazy minimalizującej liczbę przetasowań. Może więc swobodnie
   ułożyć przyszłość na nowo według HARD i zwykłego rankingu SOFT. „Całkowicie
   nowy” oznacza brak ochrony podobieństwa, nie obowiązek zmiany każdej komórki.
3. Rozpoczęte PRIMARY są przypinane według czasu odcięcia w modelu REPLAN i
   ponownie chronione przy wyborze kandydata.
4. Wąskie testy potwierdziły, że REPLAN zwraca rzeczywiście inny wariant i nie
   rusza przypisania sprzed czasu odcięcia.

### Niezgodne z zamiarem

`plan_ops.replan()` tworzy nowe dziecko `WORKING`, kopiuje do niego aktualny
grafik i natychmiast ustawia je jako bieżące **przed uruchomieniem solvera i
przed wyborem kandydata**.

Niezależny reproduktor podmienił wyłącznie wynik kosztownego solvera na
`SEARCH_INCOMPLETE`, pozostawiając cały produkcyjny zapis wersji bez zmian:

```text
result=SEARCH_INCOMPLETE
before=V1
after=SV-0720bd1d44654393be83fd2040bee85e
versions=2
after_reject=SV-0720bd1d44654393be83fd2040bee85e
```

Zatem nieukończony REPLAN:

- tworzy drugą ScheduleVersion;
- zmienia bieżącą wersję z V1 na dziecko;
- pozostawia dziecko po odrzuceniu wyniku, ponieważ „Odrzuć wynik” usuwa tylko
  osobny `plan_preview`, a nie cofa bieżącego wskaźnika.

To jest mechanizm, przez który techniczna próba staje się biznesową wersją
uczestniczącą w `current`, historii, restore i eksporcie. Przy
`SEARCH_INCOMPLETE` dziecko nadal zawiera kopię wcześniejszego grafiku, a nie
wadliwy wynik solvera — błąd dotyczy cyklu życia wersji, nie jakości tego
kandydata.

## 3. PlanPreview działa osobno i poprawnie, ale nie naprawia REPLAN

FEASIBLE kandydat PLAN/REPLAN jest przechowywany w osobnym `plan_previews` i
nie zastępuje Assignmentów przed kliknięciem „Użyj tego grafiku”. Kolejny wynik
nadpisuje poprzedni preview, a odrzucenie usuwa preview.

W REPLAN obok poprawnego preview istnieje jednak przedwcześnie utworzona
ScheduleVersion-dziecko. Usunięcie preview nie usuwa ani nie dezaktywuje tego
dziecka. To dwa różne byty.

## 4. Zamrożony wynik dla briefu

### Wspólna zasada

- Podczas liczenia i oglądania propozycji dotychczasowy zaakceptowany grafik
  pozostaje bieżący.
- Nieudany, przerwany, niepełny albo odrzucony wynik nie tworzy
  koordynatorowi wersji grafiku, nie trafia do historii i nie może być
  przywracany ani drukowany jako grafik.
- Kliknięcie „Użyj tego grafiku” jest momentem akceptacji kandydata. Dopiero ta
  operacja atomowo tworzy nową bieżącą wersję; poprzednia obowiązująca wersja
  pozostaje w historii.
- Techniczny kontener potrzebny do obliczeń może istnieć wyłącznie jako
  niewidoczny preview/draft, który nie uczestniczy w current, historii,
  restore, rozliczeniu ani eksporcie.

### Przelicz (PLAN)

- Jest dostępny także wtedy, gdy bieżący obowiązujący grafik jest FINAL.
- Zachowuje każdą już rozpoczętą służbę jako twardy fakt.
- W przyszłej części minimalizuje liczbę zmian względem bieżącego grafiku.
- Po odrzuceniu albo braku rozwiązania dotychczasowy grafik pozostaje bez
  jakiejkolwiek nowej wersji biznesowej.

### REPLAN

- Zachowuje każdą już rozpoczętą służbę jako twardy fakt.
- Dla przyszłości nie minimalizuje podobieństwa; wymaga rzeczywiście innego
  układu, o ile taki istnieje.
- Tak samo jak PLAN pozostaje preview aż do „Użyj tego grafiku”.

## 5. Minimalne granice i testy dla architekta

- Nie zmieniać solverowego podziału PLAN/REPLAN, poza ujednoliceniem twardego
  cutover dla obu operacji.
- Przenieść utworzenie nowej ScheduleVersion i zmianę current do atomowego
  zaakceptowania kandydata.
- Osobno sprawdzić pierwszy PLAN bez istniejącej wersji: żaden pusty techniczny
  kontener nie może być widoczny jako obowiązujący/historyczny grafik.
- Macierz: PLAN po FINAL; PLAN dokładnie przed/równo/po początku służby;
  minimalnie 1 vs 2 zmiany; REPLAN naprawdę inny bez minimalizacji; wszystkie
  wyniki inne niż zaakceptowany FEASIBLE pozostawiają current i liczbę wersji
  bez zmian; odrzucenie i restart; akceptacja tworzy dokładnie jedno dziecko;
  preview nie jest dostępny w historii/restore/export.

## ARCHITECTURE_PROPOSALS — nieblokujące

- Stan obecny: repo ma już osobny `plan_preview`, lecz REPLAN dodatkowo tworzy
  ScheduleVersion przed akceptacją.
- Propozycja: wykorzystać istniejący `plan_preview` jako jedyny magazyn
  kandydatów zamiast dodawać trzeci byt.
- Korzyść: jedna granica odpowiedzialności i mniejsze ryzyko, że kandydat
  stanie się current przed wyborem.
- Koszt: akceptacja będzie musiała atomowo utworzyć nową ScheduleVersion z
  danych preview, zamiast podmieniać zawartość wcześniej utworzonej wersji.

## Wykonana kontrola

- frontend → router → application → solver → validator → persistence;
- `4 passed in 0.60s`: dwie klasy minimalnego PLAN oraz inny/past-pinned
  REPLAN;
- `1 passed in 1.17s`: PLAN po FINAL jest odrzucany;
- `1 passed in 0.72s`: wersja bazowa nie ma cutover guard;
- niezależny reproduktor nieukończonego REPLAN i odrzucenia preview.

Pełnej regresji nie uruchamiano: kod produktu nie został zmieniony. Interaktywna
kontrola ekranu była niedostępna — w udostępnionej sesji przeglądarki nie było
otwartej karty aplikacji. Widoczność przycisków potwierdzono statycznie w JSX,
nie przedstawia się jej jako pełnego testu wizualnego.
