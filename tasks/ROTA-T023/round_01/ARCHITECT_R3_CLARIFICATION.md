# ROTA-T023 — ARCHITECT R3 CLARIFICATION

STATUS: OWNER DECISION REQUIRED — NOT READY FOR CC
DATE: 2026-08-22
TASK_ID: ROTA-T023
PARENT_AUDIT_COMMIT: cb585591fbfec2a5619450ad13b13ab3758036dd
AUDIT_REPORT: tasks/ROTA-T023/round_01/tests/tests_r3.txt
AUDITED_CONTRACT_HEAD: 7fbf2455b45a5372ec7b11c0426c5e4afd463998

## 1. PRECEDENCE AND NARROW SCOPE

This clarification exists only to answer T023-R3-1 through T023-R3-6.

For those six findings it has precedence over conflicting wording in:
- `arch/FROZEN_ADDENDUM_SCHEDULE_BASED_ABSENCE_ACCOUNTING_01.md`;
- `tasks/ROTA-T023/brief.md`.

The Round-3 PASS findings are not reopened:
- owner intent / canonical schedule-based accounting remains accepted;
- durable reference snapshot remains accepted and required;
- no nominal U/C operational Assignments;
- no payroll/HR scope;
- N `17:00-05:00` and persisted legal 24h start-date anchoring remain unchanged;
- later REPLAN/restore/restart/CURRENT movement must not rewrite an already BOUND reference.

No production implementation is authorized while sections R3-3 and R3-5 below remain unresolved owner questions.

## 2. DESIGN RULE FOR ARCHITECT-OWNED PROPOSALS

No new product rule may be added merely because it gives a tidy model.

Whenever this clarification recommends an implementation shape, it states:
1. why it is recommended; and
2. the concrete failure/drift it prevents.

A recommendation does not become product semantics when the owner source is silent.

---

## 3. T023-R3-1 — EXTERNAL SUPPORT CAPTURE — CLOSED

### Corrected rule

An enabled `EXTERNAL_SUPPORT` membership by itself MUST NOT add a Site to the required absence-reference scope.

Reference Site scope for an Employee is the union of:
1. enabled `LOCAL` Site memberships; and
2. Sites on which the Employee has an actual non-CANCELLED PRIMARY reference Assignment in the effective schedule facts being captured.

The second item is schedule-fact driven, not membership-kind driven. It allows real cross-Site scheduled work to participate even when the Employee is present there as external support.

A Site reached only through a dormant/unused `EXTERNAL_SUPPORT` membership is outside reference scope and cannot create `MISSING`.

`WINDOW-03` remains unchanged: the pilot does not invent X/Y home-site HR, balance or schedule truth.

### Why this correction is recommended

It uses existing operational schedule truth instead of interpreting a membership as a schedule.

### Problem it solves

It prevents an empty EXTERNAL_SUPPORT relationship from blocking a valid LOCAL WorkBalance/PLAN/PDF while preserving real cross-Site hours when the Employee actually has scheduled PRIMARY work on another Site.

### Required oracle amendment

Replace the former membership-union oracle with:
- enabled LOCAL membership with a readable adopted schedule and no Employee period -> known 0h for that Site;
- EXTERNAL_SUPPORT membership with no actual PRIMARY reference work -> does not enter scope and does not cause MISSING;
- actual PRIMARY reference work on an external-support Site -> that Site and those exact periods enter the employee-global reference once.

---

## 4. T023-R3-2 — WEEKLY COORDINATOR TOTAL — CLOSED WITHOUT NEW ANALYTICS SUBSYSTEM

### Corrected rule

The canonical T023 accounting API MUST support an explicit inclusive date range in addition to month projection.

For a caller-supplied `[range_start, range_end]`, it returns the same canonical period-level facts and totals restricted by the existing start-date anchor.

A coordinator-facing weekly total is therefore the canonical result for the explicit week range supplied by the caller. T023 does NOT invent a new calendar-week convention, screen, persisted weekly row or separate weekly arithmetic.

Monthly and quarterly consumers continue to aggregate the same canonical period facts; no second absence calculation is allowed.

### Why this correction is recommended

The owner explicitly requires weekly/monthly/quarterly totals, while no T023 source defines a new week-boundary convention or asks for a new analytics UI.

### Problem it solves

It closes the missing weekly accounting surface without guessing Monday/Sunday boundaries or creating a parallel weekly analytics model that could drift from month/quarter arithmetic.

### Required oracle amendment

Add a T023 oracle with an explicit seven-day caller range proving:
- `weekly absence_hours == sum(canonical bound periods anchored inside that range)`;
- SICK/LEAVE precedence is identical to month accounting;
- overnight N and 24h periods belong wholly to their start date;
- summing non-overlapping explicit ranges over a month reproduces the month canonical absence total.

No new production module is required solely for this oracle.

---

## 5. T023-R3-3 — MISSING LIFECYCLE — OWNER DECISION REQUIRED

The previous contract wording is retracted where it could make `MISSING` an implicitly permanent state merely through same-chain inheritance.

### Frozen now

- `MISSING` is not known 0h.
- A BOUND reference fact remains immutable historical input.
- CURRENT must not be used later to silently rewrite a BOUND reference.
- A missing reference must not be guessed as 0/8/12/24.
- A new AvailabilityVersion may preserve BOUND predecessor facts, but this clarification does NOT authorize treating predecessor `MISSING` as an immutable business fact.

### Product case that is not defined

An active granted absence can be recorded before any adopted reference schedule exists for the Employee/month.

After the first schedule is later created, Rota needs a defined, auditable way either to:
- establish the missing nominal reference; or
- explicitly accept that no numerical absence result can ever be produced for that absence.

The existing owner material does not choose between those outcomes.

### Why no architect mechanism is frozen

Binding a later CURRENT schedule automatically could capture a post-absence/replacement schedule and violate the accepted reference invariant. Inventing a new nominal schedule/editor would expand the product.

### Problem avoided by leaving this OPEN

This prevents the architect from turning a fail-closed safety rule into either false 0h or an unapproved permanent operational dead-end.

### OWNER DECISION R3-3

When granted absence was recorded before any adopted reference schedule existed, what is the authorized coordinator path for establishing the reference hours?

No CC implementation of this case is authorized until the owner answers.

---

## 6. T023-R3-4 — TRAINEE GLOBAL AMBIGUITY — CLOSED / RETRACTED

The rule "any effective TRAINEE makes the reference day AMBIGUOUS" is removed.

T023 absence accounting follows the same work-hour ownership already used by WorkBalance:
- PRIMARY scheduled work is the absence-hour source;
- TRAINEE does not add absence hours;
- the mere presence of a TRAINEE does not make an otherwise readable PRIMARY reference ambiguous.

Existing trainee/mentor structural rules remain owned by the existing schedule/planning validation layers. T023 does not weaken or redefine them.

### Why this correction is recommended

Current WorkBalance counts PRIMARY hours, not TRAINEE hours. Reusing that ownership preserves existing semantics.

### Problem it solves

It prevents a training record from blocking solver TARGET, WorkBalance, analytics and PDF through a new T023-only ambiguity rule.

### Required oracle amendment

Replace former T23-22 with:
- a valid TRAINEE alongside coherent PRIMARY reference work does not change canonical absence hours;
- TRAINEE is not counted as an additional reference period;
- pre-existing malformed trainee/mentor structures remain failures of their existing canonical validator, not a new T023 ambiguity category.

---

## 7. T023-R3-5 — REALIZED CONFLICT NUMERIC EFFECT — OWNER DECISION REQUIRED

The previous architect rule making the whole numerical scope unavailable/fail-closed solely because of a REALIZED overlap is retracted as an unapproved product decision.

### Frozen now

Only these effects are authorized by the owner input:
- a REALIZED Assignment remains REALIZED/WYK;
- later or retroactive absence data does not rewrite that worked fact to U/C;
- the overlap is visibly surfaced for coordinator resolution;
- no automatic correction is performed.

### Not frozen

The owner source does not state whether the conflicting scheduled period must:
1. count in `absence_hours`;
2. be excluded from `absence_hours` while other non-conflicting periods remain calculable; or
3. make some numerical scope unavailable.

The architect does not choose among 1/2/3.

### Why no default is frozen

Each option changes reported absence hours and therefore solver TARGET/analytics totals. That is product behavior, not a technical fail-closed detail.

### Problem avoided by leaving this OPEN

It prevents a visibility requirement ("show the conflict") from silently becoming a much broader arithmetic/blocking rule.

### OWNER DECISION R3-5

For a reference period that overlaps a REALIZED worked fact, how should that period affect numerical `absence_hours` before the coordinator resolves the conflict?

No CC implementation of this numerical effect is authorized until the owner answers.

---

## 8. T023-R3-6 — DUPLICATED VALIDATION — CLOSED

### Corrected ownership

`rota/persistence/absence_reference_repository.py` MUST be an I/O repository only. It may persist/read the bound snapshot, but it MUST NOT contain its own implementation of:
- COVERAGE-01 completeness logic;
- Assignment/Demand structural validation;
- normal/emergency 24h structural legality;
- trainee/mentor validation.

Persisted ScheduleVersion structural invariants continue to be owned by the existing schedule persistence/lifecycle validation.

For the one capture-time question that T023 genuinely needs — whether persisted effective schedule facts are complete enough to prove the adopted PRIMARY plan rather than an unfinished gap — implementation must reuse the existing canonical coverage algorithm from `rota/planning/validator.py`.

The implementation MAY refactor the current private coverage calculation into one reusable pure helper in `rota/planning/validator.py`, with `validate()` itself calling that same helper. T023 capture calls that helper; it does not copy the algorithm.

24h grouping/structure needed to turn already-persisted reference components into one canonical period MUST reuse existing functions in `rota/planning/work_periods.py`. No T023-owned equivalent is allowed.

`rota/persistence/schedule_repository.py` remains responsible only for reading the selected persisted facts/lineage; it does not become a second planning validator.

### Why this implementation shape is recommended

It puts every invariant in the module that already owns it and shares the exact predicate rather than paraphrasing it.

### Problem it solves

It prevents T023 snapshot capture and normal planning validation from disagreeing about coverage or 24h legality after future fixes.

### TASK_SCOPE correction

Add:
- `rota/planning/validator.py`

to T023 TASK_SCOPE solely for extraction/reuse of the existing coverage predicate.

Remove `rota/planning/validator.py` from the explicit OUT OF SCOPE list.

`rota/planning/work_periods.py` remains OUT OF SCOPE for modification unless a concrete implementation/audit finding proves that an existing callable cannot be reused as-is. Calling its existing functions is allowed and does not itself require modification.

### Required oracle amendment

Add a guard proving T023 capture uses the shared coverage helper and does not contain a second coverage implementation.

Keep T012 normal/emergency 24h regression oracles unchanged; T023 must consume the existing work-period result rather than recreate it.

---

## 9. TEST MATRIX DELTAS FOR NEXT CONTRACT REVISION

The following deltas supersede only the named old T23 rows:

- old `T23-22 effective TRAINEE -> AMBIGUOUS` is withdrawn; replace with the R3-4 oracle in section 6.
- old `T23-23 REALIZED -> numerical fail-closed` is narrowed to "REALIZED remains WYK + visible conflict"; numerical absence expectation is BLOCKED by OWNER DECISION R3-5.
- add `T23-R3-1`: dormant EXTERNAL_SUPPORT membership cannot create MISSING; actual external-site PRIMARY reference work still counts once.
- add `T23-R3-2`: explicit seven-day range returns canonical weekly total from the same period facts.
- add `T23-R3-3`: no test may freeze permanent MISSING or automatic later-CURRENT rebinding before owner decision.
- add `T23-R3-6`: shared coverage owner / no duplicate coverage algorithm.

Existing T23 arithmetic, anchoring, BOUND immutability, SICK-over-LEAVE, multi-Site no-duplication, HARD eligibility and no-nominal-Assignment oracles remain closed and are not reopened by this clarification.

## 10. CHECKPOINT/GATE EFFECT

Checkpoint A may not begin implementation yet because OWNER DECISION R3-3 affects reference capture lifecycle.

Checkpoint B/C may not begin implementation yet because OWNER DECISION R3-5 affects canonical numerical output consumed by WorkBalance/solver/analytics/PDF.

After the two owner decisions are recorded, the architect must amend only R3-3/R3-5 consequences and then request a narrow independent audit of R3-1 through R3-6.

The next audit MUST NOT reopen Round-3 PASS sections 1-2 unless the owner decisions themselves materially alter them.

## 11. DELIVERY MECHANICS

This clarification commit is documentation-only. It adds exactly one file:

`tasks/ROTA-T023/round_01/ARCHITECT_R3_CLARIFICATION.md`

It does not modify production code, tests, `arch/spec.md`, `arch/FROZEN.lock`, the prior audit report, or the already-recorded owner night-shift decision.

## 12. ARCHITECT OUTPUT STATUS

OWNER DECISION REQUIRED

Open product questions only:
- R3-3: authorized recovery/reference-establishment path when granted absence predates any adopted reference schedule;
- R3-5: numerical `absence_hours` effect of a period that conflicts with REALIZED work.
