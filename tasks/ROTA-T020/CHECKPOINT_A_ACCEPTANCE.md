# ROTA-T020 — CHECKPOINT A OWNER / ARCHITECT ACCEPTANCE

STATUS: CHECKPOINT A ACCEPTED — CHECKPOINT B OPEN FOR ARCHITECT CONTRACT DESIGN — NOT READY FOR PRODUCTION CC
DATE: 2026-08-20
TASK_ID: ROTA-T020
BASE_BRANCH: main
BASE_SHA: d9c87185e3051aa65df3234c8db2d703fe32c5d8
TASK_BRANCH: arch/rota-t020-schedule-export-2026-08-20
CHECKPOINT_A_ARTIFACT_COMMIT: d88a85b06a2de98eda65617603b12caec0cf5d59
PARENT_CONTRACT: tasks/ROTA-T020/brief.md
OWNER_ACCEPTANCE: explicit in conversation on 2026-08-20

This document is the Section 19 architect/owner acceptance record required to close Checkpoint A and permit Checkpoint B architecture to be designed.

It does not modify either accepted PDF, does not authorize production implementation by itself, and does not resolve the separate product questions already identified for Checkpoint B.

## 1. EXACT ACCEPTED VISUAL ARTIFACTS

The accepted artifacts are exactly the files as stored at commit:

`d88a85b06a2de98eda65617603b12caec0cf5d59`

1. `tasks/ROTA-T020/checkpoint_a/schedule_12h.pdf`
   - Git blob SHA: `91d617c32b96296814debc7696f5a621cde40973`
2. `tasks/ROTA-T020/checkpoint_a/schedule_24h.pdf`
   - Git blob SHA: `2a0f6a706142eaa77f8992c98dd1cc98d2ebf1ba`

The visual contract is bound to these exact artifact bytes. Regenerated or edited PDFs are not automatically accepted even if they have the same filenames.

The accepted prototype renderer state is also the one present at that commit:

`tasks/ROTA-T020/checkpoint_a/render_samples.py`
Git blob SHA: `ceebc745baacb28fd337d8d0aa17b82667999f58`

The renderer remains prototype evidence only. Checkpoint B may reuse its presentation logic where appropriate, but production code must not import the checkpoint renderer.

## 2. OWNER A15 VISUAL DECISIONS — ACCEPTED

The owner's explicit `Akceptuję` freezes the following A15 decisions as embodied by the exact PDFs above.

### A15-1 Paper / orientation

**ACCEPTED:** A3 landscape is the production visual baseline for the first T020 printable schedule implementation.

A later move to a different paper size or orientation is not a technical refactor; it requires an explicit owner/architect amendment if it materially changes the accepted layout/readability.

### A15-2 Pagination

**ACCEPTED:** the pagination and whole-document composition visible in the exact 12h/24h artifacts is the baseline.

Production B must preserve equivalent readability for the supported first-scope cases. It must not silently switch to a materially different pagination strategy merely to simplify rendering.

If larger real rosters cannot fit without degrading the accepted minimum readability, B must fail/handle the presentation explicitly according to its contract rather than shrink text below an unreadable threshold or silently omit rows.

### A15-3 Table density / employee-name treatment

**ACCEPTED:** the 31-day / approximately-10-employee density, enlarged employee-name column, distinct PLAN/WYK sub-row labels, and the final d88a85b long-name fitting behavior are acceptable visual behavior.

The accepted renderer may scale row height upward for smaller rosters while preserving the same overall body area; long employee names may be reduced only enough to fit inside the accepted name area and must never collide with the PLAN/WYK label.

This is a presentation rule, not a roster-size business limit. T020 must not introduce a hard employee-count limit of 10.

### A15-4 PLAN / WYK visual

**ACCEPTED:** separate PLAN and WYK sub-rows per Employee in the form shown by both accepted PDFs.

The print remains a current, correct schedule view rather than a blame/history display. Previously replaced personnel are not presented as a public "did not come" history merely because Rota retains historical ScheduleVersions.

Production semantic reconstruction of which ScheduleVersion state supplies each day is still a Checkpoint B contract matter; the accepted visual does not authorize `parent = PLAN / child = WYK`.

### A15-5 24h visual

**ACCEPTED:** one complete 24h WorkPeriod is represented as one clear symbol in the column of its start date, as demonstrated by `schedule_24h.pdf`, with its value explained by the legend.

The production mapping must continue to use real T012 WorkPeriod/demand provenance and may not treat two unrelated 12h Assignments as one 24h period merely because their durations add to 24h.

### A15-6 Legend

**ACCEPTED:** the legend presentation and its intentionally asymmetric owner-frozen values as shown in the exact PDFs.

The following remain frozen:
- D1=12h, D2=4h, D3=24h, D4=2h, D5=24h;
- N1=12h, N2=16h, N3=24h, N4=24h, N5=24h;
- U1=12h, U2=16h, U3/U4/U5=rezerwa by default;
- C1=12h, C2=16h, C3/C4/C5=rezerwa by default.

The 24h sample's `U3=24h` / `C3=24h` remains explicitly a demo of coordinator configuration, not a new global default.

The 12h 40h example remains exactly:
- PLAN: `D1 / D1 / N2` = 40h;
- WYK: `U1 / U1 / U2` = 40h.

### A15-7 Grayscale readability

**ACCEPTED:** meaning must survive black-and-white printing using text plus non-color-only visual distinctions.

The accepted family distinction is the one demonstrated by the artifacts: work-code fill density plus explicit symbol text, leave with a solid-border cue, sickness with a dashed-border cue, and explicit PLAN/WYK labels.

Color may assist but must never be the sole carrier of meaning.

### A15-8 Header / provenance presentation

**ACCEPTED:** the visual placement/concept for company name, Site name, editable period title, true date range, schedule provenance, document revision and generated-at timestamp.

Checkpoint B must replace DEMO values with real Rota/configuration data while retaining the accepted distinction between:
- editable title/labels;
- true date range;
- schedule-state provenance;
- document revision;
- generation time.

Changing only print header/configuration must not create a new ScheduleVersion.

## 3. CHECKPOINT A IS CLOSED

Checkpoint A is complete and frozen against the exact artifacts above.

No further sample-generation round is required before Checkpoint B architecture begins.

Any future visual change to the frozen A15 decisions requires a narrow owner/architect amendment; it must not be introduced silently by production implementation.

## 4. CHECKPOINT B IS NOW OPEN — BUT NOT READY FOR CC

This acceptance satisfies the Section 19 A -> B visual gate.

**Checkpoint B architecture/design may now begin.**

It does NOT yet authorize production CC because the Checkpoint-A contract already identified two real product decisions that cannot be guessed technically:

### B-PD-01 — Site-local LEAVE_GRANTED / SICK_LEAVE summary for a shared Employee

T018/WorkBalance absence accounting is Employee-global, while T020 print summaries are required to be Site-local. Before the production B contract is frozen, the owner must define how the 8h qualified-workday absence amount is attributed when the same Employee is modeled on more than one Site, or explicitly constrain the first production scope so the ambiguity cannot occur.

T020 must not duplicate the same 8h onto multiple Site prints and must not invent Site ownership from membership or schedule data without an owner rule.

### B-PD-02 — empty EXTERNAL_SUPPORT row population

Before the production B contract is frozen, the owner must decide whether an enabled EXTERNAL_SUPPORT Employee with no effective Assignment on the printed Site/month gets an empty employee row.

The already-recorded safe candidate remains:
- enabled LOCAL -> row;
- any Employee with an effective Assignment on this Site/month -> row regardless of membership_kind;
- EXTERNAL_SUPPORT with no effective Assignment -> no empty row.

This candidate is not product truth until explicitly accepted by the owner.

## 5. IMPLEMENTATION HOLD

Until B-PD-01 and B-PD-02 are explicitly closed and the architect publishes the Checkpoint B implementation contract:

**PRODUCTION CC MUST NOT START T020 CHECKPOINT B.**

No production PDF generator, production dependency, schema migration, persistence setting, application export read model, or UI integration is authorized by this acceptance record alone.
