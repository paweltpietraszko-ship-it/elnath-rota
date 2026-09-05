# PRE-BRIEF AUDIT — trzy findingi po realistycznym teście T056

AUDITED_SHA: `48c19bf2011ebaf5b9146f046abe8d7fd454c6c0`

Zakres:

- `ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT`;
- `ROTA-PRINT-IGNORES-UNACKED-DEVIATIONS`;
- `ROTA-DEVIATION-RAW-ASSIGNMENT-ID`.

To jest audyt definicji problemów przed briefem, nie brief ani projekt
rozwiązania. Kod produktu nie został zmieniony.

## Wynik w skrócie

Wszystkie trzy problemy są rzeczywiste. Nie są jednak jeszcze jednym w pełni
testowalnym kontraktem:

1. domyślna data korekty potrzebuje jednej dokładnej decyzji OWNERA o zakresie;
2. blokada eksportu potrzebuje decyzji, co dokładnie znaczy „acknowledged” bez
   finalizacji całego grafiku;
3. czytelność deviations jest brief-ready tylko wtedy, gdy „każdy typ
   ostrzeżenia” oznacza zamknięty kanał trwałych pozycji w panelu
   „Odchylenia”, a nie wszystkie komunikaty ostrzegawcze całej aplikacji.

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

### Brakująca decyzja OWNERA

Propozycja architekta mówi „data Assignmentu/demandu”. To nie jest jedna
reguła, a panel obsługuje także Assignmenty bez demandu, np. S1.

Do zamrożenia przed briefem:

> Czy przy każdym otwarciu korekty istniejącego wpisu pole „Obowiązuje od” ma
> być ustawiane na kalendarzową datę początku wybranego Assignmentu, dla
> wszystkich operacji tego panelu, z zachowaniem możliwości ręcznej zmiany?

Jeżeli OWNER chce regułę tylko dla D6+/N6+ albo chce datę pokrywanego demandu
zamiast początku Assignmentu, brief musi powiedzieć to wprost. Nie potrzeba
nowego warning subsystemu ani zmiany semantyki lineage.

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

### Sprzeczność wymagająca decyzji OWNERA

Dzisiejsze checkboxy „Odchylenia” są tylko stanem przeglądarki. Nie zmieniają
`Deviation.acknowledged`. Potwierdzenie zapisuje dopiero `Finalizuj`, a
finalizacja wymaga zaznaczenia dokładnie całego bieżącego zestawu deviations,
nie tylko LAW.

Gdy LAW współistnieje np. z HOURS, samo wymaganie finalizacji pośrednio każe
potwierdzić także HOURS przed eksportem. To przeczy decyzji „inne kategorie
nie blokują”. Nie można tego rozstrzygnąć technicznie bez decyzji produktu.

Do zamrożenia przed briefem:

> Jak koordynator ma potwierdzić LAW dla potrzeb eksportu bez obowiązku
> finalizowania i potwierdzania pozostałych kategorii: czy potwierdzenie przy
> eksporcie jest jednorazową zgodą na ten wydruk, czy ma trwale ustawić
> `Deviation.acknowledged` i zapisać kto/kiedy je potwierdził?

### Konieczne granice techniczne po decyzji

- backend/application export boundary musi być ownerem blokady; UI może tylko
  wcześniej pokazać ten sam stan i czytelny komunikat;
- bezpośredni POST export nie może omijać blokady;
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

### Brakująca granica zakresu OWNERA

Do zamrożenia przed briefem:

> Czy „każdy typ ostrzeżenia pokazywanego w UI” w tym findingu oznacza tylko
> trwałe pozycje z panelu „Odchylenia”, czy również osobny banner warningów
> SOFT, DECISION_REQUIRED i komunikaty błędów innych ekranów?

Pierwszy wariant jest zamkniętym zakresem jednego tasku. Drugi jest audytem
komunikatów całej aplikacji i nie powinien być ukryty pod nazwą
RAW-ASSIGNMENT-ID.

### Wymagania dla briefu, jeśli zakres = panel „Odchylenia”

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

1. OWNER odpowiada na trzy wąskie pytania powyżej.
2. Architekt może przygotować osobny mały brief dla defaultu daty korekty.
3. Czytelne deviations i blokadę eksportu należy opisać w jednym briefie albo
   w dwóch briefach z twardą zależnością: najpierw czytelność całej zamkniętej
   macierzy Deviation, następnie blokada LAW.
4. Audyt preimplementacyjny ma później wykonać reduction gate na gotowym
   kontrakcie. Ten dokument nie zamraża technicznego rozwiązania.
