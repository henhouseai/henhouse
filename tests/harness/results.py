"""The per-test results file (TS-H11).

Each run writes test-results/<date>_<time>_<suite>.md: a header (commit, machine, cores, versions, the command and
the selection), then one line per test, appended and flushed the moment that test ends, each failure followed by
its traceback, and at the end the counts and the commands that run just the failed tests again.  A run that is cut
off keeps every line written so far, which is what --resume reads.
"""

from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from tests.harness.lib import REPO_ROOT

RESULTS_DIR = REPO_ROOT / "test-results"
TIMINGS_FILE = RESULTS_DIR / "timings.json"

OUTCOMES = ("PASS", "FAIL", "ERROR", "SKIP", "XFAIL", "XPASS")
LINE_RE = re.compile(r"^(PASS|FAIL|ERROR|SKIP|XFAIL|XPASS) (\S+)")
SELECTION_RE = re.compile(r"^- Selection: `(.*)`$")


def _git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=20)
        return out.stdout.strip()
    except Exception:
        return ""


def _versions() -> str:
    from importlib import metadata
    parts = [f"Python {platform.python_version()}"]
    for pkg in ("pytest", "flask", "pymysql", "psutil", "wcwidth"):
        try:
            parts.append(f"{pkg} {metadata.version(pkg)}")
        except metadata.PackageNotFoundError:
            parts.append(f"{pkg} missing")
    return ", ".join(parts)


def new_results_path(label: str) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "run"
    path = RESULTS_DIR / f"{stamp}_{safe}.md"
    n = 2
    while path.exists():
        path = RESULTS_DIR / f"{stamp}_{safe}-{n}.md"
        n += 1
    return path


def latest_results_path(label: str) -> Optional[Path]:
    """The newest results file of a suite label, or None."""
    if not RESULTS_DIR.is_dir():
        return None
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-")
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}_" + re.escape(safe) + r"(-\d+)?\.md$")
    files = sorted(p for p in RESULTS_DIR.iterdir() if pattern.match(p.name))
    return files[-1] if files else None


def read_lines(path: Path) -> List[Tuple[str, str]]:
    """(outcome, test id) for every result line in a results file."""
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE_RE.match(line)
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def read_selection(path: Path) -> Optional[Dict]:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SELECTION_RE.match(line)
        if m:
            return json.loads(m.group(1))
    return None


def load_timings() -> Dict[str, float]:
    try:
        return json.loads(TIMINGS_FILE.read_text())
    except Exception:
        return {}


def save_timings(per_file: Dict[str, float]) -> None:
    if not per_file:
        return
    timings = load_timings()
    timings.update({k: round(v, 3) for k, v in per_file.items()})
    RESULTS_DIR.mkdir(exist_ok=True)
    tmp = TIMINGS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(timings, indent=1, sort_keys=True))
    tmp.replace(TIMINGS_FILE)


class ResultsPlugin:
    """A pytest plugin that writes the results file as the run goes."""

    def __init__(self, path: Path, label: str, command: str, selection: Dict, append: bool = False,
                 notes: Iterable[str] = ()) -> None:
        self.path = path
        self.label = label
        self.selection = selection
        self.counts = {k: 0 for k in OUTCOMES}
        self.failed: List[str] = []
        self.per_file: Dict[str, float] = {}
        self._reported: Dict[str, str] = {}
        self._start = time.time()
        if append and path.exists():
            self._fh = open(path, "a", encoding="utf-8")
            self._write(f"\n## Resumed {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            for outcome, nodeid in read_lines(path):
                self._reported[nodeid] = outcome
        else:
            self._fh = open(path, "w", encoding="utf-8")
            self._header(command, notes)

    # -- writing ---------------------------------------------------------------------------------------------------

    def _write(self, text: str) -> None:
        self._fh.write(text)
        self._fh.flush()
        try:
            os.fsync(self._fh.fileno())
        except OSError:
            pass

    def _header(self, command: str, notes: Iterable[str]) -> None:
        commit = _git("rev-parse", "HEAD") or "unknown"
        branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "unknown"
        dirty = " (uncommitted changes)" if _git("status", "--porcelain", "--untracked-files=no") else ""
        lines = [
            f"# Test results: {self.label}",
            "",
            f"- Started: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"- Commit: {commit} on {branch}{dirty}",
            f"- Machine: {socket.gethostname()}, {platform.platform()}, {os.cpu_count()} cores",
            f"- Versions: {_versions()}",
            f"- Command: `{command}`",
            f"- Selection: `{json.dumps(self.selection, sort_keys=True)}`",
        ]
        lines += [f"- Note: {n}" for n in notes]
        lines += ["", "## Tests", ""]
        self._write("\n".join(lines) + "\n")

    # -- pytest hooks ----------------------------------------------------------------------------------------------

    def pytest_runtest_logreport(self, report) -> None:
        nodeid = report.nodeid
        rel_file = nodeid.split("::", 1)[0]
        self.per_file[rel_file] = self.per_file.get(rel_file, 0.0) + getattr(report, "duration", 0.0)

        outcome = None
        if report.when == "call":
            if hasattr(report, "wasxfail"):
                outcome = "XFAIL" if report.skipped else "XPASS"
            elif report.passed:
                outcome = "PASS"
            elif report.failed:
                outcome = "FAIL"
            elif report.skipped:
                outcome = "SKIP"
        elif report.when == "setup":
            if report.skipped:
                outcome = "XFAIL" if hasattr(report, "wasxfail") else "SKIP"
            elif report.failed:
                outcome = "ERROR"
        elif report.when == "teardown" and report.failed:
            outcome = "ERROR"

        if outcome is None:
            return
        previous = self._reported.get(nodeid)
        if previous in ("FAIL", "ERROR"):
            return  # a teardown error after a failure: the test already has its line
        if previous is not None and outcome == "ERROR":
            # teardown failed after a pass: the test's line stands, the error gets its own line
            self.counts["ERROR"] += 1
            self.failed.append(nodeid)
            self._write(f"ERROR {nodeid} (teardown)\n")
            self._traceback(report)
            return
        if previous is not None:
            return
        self._reported[nodeid] = outcome
        self.counts[outcome] += 1
        if outcome in ("FAIL", "ERROR", "XPASS"):
            self.failed.append(nodeid)
        line = f"{outcome} {nodeid} ({report.duration:.2f}s)"
        if outcome == "SKIP" and isinstance(report.longrepr, tuple):
            line += f" -- {report.longrepr[2]}"
        if outcome == "XFAIL":
            line += f" -- {getattr(report, 'wasxfail', '')}"
        self._write(line + "\n")
        if outcome in ("FAIL", "ERROR"):
            self._traceback(report)

    def _traceback(self, report) -> None:
        text = getattr(report, "longreprtext", "") or str(report.longrepr)
        self._write("\n```\n" + text.rstrip() + "\n```\n\n")

    def pytest_collectreport(self, report) -> None:
        if report.failed:
            self.counts["ERROR"] += 1
            self.failed.append(report.nodeid)
            self._write(f"ERROR {report.nodeid} (collection)\n")
            self._traceback(report)

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        elapsed = time.time() - self._start
        summary = ", ".join(f"{v} {k.lower()}" for k, v in self.counts.items() if v) or "no tests ran"
        lines = ["", "## Summary", "", f"- {summary} in {elapsed:.1f}s"]
        if self.counts["SKIP"]:
            lines.append(f"- {self.counts['SKIP']} skipped: this is not a full run (TS-H22)")
        if self.counts["XPASS"]:
            lines.append("- XPASS means a known-bug test now passes: remove its xfail marker (TS-H23)")
        if self.failed:
            lines.append(f"- Run the failures again: `python tests/harness/run_suite.py {self.selection['target']} --failed`")
            ids = " ".join(self.failed[:20])
            lines.append(f"- Or by id: `python tests/harness/run_suite.py {self.selection['target']} --only {ids}`")
        self._write("\n".join(lines) + "\n")
        self._fh.close()
        save_timings(self.per_file)
