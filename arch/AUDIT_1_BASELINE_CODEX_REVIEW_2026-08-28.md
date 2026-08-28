# CODEX REVIEW — AUDIT-1 BASELINE BRIEF

**Reviewed branch:** `docs/audit-1-baseline-brief`  
**Reviewed exact SHA:** `1b263e258fd5008051e61caef5e6558261c59479`  
**Reviewer:** Codex, independent tester/auditor  
**Status:** `WYMAGA_KOREKTY` przed uruchomieniem AUDIT-1

## Ocena

Kierunek jest właściwy: przed kolejnymi zmianami kodu należy zebrać baseline
na jednym exact SHA. Brief pozostaje dowodowy i nie upoważnia do napraw,
refaktoryzacji ani decyzji „co ciąć”. Nie jest jednak jeszcze gotowy do
wykonania z powodu jednej sprzeczności w podziale odpowiedzialności.

## Wymagana korekta granicy CC/Codex

Brief deklaruje, że CC wyłącznie mechanicznie zbiera dowody, ale punkt 4 każe
mu ocenić, czy istniejący test rzeczywiście pokrywa scenariusz oraz czy
potrzebny jest nowy test. To jest osąd kontraktowy autora, nie czynność
mechaniczna.

W punkcie 4 CC powinien wyłącznie:

- wskazać kandydatów w formacie `plik::nazwa_testu`;
- zapisać `BRAK KANDYDATA`, jeśli niczego nie znalazł;
- nie orzekać `POKRYTE`;
- nie decydować, że potrzebny jest nowy test;
- nie pisać żadnego nowego testu w AUDIT-1.

Codex po zebraniu wyników klasyfikuje każdy scenariusz jako
`POKRYTE / CZĘŚCIOWE / BRAK`, sprawdzając asercje i rzeczywisty łańcuch
produkcyjny.

## Scenariusz 11 — zaakceptowany z zawężeniem

Scenariusz H24 ma oparcie w istniejącej decyzji właściciela i w niezależnym
dowodzie: ręczna rotacja pięciu osób przeszła produkcyjny `validate()` z
`HARD_PASS=True`, podczas gdy PLAN zwrócił fałszywe `DECISION_REQUIRED`.

Należy zapisać go jako dokładny CM0, bez tautologii „wystarczająca obsada”:

> Wrzesień 2026, OCHRONA, jedna codzienna zmiana H24 06:00–06:00, pięciu
> aktywnych LOCAL, target 176 h, wszyscy dostępni, bez dodatkowych reguł i
> wcześniejszego grafiku → PLAN zwraca FEASIBLE, a kandydat przechodzi
> produkcyjny validate().

Nie wolno rozszerzać tego do twierdzenia „H24 nigdy nie zwraca
DECISION_REQUIRED”. Przy absencji, niedostępności lub aktywnej regule
pracownika taki wynik może być prawidłowy.

## Mechaniczne artefakty

Brief powinien ustalić konkretne ścieżki surowych wyników, na przykład:

- `tasks/ROTA-AUDIT1/round_01/tests/pytest.txt`;
- `tasks/ROTA-AUDIT1/round_01/tests/rota_stress.json`;
- `tasks/ROTA-AUDIT1/round_01/tests/real_object.json`;
- `tasks/ROTA-AUDIT1/round_01/tests/baseline_report.md`.

Każdy zapis powinien podać exact SHA, dokładną komendę, kod wyjścia, czas
trwania i surowy wynik. PASS/FAIL benchmarku oznacza wyłącznie wynik
istniejącego narzędzia; nie jest samodzielnym werdyktem zgodności produktu
z PRODUCT_TRUTH.

## PRE_IMPLEMENTATION_REDUCTION_GATE

Pozostaje konieczne:

- pełny pytest;
- oba istniejące benchmarki;
- mechaniczna lista kandydatów pokrycia dla 11 scenariuszy;
- jeden raport baseline odsyłający do surowych artefaktów.

Z AUDIT-1 należy usunąć:

- ocenę CC, czy test naprawdę pokrywa scenariusz;
- decyzję CC o potrzebie nowego testu;
- pisanie nowych testów;
- jakiekolwiek naprawy, rekomendacje cięcia lub rozszerzanie kontraktu.

Ta redukcja nie zmienia zachowania produktu. Po jednej mechanicznej korekcie
brief może zostać wykonany jako AUDIT-1. Architekt nie jest potrzebny do
samego zbierania wyników; powinien dostać dopiero dowody i niezależną
klasyfikację Codexa.
