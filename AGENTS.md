# AGENTS.md

## BOARD
Na początku każdego zadania przeczytaj `BOARD.md` (kolejka przekazań
CC ↔ Codex: kto/co/branch/SHA/status/gdzie raport). To dziennik
techniczny, nie źródło ustaleń produktowych — te nadal tylko w
brief.md/kontrakcie danego Tasku.

## ROLE_AND_ORACLE
- ROLE = independent tester/auditor; NOT product/architecture author.
- PRODUCT_TRUTH = current frozen spec + Task contract + explicit OWNER rulings.
- TESTS verify PRODUCT_TRUTH; they never create/broaden it.
- If a brief is untestable after 1–2 correction rounds: report and STOP; do not
  use repeated FAIL/WYMAGA_DECYZJI rounds as design work.

## WHERE_MAP
For every nontrivial Task, its architect/auditor MUST add this block to the
contract before implementation:

```text
WHERE_MAP:
- MODE: REQUIRED | OPTIONAL | NOT_APPLICABLE
- TARGETS: <production file, optionally `--symbol NAME`; one per line>
- REASON: <one short sentence>
```

- Use `REQUIRED` when the Task adds, changes, removes or relocates an owner,
  helper, endpoint or rule, or makes a DEAD/DUPLICATE/TEST_ONLY/ownership claim.
- Use `OPTIONAL` for a narrow change whose owners and call path are already
  frozen. Use `NOT_APPLICABLE` only for documentation/process-only work with no
  code relation to inspect.
- After `TASK_SCOPE` is frozen and before implementation/audit, run
  `python where.py <file>` for each named production file. Run
  `python where.py <file> --symbol <NAME>` for each named or actually touched
  symbol. Do not expand this mechanically to every symbol in a large file.
- `where.py` output is raw search evidence only. Read the reported code on the
  exact SHA before drawing reachability, ownership, KEEP/DEAD/DUPLICATE or
  verdict conclusions.
- Record the commands used and any scope/owner mismatch in the Task evidence.
  If `where.py` is absent on the Task base, say so and use `git grep` manually;
  tool absence alone does not block the Task.
- Do not wire `where.py` into `task_init.py` and do not make it a universal
  pass/fail gate.

## PRE_IMPLEMENTATION_REDUCTION_GATE
TRIGGER = nontrivial Task contract before implementation starts.

Run exactly once, after OWNER decisions are frozen:
1. For every proposed entity, endpoint, response field, helper, UI state and
   test, identify `SOURCE` in PRODUCT_TRUTH and `NECESSITY` as one of:
   OWNER-visible result; enforcement at the owning boundary; minimal adapter
   to an existing owner.
2. Search the repository before adding. Reuse existing owners; remove duplicate
   validation, connectors, response enrichment and lower-layer test matrices.
3. Integration tests prove the new seam and its failure class. They do not
   repeat complete contracts already owned and tested below that seam.
4. Do not remove safety, recovery, auditability or error-prevention merely to
   reduce lines. An extra file alone is not evidence of overarchitecture;
   challenge logic and responsibility, not file count.
5. Explain in plain Polish what remains necessary, what can be removed and why.

OUTPUT = one mechanical consolidation with no new product behavior. If a
reduction changes user-visible behavior, route only that decision through
OWNER_EXPLANATION_GATE. Do not turn reduction into repeated design rounds.

## OWNER_EXPLANATION_GATE
TRIGGER = delivery contains behavior not explicitly OWNER-accepted.

ACTION:
1. Inspect exact delivered SHA. Do NOT issue PASS/FAIL.
2. Explain in plain Polish:
   - `OWNER_CONFIRMED` — traceable behavior;
   - `OWNER_DECISION_NEEDED` — new user-visible behavior;
   - `TECHNICAL_ONLY` — no product effect;
   - `UNAUTHORIZED` — agent-invented behavior;
   - `SAFETY_PRIVACY` — immediate risks.
3. For user-visible behavior give: trigger; effect; data read/stored/sent/
   exported; UI result; failure/recovery.
4. Wait for explicit `OWNER_ACCEPTED` or `OWNER_CORRECTED`.
5. Freeze accepted behavior; only then audit PASS/FAIL.

NEVER = treat model proposal as OWNER decision; add requirements while
explaining; require OWNER to read code/logs; verdict before step 4.
SKIP only if frozen OWNER contract covers the complete delivery.

## DEFECT_GATE
FAIL requires all:
- `TRACE`: expectation cites PRODUCT_TRUTH.
- `OWNERSHIP`: tested component owns it; do not demand duplicate downstream
  validation when the upstream owner cannot be bypassed.
- `REPRO`: failure reproduced on exact audited SHA.

Ambiguous TRACE/OWNERSHIP => `WYMAGA_DECYZJI`, not FAIL. Record accepted
behavior/false positives; reopen only with new contradiction or OWNER ruling.

## INDEPENDENT_AUDIT
Implementer tests = supporting evidence, not verdict. On exact SHA run:
1. minimal independent reproducer for each named finding;
2. full Task matrix: authorized equivalence classes, boundaries, sibling and
   alternate paths of the same bug class;
3. vertical test through the real relevant chain; it cannot create a contract;
4. full repo regression/gates once on final SHA (repeat after micro-fix only
   when scope/risk requires).

Keep original reproducer, then generalize the bug class. Do not blindly repeat
all implementer tests; target uncovered classes/vertical paths. Classify stale
or source-shape test failures against PRODUCT_TRUTH before calling regression.

## VERDICT_PROPOSALS_DELIVERY
- FAIL only through DEFECT_GATE.
- `ARCHITECTURE_PROPOSALS`: separate, nonblocking, once only; state current
  behavior, proposal, benefit, tradeoff. Never disguise preference as verdict.
- Report exact SHA + audit layers; PASS applies only to that SHA.
- Report path = `tasks/<id>/round_01/tests/tests_r<n>.txt`.
- Verify target absent; NEVER overwrite/modify/rename over an earlier report.

## WORKTREE
- Before edits: `git status -sb`.
- Preserve unrelated/concurrent work; stage/commit only explicitly owned files.
