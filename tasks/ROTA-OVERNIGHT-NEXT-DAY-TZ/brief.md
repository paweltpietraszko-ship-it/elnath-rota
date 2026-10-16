# ROTA-OVERNIGHT-NEXT-DAY-TZ — „następnego dnia” w S1 i „Dodaj pracę”

STATUS: MAŁY FIX CC bez briefu architekta (OWNER 2026-10-16: „Jeśli gdzies w kodzie zobaczysz, że program blokuje koordynatora to zgłaszaj. Jeśli to mały fix to omiń architekta.”). Audyt Codexa wymagany. Merge tylko OWNER.
DATA: 2026-10-16. Źródło: delivery ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID (flag 2), potwierdzone przez CC; BOARD ROTA-OVERNIGHT-NEXT-DAY-TZ.

## Problem
`MonthlyPlanning.tsx`: S1 (`s1EndNextDay`) i „Dodaj pracę” (`middleEndNextDay`) liczą datę końca jako `new Date(local midnight + 86400000).toISOString().slice(0,10)`. W przeglądarce w strefie Europe/Warsaw daje to ten sam dzień, więc nocne S1/praca są odrzucane („Koniec musi być po starcie”). Ten sam błąd naprawiono w R11-01 tylko w `applyExtraCode`.

## Zmiana (jedyna)
Jeden lokalny helper `nextDayIso(dayIso)` w `MonthlyPlanning.tsx` — dokładnie arytmetyka z R11-01 (Date.UTC in, getUTC* out) — użyty w trzech miejscach: S1, „Dodaj pracę”, `applyExtraCode` (dotychczasowa kopia R11-01 zastąpiona wywołaniem). Bez zmian API, backendu, walidacji, UI poza poprawną datą.
Helper umieszczony pod `firstOfMonthIso`, poza blokiem przenoszonym w ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID (brak nakładania hunków).

## Dowód
Build frontendu; `nextday_check.mjs` stary vs nowy wynik w lokalnej strefie (Warsaw) i UTC dla dat: zwykły dzień, przełom miesiąca/roku, oba dni zmiany czasu, 28/29 lutego 2028. Audytor: realne UI — S1 i „Dodaj pracę” z „kończy się następnego dnia” w przeglądarce Europe/Warsaw zapisują koniec następnego dnia.

TASK_SCOPE:
- tasks/ROTA-OVERNIGHT-NEXT-DAY-TZ/brief.md
- tasks/ROTA-OVERNIGHT-NEXT-DAY-TZ/repo_before.hash
- tasks/ROTA-OVERNIGHT-NEXT-DAY-TZ/round_01/
- frontend/src/screens/MonthlyPlanning.tsx

KONIEC TASK_SCOPE.
