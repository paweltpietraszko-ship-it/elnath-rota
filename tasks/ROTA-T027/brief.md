# ROTA-T027 — fix api/deps.py SQLite thread-affinity 500

Status: **IMPLEMENTED**

Base branch/SHA: `task/ROTA-T027` from `4aea831` (main, post-T021c merge)

## 1. Background

Found 2026-08-24 while building ROTA-T021c's Playwright e2e suite (see memory
`project_sqlite_thread_affinity_bug_found`). Strong candidate root cause for
the unreproduced live 500 Paweł hit on 2026-08-23 (memory
`project_t021_screen2_open_500_error`) — non-deterministic, depends on
worker-thread scheduling, matches why it was never reproducible on demand.

`api/deps.py::get_conn()` is a plain sync generator used as
`Depends(get_conn)`. FastAPI wraps a sync-generator dependency via
`contextmanager_in_threadpool`, dispatching `__enter__` (open) and `__exit__`
(`conn.close()`) as two *separate* `anyio.to_thread.run_sync` calls, with no
guarantee both land on the same worker thread. `sqlite3.connect()` defaults to
`check_same_thread=True`, so a connection is only valid on the thread that
created it. When teardown lands on a different worker thread than open (real
under concurrent request load), `conn.close()` raises
`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used
in that same thread` → an unhandled 500.

Reproduced repeatedly during T021c testing on three different endpoints
(`POST /workspace/sites`, `GET /workspace/employees/{id}/matrix`,
`GET /workspace/employees/{id}/target-hours`) — confirmed to be `get_conn()`
itself, not one handler. `EmployeeDetail.tsx` fires 3 GETs on mount, which hit
the race on nearly every open during testing — not a rare edge case.

## 2. Fix

`rota/persistence/db.py::connect()` — `sqlite3.connect(db_path,
check_same_thread=False)`. Each connection from `get_conn()` is opened, used,
and closed strictly sequentially within one request's lifecycle (never
concurrently by more than one thread at once) — exactly the usage pattern
`check_same_thread=False` is for. It only disables sqlite3's own same-thread
assertion; it does not change any real concurrency behavior, since nothing
here ever accesses one connection from two threads simultaneously.

Single call site for the application's own connections (`backup_repository.py`
and test files use their own separate `sqlite3.connect()` calls, outside this
threading pattern, left untouched).

## 3. Scope

`rota/persistence/db.py` only. No API contract, business logic, or schema
change.

## 4. Verification

- Full Python regression.
- Repeated `frontend/e2e/diagnostics.spec.ts` runs (the suite that originally
  surfaced this) with server logs checked for the `ProgrammingError` — must be
  absent across multiple runs, including the `EmployeeDetail`-mount-heavy
  paths that hit it most reliably before.
