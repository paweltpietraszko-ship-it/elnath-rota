# DELIVERY r1 — ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID

Implementer: CC (cloud session). No self-PASS: audit belongs to Codex + backend.py; merge/deploy OWNER only.
Resume note: BOARD on main lists this Task `ON_HOLD` ("wznowienie wyłącznie na polecenie OWNERA");
this round was started on an explicit implementer instruction received in the session, treated as that resume.

## SHAs
- BASE_SHA (brief): `923bd54917a0f9e8512d759611796e9c159fa70a`
- repo_before (`repo_before.hash`): `cc7005cc192e7f7c383e20ae441d10cd4d9123ad` = origin/codex/rota-large-files-refactor-plan
  + merge origin/main (BOARD.md conflict -> origin/main version) + carried `tasks/ROTA-LARGE-FILES-REFACTOR/round_01/tests/tests_r1.txt`.
  `git diff 923bd54 cc7005c -- frontend/src/screens/MonthlyPlanning.tsx` is empty -> moved symbols unchanged vs BASE_SHA.
- CODE SHA (audit target, all evidence + gate + suite on it): `a1572100a3de7f2a779cd05b38312452de55cf6b`.
  The delivery commit after it touches only `tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/round_01/` (this file + suite logs).

## Result: MOVED (no STOP condition hit)
No import cycle (new module imports only `react` and `../../api/client`); no parent state/effect/action/props/JSX touched; bodies unchanged; every UI usage reproduced.

## What moved (manifest.txt, manifest.py; moved_lines_check.txt; parent_diff.txt)
| symbol | old (MonthlyPlanning.tsx @cc7005c) | new (monthly-planning/ScheduleGrid.tsx) | export | body |
|---|---|---|---|---|
| daysInMonth | L27-31 | L4-8 | yes | IDENTICAL |
| hourOf | L38-40 | L10-12 | no | IDENTICAL |
| cellLabel (+ its T065 comment) | L42-60 | L14-32 | no | IDENTICAL |
| assignmentHours | L62-66 | L34-38 | no | IDENTICAL |
| totalHours (+ T031 comment) | L68-75 | L40-47 | no | IDENTICAL |
| ScheduleGrid (props + 6 useMemo) | L77-196 | L49-168 | yes | IDENTICAL |
Only change in moved text: `export ` on ScheduleGrid and daysInMonth. Relative order preserved.
Parent diff: -167/+2 = the removed blocks + import line rewritten without `DelegationDayOut`, `ScheduleEmployeeOut`
(no other use left in parent; `useMemo`, `AssignmentOut`, `ShiftDemandOut` still used, kept) + `import { daysInMonth, ScheduleGrid } from "./monthly-planning/ScheduleGrid";`.
`formatDateTime`, `stripDisplayName`, `firstOfMonthIso`, statuses, EntryMode, whole main component untouched; 3 JSX call sites byte-identical.
Size: MonthlyPlanning.tsx 1688 -> 1523 lines (still >600, owner-accepted per parent plan §5); new module 168 lines.

## Build
`npm run build` (`tsc -b && vite build`) green before and after (build_base.txt / build_after.txt); no deps/bundler change; bundle 367.33 kB both.

## WHERE_MAP (where_map_before.txt, where_map_after.txt)
where.py has no TSX parser (prints NOTE; raw text hits only) -> supplemented by targeted `grep -rnw` over frontend/src for all six symbols.
Before: all six declared/used only in MonthlyPlanning.tsx; only importer of MonthlyPlanning is Room.tsx (default export, untouched).
After (run on a157210): six declarations only in the new module; parent references only ScheduleGrid (3 JSX sites + import) and daysInMonth (L48 + import).

## Environment (Linux cloud container) — evidence-only shims, nothing product-side changed
1. LOCAL_WINDOWS `pii_crypto` needs Windows DPAPI; on Linux every employee write fails `KeyProtectionUnavailable`.
   `round_01/implementation/env_shim/sitecustomize.py` makes the DPAPI protect/unprotect a pass-through (test-only).
   `.venv/Scripts/python.exe` = copy of `env_shim/python.exe` (wrapper adding env_shim to PYTHONPATH) instead of the
   instructed plain symlink — the symlink alone cannot run the e2e backend here. `.venv` not committed; playwright.config.ts not edited.
2. Container has Chromium 1194 at /opt/pw-browsers; Playwright 1.62 wants a newer build -> evidence configs launch
   `/opt/pw-browsers/chromium`. Repo config cannot be imported from tasks/ (ESM vs CJS), so
   `capture/playwright.capture.config.ts` and `capture/playwright.e2e-linux.config.ts` mirror its webServer block verbatim.
On the owner's Windows machine none of this is needed.

## UI evidence — same data before/after (capture/, ui_compare_*.txt)
`capture/capture.spec.ts` seeds once (CAPTURE_PHASE=seed, real current month, test API only, fixture.json), then captures
each grid usage's full DOM (header, every cell text/style, buttons title/action/class/style) + element screenshot and logs
every non-GET /api request:
- A (OCHRONA, accepted): current grid with NN (past shift), S1 (last day), DEL (Ewa 27-28); click Bartek's first cell ->
  heading "Ręczna korekta — Bartek, <that day>"; history: both older versions' "Podgląd starej wersji" grids; switch to next
  month and back; entry via "Ręczna korekta" and "Wydruk Grafiku" nav.
- B (OCHRONA, accepted + Przelicz preview with fixed S1 + DEL): current + candidate grid, again after reload.
- C (ORDINARY, accepted + Przelicz preview): hour labels 8–16 / 12–20.
Results (ui_compare_all.txt):
- base vs base_repeat (original code twice): NO DIFFERENCES (harness deterministic).
- base_recheck (original code, re-run later) vs after_repeat (moved code): NO DIFFERENCES — 12/12 steps DOM-identical,
  14/14 screenshots BYTE-IDENTICAL, writes [] both.
- base vs after (ui_compare_base_vs_after.txt): DOM identical on all steps, writes [] both; 2 screenshots (B candidate grid)
  PIXEL-DIFFERENT: bottom 25 px strip only (scroll edge of the clipped grid), colour delta 1/255 (#1a2026 vs #1b2127).
  The SAME difference appears between base and base_recheck — i.e. on the unchanged original code, 8 minutes apart —
  so it is environmental drift, not the refactor. Root cause not identified (visible text identical).
- Click -> same correction (person/day) before/after; month switch, korekta/wydruk entries: identical grids, zero write requests.

## e2e (repo specs via capture/playwright.e2e-linux.config.ts, CI=1 = fresh e2e DB; e2e_base_ci.txt / e2e_after_ci.txt)
Identical outcome on original code and moved code: 8 passed, 1 failed.
- delegation-schedule-grid.spec.ts (2) PASS/PASS; cloud-review-fixes.spec.ts (1) PASS/PASS (covers month banner, not grid cells);
  t054 T54-03, A-F2 PASS/PASS (persisted preview flows);
- t054 T54-06 FAIL on base and after, identically: `plan-month-recompute` never rendered on a fresh site with no accepted
  version (test predates T057 preview-only first PLAN); its retries then fail on its own leftover SQLite trigger.
  Pre-existing, unrelated to the grid; not fixed (out of scope). Without CI=1 that leftover trigger also breaks T54-03/A-F2
  in later runs (persistent rota_e2e.db) — seen once, test pollution.
- NEW `frontend/e2e/refactor-schedule-grid.spec.ts` (3 tests, retries 0, timezone Europe/Warsaw): PASS on base and after.
  Expected cells/totals derived from the payload each usage renders (month view / plan_preview / version snapshot) by the
  frozen display contract; checks header, every cell, every row total, clickable vs read-only, NN/S1/DEL spots, click ->
  person/day heading, history read-only and showing the original plan on the NN day, ORDINARY hour labels, zero writes.
  Mutation check on base (S1 -> "S2", total +1h): all 3 tests fail; file restored byte-identical.
  Not runnable on the 1st or last day of a month (needs a started shift for NN and a future day for S1) — documented in the spec header.
Existing business expectations unchanged.

## Full backend suite on a1572100a3de7f2a779cd05b38312452de55cf6b
- RUN 1 `.venv/bin/python -m pytest tests -q -p no:cacheprovider` (plain): `472 failed, 1054 passed, 2 skipped, 1 warning, 2 errors in 192.97s`
  — INVALID ENVIRONMENT: every captured traceback (347/347) is `KeyProtectionUnavailable` (no DPAPI on Linux). full_suite_run1_no_dpapi.txt.
- RUN 2 (concrete reason: run 1 could not measure the code) same command with `PYTHONPATH=<env_shim>:<repo>`:
  **`1529 passed, 1 skipped, 1 warning in 196.96s`, exit 0.** full_suite_run2_with_dpapi_shim.txt.
  (CLAUDE.md's "34 stable failures" note is stale relative to this main; matches the instruction's "all green" baseline.)
  Frontend-only change; backend suite is supporting evidence only.

## backend.py (verbatim stdout/output file backend_r1.txt, head of it)
```
STATUS: WYMAGA_DECYZJI
HEAD_SHA: a1572100a3de7f2a779cd05b38312452de55cf6b
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES
WYMAGA_DECYZJI:
  - TOTAL_LINES: 640 lines changed (threshold 150)
EXCLUDED_ARTIFACTS:
  - tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/... (all round_01 evidence + repo_before.hash; full list in backend_r1.txt)
```
Command: `.venv/bin/python backend.py tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/brief.md cc7005cc192e7f7c383e20ae441d10cd4d9123ad a1572100a3de7f2a779cd05b38312452de55cf6b tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/round_01/implementation/backend_r1.txt`.
Not green. Only reason TOTAL_LINES 640 = move (167 deleted + 2 + 168 added) + new spec (303). No BLOCKER; DIFF_SCOPE/NEW_FILES (2) pass.
SIZE_FILE: backend.py measures `.py` files only, so MonthlyPlanning.tsx (1523 lines) is not reported; the owner-accepted
exception (parent plan §5) is what covers it — size 1688 -> 1523.

## Flagged, NOT fixed (separate topics, outside TASK_SCOPE)
1. BACKEND: after an NN on an already-started shift, Przelicz Plan returns TECHNICAL_ERROR
   ("COVERAGE-01: demand <day>-D has a coverage gap … cannot be attributed to a known autonomy boundary"). Reproduced via API
   while seeding (site with one past NN, `POST /schedule/<m>/plan {effective_from:null}`). Solver skips the NN demand
   (`_already_covered_counts` + `_historical_nn_facts`), validator still counts the gap, engine cannot attribute it.
   The coordinator cannot recompute a month after recording one "nie przepracował". This is why scenario B is a separate site.
2. FRONTEND (MonthlyPlanning.tsx, S1 form, not moved code): "S1 kończy się następnego dnia" computes the end date with
   `new Date(...+86400000).toISOString().slice(0,10)`; in a Europe/Warsaw browser that yields the SAME date
   (`TZ=Europe/Warsaw node`: 2026-10-16 -> 2026-10-16; UTC: -> 2026-10-17), so an overnight S1 is rejected as end<=start.
3. TEST: t054 T54-06 stale vs T057 + leaves a trigger in rota_e2e.db (above). CLAUDE.md test-count note stale.
4. DST (not changed, per brief): grid hour totals use browser-local Date arithmetic, so the 24/25 Oct night counts 13h — consistent
   base/after, noted only.

## For Codex
Audit exact SHA `a1572100a3de7f2a779cd05b38312452de55cf6b` in your own worktree (do not use this checkout). Report as
`tasks/ROTA-LARGE-FILES-REFACTOR/round_01/tests/tests_r2.txt` on branch `audit/rota-large-files-refactor-plan` (keep tests_r1),
update only your own BOARD row, no commits to `task/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID`, no merge.
Repro: `python tasks/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID/round_01/implementation/manifest.py cc7005cc192e7f7c383e20ae441d10cd4d9123ad`;
`cd frontend && npm run build`; e2e via repo `playwright.config.ts` on Windows (refactor-schedule-grid, delegation-schedule-grid,
cloud-review-fixes, t054); full suite is not to be repeated without reason (brief §3.5). Ultrareview by OWNER after your audit.
