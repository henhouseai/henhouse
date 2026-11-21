#!/usr/bin/env python3
"""Run a henhouse test suite and write its results file.  The rules are in context/testing.md.

    python tests/harness/run_suite.py --list                 # suites, groups and file counts
    python tests/harness/run_suite.py --counts               # system and data test counts per suite (no run)
    python tests/harness/run_suite.py hh                     # one suite
    python tests/harness/run_suite.py hh/tp                  # one group of a suite
    python tests/harness/run_suite.py hh --system            # leave the data tests out
    python tests/harness/run_suite.py framework --data       # only the data tests
    python tests/harness/run_suite.py hh --only tests/hh/system/tp/test_text_processor.py
    python tests/harness/run_suite.py hh --failed            # the failures of hh's last results file, again
    python tests/harness/run_suite.py hh --resume            # the tests hh's last file has no line for yet
    python tests/harness/run_suite.py all --shard 2/6        # slice 2 of 6 of the full run (cloud workers)
    python tests/harness/run_suite.py all --plan --minutes 8 # how to slice the full run for workers

Exit codes: 0 every test passed, 2 a test failed or errored, 3 the environment is not ready (nothing ran),
4 bad arguments.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Check what `hh` resolves to *before* the checkout goes on sys.path: another henhouse on PYTHONPATH (a deployed
# copy under /srv, say) would otherwise be what the tests import in subprocesses.
_SHADOW_HH = importlib.util.find_spec("hh")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.harness import results as results_mod  # noqa: E402
from tests.harness.lib import KINDS, TESTS_ROOT, find_test_files, module_names, suite_names  # noqa: E402

EXIT_OK, EXIT_FAILED, EXIT_ENV, EXIT_USAGE = 0, 2, 3, 4

# Suites that `all` leaves out: they need something a plain checkout does not have.
NOT_IN_ALL = {"live"}

SANDBOX_MARKER = Path("/etc/henhouse-sandbox")
DEFAULT_FILE_SECONDS = 2.0


# -- targets -----------------------------------------------------------------------------------------------------------

def parse_target(target: str) -> tuple[str, Optional[str]]:
    suite, _, group = target.partition("/")
    return suite, (group or None)


def target_paths(target: str, kinds: List[str]) -> List[Path]:
    """The folders a target covers, for the kinds asked for."""
    suite, group = parse_target(target)
    paths = []
    for kind in kinds:
        base = TESTS_ROOT / suite / kind
        path = base / group if group else base
        if path.exists():
            paths.append(path)
    return paths


def resolve_only(ids: List[str], suite: str) -> List[str]:
    """--only ids may be given from the repo root, from tests/, or from the suite folder."""
    out = []
    for raw in ids:
        file_part, sep, rest = raw.partition("::")
        candidates = [REPO_ROOT / file_part, TESTS_ROOT / file_part, TESTS_ROOT / suite / file_part]
        for cand in candidates:
            if cand.exists():
                out.append(str(cand.relative_to(REPO_ROOT)) + sep + rest)
                break
        else:
            raise SystemExit(f"--only: no such test file: {file_part}")
    return out


def files_for(paths: List[Path]) -> List[str]:
    files: List[str] = []
    for p in paths:
        found = [p] if p.is_file() else sorted(x for x in p.rglob("test_*.py") if "__pycache__" not in x.parts)
        files.extend(str(f.relative_to(REPO_ROOT)) for f in found)
    return files


def shard(files: List[str], k: int, n: int) -> List[str]:
    """Slice k of n (1-based): longest-first packing on the recorded file times, so slices come out even."""
    timings = results_mod.load_timings()
    bins: List[List[str]] = [[] for _ in range(n)]
    loads = [0.0] * n
    for f in sorted(files, key=lambda f: (-timings.get(f, DEFAULT_FILE_SECONDS), f)):
        i = loads.index(min(loads))
        bins[i].append(f)
        loads[i] += timings.get(f, DEFAULT_FILE_SECONDS)
    return sorted(bins[k - 1])


def changed_targets(ref: str) -> List[str]:
    """The suites and test files a change touches (TS-H32): a module's own suite for a change under that module,
    a test file itself for a change under tests/, and always `framework`."""
    out = subprocess.run(["git", "diff", "--name-only", f"{ref}...HEAD"], cwd=REPO_ROOT, capture_output=True,
                         text=True)
    if out.returncode != 0:
        raise SystemExit(f"--changed: git diff against {ref} failed: {out.stderr.strip()}")
    names = out.stdout.split()
    names += subprocess.run(["git", "ls-files", "-mo", "--exclude-standard"], cwd=REPO_ROOT, capture_output=True,
                            text=True).stdout.split()
    modules = set(module_names())
    targets: List[str] = ["framework"]
    for name in names:
        parts = Path(name).parts
        if parts[0] == "tests" and len(parts) > 2 and parts[1] in suite_names():
            if parts[1] == "live":
                continue  # the live suite runs in a sandbox, by the merge runner (TS-H06)
            if Path(name).name.startswith("test_") and (REPO_ROOT / name).exists():
                targets.append(name)
            else:
                targets.append(parts[1])
        elif parts[0] in modules:
            targets.append(parts[0])
    return list(dict.fromkeys(targets))


# -- environment (TS-H21) ----------------------------------------------------------------------------------------------

def _version_tuple(v: str) -> tuple:
    out = []
    for part in v.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def check_environment(suite: str) -> List[str]:
    """Problems that would make a failure not real.  Empty list: ready."""
    from importlib import metadata
    problems = []
    if sys.version_info < (3, 10):
        problems.append(f"Python {sys.version.split()[0]} is too old: henhouse needs 3.10 or newer")
    req_file = TESTS_ROOT / "requirements.txt"
    for line in req_file.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name, _, minimum = line.partition(">=")
        name = name.strip()
        try:
            have = metadata.version(name)
        except metadata.PackageNotFoundError:
            problems.append(f"{name} is not installed")
            continue
        if minimum and _version_tuple(have) < _version_tuple(minimum.strip()):
            problems.append(f"{name} {have} is older than {minimum.strip()}")
    if problems:
        problems.append("fix: pip install -r tests/requirements.txt")
    if _SHADOW_HH is not None and _SHADOW_HH.origin:
        origin = Path(_SHADOW_HH.origin).resolve()
        if REPO_ROOT not in origin.parents:
            problems.append(f"`hh` resolves to {origin.parent}, not this checkout: clear PYTHONPATH before running tests")
    if suite == "live":
        if not SANDBOX_MARKER.exists():
            problems.append(f"the live suite runs only in a throwaway sandbox ({SANDBOX_MARKER} is missing); "
                            "build one with tests/live/build_sandbox.sh.  Never on foxhouse.")
        project = os.environ.get("HH_LIVE_PROJECT")
        if not project or not (Path(project) / "hen.py").exists():
            problems.append("HH_LIVE_PROJECT must name the installed project folder (the one with hen.py)")
    return problems


# -- listing -----------------------------------------------------------------------------------------------------------

def groups_of(suite: str) -> Dict[str, int]:
    groups: Dict[str, int] = {}
    for kind in KINDS:
        base = TESTS_ROOT / suite / kind
        if not base.is_dir():
            continue
        for f in base.rglob("test_*.py"):
            if "__pycache__" in f.parts:
                continue
            rel = f.relative_to(base)
            g = rel.parts[0] if len(rel.parts) > 1 else "(top)"
            groups[g] = groups.get(g, 0) + 1
    return groups


def cmd_list() -> int:
    for suite in suite_names():
        files = find_test_files(suite)
        extra = "  (not in `all`)" if suite in NOT_IN_ALL else ""
        print(f"{suite}: {len(files)} files{extra}")
        for g, n in sorted(groups_of(suite).items()):
            if g != "(top)":
                print(f"  {suite}/{g}: {n} files")
    return EXIT_OK


def collect_count(paths: List[str]) -> int:
    if not paths:
        return 0
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", *base_pytest_args(), *paths],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    return sum(1 for line in out.stdout.splitlines() if "::" in line)


def cmd_counts(suites: List[str]) -> int:
    total = {"system": 0, "data": 0}
    print(f"{'suite':<22}{'system':>8}{'data':>8}")
    for suite in suites:
        row = {}
        for kind in KINDS:
            row[kind] = collect_count(files_for(target_paths(suite, [kind])))
            total[kind] += row[kind]
        print(f"{suite:<22}{row['system']:>8}{row['data']:>8}")
    print(f"{'total':<22}{total['system']:>8}{total['data']:>8}")
    return EXIT_OK


def cmd_plan(suites: List[str], kinds: List[str], minutes: float) -> int:
    timings = results_mod.load_timings()
    files = [f for s in suites for f in files_for(target_paths(s, kinds))]
    seconds = sum(timings.get(f, DEFAULT_FILE_SECONDS) for f in files)
    unknown = sum(1 for f in files if f not in timings)
    n = max(1, -(-int(seconds) // int(minutes * 60)))
    print(f"{len(files)} test files, about {seconds / 60:.1f} minutes on one worker "
          f"({unknown} files have no recorded time, counted as {DEFAULT_FILE_SECONDS:.0f}s each).")
    print(f"{n} slice(s) of at most about {minutes:g} minutes:")
    for k in range(1, n + 1):
        print(f"  python tests/harness/run_suite.py all --shard {k}/{n}")
    return EXIT_OK


# -- running -----------------------------------------------------------------------------------------------------------

def base_pytest_args() -> List[str]:
    return [
        "-c", str(TESTS_ROOT / "pytest.ini"),
        "--rootdir", str(REPO_ROOT),
        "--import-mode=importlib",
        "-p", "no:cacheprovider",
    ]


class _Deselect:
    """Drops tests that already have a line in the results file being resumed."""

    def __init__(self, done: set) -> None:
        self.done = done

    def pytest_collection_modifyitems(self, session, config, items) -> None:
        keep = [i for i in items if i.nodeid not in self.done]
        dropped = [i for i in items if i.nodeid in self.done]
        if dropped:
            config.hook.pytest_deselected(items=dropped)
        items[:] = keep


def run_one(label: str, selection: Dict, command: str, notes: List[str],
            resume_from: Optional[Path] = None, done: Optional[set] = None) -> int:
    import pytest

    paths: List[str] = selection["paths"]
    if not paths:
        print(f"{label}: no test files selected, nothing to run")
        return EXIT_OK
    args = [*base_pytest_args(), "-q", "-rfE", *paths]
    if selection.get("k"):
        args += ["-k", selection["k"]]
    args += selection.get("extra", [])

    out_path = resume_from or results_mod.new_results_path(label)
    plugin = results_mod.ResultsPlugin(out_path, label, command, selection, append=resume_from is not None,
                                       notes=notes)
    plugins: list = [plugin]
    if done:
        plugins.append(_Deselect(done))
    os.chdir(REPO_ROOT)
    code = pytest.main(args, plugins=plugins)
    print(f"\nResults: {out_path.relative_to(REPO_ROOT)}")
    if code == 0:
        return EXIT_OK
    if code == 5:  # nothing collected (an empty --data selection, say)
        return EXIT_OK
    if code == 1:
        return EXIT_FAILED
    return EXIT_FAILED if plugin.counts["ERROR"] else EXIT_USAGE


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run a henhouse test suite (context/testing.md).")
    ap.add_argument("target", nargs="?", help="a suite, suite/group, or `all`")
    ap.add_argument("--list", action="store_true", help="list suites and groups")
    ap.add_argument("--counts", action="store_true", help="print system and data test counts without running")
    kind = ap.add_mutually_exclusive_group()
    kind.add_argument("--system", action="store_true", help="system tests only")
    kind.add_argument("--data", action="store_true", help="data tests only")
    ap.add_argument("--only", nargs="+", metavar="ID", help="run only these test files or ids (a targeted run)")
    ap.add_argument("--changed", metavar="REF", help="targeted run: the suites of the files changed since REF")
    ap.add_argument("-k", help="pytest -k expression")
    again = ap.add_mutually_exclusive_group()
    again.add_argument("--failed", action="store_true", help="rerun the failures of this target's last results file")
    again.add_argument("--resume", action="store_true", help="run what this target's last results file has no line for")
    ap.add_argument("--shard", metavar="K/N", help="run slice K of N of the selected files")
    ap.add_argument("--plan", action="store_true", help="print how to slice the selection for parallel workers")
    ap.add_argument("--minutes", type=float, default=8.0, help="slice length for --plan (default 8)")
    ap.add_argument("--skip-check", action="store_true", help="run even if the environment check fails (noted in the file)")
    argv = list(sys.argv[1:] if argv is None else argv)
    extra: List[str] = []
    if "--" in argv:  # everything after `--` goes to pytest as is
        cut = argv.index("--")
        argv, extra = argv[:cut], argv[cut + 1:]
    a = ap.parse_args(argv)

    if a.list:
        return cmd_list()

    target = a.target or "all"
    suite, group = parse_target(target)
    known = suite_names()
    if suite != "all" and suite not in known:
        print(f"unknown suite {suite!r}; suites: {', '.join(known)}", file=sys.stderr)
        return EXIT_USAGE
    suites = [s for s in known if s not in NOT_IN_ALL] if suite == "all" else [suite]
    kinds = ["system"] if a.system else ["data"] if a.data else list(KINDS)

    if a.counts:
        return cmd_counts(suites)
    if a.plan:
        return cmd_plan(suites, kinds, a.minutes)

    notes: List[str] = []
    problems = [p for s in suites for p in check_environment(s)]
    problems = list(dict.fromkeys(problems))
    if problems:
        print("The environment is not ready, so a failure would not be real (TS-H21):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        if not a.skip_check:
            return EXIT_ENV
        notes.append("--skip-check: run despite: " + "; ".join(problems))

    if suite == "all" and len(suites) > 1 and not (a.shard or a.only or a.changed or a.failed or a.resume):
        # A full run on one machine: each suite in turn, each with its own results file (TS-H31).
        worst = EXIT_OK
        for s in suites:
            cmd = [sys.executable, str(Path(__file__).resolve()), s] + (["--system"] if a.system else []) \
                + (["--data"] if a.data else []) + (["--skip-check"] if a.skip_check else [])
            code = subprocess.run(cmd, cwd=REPO_ROOT).returncode
            worst = max(worst, code)
        return worst

    label = "changed" if a.changed else target.replace("/", "-")
    if a.data:
        label += "-data"
    elif a.system:
        label += "-system"
    shard_kn = None
    if a.shard:
        try:
            k, n = (int(x) for x in a.shard.split("/"))
            assert 1 <= k <= n
        except Exception:
            print("--shard takes K/N with 1 <= K <= N", file=sys.stderr)
            return EXIT_USAGE
        shard_kn = (k, n)
        label += f"-shard{k}of{n}"

    if a.failed or a.resume:
        last = results_mod.latest_results_path(label)
        if last is None:
            print(f"no earlier results file for {label} in test-results/", file=sys.stderr)
            return EXIT_USAGE
        if a.failed:
            ids = [nid for outcome, nid in results_mod.read_lines(last) if outcome in ("FAIL", "ERROR", "XPASS")]
            ids = list(dict.fromkeys(ids))
            if not ids:
                print(f"{last.name} has no failures")
                return EXIT_OK
            selection = {"target": target, "paths": ids, "k": None, "extra": extra}
            return run_one(label, selection, "python " + shlex.join(sys.argv), notes + [f"--failed from {last.name}"])
        selection = results_mod.read_selection(last) or {}
        done = {nid for _, nid in results_mod.read_lines(last)}
        return run_one(label, selection, "python " + shlex.join(sys.argv), notes, resume_from=last, done=done)

    if a.changed:
        paths = []
        for t in changed_targets(a.changed):
            paths += [t] if t.endswith(".py") else files_for(target_paths(t, kinds))
        paths = list(dict.fromkeys(paths))
        print("Changed since " + a.changed + ": " + ", ".join(sorted({p.split("/")[1] for p in paths})))
    elif a.only:
        paths = resolve_only(a.only, suite if suite != "all" else "")
    else:
        paths = [f for s in suites for f in files_for(target_paths(s if not group else target, kinds))]
    if shard_kn:
        paths = shard(list(dict.fromkeys(p.split("::")[0] for p in paths)), *shard_kn)
    selection = {"target": target, "paths": paths, "k": a.k, "extra": extra}
    return run_one(label, selection, "python " + shlex.join(sys.argv), notes)


if __name__ == "__main__":
    raise SystemExit(main())
