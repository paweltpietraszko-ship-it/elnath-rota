# ROTA-T021b — EMPLOYEE MATRIX RULE WRAPPERS

STATUS: READY FOR CODEX PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY UNTIL PASS
ARCHITECT_INPUT_SHA: `86979980c5c94371317c68647e51aaf68e41a853`
ARCHITECT_INPUT: `arch/T021_screen2_rule_wrapper_architect_brief_2026-08-23.md`
R1_AUDIT: `tasks/ROTA-T021b/round_01/tests/tests_r1.txt`
DATE: 2026-08-23

## 1. PURPOSE

Screen 2 (`Panel sterowania -> Obsada`) must not construct `SiteRuleVersion`, `rule_id`, `structured_parameters`, `rel` or decision-ledger text itself.

T021b adds the missing thin application commands for the already-frozen employee matrix semantics. It does **not** add a rule engine, a new persistence model or frontend/API code.

Existing owners remain unchanged:

- generic atomic decision/action write: `rota.application.rule_decisions.record_structured_rule_decision`;
- rule-family history/effective selection: T005 Decision Ledger / SiteMemory;
- executable rule semantics: `rota.planning.site_rules`;
- Screen-2 read projection: `rota.application.availability_matrix.employee_availability_matrix`.

## 2. CANONICAL MATRIX WRITE MODEL

The architect-input brief lists several executable rule kinds that exist in the code. That list is not the matrix write design.

Frozen T010-B already selected one representation for dated D/N/weekday unavailability:

`EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`

with these mappings:

- Dniówka `☐` -> `weekdays=[1..7]`, `forbidden_shift_kinds=["D"]`;
- Nocka `☐` -> `weekdays=[1..7]`, `forbidden_shift_kinds=["N"]`;
- one weekday `☐` -> `weekdays=[ISO weekday]`, `forbidden_shift_kinds=["D","N"]`.

The matrix-owned restriction is `LOCAL_RULE / HARD / RESOLVED`, with `employee_id` in `structured_parameters`.

Do **not** add Screen-2 wrappers based on `EMPLOYEE_ALLOWED_SHIFT_KINDS` or `EMPLOYEE_ALLOWED_WEEKDAYS`. Doing so would create a second write representation for the same matrix whose existing read owner currently projects `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`.

`Employee.day_only` remains the base source of Nocka `☐`. A temporary Nocka `✓` for `day_only=true` uses only the already-frozen `EMPLOYEE_DAY_ONLY_N_EXCEPTION` as `CONFIRMED_EXCEPTION / HARD / RESOLVED` with `{"employee_id": ...}`. No generic HARD override is introduced.

Ogólna dostępność remains on the existing AvailabilityRecord path (`append_availability`). `24h` remains `SiteMembership.can_work_24h` (`update_membership`). T021b does not wrap either one.

### 2.1 Employee identity boundary

Every T021b command that creates or changes a matrix rule must resolve the affected `employee_id` through the existing `get_employee()` read **before any write**.

- create commands validate their explicit `employee_id`;
- update/end commands validate the `employee_id` retained in the current matrix-owned rule's `structured_parameters`;
- unknown Employee -> fail with no DecisionRecord, SiteRuleVersion or coordinator-action write.

T021b deliberately adds **no** further membership gate:

- it does not require a `SiteMembership` row;
- it does not require `SiteMembership.enabled == True`;
- it does not reinterpret Employee `active_from/active_to` as a matrix-write permission rule.

Reason: R1-1 is a referential/read-contract gap. `employee_availability_matrix()` itself requires an existing Employee, while membership/enabled state is already a separate roster/eligibility concern. T021b must not invent a new hidden eligibility condition merely to make a structured write safer.

## 3. APPLICATION API

Keep `record_structured_rule_decision()` as the generic low-level application seam. Add the following semantic commands in the same module, with small private helpers for repeated construction/validation.

### 3.1 New D/N restriction

```python
def create_employee_shift_unavailability(
    conn, *,
    coordinator_id: str,
    site_id: str,
    employee_id: str,
    shift_kind: ShiftKind,
    effective_from: date,
    effective_to: date,
    note: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> DecisionRecord
```

- employee must exist per §2.1;
- `shift_kind` is D or N from the existing enum;
- creates a new rule family with a backend-generated opaque `rule_id`;
- writes the canonical `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` shape above;
- first decision has `rel=None`.

### 3.2 New weekday restriction

```python
def create_employee_weekday_unavailability(
    conn, *,
    coordinator_id: str,
    site_id: str,
    employee_id: str,
    iso_weekday: int,
    effective_from: date,
    effective_to: date,
    note: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> DecisionRecord
```

- employee must exist per §2.1;
- `iso_weekday` must be integer 1..7, bool excluded;
- creates a new backend-generated rule family;
- forbidden kinds are exactly D and N;
- first decision has `rel=None`.

### 3.3 Temporary N for `day_only=true`

```python
def create_day_only_n_exception(
    conn, *,
    coordinator_id: str,
    site_id: str,
    employee_id: str,
    effective_from: date,
    effective_to: date,
    note: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> DecisionRecord
```

- employee must exist per §2.1 and have `day_only == True`; otherwise fail before writing;
- creates a new backend-generated rule family;
- uses exactly the existing frozen `EMPLOYEE_DAY_ONLY_N_EXCEPTION` content;
- first decision has `rel=None`.

This wrapper does not weaken any other HARD; execution remains owned by the existing DAY_ONLY exception mechanism.

### 3.4 Edit dates of the same saved matrix rule

```python
def update_employee_matrix_rule_period(
    conn, *,
    coordinator_id: str,
    site_id: str,
    rule_id: str,
    effective_from: date,
    effective_to: date,
    note: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> DecisionRecord
```

`rule_id` must identify an existing family for this Site whose **current chain end carries one of the two matrix-owned shapes**:

1. `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` with `LOCAL_RULE / HARD / RESOLVED`; or
2. `EMPLOYEE_DAY_ONLY_N_EXCEPTION` with `CONFIRMED_EXCEPTION / HARD / RESOLVED`.

Reject an unknown/wrong-Site family, an ended family whose current chain end has no rule version, every other `rule_kind`, and the right `rule_kind` under a different category/enforcement/resolution. A matrix convenience command must not mutate a `CLIENT_REQUIREMENT` or another rule merely because its structural kind can affect the same employee.

Before writing, resolve the retained `structured_parameters["employee_id"]` through `get_employee()` per §2.1. Unknown Employee is a no-write failure.

For an accepted family:

- preserve the current rule's category, rule kind, structured parameters, enforcement, resolution and optional descriptive fields; change only the effective period through a new SiteRuleVersion;
- append to the **same** rule family;
- relation is `supersedes`, matching the existing tested T010-B edit precedent;
- do not generate a new `rule_id` for an ordinary edit.

The command may edit an existing matrix-owned forbidden-rule family even when its valid parameters are broader than one single UI cell. It preserves that content rather than trying to reinterpret or normalize it.

### 3.5 Return to base state before natural expiry

```python
def end_employee_matrix_rule_early(
    conn, *,
    coordinator_id: str,
    site_id: str,
    rule_id: str,
    effective_from: date,
    note: str | None = None,
    responds_to_decision_required_id: str | None = None,
) -> DecisionRecord
```

Apply the same matrix-owned-family validation and retained-Employee validation as §3.4, then validate the requested rejecting date against the current rule version:

For a bounded current rule `[rule.effective_from, rule.effective_to]`, both inclusive:

- `effective_from < rule.effective_from` -> invalid, no write;
- `effective_from == rule.effective_from` -> valid; the restriction/exception is cancelled from its first day and therefore has zero effective days from that version;
- `rule.effective_from < effective_from < rule.effective_to` -> valid ordinary early return;
- `effective_from == rule.effective_to` -> valid; the rule stops before its otherwise-final inclusive day, so its effective applicability ends on the previous day;
- `effective_from > rule.effective_to` -> invalid no-op, no write.

For a legitimate pre-existing matrix-owned rule with `rule.effective_to is None`:

- `effective_from < rule.effective_from` -> invalid, no write;
- `effective_from >= rule.effective_from` -> valid.

For every valid case:

- append `rel="rejects"` with `rule_content=None`;
- no fake SiteRuleVersion is created;
- from the rejecting `effective_from`, base state applies according to existing T005 effective-selection semantics.

Natural expiry of a bounded rule needs no restore command. A future bounded rule can be cancelled before it starts by recording the rejection now with rejecting `effective_from == rule.effective_from`; allowing a still-earlier effective date is unnecessary and would add ambiguous provenance.

## 4. RULE FAMILY IDENTITY

A new independent period is a new rule family. Generate an opaque UUID-based `rule_id` in the application layer (for example prefix `R-EMP-MATRIX-`); the frontend does not choose it.

Do **not** derive one deterministic family ID from `(site_id, employee_id, rule_kind)`.

Reason: frozen T010-B explicitly permits a new independent period to use a new family, while an edit of the same saved restriction must stay in its existing family. A deterministic per-employee/per-kind ID would collapse those two different operations and make independent periods one permanent chain.

The created `DecisionRecord` and the existing read projection both expose `rule_id`, so a later edit/early restore can send that exact family ID back.

## 5. PERIOD SEMANTICS

For every create/update command in §3.1-3.4:

- `effective_from` and `effective_to` are required real dates;
- both boundaries are inclusive;
- require `effective_from <= effective_to`;
- open-ended matrix restrictions/exceptions are not created by these wrappers;
- after `effective_to`, existing T005 effective selection automatically returns the base state.

The generic `record_structured_rule_decision()` remains capable of other SiteRule use cases; T021b does not globally ban `effective_to=None`. Therefore update/end must safely handle a legitimate pre-existing matrix-owned open-ended family as specified above.

`end_employee_matrix_rule_early()` uses the exact boundary table in §3.5; there is no additional implicit date rule.

No history row is updated or deleted.

## 6. STATEMENT / NOTE

Screen 2 is a structured control, not the removed natural-language command interface. Therefore these wrappers generate `DecisionRecord.statement` deterministically in Polish from the semantic action and dates; the frontend does not supply free text for `statement`.

Examples of meaning, not frozen punctuation:

- `Dniówka: niedostępna od 01.09.2026 do 30.09.2026`;
- `Piątek: niedostępny od ... do ...`;
- `Nocka: czasowo dozwolona od ... do ...`;
- `Przywrócono bazowy stan Nocka od ...`.

Internal enum/rule codes must not leak into the generated coordinator-facing statement.

Optional `note` remains the coordinator's free comment/rationale and is passed unchanged through the existing coordinator-action mechanism. Do not duplicate it into `statement`.

## 7. REUSE / ATOMICITY

Every public wrapper must perform all pre-write validation first, then delegate the material write to the existing `record_structured_rule_decision()` rather than reproducing Decision Ledger, SiteRuleVersion, coordinator-action or stale-question invalidation logic.

Consequences inherited unchanged:

- active coordinator/Site context check;
- one linear decision chain per family;
- append-only decision/rule history;
- atomic decision + rule version + exactly one existing `RULE_DECISION_RECORDED` material action;
- existing `responds_to_decision_required_id` validation/linking;
- invalidation of intersecting current DECISION_REQUIRED months.

No new CoordinatorActionKind, table, column or persistence repository is authorized.

## 8. READ/WRITE ROUND TRIP

`employee_availability_matrix()` remains unchanged and is the read owner for this UI.

After any successful T021b write and after restart, the existing projection must be callable for the affected employee and expose the resulting relevant `SiteRuleVersion` plus its `rule_applicability` slices. The frontend derives checked/unchecked state from those existing facts; T021b does not create a second matrix-state DTO or persisted checkbox state.

Successful writes are therefore impossible for an unknown Employee. T021b does not promise that membership/enabled state is part of this read contract.

## 9. SCOPE

Production modification allowed:

- `rota/application/rule_decisions.py` only.

Tests:

- add one focused T021b test module;
- reuse relevant T005/T007/T010-B regressions unchanged.

No production modification to:

- `rota/domain.py`;
- persistence/schema modules;
- `rota/planning/site_rules.py`;
- eligibility/solver/validator;
- `rota/application/availability_matrix.py`;
- `rota/application/durable_inputs.py`;
- T021 frontend/FastAPI code.

If implementation proves one of those files must change to satisfy this contract, stop and return the literal blocker instead of widening scope.

## 10. MINIMUM TEST MATRIX

1. D and N creation (parameterized): generated new family, canonical weekdays 1..7, one forbidden kind, `LOCAL_RULE/HARD/RESOLVED`, inclusive bounded period.
2. Weekday creation: one ISO weekday, forbidden D+N; reject 0/8/bool and reversed date range with no write.
3. Employee identity equivalence class: unknown employee rejects D creation, N creation, weekday creation and day-only exception with zero decision/rule/action writes. An existing Employee is sufficient; no SiteMembership/enabled precondition is introduced.
4. `day_only=true` N exception: exact `CONFIRMED_EXCEPTION/HARD/RESOLVED` content; `day_only=false` rejects with no decision/rule/action write.
5. Update dates: same `rule_id`, retained employee must still exist, one new decision + SiteRuleVersion, `rel="supersedes"`, current content preserved, no parallel family.
6. Early base return boundaries for a bounded rule (parameterized): before start FAIL/no-write; equal start PASS/cancels whole period; inside PASS; equal end PASS/applicability ends previous day; after end FAIL/no-write.
7. Early base return boundaries for a pre-existing open-ended matrix-owned rule: before start FAIL/no-write; equal start and after start PASS.
8. New independent period for the same employee/cell uses a different generated `rule_id`.
9. Update/end rejects unknown, wrong-Site, ended, non-matrix, wrong-category/enforcement/resolution families, and a matrix-owned family retaining an unknown Employee, without writing.
10. Generated `statement` is Polish semantic text and caller supplies no statement parameter; note remains action metadata.
11. Existing `employee_availability_matrix()` shows the written rule/applicability before and after restart.
12. Existing eligibility + independent validator regressions remain unchanged, including `day_only` exception AND-composition with other HARDs.
13. Each successful wrapper action produces exactly one existing `RULE_DECISION_RECORDED` coordinator action and retains existing DECISION_REQUIRED linkage/invalidation semantics.

Do not add tests for hypothetical new rule kinds, membership-state policy or a generalized rule-editor API.

## 11. PREIMPLEMENTATION RE-AUDIT

Independent Codex re-audits the corrected exact contract HEAD. Per R1, do not reopen accepted design; verify only closure of R1-1 and R1-2 plus absence of contradiction introduced by their fixes.

Required checks:

1. Does every create/update/end path now enforce one consistent existing-Employee precondition before write, while deliberately adding no membership/enabled policy?
2. Is every bounded early-return boundary unambiguous and testable: before start, equal start, inside, equal end, after end?
3. Is the open-ended pre-existing-family case explicitly defined?
4. Do invalid identity/date cases require zero decision/rule/action writes?
5. Do the corrections preserve the already-accepted canonical forbidden-rule representation, family identity, `supersedes`/`rejects` relations, generic write seam and unchanged read owner?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered remaining contract defects.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: focused T021b tests + retained T005/T007/T010-B regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.
