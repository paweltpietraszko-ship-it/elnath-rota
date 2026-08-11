# Elnath Rota

Planning/staffing system for shift scheduling (Ward Mechanical Gate pipeline, OCHRONA pilot profile), governed by `arch/spec.md`.

## Branch policy

- `main` is protected. No direct commits or pushes to `main`.
- All work happens on `task/<id>` branches (e.g. `task/T002`), or `task/<id>-<slug>` for sub-fixes (e.g. `task/T001-crlf`).
- Merge to `main` only on the owner's explicit instruction ("merge" / "zmerguj").
