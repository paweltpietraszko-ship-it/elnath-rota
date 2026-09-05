# PRE-BRIEF REAUDIT — druk, cykl życia grafiku i techniczne identyfikatory UI

AUDITED_SHA: `e4d150442deaa156b90d9ebfdf14155f70bd3588`

Zakres:

- sprawdzenie rozszerzonych ustaleń CC dla
  `ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS`;
- kontrolne inventory miejsc, których nie obejmował pierwotny finding
  `ROTA-DEVIATION-RAW-ASSIGNMENT-ID`.

To jest audyt problemu przed briefem. Kod produktu nie został zmieniony.
Nie wydano PASS/FAIL: pozostało jedno zachowanie widoczne dla OWNERA do
potwierdzenia.

## Wynik

CC poprawnie znalazł główny mechanizm, ale jego opis nie jest wyczerpujący.
Problem nie ogranicza się do ręcznych korekt i nie może być naprawiony samym
sprawdzeniem zapisanych `Deviation.acknowledged`.

## Co CC potwierdził poprawnie

1. `apply_manual_correction()` przyjmuje zarówno bieżący WORKING, jak i FINAL.
2. Korekta FINAL tworzy nowe dziecko WORKING i atomowo ustawia je jako current;
   parent FINAL pozostaje niezmieniony.
3. Zwykłe przypisanie/D6+/N6+, freeze/unfreeze i NN przechodzą przez ten sam
   application owner. `training.mark_training_realized()` również deleguje do
   `apply_manual_correction()`.
4. Jedyny endpoint PDF wywołuje `generate_schedule_pdf()` bez sprawdzenia
   statusu, deviations ani acknowledgement.
5. `finalize()` jest dziś jedyną operacją zapisującą acknowledgement i wymaga
   dokładnie całego świeżo przeliczonego zestawu deviations.

Niezależny reproduktor na exact SHA potwierdził:

```text
parent= FINAL_NO_DEVIATIONS
child= WORKING
deviations= []
export_ready= True
```

Czyli nawet bez LAW korekta FINAL natychmiast tworzy drukowalny WORKING.

## Luki pominięte przez CC

### 1. Nie tylko korekta zmienia current FINAL/WORKING

Pełny production inventory operacji poruszających bieżącą wersję obejmuje:

- `manual_edit.apply_manual_correction()` i jego wrappery;
- `plan_ops.replan()` — natychmiast tworzy i ustawia current WORKING child,
  jeszcze przed wybraniem nowego kandydata;
- `lifecycle_ops.restore()` — może ustawić jako current dowolną wcześniejszą
  wersję, również WORKING/WORKING_WITH_DEVIATIONS.

`REPLAN` i `restore` muszą wejść do tej samej macierzy bezpieczeństwa eksportu.
Ograniczenie briefu do „wszystkich typów ręcznej korekty” nadal zostawi obejścia.

Osobno w UI są user-visible warianty nieuwidocznione w wyliczeniu CC:

- dodanie S1;
- anulowanie S1;
- zwykłe przypisanie innej osoby;
- wybór D6+/N6+;
- freeze/unfreeze;
- NN;
- realizacja szkolenia przez application API.

Dodanie/anulowanie S1 korzysta z ogólnego endpointu korekty, ale nadal musi być
jawnie nazwane w acceptance matrix jako odrębna ścieżka użytkownika.

### 2. Nie wolno naprawić tego przez zakaz wydruku WORKING

Istniejące, zamrożone kontrakty i testy eksportu świadomie generują PDF po
PLAN/select, przed finalizacją (`tests/test_t020.py`, pion T47-11 oraz
`test_vertical_full_stack.py`). T041 umieszcza Wydruk na tym samym ekranie
niezależnie od statusu.

Dlatego blanket rule „drukuj tylko FINAL” zmieniłaby istniejący produkt i nie
może zostać przemycona przez ten finding. Zamrożona decyzja OWNERA pozostaje
węższa: wydruk blokuje wyłącznie niepotwierdzone LAW; inne deviations oraz sam
status WORKING nie blokują.

### 3. Frontend wyrzuca wynik korekty i nie pokazuje przejścia

Endpoint korekty już zwraca `status` i pełną listę deviations nowego childa.
`MonthlyPlanning.runCorrection()` ignoruje odpowiedź, zamyka panel i wywołuje
`load()` bez await.

Komponent `Export` jest renderowany nad częścią lifecycle i pozostaje aktywny
również podczas tego reloadu. Koordynator może więc wygenerować dokument po
zmianie current, zanim UI pokaże nowe deviations. Po zakończeniu reloadu widzi
jedynie mały status „roboczy”; nie dostaje jednoznacznej informacji, że
wcześniejszy FINAL wymaga ponownego przeglądu/finalizacji.

### 4. Stary PDF pozostaje dostępny po zmianie stanu

`Export.tsx` trzyma lokalne `previewBlob`, `previewUrl` i filename. Czyści je
tylko przed następnym wywołaniem eksportu lub przy unmount.

Nie czyści ich po:

- korekcie;
- REPLAN;
- restore;
- finalizacji/revalidacji;
- zmianie current version poza tym komponentem;
- zmianie `workingMonth`; komponent pozostaje zamontowany;
- zmianie obiektu, jeśli ten sam komponent zostanie zachowany.

W efekcie stary dokument może nadal wisieć w podglądzie i dać się pobrać po
zmianie grafiku, miesiąca albo zestawu LAW. Backendowa blokada nowego POST nie
usunie tego obejścia.

### 5. Zapisane deviations mogą być nieaktualne w chwili eksportu

Validator uwzględnia boundary month i other-site context. Po utworzeniu wersji
mogą zmienić się fakty zewnętrzne, a zapisany snapshot deviations nie odświeża
się automatycznie. `finalize()` z tego powodu świadomie wykonuje
`_fresh_deviations()` tuż przed porównaniem potwierdzeń.

Eksportowa blokada nie może więc tylko odczytać rows z tabeli `deviations`.
Musi sprawdzić świeży wynik validatora na dokładnym stanie, z którego powstaje
PDF. Walidacja i złożenie dokumentu muszą być związane z tą samą current
version/revision; inaczej zmiana pomiędzy checkiem i renderem daje TOCTOU.

### 6. `deviation_id` nie identyfikuje konkretnego naruszenia

`materialize_deviations()` buduje ID wyłącznie jako:

```text
DEV-{index}-{rule}
```

Nie zawiera targetu, okresu, wartości ani version/revision. Niezależny
reproduktor na exact SHA:

```text
DEV-0-REST-01 EMP-A
DEV-0-REST-01 EMP-B
same_id_different_problem= True
```

Stare zaznaczenie może więc pasować do świeżo przeliczonego naruszenia tej
samej reguły i pozycji, ale dotyczącego innego pracownika. Samo porównanie
zbioru `deviation_id` nie dowodzi, że koordynator przeczytał te same fakty.

Brief musi opierać potwierdzenie na tożsamości/fingerprintcie pełnego
zrozumiałego naruszenia i revision, nie na obecnym indeksowym ID. Nie parsować
angielskiego `ViolationDetail.message`.

### 7. Acknowledgement zachowuje się różnie zależnie od ścieżki

- manual correction świeżo materializuje cały zestaw z `acknowledged=False`,
  również dla niezmienionych naruszeń;
- REPLAN klonuje deviations z parenta razem z wcześniejszymi flagami
  `acknowledged=True`, choć tworzy nową current version i nową revision;
- restore przywraca dokładnie dawny stan flag.

Nowa blokada nie może ufać samemu zapisanemu booleanowi bez określenia, dla
jakiej wersji dokumentu i jakich faktów zgoda została udzielona.

## Jedno miejsce potwierdzania — możliwa spójna granica

Zamrożone decyzje OWNERA da się pogodzić bez drugiego modala/panelu:

- istniejąca lista „Odchylenia” pozostaje jedyną powierzchnią zaznaczania;
- `Finalizuj` nadal korzysta z zaznaczeń zgodnie ze swoim kontraktem;
- `Wygeneruj PDF` korzysta z zaznaczonych LAW z tej samej listy, ale zgoda
  obowiązuje tylko dla tego jednego requestu/revision;
- niezaznaczone non-LAW nie blokują PDF;
- backend świeżo przelicza LAW i sprawdza fingerprint/revision;
- po wygenerowaniu jednorazowe zaznaczenie eksportowe nie staje się trwałym
  `Deviation.acknowledged`;
- następne generowanie przy nadal istniejącym LAW wymaga ponownego zaznaczenia
  w tej samej liście.

To opis zachowania wynikający z rulingów, nie nakaz konkretnego DTO lub tabeli.
Architekt wybiera minimalny transport bez drugiego subsystemu.

## Jedna decyzja OWNERA nadal potrzebna

Po korekcie current FINAL system musi ujawnić, że powstał WORKING i że lista
odchyleń wymaga ponownego przeglądu. Nie jest zamrożone, czy:

1. po zapisie system automatycznie przewija/przenosi fokus do jedynej listy
   „Odchylenia” i pokazuje przy niej komunikat „Grafik zmieniono — przed
   finalizacją sprawdź ponownie odchylenia”; czy
2. korekta od razu otwiera krok finalizacji.

Rekomendacja audytora: wariant 1. Nie tworzy drugiego miejsca potwierdzania,
nie zmusza do finalizacji przed legalnym wydrukiem WORKING bez LAW i pasuje do
istniejącego jednego ekranu T041.

## Kontrolne inventory technicznych identyfikatorów UI

CC nie wykonał jeszcze zapowiedzianego pełnego inventory. Już statyczny
przegląd wykazał co najmniej następujące powierzchnie, których nie wolno
ominąć w briefie:

1. `MonthlyPlanning`: surowy deviation target; warningi przepisywane regexem;
   raw `plan_preview_error`, solver `error_message` i wspólny banner błędów.
2. `Overview`: `blockers[0].employee_id` jest drukowany wprost.
3. `Decisions`: fallback `display_name ?? employee_id`, `requested_by`, lista
   `linked_action_ids`; backend `_render_condition()` zwraca nieznany raw code.
4. `History`: `coordinator_id`, `source_id`, decision IDs, linked action IDs,
   rule IDs oraz surowe wartości ID z rekurencyjnego before/after state.
5. `Export`: UI pokazuje skrót `document_revision`; filename używa `siteId`;
   PDF drukuje dwa hashe: „Kod weryfikacyjny grafiku” i „Rewizja treści”.
6. `Analytics`: opis ekranu drukuje `siteId` zamiast nazwy obiektu; warningi są
   przekazywane jako gotowe stringi bez wspólnego kontraktu prezentacji.
7. Wspólny klient API rzuca `body.detail` bez translacji, a dziesiątki catchów
   renderują `String(error.message)` wprost. `api/errors.py` wstawia do detail
   `str(exc)`, które często zawiera assignment/version/employee/rule IDs.
8. Export router ma jawny fallback „Nieprzetłumaczony kod błędu wydruku:
   {problem_code}”, który pokazuje techniczny kod koordynatorowi.

To jest minimalne potwierdzone inventory source-level, nie deklaracja
kompletności runtime. Przed briefem CC/architekt nadal musi przejść realne
ścieżki renderowania wszystkich ekranów. Użyteczne kody wsparcia/audytu
(np. kod diagnostyczny albo kod weryfikacyjny PDF) również muszą zostać jawnie
sklasyfikowane: albo pozostają za wyraźnym wyjątkiem OWNERA z ludzkim opisem,
albo znikają z UI i zostają wyłącznie w diagnostyce/metadanych.

## Wymagane przekazanie

1. OWNER zamyka jedną decyzję o zachowaniu ekranu bezpośrednio po korekcie
   FINAL.
2. Architekt obejmuje jednym lifecycle/export briefem wszystkie current-pointer
   paths, świeżą walidację, bezpieczną tożsamość zgody i unieważnienie Blob.
3. Architekt/CC kończy osobne pełne inventory technicznych identyfikatorów UI;
   wynik dzieli jawnie na Taski, jeśli nie mieści się w jednym bezpiecznym
   wdrożeniu.
4. Preimplementation reduction gate sprawdza później, czy nie powstał drugi
   panel potwierdzania, drugi validator ani duplikat eksportera.
