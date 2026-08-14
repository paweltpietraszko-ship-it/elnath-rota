# TASK_CONTRACT

TASK_ID: ROTA-T011-C
TITLE: Cykl życia Site, Coordinator i CoordinatorSiteAssociation po bootstrapie
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: tak, dla jednego punktu —
patrz WYMAGA_DECYZJI niżej. Sam kształt edycji wynika z rozstrzygnięcia B-2=W1
podjętego 2026-08-14.

INTEGRATED_BASE_SHA: 95717be1682840934252c610ceafc59f9980bf28
BASE_BRANCH_AT_FREEZE: main

TASK_SCOPE:
- rota/application/durable_inputs.py
- tests/test_t011_c_site_coordinator_lifecycle.py

Powyższa lista jest zamknięta. Plik testowy jest jedynym nowym plikiem.

## ŹRÓDŁA

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znalezisko Z-2 (branch
  `cursor/audit-pipeline-completeness-d5d7`, commit `a0e4650`).
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — pytanie B-2 z
  rozstrzygnięciem W1 i CONSTRAINT o `profile_id` (branch
  `cursor/pipeline-closure-proposal-d5d7`, commit `5c2fd3c`).
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §2 — Panel
  Sterowania jest jednym miejscem pierwszej konfiguracji i późniejszej edycji
  tych samych danych; „Bootstrap nie może stać się słabiej chronioną ścieżką
  edycji istniejącego obiektu".
- `tasks/ROTA-T008/brief.md` — klasyfikacja MUTABLE CURRENT-STATE ENTITIES.

UWAGA DLA CODEXA: dwa pierwsze źródła nie są jeszcze zmergowane do `main`.

## PROCES — WARUNEK WSTĘPNY BLOKUJĄCY

Identyczny jak w `tasks/ROTA-T011-A/brief.md` (rozjazd `arch/FROZEN.lock`
CRLF/LF). `arch/FROZEN.lock` nie jest w TASK_SCOPE.

## PURPOSE

Po pierwszym udanym bootstrapie warstwa aplikacji nie ma dziś ŻADNEGO zapisu
`Site`, `Coordinator` ani `CoordinatorSiteAssociation`:

- `site_repository.save_site` (`:40`), `coordinator_repository.save_coordinator`
  (`:32`) i `save_coordinator_site_association` (`:77`) nie mają ani jednego
  wołającego w `rota/application/*`;
- warianty `*_in_open_transaction` są osiągalne wyłącznie z
  `bootstrap.bootstrap_or_resume_coordinator_context`, które podnosi
  `CoordinatorContextAlreadyActive`, gdy istnieje aktywna asocjacja
  (`bootstrap.py:102-106`);
- `durable_inputs` obejmuje Employee, SiteMembership, ExternalSupportWindow,
  target_hours i SiteProfile, ale nie te trzy encje.

Skutkiem są drzwi w jedną stronę: UI nie może zmienić nazwy obiektu, zdezaktywować
go, zdezaktywować koordynatora ani odebrać uprawnienia. Jest to sprzeczne z
`OWNER_DECISION_T010…` §2, który wymaga, by ta sama ścieżka obsługiwała pierwszą
konfigurację i późniejszą edycję.

## ROZSTRZYGNIĘCIE, KTÓRE TEN TASK REALIZUJE

B-2 = **W1**: zwykły upsert, jak każdy inny durable input. Uzasadnienie
właściciela: T008 zaklasyfikował te encje jako „MUTABLE CURRENT-STATE ENTITIES"
— ten sam status co Employee/SiteMembership, które już używają zwykłego
upsertu; wersjonowanie (W2) zmieniałoby tę już podjętą klasyfikację, a nie
tylko domykało lukę.

Przejście `CoordinatorSiteAssociation.active: 1 → 0` musi być możliwe zwykłym
zapisem. Nie wymaga nowego prymitywu: `save_coordinator_site_association`
(`coordinator_repository.py:77-79`) jest zwykłym upsertem bez klauzuli `WHERE`
i już dziś fizycznie na to pozwala. Klauzula `WHERE ... active = 0` istnieje
wyłącznie w ścieżce CAS używanej przez bootstrap
(`coordinator_repository.py:101-108`) i chroni tam przed wyścigiem dwóch
bootstrapów — nie jest ogólnym zakazem dezaktywacji.

## ANTI-BUREAUCRACY RULE

Obowiązuje lista zakazów z `tasks/ROTA-T009/brief.md:46-66`.

Dodatkowo: żadnego wersjonowania, żadnych tabel historii, żadnego audit logu dla
tych trzech encji — to jest odrzucony wariant W2. Żadnej maszyny stanów obiektu.
Żadnej macierzy uprawnień: `require_active_coordinator_context` zostaje taki,
jaki jest (`context.py:20-40`).

## DEPENDENCY BOUNDARY

Bez zmian względem `tasks/ROTA-T009/brief.md:68-91`. Wszystkie trzy nowe funkcje
to cienkie wrappery w warstwie aplikacji; nie powstaje ani jedna nowa funkcja w
`rota/persistence` (istniejące zapisy wystarczają).

## ZAKRES — trzy wrappery edycyjne

Moduł docelowy: `rota/application/durable_inputs.py`.

Wzorzec kopiowany 1:1 dla wszystkich trzech: `durable_inputs.update_membership`
(`durable_inputs.py:54-57`) — `require_active_coordinator_context`, kontrola
tożsamości payloadu, delegacja do istniejącego zapisu.

Sygnatury (wiążące):

```text
def update_site(conn, *, coordinator_id: str, site_id: str, site: Site) -> None
def update_coordinator(conn, *, coordinator_id: str, site_id: str, coordinator: Coordinator) -> None
def update_association(conn, *, coordinator_id: str, site_id: str, association: CoordinatorSiteAssociation) -> None
```

Delegacja odpowiednio do `site_repository.save_site` (`:40`),
`coordinator_repository.save_coordinator` (`:32`),
`coordinator_repository.save_coordinator_site_association` (`:77`).

Kontrola tożsamości payloadu (wymagana, nie opcjonalna):

- `update_site`: `site.site_id` musi równać się autoryzowanemu `site_id`,
  inaczej `InvalidCoordinatorContext`. Wzorzec: `_require_payload_belongs_to_site`
  (`durable_inputs.py:20-26`) oraz `bootstrap._require_id_match` używany dla Site
  w `bootstrap.py:116`.
- `update_association`: `association.site_id` musi równać się autoryzowanemu
  `site_id`, inaczej `InvalidCoordinatorContext`.
- `update_coordinator`: patrz WYMAGA_DECYZJI — kontrola tożsamości koordynatora
  jest właśnie tym nierozstrzygniętym punktem.

### Zakaz zmiany `profile_id` przez `update_site`

`update_site` MUSI odrzucić wywołanie, w którym `site.profile_id` różni się od
`profile_id` obecnie zapisanego dla tego Site, podnosząc `InvalidCoordinatorContext`.

Uzasadnienie (CONSTRAINT z dokumentu projektowego, nie nowa decyzja):
`write_site_in_open_transaction` (`site_repository.py:21-37`) nadpisuje
`profile_id` i waliduje tylko, że docelowy profil ISTNIEJE, nie że się nie
zmienił. Przepięcie Site na inny profil po cichu zmienia katalog zmian
standardowych i retroaktywnie zmienia kwalifikację szkoleń, bo
`training._qualifies_for_readiness` liczy względem BIEŻĄCEGO profilu w momencie
liczenia, nie profilu z chwili realizacji (świadomie przyjęty kompromis R6-4,
`training.py:50-56`). Jest to też niesymetryczne wobec
`durable_inputs.update_site_profile`, który już dziś odrzuca profil nienależący
do autoryzowanego Site (`durable_inputs.py:70-73`).

`profile_id` pozostaje ustawiane wyłącznie przy bootstrapie, przez istniejącą
`bootstrap.bootstrap_or_resume_coordinator_context` (`bootstrap.py:78-125`).
Świadome przepięcie Site na inny profil, gdyby kiedyś było potrzebne, jest
osobną, jawnie nazwaną operacją z własnym pytaniem produktowym o retroaktywność
szkoleń — nie efektem ubocznym zwykłej edycji nazwy.

### Samozablokowanie jest oczekiwanym, odwracalnym zachowaniem

Konsekwencja W1, którą kontrakt przyjmuje świadomie i która MUSI być pokryta
testami:

Koordynator może przez `update_association(active=False)` albo
`update_coordinator(active=False)` albo `update_site(active=False)` odebrać sam
sobie kontekst. Guard `require_active_coordinator_context` wykonuje się PRZED
zapisem, więc samo wywołanie się udaje; każde następne wywołanie dowolnej
funkcji z `durable_inputs` podnosi wtedy `InvalidCoordinatorContext`.

Wyjście z tego stanu istnieje i nie wymaga nowego kodu: skoro nie ma już
aktywnej asocjacji, `bootstrap.bootstrap_or_resume_coordinator_context` przestaje
odmawiać (`bootstrap.py:102-106`) i może ten kontekst wznowić — to jest dokładnie
ta rola „resume", dla której bootstrap powstał
(`tasks/ROTA-T010/part_a_bootstrap_roster.md`). Nie narusza to §2 decyzji
właściciela („bootstrap nie może stać się słabiej chronioną ścieżką edycji
istniejącego obiektu"), bo bootstrap nadal odmawia, dopóki kontekst JEST aktywny.

Odczyty pozostają dostępne także po dezaktywacji, bo żaden odczyt w tym repo nie
woła guardu kontekstu. Historia jest więc czytelna cały czas.

Nie wolno dodawać zabezpieczenia przed samozablokowaniem ani warunku wstępnego
„brak otwartej wersji WORKING" — ten drugi to odrzucony wariant W3. Gdyby
właściciel chciał którekolwiek z nich, jest to osobna decyzja i osobny task.

## WYMAGA_DECYZJI — WŁAŚCICIEL (nie rozstrzygam tego sam)

**Czy koordynator może zapisywać encje innego koordynatora?**

Dosłowne odczytanie B-2=W1 („zwykły upsert, jak każdy inny durable input")
prowadzi do braku kontroli, bo wzorcowy `durable_inputs.update_employee`
(`durable_inputs.py:49-51`) nie ma żadnej kontroli tożsamości payloadu —
`Employee` nie nosi `site_id`, więc nie ma czego porównywać. `Coordinator` też
nie nosi `site_id`. Przy dosłownej kopii wzorca koordynator A mógłby więc
zmienić nazwę koordynatora B albo ustawić mu `active=False`, co jest jakościowo
inną operacją niż zmiana nazwy pracownika: odbiera dostęp innej osobie.

Warianty:

- **W1 — bez kontroli, dosłowna kopia wzorca `update_employee`.** Konsekwencje:
  najprostsze i formalnie zgodne z „jak każdy inny durable input"; koszt: każdy
  aktywny koordynator może zdezaktywować każdego innego, a przy jednym
  koordynatorze w pilocie nikt tego nie zauważy — problem pojawi się dopiero
  przy drugim, czyli w T012.
- **W2 — `update_coordinator` wymaga `coordinator.coordinator_id == coordinator_id`,
  a `update_association` dodatkowo `association.coordinator_id == coordinator_id`.**
  Konsekwencje: koordynator edytuje wyłącznie siebie i własne powiązanie; spójne
  z duchem R4-3-B (`durable_inputs.py:20-26`), gdzie kontekst dla jednego Site
  nie autoryzuje mutowania payloadu innego Site; koszt: nie ma wtedy żadnej
  ścieżki aplikacyjnej do zdezaktywowania koordynatora, który odszedł — trzeba
  by jej dodać osobno w T012.
- **W3 — kontrola jak w W2 dla `update_coordinator`, brak kontroli dla
  `update_association`.** Konsekwencje: koordynator może odebrać innemu dostęp do
  OBIEKTU, którym sam zarządza (co jest naturalne dla właściciela obiektu), ale
  nie może zmienić danych tożsamościowych innej osoby; koszt: dwie różne reguły
  w jednym module, wymagające wyjaśnienia w docstringu.

Do czasu rozstrzygnięcia CC **nie implementuje** `update_coordinator` ani
kontroli tożsamości koordynatora w `update_association`. `update_site` i
zakaz zmiany `profile_id` są niezależne od tej decyzji i mogą powstać od razu.

## OUT OF SCOPE

- Wersjonowanie/historia zmian `Site`/`Coordinator`/asocjacji (odrzucony W2).
- Warunek wstępny „brak otwartej wersji WORKING" przy dezaktywacji (odrzucony W3).
- Świadome przepięcie `Site.profile_id` na inny profil.
- Kaskadowe skutki dezaktywacji obiektu (co dzieje się z jego FINAL-ami poza
  tym, że pozostają czytelne) — nie ma tu żadnej nowej logiki.
- Zabezpieczenie przed samozablokowaniem.
- Ścieżka „zdezaktywuj koordynatora, który odszedł", jeśli rozstrzygnięcie
  WYMAGA_DECYZJI ją wykluczy — wtedy trafia do T012.
- Wszystko z T011-A/B/D/E.

## WYMAGANE TESTY

Jeden nowy plik `tests/test_t011_c_site_coordinator_lifecycle.py`, prawdziwy
tymczasowy SQLite. Scenariusze, nie nazwy:

1. **Zmiana nazwy obiektu.** `update_site` z nową `display_name` zmienia ją, a
   `get_site`/`open_month` widzą nową wartość; `profile_id`, `active` i
   identyfikator pozostają bez zmian.
2. **Payload z obcym `site_id`.** `update_site` z `site.site_id` innym niż
   autoryzowany podnosi `InvalidCoordinatorContext` i nic nie zapisuje.
3. **Zakaz przepięcia profilu.** `update_site` z innym istniejącym `profile_id`
   podnosi `InvalidCoordinatorContext` i nie zmienia ani `profile_id`, ani
   `display_name` (dowód, że odrzucenie jest przed zapisem, nie po części).
4. **Brak kontekstu.** `update_site` bez aktywnej asocjacji podnosi
   `InvalidCoordinatorContext`.
5. **Dezaktywacja asocjacji.** `update_association(active=False)` udaje się;
   następne `durable_inputs.update_employee` podnosi
   `InvalidCoordinatorContext`; `open_month` i `memory_read` nadal działają.
6. **Wznowienie po samozablokowaniu.** Po scenariuszu 5
   `bootstrap.bootstrap_or_resume_coordinator_context` z tą samą asocjacją
   przywraca kontekst i kolejna edycja durable input znów działa.
7. **Bootstrap nadal odmawia przy aktywnym kontekście.** Dowód, że §2 decyzji
   właściciela nie został osłabiony: przy aktywnej asocjacji bootstrap podnosi
   `CoordinatorContextAlreadyActive`, więc nie stał się alternatywną ścieżką
   edycji.
8. **Dezaktywacja obiektu nie kasuje historii.** Miesiąc z sfinalizowanym
   grafikiem pozostaje czytelny przez `open_month`/`assemble_planning_state` po
   `update_site(active=False)`; `active_sites_for_coordinator` z T011-B (jeśli
   już zmergowane) go nie zwraca. Jeśli T011-B nie jest jeszcze w bazie, test
   sprawdza tylko czytelność historii.
9. **Restart.** Po zamknięciu i ponownym otwarciu magazynu zmienione wartości i
   flagi `active` są takie same.
10. **Payload asocjacji z obcym `site_id`** podnosi `InvalidCoordinatorContext`.

Testy nie mogą importować `rota.persistence` do budowy stanu ani do weryfikacji
— jedynym dopuszczonym oknem na stan jest `rota.application.*`.

## ENGINEERING GATES

- istniejąca suite PASS;
- nowe testy T011-C PASS;
- ROTA-REG-001 bez zmian;
- Ruff PASS na plikach z TASK_SCOPE;
- `test_18_dependency_boundary_scan` nadal PASS;
- `SIZE_FILE`/`SIZE_FUNC` PASS — `durable_inputs.py` ma dziś 74 linie.

Uwaga na kolizję z T011-A: oba taski modyfikują
`rota/application/durable_inputs.py`. Nie implementować ich jednym commitem;
jeśli T011-A jest zmergowane pierwsze, T011-C startuje z odświeżonej bazy.

Oczekiwany, dopuszczalny wynik `backend.py`: `WYMAGA_DECYZJI` na `TOTAL_LINES`
przy przekroczeniu 150 zmienionych linii.

## ACCEPTANCE

T011-C jest kompletne, gdy koordynator przez `rota/application/*` potrafi zmienić
nazwę i flagę aktywności swojego obiektu oraz odebrać/przywrócić powiązanie,
bez sięgania do `rota/persistence/*` i bez używania bootstrapu jako ścieżki
edycji — a wszystkie te operacje są odwracalne i nie kasują historii.

Znalezisko Z-2 zamknięte w części niezależnej od WYMAGA_DECYZJI. Część dotycząca
encji innego koordynatora pozostaje otwarta i jawnie oznaczona.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. sprzeczności z zamrożoną architekturą, T008 (MUTABLE CURRENT-STATE ENTITIES)
   i §2 decyzji właściciela o bootstrapie;
2. dwuznaczności zmuszającej CC do wymyślania zachowania;
3. testowalności — w szczególności czy scenariusze 5-7 (samozablokowanie i
   wznowienie) są wykonalne wyłącznie przez warstwę aplikacji;
4. czy zakaz zmiany `profile_id` jest postawiony jako twardy wymóg, a nie
   sugestia;
5. czy sekcja WYMAGA_DECYZJI jest realnym pytaniem produktowym, a nie
   architektem uchylającym się od decyzji technicznej.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
