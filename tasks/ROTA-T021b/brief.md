# ROTA-T021b — EMPLOYEE MATRIX RULE WRAPPERS

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS
ARCHITECT_INPUT_SHA: `86979980c5c94371317c68647e51aaf68e41a853`
ARCHITECT_INPUT: `arch/T021_screen2_rule_wrapper_architect_brief_2026-08-23.md`
PARENT_UI_TASK: `tasks/ROTA-T021/brief.md`
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

- requires an existing employee with `day_only == True`; otherwise fail before writing;
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

For an accepted family:

- preserve the current rule's category, rule kind, structured parameters, enforcement, resolution and optional descriptive fields; change only the effective period through a new SiteRuleVersion;
- append to the **same** rule family;
- relation is `supersedes`, matching the existing tested T010-B edit precedent;
- do not generate a new `rule_id` for an ordinary edit.

The command may edit an existing matrix-owned forbidden-rule family even when its valid parameters are broader than one single UI cell. It preserves that content rather than trying to reinterpret or normalize it.

### 3.5 Earlier return to base state

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

- same matrix-owned-family validation as §3.4;
- append `rel="rejects"` with `rule_content=None`;
- no fake SiteRuleVersion is created;
- from `effective_from` the base state returns according to existing T005 effective-selection semantics.

This is only an **early** return. Natural expiry at `effective_to` needs no restore command.

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
- open-ended matrix restrictions/exceptions are not accepted by these wrappers;
- after `effective_to`, existing T005 effective selection automatically returns the base state.

The generic `record_structured_rule_decision()` remains capable of other SiteRule use cases; T021b does not globally ban `effective_to=None`.

`end_employee_matrix_rule_early()` requires only the new inclusive `effective_from` of the rejecting decision.

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

Every public wrapper must delegate the material write to the existing `record_structured_rule_decision()` rather than reproducing Decision Ledger, SiteRuleVersion, coordinator-action or stale-question invalidation logic.

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

After any T021b write and after restart, the existing projection must expose the resulting relevant `SiteRuleVersion` plus its `rule_applicability` slices. The frontend derives checked/unchecked state from those existing facts; T021b does not create a second matrix-state DTO or persisted checkbox state.

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
3. `day_only=true` N exception: exact `CONFIRMED_EXCEPTION/HARD/RESOLVED` content; `day_only=false` rejects with no decision/rule/action write.
4. Update dates: same `rule_id`, one new decision + SiteRuleVersion, `rel="supersedes"`, current content preserved, no parallel family.
5. Early base restore: same `rule_id`, `rel="rejects"`, no new SiteRuleVersion; applicability ends the day before rejecting `effective_from`.
6. New independent period for the same employee/cell uses a different generated `rule_id`.
7. Update/end rejects unknown, wrong-Site, ended, non-matrix, or wrong-category/enforcement/resolution families without writing.
8. Generated `statement` is Polish semantic text and caller supplies no statement parameter; note remains action metadata.
9. Existing `employee_availability_matrix()` shows the written rule/applicability before and after restart.
10. Existing eligibility + independent validator regressions remain unchanged, including `day_only` exception AND-composition with other HARDs.
11. Each successful wrapper action produces exactly one existing `RULE_DECISION_RECORDED` coordinator action and retains existing DECISION_REQUIRED linkage/invalidation semantics.

Do not add tests for hypothetical new rule kinds or a generalized rule-editor API.

## 11. PREIMPLEMENTATION AUDIT

Independent Codex audits the exact contract HEAD and answers:

1. Does this design reuse the frozen T010-B `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` representation rather than introduce a competing ALLOWED-based matrix write path?
2. Do new-period vs same-period-edit semantics correctly map to new family vs same family without deterministic per-employee IDs?
3. Are `supersedes` for date edit and `rejects` for early base restore consistent with existing T005/T010-B effective-selection behaviour?
4. Does temporary N for `day_only=true` reuse only the frozen narrow exception and preserve every other HARD?
5. Does the matrix write boundary prevent these wrappers from rewriting a `CLIENT_REQUIREMENT`, unresolved rule or another non-matrix family merely because it can affect the same employee?
6. Can all wrapper writes delegate to `record_structured_rule_decision()` without duplicating transaction/action/invalidation machinery?
7. Will the unchanged `employee_availability_matrix()` read back every state these wrappers create?
8. Does any clause introduce code or product semantics unnecessary for Screen 2?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, or
- `FAIL` with numbered defects tied to exact clauses.

Until PASS: `CC READ-ONLY / NOT READY FOR IMPLEMENTATION`.

After implementation: focused T021b tests + retained T005/T007/T010-B regressions + full quality gates + independent exact-SHA implementation audit + architect exact-SHA review. Merge remains an explicit owner action.
