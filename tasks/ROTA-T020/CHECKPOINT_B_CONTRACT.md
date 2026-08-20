# ROTA-T020 — CHECKPOINT B IMPLEMENTATION CONTRACT

STATUS: READY FOR CODEX CHECKPOINT-B PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
BASE_BRANCH: main
BASE_SHA: d9c87185e3051aa65df3234c8db2d703fe32c5d8
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
DESIGN_PARENT_HEAD: 55c9b388959a3bb757d2d3e72d61f81d5e3bce88
OWNER_SOURCE: arch/T020_schedule_export_architect_brief.md
CHECKPOINT_A_ACCEPTANCE: tasks/ROTA-T020/CHECKPOINT_A_ACCEPTANCE.md
AUTHORITATIVE_ABSENCE_CORRECTION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_05.md
ROW_POPULATION_DECISION: tasks/ROTA-T020/CHECKPOINT_B_OWNER_DECISIONS_02.md section 1

## 1. PURPOSE AND HARD BOUNDARY

Checkpoint B integrates the accepted printable schedule with real Rota data.

The result is a static, ready-to-print PDF for exactly one Site and one calendar month.

T020 is a READ/PRESENTATION feature. It MUST NOT change:

- PlanningEngine / solver decisions;
- Assignment coverage semantics;
- Availability semantics;
- T018 absence accounting;
- WorkBalance calculations;
- ScheduleVersion lifecycle or history;
- T019b coordinator-action / DECISION_REQUIRED memory;
- `arch/spec.md` or `arch/FROZEN.lock`.

The operational solver continues to cover 100% of real Site demand using Employees who are actually eligible to work. U/C print symbols never reduce Site demand and never become operational Assignments.

No XLSX, PDF import, editable form, synchronization, payroll/HR logic, second solver, second schedule history, workflow engine, event bus, command bus, generic configuration framework, or export-owned planning truth is authorized.

## 2. FROZEN VISUAL BASELINE

Production B must preserve the visual decisions accepted at exact Checkpoint A artifact commit:

`d88a85b06a2de98eda65617603b12caec0cf5d59`

Accepted artifacts:

- `schedule_12h.pdf` blob `91d617c32b96296814debc7696f5a621cde40973`;
- `schedule_24h.pdf` blob `2a0f6a706142eaa77f8992c98dd1cc98d2ebf1ba`.

Frozen B baseline:

- A3 landscape;
- month in columns;
- Employees in rows;
- separate PLAN/WYK subrows;
- accepted long-name fit behavior and enlarged name column;
- accepted approximately-10-Employee density without a business limit of 10;
- one complete 24h WorkPeriod displayed as one symbol on its start date;
- accepted grayscale cues: work fill density, U solid-border cue, C dashed-border cue, explicit text and PLAN/WYK labels;
- header/provenance composition with company, Site, editable period label, true date range, schedule provenance, document revision and generated-at.

Production MUST NOT import `tasks/ROTA-T020/checkpoint_a/render_samples.py`.

A material visual change requires a narrow owner/architect amendment. Implementation convenience is not sufficient reason to repaginate radically, omit rows or shrink below the accepted readability floor.

## 3. PRODUCTION CHANGE SURFACE — MINIMAL

Checkpoint B production implementation is limited to:

NEW:

1. `rota/application/schedule_export.py`
2. `tests/test_t020.py`

MODIFIED:

3. `rota/persistence/db.py`
4. `rota/persistence/site_repository.py`
5. `rota/persistence/employee_repository.py`
6. `pyproject.toml`

No other production file is authorized without an architect amendment after a concrete audit finding.

In particular, implementation MUST NOT modify:

- `rota/planning/**`;
- `rota/balance.py`;
- `rota/domain.py`;
- `rota/persistence/schedule_lifecycle.py`;
- `arch/spec.md`;
- `arch/FROZEN.lock`;
- `Grafiki/**`.

Mechanical size gates remain the repository defaults: max 600 lines per Python file and max 50 lines per function. Dedicated `tests/test_t020.py` must also remain <=600 lines; use parametrization/helpers instead of duplicating cases.

## 4. DEPENDENCY

Production may add exactly:

`reportlab==5.0.1`

to `pyproject.toml`, matching the library proven in Checkpoint A.

No production code may depend on a machine-specific path such as `C:\\Windows\\Fonts`.

Production must resolve a Unicode-capable TTF from the installed ReportLab distribution/runtime in a path-independent way and test Polish diacritics. No font binary is added to the repository.

If the required runtime font cannot be resolved, generation fails explicitly rather than silently replacing Polish text with missing glyphs.

## 5. MIGRATION 7 — SITE PRINT SETTINGS ONLY

`rota/persistence/db.py` advances `LATEST_SCHEMA_VERSION` from 6 to 7 and adds exactly one current-state table:

`site_print_settings`

Required columns:

- `site_id TEXT PRIMARY KEY REFERENCES sites(site_id)`;
- `company_print_name TEXT NOT NULL`;
- `site_print_name TEXT NOT NULL`;
- `base_regime TEXT NOT NULL CHECK(base_regime IN ('12h','24h'))`;
- `work_code_intervals_json TEXT NOT NULL`;
- `reserve_hours_json TEXT NOT NULL`.

There is NO print-settings history table and NO generated-document history table.

`site_print_settings` is mutable current state. Saving it does not create ScheduleVersion and does not create a T019b material coordinator-action record because it changes print presentation, not schedule truth.

### 5.1 Fixed values are not duplicated as mutable configuration

The frozen legend hour values remain code constants in T020 and are not written as mutable DB values:

- D1=12, D2=4, D3=24, D4=2, D5=24;
- N1=12, N2=16, N3=24, N4=24, N5=24;
- U1=12, U2=16;
- C1=12, C2=16.

`reserve_hours_json` contains exactly configurable slots U3/U4/U5/C3/C4/C5, each `null` or a positive integer hour value. Unknown keys, zero/negative values and attempts to override frozen slots are rejected at the settings write boundary.

### 5.2 Work-code interval mapping

`work_code_intervals_json` contains the exact interval signature used to map real work Assignments to D/N presentation codes. Each configured D/N code maps to:

- start local time;
- end local time;
- `end_next_day` boolean.

A work Assignment is never mapped by duration alone. A four-hour interval is D2 only if its actual interval exactly matches the configured D2 signature.

The configured code family must also match the real D/N `ShiftDemand.shift_kind`.

## 6. SETTINGS API

`rota/persistence/site_repository.py` owns narrow CRUD for `site_print_settings`; no new repository module is created.

Write/read APIs accept/return the exact fields above and validate/serialize JSON deterministically (`sort_keys=True` or equivalent). No generic key/value settings abstraction is introduced.

Company print name and Site print name are durable Site defaults.

`period_label` is intentionally NOT stored as a Site-global default in migration 7. It is supplied for each export request because it describes that document/month. It remains editable in Rota but cannot accidentally become the label of every historical month. The true month/date range is always derived from the requested `month` and is never editable.

A settings-only change produces a different next document revision but no ScheduleVersion.

## 7. APPLICATION ENTRY POINT AND RESULTS

All B read-model assembly, presentation decomposition, revision calculation and PDF rendering live in the single new module:

`rota/application/schedule_export.py`

It contains only narrow local immutable DTO/result types needed by this use case; it must not duplicate domain entities.

Required public generation entry point:

`generate_schedule_pdf(conn, *, site_id, month, period_label, generated_at=None)`

It returns exactly one of:

- READY result: PDF bytes + full document revision + schedule provenance;
- PROBLEM result: stable problem code + human-readable coordinator message, with NO partial PDF bytes.

No SQL may appear in `rota/application/schedule_export.py`; it uses existing persistence repositories plus the narrow settings/membership helpers authorized here.

## 8. STABLE FAIL-CLOSED PROBLEM CODES

The first implementation must use stable codes for at least:

- `PRINT_SETTINGS_MISSING`
- `NO_CURRENT_SCHEDULE`
- `PROVENANCE_INCOMPLETE`
- `UNSUPPORTED_SHIFT_KIND`
- `UNSUPPORTED_TRAINEE_PRINT`
- `WORK_PROVENANCE_INCOMPLETE`
- `WORK_CODE_MAPPING_REQUIRED`
- `MULTIPLE_WORK_ITEMS_PER_CELL`
- `ABSENCE_SITE_AMBIGUOUS`
- `ABSENCE_KIND_CONFLICT`
- `ASSIGNMENT_ABSENCE_CONFLICT`
- `ABSENCE_DECOMPOSITION_REQUIRED`
- `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`
- `PRINT_FONT_UNAVAILABLE`

The module must have deterministic validation order so identical invalid state produces the same primary problem code.

No problem may be converted into a guessed PDF.

## 9. TRUE DAILY SCHEDULE STATE FROM CURRENT LINEAGE

T020 must not read the current snapshot as if it applied retroactively to the whole month and must not use `parent=PLAN / child=WYK`.

For the requested Site/month:

1. require `month.day == 1`;
2. derive true month start/end from the calendar;
3. require a current ScheduleVersion;
4. follow `parent_version_id` from current to root using repository APIs;
5. every header in the current lineage must match the requested Site/month;
6. detect missing parent/cycle/contradiction and fail `PROVENANCE_INCOMPLETE`;
7. every lineage version required for daily selection must have real `effective_from`; legacy `None` is never guessed;
8. reverse lineage root -> current;
9. for each calendar date select the deepest version in THIS current lineage whose `effective_from <= date`;
10. dates before the first applicable lineage version contain no effective work cells rather than receiving a later plan retroactively;
11. load/cache each selected ScheduleSnapshot once.

If current has been restored to an older branch, only that restored current lineage is authoritative.

A WORKING ScheduleVersion may be replaced in place without changing `version_id`; therefore document revision must hash the final export read model/content and cannot be only the version id.

## 10. REAL WORK CELLS

Normal work cells come only from the effective daily scheduling truth.

For public printable work:

- include non-CANCELLED PRIMARY Assignments;
- map PLANNED and REALIZED PRIMARY to the real D/N/24 work presentation code;
- PLAN and WYK show the same current-correct work symbol for ordinary work, matching the accepted no-blame view;
- CANCELLED/NN is not printed as a public blame symbol;
- never reconstruct a replaced Employee from an older version merely to show history.

An effective TRAINEE Assignment has no frozen first-scope paper semantics and therefore returns `UNSUPPORTED_TRAINEE_PRINT` rather than being silently omitted or counted as PRIMARY.

Every displayed Assignment must have coherent covered ShiftDemand provenance. Missing/contradictory linkage fails `WORK_PROVENANCE_INCOMPLETE`.

If any effective item that must be shown has catalog kind `INNY`, fail `UNSUPPORTED_SHIFT_KIND`; never omit it.

### 10.1 Exact D/N mapping

For a normal work item, mapping requires all of:

- Assignment actual start/end interval;
- covered ShiftDemand D/N family;
- exact configured interval signature for the selected D/N code;
- frozen code hour value equal to actual item duration.

No duration-only fallback exists. No unknown interval is silently shown as the nearest code.

### 10.2 T012 24h WorkPeriod

One 24h symbol may be emitted only when real T012 provenance proves one complete WorkPeriod:

- shared real `work_period_id`/demand work-period identity;
- same Employee;
- coherent components;
- contiguous actual interval;
- exactly 24h total;
- effective daily lineage does not produce contradictory component truth.

The symbol is placed on the WorkPeriod start date as accepted in Checkpoint A.

Two unrelated 12h Assignments must never be combined merely because their durations sum to 24h.

If more than one independent work item would occupy the same Employee/date cell and they are not one valid collapsed WorkPeriod, fail `MULTIPLE_WORK_ITEMS_PER_CELL`.

## 11. PRINTED ROSTER

Row population is frozen:

- enabled LOCAL membership on the printed Site -> row always, even with zero operational Assignments;
- any Employee with an effective Assignment in the reconstructed Site/month daily state -> row, regardless of membership kind;
- EXTERNAL_SUPPORT with zero effective Assignment -> no empty row.

Earlier dates that legitimately come from an older parent in the current lineage count for row inclusion.

Rows are sorted deterministically by `display_name.casefold()` then `employee_id`.

U/C presentation is generated only for an enabled LOCAL Employee of the printed Site. EXTERNAL_SUPPORT rows receive real work cells only; T020 does not attribute Employee-global U/C accounting to an external-support Site.

`rota/persistence/employee_repository.py` may add one batch membership read helper solely to avoid N+1 reads for the roster/ambiguity checks. No membership semantics change is authorized.

## 12. SITE-LOCAL ABSENCE FAIL-CLOSED BOUNDARY

Availability/T018 absence accounting is Employee-global and has no Site id.

T020 must not duplicate the same U/C accounting onto multiple local Site printouts.

First-scope rule:

- if a qualifying U/C absence is to be presented for an Employee who has exactly one enabled LOCAL Site membership, that LOCAL Site may present the canonical T018 monthly absence total;
- if the Employee has more than one enabled LOCAL Site membership, generation fails `ABSENCE_SITE_AMBIGUOUS` before producing any PDF;
- no Site ownership is inferred from readiness, target hours, current assignment distribution or arbitrary membership ordering.

This is a fail-closed scope boundary, not a new persistent absence-ownership model.

## 13. CANONICAL U/C HOURS

For each enabled LOCAL row, load current active Availability overlapping the true month.

Only:

- `LEAVE_GRANTED` -> U family;
- `SICK_LEAVE` -> C family

participate in T020 U/C presentation.

`LEAVE_PLAN`, `DAY_SHIFT_OFF` and `UNAVAILABLE_24H` are not silently reclassified as U/C.

CalendarDay must fully cover the month whenever qualifying U/C intersects it. T020 reuses the existing T018 `excused_absence_days_in_month` semantics; missing/conflicting calendar data remains fail-closed and is not replaced with a weekday-only guess.

Compute each kind independently:

`absence_hours = qualified_workdays_for_kind * EXCUSED_ABSENCE_HOURS_PER_DAY`

with the existing T018 constant (8h).

T020 does not use `WorkBalance.planned_hours` or `WorkBalance.realized_hours` as an absence source; those fields are real Assignment sums and WorkBalance is Employee-global across Sites.

If LEAVE_GRANTED and SICK_LEAVE overlap on any calendar date for one Employee, fail `ABSENCE_KIND_CONFLICT`; no precedence is invented.

If an effective real operational Assignment overlaps an active granted leave/sickness day for the same Employee, fail `ASSIGNMENT_ABSENCE_CONFLICT`; T020 must not overwrite the work cell or move the absence symbol to conceal contradictory source data.

## 14. U/C IS PRESENTATION, NOT ASSIGNMENT

For absence hours T020 fills otherwise empty qualifying print cells.

Each hour-bearing absence presentation position is a pair:

- PLAN: one synthetic D/N print code;
- WYK: one U/C print code of the exact same hour value.

The pair is a paper convention only. It does not assert a ShiftDemand, does not create Assignment, does not cover Site demand and is never persisted into ScheduleVersion.

Frozen example:

- 40h LEAVE_GRANTED -> PLAN `D1 / D1 / N2` = 40h;
- WYK `U1 / U1 / U2` = 40h.

SICK_LEAVE uses the analogous C family.

The full Availability calendar span may carry the accepted absence visual cue, including intervening weekend/holiday cells, while only T018-qualified workdays are eligible to carry hour-bearing presentation pairs.

## 15. DETERMINISTIC ABSENCE DECOMPOSITION

### 15.1 Legal pairs

A legal absence pair exists only when the selected PLAN D/N code and selected U/C code have exactly the same positive hour value.

For each hour value, use the first legal pair under these fixed code priorities:

PLAN priority:

`D1, D2, D3, D4, D5, N1, N2, N3, N4, N5`

U/C priority inside its family:

`U1..U5` or `C1..C5`.

### 15.2 Regime boundary

For base regime `12h`:

- 24h D/N denominations are forbidden for absence presentation;
- `can_work_24h=True` does not change this.

For base regime `24h`:

- legal 24h pairs may be used when the corresponding U/C reserve is configured;
- legal 12h/16h pairs remain available.

### 15.3 Optimization and tie-break

For the canonical absence total:

1. find an exact sum using legal positive pairs only;
2. minimize number of symbols;
3. among equal-length solutions choose lexicographically smallest sequence of pair-priority ranks;
4. render the chosen sequence in that deterministic priority order;
5. place it into the first qualifying empty absence workday cells in chronological order.

The frozen 40h case therefore resolves to `D1,D1,N2` paired with `U1,U1,U2`.

No rounding, nearest value or forbidden code is allowed.

If no exact sum exists, or the minimum exact decomposition needs more symbols than available qualifying empty absence cells, return `ABSENCE_DECOMPOSITION_REQUIRED` and no PDF.

A default one-qualified-workday 8h absence is expected to hit this problem unless the effective configured legend actually provides a legal equal-value PLAN/U/C pair. Configuring only `U3=8`/`C3=8` is insufficient if no legal D/N 8h pair exists. T020 must not invent two symbols in one day cell without a future owner amendment.

## 16. SITE-ONLY SUMMARY ARITHMETIC

Every printed row includes:

- PLAN h;
- WYK h;
- URLOP h;
- L4 h.

All four summaries are derived from the visible cells of THIS Site export, never from cross-Site WorkBalance totals.

Definitions:

- PLAN h = visible real work PLAN code hours + synthetic absence PLAN pair hours;
- WYK h = visible real work WYK code hours + visible U/C code hours;
- URLOP h = visible U* hours;
- L4 h = visible C* hours.

Therefore frozen 40h leave contributes 40h to PLAN, 40h to WYK and 40h to URLOP.

A full-month 168h U/C presentation contributes 168h to PLAN/WYK and 168h to the corresponding U/L4 summary while Site operational demand remains independently covered by actual Assignments.

Work by the same Employee on another Site must not enter these print summaries.

T020 does not force PLAN h to equal the Employee-global `target_hours`; it presents the one-Site schedule plus the frozen U/C paper convention.

## 17. DOCUMENT REVISION AND PROVENANCE

No export-history table is added.

Before rendering, build one canonical JSON representation of the complete final export read model using stable ordering and sorted JSON keys.

The revision input includes at least:

- site_id;
- true month and true date range;
- period_label;
- company/site print names;
- base regime;
- effective interval mapping and reserve configuration;
- current ScheduleVersion id;
- ordered used current-lineage `(version_id, effective_from)` data;
- deterministic roster order;
- every rendered PLAN/WYK cell;
- every row summary.

It excludes:

- `generated_at`;
- output filename/path;
- incidental PDF metadata.

Document revision is the full lowercase SHA-256 hex digest of that canonical JSON and is printed in the PDF.

Same schedule/config/title with a later generation time -> same revision.

Any visible header/config/schedule/cell/summary change -> different revision.

Schedule provenance displayed in the PDF contains the current ScheduleVersion id plus a full SHA-256 digest of the ordered current lineage metadata used by the document. This is provenance, not a new history subsystem.

`generated_at` is a separate offset-aware ISO timestamp. Tests inject it explicitly; runtime defaults to the actual generation time.

## 18. PDF RENDERING RULES

Renderer uses ReportLab and returns PDF bytes; application caller decides filesystem/location.

Required behavior:

- A3 landscape;
- static PDF, no editable form/import feature;
- accepted header/table/legend composition;
- explicit true date range independent of editable period label;
- approximately 170pt employee-name area as accepted;
- PLAN/WYK labels cannot collide with long names;
- long names may shrink only enough to fit and never below the accepted readability floor;
- row height never shrinks below the accepted Checkpoint A baseline (22pt per subrow); smaller rosters may scale up;
- weekend/holiday cue remains grayscale-safe;
- D/N/24 work uses non-color fill-density/text cues;
- U uses solid-border/text cue;
- C uses dashed-border/text cue;
- meaning remains available without color.

If the real roster/content cannot fit the accepted first-scope single-sheet composition while preserving the accepted minimum readability, return `ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`; do not omit Employees, shrink to unreadable type or silently choose a materially different pagination model.

Use deterministic/invariant ReportLab mode where practical for testability. PDF byte identity is not the product revision; the canonical revision described above is.

## 19. NO-BLAME / DAILY CORRECTION ACCEPTANCE

A manual correction that replaces A with B from its real `effective_from` must print:

- dates before `effective_from`: the then-effective state from the earlier lineage version;
- `effective_from` and later: the corrected state;
- B as the current-correct worker where applicable;
- no public NN/blame history for replaced A.

A one-day correction must not trigger or simulate REPLAN in T020.

T020 reads whatever valid ScheduleVersion lineage Rota has already produced; it never writes or recomputes that lineage.

## 20. REQUIRED DEDICATED TEST MATRIX

`tests/test_t020.py` must cover at least the following with parameterization/helpers where needed:

T20-01 fresh DB migrates to schema 7; schema 6 migrates to 7 without rewriting existing schedule/history; future schema still fails closed.

T20-02 settings save/read survive reconnect; changing only print settings creates no ScheduleVersion.

T20-03 production ReportLab import works and READY bytes begin with `%PDF`.

T20-04 PDF page is A3 landscape and Polish diacritics render using path-independent runtime font resolution.

T20-05 same state/config/period label with different `generated_at` gives same revision; header/period change changes revision; visible schedule change changes revision.

T20-06 effective_from lineage: earlier days use parent, effective date and later use child; never `parent=PLAN/child=WYK`.

T20-07 restored older current version uses only that current lineage.

T20-08 enabled LOCAL with zero Assignment gets a row; EXTERNAL_SUPPORT zero Assignment omitted; EXTERNAL_SUPPORT with any effective Assignment included.

T20-09 CANCELLED/NN is not emitted as public blame cell.

T20-10 effective TRAINEE produces `UNSUPPORTED_TRAINEE_PRINT` with no PDF.

T20-11 actual D/N mapping requires exact configured interval; same duration with wrong start/end fails `WORK_CODE_MAPPING_REQUIRED`.

T20-12 valid T012 24h WorkPeriod is one start-date symbol; unrelated 12h Assignments are never collapsed.

T20-13 effective `INNY` produces `UNSUPPORTED_SHIFT_KIND` with no PDF.

T20-14 exact frozen 40h leave produces PLAN `D1/D1/N2` and WYK `U1/U1/U2`.

T20-15 full-month canonical 168h U/C produces exact 168h presentation without altering Site coverage.

T20-16 12h base regime plus `can_work_24h=True` still forbids 24h absence denominations.

T20-17 reserve U/C configuration persists across reconnect and is used deterministically when it forms a legal equal-value pair.

T20-18 one-workday 8h absence with default legend produces `ABSENCE_DECOMPOSITION_REQUIRED`; no rounding and no partial PDF.

T20-19 overlapping LEAVE_GRANTED/SICK_LEAVE produces `ABSENCE_KIND_CONFLICT`.

T20-20 actual Assignment on an active U/C date for same Employee produces `ASSIGNMENT_ABSENCE_CONFLICT`.

T20-21 U/C Employee with multiple enabled LOCAL Site memberships produces `ABSENCE_SITE_AMBIGUOUS`; no duplication across Site exports.

T20-22 Site print work summaries ignore Assignments from other Sites.

T20-23 PLAN/WYK/URLOP/L4 summary arithmetic equals visible symbol values.

T20-24 incomplete CalendarDay coverage with qualifying U/C remains fail-closed through canonical T018 semantics.

T20-25 roster overflow is explicit and does not shrink below accepted row/font floor or omit rows.

T20-26 a current WORKING snapshot replacement that changes visible content changes document revision even when version id is unchanged.

T20-27 full existing test suite remains PASS; T020 does not change solver/T018/WorkBalance behavior.

T20-28 Ruff and `git diff --check` PASS; frozen lock remains unchanged; backend gate uses the final preimplementation accepted SHA as `before_sha`.

## 21. REGRESSION / ARCHITECTURE ASSERTIONS

Implementation audit must prove:

- no diff in `rota/planning/**`;
- no diff in `rota/balance.py`;
- no diff in `rota/domain.py`;
- no diff in `rota/persistence/schedule_lifecycle.py`;
- no diff in `arch/spec.md` / `arch/FROZEN.lock`;
- no diff in `Grafiki/**`;
- no second Assignment layer for U/C;
- no persisted PDF/export history;
- no N+1 employee Availability/membership reads in the export path where batch helpers exist/are authorized;
- no SQL in application module;
- no import of checkpoint prototype into production;
- no OS-specific font path;
- exactly two new non-pipeline implementation files.

## 22. BACKEND MECHANICAL BASE

The implementation backend gate must use the exact architect/Codex preimplementation acceptance SHA as `before_sha`, not `main`.

Reason: owner/architect/audit task artifacts already exist on the task branch before implementation and must not be counted as implementation additions.

With that base, authorized implementation has exactly two new non-pipeline files:

- `rota/application/schedule_export.py`;
- `tests/test_t020.py`.

Any backend `WYMAGA_DECYZJI` is reported to architect and handled mechanically; it is not permission to redesign product behavior.

## 23. TASK_SCOPE FOR IMPLEMENTATION

The canonical `TASK_SCOPE:` is stored in `tasks/ROTA-T020/brief.md` and must match this contract.

No production path outside that scope is authorized.

## 24. PREIMPLEMENTATION GATE

Before CC writes production code, Codex must independently audit this exact contract/HEAD against:

- owner brief;
- Checkpoint A exact acceptance;
- authoritative owner correction 05;
- current main implementation at `d9c87185e3051aa65df3234c8db2d703fe32c5d8`.

Codex MUST NOT write production code during this audit and MUST NOT redesign product behavior.

Required verdict:

`PASS — READY_FOR_IMPLEMENTATION`

or

`FAIL — CONTRACT/IMPACT FINDINGS`

with exact findings and evidence.

Until PASS is recorded and accepted by architect:

**PRODUCTION CC MUST NOT START CHECKPOINT B.**
