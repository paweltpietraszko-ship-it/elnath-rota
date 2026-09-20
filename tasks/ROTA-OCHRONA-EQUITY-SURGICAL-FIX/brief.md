# ROTA-OCHRONA-EQUITY-SURGICAL-FIX — przywrócenie sprawiedliwego podziału w OCHRONA

STATUS: PREIMPLEMENTATION — HOLD DO PRECHECKU ANTIGRAVITY/CODEX I DECYZJI OWNERA

SOURCE_REQUEST: BOARD.md / ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE, instrukcja
Architekta na `bdb563d`/decisive finding `c411bcf`, po diagnozie
`task/ROTA-TARGET-EQUITY-DIAGNOSIS`.

## 1. Zdiagnozowany problem (dowiedziony, nie hipoteza)

Ten sam kod solvera (snapshot sprzed 15.09, commit `900ef16`), te same
dane Royal, jedyna zmienna to kompletność wektora `target_hours`:

- Wektor NIEKOMPLETNY (co najmniej jeden aktywny LOCAL bez targetu) →
  awaryjny `add_equal_split_fairness`: rozstrzał **12h**
  (120/120/120/120/132/132).
- Wektor KOMPLETNY (dzisiejszy stan Royal po użyciu "Ustaw wszystkim") →
  TARGET-01: rozstrzał **120h** (48/60/144/156/168/168).

Gate `require_complete_target_hours` (`rota/application/plan_ops.py`,
15.09, task ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE) został zaprojektowany
i uzasadniony wyłącznie żywym repro na obiekcie FF (ORDINARY) — usunął
jednocześnie stary fallback (`add_equal_split_fairness`, `rota/planning/
fairness.py`) i wymusił kompletność wektora dla KAŻDEGO Site, obu reżimów.
Efekt uboczny dla OCHRONA: koordynator stracił możliwość pozostania w
niekompletnym, sprawiedliwym stanie — "Ustaw wszystkim" (funkcja
wprowadzona tym samym Taskiem) aktywnie pogarsza sprawiedliwość zamiast ją
poprawiać.

Legacy fallback NIE może wrócić bez zmian: ignorował absencje (prawdziwy,
osobny błąd z FF/ORDINARY, poprawnie naprawiony przez `_effective_targets`
już od 22.08, przed tym Taskiem — patrz `decisive_finding.md`).

## 2. Kryteria akceptacji (Architekt, dosłownie z BOARD.md)

1. Royal z kompletnymi targetami zachowuje prawie równy przydział jak
   historyczny fallback, bez regresji rytmu D/N lub budżetu czasu solvera.
2. Drugi realny obiekt OCHRONA bez targetów (`SITE-b8738d357a0f46fb97e0bd2d49565b52`)
   ponownie może PLAN/REPLAN.
3. OCHRONA z urlopem/delegacją nie dostaje pełnej pracy ponad godziny
   nieobecności — zgodnie z efektywnym limitem (`_effective_targets`).
4. ORDINARY bez zmian: bez targetów nadal blokuje (gate), z kompletnymi
   działa jak dziś (obecny algorytm, obecne wyniki, bez regresji).
5. Testy PLAN, REPLAN i precheck; HARD pass; czas solvera w dotychczasowym
   budżecie.

## 3. Zakres zmiany (do potwierdzenia/doprecyzowania przez Architekta+Codex)

CC nie projektuje ostatecznego kodowania CP-SAT — poniżej dwa kierunki
zidentyfikowane w diagnozie, oba zgodne z kryteriami powyżej, do wyboru
lub połączenia przez Architekta:

**Kierunek A — reżimowo odtworzony, absencjo-świadomy fallback.**
Przywrócić `add_equal_split_fairness`-podobny mechanizm, ale:
(a) tylko dla `SitePlanningRegime.OCHRONA` (ORDINARY bez zmian — gate
kompletności zostaje jak dziś, bo tam naprawił realny błąd);
(b) świadomy absencji/delegacji od startu — liczony na `_effective_targets`
(już istniejący, absencjo-świadomy), nie na surowych godzinach roboczych;
(c) aktywny NIEZALEŻNIE od kompletności wektora dla OCHRONA — czyli nie
tylko jako fallback dla niekompletnego wektora (kryterium 1 wymaga
sprawiedliwości TAKŻE przy kompletnym wektorze, po "Ustaw wszystkim"),
raczej jako podstawowa ścieżka sprawiedliwości dla OCHRONA w miejsce
TARGET-01's `neg`-owej presji.
(d) gate `require_complete_target_hours` dla OCHRONA złagodzony/wyłączony
(kryterium 2), dla ORDINARY bez zmian.

**Kierunek B — wariant TARGET-01 bez presji "dobijania" (pos-only lub
tłumione `neg`), aktywny tylko dla OCHRONA.** Faza 3 diagnozy
(`pos_only_report.md`) pokazała, że usunięcie `neg` z TARGET-01 dla Royal
daje rozstrzał 12h — niemal identycznie jak historyczny fallback — ale
kosztem rytmu D/N (23→11 dopasowań) i budżetu czasu solvera (90s zamiast
1.8s, FEASIBLE zamiast OPTIMAL). Ten kierunek NIE spełnia kryterium 1
("bez regresji rytmu D/N lub budżetu czasu") w obecnej, najprostszej
formie (pełne zerowanie `neg`) — wymagałby złagodzonego wariantu (np.
tłumienie zamiast zerowania, próg tylko dla dużych niedoborów) i osobnego
pomiaru rytmu/czasu przed uznaniem za spełniający kryteria. Nie rozwiązuje
też kryterium 2 (gate) samodzielnie — potrzebowałby dodatkowo złagodzenia
gate dla OCHRONA, jak w kierunku A(d).

**CC nie ma preferencji między A i B — obie wymagają decyzji projektowej
Architekta**, którego CP-SAT owner to `rota/planning/solver.py`/`rota/
planning/fairness.py`. Modyfikowane pliki w obu kierunkach: `rota/planning/
fairness.py`, `rota/planning/solver.py`, `rota/application/plan_ops.py`
(gate), ewentualnie `api/routers/durable_inputs.py`/frontend (jeśli UI
"Ustaw wszystkim" ma się zmienić dla OCHRONA — do potwierdzenia, poza
zakresem tego briefu, jeśli architekt uzna że niepotrzebne).

## 4. Poza zakresem

- Żadna zmiana dla ORDINARY (gate, `_effective_targets`, TARGET-01,
  algorytm) — kryterium 4 wprost tego zabrania.
- Przywrócenie starego `add_equal_split_fairness` bez zmian (absence-blind)
  — wprost zabronione przez Architekta.
- Zmiana innych wag (weekend/holiday/rytm), HARD reguł, limitu czasu/gap
  poza tym, co wynika bezpośrednio z wybranego kierunku.

## 5. Dowody / materiały diagnozy (branch `task/ROTA-TARGET-EQUITY-DIAGNOSIS`)

- `decisive_finding.md` + `incomplete_vector_experiment.py` — rozstrzygający dowód (sekcja 1).
- `pos_only_report.md` + `pos_only_experiment.py` — dane kierunku B.
- `regime_scope_finding.md` — chronologia gate'u i geneza na Ordinary/FF.

## Verification (do wykonania po wyborze kierunku, przed implementacją)

- Precheck Antigravity/Codex na tym briefie (poprawność zakresu, ryzyko,
  kompletność kryteriów) — PRZED jakąkolwiek implementacją.
- Po precheku: pełny Task (branch `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX`),
  implementacja dopiero po PASS prechecku i decyzji OWNERA co do kierunku.
