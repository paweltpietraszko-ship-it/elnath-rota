# Elnath Rota jako silnik — warianty integracji z Excelem i systemami zewnętrznymi

STATUS: EXPLORATION ONLY — NOT A TASK CONTRACT — NO IMPLEMENTATION AUTHORIZATION

Ten dokument służy wyłącznie do porównania możliwych kierunków. Nie zamraża zachowania produktu, nie tworzy TASK_SCOPE i nie upoważnia do implementacji. Wariant docelowy wymaga późniejszej jawnej decyzji OWNERA i osobnego briefu Tasku.

## 1. Cel eksploracji

Sprawdzić, czy Elnath Rota może działać nie tylko jako kompletna aplikacja z własnym UI, lecz również jako silnik planowania udostępniający dane i wyniki przez stabilny interfejs API.

Kluczowa potrzeba biznesowa: klient może chcieć korzystać z logiki solvera, walidacji, REPLAN i reguł Elnath Rota, ale nadal pracować w narzędziu, do którego jest przyzwyczajony, np. w Excelu.

Nie zakładamy jeszcze, że Excel ma zastąpić obecny frontend. Rozważane są zarówno warianty headless, jak i hybrydowe.

## 2. Zasada architektoniczna do zachowania

Elnath Rota pozostaje właścicielem logiki planowania. Excel ani inny klient zewnętrzny nie powinien powielać solvera, walidatora, reguł odpoczynku, ograniczeń pracowników, bilansu, logiki REPLAN ani klasyfikacji wyników.

Integracja powinna być cienkim adapterem wejścia/wyjścia nad istniejącymi ownerami produktu.

Preferowany kierunek ogólny:

`klient zewnętrzny -> API Elnath -> istniejące application/domain/planning -> wynik API -> klient zewnętrzny`

Nie tworzyć osobnego „solvera dla Excela”.

## 3. Wariant A — Elnath jako pełny headless engine

Użytkownik nie musi korzystać z UI Elnath Rota.

Dane wejściowe pochodzą z Excela lub innego systemu i są przesyłane przez API do Elnath. Elnath wykonuje walidację, planowanie i ewentualny REPLAN, po czym zwraca wynik przez API. Klient zewnętrzny prezentuje wynik użytkownikowi.

Potencjalny przepływ:

1. Excel/adapter odczytuje pracowników, obsadę, dostępność, cele godzinowe i inne wymagane dane.
2. Dane są mapowane do kontraktu API Elnath.
3. Elnath sprawdza kompletność danych i wykonuje PLAN/REPLAN.
4. API zwraca wynik: grafik, status, ostrzeżenia, kontrolowane blockery i ewentualne decyzje wymagające człowieka.
5. Adapter zapisuje wynik do arkusza.

Korzyści:

- Elnath może być używany jako usługa przez wiele różnych klientów;
- brak zależności biznesowej od obecnego frontendu;
- łatwiejsza integracja z ERP, systemem kadrowym lub własnym portalem klienta;
- jedna logika planowania dla wszystkich integracji.

Koszty i pytania:

- trzeba zdefiniować stabilny zewnętrzny kontrakt wejścia/wyjścia;
- trzeba zdecydować, czy stan lifecycle pozostaje w Elnath, czy klient wysyła kompletny stan za każdym razem;
- obsługa DECISION_REQUIRED, blockerów i REPLAN bez UI Elnath wymaga jawnego kontraktu dla klienta zewnętrznego;
- trzeba określić autoryzację, identyfikację Site i rozdzielenie klientów.

## 4. Wariant B — Elnath jako silnik, Excel tylko jako miejsce wyniku

Użytkownik nadal wprowadza i utrzymuje dane w Elnath Rota. Excel jest jedynie dodatkowym kanałem prezentacji lub dalszej pracy z gotowym grafikiem.

Potencjalny przepływ:

1. Koordynator pracuje normalnie w Elnath Rota.
2. PLAN/REPLAN odbywa się w obecnym systemie.
3. Po uzyskaniu odpowiedniego grafiku użytkownik wybiera eksport/synchronizację.
4. Elnath wystawia dane grafiku w stabilnym formacie.
5. Excel pobiera lub otrzymuje grafik i umieszcza go w uzgodnionym układzie arkusza.

Możliwe technicznie kanały:

- eksport `.xlsx` generowany przez Elnath;
- eksport CSV;
- endpoint API pobierany przez Power Query;
- Office Script / VBA wywołujące API;
- Power Automate jako warstwa pośrednia.

Korzyści:

- najmniejsze ryzyko architektoniczne;
- obecne lifecycle, REPLAN, decyzje, persistence i audyt pozostają bez zmian;
- Excel nie musi znać modelu wejściowego ani reguł solvera;
- odpowiada przypadkowi, w którym klient chce zachować swój znany format grafiku.

Koszty i pytania:

- czy potrzebny jest tylko jednorazowy eksport, czy synchronizacja po każdej zmianie;
- czy klient ma własny stały szablon Excela;
- czy Elnath ma eksportować wyłącznie zatwierdzony grafik, czy również working preview;
- czy aktualizacja ma nadpisywać arkusz, czy tworzyć nową wersję.

## 5. Wariant C — hybryda: część danych w Elnath, wynik w Excelu, wybrane dane wracają

Elnath pozostaje głównym systemem planowania, ale Excel może być zarówno odbiorcą grafiku, jak i źródłem ograniczonej klasy danych.

Przykład:

- kadry/pracownicy i ograniczenia są utrzymywane w Elnath;
- miesięczne zapotrzebowanie albo cele godzinowe klient przygotowuje w Excelu;
- Elnath importuje tylko tę uzgodnioną część danych;
- solver działa w Elnath;
- gotowy grafik wraca do Excela.

Korzyści:

- pozwala klientowi zachować istniejący proces tam, gdzie ma on wartość;
- ogranicza zakres migracji;
- Elnath nadal kontroluje krytyczne reguły planowania.

Ryzyka:

- trzeba jednoznacznie ustalić ownera każdego rodzaju danych;
- nie wolno dopuścić do dwóch równorzędnych źródeł prawdy dla tego samego pola;
- synchronizacja dwukierunkowa może szybko stać się bardziej złożona niż sam eksport;
- konieczne są zasady konfliktu wersji i błędów importu.

## 6. Wariant D — stateless planning API

Elnath otrzymuje kompletny stan planistyczny w jednym żądaniu i zwraca wynik bez trwałego zapisu danych klienta.

Model:

`POST planning-request -> validate -> solve -> response`

Klient jest ownerem danych trwałych. Elnath działa jak czysty silnik obliczeniowy.

Korzyści:

- prosty model integracyjny dla zewnętrznych systemów;
- łatwa separacja klientów;
- klient nie musi migrować danych do persistence Elnath.

Ryzyka i potencjalny konflikt z obecnym produktem:

- obecny Elnath ma lifecycle, wersje grafiku, preview, pamięć decyzji, bieżące AvailabilityRecord i REPLAN zależny od stanu;
- stateless API mogłoby wymagać osobnego adaptera składającego pełny PlanningState;
- nie wolno kopiować ani obchodzić istniejących ownerów tylko po to, by stworzyć drugi tor planowania;
- należy ustalić, czy taki tryb faktycznie jest potrzebą produktową, czy tylko techniczną możliwością.

## 7. Wariant E — stateful API bez obowiązkowego UI Elnath

Klient zewnętrzny korzysta z API, ale persistence, wersje grafiku, lifecycle, REPLAN, DecisionRequired i audyt pozostają w Elnath.

Excel lub inny system jest wtedy zewnętrznym frontendem Elnath.

Korzyści:

- zachowuje pełne zachowanie obecnego produktu;
- nie wymaga budowania drugiej semantyki REPLAN i lifecycle;
- najłatwiej utrzymać jedną prawdę produktową.

Koszty:

- zewnętrzny klient musi obsłużyć więcej stanów i odpowiedzi niż przy prostym solver-as-a-service;
- kontrakt API staje się produktem samym w sobie i wymaga wersjonowania/stabilności.

## 8. Prawdopodobne poziomy integracji z Excelem

### Poziom 1 — eksport pliku

Elnath generuje plik `.xlsx` lub CSV. Brak bezpośredniego połączenia z Excelem.

Najmniejszy zakres i najmniejsze ryzyko.

### Poziom 2 — Excel pobiera wynik

Excel przez Power Query albo prosty skrypt pobiera gotowy grafik z API Elnath.

Elnath nadal jest ownerem danych i planowania.

### Poziom 3 — przycisk „Przelicz” w Excelu

Excel wysyła dane lub komendę do Elnath i pobiera wynik. Możliwe przez Office Script, VBA lub inny adapter.

### Poziom 4 — dwukierunkowa synchronizacja

Excel może edytować część danych i synchronizować je z Elnath.

Największe ryzyko konfliktu ownerów, wersji i walidacji. Nie przyjmować jako domyślnego kierunku bez konkretnej potrzeby klienta.

## 9. Pytania do rozstrzygnięcia przed wyborem kierunku

1. Czy typowy klient chce zachować Excel wyłącznie jako format końcowego grafiku, czy również jako miejsce wprowadzania danych?
2. Czy klient oczekuje ręcznego eksportu, czy automatycznej synchronizacji?
3. Czy Elnath ma przechowywać dane i historię klienta, czy działać wyłącznie jako silnik obliczeniowy?
4. Czy REPLAN, historia wersji, DecisionRequired i audyt mają być dostępne klientowi zewnętrznemu?
5. Czy integracja ma wspierać dowolny arkusz klienta, czy jeden uzgodniony szablon?
6. Czy istnieje realna potrzeba zapisu z Excela do Elnath, czy wystarczy odczyt wyniku?
7. Czy pierwszym celem jest produkt ogólny, czy pilotaż dla jednego konkretnego klienta?

## 10. Wstępna ocena kierunków

Najmniejszym rozszerzeniem obecnego produktu wydaje się Wariant B: dane i planowanie pozostają w Elnath, a Excel jest dodatkowym miejscem odbioru grafiku.

Jeżeli pojawi się klient posiadający własny system danych, naturalnym rozszerzeniem jest Wariant E: stateful API Elnath bez obowiązkowego użycia naszego UI.

Wariant A/D — pełny headless/stateless engine — może być wartościowy jako docelowa platforma integracyjna, ale przed projektowaniem wymaga sprawdzenia, czy realni klienci potrzebują przekazywać cały stan zewnętrzny, czy tylko odbierać rezultat.

Wariant C ma sens wyłącznie wtedy, gdy zostanie jawnie rozdzielona własność danych. Nie projektować ogólnej synchronizacji dwukierunkowej bez konkretnego przypadku klienta.

## 11. Na razie poza zakresem

Ten dokument nie decyduje o:

- nowych endpointach;
- schemacie JSON;
- uwierzytelnianiu API;
- wersjonowaniu API;
- implementacji `.xlsx`;
- Power Query, VBA, Office Scripts ani Power Automate;
- modelu licencjonowania;
- hostingu;
- multi-tenancy;
- zmianach solvera;
- zmianach persistence;
- zmianach obecnego UI.

Te decyzje należy podejmować dopiero po wyborze wariantu i potwierdzeniu realnego sposobu pracy klienta.
