# Cursor audit request — backend function ↔ T021 UI coverage (2026-08-22)

STATUS: request for an independent scan, not yet run. Output goes back
through CC for verification against source (same discipline as
`tasks/CURSOR_AUDIT_2026-08-21/FINDINGS_VERIFIED.md`) before anything
here is trusted or acted on.

## Task for Cursor

Cross-reference every public function (not prefixed `_`) in
`rota/application/*.py` against `arch/T021_spec.md` (the T021 coordinator
UI spec — one section per screen, dense bullet format, no prose).

Report three categories:

**A. OMISSIONS** — a public `rota/application/` function with no mention
anywhere in `arch/T021_spec.md` (by name or by clear paraphrase of what
it does). For each: file:line, function name, one-line description of
what it does, which screen (if any) seems like the natural fit.

**B. INACCURACIES** — a place in `arch/T021_spec.md` that describes a
function's behavior, parameters, or return shape in a way that doesn't
match the actual current function signature/body. For each: the spec.md
line, what it claims, what the code actually does, file:line of the
real function.

**C. DEPENDENCY/SEQUENCING CHECK** — spec.md describes several
screen-to-screen links (e.g. "Decyzje koordynatora" options linking to
"Ręczna korekta"/"Panel sterowania"/Obiekt reguły; "Ostatnia akcja" on
"Przegląd" linking into "Planowanie miesiąca"; "target_hours" set on
the per-employee screen but read by "Analityka i bilanse"). For each
such link claimed in spec.md, confirm both ends are backed by functions
that actually exist and actually connect the way spec.md describes (same
IDs, same scoping, no invented glue). Flag any link that doesn't hold up
against the real code.

## Scope

Include: every file in `rota/application/`.
Exclude: `rota/planning/**`, `rota/persistence/**` internals (only
relevant if an `application/` function's docstring/body cites them and
that citation needs checking), `arch/**` other than `T021_spec.md`,
`tests/**`.

## Known findings already in spec.md (2026-08-22, don't just re-report these — use them as a sanity check that you're reading the same file)
- `bootstrap.coordinator_context_completeness` / `month_plan_readiness`
  — already found and written up (see "COMPLETENESS AUDIT" section at
  the top of spec.md).
- `durable_inputs.set_calendar_day` — already flagged as omitted.
- `durable_inputs.update_site_profile`'s SiteProfile toggles
  (`day_only_blocks_n`, `external_support_enabled`, `training_s_*`) —
  already flagged as omitted/not editable.
- Coordinator account management (`bootstrap.active_coordinators`/
  `all_coordinators`, `durable_inputs.update_coordinator`/
  `update_association`) — already flagged as entirely unrepresented.
- `availability_matrix.employee_availability_matrix` — already flagged
  as the purpose-built read-model the per-employee matrix screen should
  have been checked against.
- `precheck.precheck` — already flagged as unplaced, low priority.
- `open_month.open_month` / `months_with_schedule` — already flagged as
  a richer read-model several screens could ground against.

If your scan reproduces exactly these seven and finds nothing else, say
so plainly — that is itself a useful confirmation, not a failure to
find something new.

## Output format

Same shape as `tasks/CURSOR_AUDIT_2026-08-21/FINDINGS_VERIFIED.md`:
plain findings with file:line evidence, no fix proposals, no
PASS/FAIL/priority verdict (that's Paweł + architect's call after CC
verifies).
