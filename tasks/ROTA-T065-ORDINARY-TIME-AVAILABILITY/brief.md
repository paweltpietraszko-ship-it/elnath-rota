# ROTA-T065-ORDINARY-TIME-AVAILABILITY — rzeczywista dostępność godzinowa ORDINARY

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

SOURCE:
- `ROTA-T065-PANEL-CLEANUP` finding A
- audit R1 `tasks/ROTA-T065-ORDINARY-TIME-AVAILABILITY/round_01/tests/tests_r1.txt`
- OWNER ruling `main@4f59a4e` / `tests_r2.txt`
- BOARD finding `ROTA-T065-DECISION-GUIDANCE-GAP`
- OWNER real case: pracownik przez wskazany tydzień jest niedostępny na ranne godziny, np. przed 12:00
- istniejący append-only `AvailabilityRecord`, eligibility, validator, EmployeeDetail/matrix

## 1. Cel

Dla `SitePlanningRegime.ORDINARY` dodać datowane ograniczenie rzeczywistej dostępności godzinowej pracownika bez D/N, bez wiązania go z konkretnym wierszem katalogu i bez drugiego silnika dostępności.

Przykład biznesowy:

`2026-09-14..2026-09-20, niedostępny 00:00–12:00`.

W takim okresie:
- praca `05:00–12:00` jest niedozwolona automatycznie;
- `10:00–18:00` jest niedozwolona automatycznie;
- `12:00–19:00` jest dozwolona;
- ręcznie dodana realna praca również musi przejść ten sam test.

## 2. Jeden owner danych — istniejący AvailabilityRecord

Nie powstaje `OrdinaryAvailability`, drugi repository ani SiteRule udający dostępność godzinową.

Istniejący `AvailabilityRecord`/`availability_repository.py` pozostaje append-only ownerem historii dostępności. Dochodzi jeden rodzaj:

`UNAVAILABLE_TIME_WINDOW`.

Dla tego rodzaju rekord przechowuje dodatkowo:
- `start_time`;
- `end_time`.

Dla istniejących rodzajów całodniowych (`UNAVAILABLE_24H`, `SICK_LEAVE`, `LEAVE_GRANTED`, itd.) oba pola pozostają `None` i dotychczasowa semantyka się nie zmienia.

Nie zmieniać istniejącego linear-chain versioningu `availability_id`.

## 3. Zakres V1 — tylko okno dzienne

OWNER zamroził V1:
- okno godzinowe powtarza się każdego dnia w inclusive zakresie `start_date..end_date`;
- musi mieścić się w jednej dobie;
- wymagane `start_time < end_time`;
- okna przez północ są OUT OF SCOPE.

Przykład legalny: `00:00–12:00`.

Przykład odrzucony na write boundary: `20:00–06:00`.

UI i backend mają odrzucać overnight jawnie. Nie wolno interpretować go jako dwóch okien ani zgadywać daty końca.

## 4. Półotwarta semantyka przedziału — jeden oracle

Okno niedostępności jest półotwarte `[window_start, window_end)`.

Praca koliduje, gdy jej realny `[Assignment/ShiftDemand.start_datetime, end_datetime)` ma niepuste przecięcie z dowolnym dziennym wystąpieniem aktywnego `UNAVAILABLE_TIME_WINDOW` w zakresie dat.

Dlatego dla `00:00–12:00`:
- `10:00–18:00` koliduje;
- `12:00–19:00` nie koliduje.

Powstaje jeden czysty oracle w `rota/planning/availability.py` używany przez:
- automatic eligibility;
- validator/manual correction.

Nie wolno kopiować obliczenia overlap do dwóch modułów.

Istniejąca semantyka całodniowych AvailabilityKinds zostaje zachowana; helper może ją wywoływać/współdzielić, ale ten Task nie refaktoryzuje całego systemu absencji.

## 5. ORDINARY — brak ochroniarskich kwalifikacji D/N/24h

Dla `ORDINARY` o możliwości pracy decydują rzeczywiste godziny i ogólne gate'y, a nie ochrona D/N.

KRYTYCZNE:

`SiteMembership.can_work_24h` **NIGDY nie uczestniczy w eligibility ORDINARY**, nawet jeśli techniczny `catalog_kind == H24` albo obiekt działa 24/7.

Warunek `SHIFT-24-01` pozostaje wyłącznie semantyką OCHRONA. W ORDINARY nie jest emitowany, więc `decision_guidance.py` nie może również oferować ochroniarskiej akcji `Zmień 24` dla tego reżimu.

Analogicznie `day_only` i D/N-specific SiteRules nie mogą blokować ORDINARY tylko dlatego, że techniczny katalog ma D/N lub zmianę nocną. Istniejące poprawki T065 `dn_semantics_apply()` pozostają jednym właścicielem tej granicy.

## 6. Co zachowujemy w UI pracownika

Dla ORDINARY ukrywamy/wyłączamy jako nieadekwatne:
- Dniówka/Nocka jako kwalifikacje;
- `day_only` jako kontrolkę biznesową ORDINARY;
- `can_work_24h` jako kwalifikację ORDINARY.

NIE usuwamy ogólnych mechanizmów dostępności:
- całodniowa niedostępność;
- L4;
- urlop;
- ogólne ograniczenia dni tygodnia, jeśli istnieją jako niezależna semantyka kalendarzowa;
- nowe datowane okno godzinowe.

`availability_matrix.py` pozostaje read-ownerem skomponowanego widoku ograniczeń pracownika. Ma zostać rozszerzony o aktywne `UNAVAILABLE_TIME_WINDOW`, zamiast tworzenia drugiego read modelu tylko dla ORDINARY.

`api/routers/roster.py` serializuje nowe `start_time/end_time` w istniejącym EmployeeDetail. Writes pozostają w istniejącym `api/routers/durable_inputs.py` / `rota/application/durable_inputs.py`.

## 7. Automatic eligibility

Dla każdego demandu ORDINARY istniejący `check_eligibility()` korzysta ze wspólnego oracle i blokuje kandydata kodem `UNAVAILABLE_TIME-01`, jeżeli demand nachodzi na aktywne okno godzinowe.

LOCAL i EXTERNAL_SUPPORT przechodzą dokładnie ten sam gate. External nie dostaje wyjątku.

Nie dodawać drugiego passu solvera ani fallbacku.

## 8. Coordinator guidance — istniejący owner

`rota/planning/decision_guidance.py` pozostaje jedyną warstwą tłumaczącą raw blocker na komunikat koordynatora.

Dla `UNAVAILABLE_TIME-01` dodaje dedykowaną, nie-ochroniarską prezentację:
- condition text: `Koliduje z dostępnością godzinową`;
- action: `Zmień dostępność godzinową: {names}` z `target="obsada"`.

Guidance nie przelicza overlapu i nie tworzy nowej decyzji — tylko prezentuje blocker już policzony przez eligibility/engine.

`SHIFT-24-01` nie potrzebuje ORDINARY wariantu tekstu, ponieważ po poprawnym regime gate w ogóle nie jest blockerem ORDINARY. Ochroniarski tekst `Zmień 24` pozostaje dla OCHRONA bez zmian.

## 9. Manual correction

Manual correction nie dostaje drugiej logiki dostępności.

Istniejący validator korzysta z tego samego oracle i materializuje naruszenie `UNAVAILABLE_TIME-01` zgodnie z istniejącym mechanizmem HARD/deviation/manual override.

Ten Task nie zmienia ogólnej zasady produktu, że świadoma Manual Correction może zapisać odchylenie tam, gdzie istniejący lifecycle to dopuszcza. Wymagane jest natomiast, aby kolizja została wykryta i nigdy nie przeszła jako „brak naruszenia”.

`ROTA-T065-MANUAL-MIDDLE-SHIFT` ma twardą zależność od tego gate'u.

## 10. Persistence / API validation

Write boundary dla `UNAVAILABLE_TIME_WINDOW` wymaga:
- `start_date <= end_date`;
- oba `start_time/end_time` obecne;
- `start_time < end_time`;
- pełne godziny zgodnie z obecną precyzją produktu, chyba że istniejący wspólny kontrakt Availability już dopuszcza dokładniejszą precyzję; implementer nie rozszerza jej sam;
- kind inny niż `UNAVAILABLE_TIME_WINDOW` nie może przypadkiem odziedziczyć semantyki godzinowej.

Błąd overnight/shape ma być odrzucony przed PLAN, nie dopiero przez solver.

## 11. Acceptance

TA-01 — zapis/odczyt append-only `UNAVAILABLE_TIME_WINDOW` zachowuje daty i godziny po restarcie.

TA-02 — `00:00–12:00` blokuje ORDINARY `05:00–12:00` i `10:00–18:00`.

TA-03 — `00:00–12:00` NIE blokuje pracy zaczynającej się dokładnie o `12:00`.

TA-04 — write/API odrzuca `20:00–06:00` jako unsupported overnight window.

TA-05 — `can_work_24h=False` nie blokuje żadnego demandu ORDINARY wyłącznie z powodu `catalog_kind=H24`; OCHRONA zachowuje `SHIFT-24-01`.

TA-06 — DECISION_REQUIRED dla `UNAVAILABLE_TIME-01` pokazuje `Koliduje z dostępnością godzinową` i akcję `Zmień dostępność godzinową`, nigdy `Zmień 24`/`Nocka`.

TA-07 — LOCAL i EXTERNAL_SUPPORT mają identyczny hourly-availability gate.

TA-08 — manual validator wykrywa ten sam overlap tym samym oraclem; nie istnieje drugi algorytm.

TA-09 — EmployeeDetail ORDINARY nadal pokazuje całodniową niedostępność/L4/urlop i nowe okna godzinowe; ukrycie D/N/24h nie usuwa ogólnych kontrolek dostępności.

TA-10 — późniejsza edycja katalogu zmian nie zmienia znaczenia zapisanego okna; jest ono oceniane na realnym przedziale pracy.

TA-11 — OCHRONA regression unchanged, w tym dotychczasowy guidance `SHIFT-24-01`.

## 12. WHERE_MAP

WHERE_MAP: REQUIRED
- `rota/domain.py` :: `AvailabilityKind`, `AvailabilityRecord.start_time/end_time` — minimalne rozszerzenie istniejącej domeny.
- `rota/persistence/availability_repository.py` :: append/read current/history z nowymi polami; jeden owner danych.
- `rota/persistence/db.py` :: migracja `availability_versions`; nie istnieje `schema.py`.
- `rota/planning/availability.py` :: NOWY pojedynczy pure interval-overlap oracle dla hourly window.
- `rota/planning/eligibility.py` :: użycie oracle + jawny regime guard wyłączający `can_work_24h` dla ORDINARY.
- `rota/planning/validator.py` :: użycie tego samego oracle, bez kopii obliczeń.
- `rota/planning/decision_guidance.py` :: prezentacja `UNAVAILABLE_TIME-01`; żadnego ORDINARY `Zmień 24`.
- `rota/application/availability_matrix.py` :: dołączenie hourly windows do istniejącego read modelu, zachowanie full-day/general weekday facts.
- `rota/application/durable_inputs.py` :: istniejący audytowalny write path Availability.
- `api/routers/roster.py` :: EmployeeDetail read/serialization `start_time/end_time`.
- `api/routers/durable_inputs.py` :: create/update validation godzinowego AvailabilityRecord.
- `frontend/src/screens/EmployeeDetail.tsx` :: regime-aware UI; hourly window + zachowane ogólne ograniczenia.
- `frontend/src/api/client.ts` :: pola API.

## 13. TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T065-ORDINARY-TIME-AVAILABILITY/**
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/availability_repository.py
- rota/planning/availability.py
- rota/planning/eligibility.py
- rota/planning/validator.py
- rota/planning/decision_guidance.py
- rota/application/availability_matrix.py
- rota/application/durable_inputs.py
- api/routers/roster.py
- api/routers/durable_inputs.py
- frontend/src/screens/EmployeeDetail.tsx
- frontend/src/api/client.ts
- tests/test_t065_ordinary_time_availability.py
- tests/test_eligibility_matrix.py
- tests/test_t021b_employee_matrix_wrappers.py
- tests/test_t065_ordinary_roles.py

## 14. HOLD

IMPLEMENTATION HOLD do preimplementation PASS Codexa na dokładnym SHA tego briefu.

Codex ma w wąskim re-checku sprawdzić przede wszystkim: jeden Availability owner, jeden overlap oracle, explicit overnight rejection, bezwarunkowe wyłączenie `can_work_24h` w ORDINARY, poprawny coordinator guidance oraz brak regresji ogólnych kontrolek dostępności.