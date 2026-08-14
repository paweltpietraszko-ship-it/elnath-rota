# AUDYT KOMPLETNOŚCI PIPELINE'U — 2026-08-14

Rola: audytor (Elnath Rota). Raport zawiera wyłącznie fakty o brakach — bez
projektowania, bez propozycji nazw funkcji/sygnatur, bez sekcji rekomendacji.
Decyzja, co i jak zamknąć, należy do architekta/właściciela.

Stan repo w chwili audytu: `main` @ `0fb5292` ("Merge ROTA-T010: Panel Sterowania
configuration foundation (A/B/C/D)").

Metoda: dwa przejścia opisane w briefie audytu. Weryfikacja statyczna (grep po
całym repo, z pominięciem `tasks/*/round_*`, `diffs/`, `.worktrees/`) oraz
runtime — skryptami jednorazowymi poza repo, wywołującymi wyłącznie funkcje
`rota/application/*`. Nie oceniano logiki solvera.

---

## PRZEJŚCIE 1 — pełny wynik (każda funkcja zapisu w `rota/persistence/*`)

Wszystkie prymitywy zapisu znalezione przez wyszukanie prefiksów
`save_*`/`write_*`/`append_*`/`record_*`/`activate_*` **oraz** przez niezależne
wyszukanie instrukcji `INSERT`/`UPDATE`/`DELETE` w `rota/persistence/*` (żeby nie
przeoczyć zapisu o innej nazwie).

| prymityw zapisu (persistence) | wołający w `rota/application/*` |
|---|---|
| `availability_repository.append_availability_version` | `durable_inputs.append_availability` |
| `employee_repository.save_employee` | `durable_inputs.update_employee` |
| `employee_repository.save_site_membership` | `durable_inputs.update_membership` |
| `employee_repository.write_site_membership_in_open_transaction` | `training.save_site_membership` |
| `employee_repository.save_external_support_window` | `durable_inputs.add_external_support_window` (upsert po `window_id`, więc pokrywa też edycję/dezaktywację) |
| `work_balance_repository.save_work_balance_target` | `durable_inputs.set_target_hours` |
| `site_profile_repository.save_site_profile` | `durable_inputs.update_site_profile` |
| `site_profile_repository.write_site_profile_in_open_transaction` | `bootstrap.bootstrap_or_resume_coordinator_context` |
| `site_repository.write_site_in_open_transaction` | `bootstrap.bootstrap_or_resume_coordinator_context` |
| `coordinator_repository.write_coordinator_in_open_transaction` | `bootstrap.bootstrap_or_resume_coordinator_context` |
| `coordinator_repository.activate_association_if_not_already_active_in_open_transaction` | `bootstrap._activate_association_or_raise` |
| `decision_ledger.record_decision` | `rule_decisions.record_structured_rule_decision` |
| `site_rule_repository.insert_site_rule_version`, `ensure_rule_family` | tylko przez `record_decision` (celowo) |
| `schedule_lifecycle.create_schedule_version` | `plan_ops`, `manual_edit` |
| `schedule_lifecycle.replace_working_snapshot` | `plan_ops.select_candidate`, `lifecycle_ops.revalidate` |
| `schedule_lifecycle.finalize_schedule_version` | `lifecycle_ops.finalize` |
| `schedule_lifecycle.restore_schedule_version` | `lifecycle_ops.restore` |
| `backup_repository.backup_to` | `backup.backup_database` |
| **`calendar_repository.save_calendar_day`** | **BRAK — tylko `tests/`** |
| **`site_repository.save_site`** | **BRAK — tylko `tests/`** |
| **`coordinator_repository.save_coordinator`** | **BRAK — tylko `tests/`** |
| **`coordinator_repository.save_coordinator_site_association`** | **BRAK — tylko `tests/`** |
| **`coordinator_repository.write_coordinator_site_association_in_open_transaction`** | **BRAK — nikt, nawet testy** |
| **`db.connect` / `db.migrate` / `db.init_schema`** (DDL + `PRAGMA user_version`) | **BRAK — tylko `tests/`** |

---

## ZNALEZISKA

### Z-1. Brak jakiejkolwiek funkcji aplikacyjnej zapisującej `CalendarDay` (potwierdzenie przykładu z briefu, z nowym dowodem)

**Dowód.** `rota/persistence/calendar_repository.py:13 save_calendar_day` nie ma
ani jednego odwołania w `rota/application/*`; wszystkie 14 plików wołających leży
w `tests/` (m.in. `tests/support/t009_fixtures.py:34`,
`tests/test_t010_bootstrap_roster.py:71`). Warstwa aplikacji zna wyłącznie
odczyt: `rota/application/assembler.py:28,89` i `rota/application/bootstrap.py:41,212`
(`list_calendar_days`). Skanowanie publicznych funkcji `rota/application/*` po
nazwie zwraca jedynie prywatny helper odczytu `assembler._assemble_calendar`.
Docstring samego repozytorium (`calendar_repository.py:2-3`) mówi wprost, że
tabela istnieje „for a later application-layer caller" — ten caller nigdy nie
powstał. Dowód runtime: po pełnym bootstrapie wykonanym wyłącznie funkcjami
aplikacyjnymi `month_plan_readiness` zwraca `ready=False` z 30 pozycjami
`missing CalendarDay for 2026-09-01…`, a poza `save_calendar_day` z persistence
nie ma czym tych 30 rekordów zapisać.

**Dlaczego blokuje UI.** Blokuje nie tylko `plan_month`, ale też **operację 1,
czyli sam odczyt miesiąca**: `open_month` przechodzi przez
`assembler._assemble_calendar` (`assembler.py:86-96`), które rzuca
`IncompleteCalendarData`. Potwierdzone runtime:
`rota.application.errors.IncompleteCalendarData: missing CalendarDay for 2026-09-01`.
Świeża instalacja zatrzymuje się więc na ekranie „otwórz miesiąc", a nie dopiero
na przycisku PLAN, i koordynator nie ma tej ściany jak przebić bez sięgnięcia do
`rota/persistence/`.

### Z-2. Po pierwszym udanym bootstrapie warstwa aplikacji nie ma żadnego zapisu `Site`, `Coordinator` ani `CoordinatorSiteAssociation`

**Dowód.** `site_repository.save_site` (`:40`),
`coordinator_repository.save_coordinator` (`:32`) i
`save_coordinator_site_association` (`:77`) mają zero odwołań w
`rota/application/*`. Warianty `*_in_open_transaction` są osiągalne wyłącznie z
`bootstrap.bootstrap_or_resume_coordinator_context` (`bootstrap.py:110-124`),
które na wejściu rzuca `CoordinatorContextAlreadyActive`, gdy
`_has_active_association` jest prawdą (`bootstrap.py:102-106`). `durable_inputs`
obejmuje `Employee`, `SiteMembership`, `ExternalSupportWindow`, `target_hours` i
`SiteProfile` (`durable_inputs.py:29-74`), ale nie ma polecenia dla `Site`,
`Coordinator` ani asocjacji. Dodatkowo
`activate_association_if_not_already_active_in_open_transaction`
(`coordinator_repository.py:82-108`) ma w SQL
`WHERE coordinator_site_associations.active = 0`, więc potrafi wyłącznie
przestawić `0 → 1`, nigdy `1 → 0`. Dowód runtime: ponowne wywołanie bootstrapu z
samą zmienioną nazwą Site kończy się
`CoordinatorContextAlreadyActive: ('C-1', 'S-1') already has an active context; use the T009 authorized edit operations instead`
— a wśród tych operacji T009 nie ma żadnej dotyczącej Site/Coordinator/asocjacji.

**Dlaczego blokuje UI.** To drzwi w jedną stronę: po bootstrapie UI nie może
zmienić nazwy obiektu ani go zdezaktywować, nie może zdezaktywować ani przenieść
koordynatora, nie może odebrać uprawnienia (asocjacji), nie może przestawić
`Site.profile_id` na inny profil. Dotyczy to też scenariusza drugiego obiektu
zapowiedzianego w `bootstrap.py:12-17` (Panel Sterowania / T012):
`update_site_profile` wymaga `profile.profile_id == owning_site.profile_id`
(`durable_inputs.py:67-74`), więc jedyną ścieżką powstania wiersza nowego
`SiteProfile` jest bootstrap, a bootstrap odmawia przy aktywnym kontekście.

### Z-3. Brak aplikacyjnego punktu wejścia otwierającego/migrującego bazę

**Dowód.** `rota/persistence/db.py:365 connect` i `:374 migrate` wykonują realne
zapisy schematu (DDL oraz `PRAGMA user_version` w `db.py:385-402`), a wyszukanie
`connect`, `migrate` i `init_schema` w `rota/application/*` nie zwraca ani
jednego trafienia. Każda funkcja aplikacyjna przyjmuje już otwarte `conn` jako
pierwszy parametr (np. `open_month.open_month(conn, *, site_id, month)`,
`plan_ops.plan_month(conn, ...)`).

**Dlaczego blokuje UI.** Pierwsza czynność aplikacji desktopowej — otwarcie/
utworzenie lokalnego magazynu, wykonanie migracji, obsługa
`UnsupportedSchemaVersion` (`db.py:26,380-384`) — jest dziś wykonalna tylko przez
bezpośredni import `rota.persistence.db`, czyli przez wywołanie zapisujące
schemat w warstwie, do której UI nie wolno zapisywać. Nie istnieje aplikacyjne
opakowanie, przez które ten krok mógłby przejść.

### Z-4. Brak aplikacyjnego odczytu, który pozwala odkryć istniejących koordynatorów, obiekty i profile

**Dowód.** `coordinator_repository.list_coordinators` (`:48`),
`site_repository.list_sites` (`:55`),
`site_profile_repository.list_site_profile_ids` (`:127`) oraz
`coordinator_repository.list_associations_for_site` (`:120`) mają zero odwołań w
`rota/application/*`. `list_associations_for_coordinator` jest używane tylko
wewnętrznie jako straż w `context.py:35` i `bootstrap.py:69` i nigdy nie jest
zwracane na zewnątrz. Wszystkie 34 publiczne funkcje `rota/application/*` (pełna
inwentaryzacja wykonana runtime) wymagają, by `coordinator_id` i `site_id` były
już znane wołającemu.

**Dlaczego blokuje UI.** Nie da się zbudować ekranu startowego: UI nie ma czym
wylistować, kto i jakie obiekty istnieją, żeby koordynator mógł wybrać kontekst,
ani czym rozstrzygnąć „pokazać kreator pierwszej konfiguracji czy wejść w
istniejący kontekst" bez uprzedniej znajomości identyfikatorów, których nie ma
skąd wziąć.

### Z-5. Backup jest jednokierunkowy — nigdzie w repo nie istnieje odtworzenie z pliku backupu

**Dowód.** `rota/application/backup.py:17 backup_database` woła
`backup_repository.py:11 backup_to`, a `backup_repository.py` zawiera wyłącznie
`backup_to` i `diagnostics_payload`. Wyszukanie definicji
`def .*(restore|import|load)` w `rota/persistence` + `rota/application` zwraca
tylko `lifecycle_ops.restore` i `schedule_lifecycle.restore_schedule_version`
(przestawienie wskaźnika current dla `ScheduleVersion`, rzecz zupełnie inna niż
plik backupu) oraz prywatne `site_rule_repository._load_parameters`.
`tasks/ROTA-T009/brief.md:329-336` specyfikuje tylko kierunek zapisu backupu.

**Dlaczego blokuje UI.** Ostatni krok łańcucha koordynatora jest połowiczny: UI
potrafi wytworzyć kopię `.sqlite`, ale nie ma żadnego wywołania aplikacyjnego,
które by ją wczytało po utracie danych czy przy zmianie maszyny. Odtworzenie jest
dziś operacją poza programem (ręczna podmiana pliku), a nie funkcją, którą UI
może wystawić.

### Z-6. Brak aplikacyjnego odczytu narastającego salda kwartalnego

**Dowód.** `work_balance_repository.py:68 reconstruct_quarter_balance` ma zero
odwołań w `rota/application/*`. Jedyny wystawiony odczyt salda,
`assembler._assemble_work_balances` (`assembler.py:121-128`), woła
`reconstruct_month_balance` bez argumentu `quarter_balance_before`, którego
wartością domyślną jest `0` (`work_balance_repository.py:57`, `balance.py:57`).
Przy zerowym przeniesieniu `compute_month_balance` zwraca
`quarter_balance == unresolved_carryover == month_balance` (`balance.py:84-93`).

**Dlaczego blokuje UI.** `open_month` zawsze pokazuje miesiąc w izolacji: pola
`quarter_balance` i `unresolved_carryover` w zwracanym `WorkBalance` nigdy nie
zawierają narastającego salda kwartału, mimo że to właśnie ten sygnał
`arch/spec.md` (cytowany w `balance.py:3-9`) przypisuje odpowiedzialności
koordynatora. UI nie ma czym pokazać nadgodzin do oddania w następnym okresie
inaczej niż przez `rota/persistence/`.

### Z-7. Krok „odczyt historii" nie ma dwóch odczytów: enumeracji miesięcy z danymi i historii łańcucha dostępności

**Dowód.** (a) Enumeracja miesięcy nie istnieje na **żadnej** warstwie:
wyszukanie `DISTINCT` w całym `rota/persistence` nie zwraca nic, a
`schedule_repository.py:100 list_schedule_versions` wymaga konkretnej pary
`(site_id, month)`; `open_month.open_month` również przyjmuje jeden konkretny
`month`. (b) `availability_repository.py:97 get_availability_history` (historia
wersji jednej rodziny `availability_id`) ma zero odwołań w `rota/application/*`;
`availability_matrix.employee_availability_matrix` zwraca tylko rekordy bieżące i
aktywne, dodatkowo zawężone do trzech rodzajów
(`availability_matrix.py:30-32,58-61`), a `open_month` wystawia wyłącznie
aktualne aktywne rekordy (`assembler.py:105-118`).

**Dlaczego blokuje UI.** UI nie ma czym zbudować nawigacji po historii — nie może
pokazać listy miesięcy, dla których cokolwiek zaplanowano, bo musiałoby zgadywać
miesiące i pytać o każdy z osobna. Nie może też pokazać łańcucha zmian jednego
wpisu dostępności (kto i kiedy skrócił urlop, która wersja co zastąpiła), mimo że
sam zapis takiej zmiany jest wystawiony przez `durable_inputs.append_availability`.

---

## PRZEJŚCIE 2 — pełny łańcuch pracy koordynatora

| krok | funkcja w `rota/application/*` | stan |
|---|---|---|
| otwarcie/utworzenie bazy | — | **luka Z-3** |
| wybór koordynatora/obiektu | — | **luka Z-4** |
| bootstrap kontekstu | `bootstrap.bootstrap_or_resume_coordinator_context` | jest |
| profil obiektu / zmiany | `durable_inputs.update_site_profile` | jest |
| edycja `Site` / `Coordinator` / asocjacji | — | **luka Z-2** |
| obsada | `durable_inputs.update_employee`, `update_membership`, `add_external_support_window`, `bootstrap.current_roster` | jest |
| kalendarz miesiąca | — | **luka Z-1** |
| reguły | `rule_decisions.record_structured_rule_decision` | jest |
| dostępność | `durable_inputs.append_availability`, `availability_matrix.employee_availability_matrix` | jest |
| godziny docelowe | `durable_inputs.set_target_hours` | jest |
| sprawdzenie gotowości | `bootstrap.coordinator_context_completeness`, `month_plan_readiness`, `precheck.precheck` (na `assembler.assemble_planning_state`) | jest |
| otwarcie miesiąca | `open_month.open_month` | jest, ale nieosiągalne bez Z-1 |
| PLAN | `plan_ops.plan_month` | jest |
| wybór kandydata | `plan_ops.select_candidate` | jest |
| ręczne korekty | `manual_edit.apply_manual_correction`, `freeze_or_unfreeze`, `mark_not_worked`, `training.mark_training_realized` | jest |
| REPLAN | `plan_ops.replan` | jest |
| rewalidacja i odchylenia | `lifecycle_ops.revalidate` + `assembler.assemble_planning_state` (`state.deviations`) | jest |
| finalizacja | `lifecycle_ops.finalize` | jest |
| przywrócenie wersji | `lifecycle_ops.restore` | jest |
| odczyt konkretnej wersji historycznej | `assembler.assemble_planning_state(schedule_version_id=...)` | jest |
| historia reguł / decyzji | `memory_read.*` (5 funkcji) | jest |
| historia: lista miesięcy, łańcuch dostępności | — | **luka Z-7** |
| saldo kwartalne | — | **luka Z-6** |
| backup i ZIP diagnostyczny | `backup.backup_database`, `build_diagnostic_zip` | jest |
| odtworzenie z backupu | — | **luka Z-5** |

Dowód, że kalendarz jest jedyną luką w rdzeniu łańcucha planowania: po zasianiu
30 rekordów `CalendarDay` bezpośrednio przez `save_calendar_day` (tak jak robią
to testy) reszta przeszła runtime bez potknięcia — `month_plan_readiness.ready=True`,
`open_month` OK, `plan_month` → `FEASIBLE` z 1 kandydatem, `select_candidate` →
`WORKING`, `revalidate` → `WORKING`, `finalize` → `FINAL_NO_DEVIATIONS`.

---

## POZOSTAŁE FAKTY ZAOBSERWOWANE PRZY AUDYCIE (nie luki funkcjonalne — sygnalizacja, bez działania)

1. `rota/application/training.py:24 save_site_membership` jest publiczną funkcją
   warstwy aplikacji, która zapisuje `SiteMembership` **bez**
   `require_active_coordinator_context()` i wymaga już otwartej transakcji;
   docstring (`training.py:25-31`) mówi, że istnieje jako punkt do podmiany w
   testach. Z punktu widzenia UI jest nieodróżnialna od autoryzowanego polecenia
   — obok istnieje strażowana `durable_inputs.update_membership`.
2. `rota/application/__init__.py` i `rota/persistence/__init__.py` mają 0 bajtów
   — nie ma kuratorowanej listy API aplikacji; granica jest konwencją. Jedyny
   test granic (`tests/test_t009_lifecycle_memory_backup_boundary.py:156-181`)
   sprawdza `planning ↛ persistence/application` oraz `persistence ↛ application`,
   a dla `rota/application` weryfikuje tylko brak importów `tkinter/PyQt/react`.
   Nic nie wykrywa zapisu do `rota/persistence/*` z przyszłego UI.
3. `OpenMonthView` (`open_month.py:26-37`) nie zawiera pól `assignments`,
   `shift_demands` ani `deviations`, więc samą siatkę grafiku UI musi brać z
   `assembler.assemble_planning_state`. To nie luka (assembler jest w warstwie
   aplikacji), ale odczyt nazwany w briefie „read-model dla UI" nie zawiera
   treści grafiku.
4. `site_memory.decision_fate`, `site_memory.effective_rule_on` i
   `site_rule_repository.get_site_rule_version` nie mają wołających w
   `rota/application/*`; zakres operacji 11 z `tasks/ROTA-T009/brief.md:319-327`
   jest jednak pokryty przez `memory_read` bez nich.
