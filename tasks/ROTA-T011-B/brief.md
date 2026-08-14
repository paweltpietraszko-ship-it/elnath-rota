# TASK_CONTRACT

TASK_ID: ROTA-T011-B
TITLE: Odkrywanie kontekstu i nawigacja po miesiącach
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — wszystkie decyzje
produktowe tego tasku są rozstrzygnięte (B-3=W3, B-6=W1 z filtrem
uzupełniającym z 2026-08-14, B-7=W2 przeniesione do T012).

INTEGRATED_BASE_SHA: 029107be9045d2759e77450a0fb943a04483932c
BASE_BRANCH_AT_FREEZE: main

TASK_SCOPE:
- rota/application/bootstrap.py
- rota/persistence/schedule_repository.py
- rota/application/open_month.py
- tests/test_t011_b_context_discovery.py

Powyższa lista jest zamknięta. Plik testowy jest jedynym nowym plikiem.

## ŹRÓDŁA

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znaleziska Z-4, Z-7a, Z-8.
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — punkt A-3 z korektą po
  B-3, pytania B-3, B-6, B-7 z rozstrzygnięciami.
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §2, §11.
- `tasks/ROTA-T010/part_a_bootstrap_roster.md` — wymóg jawnego `site_id`
  w sygnaturach pod przyszłą wieloobiektowość T012.

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

Dziś każda z 34 publicznych funkcji `rota/application/*` wymaga, by wołający
znał już `coordinator_id` i `site_id`. Żaden odczyt aplikacyjny nie pozwala tych
identyfikatorów odkryć: `list_coordinators`, `list_sites`,
`list_site_profile_ids` i `list_associations_for_site` nie mają w
`rota/application/*` ani jednego wołającego. UI nie ma więc czym zbudować
ekranu startowego ani rozstrzygnąć „pokazać kreator pierwszej konfiguracji czy
listę obiektów".

Osobno: nie istnieje żaden — na żadnej warstwie — odczyt mówiący, dla których
miesięcy w ogóle istnieje grafik. `list_schedule_versions` wymaga konkretnej
pary `(site_id, month)`, a w całym `rota/persistence` nie ma ani jednego
`DISTINCT`. UI nie ma czym zbudować nawigacji po historii.

T011-B domyka oba braki i nic więcej.

## ANTI-BUREAUCRACY RULE

Obowiązuje lista zakazów z `tasks/ROTA-T009/brief.md:46-66`.

Dodatkowo: żadnej warstwy „katalogu obiektów", żadnego cache'u, żadnego
własnego typu wynikowego poza tym, co już zwracają istniejące odczyty. Cztery
odczyty z A-3 są kopią kształtu `bootstrap.current_roster`; odczyt miesięcy jest
jednym zapytaniem SQL plus jednolinijkowym wrapperem.

Zakaz flag boolowskich w sygnaturze (`only_active: bool` i podobne) — to była
jawna przesłanka rozstrzygnięcia B-3=W3 na rzecz nazwanych odczytów.

## DEPENDENCY BOUNDARY

Bez zmian względem `tasks/ROTA-T009/brief.md:68-91`. W szczególności: nowy
odczyt SQL powstaje **wyłącznie** w `rota/persistence/schedule_repository.py`,
a `rota/application/open_month.py` go tylko woła. Aplikacja nie zawiera SQL
ani nazw tabel.

## ZAKRES — A-3: cztery odczyty odkrywające kontekst (B-3 = W3)

Moduł docelowy: `rota/application/bootstrap.py`. Ten moduł już mieści odczyty
rozpoznające kontekst (`coordinator_context_completeness`,
`month_plan_readiness`, `current_roster`), a jego docstring (`bootstrap.py:19-23`)
opisuje „dwa odczyty, dwa znaczenia" jako własną odpowiedzialność.

Rozstrzygnięcie właściciela B-3=W3 rozdziela „w co mogę wejść" (filtrowane) od
„co istnieje" (pełne, dla panelu administracyjnego T012). Ta oś jest inna niż
oś encji, więc potrzeba czterech nazwanych odczytów, nie dwóch z trybami.

Sygnatury (wiążące):

```text
def active_coordinators(conn) -> tuple[Coordinator, ...]
def active_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]
def all_coordinators(conn) -> tuple[Coordinator, ...]
def all_sites_for_coordinator(conn, *, coordinator_id: str) -> tuple[Site, ...]
```

Wzorzec kopiowany 1:1: `bootstrap.current_roster` (`bootstrap.py:234-240`) —
odczyt bez guardu kontekstu, mapujący listę powiązań na encje przez `get_*`,
zwracający `tuple[...]`.

Znaczenie filtrów — dosłownie, bez interpretacji:

- `active_coordinators`: z `coordinator_repository.list_coordinators` (`:48`)
  tylko te z `Coordinator.active == True`.
- `active_sites_for_coordinator`: z `list_associations_for_coordinator` (`:111`)
  tylko powiązania z `association.active == True`, zmapowane przez
  `site_repository.get_site` (`:45`), z pozostawieniem tylko `Site.active == True`.
  Nie sprawdza aktywności samego koordynatora — to robi
  `active_coordinators` i `require_active_coordinator_context`.
- `all_coordinators`: pełna zawartość `list_coordinators`, bez filtra.
- `all_sites_for_coordinator`: wszystkie powiązania tego koordynatora, także
  nieaktywne, zmapowane na `Site` bez filtra `Site.active`.

Odczyty nie wołają `require_active_coordinator_context`. To nie jest osłabienie
kontroli, a zgodność z istniejącą konwencją: żaden odczyt w tym repo tego guardu
nie woła (`open_month`, wszystkie pięć funkcji `memory_read`,
`availability_matrix.employee_availability_matrix`, `bootstrap.current_roster`,
`assembler.assemble_planning_state`). Gdyby wołały, ekran startowy byłby
nieosiągalny — nie ma jeszcze wybranego kontekstu, który dałoby się sprawdzić.

Granica, której T011-B świadomie NIE przekracza: nie powstaje odczyt „wszystkie
obiekty w magazynie" niezależny od koordynatora. Cztery odczyty wyżej są
zakresowane do jednego koordynatora, dokładnie jak wymaga
`tasks/ROTA-T010/part_a_bootstrap_roster.md` (jawny identyfikator zamiast
niejawnego „jedyny aktywny Site"). Jeśli T012 będzie potrzebował listy
wszystkich obiektów bez podania koordynatora, to osobny odczyt i osobna decyzja
— CC go tutaj nie dodaje.

## ZAKRES — B-6: enumeracja miesięcy z grafikiem (B-6 = W1 + filtr obsady)

Rozstrzygnięcie właściciela, uzupełnione 2026-08-14 po znalezisku opisanym
w następnej sekcji: miesiące, dla których istnieje bieżący wskaźnik wersji
**i których bieżąca wersja ma co najmniej jeden `Assignment`**.

Sam warunek „ma bieżący wskaźnik" nie usuwa szumu, o który chodziło — usuwa go
dopiero filtr obsady. Oba warunki są wymagane i żaden z nich nie jest
opcjonalny.

Nowy odczyt w persistence (jedyne miejsce z SQL o `schedule_versions`):

```text
def list_months_with_assignments(conn: sqlite3.Connection, site_id: str) -> list[date]
```

Zwraca miesiące rosnąco, bez duplikatów. Miesiąc wchodzi do wyniku wtedy i
tylko wtedy, gdy dla pary `(site_id, month)` istnieje bieżąca wersja i ta
wersja ma co najmniej jeden wiersz `Assignment`. Liczy się wyłącznie bieżąca
wersja — obecność assignmentów w wersji historycznej niczego nie kwalifikuje.

Nazwa mówi o kryterium rzeczywistym, nie o mechanizmie: `..._with_assignments`,
a nie `..._with_current_version`, bo sam bieżący wskaźnik nie jest warunkiem
wystarczającym.

Wzorzec kształtu: istniejące `schedule_repository.list_schedule_versions`
(`:100-106`) i `get_current_version_id` (`:108-114`) — ten sam styl zapytania
i konwersji daty.

Stan `CANCELLED`/`NN` nie jest wyłączany: `Assignment` z `state=CANCELLED`
i `operational_code="NN"` nadal jest wierszem obsady i nadal kwalifikuje
miesiąc. Miesiąc, w którym koordynator odnotował niewykonaną zmianę, jest
miesiącem z grafikiem — inaczej NN mógłby usunąć miesiąc z nawigacji, co
przeczyłoby `tasks/ROTA-T010/part_d_nn.md` (wcześniejsza wersja zachowuje plan,
a demand nie znika).

Wrapper aplikacyjny w `rota/application/open_month.py`:

```text
def months_with_schedule(conn, *, site_id: str) -> tuple[date, ...]
```

Moduł jest właścicielem operacji „otwórz miesiąc"; wyliczenie, które miesiące
da się otworzyć, jest tą samą odpowiedzialnością, a modul już importuje
`schedule_repository`.

## DLACZEGO FILTR OBSADY JEST CZĘŚCIĄ DECYZJI

Pierwotne uzasadnienie B-6=W1 brzmiało: „W2 pokazywałoby też porzucone próby
(`plan_month` tworzy wersję przed wywołaniem solvera), co jest szumem".

Sprawdzone w kodzie i potwierdzone przez właściciela 2026-08-14: **samo
kryterium „ma bieżący wskaźnik" tego szumu nie usuwa.**
`schedule_lifecycle.create_schedule_version` woła `_set_current_reference`
bezwarunkowo, w tej samej transakcji (`schedule_lifecycle.py:153`), więc miesiąc
dostaje bieżący wskaźnik w tej samej chwili, w której powstaje pierwsza — jeszcze
pusta — wersja tworzona przez `plan_ops.plan_month` (`plan_ops.py:78-81`).
W dzisiejszym kodzie nie istnieje sposób, by wersja istniała bez bieżącego
wskaźnika dla swojego miesiąca, więc kryterium „ma current" i „ma jakąkolwiek
wersję" dają identyczny wynik i oba pokazują miesiąc, w którym ktoś tylko
kliknął PLAN i wyszedł.

Rozstrzygnięcie właściciela: W1 zostaje jako kryterium bazowe, ale enumeracja
filtruje dodatkowo po „co najmniej jeden `Assignment`" — to usuwa szum, którego
samo „ma current" nie usuwało. Kryterium odpowiada wtedy dosłownie na pytanie
„gdzie jest grafik", zamiast na „gdzie ktoś kiedyś nacisnął PLAN".

Świadomie przyjęta konsekwencja: miesiąc, którego bieżąca wersja jest pusta, nie
pojawia się w nawigacji, mimo że wersja trwale istnieje i pozostaje osiągalna
przez `open_month.open_month` z jawnie podanym miesiącem. Enumeracja jest
pomocą w nawigacji, nie rejestrem wszystkiego, co kiedykolwiek powstało.

## OUT OF SCOPE

- **B-7 (Z-8) — wymuszenie granicy „UI nie zapisuje do persistence": do T012.**
  Właściciel wybrał W2: rozszerzyć istniejący
  `tests/test_t009_lifecycle_memory_backup_boundary.py:156-181`
  (`test_18_dependency_boundary_scan`) o katalog UI, **gdy ten katalog
  powstanie**. Dziś nie istnieje, więc w T011-B nie ma czego skanować i CC nie
  dodaje ani atrapy katalogu, ani warunkowego testu, ani kuratorowanej listy
  eksportów w `rota/application/__init__.py` (to był odrzucony wariant W3).
  Ten punkt musi trafić do briefu T012 jako wymóg, nie zginąć.
- Odczyt „wszystkie obiekty w magazynie" bez podania koordynatora.
- Odczyt profili (`list_site_profile_ids`) — nie jest potrzebny do ekranu
  startowego przy B-3=W3 i nie ma wołającego; nie dodajemy wrapperów „na zapas".
- Jakakolwiek zmiana `require_active_coordinator_context`.
- Wszystko z T011-A/C/D/E.

## WYMAGANE TESTY

Jeden nowy plik `tests/test_t011_b_context_discovery.py`, prawdziwy tymczasowy
SQLite. Scenariusze, nie nazwy:

1. **Pusty magazyn.** Wszystkie cztery odczyty zwracają puste `tuple`, żaden nie
   rzuca. To jest stan, w którym UI ma pokazać kreator pierwszej konfiguracji.
2. **Jeden pełny kontekst.** Po bootstrapie wszystkie cztery odczyty zwracają
   ten sam pojedynczy koordynator/obiekt.
3. **Nieaktywny obiekt.** Kontekst, w którym `Site.active == False`:
   `active_sites_for_coordinator` go nie zwraca, `all_sites_for_coordinator`
   zwraca. Stan nieaktywny należy zbudować przez
   `bootstrap.bootstrap_or_resume_coordinator_context`, podając encję z
   `active=False` — nie przez `rota.persistence`.
4. **Nieaktywna asocjacja.** Analogicznie: obiekt widoczny tylko w odczycie
   pełnym.
5. **Nieaktywny koordynator.** `active_coordinators` go nie zwraca,
   `all_coordinators` zwraca.
6. **Dwa koordynatory.** `active_sites_for_coordinator` dla koordynatora A nie
   zwraca obiektu powiązanego wyłącznie z koordynatorem B. To jest właściwy
   dowód, że odczyt jest zakresowany, a nie globalny.
7. **Miesiące bez grafiku.** `months_with_schedule` na kontekście bez żadnej
   wersji zwraca pustą `tuple`.
8. **Miesiące z grafikiem.** Po `plan_month` + `select_candidate` dla dwóch
   różnych miesięcy odczyt zwraca dokładnie te dwa miesiące, rosnąco, bez
   duplikatów mimo wielu wersji w jednym miesiącu (np. po `replan`).
9. **Zakresowanie po obiekcie.** Miesiąc zaplanowany dla obiektu B nie pojawia
   się w odczycie dla obiektu A.
10. **Restart.** Po zamknięciu i ponownym otwarciu magazynu wszystkie odczyty
    zwracają to samo.
11. **Filtr obsady — porzucona próba nie jest szumem.** Miesiąc, w którym
    wywołano wyłącznie `plan_month` (bez `select_candidate`), **nie pojawia
    się** w `months_with_schedule`, mimo że ma bieżącą wersję. Ten sam miesiąc
    pojawia się natychmiast po `select_candidate`. To jest właściwy dowód, że
    filtr działa na obsadzie, a nie na obecności wskaźnika.
12. **NN nie usuwa miesiąca z nawigacji.** Miesiąc, w którym jedyną zmianą po
    `select_candidate` było `manual_edit.mark_not_worked`, nadal jest zwracany —
    `Assignment` z `state=CANCELLED` i `operational_code="NN"` liczy się jako
    obsada.
13. **Zakresowanie do bieżącej wersji.** Miesiąc, którego bieżąca wersja jest
    pusta, ale wersja historyczna miała assignmenty, **nie jest** zwracany. Jeśli
    zbudowanie takiego stanu nie jest możliwe wyłącznie przez warstwę aplikacji,
    należy to zgłosić jako finding zamiast obchodzić przez persistence — sam fakt
    nieosiągalności jest wtedy odpowiedzią.

Testy nie mogą importować `rota.persistence` do budowy stanu.

## ENGINEERING GATES

- istniejąca suite PASS;
- nowe testy T011-B PASS;
- ROTA-REG-001 bez zmian;
- Ruff PASS na plikach z TASK_SCOPE;
- `test_18_dependency_boundary_scan` nadal PASS;
- `SIZE_FILE`/`SIZE_FUNC` PASS — `bootstrap.py` ma dziś 240 linii, cztery
  krótkie odczyty nie zbliżają go do limitu 600.

Oczekiwany, dopuszczalny wynik `backend.py`: `WYMAGA_DECYZJI` na `TOTAL_LINES`
przy przekroczeniu 150 zmienionych linii. Nie obchodzić przez cięcie testów.

## ACCEPTANCE

T011-B jest kompletne, gdy UI znające wyłącznie `rota/application/*` potrafi bez
żadnego z góry znanego identyfikatora: wylistować koordynatorów, wylistować
obiekty danego koordynatora w dwóch jawnie rozdzielonych znaczeniach
(„w co mogę wejść" / „co istnieje") i wylistować miesiące, w których faktycznie
istnieje obsadzony grafik do otwarcia — bez miesięcy, w których powstała tylko
pusta wersja.

Znaleziska Z-4 i Z-7a zamknięte. Z-8 pozostaje otwarte i jest jawnie przeniesione
do T012 — nie wolno go zamknąć w tym tasku.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. sprzeczności z zamrożoną architekturą i zaakceptowanym T004-T010;
2. dwuznaczności zmuszającej CC do wymyślania zachowania — w szczególności czy
   definicje czterech filtrów są dosłowne;
3. testowalności, zwłaszcza czy stany nieaktywne da się zbudować bez sięgania do
   persistence;
4. wycieku zakresu do T012 (B-7) lub do pozostałych części T011;
5. czy filtr „co najmniej jeden `Assignment`" jest opisany jednoznacznie —
   w szczególności czy jest jasne, że liczy się wyłącznie bieżąca wersja i że
   `CANCELLED`/`NN` nadal kwalifikuje miesiąc;
6. czy sprawdzenie z `schedule_lifecycle.py:153` jest poprawne — na nim opiera
   się uzasadnienie, dla którego sam bieżący wskaźnik nie wystarcza.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
