# AUDIT-1 — Warstwa A: baseline

- Exact SHA: `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b` (`main` przed T040), zweryfikowany przed wykonaniem.
- Środowisko: izolowany worktree, Python z `C:\Projects\Elnath Rota\.venv\Scripts\python.exe`, świeże bazy SQLite tworzone przez produkcyjne operacje.

## Pełna regresja

Polecenie (Symulator świadomie pominięty):

```text
C:\Projects\Elnath Rota\.venv\Scripts\python.exe -m pytest -q --ignore=tests/property/test_coordinator_simulator.py
```

Wynik procesu: exit `1`; `3 failed, 1228 passed, 1 warning in 4604.88s (1:16:44)`. Surowy zapis: `pytest.txt` (stderr pusty).

Klasyfikacja trzech failures względem PRODUCT_TRUTH:

1. `tests/test_sick_leave.py::test_leave_granted_does_not_reduce_solver_target_unlike_sick_leave` — **STALE TEST**, nie regresja. Test zamraża pre-T023 regułę SICK-only. `tasks/ROTA-T023/brief.md:273` później jawnie ustanowił, że SICK i granted leave zmniejszają live TARGET przez ten sam canonical `WorkBalance.absence_hours`; kod robi to w `rota/planning/solver.py:408-419`.
2. `tests/test_t017.py::test_m13_first_candidate_matches_pre_t017_deterministic_result` — **STALE EXACT-PLACEMENT ORACLE**, nie regresja. Zatwierdzony SOFT T034 zmienił ranking pierwszego kandydata; wcześniejszy niezależny audyt sklasyfikował ten konkretny oracle jako stale (`tasks/ROTA-T034/round_01/tests/tests_r2.txt:89-92`). Wynik nadal jest FEASIBLE; zmieniają się dwa przypisania w symetrycznym przykładzie.
3. `tests/test_t023_checkpoint_b.py::test_t23_54_t012_legality_rest_modules_unmodified_by_checkpoint_b` — **STALE SOURCE-SHAPE TEST**, nie regresja. Test porównuje całe obecne repo z historycznym `BASE_SHA=e05dfb7...` (`tests/test_t023_checkpoint_b.py:60,355-360`) i dlatego prawidłowo widzi późniejsze, autoryzowane zmiany `constraints.py` i `work_periods.py`. Nie testuje zachowania produktu na obecnym SHA.

Pełnej suity nie powtarzano.

## Symulator Koordynatora

Wykonane dokładnie raz poleceniem z briefu, z `REPORT_PATH` skierowanym do `coordinator_simulator.md`. Interfejs narzędziowy przerwał oczekiwanie i nie zachował numerycznego exit statusu; proces dokończył pracę, nie pozostał aktywny, a kompletny raport zawiera wszystkie seedy 0–4. Zgodnie z zasadą „dokładnie raz” nie uruchamiano go ponownie.

Ocena faktów raportu:

- każdy seed zaczyna od 5 osób wynikających z 720 h zapotrzebowania;
- D/N (seedy 0, 1, 4) kończy FEASIBLE i używa wszystkich 5 osób;
- dodatkowe osoby nie są tworzone przed wynikiem solvera;
- seedy 2 i 3 dopisują po cztery LOCAL dopiero po rzeczywistym `DECISION_REQUIRED`, lecz nawet przy 9 osobach pozostają `DECISION_REQUIRED` z NIGHT-STREAK;
- raport nie zawiera rozkładu godzin, więc nie jest dowodem sprawiedliwości; ten punkt sprawdzono niezależnie w Warstwie B/C.

## Jawnie niewykonane

`benchmarks.rota_stress` i `benchmarks.real_object` **NIE ZOSTAŁY URUCHOMIONE**. OWNER_CORRECTED uznał ich dobieranie nadmiarowej obsady za niemiarodajne. Nie zastąpiono ich innym generatorem.

## Dodatkowe próby audytowe

`audit_probe.py` jest artefaktem dowodowym, nie testem produktu. Pierwsze błędy konfiguracji samego probnika zachowano w surowych `probe_*.jsonl`; autorytatywne wyniki po mechanicznej korekcie fixture są wskazane w dokumentach Warstwy B/C. Żaden taki błąd nie został sklasyfikowany jako defekt produktu.
