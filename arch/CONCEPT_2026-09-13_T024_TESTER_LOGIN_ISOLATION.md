# CONCEPT 2026-09-13 — T024: login z izolacją danych per tester

STATUS: KONCEPCJA CC — do weryfikacji technicznej Codexa, potem brief architekta.

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

## 2. Kluczowy fakt techniczny (sprawdzony, nie założenie)

`api/deps.py::get_conn()` jest DZIŚ jedynym miejscem w całym programie,
które decyduje, z jaką bazą danych rozmawia request:

```python
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

`DB_PATH` to dziś jedna, stała wartość (`api/config.py`, env
`ROTA_DB_PATH`). Każdy router/aplikacja/warstwa persystencji dostaje już
gotowe `conn` jako parametr — nigdzie indziej `DB_PATH` nie jest
importowane wprost do logiki biznesowej (ta dyscyplina istnieje już od
pracy nad szyfrowaniem RODO). To oznacza: izolacja per-tester wymaga
zmiany DOKŁADNIE tego jednego miejsca — reszta programu (planowanie,
wydruk, szyfrowanie, backup) działa identycznie, bo już dziś zakłada
"jedna baza = jeden kompletny, izolowany świat".

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
3. **Logowanie**: nazwa użytkownika + hasło (albo prostszy kod dostępu —
   do decyzji architekta/Pawła: to nie jest ochrona przed atakiem, tylko
   rozdzielenie testerów). Endpoint `/api/auth/login` weryfikuje,
   wystawia prosty token sesji (podpisany cookie albo bearer token —
   bez OAuth/SSO, "prostszy mechanizm wygrywa", zgodnie ze standardową
   zasadą tego projektu).
4. **`get_conn()` zamienia się na**: odczytaj tożsamość z sesji/tokenu
   requestu → zmapuj na ścieżkę bazy → `connect(that_path)`. Pierwsze
   logowanie danego testera = pierwsze użycie jego pliku bazy;
   `rota.persistence.db.connect()` już dziś sam migruje świeżą/starą
   bazę do aktualnego schematu, więc nowy plik "po prostu działa".
5. **Frontend**: nowy ekran logowania (wizualnie inspirowany
   LynxMask, patrz sekcja 1), zastępujący dzisiejszy tymczasowy,
   zaszyty `DEV_COORDINATOR_ID` (patrz `api/config.py` — jawnie
   opisany jako "interim, pending real authentication").

## 4. Onboarding — otwarta decyzja, nie założenie

Paweł zasygnalizował, że z ekranem logowania może być powiązany jakiś
onboarding. LynxMask ma dobry wzorzec: przy pierwszym uruchomieniu danego
konta pokazuje krótką kartę wprowadzającą (kluczowe punkty + rozwijane
"dowiedz się więcej") zamiast razu wrzucać w pełny interfejs. To osobna
decyzja zakresu — może wejść w ten sam Task, może zostać osobnym,
późniejszym findingiem. Nie zakładam bez potwierdzenia.

## 5. Jawnie POZA zakresem tej koncepcji

- Prawdziwy, produkcyjny system uwierzytelniania (OAuth/SSO, reset
  hasła, rejestracja samoobsługowa) — to zostaje przyszłym T025 F1,
  kiedy Rota przestanie być programem testowym.
- Multi-tenant w jednej bazie (kolumna tenant_id) — odrzucone w sekcji 3
  jako niepotrzebne ryzyko względem prostszej alternatywy.
- Zmiana czegokolwiek w `rota/planning/`, `rota/domain.py` lub logice
  solvera — ten Task nie dotyka niczego poza warstwą api/frontend
  (autoryzacja + wybór pliku bazy).
- Wspólne zarządzanie kluczem szyfrującym RODO między kontami testerów —
  do wyjaśnienia: czy każdy plik bazy testera dostaje własny DEK
  owinięty tym samym centralnym KEK (najprostsza opcja, zgodna z
  istniejącym `pii_crypto.py`), czy coś innego. Zakładam pierwszą
  opcję jako domyślną, do potwierdzenia przez architekta.

## 6. Otwarte pytania dla architekta/Pawła

1. Nazwa użytkownika + hasło, czy prostszy kod dostępu na testera?
2. Token sesji: cookie czy bearer — i jak długo ważny?
3. Onboarding: wchodzi teraz w ten Task, czy osobno?
4. Ile testerów na start (żeby wiedzieć, czy rejestr kont ma być
   plikiem konfiguracyjnym, czy potrzebny mały panel administracyjny)?
5. Czy tester może sam się zarejestrować, czy konta tworzy tylko Paweł
   ręcznie (rekomendacja CC: ręcznie, to program testowy, nie produkt
   z rejestracją)?
