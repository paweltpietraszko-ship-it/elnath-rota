# ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT

STATUS: OWNER REQUIREMENTS FROZEN — READY FOR CODEX PREIMPLEMENTATION RE-CHECK
IMPLEMENTATION: pending preimplementation PASS; this delivery contains contract and acceptance tests only.
BASE_SHA: bad290f3b6953673266c80206765b45d5f0a2e74

## Source and purpose

PRODUCT_TRUTH: explicit OWNER request of 2026-09-14 in this task: preserve
backend.py as the existing lightweight gate; fail closed for missing or
malformed TASK_SCOPE; include .ts and .tsx in size/file checks alongside .py;
require canonical brief format with a literal TASK_SCOPE: line and dash entries.
The referenced conversation and BOARD history are context, not additional authority.

Exactly these three requirements are frozen:

1. SCOPE-FAIL-CLOSED: absent, unreadable or malformed TASK_SCOPE produces
   STATUS: FAIL, a TASK_SCOPE reason and nonzero exit. Never treat it as a
   valid empty list or run DIFF_SCOPE against that invalid/empty scope. This
   includes a missing brief, a brief that cannot be decoded as UTF-8, an empty
   block and an empty entry. The CLI failure must be controlled: no traceback.
   Preserve existing repository-relative path validation.
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
   A canonical scope list ends when a separate Markdown heading begins; ordinary
   brief text may follow that heading and must not be parsed as scope content.

## Observable result and recovery

Trigger: running the existing backend.py CLI with a brief and the two SHAs.
It reads the brief, repository diff and scoped source files, and writes the
existing gate report. It sends no data externally and introduces no product UI.
A missing, unreadable or malformed brief is rejected with a TASK_SCOPE reason;
correct the brief to canonical UTF-8 text and rerun. An oversized scoped source
file is reported by name with the exceeded limit. Resolving existing oversized
files is a separate task.

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
- run_backend: SOURCE SCOPE-FAIL-CLOSED; NECESSITY convert missing/unreadable/
  malformed scope into the existing controlled report/exit mechanism and stop
  dependent scope checks after rejected input.
- check_sizes: SOURCE SOURCE-FILE-SIZE; NECESSITY extend the existing suffix
  selection, retain Python function analysis only for Python.
- One test module: SOURCE the three requirements above; NECESSITY direct
  acceptance coverage plus representative actual CLI/Git/report seams. No
  application, database, solver, UI or duplicate lower-layer test matrix is needed.

No new production helper, dependency, endpoint, field or subsystem is proposed.
where.py is unnecessary here: no owner is added or relocated; direct inspection
of the small gate's parser, size check and run_backend chain covers the seam.

## Acceptance evidence and handoff

tests/test_backend_task_scope_format_drift.py covers canonical scopes, rejected
format classes, a valid prefix followed by a malformed entry, missing brief,
invalid UTF-8/unreadable brief, unchanged path validation, file-size boundaries
for all three suffixes, retained Python function limits, and representative real
CLI/Git/report paths. It also freezes the positive boundary that a canonical
scope may end before a separate Markdown heading followed by normal narrative.
The CLI invalid-scope checks require STATUS: FAIL, TASK_SCOPE reason, nonzero
exit, no traceback and no misleading DIFF_SCOPE diagnosis. Fixtures are local
source files, not synthetic application data.

Direct parser tests remain the owner of the complete format-class matrix and
599/600/601 size boundaries. CLI tests are intentionally representative rather
than the full Cartesian product: malformed scope with empty/nonempty diff,
invalid UTF-8, added .ts, modified .tsx and the 600-line pass boundary are
sufficient to prove the wiring without duplicating lower-layer coverage.

Tests are intentionally ordinary failing acceptance tests until implementation;
do not hide present gaps behind xfail/skip. Their baseline results are evidence
for preimplementation review, not an independent final verdict on a fix.
Production code remains unchanged until Codex preimplementation PASS. After PASS,
implement only the narrow gate fix and rerun these tests and relevant existing
gate checks. Final independent audit applies to the delivered exact SHA.
BOARD.md is the handoff ledger; this brief remains the frozen task contract.
