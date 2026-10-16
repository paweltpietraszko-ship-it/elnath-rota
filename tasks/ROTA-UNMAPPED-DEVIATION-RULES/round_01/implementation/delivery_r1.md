# DELIVERY r1 — ROTA-UNMAPPED-DEVIATION-RULES (ROLE-01)

BASE (repo_before.hash): c81e78a (brief branch + origin/main ddf6256). EXACT SHA under audit: 93c1914.

OWNER_DECISION 2026-10-16 (CC merit review, conflict with T065-MANUAL-MIDDLE-SHIFT §6 raised to owner, option 1 chosen):
"Tak 1. nasz program nigdy nie zabrania koordynatorowi wychodzić poza zasady. Zapisuje odchylenie koordynatora. Jeśli gdzies w kodzie zobaczysz, że program blokuje koordynatora to zgłaszaj. Jeśli to mały fix to omiń architekta."
=> ROLE-01 from a deliberate manual correction is a PREFERENCE Deviation; T065-MANUAL-MIDDLE-SHIFT §6 ("ROLE-01 Deviation nie jest alternatywną zgodą") is superseded by owner for coordinator actions. The "Dodaj pracę" hard reject is OUT of this TASK_SCOPE — flagged separately in BOARD.

CHANGE: rota/application/deviation_mapping.py — one `_BUILTIN_RULE_CATEGORY` entry `"ROLE-01": PREFERENCE`. category_for_rule, _affected_target, validator, role_covers untouched; no fallback.

R1 (base repro): tests/test_role_deviation_mapping.py::test_r1_r2_... on c81e78a -> POST /manual-correction 500, `UnknownDeviationSource: no DeviationCategory mapping for rule 'ROLE-01'` (deviation_mapping.py:68). On 93c1914: 200.
R2: same test — child version, exactly one ROLE-01/PREFERENCE Deviation, parent V0 assignment unchanged, all SiteMembership.position_role_id unchanged, CoordinatorAction count +1, GET month via real router -> label "brak wymaganej roli".
R3: test_r3_... (person with required role -> no ROLE-01) + existing tests/test_t065_ordinary_roles.py (automatic gate still blocks).
R4: test_r4_... unknown code -> UnknownDeviationSource.

TESTS (.venv\Scripts\python.exe -m pytest, scoped):
- test_role_deviation_mapping + test_t065_ordinary_roles + test_t065_configurable_roles + test_t065_manual_middle_shift: 43 passed.
- category_for_rule consumers (test_t009_manual_edit, test_t012, test_t016_emp02_retirement, test_t023b, test_t036_rest_deviation_target, test_t058) + test_cloud_review_schedule_fixes: 207 passed.
- No full regression (not required by brief).

WHERE_MAP: round_01/implementation/where_map_category_for_rule.txt, where_map_file.txt. Consumers: manual_edit.py (manual correction), lifecycle_ops.py (automatic acceptance — unreachable for ROLE-01 because solver applies role_covers), tests. No second owner, no fallback.

backend.py (verbatim stdout, round_01/implementation/backend_r1.txt):
STATUS: PASS
HEAD_SHA: 93c191415a8abbed14b9b73c156079e665ffac01
CHECKS: TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES

OPEN, out of scope: WORK_PERIOD-01, FULL_HOUR-01, SITE_RULE-01, ASSIGN (unchanged, still unmapped).

## For Codex — how to work without disturbing CC
- Audit exact SHA 93c1914 in your own worktree (`git worktree add .worktrees/codex-unmapped origin/task/ROTA-UNMAPPED-DEVIATION-RULES`); never switch the branch of the main folder.
- Report as round_01/tests/tests_r2.txt on `audit/rota-unmapped-deviation-rules` (r1 = your precheck, kept); push it, update only your own BOARD row on main (AGENTS.md OWNER_AUTHORIZATION). CC carries the report onto the task branch.
- Do not commit to task/ROTA-UNMAPPED-DEVIATION-RULES; no merge.
