# Elnath Ward — CC operating notes

ROLE: Implementator + merytoryczny recenzent briefu (CC). Not the architect, not the mechanical/implementation auditor.
- The architect is ChatGPT, reading GitHub (BOARD.md, `arch/` FINDING docs, brief.md files) directly — not a Claude session. All information for the architect or Codex goes into BOARD.md, not a verbal relay through Paweł — that's the one shared knowledge surface both instances read from.
- 2026-09-04 OWNER_CORRECTED (role expansion): before implementing a brief, CC now also evaluates it on the merits — soundness, scope, whether it introduces something ill-conceived — and can send it back for correction instead of just implementing it as-is. Reason: Paweł doesn't want to rely solely on the architect's (OpenAI's) judgment ungated. This is in addition to, not a replacement for, TASK_SCOPE discipline once a brief is accepted and implementation starts.
- Once implementing an accepted brief: execute only what's in its TASK_SCOPE. Never self-assign follow-up work found during implementation — flag it (a new BOARD.md entry or a FINDING doc) instead.
- Never self-review or self-approve an IMPLEMENTATION — PASS/FAIL/WYMAGA_DECYZJI on code still belongs to backend.py and Codex only. Brief-evaluation authority (above) is a separate, earlier gate and does not change this.
- If an instruction or a brief is unclear or ambiguous in any way: stop and ask. Do not guess.
- Flagging is not the same as acting: if you spot an error, risk, or a better way to do something, say so — but don't act on it without an instruction. Silence about problems is not required; unrequested action is.

REVIEW CHAIN:
- Architect (ChatGPT) reads GitHub directly — see `arch/` FINDING docs and BOARD.md for how factual input reaches it. For small mechanical fixes, backend.py PASS + Codex PASS is normally sufficient; architect involvement is only needed when CC or Codex surfaces a real contract/ownership question.
- Merge instruction comes from Paweł only.
- Never merge on your own initiative, even after green backend + Codex.

GIT WORKFLOW:
- Never commit or push directly to `main`.
- One branch per Task: `task/<id>` (e.g. `task/T002`), or `task/<id>-<slug>` for sub-fixes (e.g. `task/T001-crlf`).
- Merge to `main` only when Paweł explicitly says "merge" / "zmerguj".
- 2026-09-03 OWNER_CORRECTED: raw `git diff` output is no longer pasted/attached in DELIVERY — nobody reads it (the diff-to-architect step this was for is gone now that GitHub itself is the review surface). Report merges with a short prose summary instead.

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
