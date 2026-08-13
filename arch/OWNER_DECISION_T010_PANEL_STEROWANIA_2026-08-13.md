# ROTA — decyzja właściciela: T010 / przyszły Panel Sterowania

DATA: 2026-08-13
STATUS: OWNER DECISION / aneks produktu przed briefem ROTA-T010
BAZA: main `51b71725186fa30be23219e94aa135bb69bc5bce`

## 1. Kierunek

ROTA-T010 nie dotyczy parsera języka naturalnego. Parser i sterowanie Rotą swobodnym tekstem są usunięte z produktu. Program nie zgaduje intencji koordynatora.

**Panel Sterowania** jest wyłącznie nazwą przyszłego okna UI. T010 nie projektuje UI ani tymczasowego panelu. Ma przygotować trwałe dane i operacje aplikacyjne, które później wykorzysta T012.

Panel nie może stać się drugim źródłem logiki ani danych. Jeśli mechanizm już istnieje, T010 ma go wykorzystać przez cienkie podpięcie. Skopiowanie lub odtworzenie istniejącej logiki w nowej warstwie jest błędem dyskwalifikującym implementację.

## 2. Bieżąca obsada obiektu

Przyszły Panel Sterowania pozwala dodać pracownika do bieżącej obsady obiektu i usunąć go z tej obsady.

Usunięcie z bieżącej obsady NIE kasuje Employee ani historii. Stare ScheduleVersion, Assignment i rozliczenia pozostają odtwarzalne i nadal wskazują pracownika. Solver nie może używać pracownika, który nie należy do bieżącej obsady obiektu.

## 3. Ustawienia pracownika

Przyszły Panel Sterowania udostępnia:

1. **Ogólna dostępność**.
2. **Dniówka**.
3. **Nocka**.
4. **Niedostępność w wybrane dni tygodnia** — rozwijana lista dni oraz zakres od–do.

Nie ma osobnej pozycji **Święta**.

Pozycja **Szkolenie** zostaje usunięta z Panelu Sterowania. Szkolenie `S` koordynator wstawia ręcznie do konkretnego grafiku, gdy uzna je za potrzebne. Solver nie decyduje o potrzebie szkolenia.

## 4. Ustawienia dostępności są HARD

Decyzje dostępności są bieżącą komunikacją koordynatora z solverem i są bezwzględne.

- ogólna niedostępność blokuje pracownika w podanym okresie;
- niedozwolona Dniówka blokuje D;
- niedozwolona Nocka blokuje N;
- zaznaczony dzień w „Niedostępność w wybrane dni tygodnia” oznacza niedostępność, nie dzień dozwolony.

Przykład: koordynator zaznacza **Piątek** i `od 01.09.2026 do 31.10.2026`. Pracownik jest niedostępny w każdy piątek tego okresu; pozostałe dni są bez zmian; po dacie `do` ograniczenie wygasa.

Jeżeli przy obowiązujących HARD nie da się stworzyć kompletnego grafiku, solver nie może ich sam naruszyć. Decyzję zmienia wyłącznie koordynator.

## 5. `day_only` i czasowe N

`Employee.day_only` pozostaje stałą regułą pracownika i jednym źródłem prawdy dla stałego zakazu N.

Koordynator może czasowo zawiesić ten zakaz, jawnie dopuszczając N w zakresie od–do. W tym okresie solver może przydzielać N. Po `effective_to` czasowy wyjątek wygasa i stałe `day_only` nadal obowiązuje.

T010 nie może tworzyć drugiego trwałego pola konkurującego z `day_only`. Stała reguła pozostaje w Employee; czasowe dopuszczenie N jest osobną, datowaną decyzją koordynatora.

## 6. Niedostępność znana przed planowaniem

Niedostępność znana wcześniej jest wejściem do planowania. Solver omija wskazane terminy i może rozdzielić pracę inaczej zgodnie z pozostałymi regułami.

Dotyczy to m.in. choroby, urlopu, innej pełnej niedostępności oraz okresowej niedostępności w wybrane dni tygodnia.

Nie należy tego utożsamiać z NN stwierdzonym po zaplanowanej zmianie.

## 7. NN po zaplanowanej zmianie

`NN` — nieobecność nieusprawiedliwiona — jest faktem operacyjnym grafiku, a nie decyzją kadrową.

Jeżeli pracownik nie wykonał zaplanowanej 12-godzinnej zmiany, po korekcie:

- kod `NN` pozostaje widoczny przy tej niewykonanej zmianie;
- efektywne godziny z tej zmiany wynoszą `0`;
- nie powstaje sztuczny REALIZED Assignment udający wykonaną pracę;
- Rota nie wyciąga konsekwencji kadrowych.

Przykład: 168 h przed zdarzeniem minus jedna niewykonana zmiana 12 h = 156 h efektywnie.

Niedostępność znana przed planem i NN po planie są różnymi zdarzeniami produktu.

## 8. READY_FOR_PRIMARY

`READY_FOR_PRIMARY` jest wyłącznie etykietą informacyjną. Nie uczestniczy w eligibility i nie może blokować ani dopuszczać pracownika do grafiku.

Uchylona zostaje automatyczna zmiana statusu po osiągnięciu liczby zrealizowanych szkoleń. Liczbę szkoleń można policzyć i pokazać jako fakt, ale program nie wyprowadza z niej decyzji o człowieku.

T010 może usunąć istniejącą automatyczną promocję readiness i testy wymagające tej automatyki. Nie zastępuje jej innym algorytmem oceny.

## 9. TARGET-01

TARGET-01 pozostaje bez zmian. Zapotrzebowanie obiektu ustala liczbę zmian. `target_hours` jest SOFT pomagającym rozdzielać istniejące zmiany i obserwować saldo. Solver nie tworzy dodatkowej pracy i nie narusza HARD dla osiągnięcia targetu.

## 10. Granica T010

T010 jest małym zadaniem backend/application. Nie tworzy UI.

Przed implementacją ma wykorzystać istniejące `SiteRuleVersion`, `AvailabilityRecord`, `SiteMembership` / `membership.enabled`, application layer T009 oraz mechanizm ręcznej korekty ScheduleVersion/Assignment.

T010 NIE tworzy drugiego źródła prawdy, uniwersalnego edytora reguł, parsera, DSL, UI, tymczasowego panelu, silnika workflow ani automatycznej oceny pracownika.
