# Henhouse tests

The rules are in [context/testing.md](../context/testing.md).  In short:

```
pip install -r tests/requirements.txt
python tests/harness/run_suite.py --list                  # suites and groups
python tests/harness/run_suite.py all                     # every suite but live
python tests/harness/run_suite.py --changed origin/henhouse   # the tests of your branch
```

- `tests/<module>/system/` and `tests/<module>/data/`: one suite per module; system tests check the code, data
  tests check committed data.
- `tests/framework/`: checks across modules, the test tree's own layout, and the runner.
- `tests/live/`: runs against a real install, only in a throwaway sandbox built by `tests/live/build_sandbox.sh`.
  Never on foxhouse.
- `tests/harness/`: the runner (`run_suite.py`), the results file writer and shared helpers.

Every run writes `test-results/<date>_<time>_<label>.md`, one line per test.
