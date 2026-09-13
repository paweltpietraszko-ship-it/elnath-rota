# ROTA-T024-TESTER-LOGIN-ISOLATION — login testerów + osobna SQLite per konto

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE:
- concept exact `e95f4a437550783eb1be60cbb640407198416c89`
- Codex concept precheck R2 `bf90abfd43c5da42572bd14d109403dd32c649aa`
- `arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`

## 1. Decyzja zakresu / ownership

Ten Task świadomie przejmuje teraz z T025 wyłącznie minimalny wycinek F1+F3 potrzebny do bezpiecznego testowania hostowanej Rota:

- F1: realny login hasłem i powiązanie requestu z jedną uwierzytelnioną tożsamością;
- F3: osobna trwała baza SQLite per konto testera na jednym hostowanym wdrożeniu.

T025 pozostaje ownerem późniejszej architektury produkcyjnej / ewentualnego Postgresa / szerszego modelu wielu koordynatorów i hostingu. Ten Task nie tworzy drugiego kontraktu auth obok T025 — jest pierwszą minimalną implementacją F1/F3.

Jawnie poza scope: OAuth/SSO, samorejestracja, reset hasła, panel administracyjny, onboarding, role/ACL wykraczające poza istniejące `CoordinatorSiteAssociation`, Postgres, multi-tenant rows w jednej bazie, mobile/PWA polish.

## 2. Zamrożony model izolacji

Każde konto testera ma dokładnie:

- unikalny `account_id` / login;
- hash hasła + salt;
- własny `coordinator_id`;
- własny dozwolony plik SQLite;
- flagę `active`.

Jedno konto NIE może wybrać innej bazy, podać innego `coordinator_id` ani przełączyć się na dane innego testera przez parametr requestu.

Baza testera jest kompletnym, izolowanym światem danych. Nie dodajemy `tenant_id` do tabel domenowych i nie zmieniamy `rota/planning`, solvera ani `rota/domain.py` z powodu tenancy.

## 3. Minimalny rejestr kont

Rejestr kont jest małym artefaktem konfiguracyjnym warstwy `api`, przechowywanym na trwałym wolumenie wdrożenia, poza bazami testerów.

Minimalny rekord:

- `account_id`;
- `password_salt`;
- `password_hash`;
- `coordinator_id`;
- `db_filename` — tylko nazwa pliku, nie dowolna ścieżka;
- `active`.

Hasła nie są przechowywane jawnie. Użyć stdlib `hashlib.scrypt` z losowym saltem i `hmac.compare_digest`; bez nowej biblioteki auth.

Konta zakłada OWNER ręcznie przez mały CLI/provisioning helper należący do tego Tasku. Helper pyta o hasło, generuje salt/hash, waliduje unikalność `account_id`, `coordinator_id` i `db_filename`, aktualizuje rejestr atomowo. Nie ma panelu webowego ani endpointu tworzenia kont.

Rejestr nie jest zwracany frontendowi i nie trafia do diagnostic ZIP.

## 4. Sesja

Login: `POST /api/auth/login` z `account_id` + hasło.

Po poprawnym loginie backend ustawia podpisane cookie sesyjne:

- `HttpOnly`;
- `Secure` w hostowanym HTTPS;
- `SameSite=Lax`;
- stały okres ważności 12 godzin od loginu;
- payload minimalny: `account_id` + expiry;
- podpis HMAC-SHA256 przy użyciu sekretu deploymentu `ROTA_SESSION_SECRET`.

Nie ma tabeli sesji, Redis, JWT frameworka ani refresh tokenów. `POST /api/auth/logout` czyści cookie. Po expiry użytkownik loguje się ponownie.

Błędny login zwraca jeden neutralny komunikat, bez ujawniania czy konto istnieje.

## 5. Jeden request-scoped owner tożsamości

Powstaje jeden request-scoped `AuthenticatedContext` (nazwa techniczna może się różnić), wyliczany wyłącznie z poprawnej sesji. Niesie razem:

- `account_id`;
- kanoniczny `db_path` wyprowadzony z rejestru i jednego zaufanego katalogu baz;
- `coordinator_id`.

`get_conn()` używa wyłącznie `context.db_path`.

Siedem routerów wskazanych w koncepcji (`bootstrap`, `durable_inputs`, `export`, `manual_edit`, `rule_decisions`, `schedule`, `site_profile`) przestaje używać `DEV_COORDINATOR_ID` jako runtime identity i bierze `coordinator_id` z tego samego contextu.

Nie wolno przyjmować `db_path`, `account_id` ani runtime `coordinator_id` z body/query/path jako źródła autoryzacji.

## 6. Pierwsze użycie bazy i Coordinator

Po provisioningu konta pierwszy poprawnie uwierzytelniony dostęp może utworzyć brakujący plik bazy przez istniejący `connect()`/migracje.

Dla nowej bazy backend zapewnia dokładnie jednego aktywnego `Coordinator` odpowiadającego `context.coordinator_id`. To zastępuje produkcyjne poleganie na globalnym `api/dev_seed.py` / `DEV_COORDINATOR_ID`.

`api/dev_seed.py` pozostaje narzędziem lokalnego developmentu i nie jest mechanizmem provisioningu kont testerów.

## 7. Backup / recovery / RODO encryption

Backup i recovery muszą używać ścieżki dokładnie tej bazy, z której pochodzi request-scoped `conn`; nie wolno używać globalnego `DB_PATH` dla requestu testera.

Każdy plik SQLite ma własny DEK zgodnie z istniejącym `pii_crypto`; w CENTRAL_SERVICE DEKi mogą być owinięte tym samym deploymentowym `ROTA_CENTRAL_KEK`. Nie powstaje nowy key-management model per tester.

Tester może pobrać backup wyłącznie swojej bazy.

## 8. Runtime log / diagnostics w multi-tester deployment

Istniejący backendowy `runtime-errors.log` w CENTRAL_SERVICE pozostaje jednym technicznym logiem procesu/deploymentu. Nie tworzymy request-aware loggera ani osobnego pliku logu per tester w tym Tasku.

Ponieważ globalny runtime log może zawierać zdarzenia wielu kont, tester-facing diagnostic ZIP w hostowanym multi-tester deployment NIE może dołączać wspólnego `runtime-errors.log*`. Diagnostic ZIP nadal zawiera diagnostykę dotyczącą aktualnej bazy i frontend report zgodnie z istniejącym kontraktem.

Runtime log pozostaje dostępny operatorowi/CC po stronie deploymentu. LOCAL_WINDOWS zachowuje dotychczasowe zachowanie jednego użytkownika/jednego logu.

Nie dodawać account_id, nazw testerów ani danych biznesowych do runtime logu tylko po to, aby filtrować ZIP.

## 9. Frontend

Przed wejściem do aplikacji hostowanej użytkownik widzi prosty ekran login + hasło.

Frontend nie przechowuje hasła ani tokenu w `localStorage`/`sessionStorage`; korzysta z cookie HttpOnly.

Po 401/wygaśnięciu sesji wraca do ekranu logowania. Nie tworzyć identity switchera.

Onboarding pozostaje poza scope.

## 10. Model wdrożenia tej fazy

Ten kontrakt dotyczy testowego hostowanego deploymentu z jednym procesem/usługą aplikacji i trwałym wolumenem zawierającym:

- rejestr kont;
- katalog baz testerów;
- istniejące pliki wymagane przez CENTRAL_SERVICE.

Jednoczesne użycie przez kilku testerów jest dopuszczone, ponieważ każdy pracuje na innym pliku SQLite. Ten Task nie obiecuje wieloinstancyjnego/multi-replica dostępu do tego samego pliku SQLite. Skalowanie poziome i Postgres należą do późniejszego T025.

## 11. Acceptance

T24-1. Bez poprawnej sesji chroniony endpoint workspace zwraca 401 i nie otwiera żadnej bazy testera.

T24-2. Poprawne konto A otwiera wyłącznie DB-A; konto B wyłącznie DB-B. Danych utworzonych przez A nie ma w API/backup/diagnostyce B i odwrotnie.

T24-3. Próba podania cudzego `site_id`, `coordinator_id`, nazwy bazy lub zmodyfikowanego cookie nie zmienia mapowania account -> db/coordinator; niedozwolona sesja/request jest odrzucany.

T24-4. Każda mutacja wykonywana jako konto A zapisuje action/audit z `coordinator_id` A, nie `DEV_COORDINATOR_ID`; analogicznie dla B.

T24-5. Wszystkie siedem wskazanych routerów korzysta z jednego request-scoped ownera identity; `DEV_COORDINATOR_ID` nie jest runtime identity hostowanego testera.

T24-6. Hasło w rejestrze nie występuje plaintext; poprawne hasło loguje, błędne nie; response nie ujawnia czy konto istnieje.

T24-7. Cookie jest HttpOnly i w hostowanym HTTPS Secure + SameSite=Lax; expiry po 12h wymaga ponownego loginu; logout unieważnia cookie po stronie klienta.

T24-8. Backup konta A zawiera snapshot DB-A i używa właściwego dla DB-A DEK/recovery metadata; nie odwołuje się do globalnego `DB_PATH` innego konta.

T24-9. Nowa baza testera migruje się istniejącym `connect()` i ma aktywnego Coordinator zgodnego z provisioned `coordinator_id`, bez ręcznego `dev_seed`.

T24-10. CENTRAL_SERVICE może mieć wspólny runtime log operatora, ale tester-facing diagnostic ZIP nie zawiera wspólnego `runtime-errors.log*`; nie ma cross-account leakage przez diagnostics.

T24-11. Dwa równoległe requesty A/B używają właściwych dwóch plików i coordinatorów; context jednego requestu nie przecieka do drugiego.

T24-12. Nie ma zmian w `rota/planning`, solverze ani tabelach domenowych w celu tenancy; nie powstaje `tenant_id` retrofit.

T24-13. Nie powstaje panel admina, samorejestracja, reset hasła, OAuth/SSO, onboarding, Redis ani tabela sesji.

## 12. Literalny TASK_SCOPE

Production — oczekiwany minimalny zakres:

- `api/` nowy mały owner kont/credential verification/session signing;
- `api/deps.py` — request-scoped auth context + DB selection;
- `api/config.py` — zaufany katalog baz/rejestru + `ROTA_SESSION_SECRET`; usunięcie zależności hostowanego runtime od `DEV_COORDINATOR_ID`;
- `api/routers/auth.py` lub równoważny pojedynczy router login/logout/session;
- siedem routerów wskazanych w §5 — tylko mechaniczne pobranie `coordinator_id` z contextu;
- `api/routers/backup.py` — właściwy per-account `db_path` + central diagnostic ZIP bez shared runtime logu;
- `api/dev_seed.py` — tylko jeśli konieczna jest jawna korekta, aby pozostał dev-only; bez użycia go do kont testerów;
- frontend: jeden ekran logowania + wspólna obsługa 401; bez identity switchera;
- provisioning CLI/helper dla ręcznego tworzenia kont;
- testy auth/isolation/backup/concurrency.

Jawnie poza scope:
- `rota/planning/**`, solver i domenowy tenant retrofit;
- Postgres;
- OAuth/SSO;
- self-registration/admin panel/password reset;
- onboarding;
- poziome multi-replica SQLite;
- redesign istniejącego RODO key-management;
- realne dane pracowników w testowym Railway poza osobną decyzją OWNERA.

## 13. Preimplementation re-check Codexa

Sprawdzić wyłącznie:

1. czy podpisane HttpOnly cookie + statyczny/manualny rejestr kont może objąć wszystkie obecne workspace endpointy jednym request contextem bez drugiej ścieżki identity;
2. czy lista miejsc używających `DEV_COORDINATOR_ID` i globalnego `DB_PATH` w request flow jest kompletna dla tego scope (backup/recovery włącznie);
3. czy per-account DB + istniejący CENTRAL_SERVICE KEK tworzy poprawnie osobny DEK per DB bez nowego key-management;
4. czy wyłączenie shared runtime logu z tester-facing diagnostic ZIP w CENTRAL_SERVICE zamyka cross-account leak bez łamania lokalnego T021c/technical-error contract;
5. czy jeden-process + per-tester SQLite na persistent volume jest technicznie spójny dla tej testowej fazy bez zmian persistence/solver;
6. czy literalny scope wystarcza do T24-1..T24-13.

Jeżeli 1–6 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać konkretną brakującą ścieżkę/seam albo sprzeczność; bez projektowania admin panelu, Postgresa lub pełnego systemu IAM.