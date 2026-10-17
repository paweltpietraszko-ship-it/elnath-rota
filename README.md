# Elnath Rota

Planning/staffing system for shift scheduling (Ward Mechanical Gate pipeline, OCHRONA pilot profile), governed by `arch/spec.md`.

## Data status — read this before any other document

**All data in this project is synthetic and was created by the owner. There is no
customer, no pilot with a real company, and no real personal data.** The site names
"Bolf" and "Royal" are borrowed from real companies that have no connection to this
project and supplied nothing.

Some documents written on 2026-09-20/21 say "real object" and "production read".
They mean *a fully assembled site object* and *the owner's own running instance* —
never a customer or real data. Full statement and terminology:
**[`arch/DATA_STATUS.md`](arch/DATA_STATUS.md)**, which overrides any document that
contradicts it.

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

**OWNER 2026-08-29/30: ten benchmark (i `benchmarks/**` ogólnie) nie jest
uznawany za miarodajny dowód poprawności produktu** -- jego świadek grafiku i
generator scenariuszy nie odzwierciedlają wystarczająco realnej pracy
koordynatora. Jedynym zaakceptowanym narzędziem tego typu jest **Symulator
Koordynatora** (`tests/property/coordinator_simulator.py`, ROTA-T038/T043),
który zakłada realne obiekty przez produkcyjne API i ocenia gotowy wynik, nie
porównuje z ręcznie skonstruowanym wzorcem.
