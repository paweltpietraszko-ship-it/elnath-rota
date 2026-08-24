# Cursor T021-coverage audit — verified findings (2026-08-22)

STATUS: INPUT FOR ARCHITECT/CODEX OPINION — not a task brief, not an
implementation instruction. Every claim below was independently
re-checked by CC against current source (`e05dfb7`) before being
trusted, same discipline as `tasks/CURSOR_AUDIT_2026-08-21/
FINDINGS_VERIFIED.md`. Cursor's raw output (relayed via Paweł, dense
PR-style) is in `tasks/CURSOR_AUDIT_2026-08-22_ui_coverage/RAW_CURSOR.md`
if needed for reference — not itself trusted as a source.

## CONFIRMED — real findings

### V-B1. STATUS block self-contradicts the retraction two sections above it
`arch/T021_spec.md`'s STATUS block (originally lines ~129-142) still
listed "(2) site-configuration-completeness backend function — NEW,
surfaced this round" as an open work item, even though the
"COMPLETENESS AUDIT" section above it already retracted that exact
claim (`coordinator_context_completeness` + `month_plan_readiness`
already exist). Self-contradiction from an incomplete edit, not two
different facts. FIXED.

### V-B2. Workspace/Przedpokój section still cites `list_sites`, contradicting the resolved decision
The "## Workspace / Przedpokój" section's own body (Source line,
"Wszystkie" bullet) still named `site_repository.list_sites` — the
"RESOLVED" note recording the switch to
`bootstrap.active_sites_for_coordinator(coordinator_id)` was added
elsewhere in the doc but the primary section was never edited to
match. FIXED.

### V-B3. Five function signatures in the Planowanie miesiąca section omit `coordinator_id`
Real signatures (`rota/application/plan_ops.py`,
`rota/application/lifecycle_ops.py`):
- `plan_month(conn, *, site_id, month, coordinator_id, effective_from=None)`
- `select_candidate(conn, *, site_id, month, candidate, coordinator_id, note=None, responds_to_decision_required_id=None)` — `coordinator_id` is REQUIRED; omitting it is not just incomplete but wrong, since `MissingCoordinatorActor` is raised if the caller doesn't supply an explicit actor (ROTA-T019b section 14 removed the old fallback to the version's own `created_by`).
- `replan(conn, *, site_id, month, coordinator_id, effective_from, note=None, responds_to_decision_required_id=None)`
- `finalize(conn, *, site_id, month, coordinator_id, acknowledged_deviation_ids, acknowledged_at=None, reason=None, responds_to_decision_required_id=None)`
- `restore(conn, *, site_id, month, coordinator_id, version_id, note=None, responds_to_decision_required_id=None)` — spec.md was also missing `note` and `responds_to_decision_required_id` entirely for this one.
spec.md's versions of all five dropped `coordinator_id` (and restore
additionally dropped two more params). FIXED.

### V-B4. "Analityka... never throws" is too absolute
`analytics_read.py:172-173`: `if month.day != 1: raise ValueError(...)`.
spec.md's "Degrades gracefully, never throws" was describing the
DATA-degradation behavior (missing target_hours / incomplete calendar
→ warnings, not an exception) which remains true, but the blanket
"never throws" is false given the month-shape precondition. FIXED —
narrowed the claim.

### V-B5. `CoordinatorActionKind` has 18 values, spec.md said 17 twice
Recounted the actual enum (`rota/site_memory_types.py`) against
spec.md's own listed items: both are 18 (`CONTEXT_CONFIGURATION_SAVED`
... `SCHEDULE_RESTORED`, counted). spec.md said "17" at two places
while listing all 18 names — a plain counting error, not a missing
value. FIXED (both instances).

### V-B6. The 24h matrix column was documented with the wrong revert mechanism
spec.md's Obsada section stated the whole matrix (Ogólna dostępność,
Dniówka, Nocka, 24h, weekdays) uses "Unchecking = od–do date range =
HARD constraint, auto-reverts after 'do'". True for the
`AvailabilityRecord`-backed and `SiteRuleVersion`-backed columns (which
carry `effective_from`/`effective_to`), FALSE for 24h:
`SiteMembership.can_work_24h` (`rota/domain.py`) is a plain persistent
`bool` with no date-range field at all, set via `update_membership` —
toggling it is permanent until toggled back, no auto-revert. FIXED —
24h is now documented as a separate, plain-boolean mechanism.

### V-B7. `employee_availability_matrix` covers fewer kinds than the mockup implies, and no read source was ever named for the absence log
`rota/application/availability_matrix.py`:
`_RELEVANT_AVAILABILITY_KINDS = (SICK_LEAVE, LEAVE_GRANTED, UNAVAILABLE_24H)`
— excludes `DAY_SHIFT_OFF` and `LEAVE_PLAN`.
`_RELEVANT_RULE_KINDS = (EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS, EMPLOYEE_DAY_ONLY_N_EXCEPTION)`
— excludes `EMPLOYEE_ALLOWED_SHIFT_KINDS`/`EMPLOYEE_ALLOWED_WEEKDAYS`
even though both are real rule kinds (`eligibility.py` docstring). My
own earlier "Mechanism correction" note in spec.md implied this one
function covers all four rule kinds and all five availability kinds —
it doesn't. Consequence: the EmployeeDetail absence log (which needs
all 5 `AvailabilityKind` values, since `append_availability` accepts
any of them) cannot be powered by `employee_availability_matrix` alone
— no broader read function was ever named for it in spec.md. FIXED —
narrowed the mechanism-correction claim, flagged the absence-log read
source as still unconfirmed (candidate: `availability_history`/direct
`availability_repository` query, not verified this round).

### V-B8. `DAY_SHIFT_OFF-01` is never translated to Polish — a backend anglicism the earlier sweep missed
`rota/planning/decision_guidance.py::_render_condition`: `if
raw_condition == "DAY_SHIFT_OFF-01": return raw_condition` — returns
the bare code, checked BEFORE `_BUILT_IN_CONDITION_TEXT` (which has no
entry for it either). A coordinator hitting this specific blocker on
Decyzje koordynatora would see the literal string "DAY_SHIFT_OFF-01",
not Polish text. The earlier anglicism sweep only caught the "checkbox"
word in the same file's `_BUILT_IN_CONDITION_TEXT` dict and missed this
second, separate backend-text gap. FIXED — added to the cross-cutting
anglicism rule's backend-finding list.

### V-A1. `bootstrap_or_resume_coordinator_context` never mentioned anywhere in spec.md
The actual function that creates the first Coordinator/SiteProfile/
Site/Association (bootstrapping a brand-new Site) — no screen, no
mention. Consequence: there is no documented "+ Nowy obiekt" flow
anywhere in T021 at all; `Main.dc.html` only lists existing sites.
FLAGGED, not built — needs Paweł's placement call (own screen? a form
reachable from workspace?).

### V-A2. `all_sites_for_coordinator` never mentioned in spec.md itself
(Was mentioned in chat and in the older `T021_ui_facts_2026-08-21.md`
facts doc, never carried into spec.md.) Relevant if "Wszystkie" should
ever mean "every site that exists" rather than "every site this
coordinator has" — not needed given the resolved decision (V-B2), but
worth naming as the function that would answer a hypothetical "all
sites, any coordinator" admin view if one is ever wanted.

### V-A3/A4. `availability_history` and `decision_chain_for_rule_family` were investigated but never written into spec.md
Both were read/discussed in chat during earlier screen-building
(availability_matrix.py investigation; Historia i audyt build) but the
actual spec.md text for Historia i audyt only lists
`effective_rules_for_month`/`rules_history_for_site`/
`provenance_for_rule_version`/`decision_for_rule` — `decision_chain_for_rule_family`
(confirmed in `memory_read.py` as `= rule_history`, i.e. same data as
`rules_history_for_site` under a per-rule-family framing) was dropped
from the written spec despite being found. `availability_history`
(`availability_matrix.py:75`, full version chain for one
`availability_id` family) is the more likely correct source for the
EmployeeDetail absence log than `employee_availability_matrix` (see
V-B7) — NOT YET confirmed as the actual answer, just the best current
candidate. FIXED — both added to spec.md with the absence-log question
left explicitly open.

### V-A5-A8. `generate_profile_demands`, `resolved_rule_version_ids`,
`category_for_rule`, `save_site_membership`, `require_real_date` — internal plumbing, correctly out of a coordinator-facing spec
Checked each: demand generation from a profile, rule-version-id
resolution for provenance stamping, deviation-category lookup, an
internal training-write helper, and a date-shape guard. None are
independently coordinator-triggered actions or reads — each is called
BY one of the functions spec.md already documents. Cursor's literal
"omitted" is correct; treating them as gaps would not be. NOT flagged
as findings requiring action.

## CONFIRMED — dependency (§C) findings

### V-C1. `current_decision_required_months_for_site` has no application-layer wrapper
Lives in `rota/persistence/site_memory.py`. `memory_read.py` wraps its
sibling functions (`current_decision_required`,
`decision_for_rule_version`, `rule_history`, `rule_provenance`) but not
this one — spec.md's Decyzje koordynatora, Przegląd, and workspace
filter-chip sections all cite it as if directly callable. Not
necessarily a defect (application code elsewhere may call
`site_memory.*` directly — `memory_read.py` itself does, for its
wrapped siblings) but worth flagging: no existing wrapper to point an
implementer at, unlike its neighbors. FLAGGED, not fixed — an
implementation-detail question for whoever builds this, not a UI
decision.

### V-C2. `get_site_print_settings`/`save_site_print_settings` have no application-layer wrapper either
Both live in `rota/persistence/site_repository.py` (confirmed
`save_site_print_settings` exists via grep — the read/write PAIR is
real at the persistence layer). `schedule_export.py` calls
`get_site_print_settings` directly (persistence import in an
application module, same pattern as V-C1). No `durable_inputs.py`
function wraps the SAVE side — Panel sterowania → Obiekt's editable
print-settings fields have no confirmed application-layer save path.
Same category as V-C1. FLAGGED, not fixed.

### V-C3. Decyzje koordynatora's "option → screen" mapping is plain-text string matching, not an ID-based link — now stated explicitly
`unblocking_options` are bare Polish strings
(`decision_guidance.build_unblocking_options`), no structured
action/screen id. spec.md's mapping table was implicitly aware of this
(it matches on string prefixes) but never said so outright — a future
implementer could easily assume there's a real enum/id underneath.
FIXED — added an explicit caveat.

### V-C4. "Odmroź..." unblocking option implies unfreeze AND replan, spec.md only mapped it to unfreeze
`_UNFREEZE_OPTION = "Odmroź zapisane przypisania i uruchom planowanie
ponownie"` — the text itself says "and run planning again." spec.md's
mapping sent this option only to "Ręczna korekta unfreeze," dropping
the implied second step (Planowanie miesiąca → replan). FIXED.

### V-C5. "Skonfiguruj Wsparcie zewnętrzne" — a real unblocking-option template, missing from the Decyzje koordynatora screen mapping
Confirmed in `decision_guidance.py`: `f"Skonfiguruj Wsparcie
zewnętrzne: {', '.join(external_names)}"` — a real, distinct
unblocking-option family (fires on `EXTERNAL-01`/
`EXTERNAL_SUPPORT_DISABLED` blockers), documented elsewhere in spec.md
(§9.2 Wsparcie zewnętrzne placement) but never added to the Decyzje
koordynatora screen's own option→screen mapping list. FIXED — mapped
to Obsada → per-employee support-window list.

## Not independently re-verified this round
Cursor's exact PR/diff framing ("PR #6") not inspected — findings
above were checked against current source directly, not against
whatever Cursor's local diff view showed. If a PR exists, it was not
read.
