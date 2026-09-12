# ROTA-RODO-ENCRYPTION-AT-REST — dwa modele wdrożenia i odzyskiwalny backup

STATUS: OWNER_CORRECTED — PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

BASE IMPLEMENTATION: `task/ROTA-RODO-ENCRYPTION-AT-REST@da1982ef933a7543c8c2a1950247bfb50b46dfb7`

SOURCE: OWNER_CORRECTED 2026-09-12 + Codex R2 `task/ROTA-RODO-ENCRYPTION-AT-REST@aea1d8cdccacea5eb2d0bf713bc6baeb07b798bf` + OWNER correction `main@eb106633fcb6fd7bde3ca45604ad7c6f81a116e8`.

## 1. Cel

Naprawić wyłącznie trzy potwierdzone luki obecnej implementacji field-level AES-256-GCM:

1. runtime key management nie może zakładać wyłącznie jednego komputera Windows;
2. backup musi być możliwy do odzyskania po utracie pierwotnej instalacji/komputera bez opierania odzysku na jednym nieodwracalnym haśle użytkownika;
3. uszkodzenie formatu szyfrogramu nie może omijać kontroli integralności i wpadać do ścieżki legacy plaintext.

Nie wracamy do whole-database SQLCipher w tym Tasku. Nie wybieramy konkretnego dostawcy chmurowego ani konkretnego KMS. Nie zmieniamy modelu domeny, solvera ani znaczenia danych pracownika.

RODO/GDPR traktujemy jako obowiązek zastosowania środków proporcjonalnych do ryzyka, a nie jako wymóg zbudowania systemu kryptograficznego, w którym zwykła utrata hasła przez użytkownika nieodwracalnie niszczy dostęp do danych biznesowych.

## 2. Rozdzielenie odpowiedzialności

Warstwa szyfrowania danych, codzienna ochrona klucza runtime i zdolność recovery są trzema osobnymi odpowiedzialnościami.

### 2.1 Data Encryption Key (DEK)

- jeden losowy 256-bitowy DEK szyfruje/dekoduje `Employee.display_name` przez istniejący AES-256-GCM;
- DEK nie jest wyprowadzany ze ścieżki pliku, nazwy komputera, konta użytkownika ani hasła użytkownika;
- format rekordów pozostaje versioned i rozpoznawalny;
- nowe szyfrogramy muszą fail-closed przy uszkodzeniu/tamperingu.

### 2.2 Runtime Key Protector

`pii_crypto` ma korzystać z wąskiej abstrakcji runtime protectora zamiast bezpośrednio zakładać DPAPI albo surowy plik klucza.

W tym Tasku są dokładnie dwa wspierane modele wdrożenia:

A. **LOCAL_WINDOWS**
- DEK jest przechowywany lokalnie wyłącznie w postaci chronionej przez Windows DPAPI;
- DPAPI służy tylko do codziennego uruchomienia tej konkretnej instalacji;
- utrata tej instalacji nie może uniemożliwiać odzyskania danych z prawidłowego backupu, o ile istnieje niezależnie przechowywana zdolność recovery opisana w sekcji 5.

B. **CENTRAL_SERVICE**
- DEK jest chroniony przez zewnętrzny względem pliku DB sekret/KEK runtime przekazany aplikacji przez środowisko wdrożeniowe;
- sekret nie może być zapisany jawnie obok SQLite ani do repozytorium;
- aplikacja przyjmuje już dostarczony sekret/KEK z warstwy deploymentu; nie implementuje własnego cloud vault/KMS;
- brak poprawnego sekretu przy danych zaszyfrowanych = fail closed, bez automatycznego wygenerowania nowego klucza;
- centralna usługa/administrator może posiadać niezależną zdolność odzyskania lub rewrap DEK, dzięki czemu utrata hasła użytkownika aplikacji nie oznacza utraty danych.

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
- co najmniej jedną odzyskiwalną, zaszyfrowaną/wrapped reprezentację DEK;
- niezbędne nie-sekretne metadata algorytmu/wrappingu.

Artefakt backupu NIE może zawierać:
- jawnego DEK;
- DPAPI blobu jako jedynej ścieżki odzyskania;
- central-service runtime secret/KEK;
- jawnego sekretu recovery w tym samym pliku.

Backup nie może wymagać od zwykłego użytkownika pamiętania jednego jedynego sekretu jako warunku przeżycia danych.

## 5. Dwie niezależne zdolności odzyskania

Kontrakt recovery nie jest już modelem „użytkownik podaje passphrase i jeśli ją zgubi, backup przepada”.

### 5.1 LOCAL_WINDOWS

Wariant lokalny musi mieć dwie niezależne ścieżki:

1. **runtime path** — lokalny DEK chroniony przez DPAPI dla codziennego działania;
2. **recovery path** — osobno generowany i osobno przechowywany recovery package/escrow material, który pozwala odzyskać DEK po utracie pierwotnego komputera lub profilu Windows.

Dopuszczalny recovery package może zawierać wrapped DEK + metadata i być chroniony osobnym kluczem recovery, ale:
- nie może być zapisany wyłącznie obok tej samej bazy/na tym samym komputerze;
- użytkownik końcowy nie musi pamiętać nieodwracalnego hasła jako jedynej ścieżki;
- recovery package ma być przeznaczony do przechowania przez administratora organizacji / właściciela instalacji w innym bezpiecznym miejscu;
- recovery package i backup danych mogą być dwoma osobnymi artefaktami, jeśli razem tworzą odzyskiwalny zestaw i nie są współzależne od utraconego DPAPI.

Jeżeli właściciel lokalnej instalacji utraci jednocześnie komputer, backup oraz wszystkie niezależne recovery materiały, silnie zaszyfrowanych danych nie da się odzyskać. Program nie ma udawać, że kryptografia może obejść całkowitą utratę wszystkich sekretów.

### 5.2 CENTRAL_SERVICE

Wariant centralny ma wykorzystywać model typowy dla współczesnej usługi:
- dane są szyfrowane DEK;
- użytkownik aplikacji nie jest jedynym właścicielem zdolności odszyfrowania;
- warstwa usługi/administrator organizacji posiada niezależnie chronioną zdolność unwrap/rewrap DEK;
- reset dostępu/hasła użytkownika nie zmienia samego DEK i nie niszczy danych;
- aplikacja nie implementuje konkretnego KMS ani dostawcy, lecz kontrakt zakłada, że deployment dostarcza runtime/recovery capability oddzielnie od SQLite i od hasła użytkownika.

### 5.3 Granica bezpieczeństwa

Nie wolno:
- przechowywać jawnego DEK w backupie lub recovery package;
- przechowywać raw runtime secret obok DB;
- robić automatycznego „backdoora” w aplikacji, który zwraca plaintext key;
- logować sekretów/recovery material;
- uzależniać odzyskania wyłącznie od jednego hasła użytkownika.

## 6. Co znaczy „odzyskiwalny backup” w tym Tasku

Nie wymagamy nowego pełnego ekranu importu/restore do produktu.

Wymagamy jednak realnego, automatycznie testowalnego recovery primitive po stronie backendu.

Dla LOCAL_WINDOWS:
`backup artifact + niezależny recovery package/material -> odzyskany DEK -> poprawny odczyt Employee.display_name`

Dla CENTRAL_SERVICE:
`backup artifact + niezależnie dostarczona deployment/recovery capability -> odzyskany DEK -> poprawny odczyt Employee.display_name`

Test recovery musi działać po skopiowaniu artefaktów do innego katalogu i przy braku oryginalnego `.pii_keystore`, DPAPI context oraz pierwotnego runtime process secret.

To dowodzi odzyskiwalności bez budowania nowego workflow UI. Osobny produktowy import/restore może powstać później.

## 7. Zachowanie przy starcie / brak klucza

Jeżeli DB zawiera dane w nowym zaszyfrowanym formacie, a runtime protector nie może odzyskać właściwego DEK:
- aplikacja nie generuje nowego DEK i nie kontynuuje jak gdyby baza była nowa;
- odczyt danych fail-closed kontrolowanym błędem konfiguracji/klucza;
- istniejące legacy plaintext-only DB mogą nadal zostać otwarte bez klucza aż do pierwszego zapisu wymagającego szyfrowania, jeśli implementacja potrafi to rozróżnić jednoznacznie.

Nie maskować wrong-key/InvalidTag jako brak danych ani tekst zastępczy.

## 8. Zachowanie użytkownika i dane opuszczające komputer

### LOCAL_WINDOWS
- zwykły użytkownik nadal uruchamia program bez wpisywania hasła szyfrowania;
- przy utworzeniu backupu nie musi wymyślać ani zapamiętywać jedynego recovery password;
- administrator/właściciel instalacji otrzymuje możliwość utworzenia/wyeksportowania recovery package do przechowania poza tym komputerem;
- nic nie jest automatycznie wysyłane do producenta programu ani zewnętrznej chmury w ramach tego Tasku.

### CENTRAL_SERVICE
- użytkownik końcowy nie zarządza DEK/KEK;
- runtime/recovery capability dostarcza środowisko usługi/administrator;
- poza serwer mogą wyjść wyłącznie backup/recovery artefakty w postaci zaszyfrowanej; plaintext DEK i plaintext `display_name` nie są eksportowane jako mechanizm recovery.

## 9. Acceptance

E1. Nowy/zmieniony `Employee.display_name` nie występuje plaintext w pliku SQLite.

E2. LOCAL_WINDOWS: restart tej samej instalacji odczytuje dane z DEK chronionym przez DPAPI.

E3. CENTRAL_SERVICE: poprawny runtime secret/capability pozwala na restart/odczyt; brak lub zły secret nie generuje nowego DEK i kończy się fail-closed.

E4. Non-Windows nie tworzy jawnego `.pii_keystore` jako automatycznego fallbacku centralnej usługi.

E5. LOCAL_WINDOWS: po utracie oryginalnego komputera/DPAPI można odzyskać nazwisko z backupu używając niezależnie przechowanego recovery package/material, bez znajomości nieodwracalnego hasła użytkownika.

E6. CENTRAL_SERVICE: backup można odzyskać przy użyciu niezależnej deployment/recovery capability bez oryginalnego procesu runtime i bez hasła użytkownika aplikacji.

E7. Brak wymaganej recovery capability/material odrzuca recovery kontrolowanie; aplikacja nie zgaduje ani nie generuje nowego DEK.

E8. Zmodyfikowany wrapped DEK / recovery package / metadata krytyczne kryptograficznie są odrzucone.

E9. Zmiana/usunięcie nagłówka/version marker zaszyfrowanej wartości nie może skierować jej do legacy plaintext; wynik = kontrolowany integrity failure.

E10. Prawdziwy legacy plaintext sprzed wdrożenia nadal odczytuje się poprawnie.

E11. Roster/API/druk korzystające z `Employee.display_name` nadal dostają plaintext dopiero po boundary repozytorium; business logic nie dostaje ciphertextu.

E12. Backup/recovery package nie zawiera jawnego DEK ani runtime KEK/secret.

E13. Utrata hasła/logowania użytkownika aplikacji sama w sobie nie niszczy możliwości odzyskania danych, jeśli niezależna recovery capability istnieje.

E14. LOCAL_WINDOWS nie wykonuje automatycznego uploadu recovery package do producenta/chmury.

## 10. Literalny TASK_SCOPE

Production:
- `rota/persistence/pii_crypto.py` — DEK, format ciphertext, runtime protector abstraction, wrapping/recovery primitives;
- `rota/persistence/employee_repository.py` — tylko mechaniczne dostosowanie boundary encrypt/decrypt, jeśli wymagane przez nowy format/API crypto;
- `rota/application/backup.py` — utworzenie przenośnego backup/recovery artefaktu oraz backendowy recovery primitive;
- `api/routers/backup.py` — download backup/recovery artefaktów i minimalne wywołania potrzebne do ich utworzenia; bez pełnego restore UI;
- `frontend/src/api/client.ts` — tylko minimalna obsługa istniejącego przycisku backup/recovery package, jeśli endpoint/response format tego wymaga;
- `frontend/src/screens/Workspace.tsx` — tylko minimalne UI pozwalające pobrać backup i lokalny recovery package oraz jasno poinformować, że recovery package należy przechować osobno; bez nowego systemu kont/hasła;
- `pyproject.toml` — tylko jeżeli potrzebna jest biblioteka już nieobecna w stacku; preferować istniejące `cryptography`/stdlib.

Tests:
- istniejący `tasks/ROTA-RODO-ENCRYPTION-AT-REST/round_01/tests/audit_r1_repro.py` ma zostać zaktualizowany/rozszerzony o oba modele deploymentu i recovery;
- nowe wąskie testy produkcyjne crypto/backup są dozwolone w `tests/` bez symulatorów i benchmarków;
- zachować regresję roster/API oraz legacy plaintext;
- jeden wąski frontend/E2E test może potwierdzić, że LOCAL_WINDOWS pozwala pobrać backup i recovery package bez wymagania nieodwracalnego hasła użytkownika.

Poza scope:
- SQLCipher / szyfrowanie całego pliku DB;
- wybór konkretnego cloud KMS/vault/dostawcy;
- implementacja zewnętrznego recovery service producenta;
- logowanie błędów i ROTA-NO-PERSISTENT-ERROR-LOG;
- nowe konto użytkownika / system resetu hasła;
- pełny UI import/restore;
- solver, planowanie, lifecycle grafiku;
- szyfrowanie PDF/diagnostics, jeśli nie niosą danych osobowych według istniejącego audytu.

Jeżeli implementation wymaga production path poza powyższą listą, CC zatrzymuje pracę i wraca do architekta.

## 11. Preimplementation re-check Codexa

Sprawdzić tylko:
1. czy rozdział DEK / runtime protector / niezależna recovery capability jest implementowalny bez powrotu do SQLCipher;
2. czy LOCAL_WINDOWS = DPAPI runtime + osobny recovery package oraz CENTRAL_SERVICE = externally supplied runtime/recovery capability wystarczają jako dwa modele bez wyboru konkretnego KMS;
3. czy oba modele pozwalają odzyskać dane po utracie zwykłego hasła użytkownika i pierwotnego runtime context, o ile niezależny recovery material/capability istnieje;
4. czy proponowane rozróżnienie legacy plaintext vs encrypted format może naprawić MAGIC downgrade fail-closed;
5. czy literalny TASK_SCOPE obejmuje minimalny frontend potrzebny do pobrania backupu/recovery package bez projektowania nowego systemu kont.

Jeżeli 1–5 = TAK: PASS exact brief SHA i zwolnienie IMPLEMENTATION HOLD. Jeżeli NIE: wskazać wyłącznie konkretną brakującą ścieżkę/konflikt, bez redesignu całego magazynu.