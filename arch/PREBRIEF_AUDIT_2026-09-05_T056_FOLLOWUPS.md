# PRE-BRIEF AUDIT — trzy findingi po realistycznym teście T056

AUDITED_SHA: `48c19bf2011ebaf5b9146f046abe8d7fd454c6c0`

Zakres:

- `ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT`;
- `ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS`;
- `ROTA-DEVIATION-RAW-ASSIGNMENT-ID`.

To jest audyt definicji problemów przed briefem, nie brief ani projekt
rozwiązania. Kod produktu nie został zmieniony.

## Wynik w skrócie

Wszystkie trzy problemy są rzeczywiste. OWNER zamknął brakujące decyzje
2026-09-05:

1. historyczna służba jest faktem rozliczeniowym, a nie planem do swobodnej
   edycji; jedynym realnym wyjątkiem jest zapisanie po fakcie osoby, która
   rzeczywiście zastąpiła zaplanowanego pracownika;
2. potwierdzenie blokującego LAW jest zgodą tylko na jeden wygenerowany wydruk;
   następny wydruk wymaga ponownej zgody;
3. z całego UI koordynatora mają zniknąć wszystkie techniczne identyfikatory.
   Nie wystarczy zastąpić ich równie niejasnym tekstem typu „LAW Godziny”.

Punkty 1 i 2 są gotowe do briefu architekta. Punkt 3 nie wymaga kolejnej
decyzji OWNERA, ale przed zamrożeniem TASK_SCOPE wymaga pełnego inventory
wszystkich miejsc UI, w których mogą pojawić się techniczne identyfikatory.
CC może delegować to przeglądającemu kod agentowi; wynik inventory musi być
jawny w briefie, a nie przemycony później jako dodatkowe testy.

Findingi 2 i 3 są zależne. Czytelna informacja o blokującym LAW musi istnieć
przed lub razem z blokadą eksportu.

## 1. ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT

### Potwierdzony stan

`frontend/src/screens/MonthlyPlanning.tsx` inicjalizuje
`correctionEffectiveFrom` przez `todayIso()`. Kliknięcie wpisu w grafiku
ustawia wyłącznie `editingAssignmentId`; nie przelicza daty obowiązywania.

Ta sama wartość jest następnie przekazywana do wszystkich operacji w panelu
ręcznej korekty:

- przypisanie innej osobie;
- wybór dodatkowego D6+/N6+;
- zamrożenie/odmrożenie;
- oznaczenie „Nie przepracował (NN)”;
- usunięcie S1.

Eksport wybiera dla każdego dnia wersję, której `effective_from <= dzień`.
Dlatego korekta wpisu z 3 września zapisana z domyślnym 5 września istnieje
w bieżącej wersji, ale wydruk dnia 3 września zgodnie z lineage nadal bierze
wersję rodzica. Problem zgłoszony przez CC odpowiada dokładnie kodowi.

### OWNER_ACCEPTED — zachowanie do briefu

Rozstrzygnięcie OWNERA: odbytej lub już rozpoczętej służby nie wolno traktować
jak planu, który można dowolnie przepisać. Jest podstawą rozliczenia
pracownika.

Kontrakt ma rozdzielić dwa przypadki:

1. **Służba jeszcze się nie rozpoczęła:** pozostają istniejące operacje korekty
   planu. Dla korekty konkretnego Assignmentu system wylicza datę obowiązywania
   z kalendarzowej daty początku tego Assignmentu; koordynator nie ustawia
   technicznego `effective_from` ręcznie.
2. **Służba już się rozpoczęła lub zakończyła:** kod, początek, koniec, demand,
   stan i freeze nie podlegają zmianie. Jedynym dopuszczalnym przypadkiem jest
   zastąpienie zaplanowanego pracownika osobą, która faktycznie wykonała całą
   tę służbę. System:
   - wymaga wskazania pracownika zastępującego i przyczyny;
   - ustawia skutek na kalendarzową datę początku tej służby;
   - zachowuje poprzedni zapis i czas wykonania korekty w istniejącej historii;
   - pokazuje na WYK i w rozliczeniu osobę, która faktycznie pracowała.

Owning boundary backendu ma odrzucać inne modyfikacje rozpoczętych/odbytych
służb; sama blokada przycisków w UI byłaby omijalna. Ten finding stał się
osobnym zadaniem ochrony historycznej służby, a nie kosmetyczną zmianą
domyślnej wartości pola. Nie rozszerza T056: wybór D6+/N6+ dla służby, która
już się rozpoczęła, również jest niedozwolony.

## 2. ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS

### Potwierdzony stan

`POST /workspace/sites/{site_id}/schedule/{month}/export` wywołuje bezpośrednio
`generate_schedule_pdf()`. Ani router, ani application owner eksportu nie
czyta bieżących deviations. Bezpośrednie API omija więc dowolną przyszłą
blokadę dodaną tylko w UI.

`Export.tsx` również nie dostaje deviations. Po udanym eksporcie przechowuje
PDF jako lokalny `Blob`; przycisk „Pobierz” korzysta z tych samych zapisanych
bajtów i nie pyta ponownie backendu.

OWNER zamroził, że blokują wyłącznie niepotwierdzone deviations kategorii
`LAW`, a pozostałe kategorie nie blokują.

### Rozstrzygnięta sprzeczność

Dzisiejsze checkboxy „Odchylenia” są tylko stanem przeglądarki. Nie zmieniają
`Deviation.acknowledged`. Potwierdzenie zapisuje dopiero `Finalizuj`, a
finalizacja wymaga zaznaczenia dokładnie całego bieżącego zestawu deviations,
nie tylko LAW.

Gdy LAW współistnieje np. z HOURS, samo wymaganie finalizacji pośrednio każe
potwierdzić także HOURS przed eksportem. To przeczy decyzji „inne kategorie
nie blokują”. Nie można tego rozstrzygnąć technicznie bez decyzji produktu.

OWNER_ACCEPTED: zgoda dotyczy tylko jednego wygenerowania dokumentu. Podgląd i
pobranie tych samych bajtów PDF są tym samym wydrukiem. Każde ponowne
wygenerowanie PDF wymaga nowej zgody, jeżeli nadal istnieje blokujące LAW.
Zgoda eksportowa nie ustawia trwale `Deviation.acknowledged`, nie finalizuje
grafiku i nie wymaga potwierdzenia pozostałych kategorii.

### Konieczne granice techniczne po decyzji

- backend/application export boundary musi być ownerem blokady; UI może tylko
  wcześniej pokazać ten sam stan i czytelny komunikat;
- bezpośredni POST export nie może omijać blokady;
- potwierdzony POST może wygenerować dokładnie jeden dokument/revision; zgoda
  nie może zostać ponownie użyta do wygenerowania następnego PDF;
- stary podgląd/Blob i przycisk „Pobierz” muszą zostać unieważnione, gdy po
  jego wygenerowaniu zmieni się bieżąca wersja lub zestaw blokujących LAW;
  inaczej stary PDF nadal daje się pobrać bez nowego POST;
- komunikat blokady ma wskazywać zrozumiale, które LAW trzeba rozstrzygnąć;
- COVERAGE/HOURS/PREFERENCE/LEAVE_OR_TIME_OFF/CLIENT_REQUIREMENT nie mogą
  blokować samodzielnie ani przypadkiem przez użycie finalizacji jako jedynej
  ścieżki potwierdzenia LAW.

## 3. ROTA-DEVIATION-RAW-ASSIGNMENT-ID

### Potwierdzony stan

`ViolationDetail` posiada `message` z faktami diagnostycznymi. Przykładowy
LOAD-01 zawiera employee, policzone godziny i rolling-7d window.
`materialize_deviations()` odrzuca jednak `message` i zapisuje tylko kategorię,
source reference oraz pojedynczy target.

`GET month` buduje potem:

- ogólną polską etykietę, np. „obciążenie godzinowe”;
- surowe `affected_assignment_or_employee`.

Frontend drukuje oba pola bez rozwiązania targetu. Niezależny reproduktor na
exact SHA z `ViolationDetail("LOAD-01", ...)` dał:

```text
label = obciążenie godzinowe
affected_assignment_or_employee = solved-2026-09-03-D-393e5bf9-691b-4d92-a8a9-76d68a3c1bb6
```

Informacja „EMP-5, 72 h, okres 2026-09-01–2026-09-08” z message nie przeszła
do Deviation ani API.

### Zamknięty inventory trwałych Deviation sources

Dzisiejszy mapper dopuszcza 13 built-in sources:

- `COVERAGE-01`;
- `DAY_SHIFT_OFF-01`;
- `LEAVE_GRANTED-01`;
- `UNAVAILABLE-01`;
- `SICK_LEAVE-01`;
- `LOAD-01`;
- `REST-01`;
- `WEEKLY-REST-01`;
- `DAY_ONLY-01`;
- `MEMBERSHIP-01`;
- `EXTERNAL-01`;
- `SHIFT-24-01`;
- `SHIFT-24-PAIR-01`.

Dodatkowo source może być dynamicznym `SiteRule.rule_version_id`. Brief nie
może ograniczyć macierzy do LOAD-01 ani do sześciu kategorii enum; musi objąć
wszystkie powyższe source classes i SiteRule.

### OWNER_ACCEPTED — pełny zakres UI

Rozstrzygnięcie obejmuje całe UI dostępne koordynatorowi, nie tylko panel
„Odchylenia”. Żaden surowy `assignment_id`, `employee_id`, `demand_id`,
`rule_version_id`, UUID ani wewnętrzny kod techniczny nie może być użyty jako
treść komunikatu dla koordynatora. Identyfikatory mogą pozostać wewnątrz
modelu, API i logów, jeżeli są potrzebne do tożsamości lub diagnostyki, ale UI
ma pokazywać ich znaczenie operacyjne.

Tekst typu „LAW Godziny” również nie spełnia kontraktu. Komunikat musi
odpowiadać co najmniej: kogo lub czego dotyczy, którego dnia/zmiany/okresu,
co jest nieprawidłowe oraz — gdy ma zastosowanie — jaka jest wartość faktyczna
i dopuszczalny limit.

Przed briefem architekt/CC ma wykonać jawne inventory wszystkich powierzchni
UI: panel „Odchylenia”, bannery SOFT i DECISION_REQUIRED, formularze, błędy
endpointów renderowane przez frontend, widoki historii, planowania, eksportu
i ustawień. Repozytoryjne wyszukiwanie stringów jest początkiem, ale wynik
trzeba potwierdzić na realnych ścieżkach renderowania. Architekt może po
inventory podzielić wdrożenie na kilka jawnych Tasków; nie wolno ukrywać
szerszego zakresu w testach jednego findingu.

### Wymagania dla części briefu dotyczącej panelu „Odchylenia”

- dla każdego source określić minimalne fakty widoczne dla człowieka:
  osoba, jeśli reguła dotyczy osoby; data/okres/zmiana; rodzaj naruszenia;
  wartość zmierzona i limit albo brak/nadmiar, gdy ma zastosowanie;
- dynamiczny SiteRule ma pokazywać treść/nazwę reguły, nie rule_version_id;
- target persistence nadal służy tożsamości i walidacji. Nie zastępować
  `affected_assignment_or_employee` tekstem prezentacyjnym;
- nie używać `Deviation.reason` do komunikatu: to istniejące pole powodu
  potwierdzenia;
- nie parsować faktów z angielskich stringów `ViolationDetail.message`;
- architekt musi wskazać jeden owner transportu potrzebnych faktów. Obecny
  trwały `Deviation` nie przechowuje skali ani okresu, a read API je dziś
  wyrzuca. Sam frontend nie może prawdziwie odtworzyć LOAD/REST z current-month
  Assignmentów, bo walidacja obejmuje również boundary i other-site context;
- istniejące `DeviationOut.label` może pozostać kanałem prezentacji albo zostać
  rozszerzone w minimalny sposób, ale decyzja o źródle faktów i ewentualnej
  trwałości należy do architekta. Nie tworzyć równoległego warning subsystemu.

## Rekomendowane przekazanie

1. Architekt przygotowuje osobny brief dla ochrony rozpoczętej/historycznej
   służby i automatycznej daty korekty.
2. Czytelne deviations i blokadę eksportu należy opisać w jednym briefie albo
   w dwóch briefach z twardą zależnością: najpierw czytelność całej zamkniętej
   macierzy Deviation, następnie blokada LAW.
3. Przed zamrożeniem zakresu usuwania identyfikatorów CC/architekt wykonuje
   pełne inventory UI. Jeśli wynik jest duży, jawnie dzieli pracę na Taski.
4. Audyt preimplementacyjny ma później wykonać reduction gate na gotowym
   kontrakcie. Ten dokument nie zamraża technicznego rozwiązania.
