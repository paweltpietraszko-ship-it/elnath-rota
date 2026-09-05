# ROTA-T056 — dodatkowe miesięczne kody D/N do ręcznej korekty i wydruku

STATUS: READY FOR PREIMPLEMENTATION AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `9d8bfd0046062078f11d08f8bd7dc1d1f5d4326a`

Źródła:
- `arch/FINDING_2026-09-05_DEFINABLE_WORK_CODE_DURATIONS.md` @ `27425435c03f20b111f855e215c14de8fbc43264`
- `BOARD.md` @ `9d8bfd0046062078f11d08f8bd7dc1d1f5d4326a`
- decyzje OWNERA 2026-09-05 zapisane w findingu

## 1. Cel

Pozwolić koordynatorowi zdefiniować dla konkretnego **obiektu i miesiąca** dodatkowe kody realnej pracy `D6`, `D7`, ... / `N6`, `N7`, ... o niestandardowych przedziałach czasu, a następnie wybrać taki kod przy ręcznej korekcie istniejącego Assignmentu.

Wybranie kodu ma zmienić realny `Assignment.start_datetime` / `end_datetime`, przejść istniejącą walidację ręcznej korekty i następnie poprawnie trafić do PLAN, WYK, sum godzin, legendy oraz PDF.

Task służy domknięciu dokładnego bilansu godzin na koniec kwartału przez **ręczną korektę po PLAN/REPLAN**. Solver pozostaje nietknięty.

## 2. Decyzje OWNERA — zamrożone

1. Definiowalne są wyłącznie **dodatkowe** kody rodzin D/N: `D6+` i `N6+`.
2. `D1–D5` / `N1–N5` oraz `FROZEN_WORK_CODE_HOURS` pozostają dokładnie takie jak dziś.
3. Definicje dodatkowych kodów są **per `(site_id, month)`**. Zestaw jednego miesiąca nie wpływa na inny miesiąc, w tym na ponowny wydruk wcześniej zamkniętego miesiąca.
4. Koordynator najpierw definiuje kod w ustawieniach. Przy korekcie wybiera kod z istniejącej listy. Program nie tworzy ani nie dobiera kodu automatycznie z liczby godzin.
5. Wybranie dodatkowego kodu naprawdę zmienia realny przedział Assignmentu w bazie. To nie jest etykieta wydruku.
6. Korekta przechodzi istniejący flow `apply_manual_correction()` i istniejącą walidację/deviations. Nie tworzyć drugiego mechanizmu korekty.
7. Dodatkowy kod realnej pracy trafia tak samo do **PLAN i WYK**.
8. U/C pozostają całkowicie poza T056. Istniejący `reserve_hours` i absence decomposition bez zmian.
9. Solver CP-SAT, `SiteProfile.standard_shifts`, `ShiftCatalogKind`, WorkBalance i analytics pozostają bez zmian.
10. Rzeczywisty PDF jest częścią acceptance. Zielone testy nie zastępują oceny optycznej wydruku.

## 3. Ważne rozróżnienie: kod NIE jest nowym `operational_code`

Dzisiejsze `D1–D5/N1–N5` nie są trwałą etykietą Assignmentu. `schedule_export.py::_map_work_code()` rozpoznaje kod z:
- rodziny D/N wynikającej z pokrywanego demandu,
- realnego `start_datetime/end_datetime`,
- skonfigurowanego przedziału kodu.

T056 rozszerza ten sam mechanizm o miesięczne dodatkowe kody.

**Nie zapisywać `D6/N6/...` do `Assignment.operational_code` tylko po to, aby pamiętać wybrany kod.** Wybranie kodu w UI jest skrótem do ustawienia jego realnego przedziału czasu; późniejszy read/export ma ponownie rozpoznać kod z tego przedziału i konfiguracji miesiąca.

Powód: nie tworzymy dwóch konkurencyjnych ownerów kodu zmiany — standardowe i dodatkowe kody mają jedną semantykę mapowania.

## 4. Minimalny model danych

Obecny `SitePrintSettings` jest per-site i zawiera również dane globalne wydruku. Nie wolno zmieniać jego semantyki na per-month ani kopiować całych ustawień wydruku do każdego miesiąca.

Potrzebny jest mały, osobny current-state persistence seam dla **wyłącznie dodatkowych miesięcznych kodów D/N**, kluczowany przez `(site_id, month)`.

Preferowana minimalna reprezentacja:
- jedna tabela/rekord per `(site_id, month)`;
- payload `extra_work_code_intervals_json` jako mapowanie `code -> WorkCodeInterval`;
- brak historii, wersjonowania, statusów, activation flags i warning subsystemu;
- miesiąc canonical first-of-month (`YYYY-MM-01`) jak inne miesięczne dane.

To jest nowy durable state wymagany wprost przez decyzję OWNERA `per obiekt + miesiąc`, a nie recovery/defensive state.

Repozytorium pozostaje w `rota/persistence/site_repository.py`, obok istniejącego ownera kodów/ustawień wydruku; nie tworzyć nowego repository module tylko dla jednej mapy JSON.

## 5. Walidacja definicji dodatkowych kodów

Dodatkowy kod:
- należy tylko do rodziny `D` albo `N`;
- suffix jest liczbą całkowitą `>= 6` (`D6`, `D7`, ..., `N6`, `N7`, ...); bez aliasów i bez nadpisywania D1–D5/N1–N5;
- ma dokładnie jeden `WorkCodeInterval(start_time, end_time, end_next_day)`;
- interval musi mieć dodatni czas trwania;
- czas trwania musi być całkowitą dodatnią liczbą godzin, ponieważ istniejące target/sumy wydruku operują godzinami całkowitymi; nie dodawać drugiego pola `duration_hours` — wartość jest pochodną interval;
- w obrębie tej samej rodziny interval/signature musi być jednoznaczny: dodatkowy kod nie może mieć identycznego `(start_time,end_time,end_next_day)` jak inny dodatkowy kod ani jak aktywnie skonfigurowany standardowy D1–D5/N1–N5. Inaczej `_map_work_code()` nie byłby w stanie odtworzyć wybranego kodu bez nowego ID na Assignment.

Nie ograniczać liczby dodatkowych kodów do jednego slotu ani do D6/N6. Produktowo kolejny kwartał może wymagać innego zestawu.

## 6. Ustawienia API/UI

Owner UI pozostaje `Panel sterowania -> Obiekt -> Ustawienia wydruku` (`PrintSettings.tsx`), ale dodatkowe kody muszą być edytowane dla aktualnego `workingMonth` należącego do `Room.tsx`.

Nie zmieniać istniejących per-site pól `company_print_name`, `site_print_name`, `base_regime`, standardowych `work_code_intervals`, `reserve_hours`, `s1_default_interval` na per-month.

Dodać w `api/routers/export.py` wąski read/write monthly subresource dla extra D/N codes; nie tworzyć drugiego routera/settings subsystemu. Frontend `client.ts` ma odzwierciedlać ten kontrakt bez reinterpretacji.

`PrintSettings.tsx`:
- pokazuje standardowe D1–D5/N1–N5 jak dziś, bez możliwości zmiany ich godzin wymaganych;
- osobna sekcja „Dodatkowe kody dla YYYY-MM”;
- umożliwia dodanie/usunięcie D6+/N6+ oraz ustawienie start/end/end_next_day;
- nie generuje kodu automatycznie z godzin; koordynator wybiera nazwę kodu i interval;
- zmiana miesiąca pokazuje niezależny zestaw tego miesiąca.

## 7. Ręczna korekta — reużycie istniejącego flow

Backend `apply_manual_correction()` już akceptuje realny Assignment z dowolnym `start_datetime/end_datetime` i uruchamia normalne `validate()`/deviations. T056 nie dodaje drugiego endpointu ani specjalnej komendy „apply code”.

W `MonthlyPlanning.tsx`, przy edycji istniejącego zwykłego Assignmentu PRIMARY:
- UI pobiera dodatkowe kody dla `(site_id, workingMonth)`;
- jeśli Assignment pokrywa demand o rodzinie D, oferuje tylko zdefiniowane `D6+`; dla N — tylko `N6+`;
- wybór kodu buduje nowy realny przedział na dacie pokrywanego ShiftDemandu zgodnie z `start_time/end_time/end_next_day` definicji;
- wszystkie pozostałe pola Assignmentu pozostają jak w istniejącej korekcie;
- zapis idzie przez istniejące `api.applyManualCorrection()` / backend manual-correction;
- wynikowe HARD deviations/soft warnings zachowują dotychczasową semantykę.

Jeśli Assignment nie ma jednoznacznego pokrywanego D/N demandu, nie oferować dodatkowego kodu i nie zgadywać rodziny/daty.

S1, TRAINEE, NN/CANCELLED i operacje freeze pozostają bez zmian.

## 8. Eksport

`generate_schedule_pdf()` ma ładować dodatkowe kody dla dokładnego `(site_id, month)` eksportowanego dokumentu.

### Mapowanie
`_map_work_code()`:
- najpierw/łącznie rozpatruje standardowe skonfigurowane D1–D5/N1–N5 i miesięczne D6+/N6+;
- rodzina nadal pochodzi z `demand.shift_kind`;
- realny Assignment musi dokładnie pasować intervalem;
- brak dopasowania nadal fail-closed `WORK_CODE_MAPPING_REQUIRED`;
- dzięki walidacji unikalności nie może być dwóch kodów tej samej rodziny pasujących do tego samego intervalu.

### Sumy PLAN/WYK
`_hours_of()` nie może dla D6+/N6+ zwracać cicho `0`.
- dla dodatkowego kodu zwraca jego realny, zwalidowany duration z konfiguracji tego miesiąca;
- nie zmienia U/C ani S1 semantics;
- PLAN i WYK dla realnej pracy nadal dostają ten sam kod i tę samą liczbę godzin.

### Legenda i layout
Legenda wydruku ma dynamicznie pokazać zdefiniowane dodatkowe kody tego miesiąca obok standardowych D/N, bez sztucznego limitu slotu 5.

Nie przebudowywać całego layoutu, jeżeli obecny można rozszerzyć lokalnie. Jednak PDF z D6/N6 i co najmniej jednym kodem >6 musi przejść gate optyczny opisany w Acceptance.

### Document revision
Miesięczne definicje dodatkowych kodów wpływają na semantykę dokumentu, więc muszą wejść do deterministycznego `document_revision`. Zmiana D6/N6 dla tego samego `(site,month)` ma zmienić revision; konfiguracja innego miesiąca nie może jej zmienić.

## 9. Zakaz rozszerzania zakresu

Poza zakresem T056:
- `rota/planning/solver.py` i jakakolwiek zmiana PLAN/REPLAN;
- `SiteProfile.standard_shifts`, `ShiftCatalogKind`, demand generation;
- `rota/balance.py`, `rota/application/analytics_read.py`, target-hours semantics;
- U/C, `reserve_hours`, absence decomposition i osobny finding urlopowy;
- automatyczne tworzenie kodu z brakujących godzin;
- automatyczne dobieranie D6/N6 przez solver;
- modyfikowanie D1–D5/N1–N5 lub ich `FROZEN_WORK_CODE_HOURS`;
- nowy `operational_code` semantics dla zwykłej pracy;
- warning/history/audit subsystem specjalnie dla kodów;
- nowy ogólny „custom shift catalog”.

Jeśli implementacja wydaje się wymagać któregoś z powyższych, wraca do architekta zamiast rozszerzać scope.

## 10. Acceptance

T56-01: dla Site A i miesiąca 2026-09 koordynator zapisuje `D6=06:00–20:00` (14h) oraz `N6=20:00–06:00 next day` (10h); reload ustawień tego miesiąca odtwarza dokładnie te definicje.

T56-02: Site A 2026-10 ma niezależny zestaw (np. `D7=06:00–23:00`, 17h). Zapis października nie zmienia odczytu ani ponownego PDF września.

T56-03: API odrzuca próbę zdefiniowania `D1`/`N5`, kod spoza D/N, suffix <6, niepoprawny/nie-dodatni interval, niecałkowitą liczbę godzin oraz interval niejednoznaczny z innym kodem tej samej rodziny.

T56-04: `MonthlyPlanning` przy PRIMARY pokrywającym D pokazuje zdefiniowane D6+ miesiąca, ale nie N6+; dla N odwrotnie. Nie pokazuje tej funkcji dla S1/TRAINEE ani Assignmentu bez jednoznacznego D/N demandu.

T56-05: wybór `D7=17h` w ręcznej korekcie zmienia realne `start_datetime/end_datetime` Assignmentu, zapisuje przez istniejący manual-correction flow i podlega istniejącemu validatorowi/deviations. `operational_code` nie jest używany do przechowywania D7.

T56-06: po reloadzie grafiku kod nie musi być przechowywany na Assignment; eksport dla tego miesiąca ponownie rozpoznaje `D7` z realnego intervalu i miesięcznej konfiguracji.

T56-07: PDF pokazuje dodatkowy kod w komórce zarówno PLAN, jak i WYK; `plan_hours`/`wyk_hours` doliczają jego prawdziwą liczbę godzin, nigdy `0`.

T56-08: legenda PDF zawiera wszystkie używane/skonfigurowane dodatkowe D/N tego miesiąca, w tym kod powyżej slotu 6, bez wpływu na U/C/S1.

T56-09: `document_revision` zmienia się po zmianie miesięcznej definicji kodu w tym samym miesiącu i nie zmienia się wskutek modyfikacji definicji w innym miesiącu.

T56-10: D1–D5/N1–N5 zachowują dotychczasowe mapowanie, godziny i wydruk; istniejące export regression przechodzą bez zmiany semantyki.

T56-11: solver/shift catalog/WorkBalance/analytics pozostają bez zmian w diffie. Realny 17h Assignment automatycznie wpływa na WorkBalance/analitykę przez istniejący mechanizm, bez kodu T056 w tych modułach.

T56-12 — REAL PDF GATE: wygenerować rzeczywisty PDF miesiąca zawierający co najmniej D6, N6 i jeden dodatkowy kod z suffixem >6. Człowiek ocenia: czytelność komórek PLAN/WYK, poprawne sumy, legendę >5 slotów, brak kolizji/ucięcia, poprawną jedną legendę miesiąca i czytelność w skali szarości. PASS testów automatycznych bez tego gate'u nie zamyka T056.

## 11. PREIMPLEMENTATION AUDIT

Codex ma przed implementacją sprawdzić:
- czy osobny `(site_id,month)` current-state record jest rzeczywiście najmniejszym sposobem spełnienia trwałości bez zmiany semantyki `SitePrintSettings`;
- czy `site_repository.py` jest właściwym istniejącym ownerem persistence, bez nowego repository module;
- czy istniejący manual-correction payload wystarcza do zapisania wybranego intervalu bez backendowego „apply code” endpointu;
- czy `operational_code` powinien pozostać nietknięty;
- czy unikalność intervalu w rodzinie jest wystarczająca do jednoznacznego round-trip mapowania kodu;
- czy export potrzebuje miesięcznych definicji dokładnie w `_map_work_code`, `_hours_of`, legendzie i `document_revision`;
- czy `Room.tsx` jest właściwym ownerem `workingMonth` dla `PrintSettings` zgodnie z T053;
- czy scope nie pomija istniejącego ownera potrzebnego mechanicznie do migracji/API/UI/exportu.

Oczekiwany werdykt: `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL` z konkretnym trace do istniejącego kodu. Test nie tworzy kontraktu.

## 12. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T056/brief.md
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/application/durable_inputs.py
- api/routers/export.py
- frontend/src/api/client.ts
- frontend/src/Room.tsx
- frontend/src/screens/PrintSettings.tsx
- frontend/src/screens/MonthlyPlanning.tsx
- rota/application/schedule_export.py

Dozwolone są małe testy targetowane oraz istniejące testy export/manual-correction dotknięte przez zmianę kontraktu. Jeżeli preimplementation audit wykaże konieczność produktu poza literalnym `TASK_SCOPE`, architekt aktualizuje brief przed pracą CC.