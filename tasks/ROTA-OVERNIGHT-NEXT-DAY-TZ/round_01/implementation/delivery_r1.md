# DELIVERY r1 — ROTA-OVERNIGHT-NEXT-DAY-TZ
EXACT SHA: 4717c4e. BASE: repo_before.hash (main@a6b86af).
Change: frontend/src/screens/MonthlyPlanning.tsx — new `nextDayIso` (R11-01 arithmetic verbatim), used by S1 (`s1EndNextDay`), Dodaj pracę (`middleEndNextDay`), `applyExtraCode` (its inline copy replaced). No other file.
Repro of bug: nextday_check_local_tz_warsaw.txt — local TZ Europe/Warsaw: old 2026-10-16 -> 2026-10-16 (same day), new -> 2026-10-17; edge dates (month/year end, both DST days, 2028-02-28/29) correct; UTC old==new.
Build: `npm run build` green. No frontend unit-test harness exists; no e2e added (CC). `git merge-tree` with task/ROTA-LARGE-FILES-REFACTOR-MONTHLY-GRID: clean.
backend.py (verbatim): STATUS: PASS / HEAD_SHA: 4717c4ee52166e5e80d0bdeb6a5c0b10b0ad26c9 (full in backend_r1.txt; TSX not covered by ruff/SIZE checks).
## For Codex
Audit exact SHA 4717c4e in your own worktree; real UI in a Europe/Warsaw browser: S1 and Dodaj pracę with "następnego dnia" save end on the next day; applyExtraCode unchanged behaviour. Report tests_r1.txt on branch audit/rota-overnight-next-day-tz; update only your BOARD row; no commits to the task branch; no merge.
