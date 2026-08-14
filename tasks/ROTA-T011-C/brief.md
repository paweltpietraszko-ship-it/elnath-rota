# TASK_CONTRACT

TASK_ID: ROTA-T011-C
TITLE: Cykl życia Site, Coordinator i CoordinatorSiteAssociation po bootstrapie
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — wszystkie decyzje
produktowe tego tasku są rozstrzygnięte (B-2=W1 oraz brak kontroli tożsamości
koordynatora, rozstrzygnięty 2026-08-14).

INTEGRATED_BASE_SHA: 029107be9045d2759e77450a0fb943a04483932c
BASE_BRANCH_AT_FREEZE: main

TASK_SCOPE:
- rota/application/durable_inputs.py
- tests/test_t011_c_site_coordinator_lifecycle.py

Powyższa lista jest zamknięta. Plik testowy jest jedynym nowym plikiem.

## ŹRÓDŁA

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znalezisko Z-2.
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — pytanie B-2 z
  rozstrzygnięciem W1 i CONSTRAINT o `profile_id`.
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §2 — Panel
  Sterowania jest jednym miejscem pierwszej konfiguracji i późniejszej edycji
  tych samych danych; „Bootstrap nie może stać się słabiej chronioną ścieżką
  edycji istniejącego obiektu".
- `tasks/ROTA-T008/brief.md` — klasyfikacja MUTABLE CURRENT-STATE ENTITIES.

Wszystkie źródła są na `main` od `029107b`.

## PROCES — BRAMKA MECHANICZNA: STAN POTWIERDZONY

Wcześniejsza blokada `FROZEN_LOCK` (hash `arch/spec.md` policzony z CRLF plus
pole `FILE:` z backslashem) została naprawiona poza zakresem T011 (`20f08f9`,
zmergowane w `0175d71`) i zweryfikowana na `029107b`:
`guard.py check arch/spec.md` → `STATUS: PASS`, `backend.check_frozen_lock()` →
brak blockera. Szczegóły w `tasks/ROTA-T011-A/brief.md`.

`arch/FROZEN.lock` pozostaje poza TASK_SCOPE. Jeśli `FROZEN_LOCK` zgłosi
cokolwiek podczas implementacji, jest to NOWY problem — zgłoś go, nie obchodź.

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
- `update_coordinator`: **żadnej kontroli tożsamości koordynatora** — patrz
  rozstrzygnięcie niżej. Dosłowna kopia wzorca `durable_inputs.update_employee`
  (`durable_inputs.py:49-51`): guard kontekstu i delegacja, bez porównywania
  `coordinator.coordinator_id` z autoryzowanym `coordinator_id`.
- `update_association`: również bez kontroli tożsamości koordynatora —
  sprawdzany jest wyłącznie `association.site_id`, jak wyżej.

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

## ROZSTRZYGNIĘCIE WŁAŚCICIELA (2026-08-14): BRAK KONTROLI TOŻSAMOŚCI KOORDYNATORA

Pytanie brzmiało: czy koordynator może zapisywać encje innego koordynatora.
Dosłowne odczytanie B-2=W1 („zwykły upsert, jak każdy inny durable input")
prowadzi do braku kontroli, bo wzorcowy `durable_inputs.update_employee`
(`durable_inputs.py:49-51`) żadnej kontroli tożsamości payloadu nie ma —
`Employee` nie nosi `site_id`, więc nie ma czego porównywać, i `Coordinator`
również go nie nosi.

Rozstrzygnięcie: **brak kontroli, świadomie.** Uzasadnienie właściciela:
koordynatorzy mogą się zastępować na jednym koncie i jest to ich wewnętrzna
sprawa organizacyjna, a każdy dostaje osobną kopię programu — model „wielu
użytkowników na jednej instalacji" nie istnieje w tym produkcie. Logowanie i
uprawnienia są odłożoną przyszłą pracą, nie przemilczanym brakiem.

Konsekwencje przyjęte świadomie, do udokumentowania w docstringu, nie do
obejścia w kodzie:

- aktywny koordynator może zmienić `display_name` innego koordynatora oraz
  ustawić mu `active=False`;
- może też odebrać innemu koordynatorowi powiązanie z obiektem przez
  `update_association`;
- nie ma w tym eskalacji uprawnień w sensie, w którym produkt ich nie modeluje:
  wszystkie te operacje wymagają już posiadania aktywnego kontekstu
  koordynator–obiekt, a instalacja jest jednoosobowa.

CC implementuje więc `update_coordinator` bez porównywania identyfikatorów i
**nie dodaje** żadnego sprawdzenia „edytujesz siebie". Nie wolno też dodawać
komentarza sugerującego, że to luka bezpieczeństwa — jest to zapisana decyzja
produktowa z podanym uzasadnieniem.

Gdy w przyszłości pojawi się logowanie, kontrola tożsamości jest naturalnym
miejscem do ponownego rozpatrzenia; to wtedy, nie teraz.

## OUT OF SCOPE

- Wersjonowanie/historia zmian `Site`/`Coordinator`/asocjacji (odrzucony W2).
- Warunek wstępny „brak otwartej wersji WORKING" przy dezaktywacji (odrzucony W3).
- Świadome przepięcie `Site.profile_id` na inny profil.
- Kaskadowe skutki dezaktywacji obiektu (co dzieje się z jego FINAL-ami poza
  tym, że pozostają czytelne) — nie ma tu żadnej nowej logiki.
- Zabezpieczenie przed samozablokowaniem.
- Logowanie, uwierzytelnianie i jakikolwiek model uprawnień — odłożona przyszła
  praca, jawnie poza T011 (patrz ROZSTRZYGNIĘCIE wyżej).
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
11. **Zmiana własnych danych koordynatora.** `update_coordinator` z nową
    `display_name` zmienia ją, a `active_coordinators`/`get_coordinator` widzą
    nową wartość.
12. **Zapis encji innego koordynatora jest dozwolony.** Koordynator A z aktywnym
    kontekstem zmienia `display_name` koordynatora B, a następnie ustawia mu
    `active=False`; oba wywołania kończą się sukcesem. Ten test utrwala
    rozstrzygnięcie właściciela z 2026-08-14 i musi mieć komentarz mówiący, że
    brak kontroli tożsamości jest świadomy — inaczej przyszły audyt zgłosi go
    jako lukę.
13. **Odebranie powiązania innemu koordynatorowi.** Koordynator A wyłącza
    asocjację koordynatora B z tym samym obiektem; B traci możliwość edycji
    durable input, A nadal ją ma.

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

Znalezisko Z-2 zamknięte w całości — łącznie z encjami innego koordynatora,
gdzie brak kontroli tożsamości jest zapisanym rozstrzygnięciem właściciela, nie
pozostawionym pytaniem.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. sprzeczności z zamrożoną architekturą, T008 (MUTABLE CURRENT-STATE ENTITIES)
   i §2 decyzji właściciela o bootstrapie;
2. dwuznaczności zmuszającej CC do wymyślania zachowania;
3. testowalności — w szczególności czy scenariusze 5-7 (samozablokowanie i
   wznowienie) są wykonalne wyłącznie przez warstwę aplikacji;
4. czy zakaz zmiany `profile_id` jest postawiony jako twardy wymóg, a nie
   sugestia;
5. czy brak kontroli tożsamości koordynatora jest opisany jako rozstrzygnięcie
   właściciela z uzasadnieniem — a nie jako przeoczenie. Nie zgłaszaj tego jako
   luki bezpieczeństwa: model „wielu użytkowników na jednej instalacji" nie
   istnieje w tym produkcie, a logowanie jest jawnie odłożone. Zgłoś natomiast,
   jeśli którykolwiek fragment briefu jest z tym rozstrzygnięciem sprzeczny.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
