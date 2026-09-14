# ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT

STATUS: OWNER REQUIREMENTS FROZEN — READY FOR CODEX PREIMPLEMENTATION REVIEW
IMPLEMENTATION: pending preimplementation review; this delivery contains contract and acceptance tests.
BASE_SHA: bad290f3b6953673266c80206765b45d5f0a2e74

## Source and purpose

PRODUCT_TRUTH: explicit OWNER request of 2026-09-14 in this task: preserve
backend.py as the existing lightweight gate; fail closed for missing or
malformed TASK_SCOPE; include .ts and .tsx in size/file checks alongside .py;
require canonical brief format with a literal TASK_SCOPE: line and dash entries.
The referenced conversation and BOARD history are context, not additional authority.

Exactly these three requirements are frozen:

1. SCOPE-FAIL-CLOSED: absent or malformed TASK_SCOPE produces STATUS: FAIL,
   a TASK_SCOPE reason and nonzero exit. Never treat it as a valid empty list
   or run DIFF_SCOPE against that invalid/empty scope. This includes an empty
   block and an empty entry. Preserve existing repository-relative path validation.
2. SOURCE-FILE-SIZE: existing SIZE_FILE limit (600 lines) applies equally to
   existing .py, .ts and .tsx files in TASK_SCOPE. 600 passes; 601 fails with
   the file, actual line count and limit in the reason. Added and modified
   files use the same check; deleted files retain existing handling.
3. CANONICAL-SCOPE: brief authors supply a literal standalone TASK_SCOPE:
   line and one bare repository-relative path per dash-prefixed entry,
   e.g. `- backend.py`. Narrative Markdown headings do not substitute for
   the literal line. Inline lists, star/numbered/bare entries, backtick-wrapped
   paths and header decorations must not silently produce a usable scope.
   A valid initial entry must not hide a later malformed entry in that block.
   Use a separate Markdown heading after the list when more brief text follows.

## Observable result and recovery

Trigger: running the existing backend.py CLI with a brief and the two SHAs.
It reads the brief, repository diff and scoped source files, and writes the
existing gate report. It sends no data externally and introduces no product UI.
A malformed brief is rejected with a scope reason; correct the brief to the
canonical format and rerun. An oversized scoped source file is reported by name
with the exceeded limit. Resolving existing oversized files is a separate task.

## Scope limits

No broker, orchestrator, permission system, merge control, new gate lifecycle,
product behavior, bulk brief migration or refactoring of existing large files.
Keep the present thresholds, CLI, report format, artifact exclusions and other
checks. Python SIZE_FUNC (50 lines) and Ruff remain as they are. This task adds
no TypeScript function parser or frontend lint infrastructure: the latest OWNER
request freezes size/file checks; the older BOARD wording is not authority to
expand that into a new TypeScript function-analysis contract.

TASK_SCOPE:
- backend.py
- tests/test_backend_task_scope_format_drift.py
- tasks/ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT/brief.md
- BOARD.md

## Preimplementation reduction (one pass)

Existing owners were inspected before proposing additions:
- read_task_scope/check_scope_paths: SOURCE SCOPE-FAIL-CLOSED and CANONICAL-SCOPE;
  NECESSITY enforcement at the existing input boundary.
- run_backend: SOURCE SCOPE-FAIL-CLOSED; NECESSITY stop dependent scope checks
  after rejected input, using the existing report/exit mechanism.
- check_sizes: SOURCE SOURCE-FILE-SIZE; NECESSITY extend the existing suffix
  selection, retain Python function analysis only for Python.
- One test module: SOURCE the three requirements above; NECESSITY direct
  acceptance coverage plus the actual CLI/Git/report chain. No application,
  database, solver, UI or duplicate lower-layer test matrix is needed.

No new production helper, dependency, endpoint, field or subsystem is proposed.
where.py is unnecessary here: no owner is added or relocated; direct inspection
of the small gate's parser, size check and run_backend chain covers the seam.

## Acceptance evidence and handoff

tests/test_backend_task_scope_format_drift.py covers canonical scopes, rejected
format classes, a valid prefix followed by a malformed entry, missing/unreadable
briefs, unchanged path validation, file-size boundaries for all three suffixes,
retained Python function limits, and the real CLI with a temporary Git repository.
The CLI test checks the report and exit code, including absence of a misleading
DIFF_SCOPE diagnosis for invalid scope. Fixtures are local source files, not
synthetic application data.

Tests are intentionally ordinary failing acceptance tests until implementation;
do not hide present gaps behind xfail/skip. Their baseline results are evidence
for preimplementation review, not an independent final verdict on a fix.
Run only this module for this contract/test delivery. Production code is unchanged.
After review, implement the narrow gate fix and rerun these tests and the relevant
existing gate checks. Final independent audit applies to the delivered exact SHA.
BOARD.md is the handoff ledger; this brief remains the frozen task contract.
