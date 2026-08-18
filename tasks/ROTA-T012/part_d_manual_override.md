# ROTA-T012-D — MANUAL REST OVERRIDE + FINAL E2E

STATUS: BLOCKED UNTIL C PASS
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`

## CEL

Domknąć świadome ręczne naruszenie nowego REST-01 bez zmiany istniejącej zasady manual correction: operacja zapisuje child ScheduleVersion mimo HARD violation, ale pozostawia pełny audit trail.

## PART D SCOPE

- rota/application/manual_edit.py
- rota/application/rule_decisions.py
- rota/application/deviation_mapping.py
- rota/persistence/decision_ledger.py
- rota/persistence/schedule_lifecycle.py
- tests/test_t012_d_manual_override.py

Żaden inny plik w D.

## ZACHOWANIE

Po manual correction:

- independent validator działa na kompletnym child candidate;
- wszystkie HARD violations nadal materializują istniejące Deviations;
- REST-01 nie blokuje zapisu;
- finalize nadal wymaga acknowledgement istniejących Deviations;
- T012 nie zmienia manual behavior dla DAY_ONLY, LEAVE, COVERAGE ani innych HARD.

Jeżeli korekta zawiera co najmniej jeden REST-01, dodatkowo zapisuje się dokładnie jeden DecisionRecord dla tej child version.

## REST OVERRIDE RECORD

Użyć istniejącego Decision Ledger, nie nowego audit store.

Wąska rodzina recordu dla konkretnej korekty:

- unikalny rule_id związany z child version, np. `REST-OVERRIDE:<child_version_id>`;
- first decision, bez sztucznego predecessor chain;
- category `CONFIRMED_EXCEPTION`;
- `rule_kind="REST_OVERRIDE_RECORD"`;
- `enforcement=INFORMATIONAL`;
- `resolution_status=RESOLVED`;
- effective_from odpowiada dacie najwcześniejszego dotkniętego okresu/demandu;
- effective_to może ograniczać record do najpóźniejszego dotkniętego dnia;
- statement ma być deterministycznym, czytelnym opisem świadomej korekty;
- structured_parameters mają zawierać child version id i wystarczające stabilne evidence do audytu: affected employee ids, assignment ids/work-period ids oraz dla każdej wykrytej pary co najmniej actual_gap_hours i required_rest_hours.

Ten informational SiteRuleVersion:

- nie wchodzi do applied_rule_version_ids child schedule;
- nie jest przekazywany jako executable SiteRule do przyszłego planowania;
- nie może zmieniać future REST;
- nie zastępuje Deviation.

## ATOMICITY

Schedule child, current-version switch, Deviations oraz DecisionRecord/SiteRuleVersion muszą być jedną transakcją.

`create_schedule_version(... on_success=...)` jest istniejącym miejscem rozszerzenia. Jeżeli obecny `record_decision()` otwiera/commituję własny `with conn`, dozwolony jest wąski refactor:

- prywatny transaction-neutral insert helper;
- istniejący public `record_decision()` nadal opakowuje helper w `with conn` dla dotychczasowych callerów;
- manual_edit/on_success używa helpera bez przedwczesnego commit.

Nie wolno tworzyć transaction managera/workflow frameworku.

Wymagany rollback proof: wymuszony wyjątek podczas DecisionRecord insert pozostawia bez nowej child version, bez current-reference switch i bez częściowego Deviation.

## TESTY D — MINIMUM

- manual rest violation saves child + REST Deviation + one DecisionRecord;
- several REST violations in same correction => one record containing all evidence;
- correction with no REST violation => no T012 DecisionRecord;
- DecisionRecord category/kind/enforcement/status exact;
- informational REST_OVERRIDE_RECORD is ignored by PlanningEngine and does not weaken next PLAN/REPLAN;
- applied_rule_version_ids child does not include audit record version id;
- finalize rejects unacknowledged REST Deviation and succeeds after normal acknowledgement path;
- forced decision-ledger failure rolls back entire correction;
- restart preserves Deviation + DecisionRecord + work-period provenance;
- normal 24, emergency 24, INNY, cross-site scenario in final end-to-end matrix;
- full suite PASS; ROTA-REG-001 PASS; Ruff/guard/diff-check PASS.

## FINAL T012 GATE

Po D Codex robi finalny audit dokładnego HEAD całego T012, nie tylko D diff:

- pełny union TASK_SCOPE;
- wszystkie A/B/C/D wymagania;
- frozen spec/lock zgodność;
- full suite i niezależne adversarial cases;
- backend.py final numbers.

Każde `WYMAGA_DECYZJI` z backend.py wraca do architekta z dokładną wartością. Dopiero po finalnym `ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T012: PASS` task jest READY FOR MERGE.
