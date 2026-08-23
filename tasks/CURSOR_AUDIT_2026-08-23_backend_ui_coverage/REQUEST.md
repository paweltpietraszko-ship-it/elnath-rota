# Cursor audit request — backend function ↔ T021 UI coverage, round 2 (2026-08-23)

STATUS: request for an independent scan, not yet run. Output goes back
through CC for verification against source (same discipline as
`tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`) before
anything here is trusted or acted on. Cursor's raw output is data to
verify, not a verdict to act on directly.

## Why this round exists

While writing `tasks/ROTA-T021/brief.md` §5.1 (Panel sterowania →
Obsada, per-employee screen), CC missed two already-existing pieces of
code on the first pass and only found them after the fact:

- `rota/persistence/availability_repository.py::list_active_overlapping`
  — an existing read that already does date-range overlap filtering CC
  nearly reinvented from scratch.
- `rota/planning/eligibility.py::_BLOCKING_KIND_PRIORITY` — an existing,
  owner-approved (2026-08-14) rule for how overlapping absence *kinds*
  resolve (e.g. sick leave interrupts vacation), found only because
  Paweł asked a plain-language question about real-world behavior that
  turned out to already be solved in code.

The first round (2026-08-22) scoped itself to `rota/application/` only
and explicitly excluded `rota/planning/**`. That exclusion is exactly
where the second miss above lived. This round widens scope on purpose.

## Task for Cursor

Cross-reference every public function (not prefixed `_`) in
`rota/application/*.py`, `rota/persistence/*.py`, and every module-level
constant/function in `rota/planning/*.py` that encodes a coordinator-
facing business rule (not solver-internals math) against:

1. `tasks/ROTA-T021/brief.md` (the LIVE, current contract — supersedes
   `arch/T021_spec.md` wherever the two disagree; note any such
   disagreement as its own finding),
2. `arch/T021_spec.md` (for screens brief.md hasn't reached yet),
3. the two currently-open architect briefs:
   - `arch/T021_screen2_rule_wrapper_architect_brief_2026-08-23.md`
   - `arch/T021_screen2_availability_singularity_architect_brief_2026-08-23.md`

Report four categories:

**A. OMISSIONS** — a public function/rule with no mention anywhere in
the four documents above (by name or clear paraphrase). For each:
file:line, function/constant name, one-line description of what it
does, which screen (per `T021_spec.md`'s nav list) seems like the
natural fit — or "none obvious" if genuinely unclear.

**B. INACCURACIES** — a place in brief.md or spec.md that describes a
function's behavior, parameters, return shape, or an enum's values in a
way that doesn't match the actual current code. For each: the doc + line
making the claim, what it claims, what the code actually does, file:line
of the real function/definition.

**C. EXISTING SOLUTIONS TO OPEN QUESTIONS** — specifically for the two
architect briefs above: is there ALREADY a function, helper, or
documented owner-decision comment in the code (anywhere in `rota/`,
including `rota/planning/`) that fully or partially answers either
brief's open question, that the brief's author (CC) missed? This is the
category that matters most this round — say explicitly if you checked
and found nothing, that's a useful negative result too.

**D. DEPENDENCY/SEQUENCING CHECK** — same as round 1: for any
screen-to-screen link brief.md or spec.md claims (e.g. a value written
on one screen and read by another), confirm both ends are backed by
functions that actually exist and actually connect the way claimed (same
IDs, same scoping, no invented glue).

## Scope

Include: `rota/application/*.py`, `rota/persistence/*.py` in full;
`rota/planning/*.py` limited to coordinator-facing rules/constants (not
solver internals like constraint-satisfaction machinery) — if unsure
whether something counts, include it and let CC's verification pass
filter it out.
Exclude: `arch/**` other than the four documents named above,
`tests/**` (except as evidence for a finding, e.g. a real usage example
clarifying a function's actual shape).

## Known findings already accounted for (don't just re-report these — use as a sanity check you're reading current state)

From round 1 (2026-08-22, `FINDINGS_VERIFIED.md`), all already fixed in
`arch/T021_spec.md`:
- `bootstrap.coordinator_context_completeness` / `month_plan_readiness`
- `durable_inputs.set_calendar_day`
- `durable_inputs.update_site_profile`'s SiteProfile toggles
- Coordinator account management functions
- `availability_matrix.employee_availability_matrix`
- `precheck.precheck`
- `open_month.open_month` / `months_with_schedule`

From this round's own motivating case (already known, don't re-report):
- `availability_repository.list_active_overlapping` /
  `list_active_overlapping_for_employees`
- `eligibility.py::_BLOCKING_KIND_PRIORITY` and its owner-decision
  comment (2026-08-14)

## Output format

Same shape as `tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/FINDINGS_VERIFIED.md`:
plain findings with file:line evidence, no fix proposals, no
PASS/FAIL/priority verdict (that's Paweł + architect's call after CC
verifies).
