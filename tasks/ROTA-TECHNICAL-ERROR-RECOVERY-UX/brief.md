# ROTA-TECHNICAL-ERROR-RECOVERY-UX — trwały log awarii + prosty recovery UX

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE FINDINGS:
- `ROTA-NO-PERSISTENT-ERROR-LOG`
- `ROTA-TECHNICAL-ERROR-RECOVERY-UX`
- Codex readiness check `d3b2ba366f714cfc92d2fcd9972f6201b1546289`
- Codex precheck R1 `2b590e99aaf338a07d8f13b16961d659bfa027f8`

OWNER DECISIONS 2026-09-12:
- oba findingi są jednym Taskiem;
- `TECHNICAL_ERROR`, HTTP error, timeout, utrata/zawieszenie backendu lub inna awaria wykonania to problem techniczny, nie blocker biznesowy i nie podstawa do Korekty ręcznej;
- restart oznacza zwykłe wyłączenie i ponowne uruchomienie aplikacji;
- realnego kanału supportowego jeszcze nie ma; UI ma wyłącznie nieaktywną/wyszarzoną makietę przycisku kontaktu ze wsparciem.

## 1. Cel

Po awarii koordynator ma zobaczyć prostą informację co zrobić, a CC ma po fakcie otrzymać wystarczający techniczny ślad diagnostyczny bez proszenia OWNERA o odtwarzanie błędu ze screena.

To nie jest system telemetryczny, activity log, SIEM ani drugi subsystem diagnostyczny.

## 2. Reuse istniejących ownerów

Obowiązkowo wykorzystać istniejące mechanizmy zamiast tworzyć równoległe:

1. T021c — istniejący ograniczony bufor frontendu w `sessionStorage`, globalne handlery/ErrorBoundary i istniejący ZIP diagnostyczny. Nowy runtime log ma zostać dołączony do istniejącego pakietu diagnostycznego; nie tworzyć drugiego eksportera diagnostyki.
2. T060 — `api/errors.py` + wspólny `frontend/src/api/client.ts` pozostają jedyną publiczną ścieżką błędów HTTP. Nie tworzyć drugiego słownika/mappera błędów.
3. `MonthlyPlanning.tsx` nie może już renderować surowego `PlanningResult.error_message` dla `TECHNICAL_ERROR`.
4. Dla ustrukturyzowanych wyników planowania wspólnym ownerem rejestracji technicznej jest `api/routers/schedule.py::_planning_result_out` albo jeden równoważny, jawnie nazwany helper używany przez wszystkie istniejące ścieżki PLAN/REPLAN/wider-search/retry. Nie logować osobno w solverze, `plan_ops` ani poszczególnych handlerach.

## 3. Jeden trwały runtime error log

Backend zapisuje jeden sanitizowany log technicznych awarii aplikacji.

Minimalna zawartość jednego wpisu dla wyjątku:
- timestamp UTC;
- severity (`ERROR` lub `CRITICAL`; `WARNING` tylko jeśli istniejący kod już klasyfikuje zdarzenie jako techniczne ostrzeżenie);
- stabilna nazwa komponentu/operacji, np. `PLAN`, `REPLAN`, `EXPORT`, `API`;
- typ wyjątku;
- bezpieczny komunikat techniczny;
- stack trace dla nieobsłużonego wyjątku lub miejsca, w którym istniejący backend już posiada exception context;
- krótki losowy/techniczny `incident_id`, który może pojawić się wyłącznie w diagnostyce/logu, nie musi być pokazywany koordynatorowi.

Dla `PlanningResult(status="TECHNICAL_ERROR")` nie ma obowiązku istnienia exception context. Taki wynik także musi dać jeden wpis runtime logu w wspólnym boundary planowania. W tym wpisie:
- operation = odpowiednia istniejąca operacja (`PLAN` lub `REPLAN`; wider-search/retry zachowują swoją rzeczywistą operację, ale nie tworzą osobnych loggerów);
- zamiast typu wyjątku użyć stałej kategorii `STRUCTURED_PLANNING_FAILURE`;
- nie kopiować surowego `PlanningResult.error_message` do logu;
- brak stack trace jest poprawny, jeśli nie istnieje exception context;
- nie zmieniać solvera ani DTO `PlanningResult` tylko po to, żeby zbudować log.

Nie logować:
- nazwisk i innych display_name;
- treści formularzy;
- request/response body;
- danych nieobecności i notatek;
- payloadów decyzji;
- sekretów, tokenów, kluczy, nagłówków autoryzacji;
- pełnych obiektów domenowych;
- pełnego activity trail użytkownika.

Nie budować automatycznego redaction engine. Wpisy mają być konstruowane z jawnie dozwolonych pól.

## 4. Miejsce zapisu, rotacja i retencja

Jeden mechanizm plikowy dla obu modeli wdrożenia.

### LOCAL_WINDOWS

Domyślny katalog: istniejący katalog danych aplikacji / diagnostyki, w podkatalogu `logs/`.

Plik bieżący: `runtime-errors.log`.

### CENTRAL_SERVICE

Ten sam logger zapisuje do katalogu wskazanego konfiguracją deploymentu (`ROTA_LOG_DIR`). Centralne wdrożenie ma zapewnić trwały/montowany katalog; brak takiego katalogu nie może być cicho zastępowany innym nieznanym miejscem.

Nie wybieramy teraz zewnętrznego SaaS/KMS/SIEM/log collector.

### Rotacja

Najprostszy bounded rolling file:
- maks. 1 MiB na plik;
- plik bieżący + 4 kopie rotacyjne;
- starsze są automatycznie usuwane.

To jest retencja ograniczona rozmiarem, nie archiwum historyczne.

## 5. Dostęp diagnostyczny

Istniejący ZIP diagnostyczny ma dołączać dostępne `runtime-errors.log*`.

CC/wsparcie nie potrzebuje nowego endpointu ani ekranu do czytania logu. Na dziś ścieżka wsparcia technicznego to przekazanie istniejącego pakietu diagnostycznego.

Jeżeli logu nie ma, ZIP nadal powstaje poprawnie.

## 6. UX awarii technicznej

Dla `TECHNICAL_ERROR`, błędu HTTP, timeoutu, utraty/zawieszenia backendu lub nieoczekiwanej awarii wykonania użytkownik nie może zobaczyć:
- stack trace;
- surowego exception string;
- kodu HTTP;
- technicznego identyfikatora;
- surowego `PlanningResult.error_message`;
- sugestii Korekty ręcznej;
- komunikatu sugerującego blocker biznesowy.

Minimalny komunikat koordynatora:

`Wystąpiła awaria techniczna. Wyłącz aplikację i uruchom ją ponownie.`

Jeżeli po ponownym uruchomieniu problem się powtarza, ekran może wskazać pobranie istniejącego pakietu diagnostycznego.

Na ekranie może istnieć przycisk:

`Kontakt ze wsparciem`

ale w tym Tasku jest on jawnie `disabled`/wyszarzony i nie wykonuje żadnej akcji. Nie tworzyć mailto, formularza, endpointu ani konfiguracji supportu.

## 7. Restart

`Restart programu` oznacza dokładnie to, co zamroził OWNER: wyłączenie aplikacji i ponowne jej uruchomienie.

- LOCAL_WINDOWS: zamknięcie aplikacji desktopowej i jej ponowne uruchomienie.
- CENTRAL_SERVICE: komunikat koordynatora nie próbuje sterować procesem serwera; użytkownik zamyka/uruchamia ponownie klienta. Jeżeli backend nadal jest niedostępny, pozostaje ten sam stan awarii i możliwość pobrania diagnostyki, gdy backend jest dostępny.

Nie implementować przycisku automatycznego restartu procesu/backendu.

## 8. Granica błędów biznesowych

Ten Task nie zmienia zachowania:
- `DECISION_REQUIRED`;
- `SEARCH_INCOMPLETE`;
- walidacji LAW/non-LAW;
- zwykłych błędów danych wejściowych, dla których istnieje już ludzki komunikat;
- błędów domenowych, które mają zdefiniowane działanie użytkownika.

Nie wolno mapować wszystkiego do „awaria techniczna”. T060 pozostaje ownerem publicznej klasyfikacji HTTP.

## 9. Acceptance

A1. Nieobsłużony wyjątek backendu zapisuje sanitizowany wpis do `runtime-errors.log` i użytkownik widzi prosty komunikat awarii technicznej.

A2. Każdy `PlanningResult(status="TECHNICAL_ERROR")` wychodzący przez wspólny boundary PLAN/REPLAN/wider-search/retry zapisuje dokładnie jeden sanitizowany wpis runtime logu, także bez exception context. Wpis używa kategorii `STRUCTURED_PLANNING_FAILURE` i nie zawiera surowego `PlanningResult.error_message`.

A3. `TECHNICAL_ERROR` z PLAN/REPLAN nie pokazuje surowego `PlanningResult.error_message`.

A4. HTTP 5xx / utrata backendu / timeout w kliencie używają tej samej powierzchni komunikatu, bez drugiego mappera.

A5. Żaden z A1–A4 nie proponuje Korekty ręcznej.

A6. Runtime log nie zawiera nazwiska ani treści request/response body w fixture zawierającym takie dane.

A7. Rotacja utrzymuje maksymalnie plik bieżący + 4 kopie po przekroczeniu 1 MiB.

A8. Istniejący ZIP diagnostyczny zawiera runtime logi, jeżeli istnieją, i nadal działa bez nich.

A9. LOCAL_WINDOWS działa bez dodatkowej konfiguracji ścieżki logu.

A10. CENTRAL_SERVICE używa `ROTA_LOG_DIR`; brak wymaganej trwałej lokalizacji jest jawnym błędem konfiguracji loggera/deploymentu, nie silent fallbackiem.

A11. Przycisk `Kontakt ze wsparciem` jest widoczny jako nieaktywny i nie wykonuje akcji.

A12. Restart oznacza wyłącznie instrukcję wyłącz/uruchom ponownie; brak automatycznego restartu backendu.

A13. `DECISION_REQUIRED`, `SEARCH_INCOMPLETE` i istniejące ludzkie błędy domenowe nie są regresyjnie zamieniane w komunikat awarii technicznej.

A14. Nie powstaje drugi ZIP diagnostyczny, drugi ErrorBoundary, drugi HTTP error mapper ani activity log.

A15. Wszystkie istniejące ścieżki PLAN/REPLAN/wider-search/retry korzystają z jednego boundary logującego structured `TECHNICAL_ERROR`; brak loggerów rozsianych po solverze, `plan_ops` i handlerach.

## 10. Literalny TASK_SCOPE

Production — oczekiwany minimalny zakres po prechecku:
- backendowy moduł/config loggera runtime w `api/` lub istniejącym wspólnym miejscu wskazanym przez where-map;
- centralne miejsce obsługi nieobsłużonych wyjątków FastAPI / istniejący `api/errors.py` tylko jeśli potrzebne do rejestracji bez zmiany jego publicznego kontraktu T060;
- `api/routers/schedule.py::_planning_result_out` albo jeden równoważny, jawnie nazwany helper używany przez wszystkie obecne ścieżki PLAN/REPLAN/wider-search/retry — wyłącznie do pojedynczego sanitizowanego wpisu dla `status == "TECHNICAL_ERROR"`, bez zmiany solvera lub DTO;
- istniejący generator pakietu diagnostycznego T021c — wyłącznie dołączenie `runtime-errors.log*`;
- `frontend/src/api/client.ts` — reuse istniejącej klasyfikacji/network failure;
- istniejący ErrorBoundary/global handlers T021c — wyłącznie reuse/ujednolicenie komunikatu, bez drugiego mechanizmu;
- `frontend/src/screens/MonthlyPlanning.tsx` — usunięcie surowego `TECHNICAL_ERROR.error_message` i użycie wspólnej powierzchni awarii;
- najbliższy istniejący komponent powierzchni błędu — dodanie instrukcji restartu, linku/przycisku istniejącej diagnostyki jeśli już dostępny oraz wyszarzonej makiety `Kontakt ze wsparciem`.

Tests:
- wąskie backend tests dla logowania, sanitizacji, rotacji i ZIP;
- wąski test wszystkich obecnych ścieżek PLAN/REPLAN/wider-search/retry przez wspólny `_planning_result_out`/równoważny helper: każdy structured `TECHNICAL_ERROR` daje dokładnie jeden sanitizowany wpis, bez raw `error_message`;
- wąskie frontend/API tests dla komunikatu technicznego i braku raw details;
- jeden E2E lub pion integracyjny: realna awaria -> komunikat -> runtime log -> pakiet diagnostyczny;
- bez symulatorów i benchmarków.

Jawnie poza scope:
- zewnętrzny monitoring/telemetria/APM;
- Sentry/Datadog/ELK/SIEM;
- serwer lub konto supportu;
- wysyłanie diagnostyki przez internet;
- automatyczny upload logów;
- automatyczny restart backendu;
- activity/audit log użytkownika;
- logowanie payloadów biznesowych;
- redesign T060/T021c;
- zmiana logiki planowania, solvera, lifecycle, DTO `PlanningResult` lub decyzji.

## 11. Preimplementation re-check Codexa

Ponowić wyłącznie literalny re-check fragmentów skorygowanych po R1:
1. czy `api/routers/schedule.py::_planning_result_out` (lub wskazany jeden równoważny helper) rzeczywiście obejmuje wszystkie obecne ścieżki PLAN/REPLAN/wider-search/retry zwracające `PlanningResult`;
2. czy `status == "TECHNICAL_ERROR"` może w tym jednym miejscu zapisać dokładnie jeden sanitizowany wpis `STRUCTURED_PLANNING_FAILURE` bez exception context, bez raw `error_message` i bez zmian solvera/DTO;
3. czy literalny TASK_SCOPE i acceptance są po tej korekcie kompletne.

Jeżeli 1–3 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: jedna konkretna luka ownera/ścieżki; bez ponawiania inventory T021c/T060 i bez proponowania zewnętrznego systemu logowania.
