# TASK_CONTRACT

TASK_ID: ROTA-T011-E
TITLE: Dowód E2E — pełny łańcuch koordynatora wyłącznie przez warstwę aplikacji
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — ten task nie zmienia
zachowania produktu, tylko dowodzi zachowania już zakontraktowanego.

INTEGRATED_BASE_SHA: 95717be1682840934252c610ceafc59f9980bf28
BASE_BRANCH_AT_FREEZE: main
DEPENDS_ON: ROTA-T011-A (twarda zależność — patrz ZALEŻNOŚĆ niżej)

TASK_SCOPE:
- tests/test_t011_e_pipeline_e2e_happy_path.py
- tests/test_t011_e_pipeline_e2e_hard_stop.py

Powyższa lista jest zamknięta. Oba pliki są nowe, co wyczerpuje limit
`MAX_NEW_FILES = 2`; ten task nie modyfikuje ani jednego pliku produkcyjnego.
Gdyby implementacja wymagała zmiany czegokolwiek w `rota/`, jest to finding do
zgłoszenia, nie licencja na rozszerzenie scope — dowód ma opisywać zachowanie
istniejące, nie je tworzyć.

## POCHODZENIE I ROZSTRZYGNIĘCIE KOLIZJI NAZWY „T011"

Treść merytoryczna tego briefu pochodzi z `arch/T011_architect_brief.md`
(commit `95717be` na `main`), przygotowanego przez CC po przeglądzie stanu
projektu po merge T010. Tamten dokument nazwał siebie „T011 (proponowane)" i
sam zastrzegł, że numer jest propozycją, nie zamrożonym przypisaniem.

Równolegle nazwa „T011" została użyta dla domknięcia luk audytowych Z-1..Z-9
(`arch/T011_pipeline_closure_proposal_2026-08-14.md`, podział na A/B/C/D). Były
więc dwa różne znaczenia „T011", w tym dwa pliki z przedrostkiem `T011_` w
`arch/`.

Rozstrzygnięcie: numeracja domknięcia luk zostaje przy T011 (A/B/C/D), a dowód
E2E zostaje **T011-E** i przenosi się z `arch/` do `tasks/ROTA-T011-E/brief.md`.
Plik `arch/T011_architect_brief.md` zostaje usunięty tym samym commitem, żeby
w `arch/` nie pozostały na stałe dwa pliki `T011_*` o różnym znaczeniu.

Uzasadnienie litery „E", a nie osobnego numeru zadania:

1. Dowód E2E nie jest szóstym rodzajem luki, lecz przekrojowym dowodem, że
   domknięty pipeline działa jako całość. Trzyma się tej samej linii dowodowej
   (ten sam audyt, ta sama baza, te same funkcje aplikacyjne), więc oderwanie go
   od rodziny T011 ukryłoby tę zależność.
2. Litera wyraża kolejność wykonania wewnątrz rodziny: A..D domykają, E dowodzi.
   Ta kolejność nie jest porządkowa, ale wymuszona treścią — patrz ZALEŻNOŚĆ.
3. T010 ma precedens rodziny z literami o różnej naturze: `part_c_training_readiness.md`
   nie jest implementacją, tylko gate'em regresyjnym, i pozostał częścią „C".

## ZALEŻNOŚĆ OD T011-A — TWARDA, WYNIKAJĄCA Z TREŚCI

T011-E **nie może** zostać zaimplementowane przed zmergowaniem T011-A.

Dokument źródłowy stawia sobie za cel dowód, że pełny łańcuch działa „bez
żadnych skrótów przez warstwę persystencji", i jednocześnie sam zauważa, że
musiałby zrobić dwa wyjątki:

- krok „gotowość miesiąca" wymaga kompletnego `CalendarDay`, a dziś jedynym
  zapisem kalendarza jest `rota.persistence.calendar_repository.save_calendar_day`
  (audyt: znalezisko Z-1) — to zamyka A-1;
- krok „restart" wymaga ponownego otwarcia magazynu, a dziś jedynym wejściem jest
  `rota.persistence.db.connect` (audyt: znalezisko Z-3) — to zamyka A-2.

Bez T011-A test musiałby zaimportować `rota.persistence` w dwóch miejscach,
czyli obalić własną tezę. Po T011-A oba kroki mają wejście aplikacyjne i dowód
jest szczelny. Dlatego brak importu `rota.persistence` w obu plikach testowych
jest w tym tasku wymogiem, nie preferencją stylu.

## PROCES — WARUNEK WSTĘPNY BLOKUJĄCY

Identyczny jak w `tasks/ROTA-T011-A/brief.md` (rozjazd `arch/FROZEN.lock`
CRLF/LF, `backend.py:61-82` i `guard.py:90-92`). `arch/FROZEN.lock` nie jest
w TASK_SCOPE.

## PURPOSE — FAKT, KTÓRY UZASADNIA TEN TASK

Sprawdzone bezpośrednio w repo: publiczne wejście aplikacyjne T010-A,
`rota.application.bootstrap.bootstrap_or_resume_coordinator_context`, jest
wołane wyłącznie we własnych testach części A
(`tests/test_t010_bootstrap_roster.py`, `tests/test_audit_t010_r3.py`,
`tests/test_audit_t010_r4_a.py`).

Każdy inny test w repo — łącznie z testem przekrojowym
`tests/test_audit_t010_r9_consistency.py`, który miał dowieść spójności A/B/C/D
— buduje kontekst (Coordinator, SiteProfile, Site, Association, Employee,
SiteMembership, CalendarDay) bezpośrednimi wywołaniami `rota.persistence.*`
(`save_coordinator`, `save_site_profile`, `save_calendar_day` i podobne),
pomijając warstwę, której realnie użyje przyszłe UI.

Żaden istniejący test nie dowodzi więc, że pełny łańcuch operacji w kolejności,
w jakiej faktycznie użyje go koordynator, przechodzi od pustej bazy do
sfinalizowanego grafiku i z powrotem po restarcie **wyłącznie** przez publiczne
funkcje `rota.application.*`.

To jest luka dowodowa, nie luka funkcjonalna: pojedyncze zachowania są pokryte,
brakuje dowodu ich złożenia po właściwej stronie granicy.

## ANTI-BUREAUCRACY RULE

Obowiązuje lista zakazów z `tasks/ROTA-T009/brief.md:46-66`.

Dodatkowo, specyficznie dla testów: nie powstaje nowy framework testowy, nowa
warstwa fixture'ów ani generator scenariuszy. Zwykły pytest i prawdziwy
tymczasowy SQLite wystarczą — tak jak w `tests/test_t010_bootstrap_roster.py`.
Nie wolno dodawać helpera w `tests/support/`: to trzeci plik, więc łamie
`MAX_NEW_FILES`, a przy okazji stworzyłoby dokładnie tę pośrednią warstwę, przez
którą import persistence mógłby wrócić niezauważony.

## DEPENDENCY BOUNDARY

Testy w tym tasku wołają wyłącznie `rota.application.*` i `rota.domain`.
Import `rota.persistence` w którymkolwiek z dwóch plików — bezpośredni lub przez
helper — jest FAIL tego tasku, nie szczegółem stylu.

Dopuszczone jest odczytanie `rota.planning.validator.validate` w Teście 2, bo
jest to niezależny walidator używany jako druga, zewnętrzna opinia o kandydacie
— dokładnie w roli, w jakiej występuje w istniejącym kontrakcie.

## ZAKRES — TEST 1: pełny happy path, zero warunków brzegowych

Jeden ciągły scenariusz, wyłącznie przez publiczne funkcje `rota.application.*`:

1. `store.open_store()` na nieistniejącym pliku — pusty magazyn.
2. `bootstrap.bootstrap_or_resume_coordinator_context()` — Coordinator,
   SiteProfile, Site, Association; w co najmniej dwóch wywołaniach z częściowymi
   danymi, żeby dowieść wznowienia („resume"), a nie tylko pierwszego zapisu.
3. `durable_inputs.update_employee()` + `update_membership()` dla
   kilkuosobowej obsady LOCAL.
4. `durable_inputs.set_target_hours()` dla każdego pracownika.
5. `durable_inputs.set_calendar_day()` dla każdego dnia planowanego miesiąca.
6. `bootstrap.month_plan_readiness()` — musi zwrócić `ready=True` PRZED próbą
   PLAN. To jest dowód, że odczyt gotowości odzwierciedla dokładnie to, co
   `plan_month()` zaraz zaakceptuje, a nie osobną heurystykę.
7. `plan_ops.plan_month()` — oczekiwany `FEASIBLE`.
8. `plan_ops.select_candidate()` — pierwsza utrwalona `ScheduleVersion`.
9. `open_month.open_month()` — odczyt potwierdza bieżącą wersję i dane wejściowe.
10. Jedna legalna ręczna korekta przez `manual_edit.apply_manual_correction()`
    albo `manual_edit.mark_not_worked()`.
11. `lifecycle_ops.revalidate()`, następnie `lifecycle_ops.finalize()` z
    dokładnym zestawem potwierdzonych `Deviation`.
12. Zamknięcie połączenia i ponowne `store.open_store()` na tym samym pliku:
    `open_month()` zwraca identyczny stan jak przed restartem, w szczególności tę
    samą bieżącą wersję i ten sam status FINAL.

Test NIE wprowadza żadnych błędów, kolizji ani warunków brzegowych. Ma dowieść,
że sama sekwencja „od zera do sfinalizowanego grafiku" przez publiczne API
działa bez skrótów.

Zestaw potwierdzanych `Deviation` w kroku 11 musi być pobrany z warstwy
aplikacji (po `revalidate` przez `assembler.assemble_planning_state`, pole
`state.deviations`), nie zbudowany ręcznie w teście — inaczej test dowodziłby
własnych założeń, nie zachowania systemu.

## ZAKRES — TEST 2: zatrzymanie na HARD i dwie legalne drogi dalej, żadnej trzeciej

Scenariusz, w którym `plan_month()` nie jest w stanie osiągnąć `FEASIBLE` z
powodu realnej kolizji HARD — na przykład jedyny eligible pracownik na dany
demand ma aktywną `SiteRuleVersion` typu
`EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`, zakazującą mu akurat tego rodzaju
zmiany w tym dniu tygodnia. Regułę zapisuje
`rule_decisions.record_structured_rule_decision()`.

Test dowodzi dokładnie trzech rzeczy, z których każda jest już w kontrakcie, ale
nigdy nie zostały połączone w jeden dowód:

1. **Silnik się zatrzymuje, nie „przepycha" grafiku.** `plan_month()` zwraca
   `DECISION_REQUIRED`, a nie `FEASIBLE` z ukrytym naruszeniem HARD. Jeśli
   zwrócony zostanie jakikolwiek kandydat, niezależny `validator.validate()`
   potwierdza na nim `hard_pass=False`.
2. **Droga A — ręczny zapis.** `manual_edit.apply_manual_correction()` z ręcznie
   dobranym Assignmentem. Jeśli koordynator wskaże innego, faktycznie eligible
   pracownika, grafik przechodzi bez nowej `Deviation`. Jeśli uparcie zapisze
   coś, co nadal łamie ten sam HARD, zapis się udaje, ale walidacja
   materializuje `Deviation` — naruszenie pozostaje widoczne i nie znika po cichu.
3. **Droga B — jawna korekta reguły przez Decision Ledger.**
   `rule_decisions.record_structured_rule_decision()` z `rel="corrects"` albo
   `"rejects"`, żeby faktycznie zmienić lub wycofać blokującą `SiteRuleVersion`.
   Dopiero PO tej zmianie ponowne `plan_month()` zwraca `FEASIBLE`. Zmiana jest
   audytowalną, historyczną decyzją — `memory_read` musi ją pokazać w łańcuchu
   rodziny reguły.

Test musi też wykazać, że **nie istnieje trzecia droga**: nie ma żadnej funkcji
aplikacyjnej pozwalającej zignorować ten HARD i zaplanować mimo niego, bez
jednej z dwóch jawnych, zapisanych w historii akcji koordynatora. To jest
właściwy przedmiot tego testu — nie mechanika PLAN, a dowód, że system nie ma
cichego wyłącznika bezpieczeństwa.

Dowód braku trzeciej drogi ma być pozytywnym stwierdzeniem o powierzchni API
(żadna publiczna funkcja `rota.application.*` nie przyjmuje parametru
wyłączającego HARD ani nie zapisuje kandydata z `hard_pass=False` przez
`select_candidate`), a nie próbą wyliczenia wszystkich możliwych obejść.
W szczególności: `plan_ops.select_candidate()` z kandydatem łamiącym HARD musi
podnieść `CandidateRejected`.

## OUT OF SCOPE

- Zmiana czegokolwiek w `rota/` — ten task nie modyfikuje kodu produkcyjnego.
- Domykanie luk audytowych — to robią T011-A/B/C/D.
- Testowanie funkcji dodawanych przez T011-B/C/D (odkrywanie kontekstu, cykl
  życia Site, saldo kwartalne). T011-E dowodzi łańcucha, który istnieje po
  T011-A; rozszerzenie dowodu o B/C/D jest osobną decyzją, gdy te taski
  wejdzą.
- Dokładny kształt fixture'u (liczba pracowników, konkretny `rule_kind` użyty do
  zablokowania) — to szczegół implementacyjny w granicach opisanych scenariuszy.
- Wydajność, benchmark, real-object benchmark.
- UI/IPC/desktop — T012.

## WYMAGANE TESTY

Ten task **jest** testami; sekcja opisuje warunki uznania ich za wystarczające.

1. Oba pliki przechodzą na czystym, tymczasowym pliku bazy, bez współdzielonego
   stanu między nimi.
2. Ani jeden import `rota.persistence` w obu plikach — sprawdzalne mechanicznie,
   np. przez `rg "rota.persistence" tests/test_t011_e_*.py` zwracające zero
   trafień. Audytor ma to sprawdzić niezależnie.
3. Test 1 przechodzi wszystkie 12 kroków w jednym ciągłym scenariuszu, nie jako
   12 niezależnych testów z własnymi fixture'ami — ciągłość jest tu przedmiotem
   dowodu.
4. Krok 12 (restart) porównuje stan przed i po, a nie tylko sprawdza, że odczyt
   nie rzucił wyjątku.
5. Test 2 zawiera wszystkie trzy dowody plus dowód braku trzeciej drogi;
   `CandidateRejected` z `select_candidate` jest asertowane wprost.
6. `SIZE_FILE` (600 linii na plik) jest realnym ryzykiem dla scenariusza z 12
   krokami — jeśli Test 1 zbliża się do limitu, należy to zgłosić jako finding,
   a nie ciąć kroków ani wyprowadzać helpera do trzeciego pliku.

## ENGINEERING GATES

- T011-A zmergowane i zielone (warunek wstępny, nie zalecenie);
- istniejąca suite PASS;
- oba nowe pliki PASS;
- ROTA-REG-001 bez zmian — ten task nie dotyka silnika, więc jakakolwiek zmiana
  oracle jest sygnałem, że scope został naruszony;
- Ruff PASS na plikach z TASK_SCOPE;
- `test_18_dependency_boundary_scan` nadal PASS;
- `SIZE_FILE`/`SIZE_FUNC` PASS.

Oczekiwany, dopuszczalny wynik `backend.py`: `WYMAGA_DECYZJI` na `TOTAL_LINES`,
niemal pewny przy dwóch pełnych scenariuszach E2E. To nie jest FAIL i nie wolno
go obchodzić przez okrojenie dowodu.

## ACCEPTANCE

T011-E jest kompletne, gdy w repo istnieje dowód, że koordynator (a więc i
przyszłe UI) przechodzi od pustego pliku bazy do sfinalizowanego grafiku i przez
restart, nie znając SQLite i nie importując `rota.persistence` — oraz że
napotkany HARD zatrzymuje planowanie i da się go przejść wyłącznie dwiema
jawnymi, zapisanymi w historii drogami.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. czy oba scenariusze są wykonalne w całości przez `rota.application.*` po
   T011-A — jeśli którykolwiek krok wymaga persistence, jest to finding
   kontraktowy, nie problem implementacji;
2. czy dowód „nie ma trzeciej drogi" jest postawiony jako sprawdzalne
   stwierdzenie o powierzchni API, a nie jako niemożliwe do zamknięcia
   wyliczanie obejść;
3. czy rozstrzygnięcie kolizji nazwy (T011-E + usunięcie
   `arch/T011_architect_brief.md`) nie gubi żadnej treści dokumentu źródłowego;
4. czy limit dwóch nowych plików jest realistyczny dla obu scenariuszy, czy
   kontrakt wymusza tu nieuczciwe cięcie dowodu;
5. wycieku zakresu do T011-B/C/D lub T012.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
