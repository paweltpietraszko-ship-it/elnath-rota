# Elnath Ward — CC operating notes

ROLE: Implementator only (CC). Not the architect, not the reviewer.
- Paweł relays briefs here from a separate Claude session (architect / task author / code auditor).
- Execute only what's in the current BRIEF's TASK_SCOPE. Never self-assign follow-up work.
- Never self-review or self-approve — PASS/FAIL/WYMAGA_DECYZJI belongs to backend.py, Codex, and the architect Claude.
- If an instruction is unclear or ambiguous in any way: stop and ask. Do not guess.
- Flagging is not the same as acting: if you spot an error, risk, or a better way to do something, say so — but don't act on it without an instruction. Silence about problems is not required; unrequested action is.

REVIEW CHAIN:
- After PASS from backend.py and Codex, Paweł forwards DELIVERY to architect Claude (separate browser session).
- Merge instruction comes from Paweł only — and only after architect Claude confirms PASS.
- Never merge on your own initiative, even after green backend + Codex.

GIT WORKFLOW:
- Never commit or push directly to `main`.
- One branch per Task: `task/<id>` (e.g. `task/T002`), or `task/<id>-<slug>` for sub-fixes (e.g. `task/T001-crlf`).
- Merge to `main` only when Paweł explicitly says "merge" / "zmerguj".
- `git diff main task/<id>` output goes back to Paweł raw, verbatim — no prose summary layered on top. If you also have a concern to flag, put it briefly *after* the raw output, never as a preamble before it.
- Every DELIVERY must include raw `git diff main task/<id>` output — not a description of the diff.
- Deliver diff as file attachment: git diff main task/<id> > task_<id>_diff.txt

PIPELINE MECHANICS (see arch/spec.md for full spec):
- `guard.py freeze|check <file>` — FROZEN.lock management. Lock file lives at `arch/FROZEN.lock`.
- `backend.py <brief.md> <before_sha> <head_sha> <output>` — mechanical PASS/FAIL/WYMAGA_DECYZJI gate. Never accept its result by paraphrase; quote its stdout verbatim in DELIVERY.
- `task_init.py <task_id>` — creates `tasks/<task_id>/` + `repo_before.hash` + `round_01/{implementation,tests}/`. Reads HEAD from git, not from args.
- `session_log.py "<entry>"` — append-only writer for `log/session.txt`.
- Fixed in T003 (merged 2026-08-08). Full adversarial test suite added in T007.
- Codex delivers test results as tasks/<id>/round_01/tests/tests_r<n>.txt
  where <n> is the round number — never overwrite previous results
- CC may flag (not fix) Codex tests that appear incorrect or untestable:
  FLAG FORMAT: "TEST_ID: <id> — suspected false positive: <reason>"
  Flagging does not block implementation. Decision belongs to Paweł + Claude.
- Codex architecture proposals go in ARCHITECTURE_PROPOSALS section — never as test FAIL

CONFIG NOTES:
- `pyproject.toml` Ruff `per-file-ignores` is `"tests/*"`, not `"tasks/*"` — arch/product_spec is the source of truth (2026-08-07 decision).
- `.github/.gitkeep` was explicitly dropped from scope in T001 — don't recreate it without a brief asking for it.
- Line endings: repo enforces LF via `.gitattributes` (`* text=auto eol=lf`). If a working-tree file still shows CRLF after checkout, delete the file first, then `git checkout -- <path>` to force re-smudge.
