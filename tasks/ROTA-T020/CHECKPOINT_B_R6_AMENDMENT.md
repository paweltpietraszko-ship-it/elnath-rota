# ROTA-T020 — CHECKPOINT B R6 ARCHITECT AMENDMENT

STATUS: READY FOR CODEX R6-ONLY REAUDIT — REMAINING R5-1/R5-3/R5-4 CLOSED BY CONTRACT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
R6_AUDIT_COMMIT: 501a3c69ee39a1f541a4567aa9c33d3040e83e5a
R6_AUDITED_HEAD: 21bb095ec9004c553811a4496f6d40e4630ff1a2
R6_REPORT: tasks/ROTA-T020/round_01/tests/tests_r6.txt
PARENT_CONTRACT: tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md
PARENT_AMENDMENT: tasks/ROTA-T020/CHECKPOINT_B_R5_AMENDMENT.md

## 1. PURPOSE AND PRECEDENCE

This is a narrow architect amendment answering only the findings that remained open in Codex Round 6:

- T020-B-R5-1: contradictory corrupt-duplicate settings oracle;
- T020-B-R5-3: normal/emergency T012 24h across month/year boundary;
- T020-B-R5-4: evidence matrix consequences of those two points.

T020-B-R5-2 remains CLOSED and is not reopened.

This amendment does not change owner product behavior, Checkpoint A visuals, U/C semantics, solver coverage, WorkBalance, Assignment meaning, ScheduleVersion lifecycle, TASK_SCOPE, or the two-new-file implementation shape.

Where this amendment conflicts with `CHECKPOINT_B_R5_AMENDMENT.md`, this amendment controls. Otherwise the R5 amendment and parent contract remain normative.

No production code is authorized until the next independent re-audit passes and the architect explicitly accepts that gate.

## 2. R5-1 FINAL CLOSURE — ONE OUTCOME FOR INVALID DUPLICATE SETTINGS

Round 6 correctly found that `WORK_CODE_MAPPING_AMBIGUOUS` was unreachable under the R5 validation order because the only possible >1 exact mapping candidate is already an invalid same-family duplicate signature.

The contract is simplified rather than adding an artificial second ambiguity class.

### 2.1 Remove `WORK_CODE_MAPPING_AMBIGUOUS`

`WORK_CODE_MAPPING_AMBIGUOUS` is REMOVED from the required T020 problem-code contract.

It MUST NOT be implemented merely to preserve an unreachable branch.

Any persisted settings state containing duplicate non-null `(start_time,end_time,end_next_day)` signatures inside D or inside N is invalid configuration and returns:

`PRINT_SETTINGS_INVALID`

before real-work mapping begins.

This applies equally to:

- invalid settings submitted through the persistence write API — rejected before write;
- legacy/raw/corrupt persisted settings discovered during export — `PRINT_SETTINGS_INVALID`, no PDF.

### 2.2 Ordinary mapping cardinality after settings validation

After successful settings validation, ordinary D/N mapping has exactly two reachable outcomes:

- zero exact candidates -> `WORK_CODE_MAPPING_REQUIRED`;
- exactly one exact candidate -> emit that code.

A valid settings object cannot produce more than one exact candidate within the ShiftDemand family because same-family signature uniqueness is a write/read invariant.

If implementation logic ever observes >1 after the settings object has allegedly passed validation, that is an internal invariant failure and MUST NOT be represented as a coordinator-facing product choice. The dedicated contract does not require a public third mapping code for an impossible validated state.

### 2.3 Test correction

R5 T20-31 is superseded by this exact oracle:

- zero exact candidate after valid settings -> `WORK_CODE_MAPPING_REQUIRED`;
- one exact candidate -> deterministic code;
- raw/corrupt same-family duplicate settings -> `PRINT_SETTINGS_INVALID` during settings validation, before mapping.

There is no `WORK_CODE_MAPPING_AMBIGUOUS` test.

## 3. R5-3 FINAL CLOSURE — 24H ACROSS MONTH/YEAR BOUNDARY

T020 keeps the accepted rule:

> one complete 24h WorkPeriod is printed as one `24` symbol on the WorkPeriod start date.

A period is never duplicated onto the following calendar date or following monthly print merely because it crosses midnight/month/year.

The two existing T012 cross-boundary shapes are handled separately below.

## 4. NORMAL CATALOG-H24 CROSSING MONTH/YEAR

T012 normal catalog-H24 generation stores the complete two-component occurrence as content of the ScheduleVersion month in which the occurrence STARTS, including the narrow accepted case where component 2 starts in the following month/year.

Therefore T020 does NOT need adjacent-month lookup to complete normal catalog-H24.

For requested month M:

1. apply the normal current-lineage/effective-date reconstruction for M;
2. a normal H24 occurrence whose first component start date lies in M may include component 2 whose start date lies just outside M;
3. both components must come from the same effective requested-month ScheduleSnapshot occurrence and satisfy the exact normal-H24 structural rules from the R5 amendment;
4. collapse them to one `24` symbol on component 1 start date in M;
5. count the visible 24h once in M summaries;
6. do not emit the second component as an ordinary D/N symbol in M or in the next month's export.

When exporting the following month, T020 MUST NOT import the prior month's normal-H24 component 2 as independent visible work. That component belongs to the prior month-owned complete occurrence and its accepted paper representation is already the single `24` on the prior start date.

The same rule applies at year boundary, e.g. 31.12 -> 01.01.

Malformed requested-month crossing H24 remains `WORK_PROVENANCE_INCOMPLETE`.

## 5. EMERGENCY CROSS-MONTH / CROSS-YEAR — EXISTING T012 PERSISTENCE SHAPE

T012 emergency cross-month pairing is different:

- first half remains persisted unchanged in the previous month's CURRENT schedule truth;
- pairing is created only while planning/replanning the later month;
- the later/current half reuses exactly the persisted first half's `work_period_id`;
- no new history table and no rewrite of the previous ScheduleVersion occurs.

T020 must recognize this existing persisted shape without changing it.

### 5.1 Narrow adjacent-boundary read is authorized

For emergency cross-month recognition ONLY, `rota/application/schedule_export.py` may inspect the immediately adjacent month of the same Site using EXISTING `schedule_repository` current-version/header/snapshot reads.

No new repository module, history service, solver call, or generic cross-month subsystem is authorized.

The adjacent read is restricted to deciding whether an exact boundary H12 Assignment is the other half of one persisted emergency WorkPeriod. Unrelated adjacent-month work is never imported into the requested monthly grid or summaries.

The same current-lineage/effective_from reconstruction rule used for the requested month MUST be reused for the exact adjacent boundary date. The exporter must not treat the adjacent current snapshot as retroactively effective for the whole adjacent month.

Month arithmetic must handle December -> January and January -> December of the previous year exactly.

### 5.2 No adjacent current schedule

If the immediately adjacent later month has no current ScheduleVersion, an outgoing first-half H12 item in the requested month cannot yet have a persisted T012 cross-month emergency continuation, because T012 creates that pairing only during PLAN/REPLAN of the later month.

In that case the requested-month first half remains ordinary 12h work and is mapped through the normal D/N interval code.

Likewise, if the immediately previous month has no current ScheduleVersion, a first-day H12 item in the requested month cannot be proven as an incoming emergency continuation and remains ordinary work unless its own requested-month provenance is otherwise malformed.

Missing adjacent month is not itself `NO_CURRENT_SCHEDULE` for the requested export.

### 5.3 Adjacent lineage exists but cannot be reconstructed

If an adjacent month has a current ScheduleVersion and its exact boundary-day truth must be inspected, but that current lineage has a missing parent, cycle, Site/month mismatch, or required `effective_from=None`, T020 returns `PROVENANCE_INCOMPLETE` and no PDF.

Fail-closed is required because that unresolved adjacent truth can change whether the requested boundary work is 12h ordinary work or one side of a 24h period.

### 5.4 Outgoing emergency pair — requested month contains the first half

Let first Assignment A be effective requested-month H12 work and let its actual start date lie in requested month M while its end lies in M+1.

A is upgraded from ordinary D/N presentation to one collapsed `24` symbol ONLY if the exact effective boundary truth of M+1 contains Assignment B satisfying ALL emergency rules from R5 Section 4.3 plus:

- same Site;
- same Employee;
- B starts exactly at A.end_datetime;
- B has the same non-null `work_period_id` as A;
- A and B cover distinct H12 demands;
- A is the persisted earlier/boundary half whose covered demand carries non-null `emergency_24h_rest_hours`;
- B is the terminal/current half whose `required_rest_after_hours` equals A demand's emergency snapshot.

If valid:

- render exactly one `24` in A.start_datetime.date() cell;
- suppress A's ordinary D/N symbol;
- do not import B as a separate cell into requested month M;
- M summary counts this visible work as 24h once;
- canonical revision/provenance for M includes the exact adjacent lineage metadata and B/demand boundary facts used to prove the pair.

If there is no matching B with the same `(employee_id, work_period_id)`, A remains ordinary 12h work.

If an adjacent effective B DOES share the same `(employee_id, work_period_id)` with A but the asserted pair fails the emergency structural rules, return `WORK_PROVENANCE_INCOMPLETE`; do not silently downgrade an asserted shared period to two unrelated shifts.

### 5.5 Incoming emergency pair — requested month contains the second half

Let B be effective requested-month H12 work whose start lies in requested month M and whose matching prior half A may lie in M-1.

If exact effective boundary truth of M-1 contains A with the same `(employee_id, work_period_id)` and A+B satisfy all rules in 5.4, then B is the continuation of a 24h WorkPeriod whose start date lies outside M.

Therefore in the requested M export:

- B emits NO ordinary D/N symbol;
- B emits NO second `24` symbol;
- B contributes 0 visible hours to M PLAN/WYK summaries;
- the single paper representation belongs to A's start date in M-1;
- M revision/provenance includes the exact adjacent lineage/boundary facts used to suppress B.

If there is no matching prior A with the same `(employee_id, work_period_id)`, B remains ordinary 12h work.

If a same-identity prior A exists but the pair is structurally malformed, return `WORK_PROVENANCE_INCOMPLETE`.

### 5.6 Regeneration of the earlier month after later pairing

This behavior is intentionally current-state-sensitive.

Example:

1. August PDF is generated before September has any current schedule: N 31.08 crossing midnight is ordinary 12h presentation.
2. September is later planned and T012 creates a valid emergency pair reusing the August boundary `work_period_id`.
3. Regenerating August now recognizes the adjacent persisted pair and prints one `24` on 31.08.
4. September print suppresses the 01.09 continuation because the one-symbol representation belongs to the WorkPeriod start date.

The August document revision MUST change between steps 1 and 3 because visible cells/summary and adjacent provenance changed. This is not ScheduleVersion mutation and does not create export history.

### 5.7 Revision/provenance input refinement

The parent revision rule is refined:

- adjacent month data is excluded when it is not consulted;
- when adjacent boundary truth is consulted for emergency cross-month recognition, the canonical revision input includes the exact ordered adjacent current-lineage `(version_id,effective_from)` metadata actually used plus the exact boundary Assignment/ShiftDemand facts used for recognition/suppression;
- `generated_at` remains excluded;
- unrelated adjacent work remains excluded.

Displayed provenance still identifies the requested month current ScheduleVersion as the primary schedule version. Its provenance digest covers the requested lineage plus any adjacent boundary provenance actually used by the document.

No export-history table is introduced.

## 6. R5-4 FINAL CLOSURE — MATRIX CORRECTIONS

All R5 T20-29..T20-37 tests remain required except where corrected below.

### 6.1 T20-31 corrected

Replace the R5 >1 mapping oracle with:

- valid settings + zero exact candidate -> `WORK_CODE_MAPPING_REQUIRED`;
- valid settings + one exact candidate -> deterministic work code;
- raw/corrupt same-family duplicate signature -> `PRINT_SETTINGS_INVALID` before mapping.

No `WORK_CODE_MAPPING_AMBIGUOUS` oracle exists.

### 6.2 T20-38 — normal catalog-H24 cross-month/cross-year

Parameterize at least month and year boundary cases already represented by T012.

Prove:

- complete normal H24 owned by the month of component-1 start collapses to one `24` on that start date;
- component 2 may start outside requested month;
- next-month export does not duplicate/import the prior normal-H24 second half;
- malformed crossing normal H24 -> `WORK_PROVENANCE_INCOMPLETE`.

### 6.3 T20-39 — emergency outgoing boundary before/after later PLAN

For 31.08->01.09 and 31.12->01.01 equivalents:

- before later month has a current schedule/pair, earlier first half renders ordinary 12h D/N;
- after later month persists a valid T012 emergency continuation with reused `work_period_id`, regenerating earlier month renders exactly one `24` on the earlier start date;
- earlier revision changes;
- no second-half cell is imported into earlier month's grid.

### 6.4 T20-40 — emergency incoming boundary suppression

For month and year boundary:

- later-month second half with a valid prior same-identity emergency boundary pair emits no ordinary D/N and no `24` in later month;
- later summary does not count the continuation separately;
- exact prior boundary provenance participates in revision/provenance;
- unrelated prior H12 with different work_period_id does not suppress current ordinary work.

### 6.5 T20-41 — emergency adjacent fail-closed matrix

Parameterize at least:

- same `(employee_id,work_period_id)` boundary candidate but gap/overlap;
- same identity but non-opposite D/N;
- same identity but missing emergency-rest snapshot;
- same identity but terminal rest mismatch;
- same identity but missing/contradictory demand provenance;
- adjacent current lineage missing parent/cycle/Site-month mismatch/required effective_from None.

Malformed asserted pair -> `WORK_PROVENANCE_INCOMPLETE`.

Malformed adjacent lineage required to decide boundary truth -> `PROVENANCE_INCOMPLETE`.

No partial PDF.

### 6.6 Existing positive same-month tests stay

R5 T20-34/T20-35 remain the normal/emergency SAME-MONTH shape tests. T20-38..T20-41 add boundary ownership; they do not replace same-month evidence.

## 7. VALIDATION / DATA-OWNERSHIP ORDER

The existing deterministic validation order remains, with this boundary refinement inside real-work provenance:

1. validate requested settings;
2. reconstruct requested current lineage;
3. validate requested work provenance;
4. for a boundary H12 work item only, reconstruct the immediately adjacent boundary date if a current adjacent schedule exists;
5. classify valid cross-boundary period vs ordinary work;
6. map remaining ordinary work through validated D/N settings;
7. continue with absence/layout/rendering rules.

Adjacent-month reads are read-only evidence. They never become general requested-month roster, work cells, U/C input, summaries, or solver state.

## 8. FINDING DISPOSITION

T020-B-R5-1: CLOSED by Section 2. `WORK_CODE_MAPPING_AMBIGUOUS` removed; corrupt duplicate -> `PRINT_SETTINGS_INVALID` only.

T020-B-R5-2: remains CLOSED by R5 amendment Section 3.

T020-B-R5-3: CLOSED by Sections 3-5, including normal and emergency cross-month/cross-year ownership.

T020-B-R5-4: CLOSED by Section 6, correcting T20-31 and adding T20-38..T20-41.

## 9. NEXT GATE

Codex must perform one narrow re-audit against the exact post-amendment HEAD.

Audit only:

- R6 remaining R5-1 conflict closure;
- R6 cross-month/cross-year portion of R5-3;
- corresponding R5-4 matrix closure;
- exact SHA / no production diff sanity.

R5-2 and every other previously PASS section are not reopened unless this amendment directly creates a contradiction.

Required verdict:

`PASS — REMAINING R5 FINDINGS CLOSED — READY_FOR_IMPLEMENTATION`

or

`FAIL — R5 FINDINGS REMAIN`

If PASS, architect still must explicitly accept the preimplementation gate before CC starts.
