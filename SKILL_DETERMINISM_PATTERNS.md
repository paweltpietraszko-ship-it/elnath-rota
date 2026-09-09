# Getting reliable behavior out of an LLM that reads instructions, not code

## The problem, stated plainly

A skill file, a CLAUDE.md, a system prompt — these are natural-language
instructions loaded into an LLM's context. The model treats them as
*guidance it weighs against everything else it's holding* (the
conversation so far, competing instructions, its own judgment about what
seems reasonable), not as code it executes. That means "the model
followed the skill this time and not last time" is not a bug to patch —
it's the expected behavior of a probabilistic system being asked to
comply with a document. Longer context, ambiguous phrasing, and
competing priorities all increase the odds of drift. No amount of
rephrasing the skill file makes this categorically go away.

This does not mean the situation is hopeless. It means the fix is not
"write a better skill.md" — it's **deciding which parts of your workflow
cannot tolerate probabilistic compliance, and moving exactly those parts
outside the model's discretion.** Below are the four patterns this
project actually runs on, in production, with a concrete case study at
the end showing them catching real bugs across five audit rounds on the
same feature.

## Pattern 1 — Hard constraints become mechanical gates, not prose

If a rule must hold every single time (line-count limits, forbidden file
patterns, "never touch this frozen contract"), don't put it in a skill
file and hope the model remembers. Write a script that checks it and
fails loudly. In this repo:

- `backend.py` parses the actual diff between two commits and mechanically
  computes SIZE_FUNC (max lines per function), SIZE_FILE, RUFF, the
  insertion/deletion RATIO, and TOTAL_LINES — then emits a verdict
  (PASS / FAIL / WYMAGA_DECYZJI) that the audit process is required to
  quote verbatim, never paraphrase. The model never gets to self-report
  "yes, my function is under 50 lines" — the AST does the counting.
- `guard.py freeze|check` maintains a lock file (`arch/FROZEN.lock`)
  naming contracts that must not change without an explicit unfreeze
  step — a structural tripwire, not a comment asking nicely.

The general move: for any rule where "the model forgot" would be a real
incident, ask "can a script check this instead of a sentence?" If yes,
write the script. Reserve the prose layer (skills, CLAUDE.md) for
judgment calls that genuinely need a model's reasoning — architecture
tradeoffs, wording quality, "does this test actually test what it claims
to."

## Pattern 2 — Adversarial review, never self-certification

A single model instance auditing its own work inherits all its own blind
spots. This project hard-separates three roles that are never allowed to
collapse into one:

- **Implementer** (this session) writes code against an accepted brief.
- **Mechanical auditor** (a separate Codex process) re-derives the bug
  from scratch — builds its own independent reproducer, traces
  ownership through the real code path, and only PASSes when its own
  test actually exercises the claim. It has no access to the
  implementer's reasoning, only the diff and the brief.
- **Merit reviewer / owner** (architect + human owner) evaluates whether
  the *design* is sound before implementation starts, and again if the
  mechanical auditor's PASS doesn't settle whether the actual product
  behavior is right — a mechanical gate proves "the code does what it
  says," not "what it says is correct."

Critically: the implementer is instructed to *never* self-review or
self-approve — PASS/FAIL authority belongs structurally to a different
party, and "the model decided its own PASS" simply isn't a legal state
in this workflow. This is the same principle as separation of duties in
finance or infra change-management, applied to AI-authored code.

## Pattern 3 — One shared, append-only handoff surface

When two AI processes (or an AI and a human) coordinate by relaying
messages through a third party, meaning drifts — a "telephone game." This
project keeps a single file, `BOARD.md`, that both the implementer and
the mechanical auditor read and write directly: exact commit SHAs, exact
statuses (only four allowed: READY_FOR_CODEX / CODEX_IN_PROGRESS /
CODEX_REPORTED / OWNER_DECISION_NEEDED), and dense technical findings —
no paraphrasing through a human intermediary. Anyone can `git log -p
BOARD.md` and see the exact decision trail, including corrections
("OWNER_CORRECTED", "ARCHITECT_RULING") stamped with the date they
landed.

The transferable idea: pick one artifact as the single source of truth
for cross-agent handoff, make both sides read and write it directly
instead of relaying through a person, and make it append/amend-in-place
rather than ephemeral chat — so the trail survives context resets and
session boundaries.

## Pattern 4 — Frozen scope with an explicit escape hatch

Before implementation starts, a brief freezes an exact list of files the
model may touch (`TASK_SCOPE`) and an exact list it may only read
(`READ_ONLY_EVIDENCE`). The brief also states, explicitly, what happens
when the model discovers mid-implementation that the real fix needs a
file outside that list: **stop and go back for approval — never expand
scope on your own judgment.** This turned into a real, useful checkpoint
multiple times in this project: a bug fix that looked like it belonged in
one file turned out to require touching a file marked read-only, the
model stopped, explained precisely why (with a rejected alternative
design and the evidence that ruled it out), and got a scoped, one-file
approval back within the same review cycle — rather than either silently
overstepping or silently doing nothing.

The transferable idea: don't just tell the model what it's allowed to
change — give it a named exit for "I need more than I was given," so
"the model exceeded its brief" and "the model asked" are distinguishable
events you can audit.

## Case study: one feature, five audit rounds, real bugs caught each time

Task ROTA-T058 added a new hard scheduling constraint. It went through
audit rounds R4 through R8 before reaching a clean PASS. Each round
found something the previous round's author (this implementer) had
missed, and every one of them was a genuine defect, not audit
nitpicking:

- **R4**: a validator scan of unbounded historical data could
  spuriously fire on completely unrelated old records, and a new
  function exceeded the mechanical line-count limit.
- **R6**: a coordinator's deliberate manual override of the new rule
  could be silently reversed by the next automatic recompute — a real
  "the automation undoes a human decision" bug, found by a *merit*
  reviewer (the architect), not the mechanical auditor, because it
  required understanding product intent, not just re-deriving a
  test failure.
- **R7**: the R6 fix itself had a gap — it only protected one of two
  linked records making up a real-world 24-hour shift, found by the
  mechanical auditor building its own independent reproducer rather
  than trusting the implementer's stated test coverage.
- **R8**: narrow re-audit, clean PASS.

None of these were "the model didn't follow its skill file." They were
findings that a *layered, adversarial process* is expected to produce —
each layer catching a different class of error the others structurally
cannot. That's the actual claim this document is making: you don't get
reliability by asking the model to try harder at reading its
instructions. You get it by building a process where no single model
turn's compliance is load-bearing on its own.

## What this does not solve

This doesn't make any individual model response deterministic — the same
prompt can still produce different phrasing, different exploration paths,
occasionally a missed detail on the first pass. What it solves is the
thing that actually matters operationally: whether *incorrect output
reaches production*. Mechanical gates catch what they're coded to check,
every time, regardless of model mood. Adversarial review catches what the
first pass missed. Neither requires the model to be perfectly obedient —
they only require the *system* to never depend on that.
