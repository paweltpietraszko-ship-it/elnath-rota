# ROTA-T065-ORDINARY-TIME-AVAILABILITY — datowana dostępność godzinowa ORDINARY

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

DEPENDENCY:
- semantycznie zależy od `ROTA-T065-CONFIGURABLE-ROLES` tylko w zakresie zwykłego eligibility; nie tworzy własnego modelu ról.

SOURCE:
- finding Codexa `ROTA-T065-PANEL-CLEANUP` część A
- OWNER example: pracownik może zgłosić, że w konkretnym tygodniu z powodu opieki nad dzieckiem jest niedostępny na ranne godziny
- OWNER correction: ograniczenie ma dotyczyć rzeczywistych godzin pracy, nie symbolu D/N ani wiersza katalogu
- istniejący append-only `AvailabilityRecord` + eligibility + validator/manual correction

## 1. Cel

Dla ORDINARY dodać czasowe ograniczenie dostępności godzinowej pracownika bez budowania drugiego systemu dostępności.

Przykład biznesowy:
- obowiązuje 14–20.09;
- pracownik niedostępny każdego dnia w tym zakresie od 00:00 do 12:00;
- praca 05:00–12:00 odpada;
- praca 10:00–18:00 odpada;
- praca 12:00–19:00 jest dozwolona.

Solver ma oceniać realny `start_datetime/end_datetime` pracy, a nie `ShiftKind`, numer zmiany ani nazwę katalogową.

## 2. Reuse istniejącego ownera Availability

Nie tworzyć drugiej tabeli/serwisu `StoreAvailability`.

Rozszerzyć istniejący append-only lifecycle `AvailabilityRecord` o jeden jawny wariant godzinowej niedostępności dla ORDINARY.

Minimalna semantyka:
- `start_date` i `end_date` — jak dziś, zakres dat włącznie;
- dzienne `start_time` i `end_time` określające okres niedostępności w każdym objętym dniu;
- aktywność, supersedes i note pozostają w obecnym chain lifecycle.

Jeżeli przedział czasu przechodzi przez północ, reprezentacja ma być jednoznaczna i testowana; nie wyprowadzać znaczenia z nazwy zmiany.

Istniejące całodniowe rodzaje (`UNAVAILABLE_24H`, urlopy, L4 itd.) pozostają bez zmiany.

## 3. Jeden oracle nakładania przedziałów

Ma istnieć jeden współdzielony test:

`czy rzeczywisty interval pracy nachodzi na aktywne godzinowe okno niedostępności?`

Ten sam oracle ma być używany przez:
- solver eligibility;
- validator ręcznej korekty;
- każdą inną istniejącą ścieżkę, która waliduje realną Assignment.

Nie wolno mieć osobnej logiki dla PLAN i osobnej dla Manual Correction.

## 4. HARD i odchylenia

Automatyczny solver traktuje aktywną godzinową niedostępność jako HARD — tak jak inne blokujące availability.

Ręczna korekta zachowuje istniejącą zasadę produktu:
- validator zgłasza naruszenie;
- koordynator może użyć istniejącego mechanizmu świadomego odchylenia tam, gdzie produkt już to dopuszcza;
- istniejący deviation/action trail zapisuje decyzję.

Nie tworzyć nowego override ani osobnego audytu.

## 5. ORDINARY vs OCHRONA

Nowa godzinowa dostępność służy ORDINARY i zastępuje potrzebę używania ochroniarskich pojęć `day_only`, D/N lub `can_work_24h` jako protezy dostępności godzinowej.

Dla ORDINARY:
- `can_work_24h` nie może blokować zwykłego eligibility tylko dlatego, że katalog ma nietypowy przedział;
- D/N-specific ograniczenia nie opisują dostępności godzinowej.

OCHRONA pozostaje bez zmian.

Nie kasować ani nie reinterpretować istniejących ochroniarskich danych.

## 6. UI

W EmployeeDetail/konfiguracji pracownika ORDINARY nie pokazywać ochroniarskiej macierzy jako sposobu ustawiania godzinowej dostępności.

Dodać prostą akcję typu `Dodaj niedostępność godzinową` z polami:
- od dnia;
- do dnia;
- od godziny;
- do godziny;
- opcjonalna notatka.

UI ma pokazywać zapisane ograniczenia i pozwalać je zakończyć/zmienić przez istniejący version-chain lifecycle, nie przez mutowanie historii.

## 7. Brak powiązania z katalogiem zmian

Godzinowa niedostępność należy do pracownika i czasu, nie do konkretnego `StandardShift`.

Po późniejszej edycji katalogu nadal obowiązuje wobec każdego realnego intervala, który na nią nachodzi.

Nie tworzyć checkboxów `1 zmiana / 2 zmiana / 3 zmiana` jako źródła eligibility.

## 8. External support

LOCAL i EXTERNAL_SUPPORT podlegają tej samej godzinowej dostępności, jeżeli rekord dotyczy danego pracownika.

Nie tworzyć osobnej wersji tego mechanizmu dla external.

## 9. Acceptance — minimum

1. Datowane okno 14–20.09, 00:00–12:00 blokuje demand 05:00–12:00 i 10:00–18:00, ale nie 12:00–19:00.
2. To samo ograniczenie blokuje ręcznie dodaną realną pracę nachodzącą na interval.
3. Edycja katalogu zmian nie zmienia znaczenia istniejącej niedostępności.
4. Całodniowe L4/urlop/UNAVAILABLE zachowują obecną semantykę.
5. Manual correction korzysta z tego samego oracla i istniejącego deviation lifecycle.
6. OCHRONA regression unchanged.
7. External nie omija ograniczenia.

TASK_SCOPE:
- rota/domain.py
- rota/persistence/availability_repository.py
- rota/persistence/schema.py
- rota/planning/eligibility.py
- rota/planning/validator.py
- rota/application/assembler.py
- rota/application/durable_inputs.py
- api/routers/durable_inputs.py
- frontend/src/screens/EmployeeDetail.tsx
- frontend/src/api/client.ts
- tests/

## 10. HOLD

IMPLEMENTATION HOLD do preimplementation PASS Codexa na dokładnym SHA tego briefu.
