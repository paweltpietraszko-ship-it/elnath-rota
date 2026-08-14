# TASK_CONTRACT

TASK_ID: ROTA-T011-D
TITLE: Domknięcie salda kwartalnego — jawny odczyt kwartału i realny carry-in w assemblerze
STATUS: DRAFT FOR CODEX AUDIT
DATE: 2026-08-14
ARCHITECT_ROLE: Cursor (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — wszystkie decyzje
produktowe tego tasku są rozstrzygnięte (B-4=W3, B-5=W2 wraz z kształtem
degradacji rozstrzygniętym 2026-08-14).

INTEGRATED_BASE_SHA: 029107be9045d2759e77450a0fb943a04483932c
BASE_BRANCH_AT_FREEZE: main

TASK_SCOPE:
- rota/application/balance_read.py
- rota/application/assembler.py
- tests/test_t011_d_quarter_balance.py

Powyższa lista jest zamknięta. `rota/application/balance_read.py` i plik testowy
są jedynymi dwoma nowymi plikami — dokładnie limit `MAX_NEW_FILES = 2`.

## ŹRÓDŁA

- `arch/AUDIT_PIPELINE_COMPLETENESS_2026-08-14.md` — znaleziska Z-5, Z-6, Z-9.
- `arch/T011_pipeline_closure_proposal_2026-08-14.md` — punkt A-5, pytania B-4
  i B-5 z rozstrzygnięciami oraz CONSTRAINT do B-5.
- `arch/OWNER_DECISION_T010_PANEL_STEROWANIA_2026-08-13.md` §3 („Brak
  `target_hours` nie blokuje PLAN") i §10 (TARGET-01 bez zmian, pozostaje SOFT).
- `rota/balance.py:3-9` — cytat z `arch/spec.md` o WorkBalance SCOPE BOUNDARY.

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

`work_balance_repository.reconstruct_quarter_balance` (`:68-81`) nie ma ani
jednego wołającego w `rota/application/*`. Jedyny wystawiony odczyt salda,
`assembler._assemble_work_balances` (`assembler.py:121-128`), woła
`reconstruct_month_balance` bez argumentu `quarter_balance_before`, którego
wartość domyślna to `0` (`work_balance_repository.py:57`, `balance.py:57`). Przy
zerowym przeniesieniu `compute_month_balance` zwraca
`quarter_balance == unresolved_carryover == month_balance` (`balance.py:84-93`).

Skutek: `open_month` zawsze pokazuje miesiąc w izolacji, a pola
`quarter_balance` i `unresolved_carryover` są mylące — mają nazwę sugerującą
saldo narastające, a zawierają saldo miesiąca. Narastające saldo kwartału, które
`arch/spec.md` przypisuje odpowiedzialności koordynatora, nie jest osiągalne
przez warstwę aplikacji w żadnej formie.

T011-D domyka Z-6 w obu częściach: dokłada jawny odczyt kwartału i naprawia
kontekst planowania.

## DECYZJE JUŻ PODJĘTE, KTÓRE TEN TASK REALIZUJE

**B-5 = W2**: obok osobnego odczytu (A-5) `assembler._assemble_work_balances`
liczy realny carry-in. Uzasadnienie właściciela: zostawienie samego W1
oznaczałoby, że `open_month` dalej kłamie, co jest gorsze niż brak danych.

**Dowód bezpieczeństwa dla silnika** (sprawdzony w kodzie, wiążący dla audytu):
solver czyta ze `state.work_balances` wyłącznie `wb.target_hours`
(`rota/planning/solver.py:320-321`) i nigdzie nie czyta `quarter_balance`,
`unresolved_carryover` ani `month_balance`. Ranking TARGET-01 i oracle
ROTA-REG-001 nie mogą się więc przez tę zmianę przesunąć. Testy asertujące te
pola dotyczą wyłącznie czystych funkcji `rota.balance`
(`tests/test_balance.py:44-55`), nie wyjścia assemblera. §10 decyzji właściciela
(„T010 nie zmienia semantyki TARGET-01") pozostaje spełniony, bo zmiana dotyczy
tylko odczytu salda, nie wejścia solvera.

## CONSTRAINT — B-5/W2 NIE JEST GOŁYM PODPIĘCIEM ISTNIEJĄCEJ FUNKCJI

To jest doprecyzowanie już podjętej decyzji W2, nie nowy wybór.

`rota.balance.compute_quarter_balance` podnosi `MissingTargetHoursError`, jeśli
KTÓRYKOLWIEK z trzech miesięcy kwartału nie ma `target_hours` — w tym miesiące
PO planowanym (`balance.py:106-116`, pętla `for offset in range(3)`).

Gdyby assembler po prostu wołał `reconstruct_quarter_balance`, planowanie
września wymagałoby z góry `target_hours` na październik i listopad. Złamałoby
to zamrożone „brak `target_hours` nie blokuje PLAN"
(`OWNER_DECISION_T010…` §3, `tasks/ROTA-T010/part_a_bootstrap_roster.md`,
zachowanie `bootstrap.month_plan_readiness`).

Wymóg wiążący:

1. Carry-in liczony **wyłącznie z miesięcy kwartału do planowanego włącznie** —
   nigdy z miesięcy po nim.
2. Dla pierwszego miesiąca kwartału carry-in wynosi `0` — to jest istniejąca
   semantyka `quarter_balance_before` (`balance.py:59-62`).
3. Brak `target_hours` **nigdy** nie może stać się wyjątkiem blokującym
   `assemble_planning_state`. Degradacja pozostaje taka jak dziś: ostrzeżenie w
   liście zwracanej przez `assemble_planning_state`, pracownik pomijany w
   `work_balances`, PLAN działa dalej (`assembler.py:124-127`).
4. Liczba i treść dzisiejszych ostrzeżeń dla miesiąca planowanego nie może się
   zmienić — dochodzą co najwyżej ostrzeżenia dotyczące wcześniejszych miesięcy
   kwartału, w kształcie opisanym w sekcji JEDNA REGUŁA DEGRADACJI DLA OBU
   ODCZYTÓW.

## ZAKRES — A-5: jawny odczyt kwartału

Moduł docelowy: nowy `rota/application/balance_read.py`, wzorowany kształtem na
całym `rota/application/memory_read.py` (cienki modul odczytów bez guardu
kontekstu, delegujący bez zmiany kształtu wyniku).

Sygnatura (wiążąca):

```text
def quarter_balance(conn, *, employee_id: str, quarter_first_month: date) -> tuple[list[WorkBalance], list[str]]
```

Kształt wyniku `(dane, ostrzeżenia)` jest kopią istniejącej konwencji
`assembler.assemble_planning_state` (`assembler.py:182-185`, zwraca
`tuple[PlanningState, list[str]]`), a styl modułu — całego
`rota/application/memory_read.py`. Delegacja:
`work_balance_repository.reconstruct_quarter_balance` (`:68-81`).

**ROZSTRZYGNIĘCIE WŁAŚCICIELA (2026-08-14): `quarter_balance` degraduje się do
ostrzeżenia, nie podnosi `MissingTargetHoursError`.** Zastępuje to wcześniejszą
notatkę architekta, która pozostawiała temu odczytowi surową semantykę.

Kształt degradacji: gdy któremuś miesiącowi kwartału brakuje normy, odczyt
zwraca **pustą listę bilansów** i ostrzeżenie nazywające brakujący miesiąc.
Nigdy nie podnosi `MissingTargetHoursError` i nigdy nie zwraca liczb policzonych
częściowo.

Implementacja pozostaje cienka: wołanie `reconstruct_quarter_balance` i
przechwycenie `MissingTargetHoursError` z zamianą na ostrzeżenie. **Nie wolno**
odtwarzać w warstwie aplikacji pętli po miesiącach z `rota.balance.compute_quarter_balance`
— duplikacja istniejącej logiki jest w tym repo błędem architektonicznym
(`tasks/ROTA-T010/brief.md`: „Reuse istniejącej logiki jest obowiązkowy.
Duplikacja = FAIL architektoniczny").

Świadomie przyjęta konsekwencja, którą trzeba znać: w trakcie kwartału, dopóki
normy na jego przyszłe miesiące nie są ustawione, ten odczyt zwraca puste dane
i ostrzeżenie. Nie jest to defekt, a podział odpowiedzialności między dwoma
odczytami: `open_month` pokazuje saldo narastające **do miesiąca planowanego
włącznie** (część B-5/W2 niżej) i jest właściwym miejscem na obraz „na teraz",
a `quarter_balance` jest raportem całego kwartału i staje się dostępny, gdy
kwartał ma wszystkie normy.

## ZAKRES — B-5/W2: carry-in w assemblerze

Zmiana ograniczona do `rota/application/assembler.py`, w praktyce do
`_assemble_work_balances` (`assembler.py:121-128`) i jej wywołania
(`assembler.py:207`).

Nie wolno: dodawać nowej funkcji w `rota/persistence`, zmieniać
`reconstruct_month_balance`/`reconstruct_quarter_balance`, zmieniać `rota/balance.py`,
ani dotykać `rota/planning/*`. `quarter_balance_before` jest już parametrem
`reconstruct_month_balance` (`work_balance_repository.py:56-57`), więc assembler
ma czym przekazać carry-in bez żadnej nowej funkcji.

## JEDNA REGUŁA DEGRADACJI DLA OBU ODCZYTÓW

Rozstrzygnięcie z 2026-08-14 („saldo kwartalne degraduje się do ostrzeżenia przy
braku normy we wcześniejszym miesiącu — tak jak zapisany constraint w B-5, i ta
sama degradacja obowiązuje nowy odczyt A-5") daje jedną regułę wiążącą dla
całego tasku:

**Nigdy nie pokazujemy liczby narastającej policzonej ponad luką w normach.
Zamiast liczby częściowej jest ostrzeżenie nazywające brakujący miesiąc.**

Ta sama reguła w dwóch kształtach, bo odczyty mają różne kształty wyniku:

- **`quarter_balance` (A-5)** — brak normy w którymkolwiek miesiącu kwartału daje
  pustą listę bilansów plus ostrzeżenie. Nie zwraca prefiksu miesięcy przed luką,
  bo raport kwartału bez części kwartału wyglądałby jak kompletny.
- **Kontekst planowania (`assembler`, B-5/W2)** — brak normy w którymkolwiek
  wcześniejszym miesiącu tego kwartału powoduje, że pracownik jest **pomijany
  w `work_balances`** dla planowanego miesiąca, z ostrzeżeniem nazywającym
  miesiąc bez normy. Jest to dokładnie ten sam kształt degradacji, który
  assembler stosuje dziś, gdy normy brakuje w samym planowanym miesiącu
  (`assembler.py:124-127`) — nie powstaje żadna nowa ścieżka zachowania.

Konsekwencja do świadomego przyjęcia: pracownik, który ma normę na planowany
miesiąc, ale nie ma jej na wcześniejszy miesiąc tego samego kwartału, zniknie
z `work_balances` — dziś by się tam pokazał z saldem miesięcznym. To jest
widoczna zmiana zachowania dla istniejących danych i jest zamierzona: liczba
narastająca policzona ponad luką byłaby myląca w sposób, którego UI nie ma jak
wykryć. `target_hours` pozostaje przy tym wyłącznie SOFT i nadal **nigdy** nie
blokuje PLAN — pominięcie w bilansie nie ma wpływu na planowanie, bo solver
czyta z `work_balances` tylko `target_hours` tych pracowników, którzy tam są.

INTERPRETACJA DO POTWIERDZENIA PRZEZ AUDYT: rozstrzygnięcie właściciela mówiło
„ta sama degradacja", nie wskazując wprost liczby. Powyższy kształt jest
odczytaniem „ta sama" jako „ten sam mechanizm, który assembler stosuje dziś",
czyli pominięcie plus ostrzeżenie — a nie carry-in policzony z części miesięcy.
Gdyby właściciel miał w myśli carry-in częściowy (suma miesięcy, które normę
mają, z ostrzeżeniem o pominiętym), zmienia się wyłącznie ta sekcja i punkt 7
wymaganych testów; reszta briefu zostaje bez zmian.

## B-1 JEST DOMKNIĘTE PRZEZ T011-A — SPRAWDZONE

Kontrakt potwierdza to, o co pytano osobno: rozstrzygnięcie B-1=W1 („zapis per
dzień, UI woła w pętli") jest w całości realizowane przez A-1 w
`tasks/ROTA-T011-A/brief.md` i nie pozostawia żadnej pracy dla T011-D.
Odrzucony wariant W2 (atomowe „wypełnij miesiąc") wymagałby nowego prymitywu w
`calendar_repository` — nie powstaje. Odłożony dodatek z W3 (źródło dni
świątecznych) właściciel jawnie wyłączył z T011. W T011-D nie ma więc żadnego
punktu kalendarzowego.

## B-4 JEST DOMKNIĘTE DECYZJĄ, NIE KODEM

Rozstrzygnięcie B-4=W3: **brak odtwarzania z backupu w produkcie.** Uzasadnienie
właściciela: nadpisanie w miejscu (W1) to nieodwracalna akcja
jednokliknięciowa wysokiego ryzyka, której unika się w całym projekcie; W2
wymaga trzymania stanu „która baza jest aktywna", czego `tasks/ROTA-T009/brief.md:355`
wprost zakazuje.

Skutki dla implementacji: **zero**. CC nie dodaje żadnej funkcji odtwarzania ani
w `rota/application`, ani w `rota/persistence`. `backup.backup_database` i
`build_diagnostic_zip` zostają bez zmian. Odtworzenie kopii pozostaje procedurą
operacyjną poza aplikacją.

Konsekwencja dla Z-9 (odczyt historycznej wersji sprzężony z kompletnością
kalendarza tego miesiąca, `assembler.py:188` przed `:194`): przy B-4=W3 znika
jedyna realna droga dojścia do stanu „istnieje wersja, brakuje dni kalendarza",
bo w repo nie istnieje żadna funkcja usuwająca wiersze z `calendar_days`, a
wypełniony kalendarz jest warunkiem wstępnym zaplanowania miesiąca. Z-9
pozostaje więc trwale informacyjne i **nie jest** przedmiotem żadnej części
T011. Gdyby kiedykolwiek powstał import danych legacy, wraca jako osobne pytanie.

## ANTI-BUREAUCRACY RULE

Obowiązuje lista zakazów z `tasks/ROTA-T009/brief.md:46-66`.

Dodatkowo: żadnej klasy raportu, żadnego cache'u salda, żadnego drugiego źródła
prawdy o bilansie. `arch/spec.md` (cytat w `rota/balance.py:1-9`) mówi wprost, że
WorkBalance jest rekonstruowany, nie przechowywany — T011-D tego nie zmienia.
Nie powstaje pole `effective_hours` ani żadne inne nowe pole w `WorkBalance`.

## DEPENDENCY BOUNDARY

Bez zmian względem `tasks/ROTA-T009/brief.md:68-91`. Cała zmiana mieści się w
`rota/application/*`; `rota/planning/*` i `rota/persistence/*` pozostają
nietknięte.

## OUT OF SCOPE

- Odtwarzanie z backupu w jakiejkolwiek formie (B-4=W3).
- Zmiany w `rota/balance.py`, `rota/persistence/work_balance_repository.py`,
  `rota/planning/*`.
- Nowe pola w `WorkBalance`.
- Rozliczenia kadrowe/płacowe — `arch/spec.md` wyklucza je z Rota.
- Zmiana semantyki TARGET-01 (§10 decyzji właściciela).
- Z-9 (patrz wyżej).
- Wszystko z T011-A/B/C/E.

## WYMAGANE TESTY

Jeden nowy plik `tests/test_t011_d_quarter_balance.py`, prawdziwy tymczasowy
SQLite. Scenariusze, nie nazwy. Punkty 1-3 dotyczą A-5, punkty 4-7 części
B-5/W2; wszystkie są w zakresie tego tasku — nic nie czeka już na decyzję.

1. **Odczyt kwartału narasta.** Pracownik z normami na wszystkie trzy miesiące
   kwartału i pracą w każdym: `quarter_balance` zwraca trzy pozycje w kolejności
   miesięcy i pustą listę ostrzeżeń, a `quarter_balance` każdej kolejnej pozycji
   jest sumą narastającą, różną od jej `month_balance` (dowód, że carry-in
   faktycznie działa, a nie tylko przepisuje saldo miesiąca).
2. **Odczyt kwartału degraduje, nie rzuca.** Brak normy w którymkolwiek miesiącu
   kwartału — w tym w miesiącu przyszłym — daje pustą listę bilansów i
   ostrzeżenie nazywające brakujący miesiąc. `MissingTargetHoursError` **nie**
   wydostaje się z tej funkcji. Test musi mieć komentarz mówiący, że pusty wynik
   mid-kwartał jest zamierzony, nie przeoczenie.
3. **Odczyt kwartału nie wymaga kontekstu koordynatora.** Wywołanie bez aktywnej
   asocjacji zwraca dane, zgodnie z konwencją odczytów w tym repo.
4. **`open_month` przestaje kłamać.** Dla drugiego miesiąca kwartału, z pracą i
   normą w miesiącu pierwszym, `WorkBalance` zwrócony w `OpenMonthView` ma
   `quarter_balance` różne od `month_balance` — dziś są zawsze równe.
5. **Pierwszy miesiąc kwartału.** Carry-in wynosi `0`, więc `quarter_balance`
   równa się `month_balance`. To jedyny przypadek, w którym ta równość jest
   poprawna.
6. **Brak normy nie blokuje PLAN.** Miesiąc planowany ma normę, wcześniejszy
   miesiąc kwartału jej nie ma: `assemble_planning_state` **nie** rzuca,
   `plan_month` nadal zwraca wynik planowania, a `month_plan_readiness` nadal
   `ready=True`. To jest test zamrożonego wymogu, nie detalu.
7. **Kształt degradacji w kontekście planowania.** Pracownik z normą na
   planowany miesiąc, ale bez normy na wcześniejszy miesiąc tego kwartału, jest
   **pomijany** w `state.work_balances`, a `assemble_planning_state` zwraca
   ostrzeżenie nazywające miesiąc bez normy. Żadna liczba narastająca policzona
   ponad luką nie pojawia się w wyniku. Drugi pracownik, mający normy na oba
   miesiące, jest w `work_balances` obecny — dowód, że degradacja jest
   per-pracownik, nie globalna.
8. **Silnik nietknięty.** ROTA-REG-001 bez zmian; dodatkowo test dowodzący, że
   dla tego samego wejścia `plan_month` zwraca ten sam status i tę samą liczbę
   kandydatów przed i po zmianie carry-in (dowód, że solver czyta tylko
   `target_hours`).
9. **Restart.** Po zamknięciu i ponownym otwarciu magazynu oba odczyty dają te
   same liczby.

## ENGINEERING GATES

- istniejąca suite PASS;
- nowe testy T011-D PASS;
- **ROTA-REG-001 bez zmian — to jest gate krytyczny dla tego tasku**, bo jedyna
  zmiana dotyka assemblera, który produkuje `PlanningState`;
- Ruff PASS na plikach z TASK_SCOPE;
- `test_18_dependency_boundary_scan` nadal PASS;
- `SIZE_FILE`/`SIZE_FUNC` PASS — `assembler.py` ma dziś 220 linii;
  `_assemble_work_balances` musi zostać poniżej 50 linii.

Oczekiwany, dopuszczalny wynik `backend.py`: `WYMAGA_DECYZJI` na `TOTAL_LINES`
przy przekroczeniu 150 zmienionych linii.

## ACCEPTANCE

T011-D jest kompletne, gdy koordynator przez `rota/application/*` widzi
narastające saldo kwartału w dwóch spójnych miejscach — jawnym odczycie kwartału
i w kontekście otwartego miesiąca — a brak `target_hours` nadal nigdy nie
blokuje PLAN.

Znalezisko Z-6 zamknięte. Z-5 zamknięte decyzją właściciela bez kodu. Z-9
zamknięte jako trwale informacyjne.

## REVIEW REQUEST TO CODEX

Audytuj wyłącznie pod kątem:
1. sprzeczności z zamrożoną architekturą, §3 i §10 decyzji właściciela oraz
   WorkBalance SCOPE BOUNDARY z `arch/spec.md`;
2. czy CONSTRAINT (carry-in tylko do miesiąca planowanego, degradacja zamiast
   wyjątku) jest sformułowany tak, że CC nie może go zrealizować gołym
   podpięciem `reconstruct_quarter_balance`;
3. czy dowód „solver czyta tylko `target_hours`" jest poprawny — sprawdź
   `rota/planning/solver.py:320-321` niezależnie, bo na nim opiera się cała ocena
   ryzyka dla ROTA-REG-001;
4. testowalności, zwłaszcza punktów 6, 7 i 8;
5. czy jedna reguła degradacji („nigdy liczba narastająca ponad luką") jest
   zastosowana spójnie w obu odczytach, mimo że mają różny kształt wyniku;
6. czy INTERPRETACJA DO POTWIERDZENIA w sekcji o degradacji jest właściwie
   oznaczona — rozstrzygnięcie właściciela mówiło „ta sama degradacja" bez
   wskazania liczby, a brief odczytuje to jako pominięcie plus ostrzeżenie.
   Jeśli uznasz, że dopuszczalne jest też odczytanie „carry-in częściowy",
   zgłoś to jako finding kontraktowy do decyzji właściciela, nie jako błąd.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
