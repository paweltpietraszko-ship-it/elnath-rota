# TASK_CONTRACT

TASK_ID: ROTA-T011-A
TITLE: Mechaniczne wejścia aplikacyjne — CalendarDay, otwarcie magazynu, historia dostępności
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — T011-A nie zawiera ani
jednego pytania produktowego; wszystkie trzy punkty są powtórzeniem wzorca,
który już istnieje w repo.

INTEGRATED_BASE_SHA: 95717be1682840934252c610ceafc59f9980bf28
BASE_BRANCH_AT_FREEZE: main

TASK_SCOPE:
- rota/application/durable_inputs.py
- rota/application/store.py
- rota/application/availability_matrix.py
- tests/test_t011_a_application_entry_points.py

Powyższa lista jest zamknięta. Zmiana jakiegokolwiek innego pliku produkcyjnego
lub testowego oznacza DIFF_SCOPE FAIL w `backend.py`. `rota/application/store.py`
i plik testowy są jedynymi dwoma nowymi plikami — to dokładnie limit
`MAX_NEW_FILES = 2`, więc nie wolno dodać trzeciego pliku pod żadnym pretekstem.

## ŹRÓDŁA

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znaleziska Z-1, Z-3, Z-7b
  (branch `cursor/audit-pipeline-completeness-d5d7`, commit `a0e4650`).
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — punkty A-1, A-2, A-4
  (branch `cursor/pipeline-closure-proposal-d5d7`, commit `5c2fd3c`).
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §2, §3.
- `tasks/ROTA-T009/brief.md` — operacje 6 i 12, DEPENDENCY BOUNDARY.

UWAGA DLA CODEXA: oba pierwsze źródła nie są jeszcze zmergowane do `main`.
Audyt kontraktu wymaga dostępu do tych gałęzi.

## PROCES — WARUNEK WSTĘPNY BLOKUJĄCY (dotyczy wszystkich części T011)

`backend.py` zwróci dziś `FAIL` dla dowolnej implementacji, niezależnie od jej
jakości, z powodu istniejącego wcześniej rozjazdu `FROZEN.lock`:

- `arch/FROZEN.lock` zawiera `SHA256: 1b23d35c…`, co jest hashem `arch/spec.md`
  **z zakończeniami linii CRLF**;
- `arch/spec.md` w repo ma LF i hashuje się do `9f5f6cfc…` na każdym commicie
  od `0fb5292` do `95717be`;
- treść pliku jest identyczna — różnią się wyłącznie zakończenia linii;
- `check_frozen_lock()` (`backend.py:61-82`) porównuje same hashe, więc zgłasza
  „arch/spec.md modified outside guard" jako blocker → `STATUS: FAIL`;
- niezależnie `guard.py check arch/spec.md` zawodzi jeszcze wcześniej, bo pole
  `FILE:` w locku brzmi `arch\spec.md` (backslash) i na POSIX
  `Path("arch\\spec.md") != Path("arch/spec.md")` (`guard.py:90-92`).

CC NIE naprawia tego w ramach T011-A — `arch/FROZEN.lock` nie jest w TASK_SCOPE
i re-freeze jest decyzją właściciela/architekta, nie implementatora. Warunek
musi być domknięty osobno, przed pierwszym uruchomieniem `backend.py` dla
którejkolwiek części T011.

## PURPOSE

Audyt wykazał, że trzy istniejące prymitywy `rota/persistence/*` nie mają
żadnego wołającego w `rota/application/*`, więc przyszłe UI mogłoby ich użyć
wyłącznie łamiąc zamrożony wymóg „UI nigdy nie zapisuje bezpośrednio do
`rota/persistence/*`" (`OWNER_DECISION_T010…` §2: „Nie ma … bezpośrednich
zapisów UI do repository").

T011-A domyka trzy z nich. Nic poza tym. Zero nowej semantyki, zero nowej
mechaniki, zero decyzji produktowych.

Skutek praktyczny: bez A-1 kompletny kalendarz miesiąca jest nieosiągalny przez
warstwę aplikacji, a `open_month` — operacja czysto odczytowa — rzuca
`IncompleteCalendarData` na świeżej instalacji. Bez A-2 pierwsza czynność
aplikacji (otwarcie/migracja magazynu) wymaga importu `rota.persistence.db`
w UI.

## ANTI-BUREAUCRACY RULE

Obowiązuje lista zakazów z `tasks/ROTA-T009/brief.md:46-66` bez zmian.

Dodatkowo dla T011-A: każdy z trzech punktów to **dosłowne powtórzenie
istniejącego wzorca**, wskazanego niżej z plikiem i zakresem linii. Jeśli
implementacja wymaga czegokolwiek poza tym wzorcem, to znaczy że kontrakt jest
źle napisany — zgłoś to jako finding, nie wymyślaj rozwiązania.

Nie wolno: dodać warstwy pośredniej, klasy serwisowej, rejestru operacji,
własnego typu wyjątku „na zapas", ani DTO wokół `CalendarDay`/
`AvailabilityRecord`.

## DEPENDENCY BOUNDARY

Bez zmian względem `tasks/ROTA-T009/brief.md:68-91`:
`future UI → rota/application → {persistence, planning} → domain`.
Aplikacja nie zawiera SQL ani nazw tabel.

Jeden świadomy wyjątek kształtu, nie kierunku: `open_store` jest jedyną funkcją
aplikacyjną, która nie przyjmuje gotowego `conn`, bo jest jego producentem.
Kierunek zależności pozostaje `application → persistence`.

## ZAKRES — A-1: zapis `CalendarDay`

Moduł docelowy: `rota/application/durable_inputs.py`. Nie nowy modul —
`CalendarDay` jest kolejnym durable input, a docstring tego modułu
(`durable_inputs.py:1-5`) opisuje dokładnie tę odpowiedzialność.

Sygnatura (wiążąca):

```text
def set_calendar_day(conn, *, coordinator_id: str, site_id: str, day: CalendarDay) -> None
```

Wzorzec kopiowany 1:1: `durable_inputs.set_target_hours` (`durable_inputs.py:60-64`).
Jest to jedyny istniejący wrapper zapisujący fakt **nie zakresowany po Site**,
więc jest dokładnie tym samym przypadkiem: `require_active_coordinator_context`,
**brak** `_require_payload_belongs_to_site` (tabela `calendar_days` jest
kluczowana samą datą, `calendar_repository.py:16-19`, więc nie ma czego
porównywać z `site_id`), delegacja do `calendar_repository.save_calendar_day`
(`calendar_repository.py:13`).

Nazwa `set_calendar_day` jest dobrana do słownika modułu: `set_*` dla upsertu
jednego kluczowanego wiersza, w odróżnieniu od `append_*` (łańcuch wersji)
i `update_*` (encja bieżąca).

`site_id` służy wyłącznie autoryzacji koordynatora i nie jest zapisywany —
kalendarz pozostaje globalny, tak jak dziś. Nie wolno tego zmieniać ani dodawać
`site_id` do tabeli.

## ZAKRES — A-2: otwarcie i migracja magazynu

Moduł docelowy: nowy `rota/application/store.py`. Nie `durable_inputs.py`, bo
tam każda funkcja wymaga kontekstu koordynatora, a tu `conn` jeszcze nie
istnieje, więc żadnego kontekstu nie da się sprawdzić.

Sygnatura (wiążąca):

```text
def open_store(db_path: str | Path) -> sqlite3.Connection
```

Wzorzec kopiowany 1:1: `rota/application/backup.py:17-18 backup_database` —
jedyny istniejący wrapper aplikacyjny, który celowo nie woła
`require_active_coordinator_context()` (operacja nie jest per-koordynator)
i deleguje jedną linią. Delegacja: `rota/persistence/db.py:365 connect`, które
samo woła `migrate` (`db.py:370`).

Obsługa błędów: wyjątki przeciekają do wołającego bez tłumaczenia, dokładnie
tak jak `backup.py` pozwala przeciekać `sqlite3.Error`. Dotyczy to w
szczególności `UnsupportedSchemaVersion` (`db.py:26`, rzucane w `db.py:380-384`).
Tłumaczenie tego wyjątku na typ z `rota/application/errors.py` jest osobnym
pytaniem produktowym („co UI ma łapać") i jest **poza zakresem** T011-A.

## ZAKRES — A-4: historia łańcucha dostępności

Moduł docelowy: `rota/application/availability_matrix.py` — moduł jest już
właścicielem read-modelu dostępności jednego pracownika i świadomie nic nie
zapisuje (`availability_matrix.py:14-16`). Nie `memory_read.py`, bo tamten
dotyczy SiteMemory/reguł, a łańcuch dostępności to inna encja.

Sygnatura (wiążąca):

```text
def availability_history(conn, *, availability_id: str) -> list[AvailabilityRecord]
```

Wzorzec kopiowany 1:1: `memory_read.decision_chain_for_rule_family`
(`memory_read.py:23-24`) — jednolinijkowy odczyt bez guardu kontekstu,
zwracający obiekty persistence bez przepakowania. Delegacja:
`availability_repository.get_availability_history` (`:97-102`).

Brak zakresowania po Site jest zgodny z istniejącym
`memory_read.decision_for_rule(conn, *, rule_version_id)` (`memory_read.py:31`).

Zachowanie dla nieznanej rodziny: pusta lista, bo tak działa istniejące
repozytorium (`availability_repository.py:98-102` zwraca listę z pustego
`fetchall()`). Testy to utrwalają; implementacja tego nie zmienia i nie dodaje
wyjątku.

## OUT OF SCOPE

- Źródło dni świątecznych (plik danych / kalendarz lokalny). `arch/spec.md:143`
  (CAL-04) na to pozwala, ale właściciel odłożył tę decyzję: „Źródło dni
  świątecznych (dodatek z W3) — osobna decyzja na później, nie blokuje T011"
  (ROZSTRZYGNIĘCIE B-1). CC nie dodaje żadnego pliku danych ani generatora.
- Atomowe „wypełnij miesiąc" jednym wywołaniem. Właściciel wybrał B-1=W1: zapis
  per dzień, UI woła w pętli. Nie wolno dodawać nowego prymitywu
  `*_in_open_transaction` w `calendar_repository`.
- Tłumaczenie `UnsupportedSchemaVersion` na typ aplikacyjny (patrz A-2).
- Odtwarzanie z backupu — właściciel wybrał B-4=W3 (brak w produkcie).
- Cokolwiek z T011-B/C/D/E.
- UI, IPC, desktop — to T012.

## WYMAGANE TESTY

Jeden nowy plik `tests/test_t011_a_application_entry_points.py`, zwykły pytest
na prawdziwym tymczasowym SQLite. Poniżej scenariusze, nie nazwy funkcji —
nazwy dobiera CC.

1. **Kalendarz przełącza gotowość.** Pełny bootstrap kontekstu + obsada
   wyłącznie funkcjami `rota.application.*`; `month_plan_readiness` zwraca
   `ready=False` z pozycjami `missing CalendarDay for …` dla każdego dnia
   miesiąca; po `set_calendar_day` dla wszystkich dni tego miesiąca zwraca
   `ready=True`.
2. **`open_month` przestaje rzucać.** Ten sam stan przed wypełnieniem
   kalendarza: `open_month` rzuca `IncompleteCalendarData`; po wypełnieniu
   zwraca widok. To dowód, że Z-1 blokowało również operację czysto odczytową.
3. **Upsert, nie duplikat.** Dwukrotny `set_calendar_day` dla tej samej daty
   z różnym `holiday` daje jeden dzień o ostatniej wartości.
4. **Guard kontekstu działa.** `set_calendar_day` bez aktywnej asocjacji
   koordynator–obiekt podnosi `InvalidCoordinatorContext` i nic nie zapisuje.
5. **`open_store` na pustej ścieżce.** Plik powstaje, `PRAGMA user_version`
   równa się `LATEST_SCHEMA_VERSION`, a zwrócone połączenie jest od razu
   użyteczne dla funkcji aplikacyjnych.
6. **`open_store` jest idempotentne.** Ponowne otwarcie tego samego pliku nie
   migruje po raz drugi i nie traci danych zapisanych przed zamknięciem.
7. **Restart bez importu persistence.** Zapis pełnego kontekstu + kalendarza,
   zamknięcie połączenia, `open_store` na tym samym pliku, `month_plan_readiness`
   nadal `ready=True`.
8. **Historia dostępności.** Rodzina z co najmniej dwiema wersjami zapisanymi
   przez `durable_inputs.append_availability` zwraca obie w kolejności łańcucha,
   z ustawionym `supersedes_availability_version_id` na nowszej; nieznana
   rodzina zwraca pustą listę.
9. **Dowód domknięcia granicy.** Ten plik testowy nie importuje niczego z
   `rota.persistence` — ani w kodzie testu, ani w fixture'ach. To jest właściwy
   przedmiot T011-A: cały scenariusz od pustego pliku bazy do `ready=True`
   przechodzi wyłącznie przez `rota.application.*`.

Testu 9 nie wolno spełnić przez import pośredni (np. helper w `tests/support/`,
który sięga do persistence za test).

## ENGINEERING GATES

- istniejąca suite PASS;
- nowe testy T011-A PASS;
- ROTA-REG-001 bez zmian;
- Ruff PASS na plikach z TASK_SCOPE;
- `test_18_dependency_boundary_scan` nadal PASS;
- `SIZE_FILE` (600) i `SIZE_FUNC` (50) PASS — wszystkie pliki w scope są dziś
  poniżej 250 linii, więc to nie jest realne ryzyko.

Oczekiwany, dopuszczalny wynik `backend.py`: `WYMAGA_DECYZJI` na `TOTAL_LINES`,
jeśli suma zmienionych linii przekroczy 150 (`backend.py:254-255`). To nie jest
FAIL i **nie wolno** go obchodzić przez okrojenie wymaganych testów — wymaga
świadomej akceptacji właściciela/architekta.

## ACCEPTANCE

T011-A jest kompletne, gdy wołający znający wyłącznie `rota/application/*`
potrafi: otworzyć/utworzyć magazyn, doprowadzić wskazany miesiąc do
`ready=True`, otworzyć ten miesiąc do odczytu i odczytać historię jednej
rodziny dostępności — nie importując `rota.persistence` ani nie znając SQLite.

Trzy znaleziska audytu zamknięte: Z-1 (zapis kalendarza), Z-3 (otwarcie
magazynu), Z-7b (historia dostępności).

## REVIEW REQUEST TO CODEX

Audytuj ten kontrakt wyłącznie pod kątem:
1. sprzeczności z zamrożoną architekturą i zaakceptowanym T004-T010;
2. realnej dwuznaczności, która zmusiłaby CC do wymyślania zachowania;
3. testowalności scenariuszy z sekcji WYMAGANE TESTY;
4. wycieku zakresu do T011-B/C/D/E lub do T012;
5. przypadkowej biurokracji — czy którykolwiek z trzech punktów nie jest
   w rzeczywistości kopią wskazanego wzorca.

Zwróć osobno ocenę, czy warunek wstępny `FROZEN.lock` jest opisany
wystarczająco, żeby nie zablokować implementacji po cichu.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
