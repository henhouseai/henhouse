# Henhouse status

Updated on every merge to `henhouse` (context/testing.md TS-H42).

## What works now

- The hookified module layout (merged Nov 5, commit `2a75850`; `REFACTOR_REPORT.md`).  A fresh install, init-db,
  add-db-users and deploy run clean in a cloud sandbox.
- Test suites: one per module plus `framework` and `live`, run with `python tests/harness/run_suite.py`
  (context/testing.md).

## Latest full run

| Suite | Passed | Failed | Skipped | Known bugs (xfail) |
|---|---|---|---|---|
| `all` (24 module suites + framework), 2026-11-21 | 834 | 0 | 0 | 0 |
| `live` (cloud sandbox), 2026-11-21 | 61 | 0 | 0 | 0 |

## Merge queue

| PR | What | State |
|---|---|---|
| #1 | nginx and systemd deploy fixes | open, waiting on Lee's review |

## Needs Lee

- Nothing right now.

## Recent changes

- 2026-11-21: removed unused DecimalMath validate, divide, average and multiply (Lee).
- 2026-11-21: test suites, runner and testing policy added (`context/testing.md`).
