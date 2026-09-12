# ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE — trwałe kopie nazwisk poza `employees`

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASE FINDING: `main@c310e19d941c4aad1eedf8607a8f8ce09d9c9d47`

DEPENDENCY: implementować dopiero na bazie zaakceptowanego/zmargowanego `ROTA-RODO-ENCRYPTION-AT-REST`; ten Task nie zastępuje ani nie rozszerza audytu tamtego Tasku w locie.

## 1. Cel

Zamknąć wyłącznie potwierdzony wyciek `Employee.display_name` do trwałych danych poza `employees.display_name`:

1. `plan_previews.warnings_json` może zawierać prawdziwe nazwisko z `_collect_warnings`;
2. `decision_required_snapshots.payload_json` może zawierać prawdziwe nazwiska w `UnblockingOption.text` budowanym przez `decision_guidance.py`.

Nazwisko ma pozostać dostępne w pamięci/UI/drukowaniu tam, gdzie jest potrzebne operacyjnie, ale nie może być zapisane plaintextem w dodatkowych kolumnach SQLite.

Nie zmieniamy logiki solvera, decyzji biznesowych ani treści widocznej dla koordynatora.

## 2. Decyzja architektoniczna

Nie przenosimy renderowania nazw do frontendu i nie przebudowujemy DTO.

Najwęższe rozwiązanie:
- pozostawić istniejące teksty w `solver.py` i `decision_guidance.py` bez zmian semantycznych;
- szyfrować całe serializowane pola `warnings_json` i `payload_json` na granicy persistence przy zapisie;
- odszyfrowywać je na tej samej granicy przy odczycie;
- użyć tego samego DEK/runtime-protector contract co zaakceptowany `ROTA-RODO-ENCRYPTION-AT-REST`;
- nie tworzyć drugiego klucza ani drugiego systemu key management.

`pii_crypto` powinno udostępnić ogólny, versioned AEAD envelope dla tekstu/JSON (`encrypt_text`/`decrypt_text` lub równoważne), zamiast kopiować algorytm `Employee.display_name` do kolejnych repozytoriów.

## 3. Co pozostaje jawne

Dozwolone są nadal:
- `employee_id` i inne identyfikatory techniczne niebędące nazwiskiem;
- nazwa odszyfrowana w pamięci procesu po odczycie z persistence;
- nazwa pokazana koordynatorowi przez istniejące API/UI;
- nazwa użyta w legalnym wydruku grafiku.

Ten Task dotyczy ochrony **at rest**, nie ukrywania nazwiska przed uprawnionym użytkownikiem programu.

## 4. Istniejące rekordy

Naprawa nie może chronić wyłącznie nowych zapisów.

Po wdrożeniu w istniejącej bazie:
- żaden istniejący `plan_previews.warnings_json` zawierający nazwiska nie może pozostać plaintextem;
- żaden istniejący `decision_required_snapshots.payload_json` zawierający nazwiska nie może pozostać plaintextem.

Wymagana jest jednorazowa, deterministyczna migracja danych wykonywana przed normalną pracą aplikacji.

Dla `decision_required_snapshots` obowiązuje szczególna ostrożność: tabela jest append-only jako reguła biznesowa runtime. Migracja techniczna może przebudować/zakodować istniejące wiersze wyłącznie w kontrolowanej migracji storage, zachowując dokładnie:
- `decision_required_id`;
- `site_id`, `month`, `schedule_version_id`;
- `requested_by`, `recorded_at`;
- semantycznie identyczny payload po odszyfrowaniu.

Nie traktować tej migracji jako zwykłego UPDATE dopuszczonego w runtime i nie osłabiać append-only po zakończeniu migracji.

## 5. Integralność i legacy

- nowe zaszyfrowane JSON-y korzystają z versioned, authenticated envelope z istniejącego kontraktu crypto;
- zły klucz/tampering/malformed ciphertext = fail closed;
- rzeczywisty legacy plaintext sprzed tej migracji może zostać odczytany tylko podczas kontrolowanej migracji danych;
- po zakończeniu migracji runtime nie może cicho akceptować nowego plaintextowego zapisu do chronionych pól.

## 6. Backup/recovery

Ponieważ te pola używają tego samego DEK co `Employee.display_name`:
- istniejący recovery/backup contract z `ROTA-RODO-ENCRYPTION-AT-REST` obejmuje je automatycznie;
- nie tworzyć osobnego recovery package ani osobnego sekretu dla warnings/payload;
- recovery test musi potwierdzić, że po odtworzeniu bazy odszyfrowują się także oba chronione JSON-y.

## 7. Acceptance

L1. PLAN generujący `DAY_SHIFT_OFF-01 SOFT` może nadal zwrócić koordynatorowi tekst z nazwiskiem, ale surowy plik SQLite nie zawiera tego nazwiska w `plan_previews.warnings_json`.

L2. DECISION_REQUIRED z opcją zawierającą nazwisko nadal renderuje ten sam tekst po odczycie, ale surowy SQLite nie zawiera nazwiska w `decision_required_snapshots.payload_json`.

L3. Restart/reload zachowuje dokładnie istniejące warnings i decision payload po odszyfrowaniu.

L4. Tampering obu zaszyfrowanych pól jest odrzucany kontrolowanym integrity failure, nie zwraca częściowego/uszkodzonego JSON-u.

L5. Migracja istniejącej bazy z plaintextowymi `warnings_json` i `payload_json` usuwa plaintext nazwisk z pliku i zachowuje semantycznie te same odczyty.

L6. Migracja zachowuje append-only invariants `decision_required_snapshots`; po migracji zwykły runtime nadal nie może UPDATE/DELETE snapshotów.

L7. Backup/recovery po utracie pierwotnej instalacji odzyskuje i poprawnie odszyfrowuje `Employee.display_name`, `warnings_json` i `payload_json` tym samym odzyskanym DEK.

L8. Solver, blocker classification, unblocking guidance i widoczny tekst dla koordynatora nie zmieniają znaczenia ani kolejności z powodu szyfrowania persistence.

## 8. Literalny TASK_SCOPE

Production:
- `rota/persistence/pii_crypto.py` — ogólny authenticated text/JSON envelope, bez drugiego DEK;
- `rota/persistence/plan_preview_repository.py` — encrypt-on-write/decrypt-on-read `warnings_json`;
- `rota/persistence/site_memory.py` — encrypt-on-write/decrypt-on-read `decision_required_snapshots.payload_json`;
- `rota/persistence/db.py` — wyłącznie wersjonowana migracja istniejących plaintextowych rekordów i zachowanie triggerów/invariants append-only;
- `rota/application/backup.py` — tylko jeśli test recovery wymaga mechanicznego rozszerzenia istniejącego recovery primitive o walidację tych pól; bez nowego formatu backupu.

Tests:
- nowy wąski `tests/test_rodo_display_name_persistence.py`;
- test migracji istniejącej DB;
- istniejące testy plan preview / decision snapshot mogą być aktualizowane tylko mechanicznie pod zaszyfrowany storage;
- reuse istniejącego recovery testu z `ROTA-RODO-ENCRYPTION-AT-REST` z dodatkową asercją na oba JSON-y.

Jawnie poza scope:
- `rota/planning/solver.py` — tekst ostrzeżeń bez zmiany;
- `rota/planning/decision_guidance.py` — treść i logika guidance bez zmiany;
- frontend/API DTO redesign;
- szyfrowanie `employee_id`;
- `coordinators.display_name` — osobny finding/decyzja, nie przemycać do tego Tasku;
- SQLCipher;
- nowy KMS/recovery model;
- solver/planowanie/lifecycle.

Jeżeli implementacja wymaga zmiany treści solver/guidance albo nowego key-management modelu, CC zatrzymuje pracę i wraca do architekta.

## 9. Preimplementation re-check Codexa

Sprawdzić tylko:
1. czy persistence-boundary encryption obu całych JSON-ów zachowuje istniejące DTO/semantykę bez ruszania solvera i `decision_guidance.py`;
2. czy ten sam DEK może być bezpiecznie użyty z odrębnymi nonce/AAD/context labels dla trzech klas danych (`Employee.display_name`, preview warnings, decision payload);
3. czy istniejące plaintextowe rekordy da się zmigrować deterministycznie bez trwałego osłabienia append-only triggerów;
4. czy backup/recovery z poprzedniego Tasku odzyska te pola bez nowego sekretu/formatu;
5. czy literalny scope jest kompletny.

Jeżeli 1–5 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD po spełnieniu dependency. Jeżeli NIE: wskazać konkretną brakującą ścieżkę lub konflikt, bez redesignu solvera/UI.
