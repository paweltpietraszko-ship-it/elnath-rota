# AUDIT-1 — Warstwa B: pionowe scenariusze CM0/CM1

Exact SHA wszystkich wyników: `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`.

Wspólny reproduktor: `audit_probe.py`. Uruchomienia:

```text
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py core
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py core_retry
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py lifecycle
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py lifecycle_retry
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py restart_retry
C:\Projects\Elnath Rota\.venv\Scripts\python.exe tasks/ROTA-AUDIT1/round_01/tests/audit_probe.py incidents
```

Pierwsze fixture failures są zachowane w logach; poniżej podano wyłącznie skuteczny REPRO każdego pionu. Źródłem oczekiwań 1–11 jest zatwierdzony `AUDIT_1_BASELINE_BRIEF_2026-08-28.md`; dodatkowe TRACE podano przy scenariuszu.

## B-01 — zwykły D/N, pięciu LOCAL

- Wejście: wrzesień 2026, OCHRONA, codziennie D 06–18 i N 18–06, 5 LOCAL, każdy target 176 h, pełna dostępność.
- Łańcuch: durable inputs → assembler → `plan_ops.plan_month()` → produkcyjny `validate()`.
- Wynik: FEASIBLE, HARD PASS, 60/60 zmian pokrytych; dokładnie po 144 h dla każdej z pięciu osób. Solver nie dopisał pracownika.
- Ocena: **PASS badanego pionu**. Ostrzeżenia o braku targetów w lipcu dotyczą quarter carry-in fixture, nie wrześniowych targetów.

## B-02 — DAY_ONLY

- Wejście jak B-01, lecz `day_only_blocks_n=true`, pierwszy pracownik ma `DAY_ONLY=true`.
- TRACE: `arch/spec.md:534-542`.
- Wynik: FEASIBLE, HARD PASS, zero nocnych przypisań DAY_ONLY; po 144 h dla wszystkich.
- Ocena: **PASS**.

## B-03 — choroba po istniejącym planie i REPLAN

- Wejście: wybrany kandydat B-01; assignment 2 września zapisany jako REALIZED/frozen; SICK_LEAVE pracownika 1 w dniach 10–14; REPLAN od 9 września.
- Wynik: FEASIBLE, HARD PASS; REALIZED/frozen zachowany; brak pracy chorego w zablokowanym przedziale.
- Ocena: **PASS**.

## B-04 — jednoczesny urlop innej osoby

- Wejście wspólne z B-03; dodatkowo LEAVE_GRANTED pracownika 2 dnia 16 września.
- Wynik: FEASIBLE, HARD PASS; brak przypisania tej osoby w dniu urlopu. Godziny kandydata: 132/144/144/144/156 — ten pion sprawdza blokady i zachowanie faktu, nie ustanawia równości przy różnych absencjach.
- Ocena: **PASS**.

## B-05 — rzeczywisty brak personelu

- Wejście: pełne D/N 720 h, tylko 2 LOCAL, target 176 h.
- TRACE: `arch/spec.md:665-712` rozdziela decyzję operacyjną od awarii technicznej.
- Wynik: DECISION_REQUIRED, brak kandydatów, nie TECHNICAL_ERROR; payload zawiera obu pracowników i NIGHT-STREAK blocker.
- Ocena: **PASS**.

## B-06 — rolling 7d ponad próg

- Wejście: B-01 z progiem `rolling_7d_decision_threshold_hours=24`.
- TRACE: `arch/spec.md:83-85,572-576`.
- Wynik: DECISION_REQUIRED; LOAD blocker dla wszystkich pięciu oraz jawna opcja akceptacji przekroczenia; nie TECHNICAL_ERROR.
- Ocena: **PASS**.

## B-07 — REST na granicy miesiąca

- Wejście: poprzedni wybrany grafik sierpnia i plan września dla tych samych 5 LOCAL.
- Łańcuch: dwa miesiące przez persistence → assembler boundary context → PLAN → validate.
- Wynik: FEASIBLE, HARD PASS; assembler widzi 62 boundary assignments; zero REST-01/WEEKLY-REST-01 violations.
- Ocena: **PASS**.

## B-08 — restart/reopen

- Wejście: zapisany i wybrany grafik 60 assignments w plikowej SQLite; połączenie zamknięte i otwarte ponownie.
- TRACE: trwałość/restart `arch/spec.md:189` oraz lifecycle contract.
- Wynik: identyczny current version id i identyczne 60 assignments po restarcie.
- Ocena: **PASS**.

## B-09 — ręczna korekta po FINAL

- Wejście: wersja z B-08 sfinalizowana jako FINAL_NO_DEVIATIONS; zmiana flagi frozen przez produkcyjne `manual_edit.apply_manual_correction()`.
- Wynik: nowy WORKING child wskazuje FINAL jako parent; current wskazuje child; snapshot rodzica przed/po jest identyczny.
- Ocena: **PASS**.

## B-10 — nieprawidłowy model/config

- Wejście: demand 08–16 niepasujący do żadnego StandardShift.
- Granica: poprawny durable/API owner odrzuca taki kształt wcześniej, dlatego minimalny nieklasyfikowalny stan podano publicznemu właścicielowi błędów planera `rota.planning.engine.plan()`; nie użyto prywatnej funkcji solvera.
- TRACE: `arch/spec.md:706-712,976`.
- Wynik: TECHNICAL_ERROR z komunikatem o niedopasowanym demandzie; nie DECISION_REQUIRED.
- Ocena: **PASS przy owning engine boundary**; nie jest to dowód bypassu przez durable API.

## B-11 — zwykły H24, pięciu LOCAL

- Wejście: wrzesień 2026, OCHRONA, jedna codzienna zmiana 06–06 H24, required rest 24 h, 5 LOCAL z capability 24h, target 176 h, bez absencji/reguł/historii.
- Wynik produkcyjny: DECISION_REQUIRED, zero kandydatów, NIGHT-STREAK blocker dla wszystkich.
- Niezależny świadek: round-robin po wygenerowanych produkcyjnych demandach, 144 h na osobę; produkcyjny `validate()` zwraca HARD PASS bez violations.
- Ocena: **FAIL badanego pionu**. Pełny DEFECT_GATE i przyczyna są w C-01.

Surowe wyniki: `probe_core*.jsonl`, `probe_lifecycle*.jsonl`, `probe_restart_retry.jsonl`, `probe_incidents*.jsonl`.
