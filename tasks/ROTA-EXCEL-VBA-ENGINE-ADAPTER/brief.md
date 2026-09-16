# ROTA-EXCEL-VBA-ENGINE-ADAPTER — Excel jako interfejs, Rota jako ukryty silnik

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS AND CC MERIT PASS

BASE_MAIN_SHA: `89f5aaa84120b2e31a2fb877a43234c03064b2f5`
SOURCE: `arch/FINDING_2026-09-16_EXCEL_VBA_ENGINE_ADAPTER.md` + OWNER rulings 2026-09-16

## 1. Cel i jawne decyzje OWNERA

Docelowy użytkownik ma nadal pracować w klasycznym desktopowym Excelu. Rota działa zdalnie jako silnik na Railway i nie wymaga od użytkownika przejścia do własnego UI.

Zamrożone decyzje:

1. Excel jest głównym interfejsem użytkownika dla tego wariantu.
2. Integracja używa VBA dla klasycznego desktopowego Excela.
3. Użytkownik może z Excela uruchomić PLAN oraz REPLAN i odebrać wynik z Rota.
4. Rota działa jako usługa sieciowa; target ma dostęp do Internetu.
5. Dostęp z Excela nie wymaga interaktywnego logowania przy każdym użyciu. Administrator wydaje raz klucz dostępu, który dodatek wysyła automatycznie.
6. Core SaaS obsługuje jeden standardowy szablon grafiku oparty na referencjach z `Grafiki/`. Dopasowanie do dowolnego arkusza klienta jest osobną usługą, nie częścią tego Tasku.
7. Standardowy plik grafiku pozostaje czystym `.xlsx`. VBA jest dostarczany osobno jako jednorazowo instalowany dodatek `.xlam` lub równoważny artefakt VBA, więc zwykły plik grafiku nie zawiera makr.
8. Przy wyniku innym niż gotowy grafik użytkownik dostaje prosty polski komunikat opisujący konkretny problem i konkretne następne działanie. Nie pokazujemy mu kodów technicznych typu `DECISION_REQUIRED`, `TARGET_HOURS_REQUIRED`, nazw klas ani surowych payloadów.
9. Przy takim blockerze lub błędzie arkusz z grafikiem pozostaje niezmieniony. Dane są wpisywane do arkusza dopiero po otrzymaniu poprawnego wyniku możliwego do przedstawienia jako grafik.
10. W pilotażu chmura ma operować na stabilnych ID/pseudonimach zamiast pełnych nazwisk. Mapowanie na pełne nazwiska może pozostać lokalnie po stronie Excela i nie jest wysyłane do Rota.

## 2. Zachowanie użytkownika

### Pierwsza instalacja

Zaufany instalator instaluje dodatek VBA na komputerze użytkownika i konfiguruje w nim adres usługi Rota oraz wydany dla tego klienta klucz dostępu. Użytkownik nie przepisuje klucza przy każdym użyciu.

### PLAN

1. Użytkownik otwiera standardowy `.xlsx`.
2. Wprowadza dane wymagane przez uzgodniony szablon.
3. Uruchamia akcję `Przelicz` z dodatku.
4. Dodatek odczytuje wyłącznie pola należące do zamrożonego kontraktu szablonu i wysyła je do Rota z kluczem dostępu.
5. Rota korzysta z istniejących ownerów persistence/application/planning; Excel nie implementuje reguł planowania.
6. Jeśli wynik jest gotowy do pokazania, dodatek zapisuje grafik do standardowego układu arkusza.
7. Jeśli operacja jest zablokowana, dodatek pokazuje komunikat po polsku z problemem i działaniem użytkownika, a istniejący grafik w arkuszu pozostaje nietknięty.

Przykładowa forma komunikatu, nie literalny tekst kontraktowy: `Anna nie ma ustawionego celu godzinowego na wrzesień. Ustaw cel godzinowy i ponownie wybierz Przelicz.` zamiast `TARGET_HOURS_REQUIRED`.

### REPLAN

REPLAN jest osobną akcją dodatku korzystającą z istniejącego lifecycle Rota. Dodatek nie przelicza lokalnie różnic i nie odtwarza historii wersji. Wynik oraz blockery podlegają tym samym zasadom co PLAN.

## 3. Granica danych i pseudonimizacja pilota

Do API nie jest wymagane pełne nazwisko pracownika. Kontrakt integracji używa `employee_id` oraz opcjonalnej nazwy/pseudonimu potrzebnej do czytelności arkusza.

Mapowanie `employee_id -> pełne nazwisko` może być utrzymywane w lokalnym arkuszu lub lokalnej konfiguracji i nie jest przesyłane do Railway.

To jest minimalizacja danych dla pilota, nie deklaracja pełnej anonimizacji ani kompletnego modelu ochrony danych.

## 4. Auth — minimalny nowy szew dla klienta Excel

Obecny browser/PWA auth pozostaje bez zmian: cookie/JWT z `api/auth/backend.py` i `api/auth/context.py` nadal obsługuje React/PWA.

Dla dodatku Excel dodać odrębny, wąski credential typu API key:

- administrator generuje losowy sekret dla istniejącego konta;
- serwer zapisuje wyłącznie bezpieczny hash klucza oraz powiązanie z istniejącym account/user id;
- surowy klucz jest pokazywany tylko przy wydaniu i trafia do konfiguracji dodatku;
- request dodatku wysyła go jako `Authorization: Bearer <key>` po HTTPS;
- dependency klucza rozwiązuje ten sam `AccountMapping -> db_path + coordinator_id`, którego używa browser auth;
- caller nie może podać `db_path`, `coordinator_id` ani innej tożsamości w body/query/path;
- klucz może zostać unieważniony bez zmiany danych domenowych klienta.

Nie przerabiać istniejącego cookie auth na wspólny własny system tokenów. Nowy credential jest tylko alternatywnym wejściem do tego samego server-side `AuthenticatedContext`.

## 5. API dla dodatku — adapter, nie drugi produkt planistyczny

Dodać jeden router zewnętrznego klienta Excel pod `/external/excel`.

Minimalna powierzchnia:

- `POST /external/excel/plan`
- `POST /external/excel/replan`
- `GET /external/excel/schedule/{site_id}/{month}`

Router ma być cienkim adapterem do istniejących ownerów. Nie wolno kopiować solvera, walidatora, gate celów, DecisionRequired lifecycle, preview/version lifecycle ani logiki wyboru grafiku.

PLAN/REPLAN mają wywoływać te same application operations, których używa obecny API flow. Zewnętrzna odpowiedź może być stabilnym DTO adaptera, ale jej wartości muszą wynikać z istniejącego wyniku Rota, nie z drugiej klasyfikacji.

## 6. Wspólna projekcja grafiku

`rota/application/schedule_export.py` ma dziś prywatną, PDF-ową logikę składania grafiku do prezentacji. Nie kopiować tej dekompozycji do Excela.

Wyodrębnić najmniejszy wspólny, niezależny od formatu model/projection builder z obecnej logiki eksportu. PDF oraz adapter Excel mają korzystać z tego samego wyniku projekcji dla kodów pracy, nieobecności, DELEGACJI, godzin i kolejności wierszy.

Renderer PDF pozostaje rendererem PDF. Nowy szew nie może importować `reportlab` ani zawierać wiedzy o komórkach Excela.

## 7. Standardowy szablon `.xlsx` i dodatek VBA

Task nie tworzy uniwersalnego parsera dowolnych arkuszy.

Dostarczyć jeden standardowy szablon `.xlsx` oparty na referencyjnym układzie z `Grafiki/` oraz osobny artefakt źródłowy dodatku VBA.

Dodatek:

- udostępnia akcje `Przelicz` i `Przelicz ponownie`;
- czyta wyłącznie nazwane/stabilne obszary standardowego szablonu;
- wysyła request do API i wpisuje wynik tylko po sukcesie;
- nie przechowuje pełnych nazwisk po stronie serwera;
- nie zawiera logiki solvera ani reguł domenowych;
- w razie problemu pokazuje prosty komunikat i nie nadpisuje grafiku.

Dokładny wygląd komórek ma wynikać z osobnego pliku specyfikacji szablonu w tym Tasku, przygotowanego na podstawie `Grafiki/`, zanim implementer zacznie VBA. Nie rozszerzać go na automatyczne rozpoznawanie obcych formatów.

## 8. Kontrakt komunikatów dla człowieka

Adapter mapuje istniejące wyniki Rota na komunikaty operacyjne. Każdy komunikat musi zawierać:

1. co konkretnie blokuje operację;
2. kogo/czego dotyczy, jeśli Rota dostarcza tę informację;
3. jednoznaczne następne działanie użytkownika;
4. informację, że można ponowić `Przelicz` po wykonaniu działania, jeżeli to właściwa ścieżka odzyskania.

Zakazane jako jedyna treść dla użytkownika: surowy status, kod, UUID, traceback, nazwa wyjątku lub ogólne `Wystąpił błąd` bez instrukcji, jeżeli backend dostarcza kontrolowany blocker i recovery.

Dla nieoczekiwanego błędu technicznego komunikat nie ujawnia szczegółów technicznych; informuje, że grafik nie został zmieniony i że użytkownik ma ponowić operację albo skontaktować się z obsługą, zależnie od istniejącej klasy recovery.

## 9. Atomiczność po stronie Excela

Przed zapisaniem nowego grafiku dodatek musi mieć kompletną, poprawnie sparsowaną odpowiedź sukcesu.

Nie wolno częściowo aktualizować grafiku podczas pobierania lub parsowania odpowiedzi. Jeśli request, auth, parsing albo kontrolowany blocker zakończy operację bez poprawnego grafiku, dotychczasowa zawartość obszaru wynikowego pozostaje bez zmian.

## 10. Acceptance

- `XL-01`: użytkownik może z desktopowego Excela uruchomić PLAN bez interaktywnego logowania przy każdym użyciu.
- `XL-02`: prawidłowy klucz rozwiązuje istniejący server-side `AccountMapping`; request nie może wybrać cudzej bazy ani coordinator_id.
- `XL-03`: unieważniony/nieprawidłowy klucz nie dociera do domenowej bazy klienta.
- `XL-04`: browser/PWA cookie auth zachowuje dotychczasowe działanie bez zmiany kontraktu.
- `XL-05`: PLAN z poprawnymi danymi zwraca grafik pochodzący z istniejącego application/planning flow i zapisuje go do standardowego arkusza.
- `XL-06`: REPLAN korzysta z istniejącego lifecycle i aktualnego stanu Rota; dodatek nie buduje własnego modelu wersji.
- `XL-07`: kontrolowany blocker nie nadpisuje istniejącego grafiku i pokazuje komunikat zawierający problem + konkretne działanie użytkownika bez kodu technicznego jako głównej treści.
- `XL-08`: błąd sieci/auth/parsing nie pozostawia częściowo nadpisanego grafiku.
- `XL-09`: PDF i Excel korzystają z jednego wspólnego modelu projekcji grafiku; nie istnieją dwie niezależne implementacje dekompozycji DEL/nieobecności/kodów pracy.
- `XL-10`: standardowy artefakt grafiku jest `.xlsx` bez makr; VBA jest osobnym dodatkiem instalowanym raz.
- `XL-11`: core SaaS obsługuje jeden zamrożony szablon; obcy layout nie jest automatycznie mapowany.
- `XL-12`: request do Railway nie wymaga pełnych nazwisk; stabilne ID/pseudonimy wystarczają do przepływu pilota.

## 11. OUT_OF_SCOPE

- automatyczne dopasowanie do dowolnego pliku Excel klienta;
- Office Script / Excel Online / SharePoint jako drugi klient;
- wbudowanie makra do `.xlsx` albo zmiana standardowego artefaktu na `.xlsm`;
- solver lub walidacja zaimplementowane w VBA;
- pełna dwukierunkowa synchronizacja wszystkich danych Rota i Excela;
- interaktywne browser login w dodatku;
- zmiana istniejącego cookie/JWT auth dla PWA;
- nowy solver/stateless planning engine;
- pełna anonimizacja/GDPR design;
- billing/licencjonowanie;
- automatyczne customizowanie layoutu per klient;
- zmiana reguł domenowych PLAN/REPLAN.

## 12. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/**`
- `api/auth/api_key.py` (nowy)
- `api/auth/models.py`
- `api/auth/db.py`
- `api/provision_account.py`
- `api/routers/excel_external.py` (nowy)
- `api/main.py`
- `rota/application/schedule_projection.py` (nowy)
- `rota/application/schedule_export.py`
- `excel/elnath_rota_addin.bas` (nowy)
- `excel/ELNATH_ROTA_TEMPLATE.xlsx` (nowy artefakt binarny, bez VBA)
- `excel/TEMPLATE_CONTRACT.md` (nowy)
- `tests/test_excel_api_key_auth.py` (nowy)
- `tests/test_excel_external_api.py` (nowy)
- `tests/test_schedule_projection.py` (nowy)
- `tests/test_t020_export.py`
- `tests/test_t024_tester_login_isolation.py`

Każdy inny plik produkcyjny wymaga STOP i korekty briefu.

## 13. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `api/auth/context.py --symbol get_authenticated_context`
- TARGETS: `api/deps.py --symbol get_conn`
- TARGETS: `api/deps.py --symbol get_coordinator_id`
- TARGETS: `api/routers/schedule.py --symbol _planning_result_out`
- TARGETS: `rota/application/plan_ops.py --symbol plan_month`
- TARGETS: `rota/application/plan_ops.py --symbol replan`
- TARGETS: `rota/application/schedule_export.py --symbol _assemble_export_model`
- TARGETS: `api/main.py`
- REASON: Task dodaje alternatywny auth client, nowy router PLAN/REPLAN i wydziela wspólny owner projekcji grafiku; przed implementacją trzeba potwierdzić istniejące szwy i uniknąć duplikacji.

`where.py` jest dowodem wyszukiwania, nie podstawą zmiany scope. Każdy znaleziony mismatch ownera/szwu należy wrócić do Architekta przed implementacją.

## 14. Weryfikacja

Minimalna macierz:

1. API-key: valid / invalid / revoked / izolacja tenantów;
2. brak regresji browser cookie auth;
3. external PLAN sukces + blocker;
4. external REPLAN sukces + blocker;
5. wspólna projection: reprezentatywny OCHRONA, ORDINARY, DEL i nieobecność;
6. VBA: success zapisuje komplet, blocker/network/auth nie zmienia starego grafiku;
7. artefakt `.xlsx` nie zawiera VBA, a dodatek jest osobny.

Nie uruchamiać pełnej regresji bez osobnej zgody OWNERA. Implementacja rusza dopiero po `PASS PREIMPLEMENTATION` Codexa i osobnym PASS merytorycznym CC.