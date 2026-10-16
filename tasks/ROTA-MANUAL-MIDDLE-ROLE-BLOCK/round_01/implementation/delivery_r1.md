# DELIVERY r1 — ROTA-MANUAL-MIDDLE-ROLE-BLOCK

BASE (repo_before.hash): e13f92d (brief f01a9b2 + origin/main). EXACT SHA under audit: 5cf3df5.
CC merit review of brief: accepted without changes (matches OWNER 2026-10-16 decisions incl. membership ruling e38a966).

CHANGE (brief §3, literal):
1. rota/planning/eligibility.py — role_covers_interval(role_id, start, end, membership, authorizations) extracted; role_covers keeps None→True and delegates. One authorization must cover the whole interval; no summing.
2. rota/planning/validator_checks_availability.py — _check_role: Assignment with manual_work_role_id and no covers_demand_id → new _check_manual_work_role (split out for SIZE_FUNC) → ROLE-01 on that assignment_id when not covered; membership None → no ROLE-01 (MEMBERSHIP-01 owner). Demand path and _covered_demands unchanged.
3. rota/application/manual_middle_work.py — removed only the missing-authorization reject and _authorizes_manual_work_role (sole consumer, WHERE_MAP confirms 0 remaining hits). ORDINARY / unknown-inactive-foreign role / no enabled membership rejects kept. Docstrings updated.
Mapping ROLE-01→PREFERENCE and label from ROTA-UNMAPPED-DEVIATION-RULES untouched.

BASE REPRO (base_repro_mm05.txt): on base old MM-05 + partial-auth tests pass (reject). New tests run against base production files: 6 failed (MM-05 x2, not-covering x3, not-summed). On exact SHA: pass.

TESTS (tests/test_t065_manual_middle_shift.py, 21 passed):
- MM-05: real add_manual_middle_work without authorization → child current, 1 ROLE-01/PREFERENCE on the work's assignment_id, CoordinatorAction +1, parent unchanged, position unchanged, no authorization created; router GET month → label "brak wymaganej roli".
- MM-06: covering authorization → no ROLE-01, position unchanged; own position role → no ROLE-01.
- Not covering: ends too early / starts too late / inactive → saved + ROLE-01; two partial authorizations not summed.
- Boundary: own-role work inside another-role demand → no ROLE-01, COVERAGE-01 of the demand still reported.
- Integrity: no membership / disabled membership / inactive role / foreign role → ManualMiddleShiftRejected, current stays SV-BASE, CoordinatorAction count unchanged.
Scoped neighbours: test_t065_configurable_roles, test_t065_ordinary_roles, test_role_deviation_mapping, test_t009_manual_edit, test_cloud_review_schedule_fixes, test_audit_r13_findings, test_t065_ordinary_time_availability, test_delegation_absence → 131 passed total. No full regression.

WHERE_MAP: where_map_before.txt / where_map_after.txt (incl. --symbol role_covers_interval, _authorizes_manual_work_role).

backend.py (verbatim stdout head, full in backend_r1.txt):
STATUS: FAIL
HEAD_SHA: 5cf3df554dadcf8feaf0d156f09f8fcfee40c6aa
REASON:
  - SIZE_FUNC: rota/planning/eligibility.py:_common_hard_gate has 68 lines (max 50)
  - SIZE_FUNC: rota/planning/validator_checks_availability.py:_check_day_only has 52 lines (max 50)
WYMAGA_DECYZJI:
  - TOTAL_LINES: 260 lines changed (threshold 150)
CC note: both SIZE_FUNC functions are untouched and had the same length on base (68 / 52, measured with ast); the gate scans whole modified files. TOTAL_LINES: production +51/-38, the rest are tests. Gate exceptions → OWNER decision.

## For Codex — how to work without disturbing CC
- Audit exact SHA 5cf3df5 in your own worktree (git worktree add .worktrees/codex-middle-role origin/task/ROTA-MANUAL-MIDDLE-ROLE-BLOCK); never switch the main folder's branch.
- Report round_01/tests/tests_r2.txt on audit/rota-manual-middle-role-block (r1 = precheck, kept); push it, update only your own BOARD row on main. CC carries the report. No commits to the task branch, no merge.
