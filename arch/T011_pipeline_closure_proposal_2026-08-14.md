# TASK_CONTRACT (PROPOZYCJA — NIE JEST JESZCZE BRIEFEM DO IMPLEMENTACJI)

PROPOSAL_ID: ROTA-T011-PROPOSAL
TITLE: Domknięcie luk pipeline'u Z-1..Z-9 — warstwa application jako jedyne wejście dla UI
STATUS: PROPOSAL_AWAITING_OWNER_DECISIONS
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (ta tura — projektant, NIE implementator)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes (grupa B poniżej)

BASE_SHA: 0fb5292e97488008586378c93b1f823d1619b2ac (`main`, "Merge ROTA-T010: Panel
Sterowania configuration foundation (A/B/C/D)")

## CZYM JEST TEN DOKUMENT

Kontynuacja audytu `AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md`
(commit `8f137b4590fcd06d06096182a9501256ee419d63`, branch
`cursor/audit-pipeline-completeness-d5d7`), znaleziska Z-1..Z-7.

To jest projekt domknięcia, nie implementacja. W tej turze świadomie nie powstał
żaden kod produkcyjny ani test — rozdzielenie projektanta (ten dokument) od
implementatora (CC) i audytora (Codex) jest zasadą procesu, nie formalnością.

Dokument NIE jest gotowym briefem. Staje się nim dopiero po odpowiedzi
właściciela na pytania z grupy B; dopóki ich nie ma, część zakresu jest
nierozstrzygnięta i CC nie ma czego implementować w tych punktach.

Dokument nie jest też zamrożony. `arch/FROZEN.lock` obejmuje wyłącznie
`arch/spec.md`; ten plik jest propozycją i ewentualne zamrożenie (`guard.py
freeze`) to osobna decyzja po akceptacji.

## UWAGA O WZORCU FORMY

Prośba mówiła „wzorowany na `tasks/ROTA-T010/brief.md`". Tego pliku nie ma w
repo: `tasks/ROTA-T010/` zawiera wyłącznie `repo_before.hash` i
`round_01/tests/tests_r{3..10}.txt`. Nie ma też
`tasks/ROTA-T010/part_a_bootstrap_roster.md` ani `part_b_availability.md` /
`part_d_nn.md`, mimo że docstringi w `rota/application/bootstrap.py:1-2`,
`availability_matrix.py:1-2` i `manual_edit.py:92` się do nich odwołują.
Formę wzorowałem więc na `tasks/ROTA-T009/brief.md`, który w repo jest
(TASK_CONTRACT / PROCESS GATE / PURPOSE / ANTI-BUREAUCRACY RULE /
DEPENDENCY BOUNDARY / zakres / OUT OF SCOPE / ACCEPTANCE).

## PROCESS GATE

1. Właściciel odpowiada na pytania zamknięte B-1..B-7.
2. Architekt (osobna sesja) przepisuje ten dokument na brief(y) per task,
   z rozstrzygniętymi decyzjami.
3. Codex audytuje brief przed implementacją.
4. CC implementuje dopiero po `PASS / READY_FOR_IMPLEMENTATION`.

Grupa A (T011-A) nie zawiera ani jednego pytania otwartego i może wejść do
osobnego briefu natychmiast, niezależnie od odpowiedzi na B.

## PURPOSE

Audyt wykazał, że silnik i warstwa trwałości są kompletne, a niekompletna jest
**powierzchnia wywołań dla UI**: część istniejących prymitywów `rota/persistence/*`
nie ma żadnego wołającego w `rota/application/*`, więc dziś UI mogłoby po nie
sięgnąć tylko łamiąc zamrożony wymóg „UI nigdy nie zapisuje bezpośrednio do
`rota/persistence/*`".

Celem T011 jest domknięcie tej powierzchni **bez** dodawania nowej mechaniki.
Większość braków to powtórzenie wzorca, który już istnieje w repo. Reszta to
decyzje produktowe, których projektant nie ma prawa podjąć za właściciela.

## ANTI-BUREAUCRACY RULE

Obowiązuje bez zmian lista zakazów z `tasks/ROTA-T009/brief.md:46-66`
(brak command bus / mediatora / event sourcingu / workflow engine / DI /
macierzy uprawnień / DTO-kopii każdej encji / osobnej klasy use-case na przycisk).

T011 nie wprowadza żadnego nowego mechanizmu. Każdy punkt grupy A to
**dosłowne powtórzenie istniejącego wzorca**, ze wskazanym plikiem i zakresem
linii, z którego kopiuje się kształt 1:1. Jeśli jakiś punkt wymaga wymyślenia
nowej mechaniki, to znaczy że został źle zaklasyfikowany i należy do grupy B.

## DEPENDENCY BOUNDARY

Bez zmian względem `tasks/ROTA-T009/brief.md:68-91`. Kierunek:
`future UI → rota/application → {persistence, planning} → domain`.
Aplikacja nie zawiera SQL ani nazw tabel.

Wyjątek do świadomego przyjęcia: A-2 (otwarcie bazy) jest jedyną funkcją
aplikacyjną, która nie przyjmuje gotowego `conn`, bo jest jego producentem.
To nie łamie kierunku zależności — nadal `application → persistence`.

## OBSERWOWANA KONWENCJA, KTÓREJ TRZYMA SIĘ CAŁA GRUPA A

Fakty odczytane z kodu, nie propozycje:

- **Zapisy inicjowane przez koordynatora** zaczynają się od
  `require_active_coordinator_context(conn, coordinator_id=..., site_id=...)`
  i delegują jedną linią — `rota/application/durable_inputs.py:29-74`
  (6 funkcji, wszystkie w tym kształcie).
- **Zapisy dotyczące danych nie zakresowanych po Site** pomijają
  `_require_payload_belongs_to_site`, bo nie mają czego porównać:
  `durable_inputs.set_target_hours` (`durable_inputs.py:60-64`) zapisuje
  `work_balance_targets` kluczowane `(employee_id, month)`, bez `site_id`.
- **Odczyty nie wołają guardu kontekstu w ogóle** — ani `open_month.open_month`,
  ani żadna z 5 funkcji `memory_read.py`, ani
  `availability_matrix.employee_availability_matrix`, ani
  `bootstrap.current_roster`, ani `assembler.assemble_planning_state`.
- **Cienki moduł przekazujący** jest w tym repo dopuszczoną formą:
  `rota/application/backup.py` (2 funkcje) i `rota/application/memory_read.py`
  (5 funkcji) nie robią nic poza delegacją.
- **Odczyt zwracający encje domenowe po liście pośredniej** ma wzorzec w
  `bootstrap.current_roster` (`bootstrap.py:234-240`): pobierz listę powiązań,
  zmapuj każdą na encję przez `get_*`, zwróć `tuple[...]`.

---

# GRUPA A — MECHANICZNE (bez decyzji produktowej)

Dla każdego punktu: co ma powstać, moduł docelowy, dokładna sygnatura, wzorzec
kopiowany 1:1, warunek uznania za zamknięte. Ciał funkcji celowo nie ma —
pisze je CC.

## A-1 (zamyka Z-1, część mechaniczna) — zapis `CalendarDay`

**Co ma powstać.** Jedna funkcja aplikacyjna zapisująca jeden `CalendarDay`,
żeby koordynator mógł oznaczyć dzień jako świąteczny/nieświąteczny bez sięgania
do `rota/persistence/`.

**Moduł docelowy.** `rota/application/durable_inputs.py` — nie nowy moduł.
`CalendarDay` jest kolejnym „durable input", a docstring tego modułu
(`durable_inputs.py:1-5`) opisuje dokładnie tę odpowiedzialność: „thin commands
for existing durable facts needed by the coordinator workflow".

**Sygnatura.**

```text
def set_calendar_day(conn, *, coordinator_id: str, site_id: str, day: CalendarDay) -> None
```

**Wzorzec kopiowany 1:1.** `durable_inputs.set_target_hours`
(`rota/application/durable_inputs.py:60-64`). To jedyny istniejący wrapper
zapisujący fakt **nie zakresowany po Site**, więc jest dokładnie tym samym
przypadkiem: guard kontekstu, brak `_require_payload_belongs_to_site` (nie ma
`day.site_id` do porównania — tabela `calendar_days` jest kluczowana samą datą,
`rota/persistence/calendar_repository.py:16-19`), delegacja do
`save_calendar_day` (`calendar_repository.py:13`).

Nazwa `set_calendar_day` jest dobrana do istniejącego słownika modułu:
`set_target_hours` dla upsertu jednego kluczowanego wiersza, w odróżnieniu od
`append_*` (łańcuch wersji) i `update_*` (encja bieżąca).

**Warunek zamknięcia.** `bootstrap.month_plan_readiness` przechodzi z
`ready=False` na `ready=True` po 28-31 wywołaniach tej funkcji, a wołający nie
importuje `rota.persistence`. Dowód regresji dla audytora: przed zmianą
`open_month.open_month` na niewypełnionym miesiącu rzuca
`rota.application.errors.IncompleteCalendarData` (`assembler.py:93-94`, ścieżka
`assembler.py:188`).

**Czego A-1 świadomie NIE rozstrzyga.** Skąd biorą się dni świąteczne i czy
„wypełnij miesiąc" jest jedną transakcją — to B-1.

## A-2 (zamyka Z-3) — otwarcie/migracja lokalnego magazynu

**Co ma powstać.** Jedna funkcja aplikacyjna otwierająca (i tworząca, gdy nie
istnieje) lokalny magazyn wraz z migracją schematu, żeby pierwsza czynność
aplikacji nie wymagała importu `rota.persistence.db` po stronie UI.

**Moduł docelowy.** Nowy, mały `rota/application/store.py`. Nie
`durable_inputs.py`, bo tam każda funkcja wymaga kontekstu koordynatora, a tu
`conn` jeszcze nie istnieje, więc żadnego kontekstu nie da się sprawdzić.

**Sygnatura.**

```text
def open_store(db_path: str | Path) -> sqlite3.Connection
```

**Wzorzec kopiowany 1:1.** `rota/application/backup.py:17-18 backup_database` —
jedyny istniejący wrapper aplikacyjny, który celowo nie woła
`require_active_coordinator_context()` (operacja nie jest per-koordynator) i
deleguje jedną linią do persistence. Delegacja: `rota/persistence/db.py:365
connect`, które samo woła `migrate` (`db.py:370`).

**Warunek zamknięcia.** Skrypt/UI potrafi dojść od „ścieżka pliku" do
`bootstrap.bootstrap_or_resume_coordinator_context` bez ani jednego importu z
`rota.persistence`.

**Opcjonalne pytanie, jeśli właściciel chce je otworzyć (domyślnie NIE).**
`UnsupportedSchemaVersion` (`db.py:26`, rzucane w `db.py:380-384`) w wariancie
1:1 z `backup.py` przecieka do wołającego jako wyjątek persistence — tak samo
jak `backup.py` pozwala przeciekać `sqlite3.Error`. Gdyby miał być tłumaczony na
typ z `rota/application/errors.py`, to przestaje być kopią wzorca i staje się
osobnym pytaniem produktowym „co UI ma łapać". Nie rozstrzygam tego sam.

## A-3 (zamyka Z-4, część mechaniczna) — odczyty odkrywające kontekst

**Co ma powstać.** Dwa odczyty pozwalające zbudować ekran startowy: kto istnieje
jako koordynator i w które obiekty dany koordynator może wejść.

**Moduł docelowy.** `rota/application/bootstrap.py` — ten moduł już mieści
odczyty rozpoznające kontekst (`coordinator_context_completeness`,
`month_plan_readiness`, `current_roster`), a jego docstring
(`bootstrap.py:19-23`) wprost opisuje „dwa odczyty, dwa znaczenia" jako własną
odpowiedzialność.

**Sygnatury.**

```text
def known_coordinators(conn) -> tuple[Coordinator, ...]
def sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]
```

**Wzorzec kopiowany 1:1.** `bootstrap.current_roster` (`bootstrap.py:234-240`):
odczyt bez guardu kontekstu, mapujący listę powiązań na encje przez `get_*`,
zwracający `tuple[...]`. `known_coordinators` deleguje do
`coordinator_repository.list_coordinators` (`:48`). `sites_for_coordinator`
składa `list_associations_for_coordinator` (`:111`) z `site_repository.get_site`
(`:45`) — dokładnie tak, jak `current_roster` składa
`list_memberships_for_site` z `get_employee`.

**Warunek zamknięcia.** UI potrafi odpowiedzieć „pokazać kreator pierwszej
konfiguracji czy listę obiektów" nie znając z góry żadnego identyfikatora.

**Czego A-3 świadomie NIE rozstrzyga.** Czy te odczyty filtrują po
`active` i po powiązaniu — to B-3. Sygnatury są od tej decyzji niezależne,
zmienia się wyłącznie treść ciał.

## A-4 (zamyka Z-7, część b) — historia łańcucha dostępności

**Co ma powstać.** Jeden odczyt zwracający pełny łańcuch wersji jednej rodziny
`availability_id` (kto i kiedy zmienił wpis, która wersja co zastąpiła).

**Moduł docelowy.** `rota/application/availability_matrix.py` — moduł już jest
właścicielem read-modelu dostępności jednego pracownika i świadomie nic nie
zapisuje (`availability_matrix.py:14-16`). Historia jest tym samym tematem.
Nie `memory_read.py`, bo tamten modul dotyczy SiteMemory/reguł, a łańcuch
dostępności to inna encja.

**Sygnatura.**

```text
def availability_history(conn, *, availability_id: str) -> list[AvailabilityRecord]
```

**Wzorzec kopiowany 1:1.** `memory_read.decision_chain_for_rule_family`
(`memory_read.py:23-24`) — jednolinijkowy odczyt bez guardu, zwracający obiekty
z persistence bez przepakowania. Delegacja:
`availability_repository.get_availability_history` (`:97`).
Brak zakresowania po Site jest zgodny z istniejącym
`memory_read.decision_for_rule(conn, *, rule_version_id)` (`memory_read.py:31`),
który też nie przyjmuje `site_id`.

**Warunek zamknięcia.** Dla rodziny, w której `durable_inputs.append_availability`
zapisał ≥2 wersje, UI dostaje obie z relacją `supersedes_availability_version_id`,
bez importu `rota.persistence`.

## A-5 (zamyka Z-6 w wariancie minimalnym) — odczyt salda kwartalnego

**Co ma powstać.** Jeden odczyt zwracający `WorkBalance` dla każdego miesiąca
jednego kwartału, z realnym narastającym saldem.

**Moduł docelowy.** Nowy, mały `rota/application/balance_read.py`, wzorowany
kształtem na całym `memory_read.py` (cienki moduł odczytów bez guardu).

**Sygnatura.**

```text
def quarter_balance(conn, *, employee_id: str, quarter_first_month: date) -> list[WorkBalance]
```

**Wzorzec kopiowany 1:1.** `memory_read.effective_rules_for_month`
(`memory_read.py:13-16`) — deleguje do funkcji persistence i zwraca jej wynik
bez zmiany kształtu, z docstringiem mówiącym, że to „to samo źródło prawdy".
Delegacja: `work_balance_repository.reconstruct_quarter_balance` (`:68`).

**Warunek zamknięcia.** UI potrafi pokazać narastające saldo kwartału i
`unresolved_carryover` bez importu `rota.persistence`.

**Zależność.** A-5 realizuje **wariant W1 pytania B-5**. Jeśli właściciel wybierze
W2, dochodzi zmiana w `assembler._assemble_work_balances` i A-5 przestaje być
całością domknięcia Z-6.

---

# GRUPA B — DECYZYJNE (pytania zamknięte dla właściciela)

Nie proponuję rozwiązania. Dla każdego pytania: warianty i ich konsekwencje
oparte na kodzie, oraz co konkretnie jest zablokowane do czasu odpowiedzi.

## B-1 (Z-1, część decyzyjna) — jak powstaje kompletny kalendarz miesiąca?

Kontekst: `plan_month` wymaga kompletnego miesiąca, a `month_plan_readiness`
raportuje braki per dzień (`bootstrap.py:213-216`). `save_calendar_day` otwiera
własną transakcję na każde wywołanie (`calendar_repository.py:14`).
`arch/spec.md:143` (CAL-04) dopuszcza jako źródło zarówno wiersze `CalendarDay`,
jak i deterministyczne lokalne źródło, w tym dołączony plik danych;
`arch/spec.md:142` (CAL-01) wymaga tylko reprodukowalności po restarcie.

- **W1 — tylko zapis per dzień (A-1), UI wypełnia pętlą.**
  Konsekwencje: zero nowych prymitywów w persistence. Częściowo wypełniony
  miesiąc jest normalnym stanem pośrednim i już dziś jest poprawnie raportowany.
  Przerwana pętla nie tworzy niespójności — tylko „miesiąc niegotowy".
  Koszt: to UI musi wiedzieć, które dni są świętami, czyli wiedza kalendarzowa
  ląduje w warstwie, w której nie chcemy logiki produktowej.
- **W2 — dodatkowo aplikacyjne „wypełnij miesiąc" w jednej transakcji.**
  Konsekwencje: wymaga NOWEJ funkcji persistence w kształcie
  `*_in_open_transaction` (dla kalendarza takiej nie ma) i `with conn:` po
  stronie aplikacji — wzorzec istnieje w `bootstrap.py:110-124`. Zysk:
  „wypełnij miesiąc" jest atomowe. Koszt: pierwszy przypadek, gdy aplikacja
  steruje transakcją dla zwykłego durable input (dziś robią to tylko bootstrap i
  hook readiness w `training._build_readiness_hook`), czyli rozszerzenie
  wzorca, nie jego kopia.
- **W3 — W1 albo W2 plus dołączone do repo źródło dni świątecznych.**
  Konsekwencje: koordynator nie odklikuje 30 dni ręcznie; CAL-01 nadal
  spełnione, bo źródłem prawdy pozostaje tabela, a plik jest tylko wsadem.
  Koszt: nowy artefakt danych do utrzymania (kolejne lata, zmiany prawa) i
  pytanie, kto go aktualizuje; dodatkowo `PlanningEngine` nadal nie może czytać
  pliku (CAL-04 zakazuje), więc wsad musi przejść przez aplikację.

Zablokowane do decyzji: istnienie i kształt operacji „wypełnij miesiąc" oraz to,
czy powstaje nowy prymityw w `calendar_repository`.

## B-2 (Z-2) — co znaczy „edytować" i „dezaktywować" Site oraz Coordinator?

Kontekst: `Site`/`Coordinator` są w T008 opisane jako „MUTABLE CURRENT-STATE
ENTITIES" (`coordinator_repository.py:1-2`) i zapisywane zwykłym upsertem
(`site_repository.py:21-38`). Po bootstrapie żadna funkcja aplikacyjna ich nie
dotyka, a `CoordinatorSiteAssociation` fizycznie nie może wrócić z `active=1` do
`0`, bo jedyny dostępny zapis ma `WHERE ... active = 0`
(`coordinator_repository.py:105`).

- **W1 — zwykły upsert, jak każdy inny durable input.**
  Nowe funkcje w `durable_inputs` w kształcie `update_employee` /
  `update_membership`. Konsekwencje: najtańsze i spójne z modelem T008.
  Koszt: historia nazwy i aktywności przepada bezpowrotnie; istniejące
  `ScheduleVersion.created_by` i `applied_rule_version_ids` będą wskazywać na
  koordynatora/obiekt, którego opis się zmienił, bez śladu jaki był w chwili
  planowania.
- **W2 — wersjonowanie jak `SiteRuleVersion` / Decision Ledger (append-only).**
  Konsekwencje: pełna historia „kto, kiedy, dlaczego zmienił obiekt", spójna z
  tym, jak repo traktuje reguły i dostępność. Koszt: to nie jest cienki wrapper,
  a zmiana modelu T008 — nowe tabele i migracja (dziś `sites`/`coordinators`
  mają PK bez wersji), plus drugie źródło prawdy o „bieżącym" Site, które
  musiałyby respektować wszystkie istniejące wywołania `get_site`
  (`context.py:29`, `bootstrap.py:156`, `assembler.py:186`,
  `durable_inputs.py:69`, `training.py:122`).
- **W3 — rozdzielić: nazwa = upsert (jak W1), a dezaktywacja/odebranie
  asocjacji = osobna jawna operacja z warunkiem wstępnym.**
  Konsekwencje: da się zablokować dezaktywację obiektu, który ma otwartą wersję
  WORKING, więc nie osieroci się grafiku w trakcie planowania. Fakt na plus:
  historia pozostaje czytelna po dezaktywacji, bo odczyty w tym repo w ogóle nie
  wołają `require_active_coordinator_context` (potwierdzone dla `open_month`,
  `memory_read.*`, `availability_matrix`, `assembler`). Koszt: trzeba
  rozstrzygnąć, czy zdezaktywowany Site ma być tylko do odczytu i co z jego
  FINAL-ami.

Pytanie sprzężone, bez którego W3 nie ma czym zadziałać: **czy przejście
`CoordinatorSiteAssociation.active: 1 → 0` ma być w ogóle możliwe?** Dziś SQL
tego nie dopuszcza, i to nie jest przeoczenie — komentarz przy
`activate_association_if_not_already_active_in_open_transaction`
(`coordinator_repository.py:85-94`) opisuje ten warunek jako celową ochronę
przed wyścigiem dwóch bootstrapów.

## B-3 (Z-4, część decyzyjna) — co dokładnie widzi ekran startowy?

- **W1 — surowo wszystko, bez filtra.** Konsekwencje: widać też nieaktywne i
  porzucone obiekty; aplikacja nie zawiera żadnej polityki. Koszt: UI musi
  filtrować samo, czyli polityka trafia dokładnie tam, gdzie jej nie chcemy.
- **W2 — tylko aktywne i tylko powiązane** (`Coordinator.active`, `Site.active`,
  `association.active`). Konsekwencje: lista pokazuje dokładnie to, w co można
  wejść, bez martwych wierszy. Koszt: obiekt zdezaktywowany znika bezpowrotnie z
  UI i nie ma jak go odzyskać — sprzężenie z B-2/W3.
- **W3 — dwa jawne odczyty: „w co mogę wejść" (filtrowane) i „co istnieje"
  (pełne, dla panelu administracyjnego / T012).** Konsekwencje: każdy odczyt ma
  jedno znaczenie, bez flag boolowskich w sygnaturze. Koszt: dwie funkcje
  zamiast jednej i konieczność zdecydowania, czy pełny odczyt ma jakiekolwiek
  ograniczenie dostępu (dziś odczyty nie mają żadnego).

Zablokowane do decyzji: treść ciał funkcji z A-3.

## B-4 (Z-5) — co znaczy „odtworzyć z backupu"?

Kontekst: `backup.backup_database` → `backup_repository.backup_to` używa API
backupu SQLite; w całym repo nie istnieje żadna funkcja odwrotna.
`tasks/ROTA-T009/brief.md:329-336` specyfikował tylko kierunek zapisu.

- **W1 — nadpisanie działającej bazy w miejscu.** Konsekwencje: najbliższe
  intuicji „przywróć". Koszt: wszystkie otwarte `conn` w procesie wskazują po
  operacji na nieaktualny obraz, więc wymusza zamknięcie i ponowne otwarcie
  (sprzężenie z A-2); operacja jest nieodwracalna — jeśli kopia była starsza,
  bieżące dane przepadają bez śladu.
- **W2 — odtworzenie „obok" (do wskazanego nowego pliku) i świadome
  przełączenie przez ponowne `open_store`.** Konsekwencje: nic nie ginie,
  decyzja „którą bazą pracuję" jest jawna. Koszt: ktoś musi trzymać stan
  „aktywna ścieżka bazy", a dziś nic go nie trzyma i to jest celowe —
  `tasks/ROTA-T009/brief.md:355` zabrania, by poprawność zależała od sesji
  trzymanej w pamięci.
- **W3 — brak odtwarzania w produkcie.** Backup pozostaje plikiem dla
  człowieka/wsparcia, a odtworzenie jest procedurą operacyjną poza aplikacją.
  Konsekwencje: zero nowego kodu i zero ryzyka utraty danych przez pomyłkę w UI.
  Koszt: „przywróć kopię" nigdy nie będzie funkcją UI i trzeba to zapisać jako
  świadomą decyzję produktową, żeby nie wracało jako luka w kolejnym audycie.

Fakt istotny dla każdego wariantu: `migrate()` dopisze migracje przy otwarciu
starszej kopii (`db.py:385-402`), więc odtworzony plik nie jest bitowo tym, co
zapisano; kopia nowsza niż binarka zostanie odrzucona przez
`UnsupportedSchemaVersion` (`db.py:380-384`).

## B-5 (Z-6) — gdzie żyje saldo kwartalne?

- **W1 — tylko nowy osobny odczyt (A-5), `open_month` bez zmian.**
  Konsekwencje: zero ryzyka dla istniejących odczytów. Koszt:
  `WorkBalance.quarter_balance` zwracany przez `open_month` nadal równa się
  `month_balance`, więc UI dostaje dwa różne znaczenia tego samego pola z dwóch
  źródeł.
- **W2 — dodatkowo `assembler._assemble_work_balances` liczy realny carry-in.**
  Konsekwencje: `open_month` przestaje wprowadzać w błąd. **Dowód, że jest to
  bezpieczne dla silnika:** solver czyta ze `state.work_balances` wyłącznie
  `wb.target_hours` (`rota/planning/solver.py:320-321`) i nigdzie nie czyta
  `quarter_balance`, `unresolved_carryover` ani `month_balance` — ranking
  TARGET-01 i oracle ROTA-REG-001 nie mogą się przez to przesunąć. Testy
  asertujące te pola dotyczą wyłącznie czystych funkcji `rota.balance`
  (`tests/test_balance.py:44-55`), nie wyjścia assemblera. Koszt: assembler
  wykonuje dodatkowe odczyty za wcześniejsze miesiące kwartału (dziś czyta
  jeden miesiąc, `assembler.py:121-128`).
- **W3 — zostawić jak jest i zapisać, że w kontekście planowania pola
  `quarter_balance`/`unresolved_carryover` są niezdefiniowane.**
  Konsekwencje: najtaniej. Koszt: `arch/spec.md` przypisuje narastające saldo
  odpowiedzialności koordynatora (cytat w `rota/balance.py:3-9`), więc jest to
  domknięcie luki decyzją „nie robimy" i musi być podjęte świadomie.

## B-6 (Z-7, część a) — co znaczy „miesiąc, w którym jest grafik"?

Kontekst: enumeracja miesięcy nie istnieje na żadnej warstwie (brak `DISTINCT`
w całym `rota/persistence`); `list_schedule_versions` wymaga konkretnej pary
`(site_id, month)`. Ten punkt wymaga NOWEGO odczytu w `schedule_repository`,
więc nie jest czystym wrapperem i nie trafił do grupy A.

- **W1 — miesiące, dla których istnieje wskaźnik current.** Odpowiada pytaniu
  „gdzie jest grafik". Konsekwencje: lista jest krótka i zgodna z tym, co UI
  faktycznie umie otworzyć.
- **W2 — miesiące, dla których istnieje jakakolwiek wersja.** Konsekwencje:
  obejmuje też porzucone próby — w tym pustą pierwszą wersję, którą `plan_month`
  tworzy przed wywołaniem solvera (`plan_ops.py:78-81`), czyli miesiąc, w którym
  ktoś tylko kliknął PLAN i wyszedł, też się pokaże.
- **W3 — zakres (najstarszy/najnowszy miesiąc) zamiast listy; UI iteruje.**
  Konsekwencje: najmniejszy możliwy odczyt. Koszt: UI pokaże także miesiące
  puste w środku zakresu.

## B-7 (Z-8, nowe znalezisko tej tury) — czy granica „UI nie zapisuje do persistence" ma być wymuszona automatycznie?

**Dowód luki.** Jedyny test granic,
`tests/test_t009_lifecycle_memory_backup_boundary.py:156-181`, sprawdza
`planning ↛ persistence/application` oraz `persistence ↛ application`, a dla
`rota/application` weryfikuje wyłącznie brak importów `tkinter`/`PyQt`/`react`.
Nic w repo nie wykryje przyszłego UI importującego `rota.persistence`.
Dodatkowo `rota/application/__init__.py` ma 0 bajtów, więc nie istnieje
zadeklarowana powierzchnia API — granica jest dziś konwencją i wynikiem review,
nie własnością sprawdzalną maszynowo. To istotne właśnie teraz: T011 dokłada
wrappery, ale samo ich istnienie nie odbiera UI możliwości dalszego wołania
persistence wprost.

- **W1 — nie wymuszać; konwencja i review wystarczają.** Konsekwencje: zero
  kosztu. Koszt: zamrożony wymóg produktowy pozostaje niesprawdzalny, a
  kolejny audyt znajdzie to samo.
- **W2 — rozszerzyć istniejący `test_18_dependency_boundary_scan` o katalog UI,
  gdy powstanie (T012).** Konsekwencje: rozszerzenie mechanizmu, który już jest,
  a nie nowy mechanizm. Koszt: działa dopiero od momentu, gdy katalog UI
  istnieje, i wymaga zapisania jego ścieżki w teście.
- **W3 — dodatkowo kuratorowana lista eksportów w `rota/application/__init__.py`
  jako zadeklarowany kontrakt + test, że UI importuje tylko z niej.**
  Konsekwencje: powierzchnia API staje się jawna i wersjonowalna. Koszt: każda
  nowa funkcja aplikacyjna wymaga dopisania w dwóch miejscach, co przy
  `ANTI-BUREAUCRACY RULE` trzeba świadomie zaakceptować.

---

# Z-9 (nowe znalezisko tej tury, priorytet informacyjny — nie blokuje UI dziś)

**Opis.** Odczyt treści konkretnej historycznej wersji grafiku jest sprzężony z
kompletnością kalendarza tego miesiąca, mimo że sama wersja jest w pełni trwała.

**Dowód.** `assemble_planning_state` woła `_assemble_calendar` bezwarunkowo
(`assembler.py:188`) i przed `_assemble_version_content` (`assembler.py:194`),
a `_assemble_calendar` rzuca `IncompleteCalendarData` przy pierwszym brakującym
dniu (`assembler.py:93-94`). Ponieważ
`assemble_planning_state(schedule_version_id=...)` jest jedyną aplikacyjną drogą
do treści wskazanej wersji (`assembler.py:163-174`), odczyt zamkniętego FINAL-a
wymaga, by tabela `calendar_days` nadal miała wszystkie dni tego miesiąca.

**Dlaczego priorytet informacyjny, a nie blokujący.** W repo nie istnieje żadna
funkcja usuwająca wiersze z `calendar_days` (`calendar_repository.py` nie ma
`DELETE`), a wypełniony kalendarz był warunkiem wstępnym zaplanowania tego
miesiąca — więc stanu „jest wersja, nie ma kalendarza" nie da się dziś osiągnąć
normalną pracą. Realne drogi dojścia to import/dane legacy albo odtworzenie
kopii sprzed wypełnienia kalendarza, czyli **sprzężenie z B-4**: wybór wariantu
odtwarzania decyduje, czy to znalezisko kiedykolwiek stanie się realne.

**Nie proponuję domknięcia.** Rozstrzygnięcie ma sens dopiero po B-4.

---

# PROPONOWANY PODZIAŁ NA TASKI

Z-1..Z-9 nie są jednym zadaniem. Podział analogiczny do T010 (A/B/C/D), z
kryterium „ile decyzji właściciela blokuje start":

- **T011-A — mechaniczne wrappery.** A-1, A-2, A-4, A-5.
  Zero pytań otwartych. Może wejść do briefu i implementacji natychmiast,
  niezależnie od B. Domyka w całości Z-3 i Z-7b, Z-1 w części zapisu, Z-6 w
  wariancie W1.
- **T011-B — odkrywanie i nawigacja.** A-3 + B-3, B-6, B-7.
  Start po odpowiedzi na B-3 i B-6. Domyka Z-4, Z-7a i Z-8.
- **T011-C — cykl życia Site / Coordinator / asocjacji.** B-2.
  Osobny task, bo w wariancie W2 dotyka schematu bazy i modelu T008 — nie wolno
  go wsadzić do tej samej paczki co cienkie wrappery.
- **T011-D — operacje na całości danych.** B-1 (wypełnienie miesiąca), B-4
  (odtwarzanie z backupu), oraz B-5/W2 jeśli zostanie wybrany. Wspólny mianownik:
  wszystkie dotyczą transakcyjności i tożsamości całego zbioru danych, nie
  jednego wiersza. Po B-4 wraca tu Z-9.

Kolejność jest luźna poza tym, że T011-A nie zależy od niczego, a Z-9 zależy od
B-4.

# OUT OF SCOPE / ZAKAZY DLA T011

T011 NIE wprowadza:

- żadnego z mechanizmów zakazanych w `tasks/ROTA-T009/brief.md:46-66`;
- warstwy pośredniej ani fasady nad `rota/application/*`;
- nowego modelu uprawnień — `require_active_coordinator_context` zostaje jaką
  jest (`context.py:20-40`);
- zmian w `rota/planning/*` (grupa A jest wyłącznie warstwą wejścia; jedyny
  punkt dotykający czegokolwiek poza aplikacją to B-5/W2, i tylko assemblera);
- nowych rodzajów `SiteRule`, nowych celów solvera ani zmian semantyki HARD;
- UI/IPC/desktop — to nadal T012;
- parsowania języka naturalnego.

# ACCEPTANCE (kiedy ten dokument przestaje być propozycją)

1. Właściciel odpowiedział na B-1..B-7 (każde jako wybór wariantu, ewentualnie z
   modyfikacją).
2. Architekt przepisał A-1..A-5 i rozstrzygnięte B na brief(y) per task w
   `tasks/ROTA-T011*/`, z `INTEGRATED_BASE_SHA` i sekcją wymaganych testów —
   ten dokument nie definiuje testów, bo definiowanie ich to część briefu, nie
   propozycji.
3. Codex zwrócił `PASS / READY_FOR_IMPLEMENTATION` dla briefu.
4. Dopiero wtedy CC implementuje.

# CZEGO TA TURA NIE ZAWIERA I DLACZEGO

Zero kodu produkcyjnego i zero testów — świadomie. Sygnatury w grupie A są
kontraktem do zaimplementowania przez CC, nie implementacją: nie ma ciał
funkcji, nie ma importów, nie ma plików `rota/**` w diffie tego commita.
Rozstrzygnięcia z grupy B nie zostały podjęte, bo zmieniają znaczenie produktu,
a to nie jest kompetencja projektanta w tym procesie.

# SPRAWDZONE W TEJ TURZE I ŚWIADOMIE NIE PROPONOWANE

Fakty, które wyglądają jak luki, a nie są — zapisane, żeby nie wracały:

- **Odchylenia przed finalizacją są osiągalne.** `lifecycle_ops.finalize` wymaga
  dokładnego zbioru `deviation_id` (`lifecycle_ops.py:75-77`), a UI dostaje go
  przez `revalidate` + `assemble_planning_state` (`state.deviations`).
  Potwierdzone runtime w audycie. Nie trzeba nowego odczytu.
- **Odczyt konkretnej wersji historycznej istnieje** —
  `assemble_planning_state(schedule_version_id=...)` (`assembler.py:163-174`),
  z zastrzeżeniem Z-9.
- **`precheck.precheck(state)` nie przyjmuje `conn`** i wymaga, by wołający
  najpierw złożył `PlanningState`. To rozbieżność wobec sformułowania operacji 2
  w `tasks/ROTA-T009/brief.md:167`, ale nie luka: obie funkcje są w warstwie
  aplikacji, a brak dostępu do persistence jest tam wymogiem wprost
  (`brief.md:176`).
- **Edycja i dezaktywacja `ExternalSupportWindow`** są możliwe istniejącą
  `durable_inputs.add_external_support_window`, bo delegat jest upsertem po
  `window_id` (`employee_repository.py:141-155`). Mimo nazwy `add_*` nie ma tu
  luki.
- **`site_memory.decision_fate`, `site_memory.effective_rule_on`,
  `site_rule_repository.get_site_rule_version`** nie mają wołających w
  aplikacji, ale zakres operacji 11 (`tasks/ROTA-T009/brief.md:319-327`) jest
  pokryty przez `memory_read` bez nich. Nie proponuję dokładania wrapperów „na
  zapas".
- **`training.save_site_membership`** (`training.py:24-32`) jest publiczną
  funkcją aplikacyjną zapisującą bez guardu kontekstu i wymagającą otwartej
  transakcji. Zgłoszone w audycie jako obserwacja 1. Nie proponuję zmiany:
  docstring wyjaśnia, że nazwa jest punktem podmiany w testach (R5-1), a ruszanie
  tego bez briefu dotknęłoby atomowości zapisu readiness. Do decyzji przy T011-B
  (powierzchnia API, B-7/W3), nie tutaj.
