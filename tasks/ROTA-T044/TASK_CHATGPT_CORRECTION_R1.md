# ROTA-T044 — TASK ChatGPT — wąska korekta R1 po audycie R7

Status: **READY_FOR_CODEX_NARROW_REAUDIT — CC READ-ONLY — NIE IMPLEMENTOWAĆ**

## 0. Zakres tej korekty

Ta korekta dotyczy wyłącznie Tasku:

- `tasks/ROTA-T044/TASK_CHATGPT.md` @ `bccdc5876df42e83781d735012d8d2dcb8242d83`;
- audyt: `tasks/ROTA-T044/round_01/tests/tests_r7.txt` @ `a5b89cfd4bfac610f2734634e945c31f955783d9` — **FAIL, jeden blocker**.

Wszystkie elementy `TASK_CHATGPT.md` poza trzema punktami niżej pozostają bez zmian i nie są ponownie projektowane:

1. §5.1 `Urlop`;
2. `T44-B-08`;
3. §17 — kolejność następnego gate'u.

Kalkulator 5/10/9, `required_primary_count` per wiersz/dzień, Hypothesis, L4, EXTERNAL, HEADCOUNT/CLOSED WORLD, TASK_SCOPE, WHERE_MAP i zakaz oceniania/naprawiania solvera pozostają dokładnie jak w `TASK_CHATGPT.md`.

## 1. KOREKTA §5.1 — Urlop

Zastępuje wyłącznie treść `TASK_CHATGPT.md` §5.1.

Urlop jest wpisywany przez istniejące API dostępności i jest wejściem koordynatora, nie elementem kalkulatora obsady.

### Dla `liczba_LOCAL == 1`

- jedyny LOCAL dostaje **jeden blok 10 dni roboczych**;
- nie dodawać drugiego LOCAL tylko po to, żeby utworzyć drugi blok;
- dalsze zachowanie produktu (`DECISION_REQUIRED`, ewentualna testowa reakcja EXTERNAL) ma zostać zaobserwowane, nie poprawione przez harness.

### Dla `liczba_LOCAL >= 2`

- dokładnie **dwie różne osoby LOCAL** dostają planowy urlop w tym wygenerowanym obiekcie;
- jedna osoba dostaje **10 dni roboczych**;
- druga osoba dostaje **5 dni roboczych**;
- te dwa bloki **nie nakładają się w czasie**;
- pozostali LOCAL **nie dostają kolejnych planowych bloków urlopu w tym obiekcie**;
- nie wolno rozszerzać tego cyklicznie na cały roster (`10/5/10/5/...`).

Wybór dwóch osób jest technicznym detalem harnessu i ma być deterministyczny względem wygenerowanego obiektu/przebiegu; nie zmienia to zamrożonej skali: dokładnie jeden blok 10-dniowy i jeden blok 5-dniowy dla dwóch różnych LOCAL.

Dla obu wariantów:

- nie ma rocznego budżetu urlopu do bilansowania w Symulatorze;
- urlop nie wpływa na kalkulator liczby LOCAL;
- Symulator nie tworzy własnej arytmetyki bilansu urlopu i nie ocenia wyniku solvera;
- znaleziony problem produktu zostaje reproduktorem, a nie sygnałem do zmiany wejścia.

## 2. KOREKTA `T44-B-08`

Zastępuje wyłącznie `T44-B-08` z macierzy odbioru.

`T44-B-08` — generator urlopu spełnia dokładnie:

- dla `1 LOCAL`: jeden blok **10 dni roboczych** dla jedynego LOCAL;
- dla `>=2 LOCAL`: dokładnie dwa bloki dla dwóch różnych LOCAL — **10 dni roboczych + 5 dni roboczych**, bez nakładania;
- żaden trzeci ani kolejny LOCAL nie dostaje planowego bloku urlopu w tym samym obiekcie;
- wpisy idą przez istniejące API dostępności;
- urlop nie zmienia wyniku kalkulatora obsady.

Minimalny test graniczny musi objąć co najmniej roster `1`, `5` i `10` LOCAL i potwierdzić, że generator nie próbuje zmieścić `10/5` dla każdego pracownika.

## 3. KOREKTA §17 — następny gate

`TASK_CHATGPT.md` **nie przechodzi jeszcze do CC jako „adwokata diabła”**.

Następna kolejność jest zamrożona:

1. Codex wykonuje **wąski reaudyt** tej korekty na exact HEAD brancha `task/ROTA-T044`.
2. Reaudyt sprawdza wyłącznie:
   - czy §5.1 nie wymaga już urlopu dla każdego LOCAL;
   - czy `T44-B-08` wymaga dokładnie skali `1 LOCAL -> jeden blok 10 dni`, `>=2 LOCAL -> 10+5 dla dwóch osób`;
   - czy reszta Tasku pozostała semantycznie nietknięta;
   - czy następny gate nie uruchamia CC przed PASS Codexa.
3. Raport Codexa powstaje jako kolejny, nieistniejący jeszcze `tests_rN.txt`; nie nadpisywać `tests_r1..r7.txt`.
4. **Dopiero po PASS Codexa** CC dostaje jawne polecenie „adwokata diabła”.
5. CC nadal nie implementuje, dopóki ten kolejny gate nie zostanie osobno zamknięty.

## 4. Zakazy

Ta korekta nie upoważnia do:

- zmiany `brief.md`;
- zmiany kodu produktu ani kodu Symulatora;
- zmiany kalkulatora warstwowego;
- zmiany generatora zapotrzebowania;
- zmiany L4/Hypothesis/EXTERNAL;
- dodania nowego zachowania produktu;
- otwierania ponownie punktów, które `tests_r7.txt` uznał za poprawne.

Do zakończenia reaudytu: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.
