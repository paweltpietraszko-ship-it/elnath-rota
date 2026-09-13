# CONCEPT 2026-09-13 — T024: login z izolacją danych per tester

STATUS: KONCEPCJA CC — poprawiona po precheck R1 Codexa (`9a2a018`,
CORRECTION_REQUIRED BEFORE ARCHITECT). Pięć punktów z raportu domkniętych
niżej, oznaczone `[R1-N]`. Gotowa do literalnego re-checku, potem do
architekta.

## 1. Skąd to się wzięło

Paweł, przy okazji T024 (bezpieczne wydanie builda testerom): chce, żeby
każdy tester logował się jako odrębny użytkownik (np. Użytkownik_01,
Użytkownik_02) i miał WŁASNĄ, w pełni izolowaną kopię danych — żadnego
mieszania między testerami na tym samym wdrożeniu Railway.

Zainspirowane pytaniem o `LynxMask Desktop` (`~/Desktop/LynxMask-Desktop`,
GitHub) — sprawdzone bezpośrednio: `LockScreen.tsx` + `OnboardingScreen.tsx`.
Wniosek: mechanizm LynxMask NIE nadaje się do przeniesienia wprost — to
jeden lokalny użytkownik, hasło odszyfrowuje lokalny klucz szyfrujący
(Tauri/Rust `invoke("derive_and_store_key", ...)`), nie jest to logowanie
wieloosobowe na współdzielonym serwerze. Do przejęcia jest WZORZEC
WIZUALNY/UX (karta na środku ekranu, pole hasła z oczkiem, banner błędu,
sprawdzenie "czy to pierwsze uruchomienie" przed pokazaniem onboardingu
zamiast logowania, ekran wprowadzający z rozwijanym "dowiedz się więcej") —
nie kod ani mechanizm bezpieczeństwa.

## 2. Kluczowy fakt techniczny (sprawdzony, skorygowany po `[R1-1]`)

`api/deps.py::get_conn()` jest GŁÓWNYM seamem dla zwykłych endpointów
domenowych — wszystkie pobierają połączenie przez `Depends(get_conn)`,
więc izolacja wyboru bazy dla planowania/wydruku/repozytoriów/solvera nie
wymaga zmian w `rota/planning/`, `rota/domain.py` ani samych
repozytoriach:

```python
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

**To NIE jest jednak jedyne miejsce zależne od `DB_PATH`** (poprzednia
wersja tej koncepcji błędnie tak twierdziła — Codex R1 znalazł to wprost
przez `git grep`):

- `api/routers/backup.py` — backup i pobranie klucza odzyskiwania
  przekazują globalny `DB_PATH` bezpośrednio (`backup_database(conn,
  path, db_path=DB_PATH)`, `create_local_recovery_kit(conn,
  db_path=DB_PATH)`), niezależnie od samego `conn`;
- `api/dev_seed.py` — `def seed(db_path: str = DB_PATH)`, jednorazowy
  skrypt tworzący dev-koordynatora;
- `api/runtime_log.py::resolve_log_dir()` — domyślny katalog logu
  LOCAL_WINDOWS liczony jest względem globalnego `DB_PATH`.

Brief architekta musi jawnie objąć backup/recovery (przekazać wybraną
per-tester ścieżkę bazy zamiast globalnej) oraz rozstrzygnąć, czy
sanitizowany runtime log jest wspólny dla całego wdrożenia (jeden log na
serwer), czy każdy tester ma widzieć tylko swoje wpisy — obie opcje są
uzasadnione, ale to decyzja produktowa, nie techniczna domyślność.
`dev_seed.py` nie jest automatycznym przygotowaniem konta testera — to
osobny, jednorazowy skrypt dev, do którego brief musi dodać nową ścieżkę
inicjalizacji (albo świadomie pozostawić poza zakresem).

## 3. Proponowany mechanizm

1. **Jedna baza SQLite na testera**, nie multi-tenant (kolumna
   tenant_id/user_id w każdej tabeli). Multi-tenant retrofit dotykałby
   całej warstwy persystencji — to dokładnie ten rodzaj ryzyka, którego
   unikamy (patrz decyzja "nie szyfrować całej bazy" przy RODO — tu ta
   sama logika: mniejsza, bezpieczniejsza zmiana zamiast inwazyjnej).
   Osobny plik per tester to naturalne rozszerzenie architektury, którą
   już mamy.
2. **Prosty rejestr użytkownik → ścieżka bazy.** Nowy, mały moduł (np.
   `api/tester_accounts.py`), niezależny od `rota/` (czysto api-layer,
   jak `api/config.py`/`api/runtime_log.py`). Format najpewniej: stała
   lista w konfiguracji/env (np. `ROTA_TESTER_ACCOUNTS` jako JSON, albo
   jeden plik konfiguracyjny) — nie pełny system zarządzania kontami,
   bo to jest program do testów, nie produkcja z rejestracją.
3. **Logowanie**: nazwa użytkownika + hasło, zgodnie z T025 F1
   ("password-based login" — patrz sekcja 3a/5). Endpoint
   `/api/auth/login` weryfikuje, wystawia prosty token sesji (podpisany
   cookie albo bearer token — bez OAuth/SSO, "prostszy mechanizm
   wygrywa", zgodnie ze standardową zasadą tego projektu).
4. **`get_conn()` zamienia się na**: odczytaj tożsamość z sesji/tokenu
   requestu → zmapuj na ścieżkę bazy → `connect(that_path)`. Pierwsze
   logowanie danego testera = pierwsze użycie jego pliku bazy;
   `rota.persistence.db.connect()` już dziś sam migruje świeżą/starą
   bazę do aktualnego schematu, więc nowy plik "po prostu działa".
5. **`[R1-2]` Tożsamość koordynatora, nie tylko baza.** Sam wybór pliku
   bazy w `get_conn()` NIE zastępuje `DEV_COORDINATOR_ID` — ten jest dziś
   importowany i używany bezpośrednio (nie przez `conn`) w siedmiu
   routerach: `bootstrap.py`, `durable_inputs.py`, `export.py`,
   `manual_edit.py`, `rule_decisions.py`, `schedule.py`,
   `site_profile.py`. Bez zmiany tam, każdy tester zapisywałby akcje pod
   tym samym, jednym, zaszytym dev-koordynatorem — nawet mając własną,
   odrębną bazę. `api/config.py` już dziś jawnie opisuje
   `DEV_COORDINATOR_ID` jako "interim... pending real authentication
   (T025 F1)" — do USUNIĘCIA, nie rozszerzenia. Brief musi nazwać jeden
   request-scoped kontekst niosący RAZEM: uwierzytelnione konto, jego
   dozwoloną bazę i właściwy `coordinator_id` (albo opisać równoważną
   izolację) — architekt wybiera minimalny kształt tego kontekstu; ta
   koncepcja go nie przesądza.
6. **Frontend**: nowy ekran logowania (wizualnie inspirowany
   LynxMask, patrz sekcja 1), zastępujący dzisiejszy tymczasowy,
   zaszyty `DEV_COORDINATOR_ID`.

## 3a. `[R1-3]` Ownership: to funkcjonalnie T025 F1/F3, nie pierwotne T024

Istniejący, zatwierdzony dokument (`arch/FINDING_2026-08-22_PWA_HOSTING_PIVOT.md`)
rozdziela to już wcześniej i wprost:

- **T024** = ochrona dystrybucji programu dla testerów (build, NDA);
- **T025 F1** = "Real authentication. Password-based login, replacing
  the no-password coordinator-identity-switcher" — dokładnie to, co
  proponuje ta koncepcja;
- **T025 F3** = "Database strategy for hosted, multi-access use" —
  ten dokument już wskazuje jako jedną z dwóch rozważanych opcji
  "SQLite on a Railway persistent volume" — dokładnie kierunek, który
  proponuje sekcja 3 tutaj.

Ta koncepcja realizuje więc F1+F3 z T025, opakowane w potrzebę T024
(bezpieczne wydanie testerom). To nie jest błąd — to naturalne, że
"bezpieczne wydanie testerom" WYMAGA login+izolacji — ale brief musi to
NAZWAĆ wprost: albo ten wycinek T024 świadomie przejmuje zakres T025
F1/F3 teraz (i T025 zostaje z resztą: F2 już częściowo zrobione przez
istniejące `api/`, ewentualna migracja do Postgres pozostaje później),
albo Paweł decyduje inaczej. Bez tej jawnej decyzji powstałyby dwa
konkurencyjne kontrakty logowania w przyszłości.

## 4. `[R1-4]` Onboarding — USUNIĘTY z zakresu

Poprzednia wersja tej koncepcji trzymała onboarding jako "otwartą
decyzję". Codex R1 słusznie wskazał: onboarding nie jest potrzebny do
logowania ani do izolacji danych i nie ma żadnego zatwierdzonego
zachowania — to niezatwierdzone rozszerzenie zakresu, nie jego część.
Usunięty stąd całkowicie. Wzorzec z LynxMask (karta wprowadzająca przy
pierwszym uruchomieniu konta) zostaje zanotowany jako osobny, późniejszy
pomysł UX — nie wchodzi w brief tego Tasku.

## 5. `[R1-5]` Jawnie POZA zakresem — minimalny rejestr, bez panelu/rejestracji

- Panel administracyjny do zarządzania kontami, samodzielna rejestracja
  testera, reset hasła i rozbudowane zarządzanie kontami — nie wynikają
  z obecnego celu testowego (garstka testerów, konta zakłada Paweł
  ręcznie). Architekt nie dodaje ich bez osobnej decyzji OWNERA.
- Wariant "sam kod dostępu" zamiast prawdziwego hasła — T025 F1 mówi
  wprost o "password-based login". Kod dostępu jako zamiennik jest
  możliwy, ale NIE jest równoważny bez jawnej korekty OWNERA — to
  koncepcja zakłada zwykłe hasło jako domyślne.
- Multi-tenant w jednej bazie (kolumna tenant_id) — odrzucone w sekcji 3
  jako niepotrzebne ryzyko względem prostszej alternatywy.
- Zmiana czegokolwiek w `rota/planning/`, `rota/domain.py` lub logice
  solvera — ten Task nie dotyka niczego poza warstwą api/frontend
  (autoryzacja + wybór pliku bazy + request-scoped coordinator_id).
- Wspólne zarządzanie kluczem szyfrującym RODO między kontami testerów —
  do wyjaśnienia: czy każdy plik bazy testera dostaje własny DEK
  owinięty tym samym centralnym KEK (najprostsza opcja, zgodna z
  istniejącym `pii_crypto.py`), czy coś innego. Zakładam pierwszą
  opcję jako domyślną, do potwierdzenia przez architekta.

Architekt sam wybiera minimalny kształt rejestru kont, sesji i trwałej
lokalizacji plików baz na wolumenie Railway (F3) — ta koncepcja podaje
kierunek (jedna baza SQLite na testera, prosty rejestr), nie gotowy
projekt.

## 6. Otwarte pytania dla architekta/Pawła

1. Token sesji: cookie czy bearer — i jak długo ważny?
2. Ile testerów na start (wpływa na to, czy rejestr kont wystarczy jako
   plik konfiguracyjny, czy trzeba czegoś więcej — bez zakładania
   panelu, patrz sekcja 5)?
3. Czy ten wycinek T024 formalnie przejmuje teraz zakres T025 F1/F3
   (sekcja 3a), czy Paweł chce to rozdzielić inaczej?
4. Wspólny runtime log dla całego wdrożenia, czy per-tester widoczność
   tylko własnych wpisów w pakiecie diagnostycznym (sekcja 2)?
