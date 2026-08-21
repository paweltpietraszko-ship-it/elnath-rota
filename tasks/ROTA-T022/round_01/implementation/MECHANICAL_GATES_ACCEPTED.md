# ROTA-T022 — mechanical gate exceptions, exact SHA only

OWNER DECISION, 2026-08-21, for exact SHA:

`d87855c58323501a1cd07abfb86d135804574626`

Verbatim owner decision:

- `SIZE_FILE tests/test_t012.py = 1704` — ACCEPTED. File is inherited;
  T022 changes only one named oracle in it (SCOPE AMENDMENT 03), net +3
  lines.
- `TOTAL_LINES = 1081` — ACCEPTED. Scope matches T022's cross-cutting
  repair and includes a 527-line regression matrix
  (`tests/test_t022_planning_integrity.py`).

This acceptance:

- does not change backend.py thresholds;
- is not precedent for any other SHA;
- is not a substantive PASS of the implementation;
- closes only the mechanical gates ahead of the Codex implementation audit.

STATUS: ROTA-T022 @ d87855c — MECHANICAL GATES ACCEPTED / READY FOR CODEX
IMPLEMENTATION AUDIT.

Full `backend.py` output for this SHA is at
`tasks/ROTA-T022/round_01/implementation/backend_output.txt`.
