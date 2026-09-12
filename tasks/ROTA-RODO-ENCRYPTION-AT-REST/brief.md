# ROTA-RODO-ENCRYPTION-AT-REST — dwa modele wdrożenia i odzyskiwalny backup

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

BASE IMPLEMENTATION: `task/ROTA-RODO-ENCRYPTION-AT-REST@da1982ef933a7543c8c2a1950247bfb50b46dfb7`

SOURCE: OWNER_CORRECTED 2026-09-12 + Codex R2 `task/ROTA-RODO-ENCRYPTION-AT-REST@aea1d8cdccacea5eb2d0bf713bc6baeb07b798bf`.

## 1. Cel

Naprawić wyłącznie trzy potwierdzone luki obecnej implementacji field-level AES-256-GCM:

1. runtime key management nie może zakładać wyłącznie jednego komputera Windows;
2. backup musi być możliwy do odzyskania po utracie pierwotnej instalacji/komputera;
3. uszkodzenie formatu szyfrogramu nie może omijać kontroli integralności i wpadać do ścieżki legacy plaintext.

Nie wracamy do whole-database SQLCipher w tym Tasku. Nie wybieramy konkretnego dostawcy chmurowego ani konkretnego KMS. Nie zmieniamy modelu domeny, solvera ani znaczenia danych pracownika.

## 2. Rozdzielenie odpowiedzialności

Warstwa szyfrowania danych i warstwa ochrony klucza są oddzielne.

### 2.1 Data Encryption Key (DEK)

- jeden losowy 256-bitowy DEK szyfruje/dekoduje `Employee.display_name` przez istniejący AES-256-GCM;
- DEK nie jest wyprowadzany ze ścieżki pliku, nazwy komputera, konta użytkownika ani innego identyfikatora środowiska;
- format rekordów pozostaje versioned i rozpoznawalny;
- nowe szyfrogramy muszą fail-closed przy uszkodzeniu/tamperingu.

### 2.2 Runtime Key Protector

`pii_crypto` ma korzystać z wąskiej abstrakcji runtime protectora zamiast bezpośrednio zakładać DPAPI albo surowy plik klucza.

W tym Tasku są dokładnie dwa wspierane modele wdrożenia:

A. **LOCAL_WINDOWS**
- DEK jest przechowywany lokalnie wyłącznie w postaci chronionej przez Windows DPAPI;
- DPAPI służy tylko do codziennego uruchomienia tej konkretnej instalacji;
- utrata tej instalacji nie może uniemożliwiać odzyskania danych z prawidłowego backupu.

B. **CENTRAL_SERVICE**
- DEK jest chroniony przez zewnętrzny względem pliku DB sekret runtime przekazany aplikacji przez środowisko wdrożeniowe;
- sekret nie może być zapisany jawnie obok SQLite ani do repozytorium;
- aplikacja przyjmuje już dostarczony sekret/KEK z warstwy deploymentu; nie implementuje własnego cloud vault/KMS;
- brak poprawnego sekretu przy danych zaszyfrowanych = fail closed, bez automatycznego wygenerowania nowego klucza.

Nie dodawać trzeciego automatycznego fallbacku typu „raw key file na non-Windows”.

## 3. Format szyfrogramu i integralność

Obecne rozpoznanie `MAGIC` nie może pozwalać na downgrade ciphertext -> legacy plaintext przez zmianę/usunięcie prefiksu.

Nowy zapis ma być jednoznacznie versioned i authenticated:
- metadata potrzebne do identyfikacji wersji są objęte AEAD/AAD albo format ma taki rozdział typów, że uszkodzony ciphertext nie może zostać potraktowany jako legacy plaintext;
- legacy plaintext pozostaje czytelny wyłącznie wtedy, gdy wartość rzeczywiście ma legacy typ/format zaakceptowany przed wdrożeniem szyfrowania;
- malformed/tampered encrypted value ma kończyć się kontrolowanym błędem integralności;
- żadnego `errors="replace"` dla danych, które mogą być uszkodzonym ciphertextem.

Nie jest wymagany rewrite wszystkich starych plaintext rows podczas startu. Migracja może pozostać write-on-touch zgodnie z obecną implementacją, o ile odczyt legacy jest jednoznaczny i bezpieczny.

## 4. Backup — niezależny od runtime keystore

`POST /workspace/backup` nie może już zwracać samego `.db`, jeżeli odtworzenie danych wymaga zewnętrznego runtime key material.

Backup ma być jednym przenośnym artefaktem, np. kontenerem ZIP, zawierającym co najmniej:
- snapshot SQLite;
- wersję formatu backupu;
- zaszyfrowany/wrapped DEK potrzebny do odtworzenia danych;
- niezbędne nie-sekretne metadata algorytmu/KDF/wrappingu.

Artefakt backupu NIE może zawierać:
- jawnego DEK;
- DPAPI blobu jako jedynej ścieżki odzyskania;
- central-service runtime secret/KEK;
- sekretu odzyskiwania w tym samym pliku.

## 5. Recovery secret

Backup ma mieć własny sekret odzyskiwania niezależny od runtime protectora.

Kontrakt:
- przy tworzeniu backupu DEK jest dodatkowo wrapped pod recovery key;
- recovery key powstaje z jawnie dostarczonego sekretu odzyskiwania/passphrase przy użyciu współczesnego password KDF dostępnego w istniejącym stacku kryptograficznym (preferowany `scrypt`; parametry zapisane w metadata backupu);
- salt jest losowy i zapisany w backupie;
- passphrase/recovery secret nigdy nie jest zapisywany w DB, backupie, logach ani diagnostyce;
- błędny sekret odzyskiwania albo zmodyfikowany backup = kontrolowany błąd integralności, nigdy częściowy odczyt;
- ten sam format recovery działa dla LOCAL_WINDOWS i CENTRAL_SERVICE.

Nie projektować kont użytkowników, resetu hasła ani escrow. OWNER nie wybrał żadnego zewnętrznego recovery service.

## 6. Co znaczy „odzyskiwalny backup” w tym Tasku

Nie wymagamy nowego pełnego ekranu importu/restore do produktu.

Wymagamy jednak realnego, automatycznie testowalnego recovery primitive po stronie backendu:

`backup artifact + recovery secret -> SQLite snapshot + odzyskany DEK -> poprawny odczyt Employee.display_name`

Test recovery musi działać po skopiowaniu artefaktu do innego katalogu i przy braku oryginalnego `.pii_keystore`, DPAPI context oraz runtime central-service secret.

To dowodzi odzyskiwalności bez budowania nowego workflow UI. Osobny produktowy import/restore może powstać później.

## 7. Zachowanie przy starcie / brak klucza

Jeżeli DB zawiera dane w nowym zaszyfrowanym formacie, a runtime protector nie może odzyskać właściwego DEK:
- aplikacja nie generuje nowego DEK i nie kontynuuje jak gdyby baza była nowa;
- odczyt danych fail-closed kontrolowanym błędem konfiguracji/klucza;
- istniejące legacy plaintext-only DB mogą nadal zostać otwarte bez klucza aż do pierwszego zapisu wymagającego szyfrowania, jeśli implementacja potrafi to rozróżnić jednoznacznie.

Nie maskować wrong-key/InvalidTag jako brak danych ani tekst zastępczy.

## 8. Acceptance

E1. Nowy/zmieniony `Employee.display_name` nie występuje plaintext w pliku SQLite.

E2. LOCAL_WINDOWS: restart tej samej instalacji odczytuje dane z DEK chronionym przez DPAPI.

E3. CENTRAL_SERVICE: poprawny runtime secret pozwala na restart/odczyt; brak lub zły secret nie generuje nowego DEK i kończy się fail-closed.

E4. Non-Windows nie tworzy jawnego `.pii_keystore` jako automatycznego fallbacku centralnej usługi.

E5. Backup jest jednym artefaktem i po przeniesieniu do innego katalogu można odzyskać nazwisko używając tylko artefaktu + poprawnego recovery secret.

E6. Recovery z E5 działa bez oryginalnego DPAPI context, bez oryginalnego runtime keystore i bez central-service runtime secret.

E7. Zły recovery secret odrzuca recovery bez plaintext/częściowego wyniku.

E8. Zmodyfikowany wrapped DEK / metadata krytyczne kryptograficznie są odrzucone.

E9. Zmiana/usunięcie nagłówka/version marker zaszyfrowanej wartości nie może skierować jej do legacy plaintext; wynik = kontrolowany integrity failure.

E10. Prawdziwy legacy plaintext sprzed wdrożenia nadal odczytuje się poprawnie.

E11. Roster/API/druk korzystające z `Employee.display_name` nadal dostają plaintext dopiero po boundary repozytorium; business logic nie dostaje ciphertextu.

E12. Backup nie zawiera jawnego DEK, runtime KEK/secret ani recovery passphrase.

## 9. Literalny TASK_SCOPE

Production:
- `rota/persistence/pii_crypto.py` — DEK, format ciphertext, runtime protector abstraction, wrapping/recovery primitives;
- `rota/persistence/employee_repository.py` — tylko mechaniczne dostosowanie boundary encrypt/decrypt, jeśli wymagane przez nowy format/API crypto;
- `rota/application/backup.py` — utworzenie przenośnego recovery artefaktu i backendowy recovery primitive;
- `api/routers/backup.py` — download nowego pojedynczego artefaktu oraz przyjęcie recovery secret do utworzenia backupu; bez pełnego restore UI/endpointu, chyba że Codex wykaże mechanicznie, że testowalnego recovery primitive nie da się inaczej wystawić;
- `pyproject.toml` — tylko jeżeli potrzebna jest biblioteka już nieobecna w stacku; preferować istniejące `cryptography`/stdlib.

Tests:
- istniejący `tasks/ROTA-RODO-ENCRYPTION-AT-REST/round_01/tests/audit_r1_repro.py` ma zostać zaktualizowany/rozszerzony o oba modele deploymentu i recovery;
- nowe wąskie testy produkcyjne crypto/backup są dozwolone w `tests/` bez symulatorów i benchmarków;
- zachować regresję roster/API oraz legacy plaintext.

Poza scope:
- SQLCipher / szyfrowanie całego pliku DB;
- wybór konkretnego cloud KMS/vault/dostawcy;
- logowanie błędów i ROTA-NO-PERSISTENT-ERROR-LOG;
- nowe konto użytkownika / recovery service / escrow;
- pełny UI import/restore;
- solver, planowanie, lifecycle grafiku;
- szyfrowanie PDF/diagnostics, jeśli nie niosą danych osobowych według istniejącego audytu.

Jeżeli implementation wymaga production path poza powyższą listą, CC zatrzymuje pracę i wraca do architekta.

## 10. Preimplementation re-check Codexa

Sprawdzić tylko:
1. czy rozdział DEK / runtime protector / recovery wrapping jest implementowalny bez powrotu do SQLCipher;
2. czy LOCAL_WINDOWS = DPAPI i CENTRAL_SERVICE = externally supplied runtime secret wystarczają jako dwa modele bez wyboru konkretnego KMS;
3. czy jeden backup artifact + recovery secret może dowieść odzyskania na nowej instalacji bez oryginalnego runtime protector context;
4. czy proponowane rozróżnienie legacy plaintext vs encrypted format może naprawić MAGIC downgrade fail-closed;
5. czy literalny TASK_SCOPE jest kompletny.

Jeżeli 1–5 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać wyłącznie konkretną brakującą ścieżkę/konflikt, bez redesignu całego magazynu.