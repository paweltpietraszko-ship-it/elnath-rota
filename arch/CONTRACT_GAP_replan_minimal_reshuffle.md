# CONTRACT_GAP — REPLAN: brak zasady minimalnej roszady

Status: CONTRACT_GAP — zgłoszone przez właściciela 2026-08-12, zweryfikowane
w kodzie i w `arch/spec.md` przez CC. Do rozstrzygnięcia przez architekta +
właściciela (anti-drift rule 8: "Materialna niejasność = CONTRACT_GAP, nie
inference", `arch/spec.md:614`) — CC nie implementuje niczego z tego
dokumentu bez osobnego, zaakceptowanego Task Contract.

## Zgłoszenie właściciela

Paweł (2026-08-12): "nie mamy na sztywno wprowadzonej zasady, że jak wypada
jakiś pracownik ze służby to solver robi najmniejszą możliwą roszadę
grafiku. Tak robi koordynator, nie przestawia wszystkich zmian gdy wypada
jedna czy nawet kilka."

## Fakty potwierdzone w kodzie i w spec

**1. `arch/spec.md` wspomina REPLAN dokładnie 4 razy w całym pliku, i tylko
jako zakaz, nigdy jako pozytywną definicję algorytmu:**
- `arch/spec.md:268` — `ASSIGN-03: REALIZED work MUST NOT be changed by REPLAN.`
- `arch/spec.md:269` — `ASSIGN-04: future frozen Assignment MUST NOT be changed by REPLAN.`
- `arch/spec.md:597` — REPLAN wymieniony w SECTION 4 REUSE MAP jako istniejący komponent.
- `arch/spec.md:636` — REPLAN jako krok 6 w SECTION 6 IMPLEMENTATION ORDER.

Nie ma żadnej frozen reguły mówiącej, co REPLAN POWINIEN robić poza tymi
dwoma zakazami (czego nie wolno ruszać). SOFT RANKING (`arch/spec.md:443-461`,
v0.4 §6.3) wymienia aktywne czynniki SOFT — równomierność godzin względem
target_hours, preferencje D/N, weekend fairness, holiday fairness (historyczne),
DAY_SHIFT_OFF, LEAVE_PLAN — żaden z nich nie dotyczy odległości nowego
rozwiązania od poprzedniego stanu grafiku.

**2. `rota/planning/solver.py:_add_objective` (funkcja celu CP-SAT, linie
~279-317) sumuje wyłącznie:**
- `TARGET_DEVIATION_WEIGHT = 100` × odchylenie od `target_hours` per pracownik;
- `SOFT_PENALTY_WEIGHT = 1` × kolizje `LEAVE_PLAN`/wejście N w `DAY_SHIFT_OFF`;
- weekend fairness (`fairness.py:add_weekend_fairness`);
- holiday fairness (`fairness.py:add_holiday_fairness`).

`model.minimize(sum(penalties))` (linia 317) — żaden z tych elementów nie
porównuje nowego rozwiązania do `state.existing_assignments`.

**3. `rota/planning/solver.py:fixed_existing_assignments` (linie 67-112)
definiuje, co jest "fixed": REALIZED, frozen, TRAINEE-linked, oraz PRIMARY
bez `covers_demand_id`. Każdy `PLANNED`, niezamrożony `PRIMARY` Assignment
z `covers_demand_id` (czyli zwykła, "żywa" zmiana przypisana komuś) jest
redystrybuowalny — wraca do puli razem z demandem zwolnionym przez
nieobecność.**

**Konsekwencja:** gdy jeden demand traci obsadę (np. absencja), CAŁA pula
redystrybuowalnych `PRIMARY` Assignment w danym miesiącu wraca do ponownego
rozwiązania razem z nim. Solver optymalizuje wyłącznie wg punktu 2 — nic nie
penalizuje zmiany przypisania względem poprzedniego stanu. Matematycznie
dopuszczalne jest rozwiązanie przestawiające wielu pracowników, jeśli
sumaryczna kara (target/fairness) wyjdzie równa lub niższa niż rozwiązanie
zostawiające resztę bez zmian.

## Pytania otwarte dla architekta (nie rozstrzygane w tym dokumencie)

1. Czy "minimalna roszada" to: (a) HARD constraint ograniczający liczbę
   zmienionych Assignment do minimum koniecznego dla pokrycia zwolnionego
   demandu, czy (b) SOFT człon w celu solvera karzący każdą zmianę względem
   poprzedniego przypisania — a jeśli (b), z jaką wagą względem
   `TARGET_DEVIATION_WEIGHT=100` i `SOFT_PENALTY_WEIGHT=1`?
2. Czy dotyczy tylko REPLAN wywołanego absencją, czy każdego przebiegu
   solvera na istniejącym `ScheduleVersion`?
3. Jak to się komponuje z `TARGET-01` (target_hours jest SOFT, solver nie
   tworzy pracy/nie łamie HARD dla targetu) — jeśli minimalizacja roszady
   koliduje z wyrównaniem `target_hours`, co ma priorytet?
4. Roszada liczona per Assignment (liczba zmienionych wierszy) czy per
   pracownik (liczba pracowników, których grafik się zmienił)?

## Rekomendacja proceduralna (nie decyzja)

W odróżnieniu od T004/T005 (nowa, izolowana warstwa persystencji), ten gap
dotyczy rdzenia `PlanningEngine` (`rota/planning/solver.py`, `engine.py`).
Zmiana wagi/członu w `_add_objective` może przesunąć wybierane rozwiązanie
nawet bez naruszenia żadnego HARD — a więc może wpłynąć na już zamrożony
regresyjny oracle `tests/regression/oracle_rota_reg_001.md` (ROTA-REG-001)
oraz na `benchmarks/rota_stress.py`. To jest zmiana definicji SOFT ranking
(`arch/spec.md` SECTION 3), więc prawdopodobnie wymaga też jawnej zmiany
`arch/spec.md`, nie tylko kodu — anti-drift rule 15 (`arch/spec.md:621`):
"Zmiana referencyjnego zachowania wymaga najpierw jawnej zmiany Frozen
Product Contract, a dopiero potem zmiany kodu i testów." Rekomenduję Task
Contract od architekta, tak jak dla T004/T005, zamiast traktować to jako
drobną korektę wagi.
