# Testing and merge policy

**Owns:** the test suites (per module, `framework`, `live`), system tests and data tests, the runner and its
results file, slicing a full run for parallel cloud workers, who runs which tests and when, the rules every test
follows, and how work reaches `henhouse`: merge first, one full run, fix forward, roll back.
**Does not own:** git basics and who merges (`CLAUDE.md` "Working in this repository"); the work docket protocol
(`context/work-page-protocol.md`); the install itself (`README/05` to `README/08`).

**Built from:** realmCAM spec 80 "Test suites and merge policy" (Lee, Nov 2026), adapted to henhouse; the realmCAM
PR watcher and merge runner setup (relayed by Lee, 2026-11-21); `CLAUDE.md` (Lee, 2026-11-04);
`REFACTOR_REPORT.md` §9 and §10 (the sandbox install run).  The rule ids are `TS-H..` so they never collide with
realmCAM's `TS-..` ids.

Henhouse will grow to tens of thousands of tests.  Everything below is chosen so that adding the ten-thousandth
test is as easy as adding the tenth: a fixed folder layout that a test checks, one runner, one results format, and
slices that come from recorded times rather than from someone's guess.

## 1. The suites and the layout

- TS-H01: **The full suite** is every suite under `tests/`: all the module suites and `framework`, which run from a
  plain checkout (`run_suite.py all`), plus `live`, which runs in a throwaway sandbox install (TS-H06).  It is the
  only check `henhouse` has: there is no CI.
- TS-H02: **One suite per module.**  Every folder with a `__module__.py` has a suite folder of the same name under
  `tests/` (`tests/hh`, `tests/hh_page`, `tests/accounting`, ...), blacklisted modules included: a module that is
  off on one install is on at another.  Two suites are not modules: `framework` (checks across modules, the test
  tree itself and the runner) and `live` (TS-H06).  The tests live in `tests/`, not inside the module folders,
  because the registry scanners read every `.py` file under a module folder (`iter_scan_files()`), and deploy and
  upgrade copy module folders.  `tests/framework/system/test_layout.py` fails when a module has no suite or a
  folder under `tests/` is neither a module nor `framework`/`live`.
- TS-H03: **Every module suite starts with `system/test_imports.py`**, which imports every `.py` file of the module
  from a plain checkout, one test per file.  It is the floor: a module whose files do not all import has no other
  test worth running.  A new module copies `tests/hh/system/test_imports.py` and changes the module name.
- TS-H04: **System tests and data tests.**  Every test file sits under `tests/<suite>/system/` or
  `tests/<suite>/data/`; the layout test fails on any other place.
  - A *data test* checks our committed data rather than the code: module manifests, `deploy/conf` whitelists and
    blacklists, `config_labels` registrations, `schema.sql` files, `example_data.sql`, help text, generated files.
    It asserts that the data is valid, consistent or current, so it fails when the data is wrong even if the code
    is right.
  - A *system test* checks what the code does, on inputs built in the test or on fixed fixtures.
  - `--system` runs only the system tests (system integrity), `--data` only the data tests, neither flag both.
    `run_suite.py --counts` prints the split per suite without running anything.  On 2026-11-21: 717 system and
    117 data tests outside `live`, and 61 live tests.
- TS-H05: **Groups.**  A suite's tests can sit in subfolders, for example `tests/hh/system/tp/` and
  `tests/hh/data/tp/`; `run_suite.py hh/tp` runs that group in both kinds.  Split a suite into groups by what the
  tests check, never by run time (slicing handles run time, TS-H13).  Mirror the source tree: the tests of
  `hh/gateway/registry/` go in `tests/hh/system/registry/` and so on, one `test_<file>.py` per source file once a
  file has more than a few tests.
- TS-H06: **The live suite** (`tests/live/`) runs henhouse commands against a real install: install, init-db,
  add-db-users, deploy, then pages, MCP and the web home page, checked in MySQL and over HTTP.
  - It runs **only in a throwaway cloud sandbox** built by `tests/live/build_sandbox.sh` (Ubuntu 24.04, root,
    MySQL 8.0, nginx, no systemd, no IPv6; about 25 seconds once the packages are on the box, plus the package
    install on a bare box).  The script writes `/etc/henhouse-sandbox`, and the runner refuses the live suite
    without that file.  **Never on foxhouse, Lee's PC or any box with real data:** it sets the MySQL root password,
    creates and deletes Unix users and uninstalls any earlier install of the project.  The script refuses to start
    on a box that has a henhouse install it did not make.
  - The script runs `install`, `uninstall` and `deploy` as root, so `CLAUDE.md`'s rule applies: a thread runs it
    only when its task says so.  The merge runner's task does; an ordinary working thread's does not.
  - The sandbox needs two shims that are not henhouse bugs: a `systemctl` that starts and reloads nginx without
    systemd, and an `nginx` wrapper that drops the generated `listen [::]` lines (no IPv6).  Both live only in
    `/usr/local/` on the sandbox.
  - Live tests create their own pages under unique names and delete them afterwards, so the suite can run again
    on the same sandbox.  Rebuild the sandbox (the same script) to start clean.
  - `run_suite.py all` leaves `live` out, because a plain checkout cannot run it.  A full run includes it (TS-H31).
- TS-H07: **Helpers.**  Shared helpers for every suite go in `tests/harness/lib.py`.  A suite's own helpers go in a
  `_name.py` file beside its tests, imported by its full dotted name (`from tests.live.system._live import hen`),
  with `__init__.py` files on the way.  A `.py` file under `system/` or `data/` that is neither `test_*.py` nor
  `_*.py` fails the layout test, because pytest would silently never run it.

## 2. The runner and the results file

- TS-H10: **Every run goes through the runner**, on Lee's PC, on foxhouse, in the cloud and in every agent thread,
  from the repo root:

  ```
  pip install -r tests/requirements.txt                    # once per machine
  python tests/harness/run_suite.py --list                 # suites and groups
  python tests/harness/run_suite.py --counts               # system and data test counts, no run
  python tests/harness/run_suite.py all                    # every suite but live, one after another
  python tests/harness/run_suite.py hh                     # one suite
  python tests/harness/run_suite.py hh/tp                  # one group
  python tests/harness/run_suite.py hh --system            # system tests only (--data: data tests only)
  python tests/harness/run_suite.py --changed origin/henhouse   # a targeted run for a branch (TS-H32)
  python tests/harness/run_suite.py hh --only tests/hh/system/tp/test_text_processor.py
  python tests/harness/run_suite.py hh -- -x               # anything after -- goes to pytest
  sudo bash tests/live/build_sandbox.sh && HH_LIVE_PROJECT=/home/hentest/henhouse \
      python tests/harness/run_suite.py live               # sandbox only (TS-H06)
  ```

  Bare `pytest` works for a quick look but writes no results file, and its counts do not go in a PR.
- TS-H11: **Each run writes `test-results/<date>_<time>_<label>.md`** (kept out of git; upload it to the project
  when a PR or report needs it).  The label is the target plus `-system`, `-data` or `-shardKofN`.  The file holds:
  the commit and branch (and whether the tree had uncommitted changes), machine, cores, Python and package
  versions, the command and the selection; then one line per test (`PASS`, `FAIL`, `ERROR`, `SKIP`, `XFAIL`,
  `XPASS`, with its time), appended and flushed the moment that test ends, each failure followed by its
  traceback; and at the end the counts and the commands that run just the failures again.  A run that is cut off
  keeps every line written so far.
- TS-H12: **Running again.**
  - `--failed` runs only the tests that failed in that label's last results file, into a new file.
  - `--resume` runs only the tests the last file has no line for yet (the same selection), and appends to it.
    This is how a slice that a machine restart cut off finishes.
  - `--only ID ...` runs given test files or ids, from the repo root, from `tests/` or from the suite folder.
- TS-H13: **Slicing.**  `--shard K/N` runs slice K of N of the selected test files.  Files are packed longest
  first using the times in `test-results/timings.json`, which every run updates (a file with no recorded time
  counts as 2 seconds), so slices come out even and the same inputs always give the same slices.
  `--plan --minutes 8` prints how many slices of about that length the selection needs and the command for each.
  The slicing unit is the test file, so **keep every test file under about two minutes**; split a file that grows
  past that.
- TS-H14: **Exit codes:** 0 every test passed (XFAIL counts as passed), 2 a test failed, errored or unexpectedly
  passed, 3 the environment is not ready and nothing ran (TS-H21), 4 bad arguments or nothing to resume.

## 3. Rules every test follows

- TS-H20: **Never skip, disable or quarantine a test to get a pass,** and never weaken an assertion to match a wrong
  result.  A test whose expectation was wrong is changed with the reason in its docstring or the commit.
  `test_layout.py` fails on `pytest.skip`, `skipif` or `importorskip` in any test file.
- TS-H21: **Check the environment before calling a failure real.**  Before a run the runner checks Python 3.10 or
  newer, every package in `tests/requirements.txt` at its minimum version, that `hh` would not resolve to another
  henhouse (a deployed copy on `PYTHONPATH`), and for `live` the sandbox marker and `HH_LIVE_PROJECT`.  A problem
  stops the run with the fix and exit 3; `--skip-check` runs anyway and the results file says so.
- TS-H22: **A full run has no skips.**  A `SKIP` line means the run was not the full suite; the summary says so.
- TS-H23: **Known bugs are pinned with a strict xfail,** never a skip:
  `pytest.param(..., marks=pytest.mark.xfail(reason="known bug: <what is wrong>", strict=True))` or the same
  decorator on a test.  The reason must start with `known bug:` and `strict` must stay true (`test_layout.py`
  checks both).  When someone fixes the bug the test passes, the run reports `XPASS` and fails, and the fix removes
  the marker in the same PR.  Use it for a bug found while writing tests that is not this change's to fix; report
  it in the PR.
- TS-H24: **Tests stay in their box.**  Module and framework tests need no MySQL, no install, no daemons and no
  network; they replace a page or image lookup with a fake (see `tests/hh/system/tp/test_text_processor.py`).
  They write only to pytest's `tmp_path`, `test-results/` and the ignored registry caches; a test that needs the
  module cache points it at `tmp_path` (`tests/hh/system/registry/test_module_discovery.py`).  Only `live` touches
  MySQL, nginx and Unix users, and only in the sandbox.  No test ever reaches foxhouse.
- TS-H25: **Lee's rule for every range:** mid-range passes, each limit passes, and twice the margin past each limit
  fails, each a single-item test (example: the `normalize()` range tests in
  `tests/accounting/system/test_currency_math.py`).
- TS-H26: **A bug fix comes with a test that fails without the fix,** in the same PR, in the module's suite (or in
  `live` when only a real install shows the bug).
- TS-H27: **Generated files get a drift test** when they are committed: a data test that fails when the file no
  longer matches its source, with the generator command in its message.  The fix is to run the generator, never to
  edit the file.  (None is built yet: the compiled `.js` next to each `ts/` folder is the first candidate, TS-H50.)

## 4. Who runs what

- TS-H30: **Only the merge runner runs the full suite,** once on `henhouse` after each merge or batch of merges.
  Parallel full runs duplicate the work and slow each other down.
- TS-H31: **How a full run is run.**  Never as one long run in the cloud: cloud machines restart, and a restart
  loses the whole run.
  - **On one machine** (Lee's PC; foxhouse only for the plain-checkout suites, never `live`):
    `run_suite.py all`, which runs every suite but `live` in turn (alphabetical), each with its own results file.
  - **In the cloud:** `run_suite.py all --plan --minutes 8` gives N slices of 5 to 10 minutes; each of about six
    workers runs `run_suite.py all --shard K/N` on a fresh clone at the merge commit, and one more worker builds
    the sandbox and runs `live` (sliced the same way once it passes 10 minutes).  A restart loses only the slice it
    was running; that slice alone runs again with `--resume`.  The full run passes when every slice's results file
    does.  Today the whole of `all` takes a few seconds, so N is 1 until the suites grow.
- TS-H32: **Every other thread runs targeted tests only:** before it opens a PR and again before it merges,
  `run_suite.py --changed origin/henhouse`, which runs `framework`, the suite of every module the branch touches,
  and every test file it adds or changes.  The PR says which tests ran and their counts, from the results file.  It
  does not start a full run.  A failure it sees outside its change goes to the coordinator, who passes it to the
  merge runner or the thread that owns that code.
- TS-H33: **When time is short:** test each item on its own, merge it, and fix forward; say in the hand-off that
  the item is in and still needs the full-suite pass.

## 5. Getting work onto `henhouse`

- TS-H40: **Merge first, then the full suite, then fix forward** (`CLAUDE.md`):
  1. **Merge** the PR (in batches when several are ready), after merging `henhouse` into the branch.  Lee is never
     asked to approve or click a merge.
  2. **Run the full suite once** on `henhouse` after the merge (the merge runner, TS-H30, TS-H31).
  3. **Fix forward** on `henhouse`: a failure the merge brought in is fixed in a follow-up PR right away, by the
     thread whose change caused it.  The merge runner reports the failure to that thread; it does not fix forward
     on someone else's code.
  4. **If fixing forward gets hard,** go back to the last known good commit and merge the PRs forward again one at
     a time, more carefully, with the suite after each, to find the culprit.  Never force-push `henhouse`.
- TS-H41: **A PR records** what changed, the tests run for it and their counts (TS-H32), any known bug it pinned
  (TS-H23), and starts with the attribution block.
- TS-H42: **Every merge updates `STATUS.md`** at the repo root: what works now, the latest full run's counts per
  suite, the merge queue (open PRs and their state), what needs Lee, and a short recent-changes log (the last few
  merges only).
- TS-H43: **The PR watcher and the merge runner** are two long-lived threads that run on top of this policy (not
  set up yet):
  - **PR watcher:** an hourly scheduled run.  It lists the open PRs on `henhouseai/henhouse`, drafts included.
    For each PR whose head has new commits since its last check it runs that PR's targeted tests (TS-H32) on a
    clone of the PR head, never a full run, and posts one PR comment with the counts and any failures, saying it
    comes from the automated watcher, not from Lee.  Drafts are tested and commented, never merged.  A ready PR
    from a trusted contributor that passes is approved and handed to the merge runner in the same turn.  A PR from
    an unknown author is tested, then flagged to the coordinator to confirm with Lee first.  If nothing needs
    anyone, it ends silently.
  - **Merge runner:** wakes only when the watcher messages it.  It merges the ready PRs in a batch (TS-H40), runs
    the full suite once in slices (TS-H31), updates `STATUS.md` (TS-H42), and writes a failure report for the
    authors of the batch, with the failing ids and the `--only` commands from the results files.
  - The coordinator stays out of the loop unless something needs Lee: an unknown author, failures to pass on, or
    a stuck thread.
- TS-H44: **Never touch foxhouse from a test or a merge.**  Foxhouse is a separate repo and the one live install;
  deploying there is its own task with Lee's go-ahead.

## 6. Not built yet

- TS-H50: drift tests for committed generated files (compiled `.js` from `ts/`, TS-H27), and a `tsc --noEmit`
  check of the TypeScript as its own suite (it needs Node).
- TS-H51: `mypy` as a framework test.  It runs clean on `tests/harness` today; the rest of the tree has the 5 errors
  listed in `REFACTOR_REPORT.md`.
- TS-H52: the live suite does not yet cover the web UI beyond the home page (a browser suite with Playwright),
  MCP tools above guest tier, export-db and import-db, upgrade, or an install with modules turned off.
- TS-H53: the PR watcher and merge runner threads (TS-H43).
