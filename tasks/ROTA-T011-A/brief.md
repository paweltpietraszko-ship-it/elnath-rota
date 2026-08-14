# TASK_CONTRACT

TASK_ID: ROTA-T011-A
TITLE: Mechaniczne wejścia aplikacyjne — CalendarDay, otwarcie magazynu, historia dostępności
STATUS: DRAFT FOR CODEX AUDIT — ROUND 2 (po FAIL round 1)
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — T011-A nie zawiera ani
jednego pytania produktowego; wszystkie trzy punkty są powtórzeniem wzorca,
który już istnieje w repo.

INTEGRATED_BASE_SHA: 029107be9045d2759e77450a0fb943a04483932c
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

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znaleziska Z-1, Z-3, Z-7b.
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — punkty A-1, A-2, A-4.
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §2, §3.
- `tasks/ROTA-T009/brief.md` — operacje 6 i 12, DEPENDENCY BOUNDARY.

Wszystkie źródła są na `main` od `029107b`, więc audyt kontraktu nie wymaga
dostępu do żadnej gałęzi roboczej.

## PROCES — BRAMKA MECHANICZNA: STAN POTWIERDZONY (dotyczy wszystkich części T011)

Wcześniejsza wersja tego briefu opisywała blokadę niezależną od T011:
`arch/FROZEN.lock` trzymał `SHA256` policzony z `arch/spec.md` w wersji CRLF,
więc `check_frozen_lock()` (`backend.py:61-82`) zgłaszał „arch/spec.md modified
outside guard" jako blocker i `backend.py` zwracał `FAIL` dla dowolnej
implementacji; niezależnie `guard.py check` zawodził na polu
`FILE: arch\spec.md` (backslash) na POSIX (`guard.py:90-92`).

Naprawione poza zakresem T011 (`20f08f9`, zmergowane w `0175d71`): dodane
`.gitattributes` (`* text=auto eol=lf`), hash przeliczony na kanonicznej treści
LF, `guard.py` zapisuje `FILE:` przez `.as_posix()`.

Zweryfikowane na `029107b` przed wydaniem tej wersji briefu:
`python3 guard.py check arch/spec.md` → `STATUS: PASS`, `SHA256:
9f5f6cfce906a0d506c019a4637a59303a190aeaf95c9deccb8cb4dcb4306b97`;
`backend.check_frozen_lock()` → brak blockera.

`arch/FROZEN.lock` pozostaje poza TASK_SCOPE każdej części T011. Jeśli
`FROZEN_LOCK` zgłosi cokolwiek podczas implementacji, jest to NOWY problem —
zgłoś go, nie obchodź i nie przeliczaj locka samodzielnie.

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
5. **`open_store` na pustej ścieżce daje działający, aktualny schemat.** Plik
   powstaje, a na zwróconym połączeniu przechodzi pełna sekwencja aplikacyjna:
   bootstrap kontekstu, zapis obsady, `set_calendar_day` i
   `month_plan_readiness`. Dowodem migracji jest to, że operacje wymagające
   aktualnego schematu działają — **nie** odczyt `PRAGMA user_version` i **nie**
   porównanie z `LATEST_SCHEMA_VERSION`.

   Uzasadnienie tego kształtu (FINDING A-1, round 1): `LATEST_SCHEMA_VERSION`
   istnieje wyłącznie w `rota.persistence.db`, a `PRAGMA user_version` wymaga
   surowego SQL na połączeniu. Każda z tych dróg przeczyłaby punktowi 9 i
   ACCEPTANCE tego samego briefu. Kontrakt wybiera dowód pośredni i **nie
   dopuszcza** wyjątku dla `PRAGMA` — CC nie ma tu wyboru między naruszeniem
   granicy a pominięciem asercji.

   Odrzucenie bazy o schemacie nowszym niż binarka (`UnsupportedSchemaVersion`)
   jest już pokryte istniejącym testem na poziomie persistence
   (`tests/test_local_store_schema_migration.py:81`) i **nie jest** duplikowane
   w T011-A: zbudowanie takiej bazy wymaga zapisu `PRAGMA user_version`, czyli
   dokładnie tego, czego ten plik testowy nie robi.
6. **`open_store` jest idempotentne w obserwowalny sposób.** Dane zapisane przez
   funkcje aplikacyjne przed zamknięciem połączenia są w całości widoczne po
   ponownym `open_store` na tym samym pliku, a ponowne otwarcie niczego nie
   psuje ani nie zeruje. Kontrakt **nie** wymaga dowodu „nie migrowało po raz
   drugi" — bez odczytu wersji schematu jest to nieobserwowalne, a samo
   `migrate` pomija już zastosowane kroki (`db.py:385-387`).
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

## ZMIANY PO AUDYCIE KONTRAKTU — ROUND 1

Raport: `tasks/ROTA-T011-A/round_01/tests/tests_r1.txt` (werdykt FAIL, jeden
finding, audytowany SHA `7670b2d`).

**FINDING A-1 — zamknięty.** Wymóg testowy nr 5 żądał sprawdzenia
`PRAGMA user_version == LATEST_SCHEMA_VERSION`, co było sprzeczne z punktem 9 i
ACCEPTANCE tego samego briefu, bo obie te wartości są dostępne wyłącznie przez
`rota.persistence` lub surowy SQL. Punkt 5 został przepisany na dowód pośredni
(operacje aplikacyjne wymagające aktualnego schematu), z jawnym zakazem wyjątku
dla `PRAGMA`; punkt 6 stracił nieobserwowalny wymóg „nie migrowało po raz
drugi"; odrzucenie nowszego schematu wskazano jako już pokryte istniejącym
testem persistence, zamiast duplikować je tutaj.

Reszta raportu round 1 była PASS i nie wymagała zmian: zakres A-1/A-2/A-4,
zgodność z CAL-01/CAL-04, brak SQL w application, realny TASK_SCOPE.

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
