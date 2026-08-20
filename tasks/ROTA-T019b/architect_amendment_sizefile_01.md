# ROTA-T019b — ARCHITECT AMENDMENT: dedicated test SIZE_FILE boundary

STATUS: FROZEN ARCHITECT AMENDMENT — READY FOR FINAL IMPLEMENTATION AUDIT
DATE: 2026-08-20
BASE_SHA: 102273b553783b5a083a60d5ee9964e9ec67221a
CONTRACT_SHA: c9101abae8b35ca1a72d7b8cd3975fa54d8c39cc
PRODUCT_SHA: 67c6536df21d03c81656cbe472e255f2aa3b770e
PARENT_CONTRACT: tasks/ROTA-T019b/brief.md
AMENDS: Section 25 `MINIMUM T019b TEST MATRIX`

This is a narrow mechanical amendment only. It changes no product behavior, storage architecture, application semantics, TASK_SCOPE, required oracle, or production code.

## A. Section 25 dedicated-test limit

The Section 25 sentence:

`Dedicated tests/test_t019b.py must remain <=600 lines using fixtures/parameterization where sensible and prove at minimum:`

is normatively amended for T019b to:

`Dedicated tests/test_t019b.py must remain <=900 lines using fixtures/parameterization where sensible and prove at minimum:`

All 78 minimum Section 25 oracles remain mandatory and unchanged.

## B. No coverage reduction to satisfy SIZE_FILE

It is forbidden to remove, weaken, skip, xfail, merge away semantically distinct required evidence, or otherwise reduce any required T019b oracle solely to satisfy a line-count metric.

Existing use of fixtures, parameterization and combined scenarios may be retained where it preserves the complete required evidence.

## C. No metric-splitting workaround

It is forbidden to create a second dedicated T019b test file, move T019b-specific oracle coverage into another test file, or otherwise split the dedicated matrix solely to evade the per-file SIZE_FILE threshold.

`tests/test_t019b.py` remains the single dedicated T019b implementation matrix.

## D. Exact PRODUCT_SHA acceptance

For exact product-code SHA:

`67c6536df21d03c81656cbe472e255f2aa3b770e`

`tests/test_t019b.py = 873 lines` is architecturally ACCEPTED under the amended `<=900` Section 25 boundary.

This acceptance is exact-SHA-only for that product code. It does not raise the repository-global backend.py SIZE_FILE threshold, does not create a general precedent, and does not authorize later growth above 900 lines.

No CC code or test change is requested or authorized by this amendment.

## E. Final audit instruction

The next Codex implementation audit must treat this amendment as the authoritative Section 25 size boundary and audit the unchanged product-code SHA `67c6536df21d03c81656cbe472e255f2aa3b770e`.

The audit must not request further compression of `tests/test_t019b.py` merely to satisfy the repository-global 600-line backend threshold. Any substantive missing oracle, vacuous test, semantic defect, scope violation, or new backend finding remains independently reviewable.

Until that final implementation audit passes, T019b is NOT READY FOR MERGE.
