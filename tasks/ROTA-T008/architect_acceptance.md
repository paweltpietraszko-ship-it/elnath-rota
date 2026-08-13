# ROTA-T008 — FINAL ARCHITECTURAL ACCEPTANCE

DATE: 2026-08-13
STATUS: PASS — ARCHITECTURALLY CLOSED / READY FOR OWNER MERGE
ARCHITECT: ChatGPT
TASK: ROTA-T008 — LocalStore + ScheduleVersion lifecycle

## ACCEPTED SHA

Final architectural acceptance is bound exactly to the delivered implementation/test SHA:

`5dee28d1a692b3fde94c0f1e0add8b27c32c9b3d`

The later branch-head commit:

`e348ed05b5f42343b90b48c942a083db4a11b528`

adds only the Codex round-5 PASS audit report and does not alter implementation or tests. It is audit provenance, not the implementation SHA to which this acceptance is bound.

The last production-code-changing commit in the accepted delivered SHA is:

`248ad8d5ecc7f5de1b83cf42c4cc8d10e1cdaeb4`

`5dee28d...` additionally contains the mandatory durable R4 evidence matrix required to close the final test-evidence finding, without changing production code.

## AUTHORITATIVE CONTRACT SET

Acceptance is against the effective contract set:

- `tasks/ROTA-T008/brief.md` — original contract at `49ab1276ae0ee2eeff375a86224a87b57fd3c6a6`;
- `tasks/ROTA-T008/review_01_architect_clarification.md` — authoritative five-topic clarification at `5506b7874cc0948b74086b995b3d75455f7b8bee`;
- frozen `arch/spec.md` and accepted T004–T007 behavior insofar as T008 must preserve it.

The clarification has precedence for manual PRIMARY persistence, parent REALIZED preservation, adjacent boundary queries, holiday-history filtering and WORKING/Deviation status coherence.

## ARCHITECTURAL FINDINGS

PASS.

Independent architectural review found no remaining mismatch with the effective T008 contract.

Accepted properties include:

1. **One durable LocalStore / one SQLite database.** T008 extends the existing T004/T005 persistence foundation rather than introducing a parallel store.
2. **Ordered schema migration.** `PRAGMA user_version` is now authoritative; migration steps are ordered, transactional, idempotent at latest version, preserve accepted legacy data, and fail closed for a database newer than the binary understands.
3. **Operational master data persistence.** Site, Coordinator, CoordinatorSiteAssociation, Employee, SiteMembership, ExternalSupportWindow and persisted CalendarDay are durable without inventing hidden history for current-state entities.
4. **Availability history is real append-only history.** One logical `availability_id` has a linear immutable version chain; current state is derived from its chain end.
5. **WorkBalance has no duplicate hours truth.** Only target_hours is persisted as authoritative input. Planned/realized/month/quarter values are reconstructed from current ScheduleVersions across Sites plus accepted AvailabilityRecord state through `rota.balance`.
6. **ScheduleVersion is a reconstructable snapshot aggregate.** Header, ordered applied rule provenance, ShiftDemands, Assignments and Deviations round-trip as one versioned state.
7. **Current reference is separate from history.** Exactly one `(site_id, month)` current pointer is maintained by supported LocalStore operations; restore/select moves the pointer without deleting or mutating version history.
8. **FINAL is physically immutable.** Storage-level guards protect header and all child/applied-rule content from INSERT/UPDATE/DELETE mutation, including UPDATE attempts that move a row from a WORKING version into FINAL.
9. **Cross-boundary references are structurally coherent.** Current version pointer cannot target a different Site/month; PRIMARY demand and TRAINEE mentor references cannot cross ScheduleVersion boundaries.
10. **Truthful manual WORKING state is persistable.** Persistence does not require PRIMARY interval equality with a ShiftDemand and therefore does not steal COVERAGE-01 responsibility from later validation/application logic.
11. **Parent REALIZED work is preserved.** Child creation fails atomically if any already-REALIZED parent Assignment is omitted or materially changed; a parent PLANNED Assignment may legitimately become REALIZED in the child.
12. **Adjacent context is interval-based.** Current-version queries can retrieve predecessor/following work needed by REST-01 and rolling LOAD-01 even when that work does not overlap the target month itself.
13. **Holiday history is current + REALIZED + PRIMARY only.** PLANNED, CANCELLED, TRAINEE, non-current and non-holiday rows are excluded.
14. **WORKING status is coherent with Deviations.** Zero Deviations derives WORKING; one-or-more derives WORKING_WITH_DEVIATIONS. FINAL mapping remains zero -> FINAL_NO_DEVIATIONS and one-or-more acknowledged -> FINAL_WITH_DEVIATIONS.
15. **Crash consistency is preserved.** New-version creation and working-snapshot replacement are transactionally all-or-nothing; current reference cannot expose a half-written snapshot after reopen.
16. **Planning isolation is preserved.** T008 changes persistence/tests only; `rota/planning/` behavior and T006/T007 solver semantics are not modified.

## CODEX AUDIT PROVENANCE

Codex round 3 found four executable-code defect classes plus one missing-evidence class. Those were corrected in `248ad8d...`.

Round 4 independently confirmed the code fixes but found the committed R1-2/R1-4 evidence matrix incomplete. `5dee28d...` added the required durable matrix without production-code changes.

Round 5 audited exact SHA `5dee28d1a692b3fde94c0f1e0add8b27c32c9b3d` and returned:

- PASS — READY TO MERGE;
- R4 matrix: 11/11 PASS;
- full suite: 299/299 PASS;
- Ruff: PASS;
- `git diff --check`: PASS;
- all findings R3-1..R3-5 and R4-1 closed;
- no architecture proposals.

## BENCHMARK NOTE

Historical reports in the T008 audit trail mention `benchmarks/rota_stress.py` as `100/100 PASS`. That synthetic-feasible benchmark is **not** used as evidence for this architectural acceptance. Its previously identified design does not measure the real five-person object and therefore must not be interpreted as a product-success rate.

This does not block T008: T008 does not change PlanningEngine. Its acceptance is supported by the LocalStore-specific contract matrix, direct-SQL invariants, migration/restart tests, crash-consistency tests, full regression suite and absence of planning-code changes.

The separately authored ROTA-REAL-OBJECT-01 benchmark remains independent test infrastructure and may audit PlanningEngine on its own lineage.

## MERGE DECISION

Architectural verdict: **PASS**.

ROTA-T008 is architecturally CLOSED and READY FOR OWNER MERGE.

The owner may merge branch `task/ROTA-T008` including later report-only audit provenance `e348ed0...`; this acceptance remains bound to delivered implementation/test SHA `5dee28d...`.

The next roadmap task after owner merge is ROTA-T009 — Application Layer. T009 must consume the LocalStore APIs established here rather than issuing raw SQL or moving persistence responsibility into PlanningEngine/UI.
