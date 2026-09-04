# PIPELINE NOTE 2026-09-04 — brief.md needs a literal `TASK_SCOPE:` block; backend.py cannot parse a narrative `## N. TASK_SCOPE` heading

STATUS: process/mechanics correction, not a product finding. Affects ROTA-T052,
ROTA-T053, ROTA-T054 identically — all three briefs from this architect
session are currently unusable by the mechanical gate. CC does not edit
brief.md content itself (contract text is architect/Codex-owned); this note
asks the architect to add the missing section to all three.

## The mechanical requirement, exactly

`backend.py` is the mechanical PASS/FAIL/WYMAGA_DECYZJI gate every
implementation is checked against before merge. It reads TASK_SCOPE with
`read_task_scope()` (`backend.py:85-103`):

```python
def read_task_scope(brief_path: Path) -> list[str]:
    ...
    for line in text.splitlines():
        if line.startswith("TASK_SCOPE:"):
            in_scope, found = True, True
            continue
        if in_scope:
            stripped = line.strip()
            if stripped.startswith("-"):
                scope.append(stripped.lstrip("- ").strip())
            elif stripped and not stripped.startswith("#"):
                in_scope = False
    if not found:
        raise ValueError("TASK_SCOPE missing in brief")
    return scope
```

It looks for a line that is **exactly** `TASK_SCOPE:` — no `##`, no leading
number, no surrounding prose on that line — then collects every following
`-` bullet as a scope path, until a non-bullet non-blank non-`#` line ends
the block. A markdown heading like `## 7. TASK_SCOPE` never matches
`line.startswith("TASK_SCOPE:")`, so the parser reports `TASK_SCOPE missing
in brief` and every changed file then fails `DIFF_SCOPE: file outside
TASK_SCOPE`, regardless of how correct the implementation is.

## What's actually in the three briefs today

`ROTA-T052/brief.md`, `ROTA-T053/brief.md`, `ROTA-T054/brief.md` each have
exactly one TASK_SCOPE section, as a narrative markdown heading (`## 9.
TASK_SCOPE`, `## 7. TASK_SCOPE`, `## 8. TASK_SCOPE` respectively) followed
by prose and bullets. None of the three contains a line that is literally
`TASK_SCOPE:`. Confirmed by running `backend.py` against a real T053
implementation commit on `task/ROTA-T053-global-working-month-contract`
(`a5bb21340765233fa5bf3234da3e4a046641a1a4`, base
`7cd5fde8446bd08a02c647d4eabaab9db200acba`): `STATUS: FAIL`, `TASK_SCOPE:
TASK_SCOPE missing in brief`, followed by a `DIFF_SCOPE` failure for every
single file actually in scope.

## What a working brief looks like

Prior briefs (written before this architect session) carry a **second**,
separate, literal section in addition to the narrative one — see
`tasks/ROTA-T051/brief.md`:

```
## 6. TASK_SCOPE

<narrative description of what's allowed and why>

## 11. EXACT TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T051/brief.md
- rota/application/schedule_export.py
- frontend/src/screens/Export.tsx
```

The narrative section stays — it carries the reasoning CC needs. The
`EXACT TASK_SCOPE` section is purely mechanical: the literal `TASK_SCOPE:`
line, then one `-` bullet per repo-relative path, nothing else on those
lines (no backticks needed, but harmless if present — the parser strips
`- ` and whitespace, not backticks, so a bulleted path wrapped in backticks
like `` - `rota/domain.py` `` would scope-check the literal string
`` `rota/domain.py` `` instead of `rota/domain.py` and fail path
validation — write the bare path, no backticks, in this block only).

## Request

Add an `EXACT TASK_SCOPE` section (literal `TASK_SCOPE:` line + bare
repo-relative path bullets, no backticks) to all three briefs, built from
the paths already listed in each brief's existing narrative TASK_SCOPE
section:

- `tasks/ROTA-T052/brief.md` — section "## 9. TASK_SCOPE"
- `tasks/ROTA-T053/brief.md` — section "## 7. TASK_SCOPE"
- `tasks/ROTA-T054/brief.md` — section "## 8. TASK_SCOPE"

Each narrative section already includes `tasks/ROTA-<id>/brief.md` itself
as an allowed path (needed since round corrections touch brief.md) — carry
that into the literal block too, matching T051's pattern above.

## Why this matters beyond these three tasks

This isn't a one-off typo — it's a structural gap in how this architect
session is producing brief.md, and it will silently break every future
task's mechanical gate the same way until fixed at the source. A quick
recap of the rule this session apparently wasn't told: **`backend.py` is a
literal-text parser, not a markdown-aware one.** It cares about exact line
prefixes (`TASK_SCOPE:`, `FROZEN.lock` SHA lines, etc.), not heading levels
or numbering. Any section a brief needs `backend.py` to consume mechanically
must be written in the exact format `backend.py` expects, verified by
actually running `backend.py --help` / reading `backend.py` itself if
unsure — not inferred from how a narrative section reads to a human. See
`CLAUDE.md` "PIPELINE MECHANICS" for the other mechanical tools
(`guard.py`, `task_init.py`, `session_log.py`) with the same property: they
are dumb, exact-format-dependent scripts, not language-model readers of the
brief.

## Where this sits in the pipeline (for reference)

- Architect (this session) authors/corrects `brief.md` and runs
  preimplementation audits (`tasks/<id>/round_01/tests/tests_r<n>.txt`)
  BEFORE any product code exists.
- CC (implementer only) never authors or edits brief.md contract text,
  never self-approves, executes only what TASK_SCOPE allows.
- `backend.py <brief.md> <before_sha> <head_sha> <output>` is the
  mechanical gate CC runs after implementing, output quoted verbatim, never
  paraphrased.
- Codex does the independent implementation-audit pass after `backend.py`
  is green.
- Merge to `main` only on Paweł's explicit instruction, after both gates
  are green.
- `BOARD.md` is the CC<->Codex handoff log (separate from this pipeline
  note) — not where architect corrections belong.
