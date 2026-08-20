# ROTA-T020 — CHECKPOINT B R5 ARCHITECT AMENDMENT

STATUS: READY FOR CODEX R5-ONLY REAUDIT — R5-1..R5-4 CLOSED BY CONTRACT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
AUDIT_COMMIT: 891013d3ccecf8fdbe8a5772d17be4fdb21ac111
AUDITED_HEAD: d05410afad336b146b9ff808566fa60030367978
AUDIT_REPORT: tasks/ROTA-T020/round_01/tests/tests_r5.txt
PARENT_CONTRACT: tasks/ROTA-T020/CHECKPOINT_B_CONTRACT.md

## 1. PURPOSE AND PRECEDENCE

This is a narrow architect amendment answering only Codex findings T020-B-R5-1 through T020-B-R5-4.

It does not change owner product behavior, Checkpoint A visuals, U/C semantics, solver coverage, WorkBalance, Assignment meaning, ScheduleVersion lifecycle, TASK_SCOPE or the two-new-file implementation shape.

Where this amendment is more specific than the parent contract, this amendment controls.

The next Codex round MUST re-audit only R5-1, R5-2, R5-3 and R5-4 plus exact-SHA/no-production-diff sanity. It must not reopen sections already PASS unless this amendment creates a direct contradiction.

## 2. R5-1 CLOSED — EXACT WORK-CODE SETTINGS SCHEMA AND MAPPING

The parent contract Section 5.2 is refined as follows.

### 2.1 Exact `work_code_intervals_json` shape

The persisted JSON value is one object with EXACTLY these ten keys:

`D1,D2,D3,D4,D5,N1,N2,N3,N4,N5`

No key may be missing and no unknown key is allowed.

Each value is either `null` (code unused for real-work mapping on this Site) or an object with EXACTLY:

- `start_time`: zero-padded 24-hour local clock string `HH:MM`;
- `end_time`: zero-padded 24-hour local clock string `HH:MM`;
- `end_next_day`: JSON boolean.

No seconds, timezone suffix, alternate time spelling, additional field or implicit default is accepted.

For validation, combine the times with an arbitrary anchor date and add one calendar day to the end iff `end_next_day=true`. The resulting duration must be strictly positive and must equal the frozen hour value of that exact code.

Therefore, for example:

- a D1 mapping must describe exactly 12h;
- a D2 mapping exactly 4h;
- a D3/D5 mapping exactly 24h;
- an N2 mapping exactly 16h.

A signature whose clock fields imply another duration is invalid even if the coordinator intended that code.

### 2.2 Signature uniqueness

Among non-null D codes, `(start_time,end_time,end_next_day)` must be unique.

Among non-null N codes, the same signature must be unique.

The same clock signature may exist once in D and once in N because `ShiftDemand.shift_kind` is an independent discriminator.

Duplicate non-null signatures inside one family are rejected at the settings write boundary. Settings are also revalidated when read for export, so raw-DB corruption cannot bypass the rule.

### 2.3 Stable invalid-settings result

Add stable problem code:

`PRINT_SETTINGS_INVALID`

Malformed JSON, wrong key set, malformed time, wrong field set/type, non-positive/frozen-duration mismatch, invalid reserve configuration, or duplicate same-family work signature returns `PRINT_SETTINGS_INVALID` and no PDF.

Persistence write APIs raise their narrow validation error before writing invalid settings; export-side read of already-corrupt persisted settings returns the stable application problem above.

### 2.4 Exact ordinary real-work mapping cardinality

For an ordinary non-collapsed D/N work item, candidate codes are only non-null configured codes whose:

1. family equals the covered effective ShiftDemand `shift_kind`;
2. start/end/end_next_day signature equals the Assignment actual interval exactly;
3. frozen code hour value equals the Assignment actual duration.

Cardinality is normative:

- zero candidates -> `WORK_CODE_MAPPING_REQUIRED`;
- exactly one -> emit that code;
- more than one -> `WORK_CODE_MAPPING_AMBIGUOUS` and no PDF.

Add stable problem code:

`WORK_CODE_MAPPING_AMBIGUOUS`

The `>1` branch is required even though a valid settings write prevents it; it is the fail-closed guard for corrupt/legacy/raw persisted settings.

A validated collapsed 24h WorkPeriod uses the accepted dedicated `24` work symbol and is NOT passed through this ordinary D/N candidate selection. D/N 24h-valued legend slots remain available to the frozen absence-pair convention where legal; they do not create an alternative symbol choice for one already-collapsed real T012 WorkPeriod.

## 3. R5-2 CLOSED — DATE ANCHOR FOR OVERNIGHT REAL WORK

The parent contract Section 9/10 daily-state rule is refined with one universal work-item anchor.

### 3.1 Ordinary Assignment anchor

For every ordinary non-collapsed Assignment, including a night shift that crosses midnight:

`work_item_date = Assignment.start_datetime.date()`

That date controls BOTH:

- which daily ScheduleVersion snapshot is authoritative for this work item;
- which calendar cell receives the work symbol.

The Assignment is not duplicated into its end date merely because its interval crosses midnight.

### 3.2 `effective_from` boundary example

For an N Assignment starting on day 10 and ending on day 11, with a child ScheduleVersion `effective_from=day 11`:

- the item is anchored to day 10;
- the day-10 effective snapshot supplies the item;
- it appears in the day-10 cell only;
- the child becoming effective on day 11 does not retroactively replace, duplicate or erase that already-started item from day 10.

This is consistent with the owner rule that dates before `effective_from` preserve the then-effective plan and with existing Rota start-date anchoring used by demand/site-rule/day-off logic.

### 3.3 24h anchor

A validated 24h collapsed WorkPeriod remains anchored to the start datetime of its first component, as already frozen by Checkpoint A. Its single `24` symbol is emitted only in that start-date cell.

24h structural recognition MUST use the effective component truths produced by the start-date anchoring rule; components from arbitrary historical/non-current lineages may never be mixed in merely to complete a pair.

## 4. R5-3 CLOSED — MECHANICAL DEFINITION OF VALID T012 24H

The phrase `complete/coherent T012 WorkPeriod` is replaced by the exact rules below.

Any item asserting 24h provenance but failing its applicable shape returns `WORK_PROVENANCE_INCOMPLETE`; it is never rendered as two guessed 12h codes merely to hide the malformed period.

### 4.1 Common rules

For any collapsed 24h work period:

- only effective, non-CANCELLED PRIMARY Assignments participate;
- both component Assignment actual intervals must exactly equal their covered ShiftDemand intervals;
- every component must resolve its covered ShiftDemand unambiguously;
- the two effective Assignment intervals are directly contiguous (`first.end == second.start`), non-overlapping and total exactly 24h;
- the ShiftDemand kinds are both explicit and opposite D/N;
- the Employee is identical across both components;
- `work_period_id` is non-null and identical for that Employee across the two components;
- component demand ids are distinct;
- no third effective Assignment for the same `(employee_id, work_period_id)` is allowed;
- no component may be TRAINEE or CANCELLED;
- collapse emits exactly one accepted `24` symbol on the first component start date.

Missing half, extra half, gap, overlap, interval-vs-demand mismatch, employee mismatch, period-id mismatch or missing demand provenance fails `WORK_PROVENANCE_INCOMPLETE`.

### 4.2 Normal catalog 24h shape

A normal T012 24h occurrence is valid for collapse only when BOTH covered demands satisfy all of:

- `catalog_kind == ShiftCatalogKind.H24`;
- the same non-null `work_period_template_id`;
- `work_period_component` values are exactly `{1,2}`, once each;
- component 1 starts first and is exactly 12h;
- component 2 starts exactly when component 1 ends and is exactly 12h;
- total template occurrence is exactly 24h.

At the occurrence level, the set of effective PRIMARY employees on component 1 must equal the set on component 2. Each Employee in that set must have exactly one Assignment on each component and the same non-null `work_period_id` across the pair.

This supports `required_primary_count > 1` without mixing employees between halves.

A H24 demand with missing template id, missing/repeated/wrong component number, more/fewer than two effective H24 demand components for the occurrence, employee-set mismatch or contradictory template identity is `WORK_PROVENANCE_INCOMPLETE`.

### 4.3 Emergency 24h shape

An emergency T012 24h occurrence is NOT a catalog-H24 pair. It is valid for collapse only when the two covered demands satisfy all of:

- both are plain `catalog_kind == ShiftCatalogKind.H12`;
- each demand/Assignment interval is exactly 12h;
- they are directly contiguous;
- D/N kinds are explicit and opposite;
- the earlier demand has non-null `emergency_24h_rest_hours`;
- the terminal/second Assignment `required_rest_after_hours` equals that earlier demand emergency-rest snapshot;
- both Assignments have the same non-null `(employee_id, work_period_id)` identity.

These are the persisted structural facts already used by T012 emergency validation; T020 only recognizes them and does not create or authorize an emergency pair.

If two H12 Assignments share one `(employee_id, work_period_id)` and therefore assert one multi-component period, but the exact emergency shape above is not satisfied, export fails `WORK_PROVENANCE_INCOMPLETE` rather than treating them as unrelated standalone work.

A singleton ordinary H12 Assignment remains ordinary work and is not an emergency candidate merely because T012 gives standalone solved work a non-null `work_period_id`.

### 4.4 No arbitrary combination

Two independent 12h Assignments with different work-period identity never collapse even if contiguous, opposite D/N and totaling 24h.

The exporter does not infer a WorkPeriod from arithmetic alone.

## 5. R5-4 CLOSED — MANDATORY NEGATIVE EVIDENCE SUPPLEMENT

The parent contract T20-01..T20-28 remains required. The following additional tests are mandatory and may be parameterized; numbering here is additive.

### T20-29 — provenance fail-closed matrix

Parameterize at least:

- missing lineage parent;
- parent cycle;
- lineage Site mismatch;
- lineage month mismatch;
- a lineage version required for daily selection with `effective_from=None`.

Each returns `PROVENANCE_INCOMPLETE`, no PDF.

### T20-30 — print-settings validation matrix

Parameterize at least:

- missing D/N key;
- unknown D/N key;
- malformed/non-canonical time string;
- missing/extra signature field;
- wrong JSON type;
- signature duration different from frozen code hours;
- duplicate non-null signature inside D;
- duplicate non-null signature inside N;
- invalid reserve key/value.

Persistence write rejects; corrupt persisted equivalents read by export return `PRINT_SETTINGS_INVALID`.

### T20-31 — real-work mapping cardinality

Prove:

- zero exact candidate -> `WORK_CODE_MAPPING_REQUIRED`;
- one exact candidate -> deterministic code;
- raw/corrupt settings producing >1 exact candidates -> `WORK_CODE_MAPPING_AMBIGUOUS`.

No nearest-duration fallback.

### T20-32 — overnight `effective_from` boundary

A normal N Assignment starts on day 10, ends day 11; child is effective day 11.

Prove that the work item comes from the day-10 effective truth and is rendered only in the day-10 cell. No duplicate on day 11 and no retroactive child replacement.

### T20-33 — ordinary work provenance / cell-conflict matrix

Parameterize at least:

- missing covered demand;
- contradictory Assignment-vs-demand interval needed for displayed work;
- missing/contradictory D/N provenance;
- two independent effective work items targeting one Employee/date cell.

Return `WORK_PROVENANCE_INCOMPLETE` or `MULTIPLE_WORK_ITEMS_PER_CELL` according to the parent contract validation order; no partial PDF.

### T20-34 — malformed normal H24 matrix

Parameterize at least:

- one missing component;
- repeated component number;
- wrong component numbers (not exact `{1,2}`);
- >2 H24 components for one template occurrence;
- component template-id mismatch;
- employee present on only one half / different employee sets;
- per-Employee work_period_id mismatch;
- gap;
- overlap;
- non-12h component;
- Assignment interval not equal to covered component demand.

Each fails `WORK_PROVENANCE_INCOMPLETE`, no partial 12h fallback.

### T20-35 — malformed emergency H24 matrix

Parameterize at least:

- !=2 Assignments sharing asserted emergency work-period identity;
- non-H12/INNY component;
- same rather than opposite D/N;
- gap;
- overlap;
- missing first-demand `emergency_24h_rest_hours`;
- terminal rest different from emergency snapshot;
- different employee/work-period identity;
- Assignment interval not equal to demand interval.

Each fails `WORK_PROVENANCE_INCOMPLETE`.

Also retain a positive emergency pair and prove it collapses to one `24` symbol, while two unrelated H12 periods never collapse.

### T20-36 — accepted-layout boundary including header

Exercise long company name, Site print name and period label together with body/legend content at the accepted font/readability floors.

If the complete accepted single-sheet composition cannot fit, return `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`; no clipping, omission, hidden text or below-floor shrinking.

The stable code name is retained even when the overflowing content is header/legend rather than row count; in T020 it means `accepted single-sheet content does not fit`.

### T20-37 — static PDF

For READY output prove at least:

- valid PDF header/page generation;
- no AcroForm/widget form fields are emitted (`/AcroForm` and `/Subtype /Widget` absent from generated document structure/bytes);
- no production import/read-back API from PDF/XLSX is introduced by `schedule_export.py`;
- PDF bytes are output-only and do not write schedule state.

No second PDF parser dependency is required merely for this oracle.

## 6. VALIDATION ORDER ADDENDUM

For deterministic primary problems, validation order is refined only where R5 introduced siblings:

1. request/month basics;
2. settings presence and `PRINT_SETTINGS_INVALID`;
3. current lineage/provenance;
4. supported roster/role/kind boundaries;
5. real-work provenance including 24h structural recognition;
6. real-work code cardinality (`REQUIRED` before render; `AMBIGUOUS` when >1);
7. Assignment/absence contradictions and Site ambiguity;
8. absence exact decomposition;
9. accepted-layout fit;
10. rendering/font failure.

Within one structural category, deterministic iteration is chronological then stable id ordering.

## 7. ARCHITECT FINDING DISPOSITION

T020-B-R5-1: CLOSED BY Sections 2.1-2.4 above.

T020-B-R5-2: CLOSED BY Section 3 above.

T020-B-R5-3: CLOSED BY Section 4 above.

T020-B-R5-4: CLOSED BY Section 5 above.

No production code has been authorized by this closure.

## 8. NEXT GATE

Codex must now perform a narrow R5 re-audit against the exact post-amendment HEAD.

Required verdict:

`PASS — R5-1..R5-4 CLOSED — READY_FOR_IMPLEMENTATION`

or

`FAIL — R5 FINDINGS REMAIN`

If PASS, architect must still explicitly accept the preimplementation gate before CC starts.
