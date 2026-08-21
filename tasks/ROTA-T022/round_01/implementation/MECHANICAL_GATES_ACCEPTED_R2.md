ROTA-T022 mechanical gate acceptance, exact SHA only.

OWNER DECISION 2026-08-21, SHA 41611c95986fd50458006a820a69ce4f3f1a2ed4:

- SIZE_FILE tests/test_t012.py=1704 — ACCEPTED (inherited, unchanged since prior acceptance)
- SIZE_FILE tests/test_t020.py=689 — ACCEPTED (inherited T020 size; T022 R1-6/R2-3 = one-arg SHA swap only)
- SIZE_FILE tests/test_t022_planning_integrity.py=605 — ACCEPTED (new T022 matrix, within 900-line ceiling)
- TOTAL_LINES=1209 — ACCEPTED (R1+R2 fix rounds, matches cross-cutting repair scope)

Scope: not a threshold change, not precedent for other SHA, not substantive PASS. Closes mechanical gates only, ahead of Codex Round 3.

STATUS: ROTA-T022 @ 41611c9 — MECHANICAL GATES ACCEPTED / READY FOR CODEX ROUND 3 (R2-1/R2-2/R2-3 only).

Supersedes: tasks/ROTA-T022/round_01/implementation/MECHANICAL_GATES_ACCEPTED.md (was pinned to d87855c).
Full backend.py output: tasks/ROTA-T022/round_01/implementation/backend_output_r2.txt.
