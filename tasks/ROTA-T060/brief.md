# ROTA-T060 — techniczne identyfikatory nie mogą trafiać do koordynatora

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / ROTA-DEVIATION-RAW-ASSIGNMENT-ID
OWNER_DECISION_2026-09-09: hash weryfikacyjny PDF z T051 pozostaje świadomym wyjątkiem i NIE jest usuwany w T060.

## 1. Cel

Usunąć z powierzchni koordynatora techniczne identyfikatory i surowe techniczne komunikaty, bez utraty informacji potrzebnej do działania produktu i bez tworzenia równoległego systemu błędów.

Problem jest systemowy, nie ekranowy: backend `api/errors.py` obecnie publikuje `str(exc)` jako `HTTPException.detail`, a wspólny frontend `client.ts` przekazuje `body.detail` bez filtra do ekranów. Równolegle istnieją jawne rendery pól technicznych w History/Decisions/Overview/Export oraz co najmniej jeden warning solvera omijający istniejący mechanizm zamiany employee_id na nazwę.

## 2. Zamrożony kontrakt OWNERA

1. Koordynator nie może zobaczyć surowego `employee_id`, `site_id`, `schedule_version_id`, `action_id`, `decision_required_id`, `source_id`, `requested_by` ani podobnego technicznego identyfikatora jako treści UI/komunikatu błędu/warningu.
2. Backend pozostaje ownerem bezpieczeństwa błędów. Frontend nie może być jedyną barierą chroniącą przed wyciekiem identyfikatora.
3. Publiczny błąd HTTP ma zachować właściwy status i użyteczną treść operacyjną, ale nie może kopiować `str(exc)` jeżeli zawiera identyfikator, repr obiektu albo wewnętrzny szczegół.
4. Nie wolno naprawić problemu przez ukrycie wszystkiego jako „Wystąpił błąd”. Komunikat ma mówić koordynatorowi co zrobić, jeśli produkt zna przyczynę.
5. Pola techniczne mogą nadal istnieć w DTO, persistence, logice backendowej, telemetryce i action trailu, jeżeli nie są renderowane koordynatorowi. T060 nie zmienia modelu danych tylko po to, aby ukryć UI.
6. W miejscach, gdzie UI potrzebuje wskazać pracownika/obiekt, używa nazwy czytelnej dla człowieka. Brak resolvowalnej nazwy nie upoważnia do fallbacku na surowe ID.
7. Warningi solvera podlegają tej samej zasadzie co błędy HTTP. Nie wolno polegać na kruchym formacie tekstowym typu „ID w cudzysłowie” jako jedynym mechanizmie sanitizacji, jeśli istnieje prostszy owner danych.
8. Wyjątek: hash weryfikacyjny PDF zamrożony w T051 pozostaje. T060 nie usuwa ani nie maskuje tego hasha i nie rozszerza wyjątku na inne identyfikatory/hash-e.
9. T060 nie zmienia semantyki planowania, solvera, lifecycle, Deviation ani zasad eksportu poza prezentacją identyfikatorów/komunikatów.

## 3. Znane powierzchnie z findingu

Do obowiązkowego sprawdzenia w WHERE_MAP, nie jako z góry zamrożony scope:
- `api/errors.py` — centralne `detail=str(exc)` oraz fallback `unexpected error: {exc}`;
- `frontend/src/api/client.ts` — bezpośrednie `body.detail` -> `Error`;
- `frontend/src/screens/Overview.tsx` — render `employee_id`;
- `frontend/src/screens/Decisions.tsx` — m.in. `requested_by`, `linked_action_ids`;
- `frontend/src/screens/History.tsx` — m.in. `source_id`, `responds_to.*`, `requested_by`, `linked_action_ids`;
- `frontend/src/screens/Export.tsx` — siteId w nazwie pliku i inne techniczne skróty, z wyłączeniem jawnie zachowanego T051 hash PDF;
- `rota/planning/solver.py` — DAY_SHIFT_OFF-01 SOFT z surowym employee_id;
- odpowiednie testy API/frontend/validator/warnings.

CC zgłosił również, że Analytics/siteId nie zostało ponownie odtworzone jako widoczny problem. Codex ma sprawdzić realny render, a nie zakładać problemu na podstawie samego użycia ID jako React key/param.

## 4. Acceptance kierunkowe

T60-01: reprezentatywne wyjątki `EmployeeNotFound`, `SiteNotFound`, `ScheduleVersionNotFound`, `InvalidCoordinatorContext`, `NoCurrentScheduleVersion`, live delete/restore i fallback 500 nie ujawniają surowych ID w `detail`.

T60-02: status HTTP i klasa błędu pozostają poprawne; nie ma globalnego zamienienia wszystkich błędów na 500/„unknown”.

T60-03: wspólny klient frontendowy nie może spowodować ponownego wycieku identyfikatora przez bezpośredni render niesanitowanego backend detail.

T60-04: History/Decisions/Overview/Export nie renderują pól technicznych jako treści dla koordynatora. Jeśli dana informacja jest potrzebna, ma czytelną reprezentację człowieka.

T60-05: DAY_SHIFT_OFF-01 SOFT i inne sprawdzone warningi nie pokazują surowego employee_id.

T60-06: brak nazwy/friendly label nie powoduje fallbacku na techniczne ID.

T60-07: hash weryfikacyjny PDF T051 pozostaje bez zmian.

T60-08: nie ma zmian semantyki solvera/lifecycle/Deviation ani nowych tabel/DTO tylko dla sanitizacji.

T60-09: targeted vertical od backend wyjątku do widocznego komunikatu w UI potwierdza brak ID; osobno targeted vertical warningu planera potwierdza czytelny pracownik/komunikat.

## 5. PREIMPLEMENTATION GATE — CODEX WHERE_MAP

IMPLEMENTATION HOLD do czasu raportu Codexa.

Codex ma:
1. zinwentaryzować wszystkie centralne writery/publiczne seamy, przez które techniczny identyfikator może dojść do koordynatora;
2. rozdzielić miejsca, które wymagają poprawki, od miejsc gdzie ID jest wyłącznie key/param i nigdy nie jest renderowane;
3. wskazać minimalny owner sanitizacji błędów HTTP — preferować centralny backend seam zamiast kilkunastu ekranowych filtrów;
4. sprawdzić, czy frontend potrzebuje drugiej fail-closed bariery i jaki ma być jej zakres, bez duplikowania pełnego słownika błędów backendu;
5. ustalić minimalny mechanizm friendly labels dla employee/site/coordinator w ekranach, wykorzystując istniejące dane zamiast nowych lookup subsystemów;
6. potwierdzić wyjątek T051 dotyczący hasha PDF i nie rozszerzać go;
7. zaproponować literalny TASK_SCOPE oraz READ_ONLY_EVIDENCE.

Nie implementować produkcyjnie przed PASS preimplementation.
