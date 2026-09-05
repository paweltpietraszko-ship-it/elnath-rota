# ROTA-T056 — dodatkowe miesięczne kody D/N do ręcznej korekty i wydruku

STATUS: READY FOR FINAL PREIMPLEMENTATION RE-AUDIT — ZERO KODU PRODUKTU

BASE_MAIN_SHA: `b85c46d5e36c5e86d6807c5269960cd331c0f146`

Źródła:
- `arch/FINDING_2026-09-05_DEFINABLE_WORK_CODE_DURATIONS.md` @ `27425435c03f20b111f855e215c14de8fbc43264`
- `tasks/ROTA-T056/round_01/tests/tests_r2.txt`
- `tasks/ROTA-T056/round_01/tests/tests_r4.txt`
- decyzje OWNERA 2026-09-05 zapisane w findingu/BOARD/R4

## 1. Cel

Pozwolić koordynatorowi zdefiniować dla konkretnego **obiektu i miesiąca** dodatkowe kody realnej pracy `D6`, `D7`, ... / `N6`, `N7`, ... o niestandardowych przedziałach czasu, a następnie wybrać taki kod przy ręcznej korekcie istniejącego Assignmentu.

Wybranie kodu ma zmienić realny `Assignment.start_datetime` / `end_datetime`, przejść istniejącą walidację ręcznej korekty i następnie poprawnie trafić do PLAN, WYK, sum godzin, legendy oraz PDF.

Task służy domknięciu dokładnego bilansu godzin na koniec kwartału przez **ręczną korektę po PLAN/REPLAN**. Solver pozostaje nietknięty.

## 2. Decyzje OWNERA — zamrożone

1. Definiowalne są wyłącznie **dodatkowe** kody rodzin D/N: `D6+` i `N6+`.
2. **Długości** `D1–D5` / `N1–N5` oraz `FROZEN_WORK_CODE_HOURS` pozostają zamrożone. Jednocześnie istniejąca per-site edycja **godzin zegarowych start/end/end_next_day** standardowych kodów pozostaje dostępna, bo różne obiekty mogą zaczynać tę samą 12h/24h służbę o różnych godzinach.
3. Definicje dodatkowych kodów są **per `(site_id, month)`**. Zestaw jednego miesiąca nie wpływa na inny miesiąc, w tym na ponowny wydruk wcześniej zamkniętego miesiąca.
4. Koordynator najpierw definiuje kod w ustawieniach. Przy korekcie wybiera kod z istniejącej listy. Program nie tworzy ani nie dobiera kodu automatycznie z liczby godzin.
5. Wybranie dodatkowego kodu naprawdę zmienia realny przedział Assignmentu w bazie. To nie jest etykieta wydruku.
6. Korekta przechodzi istniejący flow `apply_manual_correction()` i istniejącą walidację/deviations. Nie tworzyć drugiego mechanizmu korekty.
7. Dodatkowy kod realnej pracy trafia tak samo do **PLAN i WYK**.
8. U/C pozostają całkowicie poza T056. Istniejący `reserve_hours` i absence decomposition bez zmian.
9. Solver CP-SAT, `SiteProfile.standard_shifts`, `ShiftCatalogKind`, WorkBalance i analytics pozostają bez zmian.
10. Rzeczywisty PDF jest częścią acceptance. Zielone testy nie zastępują oceny optycznej wydruku.
11. **Legenda PDF pokazuje tylko kody faktycznie użyte w danym wydruku.** Jeśli wszystkie użyte oznaczenia mieszczą się czytelnie na stronie grafiku, legenda pozostaje na tej stronie. Jeśli nie mieszczą się czytelnie, PDF dostaje **drugą stronę legendy** zawierającą wszystkie użyte oznaczenia. Nie wolno kodów obcinać, ukrywać ani zmniejszać do nieczytelnego rozmiaru.

## 3. Kod nie jest nowym `operational_code`

Dzisiejsze `D1–D5/N1–N5` nie są trwałą etykietą Assignmentu. `schedule_export.py::_map_work_code()` rozpoznaje kod z rodziny D/N, realnego `start_datetime/end_datetime` i skonfigurowanego przedziału kodu.

T056 rozszerza ten sam mechanizm o miesięczne dodatkowe kody.

**Nie zapisywać `D6/N6/...` do `Assignment.operational_code` tylko po to, aby pamiętać wybrany kod.** Wybranie kodu w UI jest skrótem do ustawienia jego realnego przedziału czasu; późniejszy eksport ponownie rozpoznaje kod z tego przedziału i konfiguracji miesiąca.

## 4. Minimalny model danych

Obecny `SitePrintSettings` jest per-site i zawiera dane globalne wydruku. Nie wolno zmieniać jego semantyki na per-month ani kopiować całych ustawień wydruku do każdego miesiąca.

Potrzebny jest mały current-state persistence seam dla wyłącznie dodatkowych miesięcznych kodów D/N, kluczowany przez `(site_id, month)`:
- jeden rekord per `(site_id, month)`;
- `extra_work_code_intervals_json`: mapowanie `code -> WorkCodeInterval`;
- brak historii, statusów, activation flags i osobnego subsystemu;
- miesiąc canonical first-of-month `YYYY-MM-01`.

Repozytorium pozostaje w `rota/persistence/site_repository.py`; nie tworzyć nowego repository module dla jednej mapy JSON.

## 5. Walidacja i jeden wspólny invariant signature

Owning boundary zapisu D6+/N6+ wymusza:
- tylko rodzina `D` albo `N`;
- suffix integer `>= 6`;
- dokładnie jeden `WorkCodeInterval(start_time,end_time,end_next_day)`;
- dodatni czas trwania będący całkowitą dodatnią liczbą godzin;
- brak osobnego `duration_hours` — duration jest pochodną interval;
- jednoznaczny interval/signature w obrębie rodziny.

Wspólny invariant ma **dwa legalne wejścia**, bo standardowa długość jest zamrożona, ale standardowe godziny zegarowe są nadal edytowalne:

1. **monthly-extra save:** D6+/N6+ nie może dostać signature identycznego jak bieżący standardowy kod tej samej rodziny ani jak inny extra code tego samego `(site,month)`;
2. **istniejący per-site standard print-settings save:** zmiana start/end/end_next_day standardowego D1–D5/N1–N5 — przy zachowaniu jego zamrożonej długości — nie może stworzyć signature kolidującego z żadnym zapisanym miesięcznym D6+/N6+ tej samej rodziny dla tego Site. Ponieważ standardowe ustawienie jest per-site, sprawdzenie obejmuje wszystkie zapisane miesiące tego obiektu.

Odrzucony zapis w obu kierunkach zachowuje wcześniejsze dane i istniejącą semantykę błędu zapisu. **Nie dodawać duplicate defensive validation w exporterze** tylko na wypadek surowej korupcji bazy.

Nie ograniczać liczby dodatkowych kodów do jednego slotu ani do D6/N6.

## 6. Ustawienia API/UI

Owner UI pozostaje `Panel sterowania -> Obiekt -> Ustawienia wydruku` (`PrintSettings.tsx`). Aktualny `workingMonth` ma jednego ownera w `frontend/src/screens/Room.tsx` (T053) i jest przekazywany istniejącą ścieżką `Room -> ControlPanel -> PrintSettings`; `PrintSettings` nie tworzy drugiego month state.

Opis ekranu ma rozróżniać:
- istniejące dane trwałe per-site niezależne od miesiąca;
- osobną sekcję miesięczną „Dodatkowe kody dla YYYY-MM”.

Nie zmieniać istniejących per-site pól `company_print_name`, `site_print_name`, `base_regime`, standardowych `work_code_intervals`, `reserve_hours`, `s1_default_interval` na per-month. Nie wyłączać istniejącej możliwości ustawiania start/end standardowych kodów przy zachowaniu ich zamrożonych długości.

W `api/routers/export.py` dodać wąski read/write monthly subresource dla extra D/N codes. `frontend/src/api/client.ts` odzwierciedla kontrakt bez reinterpretacji.

`PrintSettings.tsx`:
- pokazuje standardowe D1–D5/N1–N5 jak dziś i zachowuje ich obecną edycję start/end/end_next_day;
- dodaje/usuwa D6+/N6+ dla wskazanego miesiąca oraz ustawia start/end/end_next_day;
- nie generuje kodu automatycznie z godzin;
- zmiana `workingMonth` pokazuje niezależny zestaw miesiąca.

## 7. Unified action history

Zapis miesięcznych extra codes jest materialną zmianą konfiguracji koordynatora i ma użyć istniejącego unified action history.

- mały wrapper w `rota/application/durable_inputs.py`;
- reużywa istniejący `CoordinatorActionKind.CONTEXT_CONFIGURATION_SAVED`;
- action wskazuje `site_id` i `month`;
- zapis konfiguracji i action są atomowe zgodnie z istniejącym wzorcem durable inputs;
- nie tworzy ScheduleVersion, nowego action kind ani nowego subsystemu historii.

Jeden targetowany test wystarcza do potwierdzenia tego seam-u; nie kopiować pełnej macierzy T019b/T021.

## 8. Ręczna korekta — reużycie istniejącego flow

Backend `apply_manual_correction()` już akceptuje realny Assignment z dowolnym `start_datetime/end_datetime` i uruchamia normalne `validate()`/deviations. T056 nie dodaje drugiego endpointu ani komendy „apply code”.

W `MonthlyPlanning.tsx`, przy edycji zwykłego Assignmentu PRIMARY:
- UI pobiera dodatkowe kody dla `(site_id, workingMonth)`;
- dla D oferuje tylko D6+, dla N tylko N6+;
- wybór kodu buduje nowy realny przedział na dacie jednoznacznie pokrywanego ShiftDemandu;
- pozostałe pola Assignmentu zachowuje;
- zapis idzie przez istniejące `api.applyManualCorrection()`;
- validator/deviations zachowują obecną semantykę.

Jeśli Assignment nie ma jednoznacznego pokrywanego D/N demandu, nie oferować dodatkowego kodu i nie zgadywać. S1, TRAINEE, NN/CANCELLED i freeze bez zmian.

## 9. Eksport

`generate_schedule_pdf()` ładuje dodatkowe kody dla dokładnego `(site_id,month)` eksportowanego dokumentu.

### Mapowanie
`_map_work_code()` rozpatruje standardowe skonfigurowane D1–D5/N1–N5 oraz miesięczne D6+/N6+. Rodzina nadal pochodzi z `demand.shift_kind`; Assignment musi dokładnie pasować intervalem; brak dopasowania pozostaje `WORK_CODE_MAPPING_REQUIRED`.

### Sumy PLAN/WYK
`_hours_of()` nie może dla D6+/N6+ zwracać cicho `0`. Dla dodatkowego kodu bierze zwalidowany duration z miesięcznej konfiguracji. U/C i S1 bez zmian. PLAN i WYK realnej pracy dostają ten sam kod i liczbę godzin.

### Legenda i layout
Legenda zawiera **wyłącznie oznaczenia faktycznie użyte w renderowanym dokumencie**. Nie drukować nieużywanego D6/N6 tylko dlatego, że został skonfigurowany.

- wariant 1: wszystkie użyte oznaczenia mieszczą się czytelnie — legenda na stronie grafiku;
- wariant 2: nie mieszczą się czytelnie — druga strona legendy ze wszystkimi użytymi oznaczeniami;
- bez obcięcia, ukrycia i agresywnego zmniejszania tekstu.

### Document revision
Miesięczne definicje dodatkowych kodów wpływają na deterministyczny `document_revision`. Zmiana konfiguracji tego samego `(site,month)` zmienia revision; konfiguracja innego miesiąca nie zmienia revision danego dokumentu.

## 10. Size gate — dokładny OWNER-accepted baseline exception

OWNER akceptuje dla T056 **dokładnie sześć** zastanych naruszeń size gate, odtworzonych na brief SHA `9d8305dd10202d5e2a4052361523f1bb1344eaef`:

1. `rota/persistence/db.py` — 635 linii > 600;
2. `rota/application/schedule_export.py` — 684 linie > 600;
3. `rota/application/schedule_export.py::_apply_24h_periods` — 53 linie > 50;
4. `tests/test_t012.py` — 1735 linii > 600;
5. `tests/test_t019b.py` — 907 linii > 600;
6. `tests/test_t020.py` — 773 linie > 600.

Warunki wyjątku:
- implementacja raportuje dokładne wartości baseline i HEAD;
- nie osłabia ani nie zmienia `backend.py`;
- nie tworzy nowej **siódmej** kategorii/naruszenia;
- zmiany w już nadmiarowych plikach ograniczają się do koniecznego diffu T056;
- czerwony wynik tych sześciu pozycji jest jawnie klasyfikowany jako `OWNER-accepted baseline exception`, nie ukrywany i nie nazywany PASS `backend.py`.

T056 **nie** ma refaktoryzować dużych plików tylko po to, by wyzerować metrykę. Ewentualny task redukcji pozostaje osobną, nieblokującą propozycją techniczną.

## 11. Zastane stale schema-version tests

Przed T056 cztery istniejące testy mają literalne, już nieaktualne oczekiwania wersji schematu (`tests/test_t012.py`, `tests/test_t019b.py`, `tests/test_t020.py`, `tests/test_t023b.py`). Są to source-shape/stale-oracle failures istniejące przed taskiem, nie defekt produktu T056.

Ponieważ T056 dodaje nową migrację i musi mieć spójny mechaniczny baseline, task **autoryzuje wyłącznie literalną aktualizację tych oczekiwań do nowej rzeczywistej `LATEST_SCHEMA_VERSION`**, bez zmian zachowania testowanych funkcji. Nie wolno użyć T056 do innych poprawek tych testów.

## 12. Zakaz rozszerzania zakresu

Poza zakresem T056:
- solver/PLAN/REPLAN;
- `SiteProfile.standard_shifts`, `ShiftCatalogKind`, demand generation;
- WorkBalance, analytics, target-hours semantics;
- U/C, `reserve_hours`, absence decomposition;
- automatyczne tworzenie/dobieranie kodów;
- zmiana zamrożonych **długości** D1–D5/N1–N5 / `FROZEN_WORK_CODE_HOURS`;
- nowe `operational_code` semantics;
- warning/history/audit subsystem specjalnie dla kodów;
- nowy ogólny custom shift catalog;
- defensive recovery dla surowo uszkodzonej bazy;
- refaktor size-gate niezwiązany z funkcją T056.

Jeśli implementacja wydaje się wymagać któregoś z powyższych, wraca do architekta.

## 13. Acceptance

T56-01: Site A / 2026-09 zapisuje `D6=06:00–20:00` 14h i `N6=20:00–06:00 next day` 10h; reload odtwarza definicje.

T56-02: 2026-10 ma niezależny zestaw (np. D7 17h); zapis października nie zmienia odczytu ani PDF września.

T56-03: wspólny invariant signature jest egzekwowany w obu legalnych kolejnościach zapisu. (A) Standardowy interval istnieje -> próba zapisania kolidującego D6+/N6+ jest odrzucona. (B) Monthly D6+/N6+ istnieje -> próba zmiany start/end/end_next_day standardowego kodu tej samej rodziny na kolidującą signature — przy zachowaniu jego zamrożonej długości — jest odrzucona po sprawdzeniu wszystkich miesięcy tego Site. Odrzucony zapis nie zmienia wcześniejszych danych. Dodatkowo monthly-extra API odrzuca D1/N5, złą rodzinę/suffix, zły/nie-dodatni/niecałkowity interval i kolizję z innym extra code tej samej rodziny.

T56-04: zapis monthly extra codes pojawia się w istniejącym unified action history jako `CONTEXT_CONFIGURATION_SAVED` z właściwym site+month i nie tworzy ScheduleVersion.

T56-05: MonthlyPlanning przy PRIMARY D pokazuje D6+, przy N N6+; nie pokazuje funkcji dla S1/TRAINEE ani bez jednoznacznego D/N demandu.

T56-06: wybór D7 17h zmienia realne start/end Assignmentu przez istniejący manual-correction flow, przechodzi validator/deviations i nie używa `operational_code` do pamiętania D7.

T56-07: po reloadzie eksport ponownie rozpoznaje D7 z realnego intervalu i miesięcznej konfiguracji.

T56-08: PDF pokazuje extra code w PLAN i WYK; sumy doliczają prawdziwą liczbę godzin, nigdy 0.

T56-09: legenda pokazuje tylko kody faktycznie użyte. Mały zestaw pozostaje czytelnie na stronie grafiku.

T56-10: dla zestawu użytych oznaczeń, który nie mieści się czytelnie na stronie grafiku, PDF ma drugą stronę legendy ze wszystkimi użytymi kodami; nic nie jest obcięte, ukryte ani nieczytelnie zmniejszone.

T56-11: `document_revision` zmienia się po zmianie miesięcznej definicji w tym samym miesiącu i nie zmienia się wskutek konfiguracji innego miesiąca.

T56-12: D1–D5/N1–N5 zachowują dotychczasowe zamrożone długości i dotychczasową możliwość per-site ustawienia ich godzin zegarowych; solver/shift catalog/WorkBalance/analytics pozostają bez zmian w diffie.

T56-13 — REAL PDF GATE A: wygenerować rzeczywisty PDF na danych demonstracyjnych z D6, N6 i kodem suffix >6, gdzie legenda mieści się na stronie grafiku. Człowiek sprawdza PLAN/WYK, sumy, znaczenie wszystkich użytych oznaczeń, brak kolizji/ucięcia i skalę szarości.

T56-14 — REAL PDF GATE B: wygenerować rzeczywisty PDF na danych demonstracyjnych z taką liczbą faktycznie użytych oznaczeń, aby wymagany był drugi arkusz legendy. Człowiek sprawdza kompletność drugiej strony, czytelność i brak utraty oznaczeń. Zielone testy bez obu gate'ów nie zamykają T056.

## 14. FINAL PREIMPLEMENTATION RE-AUDIT

Codex ma sprawdzić wyłącznie:
- zastosowanie OWNER rulings z `tests_r4.txt` bez otwierania nowego designu;
- dwa legalne wejścia do invariantu signature, bez duplicate exporter validation;
- zachowanie zamrożonych długości oraz istniejącej edycji godzin zegarowych standardowych kodów;
- dokładnie sześć OWNER-accepted size violations i regułę baseline-vs-HEAD/no seventh violation;
- miesięczny current-state seam i brak zmiany semantyki `SitePrintSettings`;
- reużycie manual-correction i brak `operational_code`;
- unified action history przez istniejący `CONTEXT_CONFIGURATION_SAVED`;
- `Room -> ControlPanel -> PrintSettings` jako jedyny workingMonth flow;
- export: mapping, `_hours_of`, used-only legend, druga strona legendy, revision;
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
  - `rota/application/schedule_export.py`: `_map_work_code`, `_hours_of`, legend/layout owner, `_document_revision`, `generate_schedule_pdf`
  - `frontend/src/screens/Room.tsx`: `workingMonth`
  - `frontend/src/screens/ControlPanel.tsx`: prop seam Room -> PrintSettings
  - `frontend/src/screens/PrintSettings.tsx`: settings owner UI
  - `frontend/src/screens/MonthlyPlanning.tsx`: existing manual-correction editor
  - `frontend/src/api/client.ts`: print settings + manual correction API surface
- REASON: T056 dodaje miesięczny owner danych i endpointy, rozszerza istniejące mapping/sum/legend/revision, przekazuje workingMonth oraz egzekwuje jeden signature invariant na dwóch istniejących write boundaries. `where.py` jest tylko dowodem wyszukania; nie tworzy wymagań produktu.

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

Nie dodawać innych plików testowych „na wszelki wypadek”. Jeśli implementacja wymaga zmiany istniejącego testu export/manual-correction poza powyższą listą, architekt aktualizuje TASK_SCOPE **przed** zmianą tego pliku.