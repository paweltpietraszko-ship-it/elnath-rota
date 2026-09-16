# ROTA-EXCEL-VBA-ENGINE-ADAPTER — Excel jako interfejs, Rota jako ukryty silnik

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS AND CC MERIT PASS

BASE_MAIN_SHA: `89f5aaa84120b2e31a2fb877a43234c03064b2f5`
SOURCE: `arch/FINDING_2026-09-16_EXCEL_VBA_ENGINE_ADAPTER.md` + OWNER rulings 2026-09-16 + Codex prechecks `round_01/tests/tests_r2.txt` and `tests_r3.txt`

## 1. Cel i jawne decyzje OWNERA

Docelowy użytkownik ma nadal pracować w klasycznym desktopowym Excelu. Rota działa zdalnie jako silnik na Railway i nie wymaga od użytkownika przejścia do własnego UI.

Zamrożone decyzje:

1. Excel jest głównym interfejsem użytkownika dla tego wariantu.
2. Integracja używa VBA dla klasycznego desktopowego Excela.
3. Użytkownik może z Excela uruchomić planowanie i szukanie innego wariantu przed pierwszą akceptacją.
4. Rota działa jako usługa sieciowa; target ma dostęp do Internetu.
5. Dostęp z Excela nie wymaga interaktywnego logowania przy każdym użyciu. Administrator wydaje raz klucz dostępu, który dodatek wysyła automatycznie.
6. Core SaaS obsługuje jeden standardowy szablon oparty na referencji `Grafiki/Zrzut ekranu (630).png` i pozostałych materiałach pomocniczych z `Grafiki/`. Dopasowanie do dowolnego arkusza klienta jest osobną usługą.
7. Standardowy plik grafiku pozostaje czystym `.xlsx`. VBA jest dostarczany osobno jako jednorazowo instalowany dodatek `.xlam`.
8. Przy wyniku innym niż gotowy grafik użytkownik dostaje prosty komunikat operacyjny: co jest nie tak, czego/kogo dotyczy i co konkretnie ma zrobić dalej. Nie pokazujemy mu kodów technicznych jako głównej treści.
9. Przy blockerze lub błędzie obszar wynikowego grafiku w Excelu pozostaje niezmieniony.
10. W pilotażu chmura operuje na stabilnych ID/pseudonimach zamiast pełnych nazwisk. Mapowanie na pełne nazwiska może pozostać lokalnie po stronie Excela.
11. PLAN/REPLAN zwracają kandydatów. Użytkownik musi jawnie wybrać kandydata i wykonać akcję `Użyj tego grafiku`; adapter nie wybiera automatycznie pierwszego wyniku.
12. Zachować istniejący lifecycle: przed pierwszą akceptacją użytkownik może używać REPLAN do szukania innego wariantu. Po akceptacji ponowne przeliczenie używa PLAN; REPLAN nie jest używany po akceptacji.

## 2. Granica bieżącego Tasku — miesięczna praca, nie drugi panel administracyjny

Ten Task nie przenosi całego setupu Roty do Excela.

Na wejściu istnieją już w Rota:

- `Site` i jego konfiguracja;
- aktywny roster i stabilne `employee_id`;
- pseudonimy/display_name pracowników;
- reguły, role, shift catalog i pozostałe trwałe ustawienia obiektu.

Excel jest w tym Tasku klientem miesięcznej pracy koordynatora. Może zmieniać wyłącznie dwa rodzaje danych wejściowych, które już mają istniejących ownerów:

1. miesięczny cel godzinowy pracownika — owner `rota.application.durable_inputs.set_target_hours`;
2. okres dostępności/nieobecności pracownika — owner `rota.application.durable_inputs.append_availability`.

Tworzenie/usuwanie pracowników, zmiana `day_only`, attach/detach rosteru, role, konfiguracja zmian i ustawienia Site są OUT_OF_SCOPE. Dzięki temu adapter nie buduje równoległego panelu administracyjnego.

## 3. Standardowy szablon `.xlsx` — zamrożony kontrakt danych

Implementer ma utworzyć `excel/TEMPLATE_CONTRACT.md` literalnie z poniższego kontraktu; nie wolno mu samodzielnie dodawać pól produktu.

### 3.1 Stabilne nazwy zakresów / tabel

W standardowym `.xlsx` muszą istnieć:

- `ROTA_SITE_ID` — jedna komórka, tylko odczyt dla użytkownika;
- `ROTA_MONTH` — jedna komórka w formacie `YYYY-MM-01`;
- tabela `ROTA_EMPLOYEES`;
- tabela `ROTA_AVAILABILITY`;
- obszar wynikowy `ROTA_SCHEDULE_OUTPUT`;
- obszar kandydatów/wyboru `ROTA_CANDIDATES`.

### 3.2 `ROTA_EMPLOYEES`

Jeden wiersz na aktywnego LOCAL pracownika istniejącego już w rosterze.

Kolumny:

- `employee_id` — stabilne ID, ukryte lub techniczne, nieedytowalne przez zwykłego użytkownika;
- `pseudonym` — lokalna czytelna nazwa; może być pełnym nazwiskiem wyłącznie lokalnie, ale request do Railway wysyła tylko wartość dopuszczoną przez pilota/pseudonim;
- `target_hours` — liczba całkowita >= 0; jedyne edytowalne pole tego wiersza należące do requestu planistycznego.

`employee_id` musi odpowiadać istniejącemu pracownikowi aktywnego rosteru Site. Adapter nie tworzy pracownika i nie zmienia rosteru.

### 3.3 `ROTA_AVAILABILITY`

Każdy wiersz opisuje jeden trwały rekord availability dla istniejącego `employee_id`.

Kolumny dokładnie odpowiadają istniejącemu kontraktowi write-ownera:

- `availability_id` — stabilne ID; dla nowego wiersza generowane przez klienta raz i zachowywane przy retry;
- `employee_id`;
- `kind` — istniejąca wartość `AvailabilityKind`;
- `start_date` — ISO `YYYY-MM-DD`;
- `end_date` — ISO `YYYY-MM-DD`;
- `start_time` — opcjonalne `HH:00`;
- `end_time` — opcjonalne `HH:00`;
- `delegation_hours` — opcjonalna liczba całkowita;
- `active` — boolean.

Walidacja semantyki kombinacji pól pozostaje w istniejącym ownerze persistence/application; VBA nie implementuje własnych reguł availability.

### 3.4 `ROTA_CANDIDATES` — zamrożony kontrakt podglądu

`ROTA_CANDIDATES` jest tabelą techniczno-prezentacyjną. Jeden kandydat zajmuje po jednym wierszu na pracownika.

Kolumny:

- `candidate_id` — identyczny dla wszystkich wierszy tego kandydata, tylko odczyt;
- `candidate_no` — kolejny numer prezentacyjny 1..N, tylko odczyt;
- `employee_id` — stabilne ID, tylko odczyt;
- `pseudonym` — czytelna lokalna nazwa pracownika;
- `day_01` ... `day_31` — wartość projekcji danego dnia (`D`, `N`, `DEL`, nieobecność, inny kod pracy albo puste); dni nieistniejące w miesiącu pozostają puste;
- `total_hours` — suma godzin z projekcji dla pracownika w kandydacie.

Jedna komórka nazwana `ROTA_SELECTED_CANDIDATE_ID` przechowuje `candidate_id` wybrany przez użytkownika. Akcja `Użyj tego grafiku` czyta wyłącznie tę komórkę. Wygląd, kolory i grupowanie wierszy są prezentacją i mogą zostać dobrane przez implementera, ale powyższe kolumny i nazwa komórki są kontraktem.

### 3.5 `ROTA_SCHEDULE_OUTPUT` — zamrożony kontrakt wyniku

`ROTA_SCHEDULE_OUTPUT` jest tabelą jednego zaakceptowanego/bieżącego grafiku. Jeden wiersz = jeden pracownik.

Kolumny:

- `employee_id`;
- `pseudonym`;
- `day_01` ... `day_31` — ta sama semantyka wartości co w `ROTA_CANDIDATES`;
- `total_hours`.

Dane pochodzą wyłącznie ze wspólnej `schedule_projection`. Tabela nie jest źródłem danych solvera i nie jest częściowo aktualizowana: VBA buduje kompletny nowy zestaw w pamięci i dopiero po pełnym sukcesie zastępuje zawartość tabeli.

## 4. Request DTO i zapis danych wejściowych

### 4.1 `ExcelMonthlyInputRequest`

Wspólny payload wejściowy dla PLAN/REPLAN:

```text
site_id: str
month: str  # YYYY-MM-01
target_hours: [
  { employee_id: str, target_hours: int }
]
availability: [
  {
    availability_id: str,
    employee_id: str,
    kind: str,
    start_date: str,
    end_date: str,
    start_time: str | null,
    end_time: str | null,
    delegation_hours: int | null,
    active: bool
  }
]
```

Nie ma pól `db_path`, `coordinator_id`, pełnego nazwiska ani konfiguracji Site.

### 4.2 Granica rosteru i walidacja całego payloadu przed zapisem

External router przed pierwszym zapisem:

1. rozwiązuje `site_id` w uwierzytelnionym context;
2. pobiera aktywny roster Site;
3. buduje zbiór `employee_id` dla rekordów `membership_kind=LOCAL` i `enabled=True`;
4. sprawdza, że każdy `employee_id` z `target_hours` i `availability` należy do tego zbioru;
5. waliduje format całego DTO, miesiąc oraz wszystkie wymagane pola.

Jeżeli choć jeden `employee_id` jest obcy, nieaktywny albo nie-LOCAL, cały request zostaje odrzucony przed pierwszym zapisem. Nie wolno częściowo zastosować pozostałych wierszy.

### 4.3 Retry-safe orkiestracja bez nowego ledgeru

Nie tworzyć osobnej tabeli idempotency ani drugiego modelu monthly inputs. External router ma zachowywać się jak idempotentny reconciler bieżących miesięcznych wejść:

- `target_hours`: przed wywołaniem `set_target_hours(...)` odczytać bieżącą wartość; jeżeli jest identyczna z payloadem, pominąć write;
- `availability`: dla każdego `availability_id` odczytać najnowszą wersję rodziny; jeżeli jej semantyczny stan (`employee_id`, `kind`, daty, czasy, `delegation_hours`, `active`) jest identyczny z payloadem, pominąć `append_availability(...)`;
- dopiero rekordy różniące się od bieżącego stanu trafiają do istniejących write-ownerów;
- cały payload musi przejść walidację z 4.2 przed wykonaniem pierwszego write.

Dzięki temu retry po częściowym błędzie nie dopisuje drugi raz już zastosowanych wersji availability i nie wymaga nowego request-ledgera. To jest ochrona wyłącznie na granicy external adaptera; nie zmienia semantyki `append_availability()`.

### 4.4 Ownerzy zapisu

Router external jest wyłącznie orkiestratorem:

- zmieniony `target_hours` zapisuje przez istniejący `set_target_hours(...)`;
- zmieniony wiersz availability zapisuje przez istniejący `append_availability(...)`;
- po zastosowaniu wymaganych różnic wywołuje istniejący `plan_month(...)` albo `replan(...)` zgodnie z fazą lifecycle.

Jeżeli walidacja wstępna nie przejdzie, nie ma żadnego zapisu. Jeżeli kontrolowany błąd wystąpi później, `ROTA_SCHEDULE_OUTPUT` pozostaje bez zmian, użytkownik dostaje komunikat operacyjny, a ponowienie tego samego payloadu bezpiecznie pomija już zastosowane identyczne fakty.

## 5. Zachowanie użytkownika i lifecycle

### Pierwsza instalacja

Zaufany instalator instaluje `ELNATH_ROTA_ADDIN.xlam` i konfiguruje adres usługi Rota oraz wydany klucz dostępu. Użytkownik nie wpisuje klucza przy każdym użyciu.

### PLAN / `Przelicz`

1. Użytkownik otwiera standardowy `.xlsx`.
2. Uzupełnia `target_hours` oraz potrzebne okresy w `ROTA_AVAILABILITY`.
3. Wybiera `Przelicz`.
4. Dodatek wysyła `ExcelMonthlyInputRequest`.
5. Rota zapisuje dane przez istniejących ownerów i wywołuje `plan_month()`.
6. Jeśli Rota zwraca kandydatów, dodatek pokazuje ich w `ROTA_CANDIDATES`; nie zmienia jeszcze zaakceptowanego grafiku.
7. Użytkownik wybiera jednego kandydata i uruchamia `Użyj tego grafiku`.
8. Dopiero sukces istniejącego `select_candidate()` pozwala wypełnić `ROTA_SCHEDULE_OUTPUT` projekcją bieżącego grafiku.

### REPLAN / `Pokaż inny wariant`

Przed pierwszą akceptacją miesiąca użytkownik może uruchomić `Pokaż inny wariant`. Adapter wywołuje istniejący `replan()` i ponownie pokazuje kandydatów. Żaden kandydat nie jest akceptowany automatycznie.

Po pierwszej akceptacji akcja szukania innego wariantu nie używa `replan()`. Jeżeli użytkownik ponownie wybiera `Przelicz`, adapter uruchamia zwykły PLAN zgodnie z aktualnym ownerem lifecycle. Nie zmieniać `ReplanNotAvailableAfterAcceptance` ani reguł lifecycle.

## 6. API dla dodatku — cienki adapter

Dodać jeden router pod `/external/excel`.

Minimalna powierzchnia:

- `POST /external/excel/plan` — payload `ExcelMonthlyInputRequest`;
- `POST /external/excel/replan` — ten sam payload; tylko gdy lifecycle dopuszcza REPLAN;
- `POST /external/excel/select-candidate` — `{site_id, month, candidate_id}` i delegacja do istniejącego `select_candidate()`;
- `GET /external/excel/schedule/{site_id}/{month}` — bieżąca projekcja zaakceptowanego grafiku.

Nie tworzyć endpointu zarządzania personelem, Site ani konfiguracją solvera.

Zewnętrzny response DTO może stabilizować nazwy pól dla klienta Excel, ale status/kandydaci/blockery muszą wynikać z istniejących application operations, bez drugiej klasyfikacji.

### 6.1 `candidate_id` — identyfikator adaptera, nie nowy stan domenowy

Obecny `PlanPreview` przechowuje kandydatów jako listy `Assignment`; Task nie dodaje trwałego candidate entity ani candidate table.

External router przy serializacji aktualnego server-side `PlanPreview` wylicza dla każdego kandydata `candidate_id` jako SHA-256 kanonicznej treści tej listy Assignment. Kanoniczna treść obejmuje co najmniej wszystkie pola Assignment wpływające na tożsamość grafiku i jest sortowana deterministycznie przed hashowaniem. Ten sam kandydat w tym samym preview daje ten sam hash.

`POST /external/excel/select-candidate` nie przyjmuje listy Assignment od klienta. Router:

1. odczytuje aktualny server-side `PlanPreview` dla wskazanego `site_id` + `month`;
2. ponownie wylicza `candidate_id` dla każdego kandydata z tego preview;
3. wybiera wyłącznie kandydata, którego wyliczony hash dokładnie odpowiada przesłanemu ID;
4. dopiero tę server-side listę Assignment przekazuje do istniejącego `select_candidate()`.

Brak dopasowania oznacza kontrolowany blocker: kandydat jest nieaktualny albo nie należy do bieżącego preview; użytkownik ma ponownie wybrać `Przelicz`/`Pokaż inny wariant`. Stary hash, hash z innego Site/miesiąca lub dowolna wartość klienta nie może zostać rozwiązana poza aktualnym preview.

## 7. Auth — alternatywny credential, ten sam context

Obecny browser/PWA auth pozostaje bez zmian: cookie/JWT z `api/auth/backend.py` i `api/auth/context.py` nadal obsługuje React/PWA.

Dla dodatku Excel dodać wąski API key:

- administrator generuje losowy sekret dla istniejącego konta;
- serwer zapisuje hash klucza oraz powiązanie z istniejącym account/user id;
- surowy klucz jest pokazywany tylko przy wydaniu;
- request wysyła `Authorization: Bearer <key>` po HTTPS;
- credential rozwiązuje ten sam `AccountMapping -> db_path + coordinator_id`;
- caller nie może podać `db_path` ani `coordinator_id`;
- klucz może zostać unieważniony.

Nie przerabiać istniejącego cookie auth na własny wspólny system tokenów.

## 8. Wspólna projekcja grafiku

`rota/application/schedule_export.py` ma prywatną, PDF-ową logikę składania grafiku do prezentacji. Nie kopiować tej dekompozycji do Excela.

Wyodrębnić najmniejszy wspólny model/projection builder niezależny od formatu. PDF oraz external Excel API korzystają z tego samego wyniku dla kodów pracy, nieobecności, DELEGACJI, godzin i kolejności wierszy.

Renderer PDF pozostaje rendererem PDF. Nowy projection owner nie importuje `reportlab` i nie zna komórek Excela.

## 9. Kontrakt komunikatów dla człowieka

Każdy kontrolowany komunikat musi zawierać:

1. co konkretnie blokuje operację;
2. kogo/czego dotyczy, jeśli backend to wie;
3. konkretne następne działanie użytkownika;
4. informację o ponowieniu operacji, jeśli to właściwa recovery path.

Przykład formy: `Pracownik A nie ma ustawionego celu godzinowego na wrzesień. Wpisz cel w kolumnie Godziny i wybierz Przelicz.`

Zakazane jako jedyna treść: surowy status/kod, UUID, traceback, nazwa wyjątku albo samo `Wystąpił błąd`, jeżeli backend ma kontrolowany blocker i recovery.

Przy błędzie sieci/auth/parsing obszar grafiku pozostaje bez zmian.

## 10. Artefakty Excel/VBA

Bieżący Task ma dostarczyć realny, testowalny artefakt instalacyjny dodatku, nie wyłącznie źródło `.bas`.

Wymagane:

- `excel/ELNATH_ROTA_TEMPLATE.xlsx` — standardowy plik bez VBA;
- `excel/ELNATH_ROTA_ADDIN.xlam` — instalowalny dodatek;
- `excel/src/elnath_rota_addin.bas` — źródło VBA odpowiadające artefaktowi;
- `excel/build_addin.ps1` — powtarzalny skrypt budujący/odtwarzający `.xlam` ze źródła na maszynie z desktopowym Excelem;
- `excel/INSTALL.md` — jednorazowa instalacja dodatku i konfiguracja `service_url` + access key;
- `excel/TEMPLATE_CONTRACT.md` — literalny kontrakt z sekcji 3.

Test instalacyjny nie wymaga automatyzowania całego GUI Office w CI. Musi istnieć deterministyczny build/rebuild artefaktu oraz manualny smoke procedure opisany w `INSTALL.md`.

## 11. Atomiczność prezentacji

Dodatek nie zmienia `ROTA_SCHEDULE_OUTPUT`, dopóki nie ma kompletnego sukcesu `select_candidate()` i kompletnej projekcji bieżącego grafiku.

PLAN/REPLAN mogą zapisać dane wejściowe w Rota i utworzyć preview/kandydatów zgodnie z istniejącym lifecycle; nie są jeszcze zmianą zaakceptowanego grafiku. Blocker, błąd sieci, auth lub parsing nie może zostawić częściowo nadpisanego obszaru wynikowego.

## 12. Acceptance

- `XL-01`: z desktopowego Excela można uruchomić PLAN bez interaktywnego logowania przy każdym użyciu.
- `XL-02`: prawidłowy API key rozwiązuje istniejący server-side `AccountMapping`; request nie może wybrać cudzej bazy/coordinator_id.
- `XL-03`: invalid/revoked key nie dociera do domenowej bazy klienta.
- `XL-04`: browser/PWA cookie auth nie zmienia kontraktu.
- `XL-05`: standardowy szablon ma dokładnie zakresy/tabele z sekcji 3; Excel wysyła tylko zamrożone monthly inputs.
- `XL-06`: `target_hours` trafia przez `set_target_hours`; availability przez `append_availability`; Excel nie ma drugich write-ownerów.
- `XL-07`: PLAN zwraca kandydatów i nie akceptuje żadnego automatycznie.
- `XL-08`: `Użyj tego grafiku` deleguje do istniejącego `select_candidate()` i dopiero po sukcesie aktualizuje wynik w arkuszu.
- `XL-09`: REPLAN jest dostępny wyłącznie przed pierwszą akceptacją; po akceptacji ponowne `Przelicz` używa PLAN, bez zmiany lifecycle.
- `XL-10`: kontrolowany blocker nie zmienia wyniku arkusza i pokazuje problem + konkretne działanie bez kodu technicznego jako głównej treści.
- `XL-11`: błąd sieci/auth/parsing nie pozostawia częściowo nadpisanego grafiku.
- `XL-12`: PDF i Excel używają jednego wspólnego modelu projekcji grafiku.
- `XL-13`: standardowy grafik to `.xlsx` bez makr, a repo dostarcza osobny, instalowalny `.xlam` wraz ze źródłem i powtarzalnym buildem.
- `XL-14`: core SaaS obsługuje jeden zamrożony szablon; obcy layout nie jest automatycznie mapowany.
- `XL-15`: request do Railway nie wymaga pełnych nazwisk.
- `XL-16`: `candidate_id` jest wyliczany deterministycznie z aktualnego server-side preview; select odrzuca ID stare/obce i nigdy nie przyjmuje Assignment od klienta.
- `XL-17`: `ROTA_CANDIDATES`, `ROTA_SELECTED_CANDIDATE_ID` i `ROTA_SCHEDULE_OUTPUT` mają dokładny kontrakt kolumn z sekcji 3.
- `XL-18`: cały request jest sprawdzany względem aktywnego LOCAL rosteru przed pierwszym zapisem; jeden obcy/nieaktywny employee_id odrzuca całość.
- `XL-19`: retry tego samego payloadu po częściowym błędzie nie tworzy kolejnej wersji availability dla rekordów już zgodnych z żądanym stanem.

## 13. OUT_OF_SCOPE

- tworzenie/usuwanie pracowników i zmiana rosteru z Excela;
- zmiana `day_only`, ról, Site, shift catalog i innych ustawień administracyjnych z Excela;
- automatyczne dopasowanie do dowolnego pliku Excel klienta;
- Office Script / Excel Online / SharePoint w tym Tasku;
- LibreOffice/OpenOffice i Google Sheets w tym Tasku;
- wbudowanie makra do `.xlsx` lub `.xlsm` jako standardowego grafiku;
- solver/walidacja domenowa w VBA;
- pełna dwukierunkowa synchronizacja produktu;
- interaktywne browser login w dodatku;
- zmiana cookie/JWT auth dla PWA;
- nowy solver/stateless planning engine;
- pełna anonimizacja/GDPR design;
- billing/licencjonowanie;
- zmiana reguł PLAN/REPLAN.

## 14. Ocena przyszłych cienkich klientów — poza implementacją tego Tasku

Neutralny external API + `schedule_projection` celowo nie może zawierać wiedzy o VBA/Excel. Dzięki temu przyszły klient nie musi dotykać solvera ani persistence.

### LibreOffice / OpenOffice

Wykonalność: **tak jako osobny klient**, ale nie zakładać współdzielenia kodu VBA 1:1. LibreOffice ma własny Basic/UNO i mechanizmy pobierania treści webowych; praktyczny klient powinien być cienką warstwą nad tym samym external API. OpenOffice należy traktować jako osobny wariant kompatybilności, nie jako automatycznie zgodny z LibreOffice.

Etapowanie: dopiero po stabilizacji neutralnego API na kliencie Excel. Najpierw spike jednego requestu auth + PLAN + zapis projekcji do Calc, bez zmian backendu poza ewentualną naprawą faktycznej nieprzenośności kontraktu.

### Google Sheets

Wykonalność: **tak jako osobny klient** przez Apps Script: skrypt arkusza może dodać menu/akcję, wysyłać HTTPS requesty do external API i zapisywać wynik do komórek. Wymaga jednak własnego modelu autoryzacji/sekretów i zgód Apps Script, więc nie kopiować założeń instalacyjnych `.xlam`.

Etapowanie: osobny Task po ustabilizowaniu neutralnego API. Spike: Apps Script `Przelicz` -> external API -> pokazanie kandydatów -> jawny wybór -> zapis projekcji. Bez zmian solvera.

Wniosek architektoniczny: nie budować teraz wspólnego „frameworka arkuszy”. Wspólnym produktem ma być neutralny API/projection contract; każdy arkusz dostaje własny cienki adapter.

## 15. TASK_SCOPE

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
- `excel/ELNATH_ROTA_TEMPLATE.xlsx` (nowy, bez VBA)
- `excel/ELNATH_ROTA_ADDIN.xlam` (nowy artefakt binarny)
- `excel/src/elnath_rota_addin.bas` (nowy)
- `excel/build_addin.ps1` (nowy)
- `excel/INSTALL.md` (nowy)
- `excel/TEMPLATE_CONTRACT.md` (nowy)
- `tests/test_excel_api_key_auth.py` (nowy)
- `tests/test_excel_external_api.py` (nowy)
- `tests/test_schedule_projection.py` (nowy)
- `tests/test_t020_export.py`
- `tests/test_t024_tester_login_isolation.py`

Każdy inny plik produkcyjny wymaga STOP i korekty briefu.

## 16. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `api/auth/context.py --symbol get_authenticated_context`
- TARGETS: `api/deps.py`
- TARGETS: `api/routers/schedule.py --symbol _planning_result_out`
- TARGETS: `rota/application/plan_ops.py --symbol plan_month`
- TARGETS: `rota/application/plan_ops.py --symbol replan`
- TARGETS: `rota/application/plan_ops.py --symbol select_candidate`
- TARGETS: `rota/application/durable_inputs.py --symbol set_target_hours`
- TARGETS: `rota/application/durable_inputs.py --symbol append_availability`
- TARGETS: `rota/application/schedule_export.py --symbol _assemble_export_model`
- TARGETS: `api/main.py`
- REASON: Task dodaje alternatywny auth client, cienki external router, reuse dwóch istniejących write-ownerów, istniejący select-candidate lifecycle oraz wydziela wspólną projekcję grafiku.

Dwa wcześniejsze niewykonalne cele symbolowe `api/deps.py --symbol ...` zostały zastąpione jednym celem plikowym zgodnie z precheckiem Codexa. Pozostałe mapy z R2 nie wymagają ponownego szerokiego mapowania repo.

## 17. Weryfikacja

Minimalna macierz:

1. API key: valid / invalid / revoked / izolacja tenantów;
2. brak regresji browser cookie auth;
3. zapis `target_hours` i availability korzysta z istniejących ownerów;
4. PLAN -> kandydaci, bez automatycznej akceptacji;
5. REPLAN tylko przed pierwszą akceptacją;
6. select_candidate -> bieżący grafik -> projection;
7. kontrolowany blocker + network/auth/parsing nie zmieniają `ROTA_SCHEDULE_OUTPUT`;
8. wspólna projection: reprezentatywny OCHRONA, ORDINARY, DEL i nieobecność;
9. `.xlsx` nie zawiera VBA; osobny `.xlam` jest odtwarzalny ze źródła przez build procedure;
10. candidate hash: deterministyczny, rozwiązywany tylko wobec aktualnego preview; stary/obcy hash odrzucony;
11. template contract: dokładne kolumny `ROTA_CANDIDATES` i `ROTA_SCHEDULE_OUTPUT` + `ROTA_SELECTED_CANDIDATE_ID`;
12. roster gate: jeden employee_id spoza aktywnego LOCAL rosteru odrzuca cały request bez write;
13. retry po wymuszonym błędzie po części zapisów nie dopisuje ponownie już zgodnych availability;
14. smoke manualny: instalacja add-in -> PLAN -> wybór kandydata -> `Użyj tego grafiku` -> wynik w standardowym arkuszu.

Nie uruchamiać pełnej regresji bez osobnej zgody OWNERA. Implementacja rusza dopiero po `PASS PREIMPLEMENTATION` Codexa i osobnym PASS merytorycznym CC.