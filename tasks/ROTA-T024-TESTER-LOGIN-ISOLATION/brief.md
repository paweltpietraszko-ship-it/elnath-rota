# ROTA-T024-TESTER-LOGIN-ISOLATION — lekki gotowy auth + osobna SQLite per konto

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE:
- concept exact `e95f4a437550783eb1be60cbb640407198416c89`
- Codex concept precheck R2 `bf90abfd43c5da42572bd14d109403dd32c649aa`
- `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`
- OWNER/ARCHITECT DECISION 2026-09-13: nie budować prowizorycznego własnego auth tylko dla testerów; użyć lekkiego gotowego komponentu, który może pozostać w normalnym użyciu produktu.

## 1. Decyzja zakresu / ownership

Ten Task świadomie przejmuje teraz z T025 minimalny, ale docelowo używalny wycinek F1+F3:

- F1: password-based login i sesja użytkownika;
- F3: osobna trwała baza SQLite per konto na jednym hostowanym wdrożeniu.

Nie tworzymy tymczasowego auth-lite do późniejszego wyrzucenia. Warstwa uwierzytelniania ma być oparta o dojrzały, gotowy komponent `fastapi-users`, a własny kod Rota ma odpowiadać wyłącznie za to, co jest specyficzne dla produktu: mapowanie uwierzytelnionego konta na `coordinator_id` i właściwą bazę SQLite.

T025 pozostaje ownerem późniejszej decyzji o Postgresie, skalowaniu poziomym, ewentualnym SSO/OIDC i szerszym modelu organizacyjnym. Obecny Task nie tworzy drugiego konkurencyjnego systemu auth.

## 2. Zamrożony model izolacji

Każde konto użytkownika ma dokładnie:

- stabilny identyfikator konta z warstwy auth;
- login/email lub równoważny identyfikator wymagany przez bibliotekę;
- własny `coordinator_id`;
- własny dozwolony plik SQLite;
- flagę aktywności zgodną z biblioteką / rejestrem mapowania.

Jedno konto NIE może wybrać innej bazy, podać innego `coordinator_id` ani przełączyć się na dane innego użytkownika przez parametr requestu.

Baza użytkownika pozostaje kompletnym, izolowanym światem danych. Nie dodajemy `tenant_id` do tabel domenowych i nie zmieniamy `rota/planning`, solvera ani `rota/domain.py` z powodu tenancy.

## 3. Auth — gotowy komponent, nie własny subsystem

Uwierzytelnianie implementuje `fastapi-users`.

Wymagany profil funkcjonalny:

- login hasłem;
- logout;
- cookie transport odpowiedni dla React/FastAPI;
- `HttpOnly`;
- `Secure` w hostowanym HTTPS;
- `SameSite=Lax` lub równie restrykcyjna konfiguracja zgodna z biblioteką i aktualnym deploymentem;
- chronione endpointy korzystają z jednego library-backed `current_user`/dependency zamiast własnej weryfikacji tokenu;
- hashowanie i weryfikacja haseł należą do biblioteki / jej wspieranego password helpera, nie do kodu Rota;
- brak publicznej rejestracji.

Nie implementować własnego:

- `hashlib.scrypt`/PBKDF2/bcrypt wrappera w Rota;
- formatu tokenu;
- HMAC session cookie;
- parsera/validatora sesji;
- własnego mechanizmu reset-tokenów;
- drugiego równoległego auth middleware/dependency.

## 4. Zarządzanie kontem — małe, ale nie prowizoryczne

Konta są tworzone ręcznie przez OWNERA/operatora przez mały provisioning CLI/helper. Nie powstaje panel administracyjny i nie ma samorejestracji.

Użytkownik po zalogowaniu MUSI móc zmienić własne hasło przy użyciu mechanizmu wspieranego przez `fastapi-users` / jego UserManager. Nie tworzymy osobnego algorytmu zmiany hasła w Rota.

Jeżeli użytkownik zapomni hasła, operator może ręcznie ustawić nowe hasło przez provisioning/admin CLI korzystający z tego samego library-supported password helpera. W tym Tasku nie budujemy maili, linków resetujących, SMTP ani publicznego „zapomniałem hasła”.

Zmiana/reset hasła nie może zmienić:

- identyfikatora konta;
- `coordinator_id`;
- przypisanej bazy;
- uprawnień do obiektów.

## 5. Rejestr auth a mapowanie Rota

Nie mieszamy credential storage z bazami grafików testerów.

Minimalny trwały model składa się z dwóch odpowiedzialności:

1. `fastapi-users` przechowuje/obsługuje rekord użytkownika i credential state zgodnie ze swoim wspieranym adapterem;
2. mały rejestr/mapowanie Rota wiąże stabilny identyfikator użytkownika auth z:
   - `coordinator_id`;
   - `db_filename` — tylko nazwa pliku w zaufanym katalogu, nie dowolna ścieżka;
   - ewentualną flagą aplikacyjną potrzebną do odcięcia dostępu.

Codex ma w prechecku potwierdzić najlżejszy wspierany adapter persistence dla `fastapi-users`, który nie zmusza tego Tasku do migracji domenowych baz Rota do Postgresa. Jeżeli biblioteka wymaga osobnej małej bazy auth SQLite/SQLAlchemy, jest to dopuszczalne i preferowane względem wciskania rekordów auth do każdej bazy testera.

Rejestr/mapowanie nie jest zwracane frontendowi i nie trafia do diagnostic ZIP.

## 6. Jeden request-scoped owner tożsamości Rota

Powstaje jeden request-scoped `AuthenticatedContext` (nazwa techniczna może się różnić), budowany wyłącznie z poprawnie uwierzytelnionego użytkownika zwróconego przez dependency `fastapi-users`.

Niesie razem:

- stabilny auth user/account id;
- kanoniczny `db_path` wyprowadzony z mapowania Rota i jednego zaufanego katalogu baz;
- `coordinator_id`.

`get_conn()` używa wyłącznie `context.db_path`.

Siedem routerów wskazanych w koncepcji (`bootstrap`, `durable_inputs`, `export`, `manual_edit`, `rule_decisions`, `schedule`, `site_profile`) przestaje używać `DEV_COORDINATOR_ID` jako runtime identity i bierze `coordinator_id` z tego samego contextu.

Nie wolno przyjmować `db_path`, auth user id ani runtime `coordinator_id` z body/query/path jako źródła autoryzacji.

## 7. Pierwsze użycie bazy i Coordinator

Po provisioningu konta pierwszy poprawnie uwierzytelniony dostęp może utworzyć brakujący plik bazy przez istniejący `connect()`/migracje.

Dla nowej bazy backend zapewnia dokładnie jednego aktywnego `Coordinator` odpowiadającego `context.coordinator_id`. To zastępuje produkcyjne poleganie na globalnym `api/dev_seed.py` / `DEV_COORDINATOR_ID`.

`api/dev_seed.py` pozostaje narzędziem lokalnego developmentu i nie jest mechanizmem provisioningu użytkowników.

## 8. Backup / recovery / RODO encryption

Backup i recovery muszą używać ścieżki dokładnie tej bazy, z której pochodzi request-scoped `conn`; nie wolno używać globalnego `DB_PATH` dla requestu użytkownika.

Każdy plik SQLite ma własny DEK zgodnie z istniejącym `pii_crypto`; w CENTRAL_SERVICE DEKi mogą być owinięte tym samym deploymentowym `ROTA_CENTRAL_KEK`. Nie powstaje nowy key-management model per użytkownik.

Użytkownik może pobrać backup wyłącznie swojej bazy.

## 9. Runtime log / diagnostics

Istniejący backendowy `runtime-errors.log` w CENTRAL_SERVICE pozostaje jednym technicznym logiem procesu/deploymentu. Nie tworzymy request-aware loggera ani osobnego pliku logu per użytkownik w tym Tasku.

Ponieważ globalny runtime log może zawierać zdarzenia wielu kont, user-facing diagnostic ZIP w hostowanym multi-user deployment NIE może dołączać wspólnego `runtime-errors.log*`.

Runtime log pozostaje dostępny operatorowi/CC po stronie deploymentu. LOCAL_WINDOWS zachowuje dotychczasowe zachowanie jednego użytkownika/jednego logu.

Nie dodawać danych identyfikujących użytkownika ani danych biznesowych do runtime logu tylko po to, aby filtrować ZIP.

## 10. Frontend

Przed wejściem do aplikacji hostowanej użytkownik widzi prosty ekran login + hasło.

Frontend nie przechowuje hasła ani tokenu w `localStorage`/`sessionStorage`; korzysta z cookie HttpOnly wystawianego przez backend/auth transport.

Po 401/wygaśnięciu sesji wraca do ekranu logowania. Nie tworzyć identity switchera.

W ustawieniach/profilu użytkownika istnieje prosta akcja `Zmień hasło`, korzystająca z library-backed flow. Bez panelu zarządzania kontami.

Onboarding pozostaje poza scope.

## 11. Model wdrożenia tej fazy

Ten kontrakt dotyczy hostowanego deploymentu z jednym procesem/usługą aplikacji i trwałym wolumenem zawierającym:

- małą persistence auth wymaganą przez `fastapi-users`;
- mapowanie auth-user → coordinator/database;
- katalog baz użytkowników;
- istniejące pliki wymagane przez CENTRAL_SERVICE.

Jednoczesne użycie przez kilku użytkowników jest dopuszczone, ponieważ każdy pracuje na innym pliku SQLite. Ten Task nie obiecuje wieloinstancyjnego/multi-replica dostępu do tego samego pliku SQLite. Skalowanie poziome i Postgres należą do późniejszego T025.

## 12. Acceptance

T24-1. Bez poprawnej sesji chroniony endpoint workspace zwraca 401 i nie otwiera żadnej bazy użytkownika.

T24-2. Poprawne konto A otwiera wyłącznie DB-A; konto B wyłącznie DB-B. Danych utworzonych przez A nie ma w API/backup/diagnostyce B i odwrotnie.

T24-3. Próba podania cudzego `site_id`, `coordinator_id`, nazwy bazy lub zmodyfikowania cookie nie zmienia mapowania user → db/coordinator; niedozwolona sesja/request jest odrzucany.

T24-4. Każda mutacja wykonywana jako konto A zapisuje action/audit z `coordinator_id` A, nie `DEV_COORDINATOR_ID`; analogicznie dla B.

T24-5. Wszystkie siedem wskazanych routerów korzysta z jednego request-scoped ownera identity; `DEV_COORDINATOR_ID` nie jest runtime identity hostowanego użytkownika.

T24-6. Rota nie implementuje własnego password hashing/token/session parsera; login/logout/current-user są realizowane przez jeden `fastapi-users` path.

T24-7. Cookie jest HttpOnly i w hostowanym HTTPS Secure; po utracie/wygaśnięciu sesji chronione API zwraca 401, a frontend wraca do loginu.

T24-8. Użytkownik może po zalogowaniu zmienić własne hasło bez zmiany `coordinator_id`, db mappingu i uprawnień.

T24-9. Operator może ręcznie ustawić nowe hasło konta przez CLI/helper korzystający z tego samego library-supported password helpera; nie powstaje publiczny reset-mail flow.

T24-10. Backup konta A zawiera snapshot DB-A i używa właściwego dla DB-A DEK/recovery metadata; nie odwołuje się do globalnego `DB_PATH` innego konta.

T24-11. Nowa baza użytkownika migruje się istniejącym `connect()` i ma aktywnego Coordinator zgodnego z provisioned `coordinator_id`, bez ręcznego `dev_seed`.

T24-12. CENTRAL_SERVICE może mieć wspólny runtime log operatora, ale user-facing diagnostic ZIP nie zawiera wspólnego `runtime-errors.log*`; nie ma cross-account leakage przez diagnostics.

T24-13. Dwa równoległe requesty A/B używają właściwych dwóch plików i coordinatorów; context jednego requestu nie przecieka do drugiego.

T24-14. Nie ma zmian w `rota/planning`, solverze ani tabelach domenowych w celu tenancy; nie powstaje `tenant_id` retrofit.

T24-15. Nie powstaje panel admina, samorejestracja, SMTP/reset-mail, OAuth/SSO, onboarding ani Redis.

## 13. Literalny TASK_SCOPE

Production — oczekiwany minimalny zakres:

- dependency `fastapi-users` + najlżejszy wspierany adapter persistence uzgodniony po prechecku;
- `api/` cienka konfiguracja biblioteki auth, bez własnej kryptografii/session format;
- `api/deps.py` — request-scoped auth context + DB selection;
- `api/config.py` — zaufany katalog baz/mapowania i sekrety wymagane przez library transport; usunięcie zależności hostowanego runtime od `DEV_COORDINATOR_ID`;
- pojedynczy auth router/set routerów wystawiany przez bibliotekę tylko w zakresie login/logout/current-user/update-password potrzebnym Rota;
- siedem routerów wskazanych w §6 — tylko mechaniczne pobranie `coordinator_id` z contextu;
- `api/routers/backup.py` — właściwy per-account `db_path` + central diagnostic ZIP bez shared runtime logu;
- `api/dev_seed.py` — tylko jeśli konieczna jest jawna korekta, aby pozostał dev-only;
- frontend: ekran logowania + wspólna obsługa 401 + prosta akcja zmiany własnego hasła;
- provisioning/admin CLI/helper dla ręcznego tworzenia kont i ręcznego resetu hasła;
- testy auth/isolation/password-change/backup/concurrency.

Jawnie poza scope:

- własny subsystem auth Rota;
- `rota/planning/**`, solver i domenowy tenant retrofit;
- Postgres dla baz domenowych;
- OAuth/SSO/MFA;
- self-registration/admin web panel/SMTP/password-reset-email;
- onboarding;
- poziome multi-replica SQLite;
- redesign istniejącego RODO key-management;
- realne dane pracowników w testowym Railway poza osobną decyzją OWNERA.

## 14. Preimplementation re-check Codexa

Sprawdzić wyłącznie:

1. czy aktualna wersja `fastapi-users` jest kompatybilna z obecnym FastAPI/Python stackiem repo i jaki jest najlżejszy wspierany adapter persistence dla małej osobnej bazy auth;
2. czy cookie transport + library `current_user` pozwalają zbudować jeden request context bez własnej drugiej ścieżki identity;
3. czy biblioteka ma wspierany mechanizm zmiany hasła użytkownika, a provisioning/admin CLI może korzystać z tego samego password helpera bez publicznej rejestracji/reset-mail flow;
4. czy lista miejsc używających `DEV_COORDINATOR_ID` i globalnego `DB_PATH` w request flow jest kompletna dla tego scope (backup/recovery włącznie);
5. czy per-account DB + istniejący CENTRAL_SERVICE KEK tworzy poprawnie osobny DEK per DB bez nowego key-management;
6. czy wyłączenie shared runtime logu z user-facing diagnostic ZIP w CENTRAL_SERVICE zamyka cross-account leak bez łamania lokalnego T021c/technical-error contract;
7. czy jeden-process + per-user SQLite na persistent volume jest technicznie spójny dla tej fazy bez zmian persistence/solver;
8. czy literalny scope wystarcza do T24-1..T24-15 i nie dubluje funkcji, które `fastapi-users` już dostarcza.

Jeżeli 1–8 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać konkretną niekompatybilność biblioteki, brakującą ścieżkę/seam albo sprzeczność; bez projektowania własnego auth, admin panelu, Postgresa lub korporacyjnego IAM.
