# ROTA-T056 — dodatkowe miesięczne kody D/N do ręcznej korekty i wydruku

STATUS: READY FOR FINAL PREIMPLEMENTATION RE-AUDIT — ZERO DALSZEGO KODU PRODUKTU DO PASS

BASE_MAIN_SHA: `d2c5b85b6eb22d63e7f1edd5f9ae97ebacf97b84`

Źródła:
- `arch/FINDING_2026-09-05_DEFINABLE_WORK_CODE_DURATIONS.md` @ `27425435c03f20b111f855e215c14de8fbc43264`
- `tasks/ROTA-T056/round_01/tests/tests_r2.txt`
- `tasks/ROTA-T056/round_01/tests/tests_r4.txt`
- `tasks/ROTA-T056/round_01/tests/tests_r6.txt`
- decyzje OWNERA 2026-09-05 zapisane w findingu/BOARD/R4 oraz potwierdzenie zakresu wyjątku `_validate_item` po reproduktorze CC

## 1. Cel

Pozwolić koordynatorowi zdefiniować dla konkretnego **obiektu i miesiąca** dodatkowe kody realnej pracy `D6`, `D7`, ... / `N6`, `N7`, ... o niestandardowych przedziałach czasu, a następnie wybrać taki kod przy ręcznej korekcie istniejącego Assignmentu.

Wybranie kodu ma zmienić realny `Assignment.start_datetime/end_datetime`, przejść istniejący flow ręcznej korekty i walidacji/deviations, a następnie poprawnie trafić do PLAN, WYK, sum godzin, legendy i PDF.

Task służy domknięciu dokładnego bilansu godzin na koniec kwartału przez **ręczną korektę po PLAN/REPLAN**. Solver pozostaje nietknięty.

## 2. Decyzje OWNERA — zamrożone

1. Definiowalne są wyłącznie **dodatkowe** kody rodzin D/N: `D6+` i `N6+`.
2. **Długości** `D1–D5` / `N1–N5` oraz `FROZEN_WORK_CODE_HOURS` pozostają zamrożone. Istniejąca per-site edycja **godzin zegarowych start/end/end_next_day** standardowych kodów pozostaje dostępna.
3. Definicje dodatkowych kodów są **per `(site_id, month)`**. Zestaw jednego miesiąca nie wpływa na inny miesiąc ani na ponowny wydruk wcześniej zamkniętego miesiąca.
4. Koordynator najpierw definiuje kod w ustawieniach. Przy korekcie wybiera kod z istniejącej listy. Program nie tworzy ani nie dobiera kodu automatycznie z liczby godzin.
5. Wybranie dodatkowego kodu naprawdę zmienia realny przedział Assignmentu w bazie. To nie jest etykieta wydruku.
6. Korekta przechodzi istniejący `apply_manual_correction()` i istniejące `validate()`/deviations. Nie tworzyć drugiego mechanizmu korekty.
7. Dodatkowy kod realnej pracy trafia tak samo do **PLAN i WYK**.
8. U/C pozostają poza T056. `reserve_hours` i absence decomposition bez zmian.
9. Solver CP-SAT, `SiteProfile.standard_shifts`, `ShiftCatalogKind`, demand generation, WorkBalance i analytics pozostają bez zmian.
10. Rzeczywisty PDF jest częścią acceptance. Zielone testy nie zastępują oceny optycznej.
11. Legenda PDF pokazuje tylko kody faktycznie użyte. Jeśli mieszczą się czytelnie, pozostaje na stronie grafiku; jeśli nie, PDF ma drugą stronę legendy ze wszystkimi użytymi oznaczeniami. Bez obcięcia, ukrycia i nieczytelnego zmniejszania.
12. Istniejący fail-closed check provenance Assignment↔ShiftDemand zostaje zachowany dla normalnych przypadków. T056 wprowadza **jeden wąski wyjątek wyłącznie dla miesięcznych D6+/N6+**, opisany w §9.

## 3. Kod nie jest nowym `operational_code`

Dzisiejsze `D1–D5/N1–N5` nie są trwałą etykietą Assignmentu. `schedule_export.py::_map_work_code()` rozpoznaje kod z rodziny D/N, realnego przedziału Assignmentu i skonfigurowanego przedziału kodu.

T056 rozszerza ten sam mechanizm o miesięczne dodatkowe kody.

**Nie zapisywać `D6/N6/...` do `Assignment.operational_code` tylko po to, aby pamiętać wybrany kod.** Wybranie kodu w UI ustawia realny przedział czasu; późniejszy eksport ponownie rozpoznaje kod z tego przedziału i konfiguracji miesiąca.

## 4. Minimalny model danych

Obecny `SitePrintSettings` jest per-site i zawiera dane globalne wydruku. Nie zmieniać jego semantyki na per-month ani nie kopiować całych ustawień do każdego miesiąca.

Potrzebny jest mały current-state persistence seam dla wyłącznie dodatkowych miesięcznych kodów D/N, kluczowany `(site_id, month)`:
- jeden rekord per `(site_id, month)`;
- `extra_work_code_intervals_json`: `code -> WorkCodeInterval`;
- brak historii, statusów, activation flags i osobnego subsystemu;
- miesiąc canonical first-of-month `YYYY-MM-01`.

Repozytorium pozostaje w `rota/persistence/site_repository.py`; nie tworzyć nowego repository module dla jednej mapy JSON.

## 5. Walidacja i wspólny invariant signature

Owning boundary zapisu D6+/N6+ wymusza:
- tylko rodzina `D` albo `N`;
- suffix integer `>= 6`;
- dokładnie jeden `WorkCodeInterval(start_time,end_time,end_next_day)`;
- dodatni czas trwania będący całkowitą dodatnią liczbą godzin;
- brak osobnego `duration_hours` — duration jest pochodną interval;
- jednoznaczny interval/signature w obrębie rodziny.

Invariant ma dwa legalne wejścia:

1. **monthly-extra save:** D6+/N6+ nie może dostać signature identycznego jak bieżący standardowy kod tej samej rodziny ani jak inny extra code tego samego `(site,month)`;
2. **istniejący per-site standard print-settings save:** zmiana start/end/end_next_day standardowego D1–D5/N1–N5, przy zachowaniu zamrożonej długości, nie może stworzyć signature kolidującego z żadnym zapisanym miesięcznym D6+/N6+ tej samej rodziny dla tego Site; sprawdzenie obejmuje wszystkie zapisane miesiące obiektu.

Odrzucony zapis zachowuje wcześniejsze dane i istniejącą semantykę błędu. Nie dodawać duplicate defensive validation w exporterze dla hipotetycznej surowej korupcji DB.

Nie ograniczać liczby dodatkowych kodów do jednego slotu ani do D6/N6.

## 6. Ustawienia API/UI

Owner UI pozostaje `Panel sterowania -> Obiekt -> Ustawienia wydruku` (`PrintSettings.tsx`). `workingMonth` ma jednego ownera w `frontend/src/screens/Room.tsx` i jest przekazywany `Room -> ControlPanel -> PrintSettings`; `PrintSettings` nie tworzy drugiego month state.

Ekran rozróżnia:
- dane trwałe per-site niezależne od miesiąca;
- osobną sekcję miesięczną „Dodatkowe kody dla YYYY-MM”.

Nie zmieniać istniejących per-site pól `company_print_name`, `site_print_name`, `base_regime`, standardowych `work_code_intervals`, `reserve_hours`, `s1_default_interval` na per-month. Zachować edycję godzin zegarowych standardowych kodów przy zamrożonych długościach.

W `api/routers/export.py` dodać wąski read/write monthly subresource dla extra D/N codes. `frontend/src/api/client.ts` odzwierciedla kontrakt bez reinterpretacji.

`PrintSettings.tsx`:
- pokazuje standardowe D1–D5/N1–N5 jak dziś i zachowuje edycję start/end/end_next_day;
- dodaje/usuwa D6+/N6+ dla wskazanego miesiąca;
- nie generuje kodu automatycznie z godzin;
- zmiana `workingMonth` pokazuje niezależny zestaw miesiąca.

## 7. Unified action history

Zapis miesięcznych extra codes używa istniejącego unified action history:
- mały wrapper w `rota/application/durable_inputs.py`;
- istniejący `CoordinatorActionKind.CONTEXT_CONFIGURATION_SAVED`;
- action wskazuje `site_id` i `month`;
- zapis konfiguracji i action atomowe zgodnie z istniejącym wzorcem;
- bez ScheduleVersion, nowego action kind i nowego subsystemu historii.

Jeden targetowany test wystarcza.

## 8. Ręczna korekta — reużycie istniejącego flow

Backend `apply_manual_correction()` pozostaje ownerem zapisu realnego Assignmentu i istniejącej walidacji/deviations. T056 nie dodaje endpointu „apply code”.

W `MonthlyPlanning.tsx`, przy edycji zwykłego Assignmentu PRIMARY:
- UI pobiera extra codes dla `(site_id, workingMonth)`;
- dla D oferuje tylko D6+, dla N tylko N6+;
- wybór kodu buduje nowy realny przedział na **dacie jednoznacznie pokrywanego ShiftDemandu** zgodnie z definicją kodu;
- pozostałe pola Assignmentu zachowuje, w tym `covers_demand_id`;
- zapis idzie przez istniejące `api.applyManualCorrection()`;
- validator/deviations zachowują obecną semantykę.

Jeśli Assignment nie ma jednoznacznego pokrywanego D/N demandu, nie oferować dodatkowego kodu i nie zgadywać. S1, TRAINEE, NN/CANCELLED i freeze bez zmian.

## 9. Eksport i WORK_PROVENANCE_INCOMPLETE — wąski wyjątek T056

`generate_schedule_pdf()` ładuje dodatkowe kody dla dokładnego `(site_id,month)` eksportowanego dokumentu.

### 9.1 `_validate_item` — reguła wiążąca po R6

Obecny fail-closed invariant pozostaje domyślny:
- TRAINEE nadal jest odrzucany tam, gdzie był odrzucany;
- Assignment musi mieć spójny `covers_demand_id` wskazujący istniejący demand;
- dla zwykłego Assignmentu różnica realnego `start_datetime/end_datetime` względem `ShiftDemand.start_datetime/end_datetime` nadal oznacza `WORK_PROVENANCE_INCOMPLETE`.

**Jedyny wyjątek T056:** rozbieżność Assignment vs ShiftDemand jest dopuszczalna wyłącznie wtedy, gdy wszystkie warunki są spełnione równocześnie:

1. Assignment jest zwykłym realnym Assignmentem objętym T056, nie S1/TRAINEE ani przypadkiem bez jednoznacznego D/N demandu;
2. `covers_demand_id` nadal wskazuje spójny demand należący do właściwego schedule version/site;
3. dla dokładnego `(site_id, month)` istnieje zapisana definicja miesięcznego dodatkowego kodu `D6+` albo `N6+`;
4. rodzina kodu jest zgodna z `demand.shift_kind` (`D*` tylko dla D, `N*` tylko dla N);
5. realny Assignment jest osadzony na **dacie pokrywanego demandu**, bez przesuwania go na inny dzień;
6. realny interval Assignmentu odpowiada definicji kodu **dokładnie**, nie tylko długością: `start_time`, `end_time` oraz `end_next_day` muszą być identyczne z miesięczną definicją;
7. jeśli nie ma takiego dokładnego dopasowania, zachowanie pozostaje fail-closed `WORK_PROVENANCE_INCOMPLETE`.

Nie dopuszczać „dowolnej ręcznej rozbieżności”, podobnej długości ani luźnego tolerance. Ten wyjątek istnieje tylko dlatego, że OWNER jawnie zezwala na ręczne zastąpienie standardowego intervalu demandu wcześniej zdefiniowanym miesięcznym D6+/N6+.

Sposób technicznego przekazania miesięcznej konfiguracji do `_validate_item` lub wydzielenia helpera jest decyzją implementacyjną, ale nie może zmienić powyższej granicy.

### 9.2 `_map_work_code`

Po przejściu provenance check `_map_work_code()` wykonuje końcowe dokładne mapowanie. Rozpatruje standardowe D1–D5/N1–N5 oraz miesięczne D6+/N6+. Rodzina nadal pochodzi z `demand.shift_kind`; brak dokładnego dopasowania pozostaje `WORK_CODE_MAPPING_REQUIRED`.

Nie tworzyć nowego ShiftDemandu, nie modyfikować demand generation, nie zapisywać D6+/N6+ w `operational_code`, nie zmieniać solvera/PLAN/REPLAN.

### 9.3 Sumy PLAN/WYK

`_hours_of()` nie może dla D6+/N6+ zwracać cicho `0`. Dla extra code bierze zwalidowany duration z miesięcznej konfiguracji. U/C i S1 bez zmian. PLAN i WYK realnej pracy dostają ten sam kod i liczbę godzin.

### 9.4 Legenda i layout

Legenda zawiera wyłącznie oznaczenia faktycznie użyte:
- jeśli mieszczą się czytelnie — legenda na stronie grafiku;
- jeśli nie — druga strona legendy ze wszystkimi użytymi oznaczeniami;
- bez obcięcia, ukrycia i agresywnego zmniejszania tekstu.

### 9.5 Document revision

Miesięczne definicje extra codes wpływają na deterministyczny `document_revision`. Zmiana konfiguracji tego samego `(site,month)` zmienia revision; konfiguracja innego miesiąca nie zmienia revision dokumentu.

## 10. Size gate — dokładny OWNER-accepted baseline exception

OWNER akceptuje dla T056 dokładnie sześć zastanych naruszeń size gate, odtworzonych na brief SHA `9d8305dd10202d5e2a4052361523f1bb1344eaef`:

1. `rota/persistence/db.py` — 635 linii > 600;
2. `rota/application/schedule_export.py` — 684 linie > 600;
3. `rota/application/schedule_export.py::_apply_24h_periods` — 53 linie > 50;
4. `tests/test_t012.py` — 1735 linii > 600;
5. `tests/test_t019b.py` — 907 linii > 600;
6. `tests/test_t020.py` — 773 linie > 600.

Warunki wyjątku:
- raportować dokładne wartości baseline i HEAD;
- nie osłabiać ani nie zmieniać `backend.py`;
- nie tworzyć nowej siódmej kategorii/naruszenia;
- zmiany w już nadmiarowych plikach ograniczyć do koniecznego diffu T056;
- czerwony wynik tych sześciu pozycji jawnie klasyfikować jako OWNER-accepted baseline exception, nie jako PASS.

T056 nie refaktoryzuje dużych plików tylko po to, by wyzerować metrykę.

## 11. Zastane stale schema-version tests

Przed T056 cztery istniejące testy mają literalne nieaktualne oczekiwania wersji schematu (`tests/test_t012.py`, `tests/test_t019b.py`, `tests/test_t020.py`, `tests/test_t023b.py`). To stale-oracle/source-shape failures istniejące przed taskiem.

T056 autoryzuje wyłącznie literalną aktualizację tych oczekiwań do nowej rzeczywistej `LATEST_SCHEMA_VERSION`, bez innych zmian zachowania testów.

## 12. Zakaz rozszerzania zakresu

Poza zakresem T056:
- solver/PLAN/REPLAN;
- tworzenie lub modyfikowanie ShiftDemandów dla extra codes;
- `SiteProfile.standard_shifts`, `ShiftCatalogKind`, demand generation;
- WorkBalance, analytics, target-hours semantics;
- U/C, `reserve_hours`, absence decomposition;
- automatyczne tworzenie/dobieranie kodów;
- zmiana zamrożonych długości D1–D5/N1–N5 / `FROZEN_WORK_CODE_HOURS`;
- nowe `operational_code` semantics;
- ogólne rozluźnienie `_validate_item` dla ręcznych korekt innych niż dokładnie dopasowane D6+/N6+;
- warning/history/audit subsystem specjalnie dla kodów;
- nowy ogólny custom shift catalog;
- defensive recovery dla surowo uszkodzonej bazy;
- refaktor size-gate niezwiązany z funkcją T056.

Jeśli implementacja wydaje się wymagać któregoś z powyższych, wraca do architekta.

## 13. Acceptance

T56-01: Site A / 2026-09 zapisuje `D6=06:00–20:00` 14h i `N6=20:00–06:00 next day` 10h; reload odtwarza definicje.

T56-02: 2026-10 ma niezależny zestaw, np. D7 17h; zapis października nie zmienia odczytu ani PDF września.

T56-03: wspólny invariant signature działa w obu kierunkach. (A) standard istnieje -> kolidujący D6+/N6+ odrzucony; (B) monthly D6+/N6+ istnieje -> kolidująca zmiana godzin zegarowych standardowego kodu tej samej rodziny odrzucona po sprawdzeniu wszystkich miesięcy Site. Odrzucony zapis nie zmienia danych. Monthly API odrzuca też D1/N5, złą rodzinę/suffix, zły/nie-dodatni/niecałkowity interval i kolizję z innym extra code.

T56-04: zapis monthly extra codes pojawia się w unified action history jako `CONTEXT_CONFIGURATION_SAVED` z właściwym site+month i nie tworzy ScheduleVersion.

T56-05: MonthlyPlanning przy PRIMARY D pokazuje D6+, przy N N6+; nie pokazuje funkcji dla S1/TRAINEE ani bez jednoznacznego D/N demandu.

T56-06: wybór D7 17h zmienia realne start/end Assignmentu przez istniejący manual-correction flow, przechodzi validator/deviations i nie używa `operational_code` do pamiętania D7.

T56-07 — WORK PROVENANCE EXACT EXCEPTION: dla demandu D na konkretnej dacie i miesięcznego D7 z dokładnym intervalem, ręcznie skorygowany Assignment zachowuje ten sam poprawny `covers_demand_id`; `_validate_item` akceptuje rozbieżność względem standardowego intervalu demandu wyłącznie dlatego, że Assignment dokładnie odpowiada D7 tego samego site/month/family/date w `start_time/end_time/end_next_day`. Następnie `_map_work_code` rozpoznaje D7.

T56-08 — FAIL-CLOSED NEGATIVES: ta sama ścieżka nadal zwraca `WORK_PROVENANCE_INCOMPLETE`, gdy brakuje miesięcznego extra code, rodzina D/N się nie zgadza, data nie odpowiada dacie pokrywanego demandu, start_time/end_time/end_next_day nie pasują dokładnie, Assignment ma inną dowolną ręczną rozbieżność albo `covers_demand_id` jest niespójny. Samo dopasowanie długości nie wystarcza.

T56-09: PDF pokazuje extra code w PLAN i WYK; sumy doliczają prawdziwą liczbę godzin, nigdy 0.

T56-10: legenda pokazuje tylko kody faktycznie użyte; mały zestaw pozostaje czytelnie na stronie grafiku.

T56-11: przy zbyt dużej liczbie użytych oznaczeń PDF ma drugą stronę legendy ze wszystkimi użytymi kodami; nic nie jest obcięte, ukryte ani nieczytelnie zmniejszone.

T56-12: `document_revision` zmienia się po zmianie miesięcznej definicji w tym samym miesiącu i nie zmienia się wskutek konfiguracji innego miesiąca.

T56-13: D1–D5/N1–N5 zachowują zamrożone długości i istniejącą per-site edycję godzin zegarowych; solver/shift catalog/demand generation/WorkBalance/analytics pozostają bez zmian w diffie.

T56-14 — REAL PDF GATE A: rzeczywisty PDF na danych demonstracyjnych z D6, N6 i kodem suffix >6, gdy legenda mieści się na stronie grafiku. Człowiek sprawdza PLAN/WYK, sumy, znaczenie oznaczeń, brak kolizji/ucięcia i skalę szarości.

T56-15 — REAL PDF GATE B: rzeczywisty PDF z taką liczbą faktycznie użytych oznaczeń, aby wymagana była druga strona legendy. Człowiek sprawdza kompletność, czytelność i brak utraty oznaczeń. Zielone testy bez obu gate'ów nie zamykają T056.

## 14. FINAL PREIMPLEMENTATION RE-AUDIT

Codex ma sprawdzić wyłącznie:
- czy wyjątek `_validate_item` jest dokładnie zawężony do zapisanego miesięcznego D6+/N6+ dla właściwego site/month/family/date i exact start/end/end_next_day;
- czy wszystkie inne rozbieżności Assignment↔Demand nadal są fail-closed;
- czy solver, demand generation i `operational_code` pozostają nietknięte;
- dwa legalne wejścia do invariantu signature, bez duplicate exporter validation;
- zachowanie zamrożonych długości i edycji godzin zegarowych standardowych kodów;
- dokładnie sześć OWNER-accepted size violations i baseline-vs-HEAD/no seventh violation;
- miesięczny current-state seam i brak zmiany semantyki `SitePrintSettings`;
- unified action history przez `CONTEXT_CONFIGURATION_SAVED`;
- `Room -> ControlPanel -> PrintSettings` jako jedyny workingMonth flow;
- export: exact mapping, `_hours_of`, used-only legend, druga strona legendy, revision;
- literalny TASK_SCOPE i WHERE_MAP.

Oczekiwany werdykt: `PASS — READY_FOR_IMPLEMENTATION` albo `FAIL` wyłącznie z konkretną pozostałą sprzecznością. Test nie tworzy kontraktu.

## 15. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `rota/persistence/site_repository.py`: `SitePrintSettings`, `WorkCodeInterval`, print-settings persistence + monthly-extra owner/helper + cross-check obu write boundaries
  - `rota/persistence/db.py`: schema migration registry
  - `rota/application/durable_inputs.py`: `save_print_settings`, unified `CONTEXT_CONFIGURATION_SAVED` pattern + monthly-extra wrapper
  - `api/routers/export.py`: print-settings DTO/endpoints + monthly-extra subresource
  - `rota/application/schedule_export.py`: `_validate_item`, `_map_work_code`, `_hours_of`, legend/layout owner, `_document_revision`, `generate_schedule_pdf`
  - `frontend/src/screens/Room.tsx`: `workingMonth`
  - `frontend/src/screens/ControlPanel.tsx`: prop seam Room -> PrintSettings
  - `frontend/src/screens/PrintSettings.tsx`: settings owner UI
  - `frontend/src/screens/MonthlyPlanning.tsx`: existing manual-correction editor
  - `frontend/src/api/client.ts`: print settings + manual correction API surface
- REASON: T056 dodaje miesięczny owner danych i endpointy, rozszerza mapping/sum/legend/revision, przekazuje workingMonth, egzekwuje signature invariant na dwóch write boundaries i wąsko rozszerza istniejący provenance check wyłącznie dla exact monthly extra-code match. `where.py` jest dowodem wyszukania, nie źródłem wymagań.

## 16. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T056/brief.md
- rota/persistence/db.py
- rota/persistence/site_repository.py
- rota/application/durable_inputs.py
- api/routers/export.py
- frontend/src/api/client.ts
- frontend/src/screens/Room.tsx
- frontend/src/screens/ControlPanel.tsx
- frontend/src/screens/PrintSettings.tsx
- frontend/src/screens/MonthlyPlanning.tsx
- rota/application/schedule_export.py
- tests/test_t056.py
- tests/test_t012.py
- tests/test_t019b.py
- tests/test_t020.py
- tests/test_t023b.py
- tasks/ROTA-T056/round_01/tests/real_pdf_gate_a.pdf
- tasks/ROTA-T056/round_01/tests/real_pdf_gate_b.pdf
- tasks/ROTA-T056/round_01/tests/real_pdf_gate_review.md

Standalone `tasks/ROTA-T056/round_01/tests/cc_blocker_r6_work_provenance.py` i jego output są wyłącznie materiałem diagnostycznym spoza finalnego TASK_SCOPE. Przed finalnym delivery przypadek R6 ma zostać przeniesiony do `tests/test_t056.py`, a standalone reproduktor/output usunięty z diffu tasku. Nie rozszerzać TASK_SCOPE tylko po to, by zachować jednorazowy reproduktor.

Nie dodawać innych plików testowych „na wszelki wypadek”. Jeśli implementacja wymaga zmiany istniejącego testu export/manual-correction poza powyższą listą, architekt aktualizuje TASK_SCOPE **przed** zmianą tego pliku.
