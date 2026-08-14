# TASK_CONTRACT

TASK_ID: ROTA-T011-D
TITLE: Domknięcie salda kwartalnego — jawny odczyt kwartału i realny carry-in w assemblerze
STATUS: DRAFT FOR CODEX AUDIT — ROUND 2 (po FAIL round 1)
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

**Dowód bezpieczeństwa dla silnika — w wersji poprawionej po FINDING D-1
(round 1), wiążący dla audytu.** Solver nie czyta pól `quarter_balance`,
`unresolved_carryover` ani `month_balance` — czyta wyłącznie `wb.target_hours`
(`rota/planning/solver.py:320-321`). Zmiana wartości tych trzech pól jest więc
dla silnika neutralna.

To **nie wystarcza** jako dowód bezpieczeństwa i pierwsza wersja tego briefu
błędnie na tym poprzestała. Cel TARGET-01 jest budowany **iteracją po
`state.work_balances`**:

```text
rota/planning/solver.py:319-322 (_sick_adjusted_targets)
    return {
        wb.employee_id: max(0, wb.target_hours - ...)
        for wb in state.work_balances
    }
```

Pracownik nieobecny w `state.work_balances` nie ma wpisu w słowniku celów, więc
`_add_objective` (`solver.py:325-353`) nie dodaje dla niego kary TARGET-01 wcale.
Usunięcie pracownika z tego zbioru zmienia zatem przydział godzin, ranking
kandydatów i potencjalnie liczbę zwróconych kandydatów — czyli semantykę
TARGET-01, której §10 decyzji właściciela zmieniać nie pozwala.

Wiążący wniosek: **liczy się nie tylko wartość pól, ale i przynależność do
`state.work_balances`.** Każdy kształt degradacji musi zachować pracownika w tym
zbiorze wraz z jego `target_hours` na planowany miesiąc. Wyklucza to technicznie,
nie preferencyjnie, wariant „pomiń pracownika".

Zachowanie istniejące i nietknięte przez ten task: gdy normy brakuje w **samym
planowanym miesiącu**, pracownik jest pomijany już dziś
(`assembler.py:124-127`) i już dziś nie waży w TARGET-01. T011-D tego nie zmienia
ani w jedną, ani w drugą stronę.

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
   `assemble_planning_state`, ani dla planowanego miesiąca, ani dla
   wcześniejszego miesiąca kwartału.
4. Rozróżnienie dwóch przypadków, których nie wolno mieszać:
   - **normy brakuje w samym planowanym miesiącu** — zachowanie bez zmian wobec
     dzisiejszego: ostrzeżenie plus pominięcie pracownika w `work_balances`
     (`assembler.py:124-127`). Tego T011-D nie dotyka.
   - **normy brakuje w wcześniejszym miesiącu kwartału, planowany miesiąc ma
     normę** — pracownik **zostaje** w `work_balances` ze swoim
     `target_hours`, carry-in wynosi `0`, dochodzi ostrzeżenie nazywające
     brakujący miesiąc. Kształt wiążący opisuje sekcja ROZSTRZYGNIĘCIE
     WŁAŚCICIELA (2026-08-14).
5. Liczba i treść dzisiejszych ostrzeżeń dla miesiąca planowanego nie może się
   zmienić — dochodzą co najwyżej ostrzeżenia dotyczące wcześniejszych miesięcy
   kwartału.

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

## ROZSTRZYGNIĘCIE WŁAŚCICIELA (2026-08-14, po FINDING D-1/D-2): CARRY-IN ZEROWY

Pisemna decyzja właściciela, zamykająca zarówno pytanie o liczbę, jak i konflikt
z TARGET-01. Przy braku normy we wcześniejszym miesiącu kwartału obowiązuje
dokładnie to:

1. `quarter_balance_before = 0` dla planowanego miesiąca — carry-in nie jest
   liczony z części miesięcy;
2. pracownik **pozostaje** w `state.work_balances`;
3. jego `target_hours` na planowany miesiąc **nadal uczestniczy** w TARGET-01;
4. wynik zawiera ostrzeżenie wskazujące brakujący wcześniejszy miesiąc;
5. PLAN nie jest blokowany;
6. nie pokazujemy częściowego salda narastającego ponad luką.

Carry-in **częściowy** (suma miesięcy, które normę mają) jest odrzucony: łamałby
punkt 6. Wariant **pominięcia pracownika** jest odrzucony: łamie punkty 2 i 3 i
jest właśnie tym, co FINDING D-1 wykazał jako sprzeczne z TARGET-01.

Zachowany inwariant, teraz spełnialny w całości: **żadnej liczby narastającej
policzonej ponad luką — i żadnej zmiany w wejściu solvera.** Praktycznie oznacza
to, że dla takiego pracownika `quarter_balance` i `unresolved_carryover` w
kontekście planowanego miesiąca są równe jego `month_balance` (bo carry-in to
zero), a ostrzeżenie mówi, dlaczego nie są narastające. To jest dzisiejsza
liczba, ale po raz pierwszy jawnie opisana jako niepełna, zamiast milcząco
udawać saldo kwartału.

Ta sama reguła w drugim odczycie: **`quarter_balance` (A-5)** przy braku normy w
którymkolwiek miesiącu kwartału zwraca pustą listę bilansów plus ostrzeżenie —
nie prefiks miesięcy przed luką, bo raport kwartału bez części kwartału
wyglądałby jak kompletny. A-5 nie karmi solvera, więc punkty 2 i 3 go nie
dotyczą.

W briefie nie ma już żadnej sekcji proszącej audytora o wybór znaczenia.

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
7. **Carry-in zerowy zachowuje wejście solvera.** Pracownik z normą na planowany
   miesiąc, ale bez normy na wcześniejszy miesiąc tego kwartału:
   - **jest obecny** w `state.work_balances` — asercja na przynależność, nie tylko
     na wartości pól;
   - jego `target_hours` w `work_balances` równa się dokładnie liczbie ustawionej
     przez `set_target_hours` dla planowanego miesiąca;
   - jego `quarter_balance` i `unresolved_carryover` równają się jego
     `month_balance` (carry-in zerowy), a nie sumie z niepełnego kwartału;
   - `assemble_planning_state` zwraca ostrzeżenie nazywające miesiąc bez normy.

   Ten test jest bezpośrednim dowodem zamknięcia FINDING D-1: gdyby pracownik
   wypadł ze zbioru, jego norma zniknęłaby z celu TARGET-01.
8. **Semantyka TARGET-01 nietknięta.** ROTA-REG-001 bez zmian. Dodatkowo dowód
   mocniejszy niż status i liczba kandydatów — te dwie wartości mogą być
   identyczne przy zmienionym rozkładzie godzin, więc same niczego nie dowodzą
   (FINDING D-1, round 1). Wymagane: dla scenariusza z dwoma pracownikami,
   z których jeden ma lukę w normie wcześniejszego miesiąca, zbiór
   `(employee_id, target_hours)` w `state.work_balances` jest identyczny jak w
   scenariuszu kontrolnym, w którym obaj mają wszystkie normy kwartału — czyli
   luka w normie wcześniejszego miesiąca nie zmienia ani składu zbioru, ani
   żadnej normy w nim. Różnić się mają wyłącznie pola salda narastającego i lista
   ostrzeżeń.
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

## ZMIANY PO AUDYCIE KONTRAKTU — ROUND 1

Raport: `tasks/ROTA-T011-D/round_01/tests/tests_r1.txt` (werdykt FAIL +
WYMAGA_DECYZJI, dwa findingi, audytowany SHA `7670b2d`).

**FINDING D-1 — zamknięty.** Brief twierdził, że zmiana carry-in nie może
zmienić solvera, bo solver czyta tylko `target_hours`, i jednocześnie nakazywał
usuwać pracownika z `state.work_balances`. Audyt wykazał, że cel TARGET-01 jest
budowany iteracją po tym zbiorze (`solver.py:319-322`), więc usunięcie wpisu
usuwa normę z funkcji celu i może zmienić przydział godzin. Dowód bezpieczeństwa
został poprawiony (liczy się przynależność, nie tylko wartości pól), wariant
pominięcia jest teraz jawnie wykluczony technicznie, a wymagany test 8 nie opiera
się już na samym statusie i liczbie kandydatów — porównuje zbiór
`(employee_id, target_hours)` ze scenariuszem kontrolnym. Dodano test 7
asertujący wprost obecność pracownika w `work_balances`.

**FINDING D-2 — zamknięty.** Sekcja „INTERPRETACJA DO POTWIERDZENIA PRZEZ AUDYT"
prosiła audytora o wybór znaczenia i została usunięta. Zastąpiła ją pisemna
decyzja właściciela z 2026-08-14 (carry-in zerowy, pracownik zostaje w zbiorze,
norma nadal uczestniczy w TARGET-01, ostrzeżenie, PLAN niezablokowany, brak
częściowego salda). Nagłówek `OWNER_ACCEPTANCE_REQUIRED...: no` jest teraz
zgodny z treścią.

Reszta raportu round 1 była PASS: cienki wrapper A-5 łapiący
`MissingTargetHoursError`, carry-in policzalny przez istniejący parametr
`quarter_balance_before` bez nowych funkcji persistence, brak udziału przyszłych
miesięcy w assemblerze, spójność B-4=W3.

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
5. czy rozstrzygnięcie „carry-in zerowy" jest w całym briefie zastosowane
   spójnie i czy nie został nigdzie ślad po odrzuconym wariancie pominięcia
   pracownika;
6. czy punkt 7 wymaganych testów faktycznie dowodzi zamknięcia FINDING D-1 —
   to znaczy czy asercja na przynależność do `state.work_balances` i na
   niezmienione `target_hours` jest postawiona wprost, a nie wyprowadzana
   z braku wyjątku;
7. czy rozdzielenie dwóch przypadków w CONSTRAINT punkt 4 (luka w planowanym
   miesiącu vs luka we wcześniejszym) jest jednoznaczne — pierwszy jest
   zachowaniem istniejącym, którego ten task nie dotyka.

Oczekiwany wynik: `PASS / READY_FOR_IMPLEMENTATION` albo precyzyjne findings.
Nie implementuj podczas audytu.
