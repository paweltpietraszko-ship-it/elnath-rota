# T011 multi-Site readiness evidence

Reproduce all three scenarios with:

`python -m benchmarks.t011_multisite_audit`

Files:

- `disjoint_full_cycle.json` — two Sites, one Coordinator, separate profiles,
  rosters, rules, ScheduleVersions, FINAL states and quarter balances;
- `shared_employee_full_cycle.json` — the same Employee completes legal work
  in both Sites; Site-owned state stays separate while EMP-03 WorkBalance,
  Availability and cross-Site context are intentionally shared;
- `shared_employee_rest_collision.json` — Site A remains FINAL while Site B
  fails closed with REST-01 for an illegal 10-hour cross-Site rest gap.

These are audit summaries generated from real SQLite files through
`rota.application.*`. The committed assertions are in
`tests/test_t011_multisite_pipeline.py`.
