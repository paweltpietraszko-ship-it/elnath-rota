# AUDIT-1 — Warstwa C: C-01…C-05

Exact SHA: `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`.

## C-01 — H24 fałszywie niewykonalne

| Pole | Dowód |
|---|---|
| CLAIM | Poprawny obiekt H24 z 5 LOCAL kończy DECISION_REQUIRED mimo istnienia HARD-valid grafiku. |
| TRACE | Zatwierdzony B-11 w briefie AUDIT-1; H24 i odpoczynek opisane w frozen T012/T040. |
| ENTRYPOINT | durable inputs → assembler → `plan_ops.plan_month()` → engine/solver; niezależnie `validate()`. |
| REACHABILITY | Zwykły pierwszy PLAN, bez prywatnego bypassu i bez absencji/reguł. |
| REPRO | PLAN: DECISION_REQUIRED/NIGHT-STREAK. Round-robin: HARD PASS, 144 h każda osoba. Minimalny CP-SAT: forced H24 `x=1`, occupancy `2*x`, status INFEASIBLE. |
| USER EFFECT | Koordynator nie dostaje grafiku i fałszywie otrzymuje problem kadrowy. |
| OWNER | `rota/planning/fairness.py::add_dn_rhythm_reward`; powiązanie D/N buduje solver. |
| CLASS | **DEFECT**. |

Przyczyna została niezależnie potwierdzona: `_build_day_kind_terms()` daje dla jednego H24 ten sam wybór w D i N, więc dzienny licznik obecności wynosi `2*x`; `add_dn_rhythm_reward()` używa tego licznika jak Boolean i dodaje HARD `match + any2 <= 1` / `match + any3 <= 1` (`fairness.py:167,212-244`). Minimalny model odtwarza UNSAT. Nie znaleziono drugiego mechanizmu potrzebnego do uzyskania objawu; etykieta NIGHT-STREAK jest skutkiem fallback diagnosis, nie osobnym defektem.

## C-02 — SICK_LEAVE przed pierwszym PLAN daje HTTP 500

| Pole | Dowód |
|---|---|
| CLAIM | Znane z wyprzedzeniem chorobowe zapisuje się, lecz pierwszy PLAN kończy 500. |
| TRACE | Bezpośrednia OWNER correction zapisana w `ARCHITECT_BRIEF_SICK_LEAVE_PRE_PLAN_2026-08-28.md`: znane wielomiesięczne L4 może być wprowadzone przed planem. Dokładna metoda wyliczenia godzin nadal wymaga osobnego kontraktu. |
| ENTRYPOINT | POST availability API → pierwszy POST PLAN API → assembler/absence reference. |
| REACHABILITY | Produkcyjny FastAPI TestClient, aktywny DEV coordinator, osobna SQLite `:memory:`. |
| REPRO | availability HTTP 204; PLAN HTTP 500: `MISSING accepted reference for SICK_LEAVE (POST_PLAN_REFERENCE)`. |
| USER EFFECT | Legalna decyzja koordynatora uniemożliwia pierwszy grafik i pokazuje techniczną awarię zamiast obsłużonego stanu. |
| OWNER | `absence_reference_repository._resolve_no_accepted_plan_day()` oraz mapowanie błędu API. |
| CLASS | **DEFECT** obecnego zachowania; sposób rozliczenia/prezentacji pozostaje do zaprojektowania. |

Łańcuch: tylko LEAVE_GRANTED dostaje PRE_PLAN (`absence_reference_repository.py:310-326`), SICK otrzymuje MISSING; `_require_bound()` rzuca (`absence.py:165-168`), a fallback API mapuje wyjątek na 500 (`api/errors.py:48-52`).

## C-03 — legalny overlap daje fałszywy COVERAGE-01 excess

| Pole | Dowód |
|---|---|
| CLAIM | Każdy z dwóch niezależnych, nakładających się demandów ma własną osobę, lecz validator liczy obie osoby do obu demandów. |
| TRACE | `arch/spec.md:58,485`, `tasks/ROTA-T012/brief.md:57` jawnie dopuszczają overlap i osobny demand dla każdej pozycji. Wycofanie konkretnego SPLIT_NIGHT_12_8 w T039 nie cofa ogólnego kontraktu overlap; ten wariant wycofano także z powodu braku ciągłości jednego pracownika. |
| ENTRYPOINT | production catalog generation → production `validate()`. |
| REACHABILITY | Dwie legalne 12h pozycje N na wtorki (18–06 i 22–10), 10 demandów, 10 odrębnych LOCAL, assignment dokładnie do własnego demandu. |
| REPRO | 10/10 par poprawnych względem własnych demandów; HARD FAIL, 10 razy COVERAGE-01 `2/1` na geometrycznym overlapie. |
| USER EFFECT | Poprawnie obsadzone legalne pozycje nie mogą zostać zaakceptowane. |
| OWNER | `validator._check_coverage()` (`validator.py:100-101`). |
| CLASS | **DEFECT**. |

## C-04 — katalog zapisany, istniejący WORKING pozostaje pusty

| Pole | Dowód |
|---|---|
| CLAIM | Po pierwszym PLAN z pustym katalogiem zapisanie D/N nie odświeża istniejącej wersji ani kolejnego PLAN. |
| TRACE | Incydent z briefu stale WORKING; oczekiwane zachowanie po zmianie katalogu nie ma jeszcze OWNER ruling. |
| ENTRYPOINT | durable `update_site_profile()` → assembler → ponowny `plan_month()` → schedule readback. |
| REACHABILITY | Produkcyjne operacje na świeżej SQLite; bez ręcznej edycji demandów. |
| REPRO | zapisany profil ma 2 shifts i generuje bezpośrednio 60 demandów; assembler z istniejącym WORKING widzi 0; kolejny PLAN FEASIBLE z 0 assignments; readback nadal 0; current id bez zmian. |
| USER EFFECT | Koordynator zapisuje katalog, klika PLAN i nadal widzi pusty grafik. |
| OWNER | Granica `assembler._assemble_version_content()` / lifecycle istniejącej WORKING. |
| CLASS | **OWNER_DECISION** co do sposobu odświeżenia; sam rozjazd jest potwierdzony. |

AUDIT-1 koryguje wcześniejszą diagnozę: PLAN **nie** liczy świeżych demandów w pamięci. `assembler.py:209-211` wybiera persisted snapshot, gdy istnieje current; `plan_ops.py:148` używa dokładnie tego assemblera. To węższy i wcześniejszy punkt rozjazdu niż opisany w zgłoszeniu.

## C-05 — LOCAL bez targetu znika ze sprawiedliwości

| Pole | Dowód |
|---|---|
| CLAIM | Eligible LOCAL bez targetu pozostaje w rosterze, lecz solver nie daje mu żadnej pracy. |
| TRACE | OWNER_CONFIRMED w `docs/worker-omitted-from-fairness-objective@3328ce0`, `CODEX_HANDOFF_CONSOLIDATED_SCHEDULE_UX_REPAIR_2026-08-28.md`: nie zgadywać targetu, nie blokować PLAN, ale dzielić pracę uczciwie między wszystkich eligible LOCAL i pokazać ostrzeżenie. |
| ENTRYPOINT | durable roster/4 targety → assembler → `plan_ops.plan_month()` → solver → validate. |
| REACHABILITY | Zwykły obiekt D/N, 5 LOCAL, tylko piąty nie ma wrześniowego targetu. |
| REPRO | assembler jawnie ostrzega i pomija piątego w `work_balances`; wszystkie 3 kandydaty dają 180/180/180/180/0; HARD PASS. |
| USER EFFECT | Program pokazuje możliwy do użycia, skrajnie nierówny grafik; ostrzeżenie z assemblera nie wraca w wyniku PLAN. |
| OWNER | assembler tworzy fairness context, solver buduje target/equity, plan_ops przenosi warnings. |
| CLASS | **DEFECT**. |

Mechanizm: `assembler.py:148` usuwa osobę z WorkBalance; `_effective_targets()` iteruje tylko po `state.work_balances` (`solver.py:408-419`); pięć ścieżek PLAN/REPLAN odrzuca warnings przez `state, _ = assemble_planning_state(...)` (`plan_ops.py:135,148,308,375,426,449`).

## Werdykt Warstwy C

DEFECT_GATE spełniony dla C-01, C-02, C-03 i C-05 (TRACE + owning component + deterministyczny REPRO na exact SHA). C-04 pozostaje OWNER_DECISION, ponieważ potwierdzony rozjazd nie określa, czy WORKING ma być automatycznie regenerowany, zastępowany czy jawnie odświeżany.
