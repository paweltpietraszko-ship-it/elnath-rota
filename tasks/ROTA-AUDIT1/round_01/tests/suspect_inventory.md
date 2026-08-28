# AUDIT-1 — Warstwa D: remanent pozycji SUSPECT

Audytowany kod: `d445ee64a0e634c4ca23c2fcc9f6a50b6503d22b`
Zamrożone źródło listy: PR #9 `f2eba6ce97d19d03fbef3c7bd4fe3c417ff55a05`,
`START_HERE_CODE_INVENTORY_AUDIT_2026-08-28.md`.

Klasy poniżej stosują progi z briefu AUDIT-1. Rozmiar pliku, podobieństwo nazw
ani liczba testów nie są dowodem. `KEEP` dotyczy istniejącego kontraktu i
osiągalnej ścieżki, nie oznacza, że moduł ma idealny kształt. Tam, gdzie nie
da się wskazać kanonicznego ownera albo odtworzyć skutku, wynik brzmi
`EVIDENCE_GAP`.

## Wynik skrócony

| Pozycja SUSPECT | Klasa | Produkcyjna osiągalność / jedyny owner | Ustalenie |
|---|---|---|---|
| `rota/planning/replan_reshuffle.py` | `KEEP`; lokalnie `EVIDENCE_GAP` | `solver.solve()` używa wszystkich trzech publicznych funkcji (`solver.py:38,867,922,928`); REPLAN dochodzi tu z `plan_ops.replan*` przez `engine.plan_requiring_different_result_*` | REPLAN-MIN i wymaganie wyniku różnego od bazowego są zamrożone. Moduł nie jest martwą „optymalizacją”. Predicate redistributable jest jednak świadomie skopiowany z `solver.fixed_existing_assignments()` (`replan_reshuffle.py:11-35`, `solver.py:83-108`). Dwie żywe ścieżki podejmują komplementarną decyzję o tych samych Assignmentach, lecz PRODUCT_TRUTH nie wskazuje kanonicznego ownera. Nie spełnia to progu `DUPLICATE`; pozostaje `EVIDENCE_GAP` granicy ownershipu. |
| Wielostopniowy fallback `engine.py` | `KEEP` | publiczny `engine.plan()` i oba tryby REPLAN wywołują stage table (`engine.py:114-135,452-491`) | Literalny frozen addendum wymaga kolejności: normal capped → DAY_ONLY capped → DAY_ONLY+emergency24 capped → uncapped LOAD (`FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01.md:77-106`; komunikacja: `FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md:21`). Brak drugiej osiągalnej implementacji tej samej orkiestracji. Uproszczenie sterowania mogłoby być propozycją architektoniczną, ale nie dowodem nadmiaru. |
| Wiele alternatyw / diversity search | `KEEP` | `solver._search_additional_candidates()` jest wywoływany z `solve()` (`solver.py:742-821,931-935`), a wynik trafia przez engine i `plan_ops.select_candidate()` do API | `FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md` wymaga do trzech kandydatów i ich semantyki, a T017 utrwala wybór koordynatora. To CM3, lecz nadal zaakceptowane zachowanie produktu. Ewentualne wycofanie wymaga decyzji OWNER, nie klasy `DEAD`. |
| `rota/application/durable_inputs.py` | `KEEP`; trzy eksporty `TEST_ONLY` | routery na żywo używają m.in. `update_site`, `update_site_profile`, `update_employee`, `update_membership`, `append_availability`, `set_target_hours`, `set_calendar_day`, `add_external_support_window`, `save_print_settings` (`api/routers/*.py`) | Moduł skupia wiele komend, ale są one rozłączne i osiągalne; brak dowodu równoległych write-pathów tej samej decyzji. `update_coordinator()`, `update_association()` i `correct_site_planning_regime()` nie mają żadnego callera poza testami na tym SHA (`durable_inputs.py:508,524,540`). Pierwsze dwie operacje są jawnie wyłączone z ekranów w `arch/T021_spec.md:53-56`, więc są `TEST_ONLY`, nie `DEAD`. Dla korekty reżimu występuje osobny kontrakt T023b, ale brak produkcyjnego entrypointu; bez pionowego repro i rozstrzygnięcia kompletności UI nie podnoszę tego tu do `DEFECT` — patrz „luki do dalszego dowodu”. |
| `rota/application/rule_decisions.py` | `KEEP` | pięć komend jest bezpośrednio wystawionych przez `api/routers/rule_decisions.py:17-133`; zapis prowadzi atomowo przez `decision_ledger.record_decision_no_commit()` | Jeden application owner dla zaakceptowanych decyzji checkboxowych i jeden persistence owner zapisu. Nie znaleziono równoległej implementacji decyzji. |
| `rota/application/deviation_mapping.py` | `KEEP` | `lifecycle_ops.py:15` i `manual_edit.py:19` materializują Deviation z raportu validatora | Dwie ścieżki konsumenckie mają różne zdarzenia (revalidation/finalization oraz ręczna korekta), lecz używają tego samego mappera. To współdzielenie ownera, nie duplikat. Deviation/auditability jest utrwalone w T009/T012/T036. |
| `rota/application/training.py` | `TEST_ONLY` dla publicznego entrypointu | `mark_training_realized()` (`training.py:122`) nie ma produkcyjnego callera; występuje w testach T009/T016/T019b | Moduł nie jest `DEAD`, bo kontrakty T009/T019b utrzymują lifecycle szkolenia. Jednocześnie `arch/T021_post_round1_architect_brief_2026-08-22.md:41` mówi, że operacja ma być skutkiem oznaczenia TRAINEE jako REALIZED w ręcznej korekcie, podczas gdy żywy router ręcznej korekty jej nie wywołuje. Statycznie potwierdzona klasa osiągalności to `TEST_ONLY`; klasy `DEFECT` nie nadaję bez odtworzenia user-visible flow na exact SHA. |
| `rota/application/analytics_read.py` + Analityka | `KEEP` | `api/routers/analytics.py:14` → `analytics_for_site_month`; frontend `Analytics.tsx` → `client.getAnalytics()` | Ekran i read model są osiągalne oraz jawnie zaakceptowane w T021. Read model czyta persistence i nie uczestniczy w solverze. To, czy warto zachować produkt CM3, jest późniejszą decyzją OWNER; obecnie nie ma podstaw do `DEAD`/`DUPLICATE`. |
| `rota/persistence/decision_ledger.py` | `KEEP`; wrapper `record_decision()` = `TEST_ONLY` | produkcja używa transaction-neutral `record_decision_no_commit()` z `manual_edit.py:200` i `rule_decisions.py:73` | Jeden write owner reguł/decyzji. Publiczny wrapper `record_decision()` (`decision_ledger.py:153`) ma callerów tylko w testach; żywe use-case'y muszą składać go w szerszej transakcji. Wrapper jest `TEST_ONLY`, nie dowodzi zbędności ledgeru. |
| `rota/persistence/site_memory.py` | `KEEP`; `decision_fate()` = `TEST_ONLY` | `effective_rule_on()` zasila `site_rule_assembly.py:31,69`; akcje i decision-required są czytane/zapisywane przez application/API | Różne dane w jednym module są żywe i mają konsumentów. `decision_fate()` (`site_memory.py:96`) ma callerów tylko w `tests/test_site_memory_decision_ledger.py`; to `TEST_ONLY`. Nie wykazano, że persisted state jest wyliczalnym duplikatem innego źródła. |
| `rota/persistence/absence_reference_repository.py` | `KEEP`; C-02 bada defekt integracji | write path: `durable_inputs.py:204` → `capture_and_check_in_open_transaction()`; read paths: `schedule_export.py:369` i `work_balance_repository.py:38,64` → `get_absence_reference_snapshot()` | Moduł ma żywy zapis i dwóch różnych konsumentów odczytu; utrwala provenance nieobecności po zmianie grafiku, więc usunięcie narusza recovery/auditability. C-02 może wykazać wadliwą brakującą gałąź SICK_LEAVE, ale nie czyni całego repozytorium martwym lub duplikatem. |
| `rota/persistence/work_balance_repository.py` | `KEEP`; wrapper `save_work_balance_target()` = `TEST_ONLY` | assembler, bootstrap, analytics, roster i durable inputs używają targetów/bilansów (`assembler.py:44,147`, `analytics_read.py:19`, `api/routers/roster.py:183`, `durable_inputs.py:302-307`) | WorkBalance jest żywym wejściem objective i read modelu. Produkcyjny zapis idzie atomowo przez `write_work_balance_target_in_open_transaction()`; wygodny wrapper `save_work_balance_target()` (`work_balance_repository.py:93`) ma callerów tylko w testach. C-05 bada błąd zachowania przy braku wiersza, nie martwość całej warstwy. |
| `site_rule_repository.py` + `site_rule_assembly.py` | `KEEP` | repository zapisuje/odczytuje wersje; assembly używa `list_rule_ids_for_site()` i `site_memory.effective_rule_on()`; konsumenci: assembler, availability matrix, memory read | Persistence i składanie obowiązujących reguł nie są dwiema implementacjami tej samej decyzji. Jedynym ownerem wyboru effective version jest `site_memory.effective_rule_on()`, a assembly go reużywa. Każda ścieżka jest produkcyjnie osiągalna. |
| Historia / Decyzje / Analityka UI | `KEEP` | routery są zarejestrowane w `api/main.py`; `Room.tsx` ma aktywne nav entry, a `client.ts` wywołuje endpointy historii, decyzji i analityki | Wszystkie trzy ekrany są zaakceptowanym zakresem T021 i mają realne call pathy. Kod read-only nie dubluje decyzji solvera. Pytanie „czy produkt potrzebuje tych ekranów” pozostaje decyzją OWNER po audycie, nie techniczną klasą martwości. |

## Potwierdzone symbole bez produkcyjnego callera

Poniższa lista jest węższa od klasyfikacji całych modułów. Wynika z
`git grep` na exact SHA z wyłączeniem `tests/`, `tasks/` i `arch/`:

- `durable_inputs.update_coordinator()` — `TEST_ONLY`; T021 jawnie nie daje mu ekranu;
- `durable_inputs.update_association()` — `TEST_ONLY`; T021 jawnie nie daje mu ekranu;
- `durable_inputs.correct_site_planning_regime()` — `TEST_ONLY` reachability, mimo kontraktu T023b;
- `training.mark_training_realized()` — `TEST_ONLY` reachability, mimo opisu integracji T021;
- `decision_ledger.record_decision()` — `TEST_ONLY` wrapper; produkcja używa wariantu no-commit;
- `site_memory.decision_fate()` — `TEST_ONLY` query;
- `work_balance_repository.save_work_balance_target()` — `TEST_ONLY` wrapper; produkcja używa atomowego prymitywu no-commit.

Nie klasyfikuję tych symboli jako `DEAD`, gdy istnieje trwały kontrakt albo
stanowią bezpieczny wrapper wokół żywego prymitywu. `TEST_ONLY` mówi wyłącznie,
że użytkownik nie może dziś dotrzeć do tej funkcji przez zarejestrowany runtime.

## Luki dowodowe, których nie wolno zamienić w opinię

1. `fixed_existing_assignments()` i
   `redistributable_baseline_assignments()` mają skopiowany predicate i komentarz
   „kept in sync by tests”. Rozjazd jest możliwy, ale na tym SHA nie wykazano
   rozjazdu wyniku, a kontrakt nie wskazuje jednego kanonicznego ownera.
   Klasa: `EVIDENCE_GAP`, nie `DUPLICATE`.
2. `correct_site_planning_regime()` i `mark_training_realized()` mają kontrakt,
   lecz brak runtime callerów. Aby nazwać to `DEFECT`, Warstwa C musiałaby
   odtworzyć konkretny zaakceptowany flow użytkownika i wykazać brak/niepoprawny
   rezultat. Sama nieobecność importu wystarcza tylko do `TEST_ONLY`.
3. Nie wykazano, że fallbacki engine, multi-candidate ani trzy read-only ekrany
   podejmują tę samą decyzję produktową w dwóch miejscach. Ich złożoność może
   być kosztem utrzymania, ale nie spełnia progu `DUPLICATE` lub `DEAD`.

## Komendy dowodowe

```text
git show f2eba6ce97d19d03fbef3c7bd4fe3c417ff55a05:START_HERE_CODE_INVENTORY_AUDIT_2026-08-28.md
git grep -n <symbol> HEAD -- rota api frontend ':!tests/**' ':!tasks/**' ':!arch/**'
git grep -n <symbol> HEAD -- tests tasks arch
git grep -n -E "include_router|analytics|history|decision" HEAD -- api frontend/src
```

Warstwa D nie autoryzuje usuwania ani refaktoryzacji. Plan redukcji (Warstwa E)
jest osobną decyzją właściciela po zamknięciu całego AUDIT-1.
