# ROTA-T059 — solver objective architecture: 24h equity tolerance without CP-SAT collapse

STATUS: PREIMPLEMENTATION RESEARCH REQUIRED — IMPLEMENTATION HOLD

SOURCE_OWNER_REQUIREMENT: 24h SOFT tolerance between employees from ROTA-T058 owner ruling
SOURCE_FINDING: `arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md`

## 1. Cel

Zrealizować ownerowe wymaganie 24h tolerancji equity bez destabilizacji czasu PLAN/REPLAN/Przelicz Plan i bez dalszego dokładania kruchych, kaskadowych współczynników do `_add_combined_objective`.

T059 jest osobnym zadaniem solver-engineering. Nie wolno implementować rozwiązania, dopóki niezależny audyt nie wybierze bezpiecznej architektury i nie zamrozi kontraktu wykonania.

## 2. Zamrożona prawda produktowa

- TARGET-01 pozostaje wyższym priorytetem niż zwykłe SOFT.
- Ogólny rytm D/N/W/W pozostaje SOFT.
- Equity/equal-split ma tolerować różnice godzin do 24h: dalsze wyrównanie wewnątrz tego pasma nie powinno psuć rytmu tylko dla kosmetycznego zbliżenia godzin.
- Różnica >24h pozostaje legalna; equity może ją preferencyjnie zmniejszać jako SOFT.
- Brak targetów nadal korzysta z fallbacku equal-split; nowa architektura musi obejmować także ten tor.
- Nie pogarszać semantyki HARD ani jakości wyników przez arbitralne "first feasible" jako ukrytą zmianę produktu.

## 3. Zweryfikowany problem techniczny

Na realnym obiekcie seed=42:
- zwykły equal-split: ~0.4–1s OPTIMAL;
- deadband 24h w objective: 45s i brak dowodu optymalności;
- target-equity deadband: ~32x wolniej;
- samo podniesienie `DN_RHYTHM_REWARD_WEIGHT` z 1 do 10, bez nowych zmiennych, także powoduje 45s bez dowodu;
- wzrost jednej wagi kaskaduje przez `equal_split_weight` oraz `prefer_local_weight`.

Wniosek wejściowy: nie traktować tego jako lokalnego problemu jednego ReLU/deadbandu. Trzeba sprawdzić bezpieczeństwo całego mechanizmu "strict dominance by cascading coefficients".

## 4. Obowiązkowy audyt architektoniczny przed implementacją

Codex ma porównać co najmniej trzy klasy rozwiązań na tych samych realnych fixture i tych samych limitach czasu:

A. Obecny pojedynczy weighted objective z próbą ograniczenia skali współczynników bez utraty priorytetów.

B. Sekwencyjna/lexicographic optymalizacja: najpierw wyższy priorytet, następnie zamrożenie osiągniętej wartości lub jawnej tolerancji i osobny solve niższego priorytetu. Audyt ma odtworzyć, dlaczego wcześniejsza wersja projektu odrzuciła phase split, i sprawdzić czy tamto uzasadnienie nadal jest aktualne po zmianach T041/T057.

C. Hierarchia jakości bez wielkich współczynników, np. bounded score/tie-break w osobnych fazach lub inny model pozwalający zachować relację TARGET-01 > equity/rhythm bez eksplozji współczynników.

Dopuszczalne są inne kierunki, ale muszą być porównane z A/B/C, nie tylko zaproponowane opisowo.

## 5. Evidence gate

Każdy kandydat musi zostać zmierzony co najmniej na:
- real-object seed=42, complete targets;
- real-object seed=42, missing-target equal-split;
- co najmniej jednym ciasnym staffing case;
- PLAN i jednym realnym Przelicz Plan;
- scenariuszu, w którym 24h deadband rzeczywiście zmienia ranking, aby nie zaakceptować rozwiązania "szybkiego", które nic nie robi.

Dla każdego wariantu zapisać:
- wall time;
- FEASIBLE/OPTIMAL/optimization_complete;
- objective/bound gap;
- TARGET-01 quality;
- equity spread;
- rhythm score;
- czy wynik respektuje deadband 24h;
- czy zmiana wpływa na HARD.

## 6. Kryterium wyboru architektury

Nie wybierać rozwiązania tylko dlatego, że jeden fixture jest szybszy.

PASS_PREIMPLEMENTATION wymaga:
1. zachowania prawdy produktowej z sekcji 2;
2. braku mnożnikowej kaskady współczynników, której niewielka zmiana jednej preferencji może wysadzić czas dowodzenia;
3. przewidywalnego zachowania w obu torach target/equal-split;
4. jawnego wyjaśnienia relacji z `relative_gap_limit=1%` i budżetem 45s;
5. literalnego TASK_SCOPE dopiero po wyborze rozwiązania.

## 7. Zakaz implementacji na tym etapie

Do PASS_PREIMPLEMENTATION:
- nie zmieniać produkcyjnego `_add_combined_objective`;
- nie podnosić wag eksperymentalnie w branchu produktu;
- nie dodawać kolejnego ReLU/deadband encoding do produkcji;
- nie zwiększać globalnego czasu PLAN jako obejścia;
- nie zmieniać TARGET-01 ani HARD;
- nie mieszać T059 z T058.

READ_ONLY_EVIDENCE:
- arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md
- rota/planning/solver.py
- rota/planning/fairness.py
- tests/support/t009_fixtures.py
- BOARD.md

TASK_SCOPE: NOT FROZEN — IMPLEMENTATION HOLD.
