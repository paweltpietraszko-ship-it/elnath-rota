# TASK_CONTRACT

TASK_ID: ROTA-T011-E
TITLE: Dowód E2E — pełny łańcuch koordynatora wyłącznie przez warstwę aplikacji
STATUS: DRAFT FOR CODEX AUDIT — ROUND 2 (po FAIL round 1)
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — ten task nie zmienia
zachowania produktu, tylko dowodzi zachowania już zakontraktowanego.

INTEGRATED_BASE_SHA: 029107be9045d2759e77450a0fb943a04483932c
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
(obecny na `main` do `029107b` włącznie), przygotowanego przez CC po przeglądzie
stanu projektu po merge T010. Tamten dokument nazwał siebie „T011 (proponowane)" i
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

## PROCES — BRAMKA MECHANICZNA: STAN POTWIERDZONY

Wcześniejsza blokada `FROZEN_LOCK` (hash `arch/spec.md` policzony z CRLF plus
pole `FILE:` z backslashem, `backend.py:61-82` i `guard.py:90-92`) została
naprawiona poza zakresem T011 (`20f08f9`, zmergowane w `0175d71`) i
zweryfikowana na `029107b`: `guard.py check arch/spec.md` → `STATUS: PASS`,
`backend.check_frozen_lock()` → brak blockera. Szczegóły w
`tasks/ROTA-T011-A/brief.md`.

`arch/FROZEN.lock` pozostaje poza TASK_SCOPE. Jeśli `FROZEN_LOCK` zgłosi
cokolwiek podczas implementacji, jest to NOWY problem — zgłoś go, nie obchodź.

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

## ZAKRES — TEST 2: zatrzymanie na HARD i brak cichego obejścia

Scenariusz, w którym `plan_month()` nie jest w stanie osiągnąć `FEASIBLE` z
powodu realnej kolizji HARD — na przykład jedyny eligible pracownik na dany
demand ma aktywną `SiteRuleVersion` typu
`EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`, zakazującą mu akurat tego rodzaju
zmiany w tym dniu tygodnia. Regułę zapisuje
`rule_decisions.record_structured_rule_decision()`.

Test dowodzi trzech rzeczy, z których każda jest już w kontrakcie, ale nigdy nie
zostały połączone w jeden dowód. Dwie pierwsze to przykłady legalnych dróg
wyjścia, **nie** zamknięty katalog — patrz sekcja o braku cichego obejścia niżej:

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

### Brak cichego obejścia HARD — właściwy przedmiot tego testu (FINDING E-1)

Pierwsza wersja tego briefu twierdziła, że po HARD istnieją **wyłącznie dwie
drogi** wyjścia. To twierdzenie było fałszywe i sprzeczne z zamrożonym
kontraktem. `tasks/ROTA-T009/brief.md:239-240` opisuje obowiązkowy przepływ
„PLAN → DECISION_REQUIRED → koordynator zmienia jeden durable input (na przykład
dodaje okno X) → PLAN ponownie na świeżym PlanningState", a `arch/spec.md`
w sekcji DECISION_REQUIRED wymaga pokazania **klas** odblokowania, nie zamkniętej
listy dwóch pozycji.

Legalnych dróg jest więcej i część nie dotyka blokującej reguły: dodanie albo
ponowne włączenie innego eligible pracownika (`durable_inputs.update_employee` +
`update_membership`), dodanie okna wsparcia zewnętrznego, wycofanie nieobecności
przez `append_availability`, zmiana konfiguracji profilu przez
`update_site_profile`. Po każdej z nich `plan_month` może legalnie zwrócić
`FEASIBLE`, przy nadal aktywnej regule, bez ręcznego Assignmentu i bez
`corrects`/`rejects`. To nie jest obejście HARD — to jawna zmiana wejścia,
dokładnie model DECISION_REQUIRED.

Test dowodzi zatem inwariantu węższego i prawdziwego: **nie istnieje ciche
obejście HARD.** Dowód ma być pozytywnym stwierdzeniem o powierzchni API, nie
próbą wyliczenia wszystkich dróg:

- żadna publiczna funkcja `rota.application.*` nie przyjmuje parametru
  wyłączającego, pomijającego ani osłabiającego HARD;
- `plan_ops.select_candidate()` z kandydatem łamiącym HARD podnosi
  `CandidateRejected` — nie da się utrwalić takiego kandydata jako grafiku;
- `manual_edit.apply_manual_correction()` **wolno** zapisać stan łamiący HARD, ale
  naruszenie zostaje wtedy widoczne jako `Deviation` i nie znika po cichu;
- każda droga do `FEASIBLE` albo spełnia regułę na istniejących danych, albo
  zmienia dane wejściowe jawnie przez funkcję aplikacyjną, albo zmienia samą
  regułę przez Decision Ledger. Żadna nie planuje wbrew regule bez śladu.

Test **nie może** twierdzić ani asertować, że katalog legalnych zmian wejścia jest
zamknięty do dwóch pozycji. Gdyby intencją produktu naprawdę było zamknięcie
pozostałych klas odblokowania, wymagałoby to jawnej decyzji właściciela
zmieniającej istniejący kontrakt DECISION_REQUIRED — i nie jest przedmiotem
T011-E.

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
5. Test 2 zawiera wszystkie trzy dowody plus dowód braku cichego obejścia HARD;
   `CandidateRejected` z `select_candidate` jest asertowane wprost. Test nie
   asertuje, że legalnych dróg wyjścia jest dokładnie dwie.
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
napotkany HARD zatrzymuje planowanie i nie istnieje ciche obejście: każde
przejście dalej jest albo jawną zmianą danych wejściowych przez funkcję
aplikacyjną, albo jawną zmianą reguły w Decision Ledger, albo zapisem ręcznym z
widocznym `Deviation`.

## ZMIANY PO AUDYCIE KONTRAKTU — ROUND 1

Raport: `tasks/ROTA-T011-E/round_01/tests/tests_r1.txt` (werdykt FAIL, jeden
finding, audytowany SHA `7670b2d`).

**FINDING E-1 — zamknięty.** Test 2 twierdził, że po HARD istnieją wyłącznie dwie
drogi wyjścia. Twierdzenie było fałszywe i sprzeczne z obowiązkowym przepływem
z `tasks/ROTA-T009/brief.md:239-240` oraz z modelem DECISION_REQUIRED w
`arch/spec.md`: dodanie innego eligible pracownika, okna wsparcia, wycofanie
nieobecności czy zmiana profilu też prowadzą legalnie do `FEASIBLE`, przy nadal
aktywnej regule. Dowód został zawężony do inwariantu prawdziwego — braku
**cichego obejścia HARD** — z jawnym zakazem asertowania zamkniętego katalogu
dróg. Poprawiono tytuł sekcji, treść dowodu, warunek 5 wymaganych testów,
ACCEPTANCE i punkt 2 review requestu.

Reszta raportu round 1 była PASS: wykonalność 12 kroków happy path przez samo
API aplikacji, poprawność twardej zależności od T011-A, dostępność
`Deviation` do finalize przez `assemble_planning_state`, realność limitu dwóch
plików testowych, oraz brak utraty treści przy przeniesieniu
`arch/T011_architect_brief.md`.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. czy oba scenariusze są wykonalne w całości przez `rota.application.*` po
   T011-A — jeśli którykolwiek krok wymaga persistence, jest to finding
   kontraktowy, nie problem implementacji;
2. czy dowód braku cichego obejścia HARD jest postawiony jako sprawdzalne
   stwierdzenie o powierzchni API i czy nigdzie nie został ślad po fałszywym
   twierdzeniu o zamkniętym katalogu dwóch dróg;
3. czy rozstrzygnięcie kolizji nazwy (T011-E + usunięcie
   `arch/T011_architect_brief.md`) nie gubi żadnej treści dokumentu źródłowego;
4. czy limit dwóch nowych plików jest realistyczny dla obu scenariuszy, czy
   kontrakt wymusza tu nieuczciwe cięcie dowodu;
5. wycieku zakresu do T011-B/C/D lub T012.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
