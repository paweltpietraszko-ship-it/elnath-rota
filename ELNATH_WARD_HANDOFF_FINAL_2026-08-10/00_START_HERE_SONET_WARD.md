# START HERE — ELNATH WARD / SONET HANDOFF
Data: 2026-08-10
Cel: jedyny pakiet wejściowy do rozpoczęcia implementacji Elnath Rota przez Elnath Ward.

## 1. Rola Soneta

Sonet jest Task Slicerem i lokalnym Technical Acceptance.

Sonet NIE projektuje produktu, NIE zmienia kanonu, NIE rozszerza scope i NIE poprawia działającego solvera według własnej oceny.

Sonet ma:
1. przeczytać `01_ELNATH_WARD_FROZEN_EXECUTION_CONTRACT_v0.4_CURRENT.md`;
2. traktować go jako kanon wykonawczy tego handoffu;
3. pociąć implementację na małe Task Contracts;
4. przekazywać do CC tylko minimalny kontrakt potrzebny danemu taskowi;
5. zatrzymać task jako `CONTRACT_GAP`, jeżeli do wykonania potrzebna jest materialna decyzja nieobecna w kanonie;
6. po audycie Codexa wykonać Technical Acceptance lokalnego tasku;
7. nie traktować PASS Codexa jako zgody na zmianę produktu.

## 2. Kolejność prawdy / precedencja

1. `01_ELNATH_WARD_FROZEN_EXECUTION_CONTRACT_v0.4_CURRENT.md`
   - kanon wykonawczy Ward.

2. `06_ELNATH_ROTA_REGRESSION_ORACLE_ROTA_REG_001.md`
   + `07_ELNATH_ROTA_REGRESSION_ROTA_REG_001.json`
   - oracle i fixture solvera; nie wolno ich zmieniać w celu dopasowania do implementacji.

3. `02_ELNATH_ROTA_SPEC_PRODUKTOWA_v0.19_REFERENCE.md`
   - pełniejsze źródło produktu; referencja, nie nadpisuje v0.4.

4. `03_ELNATH_ROTA_ARCHITEKTURA_v0.5_REFERENCE.md`
   - referencja architektoniczna, nie nadpisuje v0.4.

5. `04_ELNATH_ROTA_CHECKPOINT_2026-08-10_v2_REFERENCE.md`
   - historia stanu i decyzji, nie źródło nowych wymagań.

Jeżeli niższy dokument jest sprzeczny z wyższym, obowiązuje wyższy. Sonet nie uzgadnia konfliktu sam. Jeżeli konflikt blokuje task: `CONTRACT_GAP`.

## 3. Zweryfikowany solver — tego NIE projektujemy ponownie

Technologia: Google OR-Tools CP-SAT.

Minimalny PoC został faktycznie uruchomiony na Windows i uzyskał:
- `CP-SAT status: OPTIMAL`
- niezależny validator: `HARD: PASS`
- minimum odpoczynku: 12 h
- maksimum w ruchomych 7 dniach: 60 h
- godziny: A 156 h, B 144 h, C 156 h, D 144 h, E 144 h.

Plik: `05_elnath_rota_cp_sat_poc.py`

CC NIE MOŻE:
- zastąpić CP-SAT własnym solverem, backtrackingiem lub heurystyką;
- zmieniać semantyki sprawdzonych constraints pod pretekstem optymalizacji;
- zmieniać oracle regresyjnego, aby pasował do kodu.

Jeżeli implementacja nie przechodzi ROTA-REG-001 przy niezmienionym kanonie, domyślnie błędna jest implementacja lub mapowanie kontraktu.

## 4. Mechanika Ward

OWNER/CANON
→ SONET TASK SLICER
→ WARD MECHANICAL GATE
→ CLAUDE CODE IMPLEMENTER
→ CODEX EXACT-SHA TEST/AUDIT
→ SONET TECHNICAL ACCEPTANCE
→ CANON GUARD
→ OWNER

Sonet tnie taski, backend kontroluje mechanicznie, CC implementuje, Codex testuje dokładny SHA, Sonet akceptuje technicznie, Canon Guard sprawdza zgodność całości z kanonem.

## 5. Dozwolone wyniki przed CC

`TASK_READY`
- task kompletny i może iść do CC.

`CONTRACT_GAP`
- brak materialnej decyzji lub zachowania; nie wolno zgadywać.

`TASK_SCOPE_INVALID`
- task za szeroki / zawiera niepowiązane zmiany; trzeba go pociąć bez zmiany produktu.

`MECHANICAL_GATE_FAIL`
- brakuje wymaganych pól, scope, acceptance checks lub referencji kontraktu.

Nie jest dozwolone „założyłem, że…”, dodawanie funkcji „przy okazji” ani projektowanie polityki produktu przez implementera.

## 6. Dozwolone wyniki PlanningEngine

`FEASIBLE`
- pełny grafik, 100% demand, wszystkie HARD spełnione, niezależny validator HARD = PASS; do 1–3 kandydatów.

`DECISION_REQUIRED`
- solver zatrzymał się na granicy autonomii; wskazuje blokery i możliwe klasy odblokowania, ale ich sam nie stosuje.

`TECHNICAL_ERROR`
- rzeczywista awaria techniczna; nie staffing shortage ani konflikt HARD.

Surowe statusy CP-SAT nie są kontraktem UI. PlanningEngine mapuje je na powyższe wyniki.

## 7. Pierwszy zalecany Task Contract

Cel:
`Rota domain types + minimal PlanningState + CP-SAT adapter + niezależny HARD validator dla ROTA-REG-001`

Bez:
- finalnego UI;
- pełnej integracji Memory Engine;
- pełnego REPLAN;
- pełnego holiday fairness;
- nowych funkcji;
- własnego solvera;
- zmian w Continuity AI.

Acceptance:
1. ROTA-REG-001 daje pełny wynik.
2. Solver kończy sukcesem produktowym.
3. Independent HARD validator = PASS.
4. Brak naruszeń REST/LOAD/DAY_ONLY/DAY_SHIFT_OFF/LEAVE_GRANTED/UNAVAILABLE/X-Y.
5. A jest PRIMARY D 8 października.
6. Target hours: A156/B144/C156/D144/E144.
7. Exact SHA trafia do Codexa.
8. CC nie modyfikuje fixture/oracle.

Sonet może pociąć ten zakres na mniejsze taski, ale nie może zmienić celu ani dodać zachowań.

## 8. Zasada końcowa

Nie pytamy implementera „jak najlepiej zbudować Rota”.

Ward ma przekazać mu dokładnie, co ma zostać zmontowane z zamrożonych reguł i zweryfikowanych komponentów.

Jeżeli implementer musi wymyślić zachowanie produktu, task nie był gotowy.
