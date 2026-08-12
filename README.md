# Elnath Rota

Planning/staffing system for shift scheduling (Ward Mechanical Gate pipeline, OCHRONA pilot profile), governed by `arch/spec.md`.

## Branch policy

- `main` is protected. No direct commits or pushes to `main`.
- All work happens on `task/<id>` branches (e.g. `task/T002`), or `task/<id>-<slug>` for sub-fixes (e.g. `task/T001-crlf`).
- Merge to `main` only on the owner's explicit instruction ("merge" / "zmerguj").

## Automatyczny benchmark PlanningEngine

Benchmark generuje wiele różnych miesięcy z wcześniej skonstruowanym,
poprawnym grafikiem-świadkiem. Następnie uruchamia produkcyjne `plan()` i
sprawdza wynik pod kątem pełnego pokrycia, reguł HARD, obciążenia 7-dniowego,
odpoczynku, granicy miesiąca oraz zachowania frozen Assignment.

```powershell
python -m benchmarks.rota_stress --cases 100 --seed 20260812
```

Opcje `--json` i `--max-case-seconds 5` włączają odpowiednio wynik maszynowy
oraz lokalny limit wydajności. Seed nieudanego przypadku jest wypisywany, więc
można go odtworzyć przez `generate_case(index, seed)` bez losowania nowych danych.
